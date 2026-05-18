# Variables for the Azure Key Vault resource module, defining the necessary parameters for creating and configuring a Key Vault in Azure.
variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "tenant_id" {
  type = string
}

variable "sku_name" {
  type    = string
  default = "standard"
}

variable "purge_protection_enabled" {
  type    = bool
  default = false # a remettre a true en production apres la periode de test
}

/* variable "soft_delete_retention_days" {
    type = number
    default = 90
} */

variable "developer_ip_allowlist" {
  type    = list(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
