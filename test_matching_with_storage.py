#!/usr/bin/env python3
"""
Test script to match OKH manifests from storage against OKW facilities.
This script:
1. Lists OKH manifests from the storage bucket
2. Randomly selects 20 of them
3. Lists all OKW facilities from storage
4. Matches each OKH against all OKW facilities
5. Reports the results
"""

import os
import sys
import json
import subprocess
import requests
import random
from typing import List, Dict, Any, Optional
from datetime import datetime

# Configuration
SERVICE_URL = os.getenv("SERVICE_URL", "https://supply-graph-ai-1085931013579.us-west1.run.app")
USE_AUTH = os.getenv("USE_AUTH", "true").lower() == "true"
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "supply-graph-ai-storage")
OKH_PREFIX = "okh/manifests/"
OKW_PREFIX = "okw/facilities/"


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
        except subprocess.CalledProcessError:
            pass
        
        # Method 2: Try user token (may not work for --no-allow-unauthenticated services)
        result = subprocess.run(
            ["gcloud", "auth", "print-identity-token"],
            capture_output=True,
            text=True,
            check=True
        )
        token = result.stdout.strip()
        if token:
            print("⚠ Using user identity token (may not work for authenticated services)")
            return token
    except subprocess.CalledProcessError as e:
        print(f"⚠ Failed to get identity token: {e.stderr}")
        return None
    
    return None


def list_storage_files(prefix: str) -> List[str]:
    """List files in the storage bucket with the given prefix"""
    print(f"\n📦 Listing files in gs://{STORAGE_BUCKET}/{prefix}...")
    
    try:
        result = subprocess.run(
            [
                "gcloud", "storage", "ls",
                f"gs://{STORAGE_BUCKET}/{prefix}",
                "--recursive"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        files = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        # Extract just the file paths relative to the bucket
        file_paths = []
        for file in files:
            if file.startswith(f"gs://{STORAGE_BUCKET}/"):
                file_path = file[len(f"gs://{STORAGE_BUCKET}/"):]
                if file_path.endswith('.json'):
                    file_paths.append(file_path)
        
        print(f"   Found {len(file_paths)} files")
        return file_paths
    except subprocess.CalledProcessError as e:
        print(f"❌ Error listing files: {e.stderr}")
        return []


def get_okh_id_from_storage_path(storage_path: str) -> Optional[str]:
    """Extract OKH ID from storage path or filename"""
    # Try to extract ID from the path
    # Path format might be: okh/manifests/something-id-okh.json
    filename = storage_path.split('/')[-1]
    # Remove .json extension
    if filename.endswith('.json'):
        filename = filename[:-5]
    # Try to extract UUID or use the filename
    # For now, we'll need to read the file to get the actual ID
    return None


def read_okh_id_from_storage(storage_path: str) -> Optional[str]:
    """Read OKH manifest from storage and extract its ID"""
    try:
        result = subprocess.run(
            [
                "gcloud", "storage", "cat",
                f"gs://{STORAGE_BUCKET}/{storage_path}"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        data = json.loads(result.stdout)
        # Try different possible ID fields
        okh_id = (
            data.get("id") or
            data.get("okh_id") or
            data.get("manifest_id") or
            None
        )
        return okh_id
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        print(f"   ⚠ Could not read ID from {storage_path}: {e}")
        return None


def match_okh_to_okw(okh_id: str, auth_token: Optional[str]) -> Dict[str, Any]:
    """Match an OKH manifest against all OKW facilities"""
    url = f"{SERVICE_URL}/v1/api/match"
    
    headers = {
        "Content-Type": "application/json",
    }
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    # Ensure okh_id is a valid UUID string (Pydantic will parse it)
    data = {
        "okh_id": str(okh_id),  # Ensure it's a string
        "domain": "manufacturing",
        "min_confidence": 0.3,
        "max_results": 50,  # Get more results to see all matches
    }
    
    # Debug: print the request data
    print(f"   📤 Request data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        
        # Debug: Check if it's a validation error
        if response.status_code == 422:
            try:
                error_detail = response.json()
                print(f"   ⚠️  Validation error: {json.dumps(error_detail, indent=2)[:500]}")
            except:
                pass
        
        return {
            "status_code": response.status_code,
            "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else {"error": response.text},
            "success": response.status_code == 200
        }
    except requests.exceptions.RequestException as e:
        return {
            "status_code": 0,
            "response": {"error": str(e)},
            "success": False
        }


def main():
    print("=" * 80)
    print("Matching Test: OKH Manifests from Storage vs OKW Facilities")
    print("=" * 80)
    print(f"Service URL: {SERVICE_URL}")
    print(f"Storage Bucket: {STORAGE_BUCKET}")
    print(f"Use Auth: {USE_AUTH}")
    
    # Get auth token
    auth_token = get_auth_token() if USE_AUTH else None
    
    # List OKH manifests
    okh_files = list_storage_files(OKH_PREFIX)
    if not okh_files:
        print("❌ No OKH files found in storage")
        return 1
    
    # Randomly select 20 OKH files (or all if less than 20)
    num_to_select = min(20, len(okh_files))
    selected_okh_files = random.sample(okh_files, num_to_select)
    print(f"\n🎲 Randomly selected {num_to_select} OKH manifests:")
    for i, file in enumerate(selected_okh_files, 1):
        print(f"   {i}. {file}")
    
    # List OKW facilities
    okw_files = list_storage_files(OKW_PREFIX)
    print(f"\n📋 Found {len(okw_files)} OKW facilities in storage")
    
    # Read OKH IDs from storage files
    print(f"\n📖 Reading OKH IDs from storage files...")
    okh_ids = []
    for okh_file in selected_okh_files:
        okh_id = read_okh_id_from_storage(okh_file)
        if okh_id:
            okh_ids.append((okh_file, okh_id))
            print(f"   ✓ {okh_file} -> {okh_id}")
        else:
            print(f"   ⚠ Skipping {okh_file} (could not read ID)")
    
    # Also try to get OKH IDs from the API list endpoint
    print(f"\n📋 Getting OKH IDs from API list endpoint...")
    try:
        list_url = f"{SERVICE_URL}/v1/api/okh?page=1&page_size=100"
        list_headers = {"Content-Type": "application/json"}
        if auth_token:
            list_headers["Authorization"] = f"Bearer {auth_token}"
        
        list_response = requests.get(list_url, headers=list_headers, timeout=30)
        if list_response.status_code == 200:
            list_data = list_response.json()
            api_okh_ids = []
            for item in list_data.get("items", []):
                if "id" in item:
                    api_okh_ids.append(item["id"])
            print(f"   ✓ Found {len(api_okh_ids)} OKH IDs from API")
            
            # Add API IDs that aren't already in our list
            for api_id in api_okh_ids[:20]:  # Limit to 20 from API
                if not any(api_id == stored_id for _, stored_id in okh_ids):
                    okh_ids.append((f"api:{api_id}", api_id))
                    print(f"   ✓ Added API ID: {api_id}")
        else:
            print(f"   ⚠ API list returned status {list_response.status_code}")
    except Exception as e:
        print(f"   ⚠ Failed to get OKH IDs from API: {e}")
    
    if not okh_ids:
        print("❌ No valid OKH IDs found")
        return 1
    
    # Match each OKH against all OKW facilities
    print(f"\n🔍 Matching {len(okh_ids)} OKH manifests against all OKW facilities...")
    print("=" * 80)
    
    results = []
    total_matches = 0
    
    for i, (okh_file, okh_id) in enumerate(okh_ids, 1):
        print(f"\n[{i}/{len(okh_ids)}] Matching OKH: {okh_id}")
        print(f"   File: {okh_file}")
        
        match_result = match_okh_to_okw(okh_id, auth_token)
        
        if match_result["success"]:
            response_data = match_result["response"]
            solutions = response_data.get("data", {}).get("solutions", [])
            num_matches = len(solutions)
            total_matches += num_matches
            
            print(f"   ✅ Status: {match_result['status_code']}")
            print(f"   📊 Matches found: {num_matches}")
            print(f"   ⏱️  Processing time: {response_data.get('data', {}).get('processing_time', 0):.3f}s")
            
            if num_matches > 0:
                print(f"   🎯 Match types:")
                metrics = response_data.get("data", {}).get("matching_metrics", {})
                for match_type, count in metrics.items():
                    if count > 0:
                        print(f"      - {match_type}: {count}")
                
                # Show top 3 matches
                print(f"   🔝 Top matches:")
                for j, solution in enumerate(solutions[:3], 1):
                    facility_name = solution.get("facility_name", "Unknown")
                    confidence = solution.get("confidence", 0)
                    match_type = solution.get("tree", {}).get("match_type", "unknown")
                    print(f"      {j}. {facility_name} (confidence: {confidence:.2f}, type: {match_type})")
        else:
            print(f"   ❌ Status: {match_result['status_code']}")
            error = match_result["response"].get("error", "Unknown error")
            print(f"   Error: {error[:200]}")
        
        results.append({
            "okh_file": okh_file,
            "okh_id": okh_id,
            "match_result": match_result
        })
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"OKH manifests tested: {len(okh_ids)}")
    print(f"OKW facilities available: {len(okw_files)}")
    print(f"Total matches found: {total_matches}")
    print(f"Average matches per OKH: {total_matches / len(okh_ids):.2f}" if okh_ids else "N/A")
    
    successful_matches = sum(1 for r in results if r["match_result"]["success"])
    print(f"Successful match requests: {successful_matches}/{len(results)}")
    
    # Save detailed results to file
    output_file = f"matching_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            "test_config": {
                "service_url": SERVICE_URL,
                "storage_bucket": STORAGE_BUCKET,
                "okh_files_tested": len(okh_ids),
                "okw_files_available": len(okw_files),
            },
            "results": results,
            "summary": {
                "total_matches": total_matches,
                "successful_requests": successful_matches,
                "failed_requests": len(results) - successful_matches,
            }
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    return 0 if successful_matches == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

