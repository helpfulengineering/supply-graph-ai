"""
Tests for Quality Assessor functionality.

Following TDD approach: write tests first, then implement QualityAssessor.
"""

import pytest


def test_quality_assessor_import():
    """Test that QualityAssessor can be imported"""
    from src.core.generation.quality import QualityAssessor
    
    assert QualityAssessor is not None


def test_quality_assessor_creation():
    """Test QualityAssessor instantiation"""
    from src.core.generation.quality import QualityAssessor
    
    assessor = QualityAssessor()
    assert assessor is not None


def test_quality_assessor_has_generate_quality_report():
    """Test that QualityAssessor has generate_quality_report method"""
    from src.core.generation.quality import QualityAssessor
    
    assessor = QualityAssessor()
    assert hasattr(assessor, 'generate_quality_report')
    assert callable(getattr(assessor, 'generate_quality_report'))


def test_generate_quality_report_complete():
    """Test quality report generation for complete manifest"""
    from src.core.generation.quality import QualityAssessor
    from src.core.generation.models import FieldGeneration, GenerationLayer
    
    assessor = QualityAssessor()
    
    # Create complete field set
    generated_fields = {
        "title": FieldGeneration(
            value="Test Project",
            confidence=0.95,
            source_layer=GenerationLayer.DIRECT,
            generation_method="direct_mapping",
            raw_source="metadata.name"
        ),
        "version": FieldGeneration(
            value="1.0.0",
            confidence=0.9,
            source_layer=GenerationLayer.DIRECT,
            generation_method="direct_mapping",
            raw_source="metadata.version"
        ),
        "license": FieldGeneration(
            value="MIT",
            confidence=0.9,
            source_layer=GenerationLayer.DIRECT,
            generation_method="direct_mapping",
            raw_source="metadata.license"
        ),
        "licensor": FieldGeneration(
            value="Test Author",
            confidence=0.85,
            source_layer=GenerationLayer.DIRECT,
            generation_method="direct_mapping",
            raw_source="metadata.author"
        ),
        "documentation_language": FieldGeneration(
            value="en",
            confidence=0.9,
            source_layer=GenerationLayer.DIRECT,
            generation_method="direct_mapping",
            raw_source="metadata.language"
        ),
        "function": FieldGeneration(
            value="Test hardware project",
            confidence=0.8,
            source_layer=GenerationLayer.DIRECT,
            generation_method="direct_mapping",
            raw_source="metadata.description"
        )
    }
    
    confidence_scores = {field: gen.confidence for field, gen in generated_fields.items()}
    missing_fields = []
    required_fields = ["title", "version", "license", "licensor", "documentation_language", "function"]
    
    report = assessor.generate_quality_report(generated_fields, confidence_scores, missing_fields, required_fields)
    
    assert report is not None
    assert report.overall_quality >= 0.8
    assert report.required_fields_complete is True
    assert len(report.missing_required_fields) == 0
    assert len(report.low_confidence_fields) == 0


def test_generate_quality_report_partial():
    """Test quality report generation for partial manifest"""
    from src.core.generation.quality import QualityAssessor
    from src.core.generation.models import FieldGeneration, GenerationLayer
    
    assessor = QualityAssessor()
    
    # Create partial field set
    generated_fields = {
        "title": FieldGeneration(
            value="Test Project",
            confidence=0.95,
            source_layer=GenerationLayer.DIRECT,
            generation_method="direct_mapping",
            raw_source="metadata.name"
        ),
        "version": FieldGeneration(
            value="1.0.0",
            confidence=0.9,
            source_layer=GenerationLayer.DIRECT,
            generation_method="direct_mapping",
            raw_source="metadata.version"
        )
    }
    
    confidence_scores = {field: gen.confidence for field, gen in generated_fields.items()}
    missing_fields = ["license", "licensor", "documentation_language", "function"]
    required_fields = ["title", "version", "license", "licensor", "documentation_language", "function"]
    
    report = assessor.generate_quality_report(generated_fields, confidence_scores, missing_fields, required_fields)
    
    assert report is not None
    assert report.overall_quality < 0.8
    assert report.required_fields_complete is False
    assert len(report.missing_required_fields) == 4
    assert "license" in report.missing_required_fields
    assert "licensor" in report.missing_required_fields


def test_generate_quality_report_low_confidence():
    """Test quality report generation with low confidence fields"""
    from src.core.generation.quality import QualityAssessor
    from src.core.generation.models import FieldGeneration, GenerationLayer
    
    assessor = QualityAssessor()
    
    # Create field set with low confidence
    generated_fields = {
        "title": FieldGeneration(
            value="Test Project",
            confidence=0.6,  # Low confidence
            source_layer=GenerationLayer.DIRECT,
            generation_method="direct_mapping",
            raw_source="metadata.name"
        ),
        "version": FieldGeneration(
            value="1.0.0",
            confidence=0.5,  # Low confidence
            source_layer=GenerationLayer.DIRECT,
            generation_method="direct_mapping",
            raw_source="metadata.version"
        ),
        "license": FieldGeneration(
            value="MIT",
            confidence=0.9,
            source_layer=GenerationLayer.DIRECT,
            generation_method="direct_mapping",
            raw_source="metadata.license"
        )
    }
    
    confidence_scores = {field: gen.confidence for field, gen in generated_fields.items()}
    missing_fields = ["licensor", "documentation_language", "function"]
    required_fields = ["title", "version", "license", "licensor", "documentation_language", "function"]
    
    report = assessor.generate_quality_report(generated_fields, confidence_scores, missing_fields, required_fields)
    
    assert report is not None
    assert report.overall_quality < 0.7
    assert report.required_fields_complete is False
    assert len(report.low_confidence_fields) >= 2
    assert "title" in report.low_confidence_fields
    assert "version" in report.low_confidence_fields


def test_generate_quality_report_recommendations():
    """Test that quality report includes recommendations"""
    from src.core.generation.quality import QualityAssessor
    from src.core.generation.models import FieldGeneration, GenerationLayer
    
    assessor = QualityAssessor()
    
    # Create incomplete field set
    generated_fields = {
        "title": FieldGeneration(
            value="Test Project",
            confidence=0.95,
            source_layer=GenerationLayer.DIRECT,
            generation_method="direct_mapping",
            raw_source="metadata.name"
        )
    }
    
    confidence_scores = {field: gen.confidence for field, gen in generated_fields.items()}
    missing_fields = ["version", "license", "licensor", "documentation_language", "function"]
    required_fields = ["title", "version", "license", "licensor", "documentation_language", "function"]
    
    report = assessor.generate_quality_report(generated_fields, confidence_scores, missing_fields, required_fields)
    
    assert report is not None
    assert len(report.recommendations) > 0
    
    # Should recommend adding missing fields
    recommendations_text = " ".join(report.recommendations)
    assert "version" in recommendations_text or "missing" in recommendations_text.lower()


def test_assess_field_confidence():
    """Test individual field confidence assessment"""
    from src.core.generation.quality import QualityAssessor
    
    assessor = QualityAssessor()
    
    # Test high confidence field
    confidence = assessor.assess_field_confidence("title", "Test Project", "metadata.name")
    assert confidence >= 0.9
    
    # Test medium confidence field
    confidence = assessor.assess_field_confidence("description", "A test project", "metadata.description")
    assert 0.7 <= confidence <= 0.9
    
    # Test low confidence field
    confidence = assessor.assess_field_confidence("license", "", "metadata.license")
    assert confidence <= 0.5


def test_validate_required_fields():
    """Test required field validation"""
    from src.core.generation.quality import QualityAssessor
    from src.core.generation.models import FieldGeneration, GenerationLayer
    
    assessor = QualityAssessor()
    
    # Test with all required fields
    generated_fields = {
        "title": FieldGeneration("Test", 0.9, GenerationLayer.DIRECT, "direct", "test"),
        "version": FieldGeneration("1.0", 0.9, GenerationLayer.DIRECT, "direct", "test"),
        "license": FieldGeneration("MIT", 0.9, GenerationLayer.DIRECT, "direct", "test"),
        "licensor": FieldGeneration("Author", 0.9, GenerationLayer.DIRECT, "direct", "test"),
        "documentation_language": FieldGeneration("en", 0.9, GenerationLayer.DIRECT, "direct", "test"),
        "function": FieldGeneration("Test", 0.9, GenerationLayer.DIRECT, "direct", "test")
    }
    
    required_fields = ["title", "version", "license", "licensor", "documentation_language", "function"]
    result = assessor.validate_required_fields(generated_fields, required_fields)
    
    assert result.is_valid is True
    assert len(result.missing_fields) == 0
    
    # Test with missing required fields
    partial_fields = {
        "title": FieldGeneration("Test", 0.9, GenerationLayer.DIRECT, "direct", "test"),
        "version": FieldGeneration("1.0", 0.9, GenerationLayer.DIRECT, "direct", "test")
    }
    
    result = assessor.validate_required_fields(partial_fields, required_fields)
    
    assert result.is_valid is False
    assert len(result.missing_fields) == 4
    assert "license" in result.missing_fields


def test_quality_report_edge_cases():
    """Test quality report generation with edge cases"""
    from src.core.generation.quality import QualityAssessor
    from src.core.generation.models import FieldGeneration, GenerationLayer
    
    assessor = QualityAssessor()
    
    # Test with empty inputs
    report = assessor.generate_quality_report({}, {}, [], [])
    assert report is not None
    assert report.overall_quality == 0.0
    assert report.required_fields_complete is True  # No required fields = complete
    
    # Test with no required fields
    generated_fields = {
        "title": FieldGeneration("Test", 0.9, GenerationLayer.DIRECT, "direct", "test")
    }
    confidence_scores = {"title": 0.9}
    
    report = assessor.generate_quality_report(generated_fields, confidence_scores, [], [])
    assert report is not None
    assert report.overall_quality >= 0.9
    assert report.required_fields_complete is True


def test_quality_report_confidence_thresholds():
    """Test quality report with different confidence thresholds"""
    from src.core.generation.quality import QualityAssessor
    from src.core.generation.models import FieldGeneration, GenerationLayer
    
    assessor = QualityAssessor()
    
    # Test with mixed confidence levels
    generated_fields = {
        "title": FieldGeneration("Test", 0.95, GenerationLayer.DIRECT, "direct", "test"),
        "version": FieldGeneration("1.0", 0.7, GenerationLayer.DIRECT, "direct", "test"),
        "license": FieldGeneration("MIT", 0.5, GenerationLayer.DIRECT, "direct", "test")
    }
    
    confidence_scores = {field: gen.confidence for field, gen in generated_fields.items()}
    missing_fields = ["licensor", "documentation_language", "function"]
    required_fields = ["title", "version", "license", "licensor", "documentation_language", "function"]
    
    report = assessor.generate_quality_report(generated_fields, confidence_scores, missing_fields, required_fields)
    
    assert report is not None
    assert "license" in report.low_confidence_fields  # 0.5 < 0.7 threshold
    assert "title" not in report.low_confidence_fields  # 0.95 > 0.7 threshold
    # Note: version with 0.7 confidence is exactly at threshold, so not considered low
