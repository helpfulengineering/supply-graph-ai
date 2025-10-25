# Supply Graph AI Integration Guide

## Overview

This document provides comprehensive guidance for integrating the Supply Graph AI FastAPI server with the Vue.js frontend in the project-data-platform-ts application.

## Current Integration Status

### Active Integration Points

The frontend currently integrates with Supply Graph AI in **2 locations**:

1. **`pages/supply-graph-api.vue`** - Test page for Supply Graph AI functionality
2. **`pages/products/[id]/supplyTree.vue`** - Product-specific supply tree generation

### Configuration

**Environment Variables:**
```typescript
// In nuxt.config.ts
supplyGraphAiUrl: process.env.SUPPLY_GRAPH_AI_URL || 'http://localhost:8081'

// In Vue components
const supplyGraphApiUrl = ref(import.meta.env.VITE_SUPPLY_GRAPH_AI_URL || 'http://localhost:8001');
```

⚠️ **Configuration Issue**: There's a port mismatch between nuxt.config.ts (8081) and Vue components (8001). This should be standardized to 8001

## Supply Graph AI API Endpoints

The FastAPI server provides the following main endpoint categories:

### Base URL Structure
```
http://localhost:8001/v1/
```

### Available Endpoints

#### 1. Match Endpoints (`/v1/match`)
- **POST** `/v1/match` - Enhanced requirements matching
- **POST** `/v1/match/upload` - Match from file upload
- **GET** `/v1/match/domains` - List available domains

#### 2. OKH Endpoints (`/v1/okh`)
- **POST** `/v1/okh` - Create OKH manifest
- **GET** `/v1/okh/{id}` - Get OKH by ID
- **GET** `/v1/okh` - List OKH manifests (paginated)
- **PUT** `/v1/okh/{id}` - Update OKH manifest
- **DELETE** `/v1/okh/{id}` - Delete OKH manifest
- **POST** `/v1/okh/validate` - Validate OKH manifest

#### 3. OKW Endpoints (`/v1/okw`)
- **POST** `/v1/okw` - Create OKW facility
- **GET** `/v1/okw/{id}` - Get OKW by ID
- **GET** `/v1/okw` - List OKW facilities (paginated)
- **PUT** `/v1/okw/{id}` - Update OKW facility
- **DELETE** `/v1/okw/{id}` - Delete OKW facility
- **POST** `/v1/okw/validate` - Validate OKW facility

#### 4. Supply Tree Endpoints (`/v1/supply-tree`)
- **POST** `/v1/supply-tree/create` - Create supply tree
- **GET** `/v1/supply-tree/{id}` - Get supply tree by ID
- **GET** `/v1/supply-tree` - List supply trees (paginated)

#### 5. Utility Endpoints (`/v1/utility`)
- **GET** `/v1/utility/domains` - List available domains
- **GET** `/v1/utility/contexts` - List available contexts

#### 6. Package Endpoints (`/v1/package`)
- **POST** `/v1/package/build` - Build package
- **GET** `/v1/package/{id}` - Get package by ID

#### 7. System Endpoints
- **GET** `/` - Root endpoint with API information
- **GET** `/health` - Health check
- **GET** `/docs` - Interactive API documentation
- **GET** `/openapi.json` - OpenAPI specification

## Current Implementation Patterns

### Pattern 1: Match Endpoint (supply-graph-api.vue)

```typescript
const sendToSupplyGraphAI = async (okhItem) => {
  const payload = {
    okh_manifest: {
      title: okhItem.name || "Unknown Hardware",
      version: "1.0.0",
      manufacturing_specs: {
        process_requirements: [
          {
            process_name: "General Manufacturing",
            parameters: {}
          }
        ]
      }
    }
  };

  const response = await fetch(`${supplyGraphApiUrl.value}/v1/match`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'User-Agent': 'project-data-platform-ts/1.0',
      'X-Requested-With': 'XMLHttpRequest',
      'Origin': window.location.origin,
    },
    mode: 'cors',
    body: JSON.stringify(payload),
  });
};
```

### Pattern 2: Supply Tree Creation (supplyTree.vue)

```typescript
const sendToSupplyGraphAI = async (o: any) => {
  const payload = {
    okh_reference: okhItem.id?.toString() || "unknown",
    required_quantity: 1,
    deadline: null,
    metadata: {
      name: okhItem.name,
      shortDescription: okhItem.shortDescription,
      keywords: okhItem.keywords || [],
      maker: okhItem.maker,
      whereToFind: okhItem.whereToFind,
      source: "project-data-platform-ts",
      // ... additional metadata
    }
  };

  const response = await fetch(`${supplyGraphApiUrl.value}/v1/supply-tree/create`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "User-Agent": "project-data-platform-ts/1.0",
      "X-Requested-With": "XMLHttpRequest",
      Origin: window.location.origin,
    },
    mode: "cors",
    body: JSON.stringify(payload),
  });
};
```

## Recommended Integration Patterns

### 1. Standardized API Client

Create a reusable API client for Supply Graph AI:

```typescript
// utils/supplyGraphApi.ts
export class SupplyGraphApiClient {
  private baseUrl: string;
  
  constructor(baseUrl: string = 'http://localhost:8001') {
    this.baseUrl = baseUrl;
  }

  private async makeRequest(endpoint: string, options: RequestInit = {}) {
    const url = `${this.baseUrl}/v1${endpoint}`;
    
    const defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'User-Agent': 'project-data-platform-ts/1.0',
      'X-Requested-With': 'XMLHttpRequest',
      'Origin': typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000',
    };

    const response = await fetch(url, {
      ...options,
      headers: { ...defaultHeaders, ...options.headers },
      mode: 'cors',
    });

    if (!response.ok) {
      let errorData = null;
      try {
        errorData = await response.json();
      } catch (e) {
        console.warn('Could not parse error response as JSON');
      }
      throw new Error(
        `Supply Graph AI API error: ${response.status} ${response.statusText}` +
        (errorData ? ` - ${JSON.stringify(errorData)}` : '')
      );
    }

    return response.json();
  }

  // Match endpoints
  async matchRequirements(payload: any) {
    return this.makeRequest('/match', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async matchFromFile(file: File, options: any = {}) {
    const formData = new FormData();
    formData.append('okh_file', file);
    
    Object.entries(options).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        formData.append(key, value.toString());
      }
    });

    return this.makeRequest('/match/upload', {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type for FormData
    });
  }

  // Supply tree endpoints
  async createSupplyTree(payload: any) {
    return this.makeRequest('/supply-tree/create', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getSupplyTree(id: string) {
    return this.makeRequest(`/supply-tree/${id}`);
  }

  // OKH endpoints
  async createOKH(payload: any) {
    return this.makeRequest('/okh', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getOKH(id: string) {
    return this.makeRequest(`/okh/${id}`);
  }

  async listOKH(pagination: any = {}) {
    const params = new URLSearchParams(pagination);
    return this.makeRequest(`/okh?${params}`);
  }

  // OKW endpoints
  async createOKW(payload: any) {
    return this.makeRequest('/okw', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getOKW(id: string) {
    return this.makeRequest(`/okw/${id}`);
  }

  async listOKW(pagination: any = {}) {
    const params = new URLSearchParams(pagination);
    return this.makeRequest(`/okw?${params}`);
  }

  // Utility endpoints
  async getDomains() {
    return this.makeRequest('/utility/domains');
  }

  async getContexts() {
    return this.makeRequest('/utility/contexts');
  }

  // Health check
  async healthCheck() {
    return this.makeRequest('/health');
  }
}

// Export singleton instance
export const supplyGraphApi = new SupplyGraphApiClient(
  import.meta.env.VITE_SUPPLY_GRAPH_AI_URL || 'http://localhost:8001'
);
```

### 2. Vue Composable for Supply Graph AI

```typescript
// composables/useSupplyGraphAI.ts
import { ref, computed } from 'vue';
import { supplyGraphApi } from '~/utils/supplyGraphApi';

export function useSupplyGraphAI() {
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastResponse = ref<any>(null);

  const isHealthy = ref(false);

  // Check API health
  const checkHealth = async () => {
    try {
      await supplyGraphApi.healthCheck();
      isHealthy.value = true;
      return true;
    } catch (err) {
      isHealthy.value = false;
      console.warn('Supply Graph AI API is not available:', err);
      return false;
    }
  };

  // Generic request handler
  const makeRequest = async <T>(
    requestFn: () => Promise<T>,
    errorMessage: string = 'Request failed'
  ): Promise<T | null> => {
    loading.value = true;
    error.value = null;

    try {
      const result = await requestFn();
      lastResponse.value = result;
      return result;
    } catch (err: any) {
      error.value = `${errorMessage}: ${err.message}`;
      console.error(errorMessage, err);
      return null;
    } finally {
      loading.value = false;
    }
  };

  // Specific API methods
  const matchRequirements = async (payload: any) => {
    return makeRequest(
      () => supplyGraphApi.matchRequirements(payload),
      'Failed to match requirements'
    );
  };

  const createSupplyTree = async (payload: any) => {
    return makeRequest(
      () => supplyGraphApi.createSupplyTree(payload),
      'Failed to create supply tree'
    );
  };

  const createOKH = async (payload: any) => {
    return makeRequest(
      () => supplyGraphApi.createOKH(payload),
      'Failed to create OKH'
    );
  };

  const getOKH = async (id: string) => {
    return makeRequest(
      () => supplyGraphApi.getOKH(id),
      'Failed to get OKH'
    );
  };

  const listOKH = async (pagination: any = {}) => {
    return makeRequest(
      () => supplyGraphApi.listOKH(pagination),
      'Failed to list OKH items'
    );
  };

  const createOKW = async (payload: any) => {
    return makeRequest(
      () => supplyGraphApi.createOKW(payload),
      'Failed to create OKW'
    );
  };

  const getOKW = async (id: string) => {
    return makeRequest(
      () => supplyGraphApi.getOKW(id),
      'Failed to get OKW'
    );
  };

  const listOKW = async (pagination: any = {}) => {
    return makeRequest(
      () => supplyGraphApi.listOKW(pagination),
      'Failed to list OKW items'
    );
  };

  const getDomains = async () => {
    return makeRequest(
      () => supplyGraphApi.getDomains(),
      'Failed to get domains'
    );
  };

  const getContexts = async () => {
    return makeRequest(
      () => supplyGraphApi.getContexts(),
      'Failed to get contexts'
    );
  };

  return {
    // State
    loading: computed(() => loading.value),
    error: computed(() => error.value),
    lastResponse: computed(() => lastResponse.value),
    isHealthy: computed(() => isHealthy.value),

    // Methods
    checkHealth,
    matchRequirements,
    createSupplyTree,
    createOKH,
    getOKH,
    listOKH,
    createOKW,
    getOKW,
    listOKW,
    getDomains,
    getContexts,
  };
}
```

### 3. Updated Component Usage

```vue
<script setup lang="ts">
import { useSupplyGraphAI } from '~/composables/useSupplyGraphAI';

const { 
  loading, 
  error, 
  isHealthy, 
  checkHealth, 
  matchRequirements, 
  createSupplyTree 
} = useSupplyGraphAI();

// Check health on mount
onMounted(async () => {
  await checkHealth();
});

const handleMatchRequirements = async (okhItem: any) => {
  const payload = {
    okh_manifest: {
      title: okhItem.name || "Unknown Hardware",
      version: "1.0.0",
      manufacturing_specs: {
        process_requirements: [
          {
            process_name: "General Manufacturing",
            parameters: {}
          }
        ]
      }
    }
  };

  const result = await matchRequirements(payload);
  if (result) {
    console.log('Match result:', result);
    // Handle successful match
  }
};

const handleCreateSupplyTree = async (okhItem: any) => {
  const payload = {
    okh_reference: okhItem.id?.toString() || "unknown",
    required_quantity: 1,
    deadline: null,
    metadata: {
      name: okhItem.name,
      shortDescription: okhItem.shortDescription,
      keywords: okhItem.keywords || [],
      maker: okhItem.maker,
      whereToFind: okhItem.whereToFind,
      source: "project-data-platform-ts",
    }
  };

  const result = await createSupplyTree(payload);
  if (result) {
    console.log('Supply tree result:', result);
    // Handle successful supply tree creation
  }
};
</script>

<template>
  <div>
    <div v-if="!isHealthy" class="warning">
      ⚠️ Supply Graph AI API is not available
    </div>
    
    <div v-if="loading" class="loading">
      Loading...
    </div>
    
    <div v-if="error" class="error">
      {{ error }}
    </div>
    
    <!-- Your component content -->
  </div>
</template>
```

## Error Handling Best Practices

### 1. Standardized Error Response Format

The Supply Graph AI API returns errors in this format:

```json
{
  "detail": "Error message",
  "status_code": 400,
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-here"
}
```

### 2. Error Handling in Components

```typescript
const handleApiError = (error: any) => {
  if (error.message.includes('CORS')) {
    return 'CORS error: Check if Supply Graph AI server is running and CORS is configured';
  }
  
  if (error.message.includes('NetworkError')) {
    return 'Network error: Check if Supply Graph AI server is accessible';
  }
  
  if (error.message.includes('404')) {
    return 'Endpoint not found: Check if the API endpoint exists';
  }
  
  if (error.message.includes('500')) {
    return 'Server error: Check Supply Graph AI server logs';
  }
  
  return error.message || 'Unknown error occurred';
};
```

## Configuration Management

### 1. Environment Variables

Create a `.env` file:

```bash
# Supply Graph AI Configuration
VITE_SUPPLY_GRAPH_AI_URL=http://localhost:8001
VITE_SUPPLY_GRAPH_AI_TIMEOUT=30000
VITE_SUPPLY_GRAPH_AI_RETRY_ATTEMPTS=3
```

### 2. Runtime Configuration

```typescript
// config/supplyGraphAI.ts
export const supplyGraphAIConfig = {
  baseUrl: import.meta.env.VITE_SUPPLY_GRAPH_AI_URL || 'http://localhost:8001',
  timeout: parseInt(import.meta.env.VITE_SUPPLY_GRAPH_AI_TIMEOUT || '30000'),
  retryAttempts: parseInt(import.meta.env.VITE_SUPPLY_GRAPH_AI_RETRY_ATTEMPTS || '3'),
  endpoints: {
    match: '/v1/match',
    supplyTree: '/v1/supply-tree',
    okh: '/v1/okh',
    okw: '/v1/okw',
    utility: '/v1/utility',
    health: '/health',
  }
};
```

## Testing

### 1. API Health Check

```typescript
// Test if the API is accessible
const testApiConnection = async () => {
  try {
    const response = await fetch(`${supplyGraphAIConfig.baseUrl}/health`);
    return response.ok;
  } catch (error) {
    console.error('API connection test failed:', error);
    return false;
  }
};
```

### 2. Endpoint Testing

```typescript
// Test specific endpoints
const testEndpoints = async () => {
  const endpoints = [
    '/health',
    '/v1/utility/domains',
    '/v1/utility/contexts',
  ];

  for (const endpoint of endpoints) {
    try {
      const response = await fetch(`${supplyGraphAIConfig.baseUrl}${endpoint}`);
      console.log(`${endpoint}: ${response.ok ? 'OK' : 'FAILED'}`);
    } catch (error) {
      console.error(`${endpoint}: ERROR`, error);
    }
  }
};
```

## Troubleshooting

### Common Issues

1. **CORS Errors**
   - Ensure Supply Graph AI server has CORS configured
   - Check that the frontend URL is in the allowed origins

2. **Port Mismatch**
   - Standardize on port 8001 (as used in Vue components)
   - Update nuxt.config.ts to use port 8001

3. **API Not Available**
   - Check if Supply Graph AI server is running
   - Verify the base URL configuration
   - Test with `/health` endpoint first

4. **Authentication Issues**
   - Check if API key is required
   - Verify Authorization header format

### Debug Mode

```typescript
// Enable debug logging
const debugMode = import.meta.env.DEV;

if (debugMode) {
  console.log('Supply Graph AI Config:', supplyGraphAIConfig);
  console.log('API Health:', await testApiConnection());
}
```

## Migration Guide

### From Current Implementation

1. **Replace direct fetch calls** with the standardized API client
2. **Use the composable** for state management
3. **Standardize error handling** across all components
4. **Fix port configuration** inconsistency
5. **Add health checks** to components that use the API

### Step-by-Step Migration

1. Create the API client utility
2. Create the Vue composable
3. Update one component at a time
4. Test each component thoroughly
5. Remove old implementation code

## Future Enhancements

### Potential New Integrations

1. **OKH Management**: Full CRUD operations for OKH manifests
2. **OKW Management**: Full CRUD operations for OKW facilities
3. **File Upload**: Support for OKH file uploads
4. **Real-time Updates**: WebSocket integration for live updates
5. **Caching**: Implement response caching for better performance
6. **Offline Support**: Cache responses for offline usage

### API Extensions

Consider implementing:
- Batch operations for multiple items
- Advanced filtering and search
- Export functionality (PDF, Excel)
- Integration with external manufacturing databases
- Real-time supply chain monitoring

---

This documentation should provide the Vue.js team with everything they need to effectively integrate with the Supply Graph AI FastAPI server. The standardized patterns will make the codebase more maintainable and reduce integration issues.
