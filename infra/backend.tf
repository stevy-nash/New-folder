# Terraform backend configuration for Azure Resource Manager (azurerm) to manage state files in Azure, ensuring secure and scalable state management for the infrastructure deployment.
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-horoquartz-stevy-test"
    storage_account_name = "horoquartzstadev"
    container_name       = "tfstate"
    key                  = "npe.terraform.tfstate"
  }
}
