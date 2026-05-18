# AI Search module variables for Microsoft Foundry resource

variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "sku" {
  type    = string
  default = "basic" # A changer soit en standard ou premium
}

variable "replica_count" {
  type    = number
  default = 1 # A changer soit en 3 ou 6
}

variable "partition_count" {
  type    = number
  default = 1 # A changer soit en 3 ou 6
}

variable "tags" {
  type    = map(string)
  default = {}
}
