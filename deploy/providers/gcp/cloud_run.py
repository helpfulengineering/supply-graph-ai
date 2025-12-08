"""
GCP Cloud Run deployment implementation.

This module provides the GCP Cloud Run deployer that implements BaseDeployer.
"""

import subprocess
import logging
import re
import json
import secrets
import base64
from typing import Dict, Any, Optional, List, Tuple

from ...base.deployer import BaseDeployer
from .config import GCPDeploymentConfig

logger = logging.getLogger(__name__)


class DeploymentError(Exception):
    """Raised when deployment operations fail."""

    pass


class GCPCloudRunDeployer(BaseDeployer):
    """GCP Cloud Run deployer implementation."""

    def __init__(self, config: GCPDeploymentConfig):
        """
        Initialize GCP Cloud Run deployer.

        Args:
            config: GCP deployment configuration
        """
        if not isinstance(config, GCPDeploymentConfig):
            raise ValueError("GCPCloudRunDeployer requires GCPDeploymentConfig")
        super().__init__(config)
        self.config: GCPDeploymentConfig = config
        self.project_id = self.config.provider_config.get("project_id")
        if not self.project_id:
            raise ValueError("GCP deployment requires project_id in provider_config")

    def _run_gcloud_command(
        self, command: List[str], check: bool = True, capture_output: bool = True
    ) -> Tuple[int, str, str]:
        """
        Run a gcloud command and return the result.

        Args:
            command: List of command arguments (e.g., ['gcloud', 'run', 'deploy', ...])
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
                    f"gcloud command failed with exit code {result.returncode}: {result.stderr}"
                )
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            raise DeploymentError("gcloud CLI not found. Please install Google Cloud SDK.")
        except Exception as e:
            raise DeploymentError(f"Error running gcloud command: {e}")

    def _check_secret_exists(self, secret_name: str) -> bool:
        """Check if a secret exists in Secret Manager."""
        exit_code, _, _ = self._run_gcloud_command(
            [
                "gcloud",
                "secrets",
                "describe",
                secret_name,
                "--project",
                self.project_id,
            ],
            check=False,
        )
        return exit_code == 0

    def _get_service_secrets(self) -> Dict[str, str]:
        """Get currently configured secrets from the Cloud Run service."""
        exit_code, stdout, _ = self._run_gcloud_command(
            [
                "gcloud",
                "run",
                "services",
                "describe",
                self.config.service.name,
                "--region",
                self.config.region,
                "--format",
                "yaml(spec.template.spec.containers[0].env)",
            ],
            check=False,
        )

        if exit_code != 0:
            return {}

        # Parse secrets from YAML output
        secrets_dict = {}
        # This is a simplified parser - in production you might want to use PyYAML
        for line in stdout.split("\n"):
            if "secretKeyRef" in line:
                # Extract secret name from YAML
                # This is a basic implementation - could be improved
                pass
        return secrets_dict

    def _generate_secure_random_value(self, length: int = 32) -> str:
        """Generate a secure random value (base64 encoded)."""
        random_bytes = secrets.token_bytes(length)
        return base64.b64encode(random_bytes).decode("utf-8")

    def _build_env_vars_string(self) -> str:
        """Build environment variables string for gcloud command."""
        env_vars = self.config.service.environment_vars.copy()

        # Add default environment variables if not present
        if "ENVIRONMENT" not in env_vars:
            env_vars["ENVIRONMENT"] = self.config.environment

        # Convert to comma-separated string format: KEY1=value1,KEY2=value2
        return ",".join(f"{k}={v}" for k, v in env_vars.items())

    def _build_secrets_list(self) -> Tuple[str, Dict[str, str]]:
        """
        Build secrets list and handle missing secrets.

        Returns:
            Tuple of (secrets_list_string, generated_env_vars_dict)
            secrets_list_string: Comma-separated secrets for --update-secrets
            generated_env_vars_dict: Environment variables for secrets that don't exist
        """
        secrets_list = []
        generated_env_vars = {}

        # Check each secret in config
        for env_var_name, secret_ref in self.config.service.secrets.items():
            # Parse secret reference (format: "secret-name:version" or just "secret-name")
            if ":" in secret_ref:
                secret_name, _ = secret_ref.split(":", 1)
            else:
                secret_name = secret_ref

            if self._check_secret_exists(secret_name):
                secrets_list.append(f"{env_var_name}={secret_ref}")
                logger.info(f"Found secret '{secret_name}', including in deployment")
            else:
                logger.warning(f"Secret '{secret_name}' not found, will generate secure value")
                # Generate secure random value for missing secrets
                if "salt" in secret_name.lower():
                    generated_env_vars[env_var_name] = self._generate_secure_random_value(32)
                elif "password" in secret_name.lower():
                    generated_env_vars[env_var_name] = self._generate_secure_random_value(32)
                else:
                    generated_env_vars[env_var_name] = self._generate_secure_random_value(32)

        secrets_list_str = ",".join(secrets_list) if secrets_list else ""
        return secrets_list_str, generated_env_vars

    def _check_service_exists(self) -> bool:
        """Check if the Cloud Run service exists."""
        exit_code, _, _ = self._run_gcloud_command(
            [
                "gcloud",
                "run",
                "services",
                "describe",
                self.config.service.name,
                "--region",
                self.config.region,
                "--project",
                self.project_id,
            ],
            check=False,
        )
        return exit_code == 0

    def _verify_image_exists(self, image: str) -> bool:
        """Verify that the Docker image exists in Artifact Registry."""
        exit_code, _, _ = self._run_gcloud_command(
            ["gcloud", "artifacts", "docker", "images", "describe", image],
            check=False,
        )
        return exit_code == 0

    def _extract_service_url(self, deploy_output: str) -> Optional[str]:
        """Extract service URL from gcloud deploy output."""
        # Look for "Service URL: https://..."
        match = re.search(r"Service URL:\s*(https://[^\s]+)", deploy_output)
        if match:
            return match.group(1)
        return None

    def setup(self) -> None:
        """
        Setup GCP resources (IAM, storage, etc.).

        This is a no-op for Cloud Run as resources are created on-demand.
        For more complex setups, this could create IAM bindings, etc.
        """
        logger.info("GCP Cloud Run setup: No pre-deployment setup required")
        # Could add IAM setup, service account creation, etc. here if needed
        pass

    def deploy(self) -> str:
        """
        Deploy service to Cloud Run and return service URL.

        Returns:
            Service URL

        Raises:
            DeploymentError: If deployment fails
        """
        logger.info(f"Deploying {self.config.service.name} to GCP Cloud Run")

        # Verify image exists
        image = self.config.service.image
        if not self._verify_image_exists(image):
            logger.warning(f"Image {image} not found, trying 'latest' tag")
            # Try with latest tag
            image_latest = f"{image.rsplit(':', 1)[0]}:latest"
            if self._verify_image_exists(image_latest):
                logger.info(f"Using image with 'latest' tag: {image_latest}")
                image = image_latest
            else:
                raise DeploymentError(f"Image {image} not found in Artifact Registry")

        # Build secrets list and handle missing secrets
        secrets_list, generated_env_vars = self._build_secrets_list()

        # Merge generated env vars with existing ones
        env_vars = self.config.service.environment_vars.copy()
        env_vars.update(generated_env_vars)

        # Build environment variables string
        env_vars_str = self._build_env_vars_string()
        if generated_env_vars:
            # Add generated env vars to the string
            generated_str = ",".join(f"{k}={v}" for k, v in generated_env_vars.items())
            env_vars_str = f"{env_vars_str},{generated_str}" if env_vars_str else generated_str

        # Check if service has invalid secrets configured
        service_has_invalid_secrets = False
        if self._check_service_exists():
            # Check if service has secrets that don't exist
            current_secrets = self._get_service_secrets()
            for env_var_name, secret_ref in self.config.service.secrets.items():
                if ":" in secret_ref:
                    secret_name, _ = secret_ref.split(":", 1)
                else:
                    secret_name = secret_ref
                if env_var_name in current_secrets and not self._check_secret_exists(secret_name):
                    service_has_invalid_secrets = True
                    break

        # Determine authentication setting
        allow_unauthenticated = self.config.provider_config.get(
            "allow_unauthenticated", False
        )

        # Build deployment command
        deploy_args = [
            "gcloud",
            "run",
            "deploy",
            self.config.service.name,
            "--image",
            image,
            "--service-account",
            self.config.provider_config.get(
                "service_account",
                f"supply-graph-ai@{self.project_id}.iam.gserviceaccount.com",
            ),
            "--region",
            self.config.region,
            "--platform",
            "managed",
            "--set-env-vars",
            env_vars_str,
            "--memory",
            self.config.service.memory,
            "--cpu",
            str(self.config.service.cpu),
            "--timeout",
            str(self.config.service.timeout),
            "--max-instances",
            str(self.config.service.max_instances),
            "--min-instances",
            str(self.config.service.min_instances),
        ]

        # Add authentication flag
        if allow_unauthenticated:
            deploy_args.append("--allow-unauthenticated")
        else:
            deploy_args.append("--no-allow-unauthenticated")

        # Add secrets
        if secrets_list:
            deploy_args.extend(["--update-secrets", secrets_list])
        elif service_has_invalid_secrets:
            deploy_args.append("--clear-secrets")

        # Execute deployment
        logger.info(f"Executing: {' '.join(deploy_args)}")
        exit_code, stdout, stderr = self._run_gcloud_command(deploy_args, check=False)

        if exit_code != 0:
            error_msg = f"Deployment failed with exit code {exit_code}"
            if stderr:
                error_msg += f": {stderr}"
            logger.error(error_msg)
            raise DeploymentError(error_msg)

        # Extract service URL
        service_url = self._extract_service_url(stdout)
        if not service_url:
            # Try to get URL from service describe
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
        name = service_name or self.config.service.name
        exit_code, stdout, stderr = self._run_gcloud_command(
            [
                "gcloud",
                "run",
                "services",
                "describe",
                name,
                "--region",
                self.config.region,
                "--project",
                self.project_id,
                "--format",
                "value(status.url)",
            ],
            check=False,
        )

        if exit_code != 0:
            raise DeploymentError(f"Service {name} not found: {stderr}")

        url = stdout.strip()
        if not url:
            raise DeploymentError(f"Service {name} exists but has no URL")
        return url

    def update(self) -> str:
        """
        Update existing deployment.

        Returns:
            Service URL

        Raises:
            DeploymentError: If update fails
        """
        # For Cloud Run, update is the same as deploy
        return self.deploy()

    def delete(self, service_name: Optional[str] = None) -> None:
        """
        Delete deployment.

        Args:
            service_name: Optional service name (defaults to config.service.name)

        Raises:
            DeploymentError: If deletion fails
        """
        name = service_name or self.config.service.name
        logger.info(f"Deleting Cloud Run service: {name}")

        self._run_gcloud_command(
            [
                "gcloud",
                "run",
                "services",
                "delete",
                name,
                "--region",
                self.config.region,
                "--project",
                self.project_id,
                "--quiet",
            ],
            check=True,
        )

        logger.info(f"Service {name} deleted successfully")

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
        name = service_name or self.config.service.name
        exit_code, stdout, stderr = self._run_gcloud_command(
            [
                "gcloud",
                "run",
                "services",
                "describe",
                name,
                "--region",
                self.config.region,
                "--project",
                self.project_id,
                "--format",
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

        # Parse JSON output
        try:
            service_data = json.loads(stdout)
            return {
                "exists": True,
                "status": "running",
                "url": service_data.get("status", {}).get("url"),
                "latest_ready_revision": service_data.get("status", {}).get(
                    "latestReadyRevisionName"
                ),
                "traffic": service_data.get("status", {}).get("traffic", []),
            }
        except json.JSONDecodeError:
            return {
                "exists": True,
                "status": "unknown",
                "raw_output": stdout,
            }

