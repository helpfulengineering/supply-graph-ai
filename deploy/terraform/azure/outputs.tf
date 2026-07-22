output "resource_group" {
  value = azurerm_resource_group.this.name
}

output "peer_a_url" {
  value = module.peer_a.fqdn
}

output "peer_b_url" {
  value = module.peer_b.fqdn
}

output "edge_url" {
  value = var.enable_edge ? module.edge[0].fqdn : null
}

output "relay_url" {
  value = var.enable_relay ? module.relay[0].fqdn : null
}

output "api_key_a" {
  value     = random_password.api_key_a.result
  sensitive = true
}

output "api_key_b" {
  value     = random_password.api_key_b.result
  sensitive = true
}

output "api_key_edge" {
  value     = random_password.api_key_edge.result
  sensitive = true
}

output "api_key_relay" {
  value     = random_password.api_key_relay.result
  sensitive = true
}

output "peer_a_storage" {
  value = module.peer_a.storage_account_name
}

output "peer_b_storage" {
  value = module.peer_b.storage_account_name
}

output "matrix_env" {
  description = "Export these to run scripts/federation_matrix.sh"
  sensitive   = true
  value       = <<-EOT
    export PEER_A_URL='${module.peer_a.fqdn}'
    export PEER_B_URL='${module.peer_b.fqdn}'
    export INTERNAL_PEER_A_URL='${module.peer_a.fqdn}'
    export API_KEY_A='${random_password.api_key_a.result}'
    export API_KEY_B='${random_password.api_key_b.result}'
    export EDGE_URL='${var.enable_edge ? module.edge[0].fqdn : ""}'
    export RELAY_URL='${var.enable_relay ? module.relay[0].fqdn : ""}'
  EOT
}
