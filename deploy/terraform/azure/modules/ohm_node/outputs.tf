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

output "jobs_enabled" {
  value = var.enable_jobs
}

output "worker_container_app_name" {
  value = var.enable_jobs ? azurerm_container_app.worker[0].name : null
}

output "redis_hostname" {
  value = var.enable_jobs ? azurerm_redis_cache.jobs[0].hostname : null
}
