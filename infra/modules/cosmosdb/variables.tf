# Variables for Cosmos DB account module

variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "consistency_level" {
  type    = string
  default = "Session"
}

variable "failover_location" {
  type    = string
  default = ""
}

variable "database_name" {
  type = string
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
