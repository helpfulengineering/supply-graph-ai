#!/usr/bin/env python3
"""
Test script for matching endpoint on localhost.
Tests the logging improvements and okh_id parsing.
"""

import json
import requests
from uuid import UUID

# Configuration
LOCAL_URL = "http://localhost:8001"

def test_match_with_okh_id(okh_id: str):
    """Test matching endpoint with okh_id"""
    url = f"{LOCAL_URL}/v1/api/match"
    
    # Test with UUID string
    data = {
        "okh_id": okh_id,
        "domain": "manufacturing",
        "min_confidence": 0.3,
        "max_results": 10
    }
    
    print(f"\n{'='*80}")
    print(f"Testing match endpoint with okh_id")
    print(f"{'='*80}")
    print(f"URL: {url}")
    print(f"Request data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, json=data, timeout=30)
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"Response Body: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Body (text): {response.text[:500]}")
        
        return response.status_code, response.json() if response.headers.get('content-type', '').startswith('application/json') else {"text": response.text}
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None, None


def test_match_with_okh_id_uuid_object():
    """Test with UUID object (to see if that's the issue)"""
    url = f"{LOCAL_URL}/v1/api/match"
    
    # Test with a valid UUID
    test_uuid = "03350356-09f8-41b4-a7c1-aba5df2ac93e"
    
    data = {
        "okh_id": test_uuid,
        "domain": "manufacturing",
    }
    
    print(f"\n{'='*80}")
    print(f"Testing match endpoint with UUID string")
    print(f"{'='*80}")
    print(f"URL: {url}")
    print(f"Request data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, json=data, timeout=30)
        
        print(f"\nStatus Code: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"Response Body: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Body (text): {response.text[:500]}")
        
        return response.status_code, response.json() if response.headers.get('content-type', '').startswith('application/json') else {"text": response.text}
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None, None


def test_health():
    """Test health endpoint to verify server is running"""
    url = f"{LOCAL_URL}/health"
    
    try:
        response = requests.get(url, timeout=5)
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Server is running")
            return True
        else:
            print(f"⚠️  Server returned {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Server not reachable: {e}")
        return False


def list_okh_manifests():
    """List OKH manifests to find one that exists"""
    url = f"{LOCAL_URL}/v1/api/okh?page=1&page_size=10"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            if items:
                print(f"\n✅ Found {len(items)} OKH manifests:")
                for i, item in enumerate(items[:5], 1):  # Show first 5
                    okh_id = item.get("id", "unknown")
                    title = item.get("title", "No title")
                    print(f"   {i}. {okh_id} - {title}")
                return [item.get("id") for item in items if item.get("id")]
            else:
                print(f"\n⚠️  No OKH manifests found in storage")
                return []
        else:
            print(f"\n⚠️  Failed to list OKH manifests: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Failed to list OKH manifests: {e}")
        return []


if __name__ == "__main__":
    print("=" * 80)
    print("Local Match Endpoint Testing")
    print("=" * 80)
    
    # Test health first
    if not test_health():
        print("\n❌ Server is not running. Please start the server first.")
        exit(1)
    
    # List OKH manifests to find one that exists
    okh_ids = list_okh_manifests()
    
    if okh_ids:
        # Test with an existing OKH ID
        test_uuid = okh_ids[0]
        print(f"\n🎯 Testing with existing OKH ID: {test_uuid}")
        status, response = test_match_with_okh_id(test_uuid)
    else:
        # Fallback to test UUID (will get 404, but that's expected)
        test_uuid = "03350356-09f8-41b4-a7c1-aba5df2ac93e"
        print(f"\n⚠️  No OKH manifests found, testing with non-existent ID (will get 404)")
        status, response = test_match_with_okh_id(test_uuid)
    
    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)
    print(f"\nNext steps:")
    print(f"1. Check the server logs for the new debug logging")
    print(f"2. Look for 'Extracting OKH manifest from request' messages")
    print(f"3. Check if okh_id is being parsed correctly")

