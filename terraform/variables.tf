variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "newfolder"

  validation {
    condition     = can(regex("^[a-z0-9-]{1,63}$", var.project_name))
    error_message = "Project name must be lowercase alphanumeric with hyphens, max 63 characters."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production."
  }
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "East US"

  validation {
    condition     = can(regex("^[A-Za-z ]+$", var.location))
    error_message = "Location must be a valid Azure region name."
  }
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "rg-newfolder-prod"
}

variable "vnet_address_space" {
  description = "Address space for the virtual network"
  type        = list(string)
  default     = ["10.0.0.0/16"]

  validation {
    condition     = alltrue([for cidr in var.vnet_address_space : can(cidrhost(cidr, 0))])
    error_message = "All address spaces must be valid CIDR ranges."
  }
}

variable "subnet_address_prefixes" {
  description = "Address prefixes for the subnet"
  type        = list(string)
  default     = ["10.0.1.0/24"]

  validation {
    condition     = alltrue([for cidr in var.subnet_address_prefixes : can(cidrhost(cidr, 0))])
    error_message = "All subnet prefixes must be valid CIDR ranges."
  }
}

variable "app_service_sku" {
  description = "App Service Plan SKU"
  type        = string
  default     = "B2"

  validation {
    condition     = contains(["B1", "B2", "B3", "S1", "S2", "S3", "P1V2", "P2V2", "P3V2"], var.app_service_sku)
    error_message = "SKU must be a valid App Service Plan tier."
  }
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
