#!/usr/bin/env python3
"""
Direct testing script for Cloud Run service endpoints.
This script sends requests directly to the deployed service and helps debug 500 errors.
"""

import os
import sys
import json
import subprocess
import requests
from typing import Optional, Dict, Any

# Configuration
SERVICE_URL = os.getenv("SERVICE_URL", "https://supply-graph-ai-1085931013579.us-west1.run.app")
USE_AUTH = os.getenv("USE_AUTH", "true").lower() == "true"


def get_auth_token() -> Optional[str]:
    """Get GCP identity token for authentication with correct audience"""
    if not USE_AUTH:
        return None
    
    # Check for explicit token
    token = os.getenv("IDENTITY_TOKEN")
    if token:
        print("✓ Using IDENTITY_TOKEN from environment")
        return token
    
    # For Cloud Run with --no-allow-unauthenticated, we need a token with the service URL as audience
    # User accounts can't use --audiences directly, so we need to impersonate the service account
    service_account = "supply-graph-ai@nathan-playground-368310.iam.gserviceaccount.com"
    
    try:
        # Method 1: Try service account impersonation with audience (best for Cloud Run)
        try:
            result = subprocess.run(
                [
                    "gcloud", "auth", "print-identity-token",
                    "--impersonate-service-account", service_account,
                    "--audiences", SERVICE_URL
                ],
                capture_output=True,
                text=True,
                check=True
            )
            token = result.stdout.strip()
            if token:
                print(f"✓ Using service account impersonation token with audience={SERVICE_URL}")
                return token
        except subprocess.CalledProcessError as e:
            if "PERMISSION_DENIED" in e.stderr or "does not have permission" in e.stderr:
                print(f"⚠ Service account impersonation failed: {e.stderr.strip()}")
                print(f"\nTo fix this, grant yourself permission to impersonate the service account:")
                print(f"  gcloud iam service-accounts add-iam-policy-binding {service_account} \\")
                print(f"    --member='user:$(gcloud config get-value account)' \\")
                print(f"    --role='roles/iam.serviceAccountTokenCreator'")
            # Continue to fallback methods
        
        # Method 2: Try regular user account token (may not work but worth trying)
        result = subprocess.run(
            ["gcloud", "auth", "print-identity-token"],
            capture_output=True,
            text=True,
            check=True
        )
        token = result.stdout.strip()
        if token:
            print("⚠ Using user account token (may not work for Cloud Run)")
            print(f"  This token may be rejected. Consider using service account impersonation.")
            return token
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"⚠ Failed to get GCP identity token: {e}")
        print(f"\nTo get a valid token:")
        print(f"  1. Grant yourself permission to impersonate the service account:")
        print(f"     gcloud iam service-accounts add-iam-policy-binding {service_account} \\")
        print(f"       --member='user:$(gcloud config get-value account)' \\")
        print(f"       --role='roles/iam.serviceAccountTokenCreator'")
        print(f"  2. Then run this script again")
    
    return None


def make_request(method: str, endpoint: str, data: Optional[Dict[Any, Any]] = None, headers: Optional[Dict[str, str]] = None) -> requests.Response:
    """Make a request to the Cloud Run service"""
    url = f"{SERVICE_URL}{endpoint}"
    
    if headers is None:
        headers = {}
    
    # Add authentication
    if USE_AUTH:
        token = get_auth_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    
    headers["Content-Type"] = "application/json"
    
    print(f"\n{'='*80}")
    print(f"{method} {endpoint}")
    print(f"{'='*80}")
    print(f"URL: {url}")
    if data:
        print(f"Request data: {json.dumps(data, indent=2)[:500]}...")  # Truncate long data
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=120)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=120)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"Response Body: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Body (text): {response.text[:1000]}")
        
        return response
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        raise


def test_create_okh():
    """Test creating an OKH manifest"""
    print("\n" + "="*80)
    print("TEST: Create OKH Manifest")
    print("="*80)
    
    okh_data = {
        "title": "Test Hardware Module",
        "version": "1.0.0",
        "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        "licensor": "Test Organization",
        "documentation_language": "en",
        "function": "Test hardware module for debugging",
        "repo": "https://github.com/test/test-hardware",  # Required field
        "description": "A test hardware module for debugging create operations",
        "keywords": ["test", "debugging"]
    }
    
    response = make_request("POST", "/v1/api/okh/create", data=okh_data)
    
    if response.status_code == 201:
        print("\n✅ OKH created successfully!")
        data = response.json()
        if "id" in data:
            return data["id"]
    elif response.status_code == 500:
        print("\n❌ 500 Error - Check Cloud Logging for details")
        print("\nTo view logs, run:")
        print(f"  gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=supply-graph-ai AND textPayload=~\"Error\"' --limit 50 --format json")
    else:
        print(f"\n⚠ Unexpected status code: {response.status_code}")
    
    return None


def test_create_okw():
    """Test creating an OKW facility"""
    print("\n" + "="*80)
    print("TEST: Create OKW Facility")
    print("="*80)
    
    okw_data = {
        "name": "Test Manufacturing Facility",
        "facility_status": "Active",
        "access_type": "Public",
        "location": {
            "address": {
                "street": "123 Test St",
                "city": "Test City",
                "region": "Test Region",
                "country": "US",
                "postcode": "12345"
            }
        },
        "typical_materials": [
            {"name": "PLA"},
            {"name": "ABS"}
        ]
    }
    
    response = make_request("POST", "/v1/api/okw/create", data=okw_data)
    
    if response.status_code == 201:
        print("\n✅ OKW facility created successfully!")
        data = response.json()
        if "id" in data:
            return data["id"]
    elif response.status_code == 500:
        print("\n❌ 500 Error - Check Cloud Logging for details")
        print("\nTo view logs, run:")
        print(f"  gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=supply-graph-ai AND textPayload=~\"Error\"' --limit 50 --format json")
    else:
        print(f"\n⚠ Unexpected status code: {response.status_code}")
    
    return None


def test_match_okh_to_okw(okh_id: str):
    """Test matching an OKH manifest to OKW facilities"""
    print("\n" + "="*80)
    print("TEST: Match OKH to OKW")
    print("="*80)
    
    match_data = {
        "okh_id": okh_id,
        "domain": "manufacturing",
        "optimization_criteria": {
            "cost": 0.5,
            "time": 0.3,
            "quality": 0.2
        },
        "min_confidence": 0.3,
        "max_results": 10
    }
    
    response = make_request("POST", "/v1/api/match", data=match_data)
    
    if response.status_code == 200:
        print("\n✅ Match operation successful!")
        data = response.json()
        # Match response structure may vary
        if isinstance(data, dict):
            matches = data.get('matches', data.get('data', data.get('items', [])))
            if isinstance(matches, list):
                print(f"Found {len(matches)} matches")
            else:
                print(f"Match response: {list(data.keys())}")
        else:
            print(f"Match response type: {type(data)}")
    elif response.status_code == 500:
        print("\n❌ 500 Error - Check Cloud Logging for details")
        print("\nTo view logs, run:")
        print(f"  gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=supply-graph-ai AND textPayload=~\"Error\"' --limit 50 --format json")
    else:
        print(f"\n⚠ Unexpected status code: {response.status_code}")
    
    return response


def test_list_okh():
    """Test listing OKH manifests"""
    print("\n" + "="*80)
    print("TEST: List OKH Manifests")
    print("="*80)
    
    response = make_request("GET", "/v1/api/okh?page=1&page_size=10")
    
    if response.status_code == 200:
        print("\n✅ List OKH successful!")
        data = response.json()
        if isinstance(data, dict) and "items" in data:
            print(f"Found {len(data['items'])} manifests")
        elif isinstance(data, list):
            print(f"Found {len(data)} manifests")
    elif response.status_code in [500, 503]:
        print(f"\n❌ {response.status_code} Error - Check Cloud Logging for details")
    else:
        print(f"\n⚠ Unexpected status code: {response.status_code}")
    
    return response


def show_log_commands():
    """Show commands to check Cloud Run logs"""
    print("\n" + "="*80)
    print("CLOUD LOGGING COMMANDS")
    print("="*80)
    print("\nTo view recent errors:")
    print("  gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=supply-graph-ai AND severity>=ERROR' --limit 50 --format json")
    print("\nTo view all recent logs:")
    print("  gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=supply-graph-ai' --limit 100 --format json")
    print("\nTo view logs with specific error text:")
    print("  gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=supply-graph-ai AND textPayload=~\"TypeError\"' --limit 50 --format json")
    print("\nTo view logs in real-time:")
    print("  gcloud logging tail 'resource.type=cloud_run_revision AND resource.labels.service_name=supply-graph-ai' --format json")


def main():
    """Run all tests"""
    print("="*80)
    print("Cloud Run Direct Testing Script")
    print("="*80)
    print(f"Service URL: {SERVICE_URL}")
    print(f"Use Auth: {USE_AUTH}")
    
    # Test list OKH first (to see if storage is working)
    test_list_okh()
    
    # Test create operations
    okh_id = test_create_okh()
    okw_id = test_create_okw()
    
    # Test matching if we have an OKH ID
    if okh_id:
        test_match_okh_to_okw(okh_id)
    else:
        print("\n⚠ Skipping match test - no OKH ID available")
    
    # Show log commands
    show_log_commands()
    
    print("\n" + "="*80)
    print("Testing Complete")
    print("="*80)
    print("\nNext steps:")
    print("1. Review the responses above for any 500 errors")
    print("2. Run the Cloud Logging commands to see detailed error messages")
    print("3. Fix any issues found in the logs")


if __name__ == "__main__":
    main()

