# Terraform Production Setup Guide

Complete guide to setting up and managing Terraform infrastructure for production Azure deployment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Azure Setup](#azure-setup)
3. [Local Development](#local-development)
4. [Backend Configuration](#backend-configuration)
5. [Variable Management](#variable-management)
6. [Pipeline Configuration](#pipeline-configuration)
7. [Deployment Process](#deployment-process)
8. [State Management](#state-management)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Terraform**: >= 1.6.0
  ```bash
  # macOS with Homebrew
  brew install terraform

  # Windows with Chocolatey
  choco install terraform

  # Or download from https://www.terraform.io/downloads
  ```

- **Azure CLI**: >= 2.50.0
  ```bash
  # macOS with Homebrew
  brew install azure-cli

  # Windows with Chocolatey
  choco install azure-cli

  # Or download from https://learn.microsoft.com/cli/azure/install-azure-cli
  ```

- **Python**: >= 3.11 (for validation scripts)
  ```bash
  python --version
  ```

### Azure Permissions

- Subscription Contributor or Owner role
- Permission to create Service Principals
- Permission to create Storage Accounts
- Permission to create resource groups

### Verify Installation

```bash
terraform --version
az --version
python --version
```

## Azure Setup

### Step 1: Login to Azure

```bash
# Interactive login
az login

# Set default subscription
az account set --subscription "<SUBSCRIPTION_ID>"

# Verify you're in the correct subscription
az account show
```

### Step 2: Create Service Principal

Service Principal is required for automated authentication in CI/CD pipelines.

```bash
# Create Service Principal with Contributor role
az ad sp create-for-rbac \
  --name "terraform-prod-sp" \
  --role Contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>
```

**Output will include:**
```json
{
  "appId": "<CLIENT_ID>",
  "displayName": "terraform-prod-sp",
  "password": "<CLIENT_SECRET>",
  "tenant": "<TENANT_ID>"
}
```

**⚠️ Save these values securely!** They will be used in Azure DevOps.

### Step 3: Create Backend Storage Account

Terraform state must be stored in Azure Storage for security and collaboration.

```bash
# Set variables
RESOURCE_GROUP="rg-terraform-state"
STORAGE_ACCOUNT="tfstateproduction"
CONTAINER_NAME="tfstate"
REGION="eastus"

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $REGION

# Create storage account
az storage account create \
  --resource-group $RESOURCE_GROUP \
  --name $STORAGE_ACCOUNT \
  --sku Standard_LRS \
  --encryption-services blob

# Create blob container
az storage container create \
  --account-name $STORAGE_ACCOUNT \
  --name $CONTAINER_NAME

# Enable versioning
az storage account blob-service-properties update \
  --account-name $STORAGE_ACCOUNT \
  --enable-change-feed true \
  --enable-versioning true

# Retrieve storage account key
STORAGE_KEY=$(az storage account keys list \
  --resource-group $RESOURCE_GROUP \
  --account-name $STORAGE_ACCOUNT \
  --query '[0].value' -o tsv)

echo "Storage Key: $STORAGE_KEY"
```

### Step 4: Configure Service Principal Access to Backend

Grant the Service Principal access to the storage account:

```bash
SP_OBJECT_ID=$(az ad sp show \
  --id <CLIENT_ID> \
  --query id -o tsv)

az role assignment create \
  --role "Storage Blob Data Contributor" \
  --assignee $SP_OBJECT_ID \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT
```

## Local Development

### Step 1: Clone Repository

```bash
git clone <REPOSITORY_URL>
cd New-folder
```

### Step 2: Initialize Terraform

```bash
cd terraform

terraform init \
  -backend-config="resource_group_name=rg-terraform-state" \
  -backend-config="storage_account_name=tfstateproduction" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=prod.terraform.tfstate"
```

### Step 3: Validate Configuration

```bash
# Format check
terraform fmt -check -recursive

# Auto-format (if needed)
terraform fmt -recursive

# Validate syntax
terraform validate
```

### Step 4: Review Plan

```bash
# Generate plan
terraform plan -var-file="terraform.prod.tfvars" -out=tfplan

# View plan in detail
terraform show tfplan

# Save plan output
terraform show tfplan > plan_output.txt
```

### Step 5: Apply Configuration

```bash
# ⚠️ Review the plan carefully before applying!

# Apply the plan
terraform apply tfplan

# Or auto-approve (not recommended in production)
terraform apply -var-file="terraform.prod.tfvars" -auto-approve
```

### Step 6: View Outputs

```bash
# Display all outputs
terraform output

# Get specific output
terraform output app_service_default_hostname

# Output as JSON
terraform output -json > outputs.json
```

## Backend Configuration

### Backend File Structure

Create `terraform/backend.tf` for backend configuration:

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "tfstateproduction"
    container_name       = "tfstate"
    key                  = "prod.terraform.tfstate"
  }
}
```

### Switching Backends

```bash
# Switch to different backend
terraform init \
  -reconfigure \
  -backend-config="key=staging.terraform.tfstate"

# Verify backend
terraform show -json | jq '.terraform.backend'
```

## Variable Management

### Variable File Structure

Variables are defined in `terraform/terraform.prod.tfvars`:

```hcl
project_name           = "newfolder"
environment            = "production"
location               = "East US"
resource_group_name    = "rg-newfolder-prod"
vnet_address_space     = ["10.0.0.0/16"]
subnet_address_prefixes = ["10.0.1.0/24"]
app_service_sku        = "B2"
```

### Using Environment Variables

```bash
# Set variable via environment
export TF_VAR_location="West US"

# Terraform will use this value
terraform plan
```

### Sensitive Variables

For sensitive values, use a separate `.tfvars` file that is **NOT committed**:

```bash
# Create sensitive variables file
cat > terraform/secrets.tfvars <<EOF
sensitive_variable = "secret_value"
EOF

# Use it in plan/apply
terraform plan \
  -var-file="terraform.prod.tfvars" \
  -var-file="terraform/secrets.tfvars"
```

## Pipeline Configuration

### Azure DevOps Setup

1. **Create Service Connection:**
   - Azure DevOps Project → Project Settings → Service connections
   - Create "Azure Resource Manager" service connection
   - Use the Service Principal credentials from Step 2
   - Name it: `terraform-prod-sp`

2. **Create Variable Group:**
   - Pipelines → Library → Variable groups
   - Create group: `terraform-prod-secrets`
   - Add variables:
     ```
     AZURE_SUBSCRIPTION_ID: <your-subscription-id>
     AZURE_CLIENT_ID: <service-principal-app-id>
     AZURE_CLIENT_SECRET: <service-principal-password>
     AZURE_TENANT_ID: <tenant-id>
     ```
   - Mark `AZURE_CLIENT_SECRET` as secret

3. **Configure Pipeline:**
   - Push `.azure-pipelines/terraform-production.yml` to repository
   - Azure DevOps will auto-detect the pipeline
   - Configure required approvers for "Review" stage

### Pipeline Triggers

Pipeline automatically runs on:
- Commits to `main` branch
- Changes to `terraform/*` files
- Changes to `.azure-pipelines/terraform-production.yml`

## Deployment Process

### Manual Deployment (Local)

```bash
# 1. Create plan
cd terraform
terraform plan -var-file="terraform.prod.tfvars" -out=tfplan

# 2. Review plan output
terraform show tfplan

# 3. Apply if plan looks correct
terraform apply tfplan

# 4. Check outputs
terraform output
```

### Automated Deployment (CI/CD)

1. Push changes to `main` branch
2. Pipeline automatically triggers
3. Validate stage runs (format check, validation)
4. Plan stage generates and publishes plan
5. Review stage requires manual approval
6. Apply stage executes the plan
7. PostDeploy stage validates resources

## State Management

### Backup State

```bash
# Download state file
terraform state pull > backup_$(date +%Y%m%d_%H%M%S).tfstate

# Backup to cloud
az storage blob download \
  --account-name tfstateproduction \
  --container-name tfstate \
  --name prod.terraform.tfstate \
  --file prod.terraform.tfstate.backup
```

### Restore State

```bash
# ⚠️ Use with caution!

# Restore from backup
terraform state push backup_20240518_120000.tfstate

# Or restore from Azure Storage
az storage blob upload \
  --account-name tfstateproduction \
  --container-name tfstate \
  --name prod.terraform.tfstate \
  --file prod.terraform.tfstate.backup \
  --overwrite
```

### State Locking

State is automatically locked during `apply` operations. If a lock is stuck:

```bash
# View current locks
terraform force-unlock <lock-id>
```

## Troubleshooting

### Common Issues

#### "Error: Error building AzureRM Client"

**Cause**: Azure authentication failed

**Solution**:
```bash
az login
az account show
az account set --subscription "<SUBSCRIPTION_ID>"
```

#### "Error: Backend initialization required"

**Cause**: Backend not initialized

**Solution**:
```bash
terraform init \
  -backend-config="resource_group_name=rg-terraform-state" \
  -backend-config="storage_account_name=tfstateproduction" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=prod.terraform.tfstate"
```

#### "Error: resource already exists"

**Cause**: Resource exists outside of Terraform state

**Solution**:
```bash
# Option 1: Import existing resource
terraform import azurerm_resource_group.rg /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/rg-newfolder-prod

# Option 2: Delete resource and re-create
az group delete --name rg-newfolder-prod --yes
terraform apply
```

#### "Error: Error acquiring the state lock"

**Cause**: State is locked by another operation

**Solution**:
```bash
# Check for stale locks
terraform force-unlock <LOCK_ID>

# Or wait 10 minutes for lock to expire
```

### Debug Mode

Enable verbose logging:

```bash
# Set debug logging
export TF_LOG=DEBUG
export TF_LOG_PATH=terraform.log

# Run terraform command
terraform plan

# Review logs
cat terraform.log

# Disable logging
unset TF_LOG
unset TF_LOG_PATH
```

### Validation Scripts

Run post-deployment validation:

```bash
# Install validation dependencies
pip install -r scripts/requirements.txt

# Run validation
python scripts/validate_deployment.py \
  --resource-group "rg-newfolder-prod" \
  --location "East US" \
  --subscription-id "<SUBSCRIPTION_ID>"
```

## Security Best Practices

1. **Never commit secrets** to version control
2. **Rotate Service Principal credentials** regularly
3. **Use managed identities** for Azure resources
4. **Enable state encryption** (automatically done by Azure Storage)
5. **Implement RBAC** for access control
6. **Use approval gates** in CI/CD pipeline
7. **Enable audit logging** for state changes
8. **Keep Terraform updated** to latest version

## Support & Resources

- [Terraform Azure Documentation](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Azure DevOps Pipelines](https://learn.microsoft.com/en-us/azure/devops/pipelines)
- [Terraform Best Practices](https://developer.hashicorp.com/terraform/cloud-docs/recommended-practices)
- [Azure CLI Reference](https://learn.microsoft.com/en-us/cli/azure)

---

**Last Updated**: 2026-05-18  
**Terraform Version**: 1.6.0+  
**Provider Version**: azurerm ~> 3.85
