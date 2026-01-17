# Request for Quote (RFQ) System

The Request for Quote (RFQ) system in OHM allows for bidirectional communication with external supply chain providers. It enables OHM to broadcast project requirements to potential suppliers and receive commercial quotes and status updates in return.

## Overview

The system supports a generic `SUPPLY_CHAIN` integration category. Any external provider that implements the OHM Supply Chain API contract can be connected.

**Key Features:**
*   **Outbound RFQs**: Broadcast project details (ID, name, description, capabilities) to configured providers.
*   **Inbound Quotes**: Receive price and availability quotes via secure webhooks.
*   **Status Synchronization**: Receive status updates (e.g., "accepted", "filled") from providers.
*   **Security**: All inbound webhooks are secured using HMAC-SHA256 signatures.

## Configuration

To connect a supply chain provider (like WeFlourish or others), add an entry to `config/integration_config.json`:

```json
{
  "providers": {
    "weflourish_main": {
      "provider_type": "supply_chain",
      "api_url": "https://api.weflourish.com/api/ohm/bids",
      "api_key": "your-api-key-here",
      "webhook_secret": "your-shared-secret-here",
      "use_secrets": true,
      "secret_key_env": "WEFLOURISH_API_KEY"
    }
  }
}
```

*   `api_url`: The full endpoint URL where RFQs should be sent via POST.
*   `webhook_secret`: Shared secret used to verify incoming webhook signatures.

## API Usage

### creating an RFQ

**POST** `/v1/api/rfq/`

Triggers the creation of an RFQ and broadcasts it to all active `supply_chain` providers.

**Request Payload:**
```json
{
  "project_name": "Project Alpha",
  "description": "Prototype chassis manufacturing",
  "capabilities": ["cnc-milling", "anodizing"],
  "callback_url": "https://ohm.example.com/v1/api/rfq/webhooks"
}
```

**Response:**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "open",
  ...
}
```

### Webhooks (Inbound)

External providers should send updates to the configured `callback_url` (or base webhook endpoints).

**Security Requirement:**
All webhook requests must include the `X-OHM-Signature` header containing the HMAC-SHA256 signature of the request body, signed with the `webhook_secret`.

#### Receiving a Quote

**POST** `/v1/api/rfq/webhooks/quotes`

**Payload:**
```json
{
  "rfq_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "provider_id": "weflourish_main",
  "amount": 1500.00,
  "currency": "USD",
  "items": [
    {
      "description": "CNC Machining",
      "quantity": 1,
      "unit_price": 1500.00,
      "total_price": 1500.00
    }
  ]
}
```

#### Updating Status

**POST** `/v1/api/rfq/webhooks/status`

**Payload:**
```json
{
  "rfq_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "new_status": "filled"
}
```
