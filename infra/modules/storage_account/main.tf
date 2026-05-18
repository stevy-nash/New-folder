# Storage Account module for Azure

resource "azurerm_storage_account" "StorageAccount" {
  name                            = var.name
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = var.account_tier
  account_replication_type        = var.account_replication_type
  min_tls_version                 = "TLS1_2"
  public_network_access_enabled   = length(var.developer_ip_allowlist) > 0 ? true : false
  allow_nested_items_to_be_public = false
  is_hns_enabled                  = true # Hierarchical Namespace pour Data Lake Gen2
  sftp_enabled                    = true # Secure File Transfer


  # Je le commente pour l'instant, je le remet plus tard, je veux d'abord faire les tests de base

  /* blob_properties {
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
  } */

  network_rules {
    default_action             = "Deny"
    bypass                     = ["AzureServices"]
    ip_rules                   = var.developer_ip_allowlist
    virtual_network_subnet_ids = var.subnet_ids
  }

  tags = var.tags
}