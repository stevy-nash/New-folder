# Azure Cosmos DB resource module for Azure Cognitive Services

resource "azurerm_cosmosdb_account" "cosmosdb" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  offer_type          = "Standard" # A changer en fonction des besoins (Ex: Standard, StandardMultiRegion, etc.)
  kind                = "GlobalDocumentDB"
  consistency_policy {
    consistency_level = var.consistency_level
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }

  dynamic "geo_location" {
    for_each = var.failover_location != "" ? [var.failover_location] : []
    content {
      location          = geo_location.value
      failover_priority = 1
    }
  }

  public_network_access_enabled     = length(var.developer_ip_allowlist) > 0 ? true : false
  is_virtual_network_filter_enabled = false
  local_authentication_disabled     = false

  tags = var.tags
}

resource "azurerm_cosmosdb_sql_database" "cosmosdbdatabase" {
  name                = var.database_name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.cosmosdb.name
}
