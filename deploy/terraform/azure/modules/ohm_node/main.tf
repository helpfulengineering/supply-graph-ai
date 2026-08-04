terraform {
  required_providers {
    azurerm = {
      source = "hashicorp/azurerm"
    }
    random = {
      source = "hashicorp/random"
    }
  }
}

resource "random_string" "storage" {
  length  = 6
  special = false
  upper   = false
}

locals {
  # Storage account names: 3-24 lowercase alphanumeric
  storage_account_name = substr(replace(lower("${var.name}${random_string.storage.result}"), "/[^a-z0-9]/", ""), 0, 24)
  container_name       = "ohm"
  # Include location so a region change creates a new resource instead of trying
  # to relocate an Azure resource that cannot change location under the same name
  # (Log Analytics / ACA Environment → InvalidResourceLocation).
  location_slug = replace(lower(var.location), "/[^a-z0-9]/", "")
  logs_name     = "${var.name}-${local.location_slug}-logs"
  env_name      = "${var.name}-${local.location_slug}-env"
  redis_name    = substr(replace(lower("${var.name}-redis"), "/[^a-z0-9-]/", ""), 0, 63)

  # Mirrors src/config/schema.py::is_production_like — anything outside the
  # relaxed sandboxes is a real deployment. The application REQUIRES these
  # secrets for every such environment and refuses to boot without them, so a
  # node named anything but "production" would otherwise crash-loop exactly as
  # the production worker did before v0.10.6 was fixed. Currently unreachable
  # because `environment` is validated to test|development|production, which is
  # precisely why it would bite whoever first adds a name to that list.
  provision_encryption = !contains(["development", "test"], var.environment)
  # Celery + cache DB split matches docker-compose.yml: 0=cache, 1=broker,
  # 2=results. Database 0 was previously left unused, so a node paid for Redis
  # and still ran an in-memory cache.
  redis_host = var.enable_jobs ? azurerm_redis_cache.jobs[0].hostname : ""

  # urlencode is load-bearing. Azure Redis access keys are base64, whose
  # alphabet includes "/" and "+"; an unencoded "/" terminates the URL's
  # userinfo section and silently truncates the password, so the client
  # authenticates with a fragment and fails far from the cause.
  redis_password = var.enable_jobs ? urlencode(azurerm_redis_cache.jobs[0].primary_access_key) : ""

  # ?ssl_cert_reqs=required is also load-bearing: the pinned client parses a
  # bare rediss:// URL as CERT_NONE — no error, no warning, TLS verification
  # silently off.
  redis_url_base  = var.enable_jobs ? "rediss://:${local.redis_password}@${local.redis_host}:6380" : ""
  redis_url_query = "?ssl_cert_reqs=required"
  cache_redis_url = var.enable_jobs ? "${local.redis_url_base}/0${local.redis_url_query}" : ""
  job_broker_url  = var.enable_jobs ? "${local.redis_url_base}/1${local.redis_url_query}" : ""
  job_result_url  = var.enable_jobs ? "${local.redis_url_base}/2${local.redis_url_query}" : ""
}

resource "azurerm_storage_account" "this" {
  name                     = local.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = var.tags
}

resource "azurerm_storage_container" "this" {
  name                  = local.container_name
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "private"
}

resource "azurerm_log_analytics_workspace" "this" {
  name                = local.logs_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

resource "azurerm_container_app_environment" "this" {
  name                       = local.env_name
  location                   = var.location
  resource_group_name        = var.resource_group_name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  tags                       = var.tags
}

# --- Async jobs (optional): Redis + Celery worker ----------------------------

resource "azurerm_redis_cache" "jobs" {
  count               = var.enable_jobs ? 1 : 0
  name                = local.redis_name
  location            = var.location
  resource_group_name = var.resource_group_name
  capacity            = 0
  family              = "C"
  sku_name            = "Basic"
  minimum_tls_version = "1.2"
  # Public access so ACA can reach the cache without a VNet integration.
  public_network_access_enabled = true
  non_ssl_port_enabled          = false
  tags                          = var.tags
}

resource "random_password" "llm_encryption_salt" {
  count   = local.provision_encryption ? 1 : 0
  length  = 32
  special = false
}

resource "random_password" "llm_encryption_password" {
  count   = local.provision_encryption ? 1 : 0
  length  = 48
  special = false
}

resource "azurerm_container_app" "api" {
  name                         = "${var.name}-api"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  tags                         = var.tags

  secret {
    name  = "api-keys"
    value = var.api_key
  }

  secret {
    name  = "azure-storage-key"
    value = azurerm_storage_account.this.primary_access_key
  }

  dynamic "secret" {
    for_each = var.enable_jobs ? [1] : []
    content {
      name  = "cache-redis-url"
      value = local.cache_redis_url
    }
  }

  dynamic "secret" {
    for_each = var.enable_jobs ? [1] : []
    content {
      name  = "job-broker-url"
      value = local.job_broker_url
    }
  }

  dynamic "secret" {
    for_each = var.enable_jobs ? [1] : []
    content {
      name  = "job-result-backend"
      value = local.job_result_url
    }
  }

  dynamic "secret" {
    for_each = local.provision_encryption ? [1] : []
    content {
      name  = "llm-encryption-salt"
      value = random_password.llm_encryption_salt[0].result
    }
  }

  dynamic "secret" {
    for_each = local.provision_encryption ? [1] : []
    content {
      name  = "llm-encryption-password"
      value = random_password.llm_encryption_password[0].result
    }
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = 2

    container {
      name   = "ohm-api"
      image  = var.image
      cpu    = tonumber(var.cpu)
      memory = var.memory

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "API_HOST"
        value = "0.0.0.0"
      }
      env {
        name  = "PORT"
        value = "8080"
      }
      env {
        name  = "API_PORT"
        value = "8080"
      }
      env {
        name  = "STORAGE_PROVIDER"
        value = "azure_blob"
      }
      env {
        name  = "AZURE_STORAGE_ACCOUNT"
        value = azurerm_storage_account.this.name
      }
      env {
        name  = "AZURE_STORAGE_CONTAINER"
        value = azurerm_storage_container.this.name
      }
      env {
        name        = "AZURE_STORAGE_KEY"
        secret_name = "azure-storage-key"
      }
      env {
        name        = "API_KEYS"
        secret_name = "api-keys"
      }
      env {
        name  = "CORS_ORIGINS"
        value = "*"
      }
      # LLM_ENABLED is deliberately NOT set. It is a kill switch, not an
      # enable switch: forcing it false here disabled the LLM even when an
      # operator had configured a credential, silently producing worse
      # manifests. Leaving it unset means a configured provider is used, and an
      # operator can still switch it off deliberately.
      env {
        name  = "MATCHING_EAGER_INIT"
        value = "false"
      }
      env {
        name  = "OHM_FEDERATION_ENABLED"
        value = "true"
      }
      env {
        name  = "OHM_FEDERATION_NODE_NAME"
        value = var.node_name
      }
      env {
        name  = "OHM_FEDERATION_NODE_ROLE"
        value = var.node_role
      }
      env {
        name  = "OHM_FEDERATION_DATA_DIR"
        value = "/app/storage/federation"
      }
      env {
        name  = "OHM_FEDERATION_MDNS_ENABLED"
        value = "false"
      }
      env {
        name  = "OHM_FEDERATION_MANUAL_PEERS"
        value = var.manual_peers
      }
      env {
        name  = "OHM_FEDERATION_SYNC_INTERVAL_SEC"
        value = tostring(var.sync_interval_sec)
      }
      env {
        name  = "OHM_FEDERATION_SYNC_RATE_LIMIT_PER_MIN"
        value = tostring(var.sync_rate_limit_per_min)
      }
      env {
        name  = "GUNICORN_WORKERS"
        value = "1"
      }
      env {
        name  = "GUNICORN_TIMEOUT"
        value = "300"
      }
      env {
        name  = "JOBS_ENABLED"
        value = var.enable_jobs ? "true" : "false"
      }

      dynamic "env" {
        for_each = var.enable_jobs ? [1] : []
        content {
          name        = "CACHE_REDIS_URL"
          secret_name = "cache-redis-url"
        }
      }

      # cache_backend comes from config/environments/<env>.toml. Without the URL
      # above it silently degrades to an in-memory cache, so a node paid for
      # Redis and cached per-replica anyway.
      dynamic "env" {
        for_each = var.enable_jobs ? [1] : []
        content {
          name  = "CACHE_BACKEND"
          value = "redis"
        }
      }

      dynamic "env" {
        for_each = var.enable_jobs ? [1] : []
        content {
          name        = "JOB_BROKER_URL"
          secret_name = "job-broker-url"
        }
      }

      dynamic "env" {
        for_each = var.enable_jobs ? [1] : []
        content {
          name        = "JOB_RESULT_BACKEND"
          secret_name = "job-result-backend"
        }
      }

      dynamic "env" {
        for_each = local.provision_encryption ? [1] : []
        content {
          name        = "LLM_ENCRYPTION_SALT"
          secret_name = "llm-encryption-salt"
        }
      }

      dynamic "env" {
        for_each = local.provision_encryption ? [1] : []
        content {
          name        = "LLM_ENCRYPTION_PASSWORD"
          secret_name = "llm-encryption-password"
        }
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8080
    transport        = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}

resource "azurerm_container_app" "worker" {
  count                        = var.enable_jobs ? 1 : 0
  name                         = "${var.name}-worker"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  tags                         = var.tags

  secret {
    name  = "azure-storage-key"
    value = azurerm_storage_account.this.primary_access_key
  }

  secret {
    name  = "cache-redis-url"
    value = local.cache_redis_url
  }

  secret {
    name  = "job-broker-url"
    value = local.job_broker_url
  }

  secret {
    name  = "job-result-backend"
    value = local.job_result_url
  }

  dynamic "secret" {
    for_each = local.provision_encryption ? [1] : []
    content {
      name  = "llm-encryption-salt"
      value = random_password.llm_encryption_salt[0].result
    }
  }

  dynamic "secret" {
    for_each = local.provision_encryption ? [1] : []
    content {
      name  = "llm-encryption-password"
      value = random_password.llm_encryption_password[0].result
    }
  }

  template {
    min_replicas = var.worker_min_replicas
    max_replicas = var.worker_max_replicas

    container {
      name   = "ohm-worker"
      image  = var.image
      cpu    = tonumber(var.cpu)
      memory = var.memory
      # Preserve image ENTRYPOINT; pass mode as args (Compose: command: ["worker"]).
      command = ["/usr/local/bin/docker-entrypoint.sh"]
      args    = ["worker"]

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "STORAGE_PROVIDER"
        value = "azure_blob"
      }
      env {
        name  = "AZURE_STORAGE_ACCOUNT"
        value = azurerm_storage_account.this.name
      }
      env {
        name  = "AZURE_STORAGE_CONTAINER"
        value = azurerm_storage_container.this.name
      }
      env {
        name        = "AZURE_STORAGE_KEY"
        secret_name = "azure-storage-key"
      }
      # LLM_ENABLED is deliberately NOT set. It is a kill switch, not an
      # enable switch: forcing it false here disabled the LLM even when an
      # operator had configured a credential, silently producing worse
      # manifests. Leaving it unset means a configured provider is used, and an
      # operator can still switch it off deliberately.
      # MATCHING_EAGER_INIT is not set here: it is read only in the API's
      # lifespan, which a Celery worker never runs.
      env {
        name  = "JOBS_ENABLED"
        value = "true"
      }
      env {
        name        = "CACHE_REDIS_URL"
        secret_name = "cache-redis-url"
      }

      env {
        name  = "CACHE_BACKEND"
        value = "redis"
      }

      env {
        name        = "JOB_BROKER_URL"
        secret_name = "job-broker-url"
      }
      env {
        name        = "JOB_RESULT_BACKEND"
        secret_name = "job-result-backend"
      }
      env {
        name  = "CELERY_CONCURRENCY"
        value = "1"
      }
      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      dynamic "env" {
        for_each = local.provision_encryption ? [1] : []
        content {
          name        = "LLM_ENCRYPTION_SALT"
          secret_name = "llm-encryption-salt"
        }
      }

      dynamic "env" {
        for_each = local.provision_encryption ? [1] : []
        content {
          name        = "LLM_ENCRYPTION_PASSWORD"
          secret_name = "llm-encryption-password"
        }
      }
    }
  }

  # No ingress — worker is reached only via Redis/Celery.
}
