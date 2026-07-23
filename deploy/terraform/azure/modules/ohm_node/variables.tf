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
