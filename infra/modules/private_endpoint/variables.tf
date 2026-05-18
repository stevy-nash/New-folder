# Variables for the Private Endpoint module, defining the necessary inputs for creating and configuring an Azure Private Endpoint resource, including its name, location, subnet association, target resource, and related Private DNS Zones.
variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "subnet_id" {
  type = string
}

variable "target_resource_id" {
  type = string
}

variable "subresource_names" {
  type = list(string)
}

variable "private_dns_zone_ids" {
  type = list(string)
}

variable "private_dns_zone_group_name" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
