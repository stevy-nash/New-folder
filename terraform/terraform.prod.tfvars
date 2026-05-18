# Production Environment Variables

project_name           = "newfolder"
environment            = "production"
location               = "East US"
resource_group_name    = "rg-newfolder-prod"
vnet_address_space     = ["10.0.0.0/16"]
subnet_address_prefixes = ["10.0.1.0/24"]
app_service_sku        = "B2"

tags = {
  "CostCenter"   = "Engineering"
  "Owner"        = "DevOps Team"
  "Compliance"   = "SOC2"
  "Backup"       = "Daily"
}
