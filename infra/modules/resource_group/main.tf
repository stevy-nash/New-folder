# Resource Group module for Azure

resource "azurerm_resource_group" "ResourceGroup" {
  name     = var.name
  location = var.location
  tags     = var.tags
}
