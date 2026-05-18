# Outputs for Azure Cognitive Search Service

output "id" {
  value       = azurerm_search_service.AISearch.id
  description = "The ID of the Azure Cognitive Search service."
}

output "endpoint" {
  value       = "https://${azurerm_search_service.AISearch.name}.search.windows.net"
  description = "The endpoint URL of the Azure Cognitive Search service."
}