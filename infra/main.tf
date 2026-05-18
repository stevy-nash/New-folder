# ─────────────────────────────────────────────────────────────────────────────
# DATA SOURCES
# ─────────────────────────────────────────────────────────────────────────────

data "azurerm_client_config" "current" {}

# ─────────────────────────────────────────────────────────────────────────────
# RESOURCE GROUPS
# Architecture : 3 RG distincts selon la conception
# ─────────────────────────────────────────────────────────────────────────────

module "rg_network" {
  source   = "./modules/resource_group"
  name     = local.rg_network
  location = var.location
  tags     = merge(local.common_tags, { purpose = "networking" })
}

module "rg_keyvault" {
  source   = "./modules/resource_group"
  name     = local.rg_keyvault
  location = var.location
  tags     = merge(local.common_tags, { purpose = "security" })
}

module "rg_services" {
  source   = "./modules/resource_group"
  name     = local.rg_services
  location = var.location
  tags     = merge(local.common_tags, { purpose = "ia-services" })
}

# ─────────────────────────────────────────────────────────────────────────────
# OBSERVABILITÉ (RG services)
# ─────────────────────────────────────────────────────────────────────────────

resource "azurerm_log_analytics_workspace" "LAW" {
  name                = local.log_analytics_name
  resource_group_name = module.rg_services.name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days
  tags                = local.common_tags
}

resource "azurerm_application_insights" "AINSIGHTS" {
  name                = local.app_insights_name
  resource_group_name = module.rg_services.name
  location            = var.location
  workspace_id        = azurerm_log_analytics_workspace.LAW.id
  application_type    = "web"
  tags                = local.common_tags
}

# ─────────────────────────────────────────────────────────────────────────────
# NETWORKING (RG réseau)
# VNet + 2 subnets (intégration / endpoints) + NSG restrictifs
# ─────────────────────────────────────────────────────────────────────────────

module "networking" {
  source = "./modules/networking"

  resource_group_name               = module.rg_network.name
  location                          = var.location
  vnet_name                         = local.vnet_name
  vnet_address_space                = var.vnet_address_space
  subnet_integration_name           = local.subnet_integration_name
  subnet_integration_address_prefix = var.subnet_integration_address_prefix
  subnet_endpoint_name              = local.subnet_endpoint_name
  subnet_endpoint_address_prefix    = var.subnet_endpoint_address_prefix
  nsg_integration_name              = local.nsg_integration_name
  nsg_endpoint_name                 = local.nsg_endpoint_name
  tags                              = local.common_tags
}

# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE DNS ZONES (RG réseau)
# Une zone par service + VNet Link vers le VNet principal
# ─────────────────────────────────────────────────────────────────────────────

module "dns_keyvault" {
  source              = "./modules/private_dns_zone"
  zone_name           = "privatelink.vaultcore.azure.net"
  resource_group_name = module.rg_network.name
  location            = var.location
  vnet_id             = module.networking.vnet_id
  vnet_link_name      = "${local.vnet_name}-link-kv"
  tags                = local.common_tags
}

module "dns_storage_blob" {
  source              = "./modules/private_dns_zone"
  zone_name           = "privatelink.blob.core.windows.net"
  resource_group_name = module.rg_network.name
  location            = var.location
  vnet_id             = module.networking.vnet_id
  vnet_link_name      = "${local.vnet_name}-link-blob"
  tags                = local.common_tags
}

module "dns_cosmos" {
  source              = "./modules/private_dns_zone"
  zone_name           = "privatelink.documents.azure.com"
  resource_group_name = module.rg_network.name
  location            = var.location
  vnet_id             = module.networking.vnet_id
  vnet_link_name      = "${local.vnet_name}-link-cosmos"
  tags                = local.common_tags
}

module "dns_search" {
  source              = "./modules/private_dns_zone"
  zone_name           = "privatelink.search.windows.net"
  resource_group_name = module.rg_network.name
  location            = var.location
  vnet_id             = module.networking.vnet_id
  vnet_link_name      = "${local.vnet_name}-link-search"
  tags                = local.common_tags
}

module "dns_ai_services" {
  source              = "./modules/private_dns_zone"
  zone_name           = "privatelink.cognitiveservices.azure.com"
  resource_group_name = module.rg_network.name
  location            = var.location
  vnet_id             = module.networking.vnet_id
  vnet_link_name      = "${local.vnet_name}-link-ai"
  tags                = local.common_tags
}

# Zone DNS requise pour le endpoint openai.azure.com (services Azure AI Foundry / Azure OpenAI)
module "dns_openai" {
  source              = "./modules/private_dns_zone"
  zone_name           = "privatelink.openai.azure.com"
  resource_group_name = module.rg_network.name
  location            = var.location
  vnet_id             = module.networking.vnet_id
  vnet_link_name      = "${local.vnet_name}-link-openai"
  tags                = local.common_tags
}

# ─────────────────────────────────────────────────────────────────────────────
# KEY VAULT (RG keyvault dédié)
# Private Endpoint dans le RG réseau
# ─────────────────────────────────────────────────────────────────────────────

module "key_vault" {
  source = "./modules/key_vault"

  name                = local.key_vault_name
  resource_group_name = module.rg_keyvault.name
  location            = var.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = var.key_vault_sku
  #soft_delete_retention_days = var.key_vault_soft_delete_retention_days
  developer_ip_allowlist = var.developer_ip_allowlist
  tags                   = local.common_tags
}

module "pe_keyvault" {
  source = "./modules/private_endpoint"

  name                        = local.pe_keyvault_name
  resource_group_name         = module.rg_network.name
  location                    = var.location
  subnet_id                   = module.networking.subnet_endpoint_id
  target_resource_id          = module.key_vault.id
  subresource_names           = ["vault"]
  private_dns_zone_ids        = [module.dns_keyvault.zone_id]
  private_dns_zone_group_name = "pdz-kv"
  tags                        = local.common_tags
}

# ─────────────────────────────────────────────────────────────────────────────
# STORAGE ACCOUNT (RG services)
# ─────────────────────────────────────────────────────────────────────────────

module "storage_account" {
  source     = "./modules/storage_account"
  depends_on = [module.networking]

  name                     = local.storage_account_name
  resource_group_name      = module.rg_services.name
  location                 = var.location
  account_tier             = var.storage_account_tier
  account_replication_type = var.storage_account_replication_type
  developer_ip_allowlist   = var.developer_ip_allowlist
  tags                     = local.common_tags
  subnet_ids               = [module.networking.subnet_integration_id]
}

module "pe_storage" {
  source = "./modules/private_endpoint"

  name                        = local.pe_storage_name
  resource_group_name         = module.rg_network.name
  location                    = var.location
  subnet_id                   = module.networking.subnet_endpoint_id
  target_resource_id          = module.storage_account.id
  subresource_names           = ["blob"]
  private_dns_zone_ids        = [module.dns_storage_blob.zone_id]
  private_dns_zone_group_name = "pdz-blob"
  tags                        = local.common_tags
}

# ─────────────────────────────────────────────────────────────────────────────
# COSMOS DB (RG services)
# ─────────────────────────────────────────────────────────────────────────────

module "cosmosdb" {
  source = "./modules/cosmosdb"

  name                   = local.cosmosdb_name
  resource_group_name    = module.rg_services.name
  location               = var.location
  consistency_level      = var.cosmos_consistency_level
  failover_location      = var.cosmos_failover_location
  database_name          = var.cosmos_database_name
  developer_ip_allowlist = var.developer_ip_allowlist
  tags                   = local.common_tags
}

module "pe_cosmos" {
  source = "./modules/private_endpoint"

  name                        = local.pe_cosmos_name
  resource_group_name         = module.rg_network.name
  location                    = var.location
  subnet_id                   = module.networking.subnet_endpoint_id
  target_resource_id          = module.cosmosdb.id
  subresource_names           = ["Sql"]
  private_dns_zone_ids        = [module.dns_cosmos.zone_id]
  private_dns_zone_group_name = "pdz-cosmos"
  tags                        = local.common_tags
}

# ─────────────────────────────────────────────────────────────────────────────
# AI SEARCH (RG services)
# ─────────────────────────────────────────────────────────────────────────────

module "ai_search" {
  source = "./modules/ai_search"

  name                = local.search_service_name
  resource_group_name = module.rg_services.name
  location            = var.location
  sku                 = var.search_sku
  replica_count       = var.search_replica_count
  partition_count     = var.search_partition_count
  tags                = local.common_tags
}

module "pe_search" {
  source = "./modules/private_endpoint"

  name                        = local.pe_search_name
  resource_group_name         = module.rg_network.name
  location                    = var.location
  subnet_id                   = module.networking.subnet_endpoint_id
  target_resource_id          = module.ai_search.id
  subresource_names           = ["searchService"]
  private_dns_zone_ids        = [module.dns_search.zone_id]
  private_dns_zone_group_name = "pdz-search"
  tags                        = local.common_tags
}

# ─────────────────────────────────────────────────────────────────────────────
# AI FOUNDRY / Azure AI Services (RG services)
# ─────────────────────────────────────────────────────────────────────────────

module "microsoft_foundry" {
  source = "./modules/microsoft_foundry"
  depends_on = [
    module.rg_services,
  ]

  name                   = local.ai_services_name
  resource_group_name    = module.rg_services.name
  location               = var.location
  sku_name               = var.ai_services_sku
  developer_ip_allowlist = var.developer_ip_allowlist
  tags                   = local.common_tags
  rg_services_id         = module.rg_services.id
}

module "pe_ai_foundry" {
  source = "./modules/private_endpoint"

  name                        = local.pe_ai_name
  resource_group_name         = module.rg_network.name
  location                    = var.location
  subnet_id                   = module.networking.subnet_endpoint_id
  target_resource_id          = module.microsoft_foundry.id
  subresource_names           = ["account"]
  private_dns_zone_ids        = [module.dns_ai_services.zone_id, module.dns_openai.zone_id]
  private_dns_zone_group_name = "pdz-ai"
  tags                        = local.common_tags
  depends_on = [
    module.microsoft_foundry
  ]
}

module "pe_ai_foundry_mistral" {
  source = "./modules/private_endpoint"

  name                        = local.pe_ai_mistral_name
  resource_group_name         = module.rg_network.name
  location                    = var.location
  subnet_id                   = module.networking.subnet_endpoint_id
  target_resource_id          = module.microsoft_foundry.mistral_id
  subresource_names           = ["account"]
  private_dns_zone_ids        = [module.dns_ai_services.zone_id]
  private_dns_zone_group_name = "pdz-ai-mistral"
  tags                        = local.common_tags
  depends_on = [
    module.microsoft_foundry
  ]
}

# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION APP (RG services)
# Intégration VNet via subnet_integration | Managed Identity System-Assigned
# ─────────────────────────────────────────────────────────────────────────────

module "function_app" {
  source = "./modules/function_app"

  name                  = local.function_app_name
  app_service_plan_name = local.app_service_plan_name
  resource_group_name   = module.rg_network.name
  location              = var.location

  sku_name        = var.function_app_sku
  runtime_version = var.function_app_runtime_version
  python_version  = var.function_app_python_version

  storage_account_name       = module.storage_account.name
  storage_account_access_key = module.storage_account.primary_access_key
  vnet_subnet_id             = module.networking.subnet_integration_id

  key_vault_uri = module.key_vault.uri

  cosmos_endpoint          = module.cosmosdb.endpoint
  search_endpoint          = module.ai_search.endpoint
  ai_endpoint              = module.microsoft_foundry.endpoint
  mistral_endpoint         = module.microsoft_foundry.mistral_endpoint
  azure_openai_api_version = var.azure_openai_api_version

  app_insights_connection_string = azurerm_application_insights.AINSIGHTS.connection_string

  cors_allowed_origins = var.cors_allowed_origins

  /* Quand create_rbac_assignments = true → Terraform gère les RBAC
  et la Function App peut utiliser la Managed Identity pour le Storage */
  use_managed_identity = var.create_rbac_assignments

  tags = local.common_tags

  depends_on = [
    module.pe_storage,
    module.pe_keyvault,
    module.pe_cosmos,
    module.pe_search,
    module.pe_ai_foundry,
    module.pe_ai_foundry_mistral,
    module.storage_account,
  ]
}


# ─────────────────────────────────────────────────────────────────────────────
/* RBAC – Managed Identity Function App → services

⚠️  GOUVERNANCE: Le client gere les accès RBAC
Le client gère toutes les identités et les assignments IAM.
Par défaut, ces ressources sont DÉSACTIVÉES (create_rbac_assignments = false).

*/


resource "azurerm_role_assignment" "func_kv_secrets_user" {
  count                = var.create_rbac_assignments ? 1 : 0
  scope                = module.key_vault.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = module.function_app.principal_id
}

resource "azurerm_role_assignment" "func_storage_blob_contributor" {
  count                = var.create_rbac_assignments ? 1 : 0
  scope                = module.storage_account.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = module.function_app.principal_id
}

resource "azurerm_role_assignment" "func_storage_table_contributor" {
  count                = var.create_rbac_assignments ? 1 : 0
  scope                = module.storage_account.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = module.function_app.principal_id
}

resource "azurerm_cosmosdb_sql_role_assignment" "func_cosmos_contributor" {
  count               = var.create_rbac_assignments ? 1 : 0
  resource_group_name = module.rg_services.name
  account_name        = module.cosmosdb.account_name
  role_definition_id  = "${module.cosmosdb.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002" # Cosmos DB Built-in Role: "Cosmos DB Account Contributor"
  principal_id        = module.function_app.principal_id
  scope               = module.cosmosdb.id
}

resource "azurerm_role_assignment" "func_search_index_contributor" {
  count                = var.create_rbac_assignments ? 1 : 0
  scope                = module.ai_search.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = module.function_app.principal_id
}

resource "azurerm_role_assignment" "func_ai_user" {
  count                = var.create_rbac_assignments ? 1 : 0
  scope                = module.microsoft_foundry.id
  role_definition_name = "Cognitive Services User"
  principal_id         = module.function_app.principal_id
}