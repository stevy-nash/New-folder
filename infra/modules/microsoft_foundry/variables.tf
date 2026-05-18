# Variables for Microsoft Foundry resource

variable "name" {
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
  default = "S0"
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "developer_ip_allowlist" {
  type        = list(string)
  default     = []
  description = "IPs des développeurs autorisées (accès temporaire depuis internet, vide en prod)"
}

variable "rg_services_id" {
  type        = string
  default     = ""
  description = "ID du resource group des services IA. Nécessaire pour la création de certains services (ex: Azure OpenAI) qui requièrent une référence au RG parent."
}
