output "resource_group_id" {
  description = "Resource Group ID"
  value       = azurerm_resource_group.rg.id
}

output "resource_group_name" {
  description = "Resource Group Name"
  value       = azurerm_resource_group.rg.name
}

output "vnet_id" {
  description = "Virtual Network ID"
  value       = azurerm_virtual_network.vnet.id
}

output "vnet_name" {
  description = "Virtual Network Name"
  value       = azurerm_virtual_network.vnet.name
}

output "subnet_id" {
  description = "Subnet ID"
  value       = azurerm_subnet.subnet.id
}

output "nsg_id" {
  description = "Network Security Group ID"
  value       = azurerm_network_security_group.nsg.id
}

output "app_service_plan_id" {
  description = "App Service Plan ID"
  value       = azurerm_service_plan.asp.id
}

output "app_service_id" {
  description = "App Service ID"
  value       = azurerm_linux_web_app.app.id
}

output "app_service_name" {
  description = "App Service Name"
  value       = azurerm_linux_web_app.app.name
}

output "app_service_default_hostname" {
  description = "App Service Default Hostname"
  value       = azurerm_linux_web_app.app.default_hostname
}

output "app_service_identity_principal_id" {
  description = "App Service Managed Identity Principal ID"
  value       = azurerm_linux_web_app.app.identity[0].principal_id
}

output "application_insights_id" {
  description = "Application Insights ID"
  value       = azurerm_application_insights.ai.id
}

output "application_insights_instrumentation_key" {
  description = "Application Insights Instrumentation Key"
  value       = azurerm_application_insights.ai.instrumentation_key
  sensitive   = true
}

output "application_insights_connection_string" {
  description = "Application Insights Connection String"
  value       = azurerm_application_insights.ai.connection_string
  sensitive   = true
}

output "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID"
  value       = azurerm_log_analytics_workspace.law.id
}

output "log_analytics_workspace_name" {
  description = "Log Analytics Workspace Name"
  value       = azurerm_log_analytics_workspace.law.name
}

output "deployment_summary" {
  description = "Summary of deployed resources"
  value = {
    resource_group     = azurerm_resource_group.rg.name
    location           = azurerm_resource_group.rg.location
    vnet_name          = azurerm_virtual_network.vnet.name
    app_service_name   = azurerm_linux_web_app.app.name
    app_service_url    = "https://${azurerm_linux_web_app.app.default_hostname}"
    monitoring_enabled = true
  }
}
