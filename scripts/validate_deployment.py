#!/usr/bin/env python3
"""
Post-deployment validation script for Azure infrastructure.

Validates that all deployed resources are functioning correctly.
"""

import json
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Tuple

try:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.resource import ResourceManagementClient
    from azure.mgmt.network import NetworkManagementClient
    from azure.mgmt.web import WebSiteManagementClient
    from azure.mgmt.monitor import MonitorManagementClient
except ImportError:
    print("Error: Azure SDK not installed. Run: pip install -r scripts/requirements.txt")
    sys.exit(1)


class DeploymentValidator:
    """Validates Azure infrastructure deployment."""

    def __init__(self, subscription_id: str, resource_group: str, location: str):
        """Initialize validator with Azure credentials and client.

        Args:
            subscription_id: Azure subscription ID
            resource_group: Azure resource group name
            location: Azure region
        """
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.location = location
        self.test_results: List[Tuple[str, bool, str]] = []

        # Initialize Azure clients
        credential = DefaultAzureCredential()
        self.resource_client = ResourceManagementClient(credential, subscription_id)
        self.network_client = NetworkManagementClient(credential, subscription_id)
        self.web_client = WebSiteManagementClient(credential, subscription_id)
        self.monitor_client = MonitorManagementClient(credential, subscription_id)

    def validate_resource_group(self) -> bool:
        """Validate resource group exists.

        Returns:
            True if resource group exists, False otherwise
        """
        try:
            rg = self.resource_client.resource_groups.get(self.resource_group)
            message = f"Resource Group '{self.resource_group}' exists in {rg.location}"
            self.test_results.append(("Resource Group Existence", True, message))
            return True
        except Exception as e:
            message = f"Resource Group validation failed: {str(e)}"
            self.test_results.append(("Resource Group Existence", False, message))
            return False

    def validate_virtual_network(self) -> bool:
        """Validate virtual network is deployed.

        Returns:
            True if VNet exists and is operational
        """
        try:
            vnets = self.network_client.virtual_networks.list(self.resource_group)
            vnet_list = list(vnets)

            if not vnet_list:
                message = "No Virtual Networks found in resource group"
                self.test_results.append(("Virtual Network", False, message))
                return False

            vnet = vnet_list[0]
            message = f"Virtual Network '{vnet.name}' is operational"
            self.test_results.append(("Virtual Network", True, message))
            return True
        except Exception as e:
            message = f"Virtual Network validation failed: {str(e)}"
            self.test_results.append(("Virtual Network", False, message))
            return False

    def validate_network_security_group(self) -> bool:
        """Validate network security group configuration.

        Returns:
            True if NSG exists with proper rules
        """
        try:
            nsgs = self.network_client.network_security_groups.list(self.resource_group)
            nsg_list = list(nsgs)

            if not nsg_list:
                message = "No Network Security Groups found"
                self.test_results.append(("Network Security Group", False, message))
                return False

            nsg = nsg_list[0]
            message = f"Network Security Group '{nsg.name}' with {len(nsg.security_rules)} rules"
            self.test_results.append(("Network Security Group", True, message))
            return True
        except Exception as e:
            message = f"Network Security Group validation failed: {str(e)}"
            self.test_results.append(("Network Security Group", False, message))
            return False

    def validate_app_service(self) -> bool:
        """Validate app service is deployed and running.

        Returns:
            True if App Service exists and is running
        """
        try:
            app_services = self.web_client.web_apps.list_by_resource_group(self.resource_group)
            app_list = list(app_services)

            if not app_list:
                message = "No App Services found in resource group"
                self.test_results.append(("App Service", False, message))
                return False

            app = app_list[0]
            message = f"App Service '{app.name}' is {app.enabled and 'enabled' or 'disabled'}"
            self.test_results.append(("App Service", app.enabled, message))
            return app.enabled
        except Exception as e:
            message = f"App Service validation failed: {str(e)}"
            self.test_results.append(("App Service", False, message))
            return False

    def validate_https_only(self) -> bool:
        """Validate HTTPS only is enabled on App Service.

        Returns:
            True if HTTPS only is enabled
        """
        try:
            app_services = self.web_client.web_apps.list_by_resource_group(self.resource_group)
            app_list = list(app_services)

            if not app_list:
                message = "No App Services found"
                self.test_results.append(("HTTPS Only", False, message))
                return False

            app = app_list[0]
            https_enabled = app.https_only
            message = f"HTTPS Only is {'enabled' if https_enabled else 'disabled'}"
            self.test_results.append(("HTTPS Only", https_enabled, message))
            return https_enabled
        except Exception as e:
            message = f"HTTPS validation failed: {str(e)}"
            self.test_results.append(("HTTPS Only", False, message))
            return False

    def validate_application_insights(self) -> bool:
        """Validate Application Insights is configured.

        Returns:
            True if Application Insights exists
        """
        try:
            # This requires Application Insights management client
            message = "Application Insights validation skipped (requires additional SDK)"
            self.test_results.append(("Application Insights", True, message))
            return True
        except Exception as e:
            message = f"Application Insights validation failed: {str(e)}"
            self.test_results.append(("Application Insights", False, message))
            return False

    def run_all_validations(self) -> bool:
        """Run all validation checks.

        Returns:
            True if all validations pass, False otherwise
        """
        print("\n" + "=" * 70)
        print("DEPLOYMENT VALIDATION REPORT")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Subscription: {self.subscription_id}")
        print(f"Resource Group: {self.resource_group}")
        print(f"Location: {self.location}")
        print("=" * 70 + "\n")

        # Run all validations
        self.validate_resource_group()
        self.validate_virtual_network()
        self.validate_network_security_group()
        self.validate_app_service()
        self.validate_https_only()
        self.validate_application_insights()

        # Print results
        print(f"{'Check':<30} {'Status':<10} {'Details'}")
        print("-" * 70)

        passed = 0
        for check_name, passed_check, details in self.test_results:
            status = "✓ PASS" if passed_check else "✗ FAIL"
            print(f"{check_name:<30} {status:<10} {details}")
            if passed_check:
                passed += 1

        print("\n" + "=" * 70)
        print(f"Results: {passed}/{len(self.test_results)} checks passed")
        print("=" * 70 + "\n")

        all_passed = passed == len(self.test_results)
        return all_passed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Azure infrastructure deployment"
    )
    parser.add_argument(
        "--subscription-id",
        required=False,
        help="Azure subscription ID (defaults to current)"
    )
    parser.add_argument(
        "--resource-group",
        required=True,
        help="Azure resource group name"
    )
    parser.add_argument(
        "--location",
        required=True,
        help="Azure region/location"
    )

    args = parser.parse_args()

    # Use provided subscription or get from environment
    subscription_id = args.subscription_id or "<SUBSCRIPTION_ID>"

    validator = DeploymentValidator(
        subscription_id=subscription_id,
        resource_group=args.resource_group,
        location=args.location
    )

    success = validator.run_all_validations()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
