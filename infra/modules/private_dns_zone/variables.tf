# Variables for the Private DNS Zone module, defining the necessary inputs for creating and configuring a Private DNS Zone in Azure.
variable "zone_name" {
  type = string
}

variable "resource_group_name" {
  type = string
}
variable "location" {
  type = string
}

variable "vnet_id" {
  type = string
}

variable "vnet_link_name" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
