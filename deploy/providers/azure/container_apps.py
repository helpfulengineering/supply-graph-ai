"""
Azure Container Apps deployment implementation.

This module provides the Azure Container Apps deployer that implements BaseDeployer.
"""

import json
import logging
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from ...base.deployer import BaseDeployer
from .config import AzureDeploymentConfig

logger = logging.getLogger(__name__)


class DeploymentError(Exception):
    """Raised when deployment operations fail."""

    pass


class AzureContainerAppsDeployer(BaseDeployer):
    """Azure Container Apps deployer implementation."""

    def __init__(self, config: AzureDeploymentConfig):
        """
        Initialize Azure Container Apps deployer.

        Args:
            config: Azure deployment configuration
        """
        if not isinstance(config, AzureDeploymentConfig):
            raise ValueError(
                "AzureContainerAppsDeployer requires AzureDeploymentConfig"
            )
        super().__init__(config)
        self.config: AzureDeploymentConfig = config

        # Extract Azure-specific config
        self.resource_group = self.config.provider_config.get("resource_group")
        self.subscription_id = self.config.provider_config.get("subscription_id")
        self.container_app_name = self.config.provider_config.get(
            "container_app_name", self.config.service.name
        )
        self.container_app_env = self.config.provider_config.get("container_app_env")
        self.registry_server = self.config.provider_config.get("registry_server")
        self.registry_username = self.config.provider_config.get("registry_username")
        self.registry_password = self.config.provider_config.get("registry_password")

    def _run_az_command(
        self, command: List[str], check: bool = True, capture_output: bool = True
    ) -> Tuple[int, str, str]:
        """
        Run an Azure CLI command and return the result.

        Args:
            command: List of command arguments (e.g., ['az', 'containerapp', 'create', ...])
            check: If True, raise DeploymentError on non-zero exit code
            capture_output: If True, capture stdout and stderr

        Returns:
            Tuple of (exit_code, stdout, stderr)

        Raises:
            DeploymentError: If check=True and command fails
        """
        try:
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                check=False,
            )
            if check and result.returncode != 0:
                raise DeploymentError(
                    f"Azure CLI command failed with exit code {result.returncode}: {result.stderr}"
                )
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            raise DeploymentError("Azure CLI not found. Please install Azure CLI.")
        except Exception as e:
            raise DeploymentError(f"Error running Azure CLI command: {e}")

    def _convert_memory_to_gb(self, memory: str) -> float:
        """
        Convert memory string (e.g., '4Gi', '2Gi') to GB for Azure.

        Azure Container Apps use GB units.
        """
        memory = memory.upper().strip()
        if memory.endswith("GI"):
            return float(memory[:-2])
        elif memory.endswith("GB"):
            return float(memory[:-2])
        elif memory.endswith("MI"):
            return float(memory[:-2]) / 1024.0
        elif memory.endswith("MB"):
            return float(memory[:-2]) / 1000.0
        else:
            # Assume GB if no unit
            return float(memory)

    def _check_secret_exists(self, secret_name: str) -> bool:
        """Check if a secret exists in Azure Key Vault."""
        # Azure Container Apps can use Key Vault or environment variables
        # For simplicity, we'll check Key Vault if configured
        if "key_vault" not in self.config.provider_config:
            return False

        key_vault = self.config.provider_config["key_vault"]
        exit_code, _, _ = self._run_az_command(
            [
                "az",
                "keyvault",
                "secret",
                "show",
                "--vault-name",
                key_vault,
                "--name",
                secret_name,
                "--subscription",
                self.subscription_id,
            ],
            check=False,
        )
        return exit_code == 0

    def setup(self) -> None:
        """
        Setup Azure resources (resource group, container app environment, etc.).

        This creates the resource group and container app environment if they don't exist.
        """
        logger.info(
            f"Setting up Azure resources for resource group: {self.resource_group}"
        )

        # Set subscription
        self._run_az_command(
            ["az", "account", "set", "--subscription", self.subscription_id], check=True
        )

        # Check if resource group exists
        exit_code, _, _ = self._run_az_command(
            [
                "az",
                "group",
                "show",
                "--name",
                self.resource_group,
                "--subscription",
                self.subscription_id,
            ],
            check=False,
        )

        if exit_code != 0:
            # Resource group doesn't exist, create it
            logger.info(f"Creating resource group: {self.resource_group}")
            self._run_az_command(
                [
                    "az",
                    "group",
                    "create",
                    "--name",
                    self.resource_group,
                    "--location",
                    self.config.region,
                    "--subscription",
                    self.subscription_id,
                ],
                check=True,
            )
            logger.info(f"Created resource group: {self.resource_group}")
        else:
            logger.info(f"Resource group {self.resource_group} already exists")

        # Create container app environment if specified and doesn't exist
        if self.container_app_env:
            exit_code, _, _ = self._run_az_command(
                [
                    "az",
                    "containerapp",
                    "env",
                    "show",
                    "--name",
                    self.container_app_env,
                    "--resource-group",
                    self.resource_group,
                ],
                check=False,
            )

            if exit_code != 0:
                logger.info(
                    f"Creating container app environment: {self.container_app_env}"
                )
                self._run_az_command(
                    [
                        "az",
                        "containerapp",
                        "env",
                        "create",
                        "--name",
                        self.container_app_env,
                        "--resource-group",
                        self.resource_group,
                        "--location",
                        self.config.region,
                    ],
                    check=True,
                )
                logger.info(
                    f"Created container app environment: {self.container_app_env}"
                )

    def deploy(self) -> str:
        """
        Deploy service to Azure Container Apps and return service URL.

        Returns:
            Service URL

        Raises:
            DeploymentError: If deployment fails
        """
        logger.info(f"Deploying {self.config.service.name} to Azure Container Apps")

        # Setup resources
        self.setup()

        # Build environment variables
        env_vars = []
        for k, v in self.config.service.environment_vars.items():
            env_vars.append(f"{k}={v}")

        # Convert memory to GB
        memory_gb = self._convert_memory_to_gb(self.config.service.memory)

        # Build create/update command
        create_args = [
            "az",
            "containerapp",
            "create" if not self._check_service_exists() else "update",
            "--name",
            self.container_app_name,
            "--resource-group",
            self.resource_group,
            "--image",
            self.config.service.image,
            "--cpu",
            str(self.config.service.cpu),
            "--memory",
            f"{memory_gb}Gi",
            "--min-replicas",
            str(self.config.service.min_instances),
            "--max-replicas",
            str(self.config.service.max_instances),
            "--target-port",
            str(self.config.service.port),
            "--ingress",
            "external",
            "--env-vars",
            " ".join(env_vars),
        ]

        if self.container_app_env:
            create_args.extend(["--environment", self.container_app_env])

        if self.registry_server:
            create_args.extend(["--registry-server", self.registry_server])
            if self.registry_username and self.registry_password:
                create_args.extend(
                    [
                        "--registry-username",
                        self.registry_username,
                        "--registry-password",
                        self.registry_password,
                    ]
                )

        # Execute deployment
        logger.info(f"Executing: {' '.join(create_args)}")
        exit_code, stdout, stderr = self._run_az_command(create_args, check=False)

        if exit_code != 0:
            error_msg = f"Deployment failed with exit code {exit_code}"
            if stderr:
                error_msg += f": {stderr}"
            logger.error(error_msg)
            raise DeploymentError(error_msg)

        # Get service URL
        service_url = self.get_service_url()
        logger.info(f"Deployment successful. Service URL: {service_url}")
        return service_url

    def get_service_url(self, service_name: Optional[str] = None) -> str:
        """
        Get the deployed service URL.

        Args:
            service_name: Optional service name (defaults to config.service.name)

        Returns:
            Service URL

        Raises:
            DeploymentError: If service not found
        """
        name = service_name or self.container_app_name
        exit_code, stdout, stderr = self._run_az_command(
            [
                "az",
                "containerapp",
                "show",
                "--name",
                name,
                "--resource-group",
                self.resource_group,
                "--query",
                "properties.configuration.ingress.fqdn",
                "--output",
                "tsv",
            ],
            check=False,
        )

        if exit_code != 0:
            raise DeploymentError(f"Service {name} not found: {stderr}")

        fqdn = stdout.strip()
        if not fqdn:
            raise DeploymentError(f"Service {name} exists but has no FQDN")
        return f"https://{fqdn}"

    def update(self) -> str:
        """
        Update existing deployment.

        Returns:
            Service URL

        Raises:
            DeploymentError: If update fails
        """
        # For Container Apps, update is the same as deploy
        return self.deploy()

    def delete(self, service_name: Optional[str] = None) -> None:
        """
        Delete deployment.

        Args:
            service_name: Optional service name (defaults to config.service.name)

        Raises:
            DeploymentError: If deletion fails
        """
        name = service_name or self.container_app_name
        logger.info(f"Deleting Azure Container App: {name}")

        self._run_az_command(
            [
                "az",
                "containerapp",
                "delete",
                "--name",
                name,
                "--resource-group",
                self.resource_group,
                "--yes",
            ],
            check=True,
        )

        logger.info(f"Container App {name} deleted successfully")

    def get_status(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get deployment status.

        Args:
            service_name: Optional service name (defaults to config.service.name)

        Returns:
            Dictionary with status information

        Raises:
            DeploymentError: If status check fails
        """
        name = service_name or self.container_app_name
        exit_code, stdout, stderr = self._run_az_command(
            [
                "az",
                "containerapp",
                "show",
                "--name",
                name,
                "--resource-group",
                self.resource_group,
                "--output",
                "json",
            ],
            check=False,
        )

        if exit_code != 0:
            return {
                "exists": False,
                "status": "not_found",
                "error": stderr,
            }

        try:
            app_data = json.loads(stdout)
            return {
                "exists": True,
                "status": app_data.get("properties", {}).get(
                    "provisioningState", "unknown"
                ),
                "url": self.get_service_url(name),
                "replicas": app_data.get("properties", {})
                .get("template", {})
                .get("scale", {})
                .get("minReplicas", 0),
            }
        except json.JSONDecodeError:
            return {
                "exists": True,
                "status": "unknown",
                "raw_output": stdout,
            }
