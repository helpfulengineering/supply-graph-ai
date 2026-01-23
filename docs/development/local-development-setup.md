# Local Development Setup Guide

This guide will help you set up both the **project-data-platform-ts** and **supply-graph-ai** applications for local development.

## Prerequisites

### System Requirements

- **Node.js**: Version 18+ (tested with v24.10.0)
- **npm**: Version 8+ (tested with v11.6.0)
- **Python**: Version 3.12+ (required, tested with v3.12.12)
  - **Note**: Python 3.10 reaches end-of-life in October 2026
  - Python 3.12 offers ~10-15% performance improvements
  - All dependencies are fully compatible with Python 3.12
- **Azure CLI**: For backend authentication (optional for basic development)
- **Git**: For cloning repositories

### Required Tools

1. **Azure CLI** (for backend development):
   ```bash
   # Install Azure CLI
   # macOS (using Homebrew)
   brew install azure-cli
   
   # Or download from: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli
   ```

2. **Azure Functions Core Tools** (for backend development):
   ```bash
   npm install -g azure-functions-core-tools@4 --unsafe-perm true
   ```

## Project Structure Overview

```
open-hardware-manager/
├── project-data-platform-ts/          # Main web application
│   ├── packages/
│   │   ├── front-end/                 # Vue.js/Nuxt frontend
│   │   └── back-end/                  # Azure Functions backend
│   └── docs/
└── supply-graph-ai/                   # FastAPI matching engine
    ├── src/                          # Python source code
    ├── run.py                        # Server entry point
    └── requirements.txt              # Python dependencies
```

## Setup Instructions

### 1. Supply Graph AI (FastAPI Server)

The Supply Graph AI server provides the matching engine API that the frontend consumes.

#### Step 1: Navigate to Supply Graph AI Directory
```bash
cd supply-graph-ai
```

#### Step 2: Create Python Virtual Environment

**Option A: Using Conda (Recommended)**
```bash
# Create conda environment with Python 3.12
conda create -n supply-graph-ai python=3.12 -y

# Activate conda environment
conda activate supply-graph-ai
```

**Option B: Using venv**
```bash
# Create virtual environment (requires Python 3.12 installed)
python3.12 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

#### Step 3: Install Dependencies
```bash
# Install all dependencies
pip install -r requirements.txt

# Install the package in editable mode (recommended for development)
pip install -e .
```

#### Step 4: Install spaCy Models
The NLP matching functionality requires spaCy language models. Install the recommended model:
```bash
# Install the medium model with word vectors (recommended)
python -m spacy download en_core_web_md

# Optional: Install larger model for better accuracy (requires more disk space)
# python -m spacy download en_core_web_lg
```

**Note**: The system will automatically fall back to `en_core_web_sm` if the preferred models are not available, but the medium model (`en_core_web_md`) provides better semantic similarity matching with word vectors.

#### Step 5: Create Logs Directory (if needed)
```bash
mkdir -p logs
```

#### Step 6: Start the Server
```bash
python run.py
```

The server will start on **http://localhost:8001**

#### Step 7: Verify Installation
- Open your browser to: **http://localhost:8001/docs**
- You should see the FastAPI interactive documentation
- Health check: **http://localhost:8001/health**

### 2. Project Data Platform TS (Web Application)

The main web application consists of a Vue.js frontend and Azure Functions backend.

#### Backend Setup (Azure Functions)

##### Step 1: Navigate to Backend Directory
```bash
cd project-data-platform-ts/packages/back-end
```

##### Step 2: Install Dependencies
```bash
npm install
```

##### Step 3: Configure Local Settings
```bash
# Copy the template file
cp local.settings.json.template local.settings.json
```

The `local.settings.json` file should look like this:
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "node",
    "Azure_Storage_ServiceName": "${AZURE_STORAGE_SERVICE_NAME}",
    "Azure_Storage_OKH_ContainerName": "okh",
    "Azure_Storage_OKW_ContainerName": "okw"
  },
  "Host": {
    "CORS": "*",
    "CORS_AllowedOrigins": [
      "http://localhost:3000/"
    ]
  }
}
```

##### Step 4: Azure Authentication (Optional for Development)
If you need to access Azure resources:

```bash
# Login to Azure
az login

# Select your subscription (if you have multiple)
az account list --output table
az account set --subscription "Your-Subscription-Name"
```

**Note**: You need proper Azure permissions to access the storage account. Contact the admin if you don't have access.

##### Step 5: Start the Backend Server
```bash
npm run start
```

The backend will start on **http://localhost:7071**

Expected output:
```
[2024-10-29T22:44:06.199Z] Worker process started and initialized.

Functions:
  getOKH: [GET,POST] http://localhost:7071/api/getOKH
  getOKHs: [GET,POST] http://localhost:7071/api/getOKHs
  listOKHsummaries: [GET] http://localhost:7071/api/listOKHsummaries
```

#### Frontend Setup (Vue.js/Nuxt)

##### Step 1: Navigate to Frontend Directory
```bash
cd project-data-platform-ts/packages/front-end
```

##### Step 2: Install Dependencies
```bash
npm install
```

##### Step 3: Start the Development Server
```bash
npm run dev
```

The frontend will start on **http://localhost:3000**

##### Step 4: Verify Installation
- Open your browser to: **http://localhost:3000**
- You should see the main application homepage
- Test the Supply Graph AI integration at: **http://localhost:3000/supply-graph-api**

## Development Workflow

### Starting All Services

For full-stack development, you'll need to run all three services:

#### Terminal 1: Supply Graph AI
```bash
cd supply-graph-ai
# If using conda:
conda activate supply-graph-ai
# If using venv:
# source venv/bin/activate  # On Windows: venv\Scripts\activate

python run.py
```

#### Terminal 2: Backend (Azure Functions)
```bash
cd project-data-platform-ts/packages/back-end
npm run start
```

#### Terminal 3: Frontend (Vue.js/Nuxt)
```bash
cd project-data-platform-ts/packages/front-end
npm run dev
```

### Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:3000 | Main web application |
| Backend | http://localhost:7071 | Azure Functions API |
| Supply Graph AI | http://localhost:8001 | Matching engine API |
| Supply Graph AI Docs | http://localhost:8001/docs | API documentation |

## Configuration

### Environment Variables

#### Frontend Configuration
The frontend uses Nuxt's runtime configuration. Key settings in `nuxt.config.ts`:

```typescript
runtimeConfig: {
  public: {
    baseUrl: process.env.BACKEND_URL || 'http://127.0.0.1:7071/api',
    supplyGraphAiUrl: process.env.SUPPLY_GRAPH_AI_URL || 'http://localhost:8001'
  }
}
```

**Note**: The API server runs on port 8001 by default. This matches the CLI default and Docker compose configuration.

#### Supply Graph AI Configuration
The server can be configured using environment variables:

```bash
# Optional: Create .env file in supply-graph-ai directory
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8001
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
DEBUG=True
```

### CORS Configuration

The Supply Graph AI server is configured to allow CORS requests from the frontend. The default configuration allows all origins (`*`), but for production, you should specify exact origins.

## Testing the Integration

### 1. Test Backend Connectivity
```bash
# Test backend health
curl http://localhost:7071/api/listOKHsummaries

# Expected: JSON response with OKH summaries
```

### 2. Test Supply Graph AI Connectivity
```bash
# Test API health
curl http://localhost:8001/health

# Expected: {"status": "ok", "domains": [...], "version": "1.0.0"}

# Test API documentation
open http://localhost:8001/docs
```

### 3. Test Frontend Integration
1. Open http://localhost:3000/supply-graph-api
2. The page should load OKH data from the backend
3. Click on an OKH item to test the Supply Graph AI integration
4. Check browser console for any errors

## Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Find process using port 8001
lsof -i :8001

# Kill the process
kill -9 <PID>
```

#### 2. Python Virtual Environment Issues
```bash
# If you get permission errors
python -m venv venv --clear
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 2a. spaCy Model Not Found
If you see warnings about spaCy models not being found:
```bash
# Verify spaCy is installed
python -c "import spacy; print(spacy.__version__)"

# Check available models
python -m spacy info

# Install the recommended model
python -m spacy download en_core_web_md
```

**Symptoms**: You may see warnings like:
- `spaCy model 'en_core_web_md' not found, trying next...`
- `[W007] The model you're using has no word vectors loaded`

**Solution**: Install the spaCy model as shown above. The system will work with `en_core_web_sm` (installed by default), but `en_core_web_md` provides better semantic matching.

#### 3. Node.js Dependencies Issues
```bash
# Clear npm cache and reinstall
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

#### 4. Azure Functions Issues
```bash
# Reinstall Azure Functions Core Tools
npm uninstall -g azure-functions-core-tools
npm install -g azure-functions-core-tools@4 --unsafe-perm true
```

#### 5. CORS Errors
If you see CORS errors in the browser console:

1. Check that Supply Graph AI is running on port 8001
2. Verify the frontend is making requests to the correct URL
3. Check the CORS configuration in Supply Graph AI

#### 6. Backend Connection Issues
If the frontend can't connect to the backend:

1. Verify the backend is running on port 7071
2. Check the `baseUrl` configuration in `nuxt.config.ts`
3. Ensure the backend has proper CORS configuration

### Debug Mode

#### Enable Debug Logging
For Supply Graph AI:
```bash
export LOG_LEVEL=DEBUG
python run.py
```

For Frontend:
```bash
# Add to nuxt.config.ts
export default defineNuxtConfig({
  devtools: { enabled: true },
  // ... other config
})
```

#### Check Logs
- Supply Graph AI logs: `supply-graph-ai/logs/app.log`
- Frontend logs: Browser developer console
- Backend logs: Terminal output

## Development Tips

### 1. Hot Reloading
- **Frontend**: Nuxt provides hot reloading by default
- **Backend**: Azure Functions restarts automatically on file changes
- **Supply Graph AI**: Use `reload=True` in `run.py` for auto-restart

### 2. API Testing
- Use the interactive docs at http://localhost:8001/docs
- Test endpoints with curl or Postman
- Use browser developer tools to inspect network requests

### 3. Database/Storage
- The backend connects to Azure Blob Storage
- For development, you can use the existing storage account
- No local database setup required

### 4. Code Organization
- Frontend: Vue.js components in `packages/front-end/components/`
- Backend: Azure Functions in `packages/back-end/src/functions/`
- Supply Graph AI: FastAPI routes in `src/core/api/routes/`

## Next Steps

After setting up the development environment:

1. **Read the Integration Guide**: See `docs/supply-graph-ai-integration.md` for detailed API usage
2. **Explore the Codebase**: Familiarize yourself with the project structure
3. **Run Tests**: Check if there are any existing tests to run
4. **Start Developing**: Make your first changes and test them locally

## Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Review the logs for error messages
3. Check the GitHub issues for known problems
4. Ask the team for help with Azure permissions or configuration

---

This setup guide should get you up and running with both applications for local development. The key is ensuring all three services (frontend, backend, and Supply Graph AI) are running and can communicate with each other.
