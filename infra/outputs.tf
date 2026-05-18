output "resource_group_network_name" {
  description = "Nom du Resource Group réseau."
  value       = module.rg_network.name
}

output "resource_group_keyvault_name" {
  description = "Nom du Resource Group Key Vault."
  value       = module.rg_keyvault.name
}

output "resource_group_services_name" {
  description = "Nom du Resource Group services IA."
  value       = module.rg_services.name
}

output "vnet_id" {
  description = "ID du Virtual Network."
  value       = module.networking.vnet_id
}

output "subnet_integration_id" {
  description = "ID du subnet d'intégration Azure Functions."
  value       = module.networking.subnet_integration_id
}

output "subnet_endpoint_id" {
  description = "ID du subnet des Private Endpoints."
  value       = module.networking.subnet_endpoint_id
}

output "key_vault_uri" {
  description = "URI du Key Vault."
  value       = module.key_vault.uri
}

output "storage_account_name" {
  description = "Nom du Storage Account."
  value       = module.storage_account.name
}

output "cosmosdb_endpoint" {
  description = "Endpoint Cosmos DB."
  value       = module.cosmosdb.endpoint
}

output "ai_search_endpoint" {
  description = "Endpoint Azure AI Search."
  value       = module.ai_search.endpoint
}

output "ai_foundry_endpoint" {
  description = "Endpoint Azure AI Services."
  value       = module.microsoft_foundry.endpoint
}

output "function_app_name" {
  description = "Nom de la Function App."
  value       = module.function_app.name
}

# ─── Informations après déploiement ── ────────────────────

output "function_app_principal_id" {
  description = "Principal ID de la Managed Identity – À communiquer à la DSI pour les RBAC assignments."
  value       = module.function_app.principal_id
}

output "dsi_rbac_summary" {
  description = "Résumé des RBAC assignments à créer par la DSI Horoquartz."
  value = {
    managed_identity_principal_id = module.function_app.principal_id
    assignments_required = {
      key_vault = {
        role  = "Key Vault Secrets User",
        scope = module.key_vault.id
      }

      storage = {
        role  = "Storage Blob Data Contributor",
        scope = module.storage_account.id
      }

      cosmos_db = {
        role  = "Cosmos DB Built-in Data Contributor",
        scope = module.cosmosdb.id
      }

      ai_search = {
        role  = "Search Index Data Contributor",
        scope = module.ai_search.id
      }

      ai_foundry = {
        role  = "Cognitive Services User",
        scope = module.microsoft_foundry.id
      }

    }
  }
}

output "app_insights_connection_string" {
  description = "Connection string Application Insights."
  value       = azurerm_application_insights.AINSIGHTS.connection_string
  sensitive   = true
}
