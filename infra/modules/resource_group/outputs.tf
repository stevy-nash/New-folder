# Outputs for the Resource Group module

output "name" {
  value       = azurerm_resource_group.ResourceGroup.name
  description = "The name of the resource group."
}

output "id" {
  value       = azurerm_resource_group.ResourceGroup.id
  description = "The ID of the resource group."
}
