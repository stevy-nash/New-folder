# Outputs for Cosmos DB Account

output "id" {
  value       = azurerm_cosmosdb_account.cosmosdb.id
  description = "The ID of the Cosmos DB account."
}

output "account_name" {
  value       = azurerm_cosmosdb_account.cosmosdb.name
  description = "The name of the Cosmos DB account."
}

output "endpoint" {
  value       = azurerm_cosmosdb_account.cosmosdb.endpoint
  description = "The endpoint URL of the Cosmos DB account."
}
