"""
AWS ECS Fargate deployment implementation.

This module provides the AWS ECS Fargate deployer that implements BaseDeployer.
"""

import subprocess
import logging
import json
from typing import Dict, Any, Optional, List, Tuple

from ...base.deployer import BaseDeployer
from .config import AWSDeploymentConfig

logger = logging.getLogger(__name__)


class DeploymentError(Exception):
    """Raised when deployment operations fail."""

    pass


class AWSFargateDeployer(BaseDeployer):
    """AWS ECS Fargate deployer implementation."""

    def __init__(self, config: AWSDeploymentConfig):
        """
        Initialize AWS Fargate deployer.

        Args:
            config: AWS deployment configuration
        """
        if not isinstance(config, AWSDeploymentConfig):
            raise ValueError("AWSFargateDeployer requires AWSDeploymentConfig")
        super().__init__(config)
        self.config: AWSDeploymentConfig = config

        # Extract AWS-specific config
        self.cluster = self.config.provider_config.get("cluster", "default")
        self.task_definition_family = self.config.provider_config.get(
            "task_definition", self.config.service.name
        )
        self.ecr_repository = self.config.provider_config.get("ecr_repository")
        self.execution_role_arn = self.config.provider_config.get("execution_role_arn")
        self.task_role_arn = self.config.provider_config.get("task_role_arn")
        self.subnets = self.config.provider_config.get("subnets", [])
        self.security_groups = self.config.provider_config.get("security_groups", [])
        self.assign_public_ip = self.config.provider_config.get("assign_public_ip", "ENABLED")

    def _run_aws_command(
        self, command: List[str], check: bool = True, capture_output: bool = True
    ) -> Tuple[int, str, str]:
        """
        Run an AWS CLI command and return the result.

        Args:
            command: List of command arguments (e.g., ['aws', 'ecs', 'describe-service', ...])
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
                    f"AWS CLI command failed with exit code {result.returncode}: {result.stderr}"
                )
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            raise DeploymentError("AWS CLI not found. Please install AWS CLI.")
        except Exception as e:
            raise DeploymentError(f"Error running AWS CLI command: {e}")

    def _convert_memory_to_mb(self, memory: str) -> int:
        """
        Convert memory string (e.g., '4Gi', '2Gi') to MB for AWS.

        AWS Fargate uses MB units.
        """
        memory = memory.upper().strip()
        if memory.endswith("GI"):
            return int(float(memory[:-2]) * 1024)
        elif memory.endswith("GB"):
            return int(float(memory[:-2]) * 1000)
        elif memory.endswith("MI"):
            return int(float(memory[:-2]))
        elif memory.endswith("MB"):
            return int(float(memory[:-2]))
        else:
            # Assume MB if no unit
            return int(memory)

    def _convert_cpu_to_units(self, cpu: int) -> str:
        """
        Convert CPU count to AWS Fargate CPU units.

        AWS Fargate CPU units: 256 (.25 vCPU), 512 (.5 vCPU), 1024 (1 vCPU), 2048 (2 vCPU), etc.
        """
        # AWS Fargate CPU units are in 256 increments
        cpu_units = cpu * 1024
        # Validate against AWS limits (256-4096 for Fargate)
        if cpu_units < 256:
            cpu_units = 256
        elif cpu_units > 4096:
            cpu_units = 4096
        return str(cpu_units)

    def _check_secret_exists(self, secret_name: str) -> bool:
        """Check if a secret exists in AWS Secrets Manager."""
        exit_code, _, _ = self._run_aws_command(
            [
                "aws",
                "secretsmanager",
                "describe-secret",
                "--secret-id",
                secret_name,
                "--region",
                self.config.region,
            ],
            check=False,
        )
        return exit_code == 0

    def _build_task_definition(self, image: str) -> Dict[str, Any]:
        """Build ECS task definition JSON."""
        # Convert memory and CPU
        memory_mb = self._convert_memory_to_mb(self.config.service.memory)
        cpu_units = self._convert_cpu_to_units(self.config.service.cpu)

        # Build environment variables
        environment = [
            {"name": k, "value": v} for k, v in self.config.service.environment_vars.items()
        ]

        # Build secrets (from AWS Secrets Manager)
        secrets = []
        for env_var_name, secret_ref in self.config.service.secrets.items():
            # AWS Secrets Manager format: "arn:aws:secretsmanager:region:account:secret:name"
            # Or just the secret name (we'll construct ARN if needed)
            if secret_ref.startswith("arn:aws:secretsmanager:"):
                secret_arn = secret_ref
            else:
                # Assume it's a secret name - we'd need account ID to build full ARN
                # For now, use the secret name and let AWS resolve it
                secret_arn = secret_ref

            secrets.append(
                {
                    "name": env_var_name,
                    "valueFrom": secret_arn,
                }
            )

        # Build container definition
        container_def = {
            "name": self.config.service.name,
            "image": image,
            "portMappings": [
                {
                    "containerPort": self.config.service.port,
                    "protocol": "tcp",
                }
            ],
            "environment": environment,
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": f"/ecs/{self.config.service.name}",
                    "awslogs-region": self.config.region,
                    "awslogs-stream-prefix": "ecs",
                },
            },
        }

        if secrets:
            container_def["secrets"] = secrets

        # Build task definition
        task_def = {
            "family": self.task_definition_family,
            "networkMode": "awsvpc",
            "requiresCompatibilities": ["FARGATE"],
            "cpu": cpu_units,
            "memory": str(memory_mb),
            "containerDefinitions": [container_def],
        }

        if self.execution_role_arn:
            task_def["executionRoleArn"] = self.execution_role_arn
        if self.task_role_arn:
            task_def["taskRoleArn"] = self.task_role_arn

        return task_def

    def _register_task_definition(self, task_def: Dict[str, Any]) -> str:
        """Register task definition and return task definition ARN."""
        # Write task definition to temp file
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(task_def, f, indent=2)
            temp_file = f.name

        try:
            exit_code, stdout, stderr = self._run_aws_command(
                [
                    "aws",
                    "ecs",
                    "register-task-definition",
                    "--cli-input-json",
                    f"file://{temp_file}",
                    "--region",
                    self.config.region,
                ],
                check=True,
            )

            # Parse task definition ARN from output
            result = json.loads(stdout)
            task_def_arn = result["taskDefinition"]["taskDefinitionArn"]
            logger.info(f"Registered task definition: {task_def_arn}")
            return task_def_arn
        finally:
            os.unlink(temp_file)

    def _check_service_exists(self) -> bool:
        """Check if the ECS service exists."""
        exit_code, _, _ = self._run_aws_command(
            [
                "aws",
                "ecs",
                "describe-services",
                "--cluster",
                self.cluster,
                "--services",
                self.config.service.name,
                "--region",
                self.config.region,
            ],
            check=False,
        )
        return exit_code == 0

    def _verify_image_exists(self, image: str) -> bool:
        """Verify that the Docker image exists in ECR."""
        # Extract repository name from image
        # Format: ACCOUNT.dkr.ecr.REGION.amazonaws.com/REPO:TAG
        if "amazonaws.com" not in image:
            # Not an ECR image, skip verification
            return True

        try:
            # Try to describe the image
            repo_name = image.split("/")[-1].split(":")[0]
            tag = image.split(":")[-1] if ":" in image else "latest"

            exit_code, _, _ = self._run_aws_command(
                [
                    "aws",
                    "ecr",
                    "describe-images",
                    "--repository-name",
                    repo_name,
                    "--image-ids",
                    f"imageTag={tag}",
                    "--region",
                    self.config.region,
                ],
                check=False,
            )
            return exit_code == 0
        except Exception:
            # If we can't verify, assume it exists
            return True

    def setup(self) -> None:
        """
        Setup AWS resources (ECS cluster, IAM roles, etc.).

        This creates the ECS cluster if it doesn't exist.
        """
        logger.info(f"Setting up AWS resources for cluster: {self.cluster}")

        # Check if cluster exists
        exit_code, stdout, _ = self._run_aws_command(
            [
                "aws",
                "ecs",
                "describe-clusters",
                "--clusters",
                self.cluster,
                "--region",
                self.config.region,
            ],
            check=False,
        )

        if exit_code != 0:
            # Cluster doesn't exist, create it
            logger.info(f"Creating ECS cluster: {self.cluster}")
            self._run_aws_command(
                [
                    "aws",
                    "ecs",
                    "create-cluster",
                    "--cluster-name",
                    self.cluster,
                    "--region",
                    self.config.region,
                ],
                check=True,
            )
            logger.info(f"Created ECS cluster: {self.cluster}")
        else:
            logger.info(f"ECS cluster {self.cluster} already exists")

        # Create CloudWatch log group if it doesn't exist
        log_group = f"/ecs/{self.config.service.name}"
        exit_code, _, _ = self._run_aws_command(
            [
                "aws",
                "logs",
                "describe-log-groups",
                "--log-group-name-prefix",
                log_group,
                "--region",
                self.config.region,
            ],
            check=False,
        )

        if exit_code != 0:
            logger.info(f"Creating CloudWatch log group: {log_group}")
            self._run_aws_command(
                [
                    "aws",
                    "logs",
                    "create-log-group",
                    "--log-group-name",
                    log_group,
                    "--region",
                    self.config.region,
                ],
                check=False,  # May fail if it exists, that's OK
            )

    def deploy(self) -> str:
        """
        Deploy service to AWS ECS Fargate and return service URL.

        Returns:
            Service URL (load balancer URL or service endpoint)

        Raises:
            DeploymentError: If deployment fails
        """
        logger.info(f"Deploying {self.config.service.name} to AWS ECS Fargate")

        # Setup resources
        self.setup()

        # Verify image exists
        image = self.config.service.image
        if not self._verify_image_exists(image):
            logger.warning(f"Could not verify image {image} exists in ECR")

        # Build task definition
        task_def = self._build_task_definition(image)

        # Register task definition
        task_def_arn = self._register_task_definition(task_def)

        # Create or update service
        if self._check_service_exists():
            logger.info(f"Updating ECS service: {self.config.service.name}")
            return self.update()
        else:
            logger.info(f"Creating ECS service: {self.config.service.name}")

            # Build network configuration
            network_config = {
                "awsvpcConfiguration": {
                    "subnets": self.subnets,
                    "securityGroups": self.security_groups,
                    "assignPublicIp": self.assign_public_ip,
                }
            }

            # Create service
            create_args = [
                "aws",
                "ecs",
                "create-service",
                "--cluster",
                self.cluster,
                "--service-name",
                self.config.service.name,
                "--task-definition",
                task_def_arn,
                "--desired-count",
                str(self.config.service.min_instances),
                "--launch-type",
                "FARGATE",
                "--network-configuration",
                json.dumps(network_config),
                "--region",
                self.config.region,
            ]

            # Add load balancer if configured
            if "load_balancer" in self.config.provider_config:
                lb_config = self.config.provider_config["load_balancer"]
                create_args.extend(
                    [
                        "--load-balancers",
                        json.dumps([lb_config]),
                    ]
                )

            self._run_aws_command(create_args, check=True)

            # Get service URL (from load balancer or service endpoint)
            return self.get_service_url()

    def get_service_url(self, service_name: Optional[str] = None) -> str:
        """
        Get the deployed service URL.

        Args:
            service_name: Optional service name (defaults to config.service.name)

        Returns:
            Service URL (load balancer URL or service endpoint)

        Raises:
            DeploymentError: If service not found
        """
        name = service_name or self.config.service.name

        # Get service details
        exit_code, stdout, stderr = self._run_aws_command(
            [
                "aws",
                "ecs",
                "describe-services",
                "--cluster",
                self.cluster,
                "--services",
                name,
                "--region",
                self.config.region,
            ],
            check=False,
        )

        if exit_code != 0:
            raise DeploymentError(f"Service {name} not found: {stderr}")

        service_data = json.loads(stdout)
        services = service_data.get("services", [])

        if not services:
            raise DeploymentError(f"Service {name} not found")

        service = services[0]

        # Try to get URL from load balancer
        if "loadBalancers" in service and service["loadBalancers"]:
            lb = service["loadBalancers"][0]
            # Would need to query ELB/ALB to get DNS name
            # For now, return a placeholder
            return f"https://{name}.{self.config.region}.elb.amazonaws.com"

        # If no load balancer, return service endpoint
        # ECS services don't have direct URLs without load balancers
        return f"ecs://{self.cluster}/{name}"

    def update(self) -> str:
        """
        Update existing deployment.

        Returns:
            Service URL

        Raises:
            DeploymentError: If update fails
        """
        logger.info(f"Updating ECS service: {self.config.service.name}")

        # Build and register new task definition
        task_def = self._build_task_definition(self.config.service.image)
        task_def_arn = self._register_task_definition(task_def)

        # Update service
        update_args = [
            "aws",
            "ecs",
            "update-service",
            "--cluster",
            self.cluster,
            "--service",
            self.config.service.name,
            "--task-definition",
            task_def_arn,
            "--desired-count",
            str(self.config.service.min_instances),
            "--region",
            self.config.region,
        ]

        self._run_aws_command(update_args, check=True)

        logger.info(f"Service {self.config.service.name} updated successfully")
        return self.get_service_url()

    def delete(self, service_name: Optional[str] = None) -> None:
        """
        Delete deployment.

        Args:
            service_name: Optional service name (defaults to config.service.name)

        Raises:
            DeploymentError: If deletion fails
        """
        name = service_name or self.config.service.name
        logger.info(f"Deleting ECS service: {name}")

        # Update desired count to 0 first
        self._run_aws_command(
            [
                "aws",
                "ecs",
                "update-service",
                "--cluster",
                self.cluster,
                "--service",
                name,
                "--desired-count",
                "0",
                "--region",
                self.config.region,
            ],
            check=False,
        )

        # Delete service
        self._run_aws_command(
            [
                "aws",
                "ecs",
                "delete-service",
                "--cluster",
                self.cluster,
                "--service",
                name,
                "--region",
                self.config.region,
                "--force",
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
        exit_code, stdout, stderr = self._run_aws_command(
            [
                "aws",
                "ecs",
                "describe-services",
                "--cluster",
                self.cluster,
                "--services",
                name,
                "--region",
                self.config.region,
            ],
            check=False,
        )

        if exit_code != 0:
            return {
                "exists": False,
                "status": "not_found",
                "error": stderr,
            }

        service_data = json.loads(stdout)
        services = service_data.get("services", [])

        if not services:
            return {
                "exists": False,
                "status": "not_found",
            }

        service = services[0]
        return {
            "exists": True,
            "status": service.get("status", "unknown"),
            "desired_count": service.get("desiredCount", 0),
            "running_count": service.get("runningCount", 0),
            "task_definition": service.get("taskDefinition", ""),
            "url": self.get_service_url(name) if service.get("status") == "ACTIVE" else None,
        }

