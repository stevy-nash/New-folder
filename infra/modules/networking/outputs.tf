# Outputs for the Azure Virtual Network and Subnets module, providing essential information about the created networking resources.
output "vnet_id" {
  value       = azurerm_virtual_network.VNet.id
  description = "The ID of the Azure Virtual Network."
}

output "subnet_integration_id" {
  value       = azurerm_subnet.integration.id
  description = "The ID of the integration subnet."
}

output "subnet_endpoint_id" {
  value       = azurerm_subnet.endpoint.id
  description = "The ID of the endpoint subnet."
}
