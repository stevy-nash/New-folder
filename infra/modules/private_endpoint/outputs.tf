# Outputs for the Azure Private Endpoint module, providing essential information about the created Private Endpoint resource.
output "id" {
  value       = azurerm_private_endpoint.PrivateEndpoint.id
  description = "The ID of the Azure Private Endpoint."
}

output "private_ip" {
  value       = azurerm_private_endpoint.PrivateEndpoint.private_service_connection[0].private_ip_address
  description = "The private IP address of the Azure Private Endpoint."
}
