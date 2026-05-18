# Outputs for the Microsoft Foundry module

output "id" {
  value       = azurerm_cognitive_account.OpenAI.id
  description = "The ID of the Microsoft Foundry resource."
}

output "endpoint" {
  value       = azurerm_cognitive_account.OpenAI.endpoint
  description = "The endpoint of the Microsoft Foundry resource."
}

output "mistral_endpoint" {
  value       = "https://${azapi_resource.mistral_account.name}.cognitiveservices.azure.com/"
  description = "The endpoint of the Mistral AI Services account."
}

output "mistral_id" {
  value       = azapi_resource.mistral_account.id
  description = "The ID of the Mistral AI Services account."
}
