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

  template {
    min_replicas = var.min_replicas
    max_replicas = 2

    container {
      name   = "ohm-api"
      image  = var.image
      cpu    = tonumber(var.cpu)
      memory = var.memory

      env {
        # Ephemeral federation lab: avoid production boot requirements
        # (LLM_ENCRYPTION_SALT/PASSWORD). Self-hosters aiming at prod should
        # set ENVIRONMENT=production and supply those secrets.
        name  = "ENVIRONMENT"
        value = "test"
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
      env {
        name  = "LLM_ENABLED"
        value = "false"
      }
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
