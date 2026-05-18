terraform {
  required_version = ">= 1.15.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.70"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~> 1.15"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  subscription_id = var.subscription_id

  features {
    key_vault {
      purge_soft_delete_on_destroy          = false
      recover_soft_deleted_key_vaults       = true
      purge_soft_deleted_secrets_on_destroy = false
    }
    resource_group {

      # dev  → false : détruire le RG même s'il contient des ressources
      # prod → true  : bloque la suppression si le RG n'est pas vide
      prevent_deletion_if_contains_resources = var.environment == "dev" ? false : true
    }
    cognitive_account {
      # dev  → true  : permet de recréer l'AI Service immédiatement après suppression
      # prod → false : gardé en soft-delete 48h pour récupération éventuelle
      purge_soft_delete_on_destroy = var.environment == "dev" ? true : false
    }
  }
}
