# Azure Key Vault resource module for Azure Cognitive Services
resource "azurerm_key_vault" "KV" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = var.tenant_id
  sku_name            = var.sku_name

  # Désactivé pour la période de test — remettre à 90 AVANT la mise en production
  #soft_delete_retention_days = var.soft_delete_retention_days
  enable_rbac_authorization = true

  purge_protection_enabled = var.purge_protection_enabled

  public_network_access_enabled = length(var.developer_ip_allowlist) > 0 ? true : false

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
    ip_rules       = var.developer_ip_allowlist # [] en prod, IPs devs en dev
  }

  tags = var.tags
}