variable "name" {
  description = "Short node name (used in resource names)"
  type        = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "image" {
  type = string
}

variable "node_role" {
  type    = string
  default = "peer"
}

variable "node_name" {
  type = string
}

variable "manual_peers" {
  description = "Comma-separated peer base URLs (HTTPS). Set after first apply if needed."
  type        = string
  default     = ""
}

variable "api_key" {
  description = "API_KEYS value for this node"
  type        = string
  sensitive   = true
}

variable "min_replicas" {
  type    = number
  default = 1
}

variable "cpu" {
  type    = string
  default = "0.5"
}

variable "memory" {
  type    = string
  default = "1Gi"
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "sync_interval_sec" {
  type    = number
  default = 60
}

variable "sync_rate_limit_per_min" {
  type    = number
  default = 60
}

variable "environment" {
  description = <<-EOT
    OHM ENVIRONMENT setting. Use "test" for the ephemeral federation lab (no
    LLM encryption secrets required). Use "production" for a self-host node that
    will store LLM API keys — this module then provisions LLM_ENCRYPTION_SALT
    and LLM_ENCRYPTION_PASSWORD as Container App secrets.
  EOT
  type        = string
  default     = "test"

  validation {
    condition     = contains(["test", "development", "production"], var.environment)
    error_message = "environment must be test, development, or production."
  }
}

variable "enable_jobs" {
  description = <<-EOT
    Provision Azure Cache for Redis plus a no-ingress Celery worker Container
    App, and wire JOBS_ENABLED / JOB_BROKER_URL / JOB_RESULT_BACKEND on the API.
    Leave false on the multi-peer federation lab (cost); enable for self-host
    nodes that need async generate-from-url.
  EOT
  type        = bool
  default     = false
}

variable "worker_min_replicas" {
  description = "Min replicas for the Celery worker when enable_jobs is true"
  type        = number
  default     = 1
}

variable "worker_max_replicas" {
  description = "Max replicas for the Celery worker when enable_jobs is true"
  type        = number
  default     = 2
}
