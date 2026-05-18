# Azure Search Service (Microsoft Foundry) resource module for Azure Cognitive Services

resource "azurerm_search_service" "AISearch" {
  name                          = var.name
  resource_group_name           = var.resource_group_name
  location                      = var.location
  sku                           = var.sku
  replica_count                 = var.replica_count
  partition_count               = var.partition_count
  public_network_access_enabled = false
  local_authentication_enabled  = false
  tags                          = var.tags
}
