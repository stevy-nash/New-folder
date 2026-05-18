# Variables for the Networking module, defining the necessary inputs for creating and configuring Azure networking resources such as virtual networks, subnets, and network security groups.
variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "vnet_name" {
  type = string
}

variable "vnet_address_space" {
  type = list(string)
}

variable "subnet_integration_name" {
  type = string
}

variable "subnet_integration_address_prefix" {
  type = string
}

variable "subnet_endpoint_name" {
  type = string
}

variable "subnet_endpoint_address_prefix" {
  type = string
}

variable "nsg_integration_name" {
  type = string
}

variable "nsg_endpoint_name" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
