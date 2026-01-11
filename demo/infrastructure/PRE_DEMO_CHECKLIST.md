# Pre-Demo Validation Checklist

This checklist ensures all systems are ready before the demo. Complete all items in each section before proceeding with the demonstration.

**Recommended Timeline:**
- **24 hours before demo**: Complete full checklist
- **2 hours before demo**: Quick verification (marked with ⚡)
- **30 minutes before demo**: Final spot checks (marked with 🔴)

---

## 1. Cloud Run Deployment

### 1.1 Accessibility Verification

- [ ] **1.1.1**: Cloud Run deployment is accessible from demo location
  - **Command**: `python -m demo.infrastructure.verify_deployment`
  - **Expected**: All endpoints return 200 OK
  - **Acceptable**: Health endpoint 200 OK, others may have acceptable errors
  - **⚠️ Critical**: Must pass 24 hours before demo

- [ ] **1.1.2**: Public access is configured (no authentication required)
  - **Command**: `python -m demo.infrastructure.verify_deployment`
  - **Check**: No "requires authentication" warnings
  - **Verify**: `curl https://supply-graph-ai-1085931013579.us-west1.run.app/health` returns 200
  - **⚠️ Critical**: Must pass 24 hours before demo

- [ ] **1.1.3**: Network latency is acceptable
  - **Command**: `python -m demo.infrastructure.verify_deployment`
  - **Expected**: Health endpoint < 200ms, Match endpoint < 3s
  - **Acceptable**: Health < 500ms, Match < 5s
  - **⚠️ Critical**: Must pass 24 hours before demo

### 1.2 API Endpoint Health

- [ ] **1.2.1**: Health endpoint responds correctly
  - **Command**: `curl https://supply-graph-ai-1085931013579.us-west1.run.app/health`
  - **Expected**: `{"status":"ok","domains":["cooking","manufacturing"],"version":"1.0.0"}`
  - **Status**: ⚡ Quick check (2 hours before)

- [ ] **1.2.2**: Match endpoint is accessible
  - **Command**: `python -m demo.infrastructure.verify_deployment`
  - **Expected**: Status 200 or 422 (validation error is acceptable)
  - **Status**: ⚡ Quick check (2 hours before)

- [ ] **1.2.3**: OKH endpoint is accessible
  - **Command**: `curl "https://supply-graph-ai-1085931013579.us-west1.run.app/v1/api/okh?page=1&page_size=1"`
  - **Expected**: Status 200 with JSON response
  - **Status**: ⚡ Quick check (2 hours before)

- [ ] **1.2.4**: OKW endpoint is accessible
  - **Command**: `curl "https://supply-graph-ai-1085931013579.us-west1.run.app/v1/api/okw/search?page=1&page_size=1"`
  - **Expected**: Status 200 with JSON response (or timeout if no data)
  - **Status**: ⚡ Quick check (2 hours before)

### 1.3 Performance Verification

- [ ] **1.3.1**: Match endpoint responds within acceptable time
  - **Command**: `python -m demo.infrastructure.verify_deployment`
  - **Expected**: Latency < 3 seconds
  - **Acceptable**: Latency < 10 seconds (with warning)
  - **⚠️ Critical**: Must pass 24 hours before demo

- [ ] **1.3.2**: Concurrent request handling works
  - **Command**: Run 5 simultaneous health checks
  - **Expected**: All requests succeed
  - **Test**: `for i in {1..5}; do curl -s https://supply-graph-ai-1085931013579.us-west1.run.app/health & done; wait`
  - **Status**: ⚡ Quick check (2 hours before)

---

## 2. Demo Data Availability

### 2.1 OKH Data

- [ ] **2.1.1**: Primary OKH design is loaded and accessible
  - **Command**: `curl "https://supply-graph-ai-1085931013579.us-west1.run.app/v1/api/okh?page=1&page_size=10"`
  - **Expected**: At least 1 OKH manifest in response
  - **Verify**: Check that primary design (e.g., IoT Sensor Network Hub) is present
  - **⚠️ Critical**: Must pass 24 hours before demo

- [ ] **2.1.2**: OKH design has nested components
  - **Manual**: Review OKH manifest structure
  - **Expected**: Nested components with depth 2-4
  - **Verify**: Check component hierarchy in response
  - **Status**: ⚡ Quick check (2 hours before)

- [ ] **2.1.3**: OKH design is relatable/appropriate for demo
  - **Manual**: Review OKH manifest title and description
  - **Expected**: Clear, relatable product (medical device, PPE, etc.)
  - **Status**: ⚡ Quick check (2 hours before)

### 2.2 OKW Data

- [ ] **2.2.1**: OKW facilities are loaded and accessible
  - **Command**: `curl "https://supply-graph-ai-1085931013579.us-west1.run.app/v1/api/okw/search?page=1&page_size=10"`
  - **Expected**: At least 20-50 facilities in response
  - **⚠️ Critical**: Must pass 24 hours before demo

- [ ] **2.2.2**: Facilities demonstrate multi-facility matching
  - **Manual**: Review facility capabilities
  - **Expected**: No single facility can complete entire product
  - **Verify**: Test matching with primary OKH design
  - **Status**: ⚡ Quick check (2 hours before)

- [ ] **2.2.3**: Facilities show diverse capabilities
  - **Manual**: Review facility types and capabilities
  - **Expected**: Mix of exact, heuristic, and NLP matching opportunities
  - **Status**: ⚡ Quick check (2 hours before)

### 2.3 Data Quality

- [ ] **2.3.1**: Data is realistic (not obviously synthetic)
  - **Manual**: Review sample OKH and OKW entries
  - **Expected**: Realistic names, descriptions, capabilities
  - **Status**: ⚡ Quick check (2 hours before)

- [ ] **2.3.2**: Data matches demo requirements
  - **Manual**: Cross-reference with demo script requirements
  - **Expected**: All required data elements present
  - **Status**: ⚡ Quick check (2 hours before)

---

## 3. Backup Deployment

### 3.1 Local Docker Deployment

- [ ] **3.1.1**: Local Docker deployment is ready
  - **Command**: `docker-compose ps`
  - **Expected**: `ohm-api` service is running
  - **Status**: ⚡ Quick check (2 hours before)

- [ ] **3.1.2**: Local deployment endpoints are accessible
  - **Command**: `python -m demo.infrastructure.verify_local_deployment`
  - **Expected**: All endpoints return 200 OK (or acceptable errors)
  - **Status**: ⚡ Quick check (2 hours before)

- [ ] **3.1.3**: Local deployment has demo data loaded
  - **Command**: `curl "http://localhost:8001/v1/api/okh?page=1&page_size=1"`
  - **Expected**: At least 1 OKH manifest in response
  - **Note**: If not loaded, follow `BACKUP_DEPLOYMENT.md` data loading procedure
  - **Status**: ⚡ Quick check (2 hours before)

### 3.2 Backup Readiness

- [ ] **3.2.1**: Backup deployment tested end-to-end
  - **Manual**: Run full demo workflow on backup
  - **Expected**: All demo steps complete successfully
  - **⚠️ Critical**: Must pass 24 hours before demo

- [ ] **3.2.2**: Backup switch procedure is documented and understood
  - **Manual**: Review `BACKUP_DEPLOYMENT.md`
  - **Expected**: Clear understanding of how to switch to backup
  - **Status**: ⚡ Quick check (2 hours before)

- [ ] **3.2.3**: Backup URL is ready for demo interface
  - **Manual**: Note backup URL: `http://localhost:8001`
  - **Expected**: URL configured in demo interface (if applicable)
  - **Status**: 🔴 Final check (30 minutes before)

---

## 4. Network Connectivity

### 4.1 Demo Location Network

- [ ] **4.1.1**: Internet connectivity is available
  - **Command**: `ping -c 3 8.8.8.8`
  - **Expected**: All packets received
  - **Status**: 🔴 Final check (30 minutes before)

- [ ] **4.1.2**: Cloud Run is accessible from demo location
  - **Command**: `curl -I https://supply-graph-ai-1085931013579.us-west1.run.app/health`
  - **Expected**: HTTP 200 response
  - **Status**: 🔴 Final check (30 minutes before)

- [ ] **4.1.3**: Network latency is acceptable from demo location
  - **Command**: `python -m demo.infrastructure.verify_deployment`
  - **Expected**: Health endpoint < 500ms
  - **Acceptable**: Health endpoint < 1000ms
  - **Status**: 🔴 Final check (30 minutes before)

### 4.2 Firewall and Security

- [ ] **4.2.1**: No firewall blocking Cloud Run access
  - **Command**: `curl https://supply-graph-ai-1085931013579.us-west1.run.app/health`
  - **Expected**: Successful connection
  - **Status**: 🔴 Final check (30 minutes before)

- [ ] **4.2.2**: VPN/proxy settings are configured (if needed)
  - **Manual**: Verify network configuration
  - **Expected**: Cloud Run accessible through VPN/proxy
  - **Status**: 🔴 Final check (30 minutes before)

---

## 5. Demo Interface

### 5.1 Interface Configuration

- [ ] **5.1.1**: Demo interface is configured with correct API URL
  - **Manual**: Check interface configuration
  - **Expected**: Points to Cloud Run URL (or backup if needed)
  - **Status**: 🔴 Final check (30 minutes before)

- [ ] **5.1.2**: Demo interface can connect to API
  - **Manual**: Test connection from interface
  - **Expected**: Successful API connection
  - **Status**: 🔴 Final check (30 minutes before)

- [ ] **5.1.3**: Demo interface displays correctly
  - **Manual**: Visual check of interface
  - **Expected**: All UI elements render correctly
  - **Status**: 🔴 Final check (30 minutes before)

### 5.2 Demo Workflow

- [ ] **5.2.1**: Demo workflow is tested end-to-end
  - **Manual**: Run through complete demo workflow
  - **Expected**: All steps complete successfully
  - **⚠️ Critical**: Must pass 24 hours before demo

- [ ] **5.2.2**: Demo data loads correctly in interface
  - **Manual**: Test loading OKH and OKW data
  - **Expected**: Data displays correctly
  - **Status**: ⚡ Quick check (2 hours before)

- [ ] **5.2.3**: Matching workflow functions correctly
  - **Manual**: Test matching with demo OKH design
  - **Expected**: Supply tree solution generated and displayed
  - **Status**: ⚡ Quick check (2 hours before)

---

## 6. Error Handling & Recovery

### 6.1 Error Scenarios

- [ ] **6.1.1**: API error handling is graceful
  - **Manual**: Test with invalid requests
  - **Expected**: Error messages are clear and helpful
  - **Status**: ⚡ Quick check (2 hours before)

- [ ] **6.1.2**: Network error handling works
  - **Manual**: Test with network interruption simulation
  - **Expected**: Interface handles errors gracefully
  - **Status**: ⚡ Quick check (2 hours before)

- [ ] **6.1.3**: Backup switch procedure is tested
  - **Manual**: Simulate primary failure and switch to backup
  - **Expected**: Smooth transition to backup
  - **⚠️ Critical**: Must pass 24 hours before demo

### 6.2 Recovery Procedures

- [ ] **6.2.1**: Recovery procedures are documented
  - **Manual**: Review recovery documentation
  - **Expected**: Clear steps for common issues
  - **Status**: ⚡ Quick check (2 hours before)

- [ ] **6.2.2**: Recovery procedures are understood
  - **Manual**: Review and understand recovery steps
  - **Expected**: Can execute recovery procedures
  - **Status**: ⚡ Quick check (2 hours before)

---

## 7. Final Pre-Demo Checks (30 Minutes Before)

### 7.1 Quick Verification

- [ ] **7.1.1**: Cloud Run health check passes
  - **Command**: `python -m demo.infrastructure.verify_deployment`
  - **Expected**: All endpoints accessible
  - **Status**: 🔴 Final check

- [ ] **7.1.2**: Demo data is accessible
  - **Command**: Quick curl to OKH and OKW endpoints
  - **Expected**: Data returns successfully
  - **Status**: 🔴 Final check

- [ ] **7.1.3**: Demo interface is ready
  - **Manual**: Visual check and quick test
  - **Expected**: Interface loads and connects
  - **Status**: 🔴 Final check

### 7.2 Backup Readiness

- [ ] **7.2.1**: Backup deployment is running (if needed)
  - **Command**: `docker-compose ps`
  - **Expected**: Services running (if using backup)
  - **Status**: 🔴 Final check

- [ ] **7.2.2**: Backup URL is noted
  - **Manual**: Note backup URL for quick reference
  - **Expected**: `http://localhost:8001` (or configured URL)
  - **Status**: 🔴 Final check

---

## 8. During Demo

### 8.1 Monitoring

- [ ] **8.1.1**: Monitor API health during demo
  - **Tool**: Keep verification script ready
  - **Action**: Run if issues occur
  - **Status**: During demo

- [ ] **8.1.2**: Monitor network connectivity
  - **Tool**: Keep ping/curl ready
  - **Action**: Test if connection issues occur
  - **Status**: During demo

### 8.2 Quick Recovery

- [ ] **8.2.1**: Know how to switch to backup
  - **Action**: Review `BACKUP_DEPLOYMENT.md` quick reference
  - **Expected**: Can switch within 2 minutes
  - **Status**: During demo

- [ ] **8.2.2**: Have backup URL ready
  - **Action**: Note backup URL: `http://localhost:8001`
  - **Expected**: Can update interface quickly
  - **Status**: During demo

---

## Quick Reference Commands

### Cloud Run Verification
```bash
# Full verification
python -m demo.infrastructure.verify_deployment

# Quick health check
curl https://supply-graph-ai-1085931013579.us-west1.run.app/health

# Check OKH data
curl "https://supply-graph-ai-1085931013579.us-west1.run.app/v1/api/okh?page=1&page_size=1"

# Check OKW data
curl "https://supply-graph-ai-1085931013579.us-west1.run.app/v1/api/okw/search?page=1&page_size=1"
```

### Local Deployment Verification
```bash
# Full verification
python -m demo.infrastructure.verify_local_deployment

# Quick health check
curl http://localhost:8001/health

# Check service status
docker-compose ps

# View logs
docker-compose logs -f ohm-api
```

### Network Testing
```bash
# Test connectivity
ping -c 3 8.8.8.8

# Test Cloud Run connectivity
curl -I https://supply-graph-ai-1085931013579.us-west1.run.app/health

# Test latency
time curl -s https://supply-graph-ai-1085931013579.us-west1.run.app/health
```

---

## Checklist Status Legend

- **⚠️ Critical**: Must pass 24 hours before demo
- **⚡ Quick check**: Verify 2 hours before demo
- **🔴 Final check**: Verify 30 minutes before demo
- **During demo**: Monitor during actual demonstration

---

## Troubleshooting Quick Reference

### Cloud Run Not Accessible
1. Check public access: `python -m demo.infrastructure.configure_public_access --check`
2. Verify deployment: `gcloud run services describe supply-graph-ai --region us-west1`
3. Check logs: `gcloud run services logs read supply-graph-ai --region us-west1`

### API Endpoints Slow
1. Check latency: `python -m demo.infrastructure.verify_deployment`
2. Review Cloud Run metrics in GCP console
3. Consider switching to backup if latency > 10s

### Demo Data Not Available
1. Verify data loading: Check OKH/OKW endpoints
2. Reload data if needed (follow data loading procedure)
3. Switch to backup if primary unavailable

### Network Issues
1. Test connectivity: `ping 8.8.8.8`
2. Check firewall/VPN settings
3. Switch to local backup if network issues persist

### Backup Deployment Issues
1. Check service status: `docker-compose ps`
2. View logs: `docker-compose logs ohm-api`
3. Restart if needed: `docker-compose restart ohm-api`
4. See `BACKUP_DEPLOYMENT.md` for detailed troubleshooting

---

## Success Criteria

**Before Demo:**
- ✅ All ⚠️ Critical items completed
- ✅ All ⚡ Quick check items verified
- ✅ All 🔴 Final check items confirmed
- ✅ Backup deployment ready and tested
- ✅ Demo workflow tested end-to-end

**During Demo:**
- ✅ API remains accessible
- ✅ Network connectivity stable
- ✅ Demo interface functions correctly
- ✅ Backup available if needed

---

## Notes

- **Last Updated**: December 2024
- **Maintained By**: Demo Infrastructure Team
- **Related Documents**:
  - `BACKUP_DEPLOYMENT.md` - Backup deployment runbook
  - `PUBLIC_ACCESS.md` - Public access configuration
  - `README.md` - Infrastructure verification overview
