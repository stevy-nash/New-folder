# Azure Private DNS Zone resource module for Azure Cognitive Services deployment, including the creation of a Private DNS Zone and its association with a Virtual Network.
resource "azurerm_private_dns_zone" "PrivateDNSZone" {
  name                = var.zone_name
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "PrivateDNSZoneLink" {
  name                  = var.vnet_link_name
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.PrivateDNSZone.name
  virtual_network_id    = var.vnet_id
  registration_enabled  = false
  tags                  = var.tags
}
