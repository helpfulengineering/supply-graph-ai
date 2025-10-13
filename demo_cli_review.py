#!/usr/bin/env python3
"""
Demo script showing how to use the CLI review interface.

This script demonstrates the complete workflow from URL to reviewed manifest.
"""

import asyncio
from src.core.generation.engine import GenerationEngine
from src.core.generation.url_router import URLRouter
from src.core.generation.review import ReviewInterface
from src.core.generation.models import LayerConfig


async def demo_cli_review(github_url: str):
    """
    Demo the complete CLI review workflow.
    
    Args:
        github_url: GitHub repository URL to process
    """
    print("🚀 OKH Manifest Generation & Review Demo")
    print("=" * 50)
    print(f"Processing: {github_url}")
    print()
    
    # Step 1: Initialize components
    print("📋 Step 1: Initializing generation system...")
    config = LayerConfig(
        use_direct=True,
        use_heuristic=False,
        use_nlp=False,
        use_llm=False,
        progressive_enhancement=True,
        min_confidence=0.8
    )
    engine = GenerationEngine(config)
    router = URLRouter()
    
    # Step 2: Detect platform and extract project data
    print("🔍 Step 2: Detecting platform and extracting project data...")
    platform = router.detect_platform(github_url)
    print(f"   Platform: {platform.value}")
    
    extractor = router.route_to_extractor(platform)
    print(f"   Extractor: {extractor.__class__.__name__}")
    
    project_data = await extractor.extract_project(github_url)
    print(f"   Metadata fields: {len(project_data.metadata)}")
    print(f"   Files: {len(project_data.files)}")
    print(f"   Documentation: {len(project_data.documentation)}")
    
    # Step 3: Generate manifest
    print("\n⚙️  Step 3: Generating manifest...")
    result = engine.generate_manifest(project_data)
    print(f"   Generated fields: {len(result.generated_fields)}")
    print(f"   Missing required: {len(result.missing_fields)}")
    print(f"   Overall quality: {result.quality_report.overall_quality:.2f}")
    
    # Step 4: Start review interface
    print("\n🔍 Step 4: Starting review interface...")
    print("   You can now review and edit the generated manifest.")
    print("   Type 'h' for help, 'quit' to exit.")
    print()
    
    interface = ReviewInterface(result)
    final_manifest = interface.review()
    
    if final_manifest:
        print("\n✅ Review completed successfully!")
        print(f"   Final manifest has {len(final_manifest.__dict__)} fields")
        print(f"   Title: {final_manifest.title}")
        print(f"   ID: {final_manifest.id}")
    else:
        print("\n👋 Review cancelled by user.")


def show_usage_instructions():
    """Show usage instructions for the CLI review interface"""
    print("\n📖 CLI REVIEW INTERFACE USAGE")
    print("=" * 50)
    print()
    print("🔧 SETUP:")
    print("   1. Run: python demo_cli_review.py")
    print("   2. Provide GitHub URL when prompted")
    print("   3. Review the generated manifest")
    print()
    print("⌨️  AVAILABLE COMMANDS:")
    print("   e     - Edit an existing field")
    print("   a     - Add a new field")
    print("   r     - Remove a field")
    print("   q     - Show quality report")
    print("   x     - Export manifest (saves and exits)")
    print("   h     - Show help")
    print("   quit  - Quit without saving")
    print()
    print("📝 EXAMPLE WORKFLOW:")
    print("   1. Type 'q' to see quality report")
    print("   2. Type 'e' to edit a field (e.g., title)")
    print("   3. Type 'a' to add missing fields (e.g., version)")
    print("   4. Type 'q' again to see improved quality (updates automatically!)")
    print("   5. Type 'x' to export final manifest")
    print()
    print("💡 TIPS:")
    print("   • Start with 'q' to see what needs improvement")
    print("   • Use 'e' to fix existing fields")
    print("   • Use 'a' to add missing required fields")
    print("   • Check quality after each change")
    print("   • Export when satisfied with the result")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        show_usage_instructions()
    else:
        # Get GitHub URL from user
        github_url = input("Enter GitHub repository URL: ").strip()
        if not github_url:
            print("❌ No URL provided. Exiting.")
            sys.exit(1)
        
        # Run the demo
        asyncio.run(demo_cli_review(github_url))
