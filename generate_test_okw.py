#!/usr/bin/env python3
"""
Quick script to generate additional OKW facilities for testing
"""
import subprocess
import sys
from pathlib import Path

def generate_okw_facilities(count: int = 3, complexity: str = "mixed"):
    """Generate additional OKW facilities for testing"""
    print(f"Generating {count} OKW facilities with {complexity} complexity...")
    
    # Run the synthetic data generator
    cmd = [
        sys.executable, 
        "synth/generate_synthetic_data.py",
        "--type", "okw",
        "--count", str(count),
        "--complexity", complexity,
        "--output-dir", "synth/synthetic_data"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Generation completed successfully!")
        print(result.stdout)
        
        # List the generated files
        synthetic_dir = Path("synth/synthetic_data")
        okw_files = list(synthetic_dir.glob("*-okw.json"))
        print(f"\n📁 Generated {len(okw_files)} OKW files:")
        for file in okw_files[-count:]:  # Show only the newly generated ones
            print(f"   - {file.name}")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating OKW facilities: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
    except FileNotFoundError:
        print("❌ Synthetic data generator not found. Make sure you're in the correct directory.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate OKW facilities for testing")
    parser.add_argument("--count", type=int, default=3, help="Number of facilities to generate")
    parser.add_argument("--complexity", choices=["minimal", "complex", "mixed"], default="mixed", help="Complexity level")
    
    args = parser.parse_args()
    
    generate_okw_facilities(args.count, args.complexity)
