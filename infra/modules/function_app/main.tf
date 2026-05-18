# Azure Function App resource module for Azure Cognitive Services, supporting both Linux and Windows environments based on the specified runtime.
locals {
  app_settings = merge(
    {
      FUNCTIONS_EXTENSION_VERSION           = var.runtime_version
      FUNCTIONS_WORKER_RUNTIME              = var.runtime
      APPLICATIONINSIGHTS_CONNECTION_STRING = var.app_insights_connection_string
      KEYVAULT_URL                          = var.key_vault_uri
      COSMOS_ENDPOINT                       = var.cosmos_endpoint
      COSMOS_CONNECTION_STRING              = "@Microsoft.KeyVault(SecretUri=${var.key_vault_uri}secrets/cosmosdb-connection-string/)"
      SEARCH_ENDPOINT                       = var.search_endpoint
      AZURE_OPENAI_ENDPOINT                 = var.ai_endpoint
      MISTRAL_ENDPOINT                      = var.mistral_endpoint
      AZURE_OPENAI_API_VERSION              = var.azure_openai_api_version
      AzureWebJobsStorage__accountName      = var.storage_account_name
      AzureWebJobsStorage__blobServiceUri   = "https://${var.storage_account_name}.blob.core.windows.net"
      AzureWebJobsStorage__credential       = "managedidentity"
      AzureWebJobsStorage__queueServiceUri  = "https://${var.storage_account_name}.queue.core.windows.net"
      AzureWebJobsStorage__tableServiceUri  = "https://${var.storage_account_name}.table.core.windows.net"
    },
    var.use_managed_identity ? {
      AzureWebJobsStorage__credential = "managedidentity"
    } : {}
  )
}

# ─── Plan App Service ────────────────────────────────────────────────────────
resource "azurerm_service_plan" "ASP" {
  name                = var.app_service_plan_name
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux" # Python → Linux uniquement
  sku_name            = var.sku_name
  tags                = var.tags
}

# ─── Linux Function App ───────────────────────────────────────────────────────
# Python est uniquement supporté sur Linux.
resource "azurerm_linux_function_app" "APP" {
  name                      = var.name
  resource_group_name       = var.resource_group_name
  location                  = var.location
  service_plan_id           = azurerm_service_plan.ASP.id
  virtual_network_subnet_id = var.vnet_subnet_id
  https_only                = true

  # Authentification Storage : clé OU Managed Identity (mutuellement exclusifs)
  storage_account_name          = var.storage_account_name
  storage_account_access_key    = var.use_managed_identity ? null : var.storage_account_access_key
  storage_uses_managed_identity = var.use_managed_identity ? true : null

  identity {
    type = "SystemAssigned"
  }

  app_settings = local.app_settings

  site_config {
    always_on = true

    vnet_route_all_enabled = true

    application_stack {
      python_version = var.python_version
    }
    cors {
      allowed_origins     = var.cors_allowed_origins
      support_credentials = false
    }
  }

  tags = var.tags
}
