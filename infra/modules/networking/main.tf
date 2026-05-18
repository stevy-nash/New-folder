# Azure Networking resources module for Azure Cognitive Services deployment, including Virtual Network, Subnets, and Network Security Groups (NSGs) for both integration and private endpoints.
# ─── NSG Integration ────────────────────────────────────────────────────────
resource "azurerm_network_security_group" "integration" {
  name                = var.nsg_integration_name
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

# ─── NSG Endpoint ───────────────────────────────────────────────────────────
resource "azurerm_network_security_group" "endpoint" {
  name                = var.nsg_endpoint_name
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

# ─── Virtual Network ─────────────────────────────────────────────────────────
resource "azurerm_virtual_network" "VNet" {
  name                = var.vnet_name
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = var.vnet_address_space
  tags                = var.tags
}

# ─── Subnet d'intégration (Azure Functions VNet Integration) ─────────────────
resource "azurerm_subnet" "integration" {
  name                 = var.subnet_integration_name
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.VNet.name
  address_prefixes     = [var.subnet_integration_address_prefix]

  delegation {
    name = "azure-function-delegation"
    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }

  service_endpoints = ["Microsoft.Storage"] # Permet d'autoriser les connexions vers le Storage Account depuis ce subnet
}

# ─── Subnet des Private Endpoints ────────────────────────────────────────────
resource "azurerm_subnet" "endpoint" {
  name                 = var.subnet_endpoint_name
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.VNet.name
  address_prefixes     = [var.subnet_endpoint_address_prefix]

  private_endpoint_network_policies = "Disabled"
}

# ─── Associations NSG ────────────────────────────────────────────────────────
resource "azurerm_subnet_network_security_group_association" "integration" {
  subnet_id                 = azurerm_subnet.integration.id
  network_security_group_id = azurerm_network_security_group.integration.id
}

resource "azurerm_subnet_network_security_group_association" "endpoint" {
  subnet_id                 = azurerm_subnet.endpoint.id
  network_security_group_id = azurerm_network_security_group.endpoint.id
}
