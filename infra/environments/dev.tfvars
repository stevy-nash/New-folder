# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONNEMENT : DÉVELOPPEMENT
# Subscription : pptech-ia-devtest
# Organisation DevOps : Azure DevOps : IA-HQ | Projet : RE-IA
# ─────────────────────────────────────────────────────────────────────────────


# Projet & nommage
project        = "horoquatz"
project_prefix = "pprod-ia-re"
environment    = "dev"
location       = "francecentral"
owner          = "HOROQUARTZ" # A Remplacer par l'email de l'équipe ou du responsable
cost_center    = "HOQ-DEV"

# Azure DevOps
devops_organization = "Azure DevOps : IA-HQ"
devops_project_name = "RE-IA"


# Resource Groups
resource_group_network_name  = "pprod-ia-re-vnets-rg"
resource_group_keyvault_name = "pprod-ia-keyvault-rg"
resource_group_services_name = "pprod-ia-re-services-rg"

# Observabilité
log_retention_days = 30

# Réseau
vnet_address_space                = ["10.0.0.0/16"]
subnet_integration_address_prefix = "10.0.1.0/24"
subnet_endpoint_address_prefix    = "10.0.2.0/24"

# Accès développeurs 
developer_ip_allowlist = []

# Key Vault
key_vault_sku                        = "standard"
key_vault_soft_delete_retention_days = 7

# Storage
storage_account_tier             = "Standard"
storage_account_replication_type = "LRS"

# Cosmos DB
cosmos_consistency_level = "Session"
cosmos_failover_location = ""
cosmos_database_name     = "horoquatz-db"

# AI Search
search_sku             = "basic"
search_replica_count   = 1
search_partition_count = 1

# AI Services
ai_services_sku = "S0"

# Function App
function_app_sku             = "P1v2"
function_app_os_type         = "Linux"
function_app_runtime         = "python"
function_app_runtime_version = "~4"
function_app_python_version  = "3.13"
cors_allowed_origins         = ["https://make.powerapps.com"]

# Tags supplémentaires
additional_tags = {
  criticality = "low"
}

# ─────────────────────────────────────────────────────────────────────────────
# GOUVERNANCE
# La DSI gère les identités et RBAC
# ─────────────────────────────────────────────────────────────────────────────
create_rbac_assignments = false
