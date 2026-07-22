# Minimal single-peer example (self-host)

Copy this beside `modules/` if you only need one OHM API node:

```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
    random  = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

provider "azurerm" {
  features {}
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "random_password" "api_key" {
  length  = 32
  special = false
}

resource "azurerm_resource_group" "this" {
  name     = "ohm-selfhost-${random_string.suffix.result}"
  location = "eastus"
}

module "ohm" {
  source              = "../modules/ohm_node"
  name                = "ohm${random_string.suffix.result}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  image               = "touchthesun/openhardwaremanager:0.10.0"
  node_role           = "peer"
  node_name           = "My OHM Node"
  api_key             = random_password.api_key.result
  manual_peers        = "" # or "https://other-peer.example"
  min_replicas        = 1
}

output "url" {
  value = module.ohm.fqdn
}

output "api_key" {
  value     = random_password.api_key.result
  sensitive = true
}
```

See the parent [README.md](../README.md) for the full multi-peer federation lab.
