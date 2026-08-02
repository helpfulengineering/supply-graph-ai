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

    def fetch_redis_access_key(self, resource_name: str) -> str:
        """Primary access key for an Azure Cache for Redis in this deployer's RG.

        Raises:
            DeploymentError: if the key cannot be read. Failing loudly is the
                point — a deploy that silently skipped this would write no
                secret, and the app would fail later as an unrelated-looking
                connection error.
        """
        exit_code, stdout, stderr = self._run_az_command(
            [
                "az",
                "redis",
                "list-keys",
                "--name",
                resource_name,
                "--resource-group",
                self.resource_group,
                "--subscription",
                self.subscription_id,
                "--query",
                "primaryKey",
                "--output",
                "tsv",
            ],
            check=False,
        )
        if exit_code != 0 or not stdout.strip():
            raise DeploymentError(
                f"Could not read the access key for Redis {resource_name!r} in "
                f"{self.resource_group!r}: {stderr.strip() or 'empty key returned'}"
            )
        return stdout.strip()

    def set_secrets(self, secrets: Dict[str, str]) -> None:
        """Set Container App secrets, logging their NAMES only, never values.

        Secrets must exist before any env var references them via
        ``secretref:``, so callers set them ahead of the app update.
        """
        if not secrets:
            return

        command = [
            "az",
            "containerapp",
            "secret",
            "set",
            "--name",
            self.container_app_name,
            "--resource-group",
            self.resource_group,
            "--secrets",
        ]
        command.extend(f"{name}={value}" for name, value in secrets.items())

        # NB: deliberately not logging `command` — it carries secret values.
        logger.info(
            "Setting %d container app secret(s) on %s: %s",
            len(secrets),
            self.container_app_name,
            ", ".join(sorted(secrets)),
        )
        exit_code, _, stderr = self._run_az_command(command, check=False)
        if exit_code != 0:
            raise DeploymentError(
                f"Failed to set secrets ({', '.join(sorted(secrets))}) on "
                f"{self.container_app_name}: {stderr}"
            )

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

    def _check_service_exists(self) -> bool:
        """Check if the Container App already exists."""
        exit_code, _, _ = self._run_az_command(
            [
                "az",
                "containerapp",
                "show",
                "--name",
                self.container_app_name,
                "--resource-group",
                self.resource_group,
            ],
            check=False,
        )
        return exit_code == 0

    def deploy(self) -> str:
        """
        Deploy service to Azure Container Apps and return service URL.

        ``az containerapp create`` and ``az containerapp update`` accept different
        flag sets (confirmed against the installed CLI's ``--help`` output, not
        assumed): ``--target-port``, ``--ingress``, ``--environment``, and
        ``--registry-*`` are create-only — passing them to ``update`` is a CLI
        argument error. ``--command`` / ``--args`` exist on BOTH. Env vars also
        differ: ``create`` takes ``--env-vars`` (full list, nothing to preserve
        yet); ``update`` has no ``--env-vars`` flag at all and instead takes
        ``--set-env-vars`` (adds/updates listed vars, leaves any other existing
        container env vars — e.g. ones set directly via ``az`` outside this
        deployer — untouched).

        With ``service.ingress_enabled`` False the app serves no HTTP: the
        create-only ingress flags are omitted (no ``--ingress`` means Azure
        creates the app with ingress disabled) and no URL lookup is attempted,
        because an app without ingress has no FQDN to look up.

        Returns:
            Service URL, or an empty string for an ingress-less app

        Raises:
            DeploymentError: If deployment fails
        """
        logger.info(f"Deploying {self.config.service.name} to Azure Container Apps")

        # Setup resources
        self.setup()

        # Build environment variables as separate "K=V" tokens (NOT a single
        # space-joined string — az's --env-vars/--set-env-vars take nargs='*',
        # so each KEY=VALUE pair must be its own argv element).
        env_vars = [f"{k}={v}" for k, v in self.config.service.environment_vars.items()]

        # Convert memory to GB
        memory_gb = self._convert_memory_to_gb(self.config.service.memory)

        is_update = self._check_service_exists()

        deploy_args = [
            "az",
            "containerapp",
            "update" if is_update else "create",
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
        ]

        # --command / --args take nargs='*', so each element is its own argv
        # token (same rule as env vars above).
        if self.config.service.command:
            deploy_args.append("--command")
            deploy_args.extend(self.config.service.command)
        if self.config.service.args:
            deploy_args.append("--args")
            deploy_args.extend(self.config.service.args)

        if is_update:
            if env_vars:
                deploy_args.append("--set-env-vars")
                deploy_args.extend(env_vars)
        else:
            if self.config.service.ingress_enabled:
                deploy_args.extend(
                    [
                        "--target-port",
                        str(self.config.service.port),
                        "--ingress",
                        "external",
                    ]
                )
            if env_vars:
                deploy_args.append("--env-vars")
                deploy_args.extend(env_vars)
            if self.container_app_env:
                deploy_args.extend(["--environment", self.container_app_env])
            if self.registry_server:
                deploy_args.extend(["--registry-server", self.registry_server])
                if self.registry_username and self.registry_password:
                    deploy_args.extend(
                        [
                            "--registry-username",
                            self.registry_username,
                            "--registry-password",
                            self.registry_password,
                        ]
                    )

        # Execute deployment
        logger.info(f"Executing: {' '.join(deploy_args)}")
        exit_code, stdout, stderr = self._run_az_command(deploy_args, check=False)

        if exit_code != 0:
            error_msg = f"Deployment failed with exit code {exit_code}"
            if stderr:
                error_msg += f": {stderr}"
            logger.error(error_msg)
            raise DeploymentError(error_msg)

        # An ingress-less app (e.g. a queue worker) has no FQDN, so looking one
        # up would fail a deployment that in fact succeeded.
        if not self.config.service.ingress_enabled:
            logger.info(
                "Deployment successful. %s has no ingress; no service URL.",
                self.container_app_name,
            )
            return ""

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

    @staticmethod
    def _fqdn_from_app_data(app_data: Dict[str, Any]) -> str:
        """Ingress FQDN as an https URL, or "" when the app has no ingress."""
        ingress = (
            app_data.get("properties", {}).get("configuration", {}).get("ingress") or {}
        )
        fqdn = ingress.get("fqdn") or ""
        return f"https://{fqdn}" if fqdn else ""

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
                # Read the FQDN out of the response we already have rather than
                # calling get_service_url(), which raises when an app has no
                # ingress — a worker's status is not an error.
                "url": self._fqdn_from_app_data(app_data),
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
