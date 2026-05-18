# Production Azure Infrastructure with Terraform

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85"
    }
  }
}

provider "azurerm" {
  features {
    app_service {
      purge_soft_delete_on_destroy = true
    }
    key_vault {
      purge_soft_delete_on_destroy = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

# Resource Group
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location

  tags = merge(
    local.common_tags,
    {
      "Environment" = var.environment
    }
  )
}

# Virtual Network
resource "azurerm_virtual_network" "vnet" {
  name                = "${local.name_prefix}-vnet-${var.environment}"
  address_space       = var.vnet_address_space
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  tags = local.common_tags
}

# Subnet
resource "azurerm_subnet" "subnet" {
  name                 = "${local.name_prefix}-subnet-${var.environment}"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = var.subnet_address_prefixes

  service_endpoints = [
    "Microsoft.Storage",
    "Microsoft.Sql",
    "Microsoft.KeyVault"
  ]
}

# Network Security Group
resource "azurerm_network_security_group" "nsg" {
  name                = "${local.name_prefix}-nsg-${var.environment}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  security_rule {
    name                       = "AllowHTTP"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 101
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = local.common_tags
}

# Associate NSG with Subnet
resource "azurerm_subnet_network_security_group_association" "subnet_nsg" {
  subnet_id                 = azurerm_subnet.subnet.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

# App Service Plan
resource "azurerm_service_plan" "asp" {
  name                = "${local.name_prefix}-asp-${var.environment}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  os_type             = "Linux"
  sku_name            = var.app_service_sku

  tags = local.common_tags
}

# App Service
resource "azurerm_linux_web_app" "app" {
  name                = "${local.name_prefix}-app-${var.environment}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  service_plan_id     = azurerm_service_plan.asp.id

  https_only                    = true
  minimum_tls_version           = "1.2"
  client_certificate_enabled    = false
  client_affinity_enabled       = false
  virtual_network_subnet_id     = azurerm_subnet.subnet.id

  site_config {
    always_on                   = true
    use_32_bit_worker_process  = false
    websockets_enabled         = true
    managed_pipeline_mode      = "Integrated"
    health_check_path          = "/health"

    application_stack {
      python_version = "3.11"
    }

    ip_restriction {
      virtual_network_subnet_id = azurerm_subnet.subnet.id
      action                    = "Allow"
      priority                  = 100
      name                      = "AllowVNet"
    }
  }

  app_settings = {
    "WEBSITE_RUN_FROM_PACKAGE"        = "0"
    "PYTHON_ENABLE_WORKER_EXTENSIONS" = "1"
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.ai.connection_string
    "ApplicationInsightsAgent_EXTENSION_VERSION" = "~3"
  }

  identity {
    type = "SystemAssigned"
  }

  logs {
    detailed_error_messages = true
    failed_request_tracing  = true

    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 35
      }
    }
  }

  tags = local.common_tags

  depends_on = [azurerm_application_insights.ai]
}

# Application Insights
resource "azurerm_application_insights" "ai" {
  name                = "${local.name_prefix}-appinsights-${var.environment}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"

  tags = local.common_tags
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "law" {
  name                = "${local.name_prefix}-law-${var.environment}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = local.common_tags
}

# Diagnostic Settings for App Service
resource "azurerm_monitor_diagnostic_setting" "app_diagnostics" {
  name                       = "${local.name_prefix}-app-diagnostics"
  target_resource_id         = azurerm_linux_web_app.app.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id

  enabled_log {
    category = "AppServiceHTTPLogs"
  }

  enabled_log {
    category = "AppServiceConsoleLogs"
  }

  enabled_log {
    category = "AppServiceAppLogs"
  }

  enabled_log {
    category = "AppServiceAuditLogs"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

# Local variables for naming and common tags
locals {
  name_prefix = lower(replace(var.project_name, "-", ""))

  common_tags = {
    "Project"     = var.project_name
    "Environment" = var.environment
    "ManagedBy"   = "Terraform"
    "CreatedDate" = timestamp()
  }
}
