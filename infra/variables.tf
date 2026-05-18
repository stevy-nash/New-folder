# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL VARIABLES CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

variable "subscription_id" {
  description = "ID de la subscription Azure cible (pptech-ia-devtest)."
  type        = string
}

variable "project" {
  description = "Nom du projet (utilisé dans les tags)."
  type        = string
  default     = "RE-IA"
}

variable "project_prefix" {
  description = "Préfixe de nommage client. Pilote tous les noms de ressources."
  type        = string
  default     = "npe"
}

variable "environment" {
  description = "Environnement cible."
  type        = string
  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "L'environnement doit être 'dev' ou 'prod'."
  }
}

variable "location" {
  description = "Région Azure de déploiement."
  type        = string
  default     = "francecentral"
}

variable "owner" {
  description = "Propriétaire des ressources (équipe)."
  type        = string
}

variable "cost_center" {
  description = "Centre de coût."
  type        = string
}

variable "additional_tags" {
  description = "Tags supplémentaires."
  type        = map(string)
  default     = {}
}

# ─────────────────────────────────────────────────────────────────────────────
# AZURE DEVOPS
# ─────────────────────────────────────────────────────────────────────────────

variable "devops_organization" {
  description = "Nom de l'organisation Azure DevOps."
  type        = string
  default     = "Azure DevOps : IA-HQ"
}

variable "devops_project_name" {
  description = "Nom du projet Azure DevOps."
  type        = string
  default     = "RE-IA"
}

# ─────────────────────────────────────────────────────────────────────────────
# RESOURCE GROUPS
# ─────────────────────────────────────────────────────────────────────────────

variable "resource_group_network_name" {
  description = "Nom du RG réseau. Si vide : généré depuis project_prefix."
  type        = string
  default     = ""
}

variable "resource_group_keyvault_name" {
  description = "Nom du RG Key Vault. Si vide : généré depuis project_prefix."
  type        = string
  default     = ""
}

variable "resource_group_services_name" {
  description = "Nom du RG services IA. Si vide : généré depuis project_prefix."
  type        = string
  default     = ""
}

# ─────────────────────────────────────────────────────────────────────────────
# NETWORKING
# ─────────────────────────────────────────────────────────────────────────────

variable "vnet_address_space" {
  description = "Espace d'adressage du VNet."
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "subnet_integration_address_prefix" {
  description = "CIDR du subnet d'intégration Azure Functions."
  type        = string
  default     = "10.0.1.0/24"
}

variable "subnet_endpoint_address_prefix" {
  description = "CIDR du subnet des Private Endpoints."
  type        = string
  default     = "10.0.2.0/24"
}

variable "developer_ip_allowlist" {
  description = "IPs développeurs autorisées (CIDR). Appliquées sur KV et Storage en dev. Vide en prod."
  type        = list(string)
  default     = []
}

# ─────────────────────────────────────────────────────────────────────────────
# OBSERVABILITÉ
# ─────────────────────────────────────────────────────────────────────────────

variable "log_retention_days" {
  description = "Rétention Log Analytics en jours."
  type        = number
  default     = 30 # À ajuster selon les besoins et coûts
}

# ─────────────────────────────────────────────────────────────────────────────
# KEY VAULT
# ─────────────────────────────────────────────────────────────────────────────

variable "key_vault_sku" {
  description = "SKU Key Vault (standard ou premium)."
  type        = string
  default     = "standard" # À changer en 'premium' si besoin de fonctionnalités avancées (HSM, RBAC, etc.)
  validation {
    condition     = contains(["standard", "premium"], var.key_vault_sku)
    error_message = "SKU doit être 'standard' ou 'premium'."
  }
}

variable "key_vault_soft_delete_retention_days" {
  description = "Rétention soft-delete Key Vault (jours)."
  type        = number
  default     = 90 # À ajuster selon les besoins et coûts
}

# ─────────────────────────────────────────────────────────────────────────────
# STORAGE ACCOUNT
# ─────────────────────────────────────────────────────────────────────────────

variable "storage_account_tier" {
  description = "Tier Storage Account (Standard ou Premium)."
  type        = string
  default     = "Standard" # À changer en 'Premium' si besoin de fonctionnalités avancées
}

variable "storage_account_replication_type" {
  description = "Réplication Storage Account (LRS, GRS, ZRS, GZRS)."
  type        = string
  default     = "LRS" # À ajuster selon les besoins de résilience et coûts (LRS = local, GRS = géo-redondant, ZRS = zone-redundant, GZRS = géo + zone)
  validation {
    condition     = contains(["LRS", "GRS", "ZRS", "GZRS", "RA-GRS", "RA-GZRS"], var.storage_account_replication_type)
    error_message = "Type de réplication invalide."
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# COSMOS DB
# ─────────────────────────────────────────────────────────────────────────────

variable "cosmos_consistency_level" {
  description = "Niveau de cohérence Cosmos DB."
  type        = string
  default     = "Session"
  validation {
    condition     = contains(["BoundedStaleness", "Eventual", "Session", "Strong", "ConsistentPrefix"], var.cosmos_consistency_level)
    error_message = "Niveau de cohérence invalide."
  }
}

variable "cosmos_failover_location" {
  description = "Région de failover géo-redondant Cosmos DB. Vide = désactivé."
  type        = string
  default     = ""
}

variable "cosmos_database_name" {
  description = "Nom de la base de données SQL Cosmos DB."
  type        = string
  default     = "horoquatz-db"
}

# ─────────────────────────────────────────────────────────────────────────────
# AI SEARCH
# ─────────────────────────────────────────────────────────────────────────────

variable "search_sku" {
  description = "SKU Azure AI Search."
  type        = string
  default     = "basic" # A changer en fonction des besoins en prod
  validation {
    condition     = contains(["free", "basic", "standard", "standard2", "standard3", "storage_optimized_l1", "storage_optimized_l2"], var.search_sku)
    error_message = "SKU AI Search invalide."
  }
}

variable "search_replica_count" {
  description = "Nombre de réplicas AI Search."
  type        = number
  default     = 1
}

variable "search_partition_count" {
  description = "Nombre de partitions AI Search."
  type        = number
  default     = 1
}

# ─────────────────────────────────────────────────────────────────────────────
# AI FOUNDRY (Azure AI Services)
# ─────────────────────────────────────────────────────────────────────────────

variable "ai_services_sku" {
  description = "SKU Azure AI Services."
  type        = string
  default     = "S0"
}

variable "azure_openai_api_version" {
  description = "Version de l'API Azure OpenAI."
  type        = string
  default     = "2025-01-01-preview"
}

# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION APP
# ─────────────────────────────────────────────────────────────────────────────

variable "function_app_sku" {
  description = "SKU du plan App Service (EP1 recommandé pour VNet Integration)."
  type        = string
  default     = "EP1" # A changer en fonction des besoins (Ex: EP1, EP2, EP3, etc.)
}

variable "function_app_os_type" {
  description = "OS de la Function App (Linux ou Windows)."
  type        = string
  default     = "Linux"
  validation {
    condition     = contains(["Linux", "Windows"], var.function_app_os_type)
    error_message = "OS type doit être 'Linux' ou 'Windows'."
  }
}

variable "function_app_runtime" {
  description = "Runtime : python "
  type        = string
  default     = "python"
}

variable "function_app_runtime_version" {
  description = "Version de l'extension Azure Functions (~4)."
  type        = string
  default     = "~4"
}


variable "function_app_python_version" {
  description = "Version Python si runtime='python'."
  type        = string
  default     = "3.11"
}


variable "cors_allowed_origins" {
  description = "Origines CORS autorisées pour la Function App (URL Power Apps)."
  type        = list(string)
  default     = ["https://make.powerapps.com"] # À ajuster selon les besoins (ex: ajouter l'URL de l'application front-end si nécessaire)
}

# ─────────────────────────────────────────────────────────────────────────────
# GOUVERNANCE 
# ─────────────────────────────────────────────────────────────────────────────

variable "create_rbac_assignments" {
  description = <<-EOT
    Active la création des RBAC assignments pour la Managed Identity de la Function App.
     - False (défaut) : ne crée pas les RBAC assignments. La DSI doit les créer manuellement après déploiement, en se basant sur le principal_id de la MI (affiché dans les outputs).
     - True : crée automatiquement les RBAC assignments pendant le déploiement. Utile pour les environnements de développement ou si la DSI accepte de déléguer cette tâche à l'équipe projet.

    Rôles concernés :
      - Key Vault Secrets User
      - Storage Blob Data Contributor
      - Cosmos DB Built-in Data Contributor
      - Search Index Data Contributor
      - Cognitive Services User
  EOT
  type        = bool
  default     = true
}
