variable "name_prefix" {
  description = "Prefix for ephemeral resource names (lowercase alphanumeric)"
  type        = string
  default     = "ohmfed"
}

variable "subscription_id" {
  description = "Azure subscription ID (optional if set via ARM_SUBSCRIPTION_ID / az account)"
  type        = string
  default     = null
}

variable "image" {
  description = "OHM API container image (Docker Hub)"
  type        = string
  default     = "touchthesun/openhardwaremanager:0.10.1"
}

variable "enable_edge" {
  description = "Provision an edge-role node (federation API hidden)"
  type        = bool
  default     = true
}

variable "enable_relay" {
  description = "Provision a relay-role node (API on; no distinct protocol yet)"
  type        = bool
  default     = true
}

variable "enable_frontend" {
  description = "Also deploy frontend Container Apps (optional UI)"
  type        = bool
  default     = false
}

variable "frontend_image" {
  description = "OHM frontend image"
  type        = string
  default     = "touchthesun/openhardwaremanager-frontend:0.10.1"
}

variable "peer_a_location" {
  type    = string
  default = "westus3"
}

variable "peer_b_location" {
  type    = string
  default = "eastus"
}

variable "relay_location" {
  description = "Region for the relay node. Prefer a third region so it does not compete with peer_b for ACA environment capacity."
  type        = string
  default     = "westus2"
}

variable "min_replicas" {
  description = "Min replicas while testing (use 0 to save cost when idle before destroy)"
  type        = number
  default     = 1
}

# Consumption plan only allows fixed CPU/memory pairs, e.g.:
#   0.25/0.5Gi, 0.5/1Gi, 0.75/1.5Gi, 1.0/2Gi, 1.25/2.5Gi, 1.5/3Gi, 1.75/3.5Gi, 2.0/4Gi
variable "cpu" {
  type    = string
  default = "0.5"
}

variable "memory" {
  type    = string
  default = "1Gi"
}

variable "tags" {
  type = map(string)
  default = {
    project = "ohm-federation-ephemeral"
    purpose = "federation-validation"
  }
}

# Wired by scripts/up.sh on the second apply (comma-separated HTTPS origins).
variable "_manual_peers_a" {
  type    = string
  default = ""
}

variable "_manual_peers_b" {
  type    = string
  default = ""
}

variable "_manual_peers_edge" {
  type    = string
  default = ""
}

variable "_manual_peers_relay" {
  type    = string
  default = ""
}
