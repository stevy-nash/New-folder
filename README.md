# RE-IA - Terraform Infrastructure

Infrastructure Terraform pour deploiement Azure de la plateforme RE-IA.

## Sommaire

1. Objectif
2. Demarrage rapide
3. Architecture cible
4. Structure du repository
5. Processus Terraform (local)
6. Variables et conventions
7. Modules Terraform
8. Pipelines CI/CD
9. Checklist de reprise
10. Commandes utiles

## 1. Objectif

Le dossier `infra/` deploie les briques Azure suivantes :

- Resource Groups (reseau, services, securite)
- Networking (VNet, subnets, NSG, DNS prive)
- Key Vault
- Storage Account
- Cosmos DB SQL API
- Azure AI Search
- Azure AI Services / OpenAI (Foundry)
- Function App (Python)
- Observabilite (Log Analytics, Application Insights)

Principes techniques :

- Reseau prive via Private Endpoints
- Authentification par Managed Identity
- Segmentation par modules Terraform reutilisables
- Parametrage par environnement via `environments/*.tfvars`

## 2. Demarrage rapide

### Prerequis

- Terraform >= 1.6
- Azure CLI connecte sur la subscription cible
- Droits suffisants sur la subscription et sur le backend tfstate

### 1) Se placer dans le dossier infra

```bash
cd infra
```

### 2) Initialiser Terraform avec le backend cible

```bash
terraform init -backend-config="environments/dev.azurerm.tfbackend"
```

### 3) Verifier et planifier

```bash
terraform fmt -recursive
terraform validate
terraform plan -var-file="environments/dev.tfvars"
```

### 4) Appliquer

```bash
terraform apply -var-file="environments/dev.tfvars"
```

## 3. Architecture cible

Architecture logique en 3 zones :

- Zone reseau
  - VNet
  - Subnet integration (Function App)
  - Subnet endpoints (Private Endpoints)
  - DNS zones privees
- Zone securite
  - Key Vault
- Zone services
  - Storage, Cosmos, AI Search, AI Services/OpenAI, Function App, Observabilite

Flux principal :

1. La Function App s'integre au VNet
2. Elle accede aux services data/IA via Private Endpoints
3. Les secrets et configurations sensibles sont resolus via Key Vault / identité managée

## 4. Structure du repository

Arborescence utile pour la reprise :

```text
infra/
|- backend.tf
|- versions.tf
|- locals.tf
|- variables.tf
|- main.tf
|- outputs.tf
|- environments/
|  |- dev.tfvars
|  |- dev.azurerm.tfbackend
|  |- prod.tfvars
|  |- prod.azurerm.tfbackend
|- modules/
|  |- resource_group/
|  |- networking/
|  |- private_dns_zone/
|  |- private_endpoint/
|  |- key_vault/
|  |- storage_account/
|  |- cosmosdb/
|  |- ai_search/
|  |- microsoft_foundry/
|  |- function_app/
```

## 5. Processus Terraform (local)

1. `terraform init` avec le backend de l'environnement
2. `terraform fmt -recursive`
3. `terraform validate`
4. `terraform plan -var-file=...`
5. `terraform apply -var-file=...`

Pour detruire un environnement de test :

```bash
terraform destroy -var-file="environments/dev.tfvars"
```

## 6. Variables et conventions

Points d'entree importants :

- `variables.tf`
  - Variables globales (subscription, environment, tags)
  - Parametres reseau, data, ia, function app
- `locals.tf`
  - Convention de nommage centralisee
  - Tags communs
- `versions.tf`
  - Contraintes de versions Terraform/providers
  - Feature flags du provider AzureRM selon l'environnement

Convention recommandee :

- Ne pas coder de valeurs en dur dans les modules
- Passer toutes les valeurs d'environnement par `environments/*.tfvars`
- Garder les noms derives de `project_prefix`

Deployments IA disponibles dans l'infra :

- gpt-5
- gpt-4-1
- gpt-5-mini
- mistral-large-3

## 7. Modules Terraform

Resume des modules et responsabilites :

- `resource_group`: creation des RG
- `networking`: VNet, subnets, NSG
- `private_dns_zone`: zones DNS privees + liens VNet
- `private_endpoint`: endpoints prives et associations DNS
- `key_vault`: coffre de secrets et controle reseau
- `storage_account`: stockage applicatif
- `cosmosdb`: compte + base SQL API
- `ai_search`: service de recherche
- `microsoft_foundry`: compte AI Services/OpenAI
- `function_app`: plan App Service + Function App Linux

## 8. Pipelines CI/CD

Les pipelines sont situes dans `.azure/`.

Schema classique des etapes :

1. Init/Validation
2. Plan
3. Validation manuelle
4. Apply

Bonnes pratiques :

- Verifier que le lockfile provider est versionne
- Garder les variables sensibles hors repository
- Utiliser des service connections separees par environnement

## 9. Checklist

Utiliser cette checklist

1. Verifier l'acces Azure (`az account show`)
2. Verifier le backend tfstate (`environments/*.azurerm.tfbackend`)
3. Lancer `terraform init` puis `terraform validate`
4. Comparer `dev.tfvars` et `prod.tfvars`
5. Executer un `terraform plan` sur l'environnement cible
6. Relire les changements reseau et RBAC avant apply
7. Verifier les outputs utiles apres deploiement

## 10. Commandes utiles

```bash
# Initialisation
terraform init -backend-config="environments/dev.azurerm.tfbackend"

# Validation
terraform fmt -recursive
terraform validate

# Plan / Apply
terraform plan  -var-file="environments/dev.tfvars"
terraform apply -var-file="environments/dev.tfvars"

# Outputs
terraform output
terraform output -json

# Destruction (environnement de test uniquement)
terraform destroy -var-file="environments/dev.tfvars"
```
