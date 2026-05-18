# Microsoft Foundry resource module - Azure OpenAI Service

resource "azurerm_cognitive_account" "OpenAI" {
  name                          = var.name
  resource_group_name           = var.resource_group_name
  location                      = var.location
  kind                          = "OpenAI"
  sku_name                      = var.sku_name
  custom_subdomain_name         = var.name
  public_network_access_enabled = length(var.developer_ip_allowlist) > 0 ? true : false
  local_auth_enabled            = false

  dynamic "network_acls" {
    for_each = length(var.developer_ip_allowlist) > 0 ? [1] : []
    content {
      default_action = "Deny"
      ip_rules       = var.developer_ip_allowlist
    }
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_cognitive_account" "DocumentIntelligence" {
  name                          = "${var.name}-di"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  kind                          = "FormRecognizer"
  sku_name                      = var.sku_name
  custom_subdomain_name         = "${var.name}-di"
  public_network_access_enabled = length(var.developer_ip_allowlist) > 0 ? true : false
  local_auth_enabled            = true

  dynamic "network_acls" {
    for_each = length(var.developer_ip_allowlist) > 0 ? [1] : []
    content {
      default_action = "Deny"
      ip_rules       = var.developer_ip_allowlist
    }
  }

  tags = var.tags
}

#resource "azurerm_cognitive_deployment" "gpt_5" {
#  name                 = "gpt-5"
#  cognitive_account_id = azurerm_cognitive_account.OpenAI.id
#
#  model {
#    format  = "OpenAI"
#    name    = "gpt-5"
#    version = "2025-08-07"
#  }
#
#  scale {
#    type     = "DataZoneStandard"
#    capacity = 300
#  }
#}
#
#resource "azurerm_cognitive_deployment" "gpt_4_1" {
#  name                 = "gpt-4-1"
#  cognitive_account_id = azurerm_cognitive_account.OpenAI.id
#
#  model {
#    format  = "OpenAI"
#    name    = "gpt-4.1"
#    version = "2025-04-14"
#  }
#
#  scale {
#    type     = "DataZoneStandard"
#    capacity = 300
#  }
#}
#
#resource "azurerm_cognitive_deployment" "gpt_5_mini" {
#  name                 = "gpt-5-mini"
#  cognitive_account_id = azurerm_cognitive_account.OpenAI.id
#
#  model {
#    format  = "OpenAI"
#    name    = "gpt-5-mini"
#    version = "2025-08-07"
#  }
#
#  scale {
#    type     = "DataZoneStandard"
#    capacity = 300
#  }
#}
#
#
## Compte AIServices dédié aux modèles Mistral (azapi requis, kind AIServices non supporté par azurerm ~> 3.x)
resource "azapi_resource" "mistral_account" {
  type      = "Microsoft.CognitiveServices/accounts@2024-06-01-preview"
  name      = "${var.name}-mistral"
  location  = var.location
  parent_id = var.rg_services_id

  body = jsonencode({
    kind = "AIServices"
    sku = {
      name = var.sku_name
    }
    properties = {
      customSubDomainName = "${var.name}-mistral"
      publicNetworkAccess = length(var.developer_ip_allowlist) > 0 ? "Enabled" : "Disabled"
      disableLocalAuth    = true
      networkAcls = length(var.developer_ip_allowlist) > 0 ? {
        defaultAction = "Deny"
        ipRules       = [for ip in var.developer_ip_allowlist : { value = ip }]
      } : null
    }
  })

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

#resource "azapi_resource" "mistral_large_3" {
#  type      = "Microsoft.CognitiveServices/accounts/deployments@2024-06-01-preview"
#  name      = "mistral-large-3"
#  parent_id = azapi_resource.mistral_account.id
#
#  body = jsonencode({
#    properties = {
#      model = {
#        format  = "Mistral AI"
#        name    = "Mistral-Large-3"
#        version = "1"
#      }
#    }
#    sku = {
#      name     = "DataZoneStandard"
#      capacity = 20
#    }
#  })
#}
