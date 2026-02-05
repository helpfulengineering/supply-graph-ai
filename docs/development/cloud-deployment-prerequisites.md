# Cloud Deployment Prerequisites

This guide explains what information you need to collect from AWS and Azure to test their respective deployers.

## Prerequisites

### AWS
- AWS account with appropriate permissions
- AWS CLI installed and configured: `aws configure`
- Permissions needed:
  - ECS (create/update services, task definitions, clusters)
  - ECR (push/pull images, describe repositories)
  - IAM (create/read roles)
  - VPC (read subnets, security groups)
  - CloudWatch Logs (create log groups)

### Azure
- Azure account with active subscription
- Azure CLI installed and configured: `az login`
- Permissions needed:
  - Contributor role on subscription or resource group
  - Container Apps (create/update apps, environments)
  - Resource Groups (create/read)
  - Container Registry (if using private registry)

---

## AWS (ECS Fargate) Requirements

### 1. AWS Account ID
**What:** Your 12-digit AWS account ID  
**Where to find:**
- AWS Console → Click your username (top right) → Account ID is displayed
- Or run: `aws sts get-caller-identity --query Account --output text`

**Example:** `123456789012`

### 2. AWS Region
**What:** The AWS region where you want to deploy (e.g., `us-east-1`, `us-west-2`)  
**Where to find:**
- AWS Console → Region selector (top right)
- Or check your default: `aws configure get region`

**Example:** `us-east-1`

### 3. ECS Cluster Name
**What:** Name of your ECS cluster (will be created if it doesn't exist)  
**Where to find:**
- AWS Console → ECS → Clusters
- Or list clusters: `aws ecs list-clusters --region us-east-1`

**Example:** `supply-graph-ai-cluster`  
**Note:** If the cluster doesn't exist, the deployer will create it automatically.

### 4. VPC and Subnets
**What:** VPC ID and subnet IDs where your containers will run  
**Where to find:**
- AWS Console → VPC → Your VPCs
- AWS Console → VPC → Subnets
- Or list subnets: `aws ec2 describe-subnets --region us-east-1 --query 'Subnets[*].[SubnetId,VpcId,AvailabilityZone]' --output table`

**What you need:**
- At least one subnet ID (preferably in different availability zones for high availability)
- VPC ID (for reference, but subnet IDs are what's needed)

**Example:**
```yaml
subnets:
  - subnet-0123456789abcdef0  # us-east-1a
  - subnet-0fedcba9876543210  # us-east-1b
```

**How to create (if needed):**
```bash
# Create VPC (if you don't have one)
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --region us-east-1

# Create subnets
aws ec2 create-subnet \
  --vpc-id vpc-0123456789abcdef0 \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --region us-east-1
```

### 5. Security Groups
**What:** Security group IDs that allow inbound traffic to your containers  
**Where to find:**
- AWS Console → EC2 → Security Groups
- Or list: `aws ec2 describe-security-groups --region us-east-1 --query 'SecurityGroups[*].[GroupId,GroupName]' --output table`

**What you need:**
- At least one security group ID
- The security group should allow inbound traffic on your container port (default: 8080)

**Example:** `sg-0123456789abcdef0`

**How to create (if needed):**
```bash
# Create security group
aws ec2 create-security-group \
  --group-name supply-graph-ai-sg \
  --description "Security group for supply-graph-ai" \
  --vpc-id vpc-0123456789abcdef0 \
  --region us-east-1

# Allow inbound HTTP traffic (adjust port as needed)
aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789abcdef0 \
  --protocol tcp \
  --port 8080 \
  --cidr 0.0.0.0/0 \
  --region us-east-1
```

### 6. IAM Roles

#### Execution Role
**What:** IAM role ARN that allows ECS to pull images and write logs  
**Where to find:**
- AWS Console → IAM → Roles
- Look for roles with `ecsTaskExecutionRole` in the name
- Or list: `aws iam list-roles --query 'Roles[?contains(RoleName, `ecs`)].Arn' --output table`

**Example:** `arn:aws:iam::123456789012:role/ecsTaskExecutionRole`

**How to create (if needed):**
```bash
# Create trust policy
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://trust-policy.json

# Attach managed policy
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

#### Task Role (Optional)
**What:** IAM role ARN for the running container (for accessing AWS services)  
**Where to find:**
- AWS Console → IAM → Roles
- Or create a new role for your application

**Example:** `arn:aws:iam::123456789012:role/ecsTaskRole`  
**Note:** Only needed if your application needs to access AWS services (S3, Secrets Manager, etc.)

### 7. ECR Repository
**What:** ECR repository name where your Docker image will be stored  
**Where to find:**
- AWS Console → ECR → Repositories
- Or list: `aws ecr describe-repositories --region us-east-1 --query 'repositories[*].repositoryName' --output table`

**Example:** `supply-graph-ai`

**How to create (if needed):**
```bash
aws ecr create-repository \
  --repository-name supply-graph-ai \
  --region us-east-1
```

**Image format:** `{account-id}.dkr.ecr.{region}.amazonaws.com/{repository}:{tag}`  
**Example:** `123456789012.dkr.ecr.us-east-1.amazonaws.com/supply-graph-ai:latest`

### 8. CloudWatch Log Group
**What:** CloudWatch log group name (will be created automatically if it doesn't exist)  
**Format:** `/ecs/{service-name}`

**Example:** `/ecs/supply-graph-ai`  
**Note:** The deployer will create this automatically if it doesn't exist.

### 9. Load Balancer (Optional)
**What:** Application Load Balancer (ALB) or Network Load Balancer (NLB) for public access  
**Where to find:**
- AWS Console → EC2 → Load Balancers
- Or list: `aws elbv2 describe-load-balancers --region us-east-1`

**Note:** If you want public access to your service, you'll need to configure a load balancer. This is optional for testing.

---

## Azure (Container Apps) Requirements

### 1. Subscription ID
**What:** Your Azure subscription ID (GUID)  
**Where to find:**
- Azure Portal → Subscriptions → Copy Subscription ID
- Or run: `az account show --query id --output tsv`
- Or list all: `az account list --query '[].{Name:name, SubscriptionId:id}' --output table`

**Example:** `12345678-1234-1234-1234-123456789012`

### 2. Resource Group
**What:** Name of the resource group where resources will be created  
**Where to find:**
- Azure Portal → Resource groups
- Or list: `az group list --query '[].name' --output table`

**Example:** `supply-graph-ai-rg`

**How to create (if needed):**
```bash
az group create \
  --name supply-graph-ai-rg \
  --location eastus
```

### 3. Region (Location)
**What:** Azure region where you want to deploy (e.g., `eastus`, `westus`)  
**Where to find:**
- Azure Portal → Resource groups → Your resource group → Location
- Or check: `az account list-locations --query '[].{Name:name, DisplayName:displayName}' --output table`

**Example:** `eastus`

### 4. Container App Environment (Optional but Recommended)
**What:** Container Apps environment name (will be created if it doesn't exist)  
**Where to find:**
- Azure Portal → Container Apps environments
- Or list: `az containerapp env list --resource-group supply-graph-ai-rg --query '[].name' --output table`

**Example:** `supply-graph-ai-env`

**How to create (if needed):**
```bash
az containerapp env create \
  --name supply-graph-ai-env \
  --resource-group supply-graph-ai-rg \
  --location eastus
```

**Note:** The deployer will create this automatically if you provide a name and it doesn't exist.

### 5. Container Registry (If Using Private Registry)
**What:** Azure Container Registry (ACR) details if using private images  
**Where to find:**
- Azure Portal → Container registries
- Or list: `az acr list --query '[].{Name:name, LoginServer:loginServer}' --output table`

**What you need:**
- Registry server (e.g., `supplygraphai.azurecr.io`)
- Username (usually the registry name)
- Password (admin password or service principal)

**Example:**
```yaml
registry_server: supplygraphai.azurecr.io
registry_username: supplygraphai
registry_password: <admin-password>
```

**How to create (if needed):**
```bash
# Create ACR
az acr create \
  --resource-group supply-graph-ai-rg \
  --name supplygraphai \
  --sku Basic \
  --admin-enabled true

# Get login credentials
az acr credential show --name supplygraphai --query passwords[0].value --output tsv
```

**Note:** If using public images (e.g., from Docker Hub or GHCR), you don't need this.

### 6. Key Vault (Optional - for Secrets)
**What:** Azure Key Vault name if storing secrets there  
**Where to find:**
- Azure Portal → Key vaults
- Or list: `az keyvault list --query '[].name' --output table`

**Example:** `supply-graph-ai-kv`

**Note:** Currently, the deployer supports environment variables for secrets. Key Vault integration is optional.

---

## Quick Reference: Information Checklist

### AWS Checklist
- [ ] AWS Account ID: `_________________`
- [ ] Region: `_________________`
- [ ] ECS Cluster Name: `_________________` (or will be created)
- [ ] Subnet IDs: `_________________` (at least one, preferably two)
- [ ] Security Group ID: `_________________`
- [ ] Execution Role ARN: `_________________`
- [ ] Task Role ARN: `_________________` (optional)
- [ ] ECR Repository Name: `_________________`
- [ ] Load Balancer ARN: `_________________` (optional)

### Azure Checklist
- [ ] Subscription ID: `_________________`
- [ ] Resource Group: `_________________`
- [ ] Region: `_________________`
- [ ] Container App Environment: `_________________` (optional, will be created)
- [ ] Container Registry Server: `_________________` (if using private registry)
- [ ] Container Registry Username: `_________________` (if using private registry)
- [ ] Container Registry Password: `_________________` (if using private registry)
- [ ] Key Vault Name: `_________________` (optional)

---

## Testing the Deployers

Once you have the required information, you can test the deployers:

### AWS Test
```bash
python deploy/scripts/test_aws_deployer.py \
  --account-id YOUR_ACCOUNT_ID \
  --region us-east-1 \
  --cluster your-cluster \
  --subnet subnet-12345 \
  --security-group sg-12345
```

### Azure Test
```bash
python deploy/scripts/test_azure_deployer.py \
  --subscription-id YOUR_SUBSCRIPTION_ID \
  --resource-group your-rg \
  --region eastus
```

---

## Common Issues and Solutions

### AWS
**Issue:** "No default VPC found"  
**Solution:** Create a VPC and subnets, or use an existing VPC.

**Issue:** "Security group doesn't allow inbound traffic"  
**Solution:** Add an inbound rule to your security group allowing traffic on your container port.

**Issue:** "Execution role doesn't have permissions"  
**Solution:** Attach the `AmazonECSTaskExecutionRolePolicy` managed policy to your execution role.

### Azure
**Issue:** "Subscription not found"  
**Solution:** Verify your subscription ID and ensure you're logged in: `az account show`

**Issue:** "Resource group not found"  
**Solution:** Create the resource group first: `az group create --name your-rg --location eastus`

**Issue:** "Container App Environment not found"  
**Solution:** The deployer will create it automatically, or create it manually first.

---

## Next Steps

1. Collect all required information using the checklists above
2. Verify CLI tools are installed and configured:
   - AWS: `aws --version` and `aws configure`
   - Azure: `az --version` and `az login`
3. Test the deployers with the test scripts (to be created)
4. Deploy using the deployment scripts


