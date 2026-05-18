
locals {
  # ─────────────────────────────────────────────────────────────────────────────
  # Convention de nommage 
  # Pattern : {project_prefix}-{composant}
  # ─────────────────────────────────────────────────────────────────────────────

  p = var.project_prefix # alias court pour lisibilité

  # ─── Resource Groups (3 RG distincts – architecture client) ─────────────────
  rg_network  = var.resource_group_network_name != "" ? var.resource_group_network_name : "${local.p}-vnets-rg"
  rg_keyvault = var.resource_group_keyvault_name != "" ? var.resource_group_keyvault_name : "${local.p}-keyvault-rg"
  rg_services = var.resource_group_services_name != "" ? var.resource_group_services_name : "${local.p}-services-rg"


  # ─── Réseau ────────────────────────────────────────────────────────────────
  vnet_name               = "${local.p}-vnet"
  subnet_integration_name = "${local.p}-sub-integration-${var.environment}1"
  subnet_endpoint_name    = "${local.p}-sub-endpoint-${var.environment}1"
  nsg_integration_name    = "${local.p}-nsg-integration"
  nsg_endpoint_name       = "${local.p}-nsg-endpoint"


  # ─── Services IA ────────────────────────────────────────────────────────────
  log_analytics_name    = "${local.p}-log"
  app_insights_name     = "${local.p}-appi"
  cosmosdb_name         = "${local.p}-cosmos"
  search_service_name   = "${local.p}-aisearch-${var.environment}"
  ai_services_name      = "${local.p}-iafoundry"
  function_app_name     = "${local.p}-azurefunction-${var.environment}"
  app_service_plan_name = "${local.p}-asp"


  # Storage Account : pas de tiret, max 24 chars, tout minuscule
  storage_account_name = lower(substr(replace("${local.p}cs${var.environment}", "-", ""), 0, 24))


  # ─── Key Vault (RG dédié) ───────────────────────────────────────────────────
  key_vault_name = "${local.p}-keyvault"


  # ─── Private Endpoints (dans le RG réseau) ──────────────────────────────────
  pe_cosmos_name     = "${local.p}-ep-cosmos"
  pe_search_name     = "${local.p}-ep-aisearch"
  pe_storage_name    = "${local.p}-ep-cs"
  pe_ai_name         = "${local.p}-ep-iafoundry"
  pe_ai_mistral_name = "${local.p}-ep-iafoundry-mistral"
  pe_keyvault_name   = "${local.p}-ep-keyvault"


  # ─── Tags communs ────────────────────────────────────────────────────────────
  common_tags = merge({
    project        = var.project
    environment    = var.environment
    location       = var.location
    managed_by     = "terraform"
    owner          = var.owner
    cost_center    = var.cost_center
    devops_org     = var.devops_organization
    devops_project = var.devops_project_name
    },
  var.additional_tags)
}
