# Outputs for the Function App module, providing essential information about the created Function App resource.

output "id" {
  value       = azurerm_linux_function_app.APP.id
  description = "The ID of the Azure Function App."
}

output "name" {
  value       = azurerm_linux_function_app.APP.name
  description = "The name of the Azure Function App."
}

output "principal_id" {
  value       = azurerm_linux_function_app.APP.identity[0].principal_id
  description = "The principal ID of the Azure Function App's managed identity."
}

output "default_hostname" {
  value       = azurerm_linux_function_app.APP.default_hostname
  description = "The default hostname of the Azure Function App."
}
