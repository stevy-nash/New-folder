# Outputs for the Private DNS Zone module, providing essential information about the created Private DNS Zone resource.
output "zone_id" {
  value       = azurerm_private_dns_zone.PrivateDNSZone.id
  description = "The ID of the Azure Private DNS Zone."
}

output "zone_name" {
  value       = azurerm_private_dns_zone.PrivateDNSZone.name
  description = "The name of the Azure Private DNS Zone."
}
