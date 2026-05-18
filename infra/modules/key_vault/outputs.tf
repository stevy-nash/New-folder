# Outputs for the Azure Key Vault module, providing essential information about the created Key Vault resource.
output "id" {
  value       = azurerm_key_vault.KV.id
  description = "The ID of the Azure Key Vault."
}

output "uri" {
  value       = azurerm_key_vault.KV.vault_uri
  description = "The URI of the Azure Key Vault."
}
