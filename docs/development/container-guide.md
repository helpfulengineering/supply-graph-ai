# Container Guide

This guide covers running and deploying the Open Hardware Manager (OHM) in containerized environments.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage Modes](#usage-modes)
- [Production Deployment](#production-deployment)
- [Cloud Platform Deployment](#cloud-platform-deployment)
- [Monitoring and Logging](#monitoring-and-logging)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Using Docker Compose (Recommended for Development)

1. **Clone and navigate to the project:**
   ```bash
   cd supply-graph-ai
   ```

2. **Copy the environment template:**
   ```bash
   cp env.template .env
   ```

3. **Edit the `.env` file with your configuration:**
   ```bash
   nano .env  # or your preferred editor
   ```

4. **Start the API server:**
   ```bash
   docker-compose up ohm-api
   ```

5. **Access the API:**
   - API Documentation: http://localhost:8001/docs
   - Health Check: http://localhost:8001/health
   - API Base URL: http://localhost:8001/v1

### Using Docker Directly

1. **Build the image:**
   ```bash
   docker build -t supply-graph-ai .
   ```

2. **Run the API server:**
   ```bash
   docker run -p 8001:8001 \
     -e API_KEYS="your-api-key" \
     -v $(pwd)/storage:/app/storage \
     -v $(pwd)/logs:/app/logs \
     supply-graph-ai api
   ```

3. **Run CLI commands:**
   ```bash
   docker run --rm \
     -v $(pwd)/storage:/app/storage \
     -v $(pwd)/test-data:/app/test-data \
     supply-graph-ai cli okh validate /app/test-data/manifest.okh.json
   ```

## Configuration

### Environment Variables

The container supports configuration through environment variables. See `env.template` for a complete list of available options.

#### Essential Configuration

- `API_HOST`: API server host (default: 0.0.0.0)
- `API_PORT`: API server port (default: 8001)
- `API_KEYS`: Comma-separated list of API keys for authentication
- `LOG_LEVEL`: Logging level (default: INFO)
- `DEBUG`: Enable debug mode (default: false)

#### Storage Configuration

- `STORAGE_PROVIDER`: Storage provider (local, aws_s3, azure_blob, gcp_storage)
- `STORAGE_BUCKET_NAME`: Storage bucket/container name

#### LLM Configuration

- `LLM_ENABLED`: Enable LLM integration (default: false)
- `LLM_PROVIDER`: LLM provider (openai, anthropic, google, azure, local)
- `LLM_MODEL`: Specific model to use
- `LLM_QUALITY_LEVEL`: Quality level (hobby, professional, medical)

### Volume Mounts

The container expects the following volume mounts:

- `/app/storage`: Persistent storage directory
- `/app/logs`: Log files directory
- `/app/test-data`: Test data directory (optional)

## Usage Modes

### API Server Mode

Start the FastAPI server:

```bash
docker run -p 8001:8001 supply-graph-ai api
```

### CLI Mode

Run CLI commands:

```bash
# Show CLI help
docker run --rm supply-graph-ai cli --help

# Validate an OKH file
docker run --rm \
  -v $(pwd)/test-data:/app/test-data \
  supply-graph-ai cli okh validate /app/test-data/manifest.okh.json

# List packages
docker run --rm supply-graph-ai cli package list

# Run matching
docker run --rm \
  -v $(pwd)/test-data:/app/test-data \
  supply-graph-ai cli match okh /app/test-data/manifest.okh.json
```

## Production Deployment

### Using Docker

1. **Build production image:**
   ```bash
   docker build -t ohm-prod .
   ```

2. **Run with production settings:**
   ```bash
   docker run -d \
     --name ohm-api \
     -p 8001:8001 \
     -e API_KEYS="your-production-api-key" \
     -e LOG_LEVEL="INFO" \
     -e STORAGE_PROVIDER="aws_s3" \
     -e AWS_S3_BUCKET="your-bucket" \
     -v ohm-storage:/app/storage \
     -v ohm-logs:/app/logs \
     ohm-prod
   ```

### Using Docker Compose (Production)

Create a `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  ohm-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ohm-api-prod
    ports:
      - "8001:8001"
    environment:
      - API_HOST=0.0.0.0
      - API_PORT=8001
      - LOG_LEVEL=INFO
      - DEBUG=false
      - API_KEYS=${API_KEYS}
      - STORAGE_PROVIDER=${STORAGE_PROVIDER}
      - STORAGE_BUCKET_NAME=${STORAGE_BUCKET_NAME}
      - LLM_ENABLED=${LLM_ENABLED}
      - LLM_PROVIDER=${LLM_PROVIDER}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ohm-storage:/app/storage
      - ohm-logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  ohm-storage:
  ohm-logs:
```

Deploy with:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Cloud Platform Deployment

### Google Cloud Run

1. **Build and push image:**
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/supply-graph-ai
   ```

2. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy supply-graph-ai \
     --image gcr.io/PROJECT_ID/supply-graph-ai \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --port 8001 \
     --memory 4Gi \
     --cpu 2 \
     --max-instances 10 \
     --set-env-vars="API_KEYS=your-api-key,STORAGE_PROVIDER=gcp_storage"
   ```

### AWS ECS (Fargate)

1. **Create ECS task definition:**
   ```json
   {
     "family": "supply-graph-ai",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "1024",
     "memory": "2048",
     "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
     "containerDefinitions": [{
       "name": "ohm-api",
       "image": "ACCOUNT.dkr.ecr.REGION.amazonaws.com/supply-graph-ai:latest",
       "portMappings": [{
         "containerPort": 8001,
         "protocol": "tcp"
       }],
       "environment": [
         {"name": "API_KEYS", "value": "your-api-key"},
         {"name": "STORAGE_PROVIDER", "value": "aws_s3"},
         {"name": "AWS_S3_BUCKET", "value": "your-bucket"}
       ],
       "logConfiguration": {
         "logDriver": "awslogs",
         "options": {
           "awslogs-group": "/ecs/supply-graph-ai",
           "awslogs-region": "us-east-1",
           "awslogs-stream-prefix": "ecs"
         }
       }
     }]
   }
   ```

2. **Create ECS service:**
   ```bash
   aws ecs create-service \
     --cluster your-cluster \
     --service-name ohm-api \
     --task-definition supply-graph-ai \
     --desired-count 2 \
     --launch-type FARGATE \
     --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
   ```

### Azure Container Instances

1. **Deploy with Azure CLI:**
   ```bash
   az container create \
     --resource-group myResourceGroup \
     --name ohm-api \
     --image your-registry.azurecr.io/supply-graph-ai:latest \
     --cpu 2 \
     --memory 4 \
     --ports 8001 \
     --environment-variables \
       API_KEYS=your-api-key \
       STORAGE_PROVIDER=azure_blob \
       AZURE_STORAGE_ACCOUNT_NAME=your-account \
     --registry-login-server your-registry.azurecr.io \
     --registry-username your-username \
     --registry-password your-password
   ```

### Kubernetes

1. **Apply Kubernetes manifests:**
   ```bash
   kubectl apply -f k8s-deployment.yaml
   ```

2. **Check deployment status:**
   ```bash
   kubectl get pods -n ohm
   kubectl get services -n ohm
   kubectl get ingress -n ohm
   ```

3. **Access the application:**
   ```bash
   kubectl port-forward -n ohm service/ohm-api-service 8001:80
   ```

## Monitoring and Logging

### Health Checks

The application provides several health check endpoints:

- `GET /health` - Basic health check
- `GET /` - API information and status

### Logging

Configure logging through environment variables:

```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FILE=logs/app.log
```

### Monitoring with Prometheus

Add Prometheus metrics endpoint:

```python
# In your FastAPI app
from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)
```

### Log Aggregation

For production, consider using:

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Fluentd** for log collection
- **CloudWatch** (AWS) or **Stackdriver** (GCP) for cloud logging

## Security Considerations

### API Security

1. **Use strong API keys:**
   ```bash
   API_KEYS="$(openssl rand -hex 32),$(openssl rand -hex 32)"
   ```

2. **Enable HTTPS in production:**
   - Use reverse proxy (nginx, traefik)
   - Configure SSL certificates
   - Set secure headers

3. **Network security:**
   - Use private networks where possible
   - Configure firewall rules
   - Implement rate limiting

### Container Security

1. **Use non-root user** (already configured)
2. **Scan images for vulnerabilities:**
   ```bash
   docker scan supply-graph-ai
   ```
3. **Keep base images updated**
4. **Use secrets management** for sensitive data

### Data Protection

1. **Encrypt data at rest**
2. **Use secure storage backends**
3. **Implement data retention policies**
4. **Regular security audits**

## Troubleshooting

### Common Issues

1. **Container won't start:**
   ```bash
   docker logs <container-id>
   ```

2. **API not accessible:**
   - Check port mapping
   - Verify firewall settings
   - Check container health

3. **Storage issues:**
   - Verify volume mounts
   - Check storage provider credentials
   - Ensure proper permissions

4. **Memory issues:**
   - Monitor memory usage
   - Adjust container limits
   - Check for memory leaks

### Debug Mode

Enable debug mode for troubleshooting:

```bash
docker run -e DEBUG=true -e LOG_LEVEL=DEBUG supply-graph-ai api
```

### Performance Tuning

1. **Monitor resource usage:**
   ```bash
   docker stats <container-id>
   ```

2. **Scale horizontally:**
   ```bash
   docker-compose up --scale ohm-api=3
   ```

## Best Practices

1. **Use environment-specific configurations**
2. **Implement proper logging and monitoring**
3. **Regular security updates**
4. **Backup strategies for persistent data**
5. **Disaster recovery planning**
6. **Performance testing and optimization**

## Support

For deployment issues:

1. Check the logs for error messages
2. Verify environment variable configuration
3. Ensure all required volumes are mounted
4. Check network connectivity for external services
5. Review the troubleshooting section above
