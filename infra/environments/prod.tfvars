# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONNEMENT : PRODUCTION
# Organisation DevOps : Azure DevOps : IA-HQ | Projet : RE-IA
# ─────────────────────────────────────────────────────────────────────────────

# Projet & nommage
project        = "horoquatz"
project_prefix = "subs-ia-re"
environment    = "prod"
location       = "westeurope"
owner          = "HOROQUARTZ" # A Remplacer par l'email de l'équipe ou du responsable
cost_center    = "HOQ-PROD"

# Azure DevOps
devops_organization = "Azure DevOps : IA-HQ"
devops_project_name = "RE-IA"

# Resource Groups
resource_group_network_name  = "subs-ia-re-vnets-rg"
resource_group_keyvault_name = "subs-ia-keyvault-rg"
resource_group_services_name = "subs-ia-re-services-rg"

# Observabilité
log_retention_days = 90

# Réseau
vnet_address_space                = ["10.1.0.0/16"]
subnet_integration_address_prefix = "10.1.1.0/24"
subnet_endpoint_address_prefix    = "10.1.2.0/24"

# Aucun accès direct en production
developer_ip_allowlist = []

# Key Vault
key_vault_sku                        = "standard"
key_vault_soft_delete_retention_days = 90

# Storage
storage_account_tier             = "Standard"
storage_account_replication_type = "GRS"

# Cosmos DB
cosmos_consistency_level = "Session"
cosmos_failover_location = "northeurope"
cosmos_database_name     = "horoquatz-db"

# AI Search
search_sku             = "standard"
search_replica_count   = 2
search_partition_count = 1

# AI Services
ai_services_sku = "S0"

# Function App
function_app_sku             = "EP1"
function_app_os_type         = "Linux"
function_app_runtime         = "python"
function_app_runtime_version = "~4"
function_app_python_version  = "3.11"
cors_allowed_origins         = ["https://make.powerapps.com"]

# Tags supplémentaires
additional_tags = {
  criticality = "high"
}

# ─────────────────────────────────────────────────────────────────────────────
# GOUVERNANCE –
# La DSI gère les identités et RBAC. Ne pas changer à true sans accord de la DSI.
# ─────────────────────────────────────────────────────────────────────────────
create_rbac_assignments = false
