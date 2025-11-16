"""
Temporary script to reproduce the 500 error when creating a supply tree.
This will help us trace the error through server logs.
"""
import asyncio
import httpx
import json
import sys
from pathlib import Path

async def reproduce_error():
    """Reproduce the 500 error step by step"""
    base_url = "http://localhost:8001/v1"
    
    async with httpx.AsyncClient(base_url=base_url, timeout=60.0, follow_redirects=True) as client:
        print("=" * 80)
        print("STEP 1: Reading OKH file")
        print("=" * 80)
        
        okh_file_path = Path("synth/synthetic-data/arduino-based-iot-sensor-node-1-9-0-okh.json")
        if not okh_file_path.exists():
            print(f"ERROR: OKH file not found at {okh_file_path}")
            return
        
        with open(okh_file_path, 'r') as f:
            okh_data = json.load(f)
        
        print(f"✓ OKH file loaded: {okh_data.get('title', 'Unknown')}")
        print(f"  OKH ID: {okh_data.get('id', 'Unknown')}")
        
        print("\n" + "=" * 80)
        print("STEP 2: Running match to get facility and tree data")
        print("=" * 80)
        
        match_data = {"okh_manifest": okh_data}
        try:
            match_response = await client.post("/api/match", json=match_data, timeout=60.0)
            print(f"Match API status: {match_response.status_code}")
            
            if match_response.status_code != 200:
                print(f"ERROR: Match failed: {match_response.text[:500]}")
                return
            
            match_result = match_response.json()
            data = match_result.get("data", {})
            solutions = data.get("solutions", [])
            
            if not solutions:
                print("ERROR: No solutions returned from match")
                return
            
            print(f"✓ Match successful: {len(solutions)} solutions found")
            
            first_solution = solutions[0]
            tree = first_solution.get("tree", {})
            facility_id = first_solution.get("facility_id")
            
            print(f"  Tree ID: {tree.get('id')}")
            print(f"  Facility ID: {facility_id}")
            print(f"  Facility Name: {tree.get('facility_name', 'Unknown')}")
            print(f"  OKH Reference: {tree.get('okh_reference', 'Unknown')}")
            print(f"  Confidence Score: {tree.get('confidence_score', 'Unknown')}")
            
        except Exception as e:
            print(f"ERROR in match step: {e}")
            import traceback
            traceback.print_exc()
            return
        
        print("\n" + "=" * 80)
        print("STEP 3: Creating supply tree via create endpoint")
        print("=" * 80)
        
        if not facility_id:
            print("ERROR: No facility_id found in solution")
            return
        
        create_data = {
            "facility_id": str(facility_id),
            "facility_name": tree.get("facility_name", "Test Facility"),
            "okh_reference": tree.get("okh_reference") or okh_data.get("id") or "test-reference",
            "confidence_score": tree.get("confidence_score", 0.85),
            "estimated_cost": tree.get("estimated_cost"),
            "estimated_time": tree.get("estimated_time"),
            "materials_required": tree.get("materials_required", []),
            "capabilities_used": tree.get("capabilities_used", []),
            "match_type": tree.get("match_type", "direct"),
            "metadata": tree.get("metadata", {})
        }
        
        print("Request payload:")
        print(json.dumps(create_data, indent=2))
        
        try:
            print("\nSending POST request to /api/supply-tree/create...")
            create_response = await client.post("/api/supply-tree/create", json=create_data)
            
            print(f"\nResponse status: {create_response.status_code}")
            print(f"Response headers: {dict(create_response.headers)}")
            
            if create_response.status_code == 201:
                result = create_response.json()
                print("✓ SUCCESS! Supply tree created")
                print(f"  Created tree ID: {result.get('data', {}).get('id', 'Unknown')}")
            else:
                print(f"\n✗ ERROR: Status {create_response.status_code}")
                print("\nResponse body:")
                try:
                    error_data = create_response.json()
                    print(json.dumps(error_data, indent=2))
                except:
                    print(create_response.text)
                
                # Print full response for debugging
                print(f"\nFull response text (first 2000 chars):")
                print(create_response.text[:2000])
                
        except httpx.ReadError as e:
            print(f"ERROR: ReadError - {e}")
            print("This might indicate a connection issue or server crash")
        except Exception as e:
            print(f"ERROR: Exception during create: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("REPRODUCING 500 ERROR - Check server logs for detailed error trace")
    print("=" * 80 + "\n")
    
    asyncio.run(reproduce_error())
    
    print("\n" + "=" * 80)
    print("Test completed. Please check server logs for the error trace.")
    print("=" * 80)

