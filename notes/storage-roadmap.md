# Storage & Matching Endpoint Roadmap

## Goal
Enable a minimal, functioning matching endpoint for the frontend team, using a provider-agnostic storage system.

---

## 1. Implement and Register Domain Handlers
- [ ] Implement `OKHStorageHandler` (subclass `DomainStorageHandler`)
- [ ] Implement `OKWStorageHandler` (subclass `DomainStorageHandler`)
- [ ] Register both handlers with `StorageRegistry`
- [ ] Ensure correct serialization/deserialization for `OKHManifest` and `ManufacturingFacility`

---

## 2. Validate StorageService Integration
- [ ] Ensure `StorageService` is configured at app startup (with Azure or chosen provider)
- [ ] All storage access in endpoints/services goes through domain handlers (no direct provider access)

---

## 3. Minimal Data Validation
- [x] OKH manifest validation in endpoint
- [ ] (Optional) OKW facility validation in handler or during loading

---

## 4. End-to-End Test the Matching Endpoint
- [ ] POST a valid OKH manifest to the endpoint
- [ ] Confirm endpoint loads OKW facilities from storage
- [ ] Confirm matching logic runs and returns a valid response
- [ ] Ensure errors are handled gracefully (400 for bad input, 500 for system errors)

---

## 5. Minimal Frontend Contract
- [ ] Document request/response schema for frontend team
- [ ] Provide example payloads and responses
- [ ] Ensure OpenAPI/Swagger docs are accurate

---

## 6. (Optional) Minimal Persistence for OKH
- [ ] Store OKH manifests for audit/history (already in endpoint, but verify)

---

## 7. (Optional) Add Logging and Basic Monitoring
- [x] Ensure logs are written for key events
- [ ] (Optional) Add health check endpoint for storage/matching readiness

---

## Summary Table

| Step                        | Required for MVP | Optional | Status/Notes                |
|-----------------------------|------------------|----------|-----------------------------|
| OKH/OKW domain handlers     | Yes              |          | Implement & register        |
| StorageService integration  | Yes              |          | Use everywhere              |
| OKH validation              | Yes              |          | Already in endpoint         |
| OKW validation              |                  | Yes      | Add if time allows          |
| End-to-end test             | Yes              |          | Manual or automated         |
| Frontend contract/docs      | Yes              |          | Share OpenAPI + examples    |
| OKH persistence             |                  | Yes      | For audit/history           |
| Logging/monitoring          |                  | Yes      | Already present/basic       |

---

## Next Steps
1. Implement and register domain handlers for OKH and OKW.
2. Test the endpoint with real data.
3. Share the endpoint contract with the frontend team.
4. Iterate based on feedback and edge cases.
