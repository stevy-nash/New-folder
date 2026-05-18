# Azure Function App resource module for Azure Cognitive Services

variable "name" {
  type = string
}

variable "app_service_plan_name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "sku_name" {
  type    = string
  default = "EP1" # A changer en fonction des besoins (Ex: EP1, EP2, EP3, etc.)
}

variable "os_type" {
  type    = string
  default = "Linux"
}

variable "runtime" {
  type    = string
  default = "python" # A changer en fonction des besoins
}

variable "runtime_version" {
  type    = string
  default = "~4"
}

variable "python_version" {
  type = string
}

variable "use_managed_identity" {
  type    = bool
  default = false
}

variable "storage_account_name" {
  type = string
}

variable "storage_account_access_key" {
  type      = string
  sensitive = true
}

variable "vnet_subnet_id" {
  type = string
}

variable "key_vault_uri" {
  type = string
}

variable "cosmos_endpoint" {
  type = string
}

variable "search_endpoint" {
  type = string
}

variable "ai_endpoint" {
  type = string
}

variable "mistral_endpoint" {
  type = string
}

variable "azure_openai_api_version" {
  type    = string
  default = "2025-01-01-preview"
}

variable "app_insights_connection_string" {
  type      = string
  sensitive = true
}

variable "cors_allowed_origins" {
  type    = list(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
