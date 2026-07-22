locals {
  suffix = random_string.suffix.result
  rg     = "${var.name_prefix}-${local.suffix}-rg"
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "random_password" "api_key_a" {
  length  = 32
  special = false
}

resource "random_password" "api_key_b" {
  length  = 32
  special = false
}

resource "random_password" "api_key_edge" {
  length  = 32
  special = false
}

resource "random_password" "api_key_relay" {
  length  = 32
  special = false
}

resource "azurerm_resource_group" "this" {
  name     = local.rg
  location = var.peer_a_location
  tags     = var.tags
}

# First apply: empty MANUAL_PEERS (FQDNs unknown until apps exist).
# Second apply (or null_resource): wire peer URLs. up.sh does a two-pass apply.

module "peer_a" {
  source              = "./modules/ohm_node"
  name                = "${var.name_prefix}${local.suffix}a"
  location            = var.peer_a_location
  resource_group_name = azurerm_resource_group.this.name
  image               = var.image
  node_role           = "peer"
  node_name           = "OHM Fed Peer A"
  api_key             = random_password.api_key_a.result
  manual_peers        = var._manual_peers_a
  min_replicas        = var.min_replicas
  cpu                 = var.cpu
  memory              = var.memory
  tags                = var.tags
  sync_rate_limit_per_min = 30
}

module "peer_b" {
  source              = "./modules/ohm_node"
  name                = "${var.name_prefix}${local.suffix}b"
  location            = var.peer_b_location
  resource_group_name = azurerm_resource_group.this.name
  image               = var.image
  node_role           = "peer"
  node_name           = "OHM Fed Peer B"
  api_key             = random_password.api_key_b.result
  manual_peers        = var._manual_peers_b
  min_replicas        = var.min_replicas
  cpu                 = var.cpu
  memory              = var.memory
  tags                = var.tags
  sync_rate_limit_per_min = 30
}

module "edge" {
  count               = var.enable_edge ? 1 : 0
  source              = "./modules/ohm_node"
  name                = "${var.name_prefix}${local.suffix}e"
  location            = var.peer_a_location
  resource_group_name = azurerm_resource_group.this.name
  image               = var.image
  node_role           = "edge"
  node_name           = "OHM Fed Edge"
  api_key             = random_password.api_key_edge.result
  manual_peers        = var._manual_peers_edge
  min_replicas        = var.min_replicas
  cpu                 = var.cpu
  memory              = var.memory
  tags                = var.tags
}

module "relay" {
  count               = var.enable_relay ? 1 : 0
  source              = "./modules/ohm_node"
  name                = "${var.name_prefix}${local.suffix}r"
  location            = var.relay_location
  resource_group_name = azurerm_resource_group.this.name
  image               = var.image
  node_role           = "relay"
  node_name           = "OHM Fed Relay"
  api_key             = random_password.api_key_relay.result
  manual_peers        = var._manual_peers_relay
  min_replicas        = var.min_replicas
  cpu                 = var.cpu
  memory              = var.memory
  tags                = var.tags
}
