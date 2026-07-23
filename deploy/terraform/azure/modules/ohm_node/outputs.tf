output "fqdn" {
  description = "HTTPS base URL for this node (no trailing slash)"
  value       = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}

output "container_app_name" {
  value = azurerm_container_app.api.name
}

output "storage_account_name" {
  value = azurerm_storage_account.this.name
}

output "storage_container_name" {
  value = azurerm_storage_container.this.name
}

output "location" {
  value = var.location
}

output "node_role" {
  value = var.node_role
}
