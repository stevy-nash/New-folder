# Outputs for the storage account module

output "id" {
  value = azurerm_storage_account.StorageAccount.id
}

output "name" {
  value = azurerm_storage_account.StorageAccount.name
}

output "primary_access_key" {
  value     = azurerm_storage_account.StorageAccount.primary_access_key
  sensitive = true
}
