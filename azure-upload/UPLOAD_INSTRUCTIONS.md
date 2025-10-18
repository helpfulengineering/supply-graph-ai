
# Azure Storage Upload Instructions

## Directory Structure Created
The following organized directory structure has been created in the `azure-upload` folder:

```
azure-upload/
├── okh/
│   └── manifests/
│       ├── 01/          # 2 OKH manifest files
│       └── 02/
├── okw/
│   └── facilities/
│       ├── manufacturing/    # Manufacturing facilities
│       ├── makerspaces/      # Makerspace facilities with 3D printing
│       └── research/         # Research facilities
└── supply-trees/
    ├── generated/
    └── validated/
```

## Files to Upload
- 2 OKH manifest files (including test data)
- 13 OKW facility files (including test data)
- Organized by facility type and capabilities

## Upload Methods

### Option 1: Azure Portal
1. Go to your Azure Storage Account
2. Navigate to the 'ome' container
3. Upload the entire `azure-upload` folder structure
4. Maintain the directory hierarchy

### Option 2: Azure CLI
```bash
# Upload entire directory structure
az storage blob upload-batch \
    --source azure-upload \
    --destination ome \
    --account-name <your-account-name> \
    --account-key <your-account-key>
```

### Option 3: Azure Storage Explorer
1. Open Azure Storage Explorer
2. Connect to your storage account
3. Navigate to the 'ome' container
4. Upload the `azure-upload` folder
5. Ensure directory structure is preserved

## Testing the Matching System

After upload, test the system:

### 1. Test OKW endpoint
```bash
curl -X GET "http://localhost:8001/v1/okw"
```

### 2. Test matching with 3D printing
```bash
curl -X POST http://localhost:8001/v1/match -H "Content-Type: application/json" -d '{
  "okh_manifest": {
    "title": "3D Printed Bracket",
    "version": "1.0.0",
    "license": {"hardware": "MIT"},
    "licensor": "Test User",
    "documentation_language": "en",
    "function": "Support bracket for mounting components",
    "manufacturing_processes": ["3DP"],
    "manufacturing_specs": {
      "process_requirements": [
        {
          "process_name": "3DP",
          "parameters": {}
        }
      ]
    }
  }
}'
```

### 3. Test with different processes
```bash
# Test CNC matching
curl -X POST http://localhost:8001/v1/match -H "Content-Type: application/json" -d '{
  "okh_manifest": {
    "title": "CNC Machined Part",
    "version": "1.0.0",
    "license": {"hardware": "MIT"},
    "licensor": "Test User",
    "documentation_language": "en",
    "function": "Precision machined component",
    "manufacturing_processes": ["CNC"],
    "manufacturing_specs": {
      "process_requirements": [
        {
          "process_name": "CNC",
          "parameters": {}
        }
      ]
    }
  }
}'
```

## Expected Results
- OKW endpoint should return 13 facilities
- Matching system should find facilities with matching capabilities
- 3DP requests should match makerspace facilities
- CNC requests should match manufacturing facilities

## Troubleshooting
- If no matches found, check that files are properly uploaded
- Verify the API server is running and connected to Azure storage
- Check server logs for any errors
- Ensure the smart discovery system is working correctly
