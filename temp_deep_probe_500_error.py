"""
Deep probe to isolate where the 500 error is occurring.
The logs show the supply tree is created successfully, so the error must be
in response serialization, decorators, or validation.
"""
import asyncio
import httpx
import json
import sys
from pathlib import Path
from uuid import UUID

async def probe_error():
    """Probe the error step by step"""
    base_url = "http://localhost:8001/v1"
    
    async with httpx.AsyncClient(base_url=base_url, timeout=60.0, follow_redirects=True) as client:
        print("=" * 80)
        print("PROBE 1: Test with minimal data")
        print("=" * 80)
        
        minimal_data = {
            "facility_id": "7afa1ca2-8c52-4837-b7c2-09172b2f63b1",
            "facility_name": "Test Facility",
            "okh_reference": "test-reference-123",
            "confidence_score": 0.85
        }
        
        try:
            response = await client.post("/api/supply-tree/create", json=minimal_data)
            print(f"Minimal data test: {response.status_code}")
            if response.status_code != 201:
                print(f"Error: {response.text[:500]}")
        except Exception as e:
            print(f"Exception: {e}")
        
        print("\n" + "=" * 80)
        print("PROBE 2: Test with materials_required as empty list")
        print("=" * 80)
        
        data_with_empty_materials = {
            "facility_id": "7afa1ca2-8c52-4837-b7c2-09172b2f63b1",
            "facility_name": "Test Facility",
            "okh_reference": "test-reference-456",
            "confidence_score": 0.85,
            "materials_required": [],
            "capabilities_used": []
        }
        
        try:
            response = await client.post("/api/supply-tree/create", json=data_with_empty_materials)
            print(f"Empty materials test: {response.status_code}")
            if response.status_code != 201:
                print(f"Error: {response.text[:500]}")
        except Exception as e:
            print(f"Exception: {e}")
        
        print("\n" + "=" * 80)
        print("PROBE 3: Test with simple string materials")
        print("=" * 80)
        
        data_with_simple_materials = {
            "facility_id": "7afa1ca2-8c52-4837-b7c2-09172b2f63b1",
            "facility_name": "Test Facility",
            "okh_reference": "test-reference-789",
            "confidence_score": 0.85,
            "materials_required": ["copper", "plastic"],
            "capabilities_used": ["milling", "turning"]
        }
        
        try:
            response = await client.post("/api/supply-tree/create", json=data_with_simple_materials)
            print(f"Simple materials test: {response.status_code}")
            if response.status_code != 201:
                print(f"Error: {response.text[:500]}")
            else:
                result = response.json()
                print(f"Success! Tree ID: {result.get('data', {}).get('id', 'Unknown')}")
        except Exception as e:
            print(f"Exception: {e}")
        
        print("\n" + "=" * 80)
        print("PROBE 4: Test with MaterialSpec string representations (from match)")
        print("=" * 80)
        
        data_with_materialspec_strings = {
            "facility_id": "7afa1ca2-8c52-4837-b7c2-09172b2f63b1",
            "facility_name": "Test Facility",
            "okh_reference": "test-reference-abc",
            "confidence_score": 0.85,
            "materials_required": [
                "MaterialSpec(material_id='Steel', name='Mild Steel', quantity=804.85, unit='kg', notes=None)",
                "MaterialSpec(material_id='Acrylic', name='Acrylic Sheet', quantity=None, unit='m²', notes=None)"
            ],
            "capabilities_used": [
                "https://en.wikipedia.org/wiki/Fused_filament_fabrication",
                "https://en.wikipedia.org/wiki/Laser_cutting"
            ]
        }
        
        try:
            response = await client.post("/api/supply-tree/create", json=data_with_materialspec_strings)
            print(f"MaterialSpec strings test: {response.status_code}")
            if response.status_code != 201:
                print(f"Error: {response.text[:500]}")
                try:
                    error_json = response.json()
                    print(f"Error JSON: {json.dumps(error_json, indent=2)[:1000]}")
                except:
                    pass
        except Exception as e:
            print(f"Exception: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 80)
        print("PROBE 5: Test with full match response data")
        print("=" * 80)
        
        # Read the OKH file
        okh_file_path = Path("synth/synthetic-data/arduino-based-iot-sensor-node-1-9-0-okh.json")
        if okh_file_path.exists():
            with open(okh_file_path, 'r') as f:
                okh_data = json.load(f)
            
            # Run match
            match_data = {"okh_manifest": okh_data}
            match_response = await client.post("/api/match", json=match_data, timeout=60.0)
            
            if match_response.status_code == 200:
                match_result = match_response.json()
                data = match_result.get("data", {})
                solutions = data.get("solutions", [])
                
                if solutions:
                    first_solution = solutions[0]
                    tree = first_solution.get("tree", {})
                    facility_id = first_solution.get("facility_id")
                    
                    if facility_id:
                        # Try with the exact data from match
                        create_data = {
                            "facility_id": str(facility_id),
                            "facility_name": tree.get("facility_name", "Test"),
                            "okh_reference": tree.get("okh_reference") or okh_data.get("id") or "test-reference",
                            "confidence_score": tree.get("confidence_score", 0.85),
                            "estimated_cost": tree.get("estimated_cost"),
                            "estimated_time": tree.get("estimated_time"),
                            "materials_required": tree.get("materials_required", []),
                            "capabilities_used": tree.get("capabilities_used", []),
                            "match_type": tree.get("match_type", "direct"),
                            "metadata": tree.get("metadata", {})
                        }
                        
                        print(f"Testing with match data:")
                        print(f"  materials_required type: {type(create_data['materials_required'])}")
                        print(f"  materials_required length: {len(create_data['materials_required'])}")
                        if create_data['materials_required']:
                            print(f"  First material type: {type(create_data['materials_required'][0])}")
                            print(f"  First material: {str(create_data['materials_required'][0])[:100]}")
                        
                        try:
                            response = await client.post("/api/supply-tree/create", json=create_data)
                            print(f"Full match data test: {response.status_code}")
                            if response.status_code != 201:
                                print(f"Error: {response.text[:500]}")
                                try:
                                    error_json = response.json()
                                    print(f"Error JSON: {json.dumps(error_json, indent=2)[:1000]}")
                                except:
                                    pass
                        except Exception as e:
                            print(f"Exception: {e}")
                            import traceback
                            traceback.print_exc()

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("DEEP PROBE - Testing different scenarios to isolate the 500 error")
    print("=" * 80 + "\n")
    
    asyncio.run(probe_error())
    
    print("\n" + "=" * 80)
    print("Probe completed.")
    print("=" * 80)

