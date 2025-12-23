#!/usr/bin/env python3
"""
Diagnostic script to check spaCy installation and model availability.

This script helps troubleshoot spaCy model issues by checking:
- spaCy installation status
- Available models
- Model capabilities (word vectors, etc.)
- Recommended actions
"""

import sys
import subprocess


def check_spacy_installed():
    """Check if spaCy is installed."""
    try:
        import spacy
        print(f"✅ spaCy is installed (version {spacy.__version__})")
        return True, spacy
    except ImportError:
        print("❌ spaCy is not installed")
        print("   Install with: pip install spacy")
        return False, None


def check_models(spacy_module):
    """Check which spaCy models are available."""
    if not spacy_module:
        return

    print("\n📦 Checking available models...")
    
    # Preferred models in order
    preferred_models = [
        ("en_core_web_md", "Medium model with word vectors (recommended)"),
        ("en_core_web_lg", "Large model with word vectors (best accuracy)"),
        ("en_core_web_sm", "Small model without word vectors (fallback)"),
    ]
    
    available_models = []
    for model_name, description in preferred_models:
        try:
            nlp = spacy_module.load(model_name)
            has_vectors = nlp.vocab.vectors.size > 0
            vector_size = nlp.vocab.vectors.size if has_vectors else 0
            
            status = "✅"
            if has_vectors:
                status += " (with word vectors)"
            else:
                status += " (no word vectors)"
            
            print(f"  {status} {model_name}: {description}")
            if has_vectors:
                print(f"      Vector size: {vector_size:,}")
            
            available_models.append((model_name, has_vectors))
        except OSError:
            print(f"  ❌ {model_name}: Not installed")
    
    return available_models


def get_recommendations(available_models):
    """Provide recommendations based on available models."""
    print("\n💡 Recommendations:")
    
    if not available_models:
        print("  ⚠️  No spaCy models found!")
        print("     Install recommended model: python -m spacy download en_core_web_md")
        return
    
    # Check if we have a model with vectors
    has_vectors = any(has_vec for _, has_vec in available_models)
    
    if not has_vectors:
        print("  ⚠️  No models with word vectors found!")
        print("     For better semantic matching, install: python -m spacy download en_core_web_md")
        print("     Current models will work but with reduced accuracy")
    else:
        print("  ✅ You have models with word vectors - NLP matching will work optimally")
    
    # Check if we have the recommended model
    model_names = [name for name, _ in available_models]
    if "en_core_web_md" not in model_names:
        print("  💡 Consider installing en_core_web_md for optimal performance:")
        print("     python -m spacy download en_core_web_md")


def main():
    """Main diagnostic function."""
    print("🔍 spaCy Diagnostic Tool\n")
    print("=" * 60)
    
    # Check spaCy installation
    is_installed, spacy_module = check_spacy_installed()
    
    if not is_installed:
        sys.exit(1)
    
    # Check available models
    available_models = check_models(spacy_module)
    
    # Provide recommendations
    get_recommendations(available_models)
    
    print("\n" + "=" * 60)
    print("✅ Diagnostic complete")


if __name__ == "__main__":
    main()

