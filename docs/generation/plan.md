# OKH Manifest Extraction System - Implementation Plan

## Overview

This document outlines the implementation plan for an intelligent OKH manifest generation system that can automatically extract and create standardized OpenKnowHow manifests from open hardware projects found on various online platforms.

## Problem Statement

Creating OKH manifests manually is time-consuming and error-prone, creating a significant barrier to OKH adoption. We need a systematic, intelligent system that can:

1. **Ingest** projects from various platforms (GitHub, GitLab, Hackaday.io, etc.)
2. **Extract** relevant information through multiple layers of intelligence
3. **Generate** standardized OKH manifests with high accuracy
4. **Validate** and allow user review/correction of extracted data

## Strategic Direction

### Core Principles

- **Quality-First Approach**: Prioritize maximum extraction quality over speed
- **Progressive Enhancement**: Start with minimum viable manifests, improve iteratively
- **User-Centric Design**: Human review and intervention for quality control
- **Platform Extensibility**: Support multiple platforms with consistent interface

### Access Patterns

- **Infrequent Usage**: Typical access pattern is infrequent and async
- **Incremental Updates**: Once extracted, updates occur rarely and are incremental (e.g., git releases)
- **Quality Over Speed**: Can safely prioritize maximum quality as default setting

## System Architecture

### Core Components

```
URL → Platform Detection → Project Extraction → Multi-Layer Processing → Quality Assessment → User Review → Manifest Generation
```

#### 1. URL Router & Validator
- Validates URLs and determines platform type
- Routes to appropriate extractor
- Handles URL normalization and validation

#### 2. Platform Extractors
- GitHub, GitLab, Codeberg, Hackaday.io extractors
- Each implements common `ProjectExtractor` interface
- Platform-specific API integration and data parsing
- HTML parsing support (BeautifulSoup) for platforms without clean APIs

#### 3. Multi-Layer Extraction Engine
- Orchestrates the 4-layer extraction process
- Manages field completion and confidence scoring
- Handles extraction pipeline coordination

#### 4. Quality Assessment System
- Field confidence scoring
- Required field validation
- Quality report generation

#### 5. User Review Interface
- Presents extracted data for validation
- Collects user corrections
- Generates final manifest

## Multi-Layer Extraction Strategy

### Default Behavior: Progressive Enhancement
- **Strategy**: Proceed from simple direct matching to LLM matching
- **Termination**: Stop when sufficient quality is reached
- **Quality Threshold**: Configurable minimum confidence score per field

### Layer 1: Direct Matching
- **Purpose**: Exact field mapping from platform metadata
- **Examples**: `project.name` → `manifest.title`, `project.description` → `manifest.description`
- **Implementation**: Platform-specific field mapping dictionaries
- **Performance**: Fast, high confidence when available

### Layer 2: Heuristic Matching
- **Purpose**: Rule-based pattern recognition
- **Examples**: 
  - "README.md" → `manifest.description`
  - "LICENSE" file → `manifest.license`
  - "docs/" folder → `manifest.documentation`
- **Implementation**: File structure analysis and naming convention rules
- **Performance**: Fast, moderate confidence

### Layer 3: NLP Matching
- **Purpose**: Semantic understanding of content
- **Examples**:
  - Parse README for project description
  - Extract requirements from documentation
  - Identify materials from BOM files
- **Implementation**: spaCy library for content analysis
- **Performance**: Moderate speed, good confidence

### Layer 4: LLM Matching
- **Purpose**: AI-powered content understanding
- **Examples**:
  - Generate missing descriptions
  - Infer requirements from code/documentation
  - Suggest appropriate categories
- **Implementation**: LLM integration for complex field extraction
- **Performance**: Slow, high confidence, expensive
- **Use Cases**: 
  - Development: Create high-quality reference manifests
  - Production: Fill critical missing fields when other layers fail
  - Validation: Compare other layers against LLM-generated "ground truth"

### Command-Line Control
- **Default**: Progressive enhancement (Direct → Heuristic → NLP → LLM as needed)
- **Explicit Control**: `--use-direct`, `--use-heuristic`, `--use-nlp`, `--use-llm`
- **Combination**: `--use-llm --use-heuristic` (skip Direct and NLP layers)
- **Quality Override**: `--min-confidence 0.8` (require higher confidence before stopping)

## Platform Support Strategy

### Phase 1: GitHub (Primary Focus)
- **Rationale**: Most structured, common use case, rich API
- **Features**: Repository metadata, file structure, documentation parsing
- **Challenges**: Varying documentation quality, different conventions

### Phase 2: GitLab & Codeberg
- **Rationale**: Similar to GitHub, easier to implement
- **Features**: Similar API structure, consistent file layouts
- **Challenges**: Platform-specific API differences

### Phase 3: Hackaday.io
- **Rationale**: Hardware-focused platform with rich metadata
- **Features**: Project metadata, documentation, media files
- **Challenges**: Different data model, less structured
- **Implementation**: HTML parsing with BeautifulSoup (no clean API available)

### Phase 4: Extensible Architecture
- **Future Platforms**: Thingiverse, Instructables, custom websites
- **Architecture**: Plugin-based system for new platform support

## HTML Parsing Strategy

### Platforms Requiring HTML Parsing
- **Hackaday.io**: No clean API, requires web scraping
- **Thingiverse**: Limited API, HTML parsing for detailed information
- **Instructables**: No API, HTML parsing for project content
- **Custom Websites**: Unpredictable structure, adaptive parsing

### HTML Parsing Implementation
```python
class HTMLParser:
    def __init__(self, platform: PlatformType):
        self.platform = platform
        self.selectors = self._load_selectors(platform)
    
    def parse_project_page(self, html_content: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html_content, 'html.parser')
        return self._extract_metadata(soup)
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        # Platform-specific extraction logic
        pass
```

### Selector-Based Extraction
- **CSS Selectors**: Platform-specific selectors for common elements
- **Fallback Strategies**: Multiple selector attempts for robustness
- **Content Cleaning**: Remove HTML tags, normalize whitespace
- **Error Handling**: Graceful degradation when selectors fail

## Field Completeness Strategy

### Minimum Viable Manifest
- **Required Fields**: Title, description, license
- **Goal**: Ensure all required fields are filled
- **Validation**: Strict validation for required fields

### Progressive Enhancement
- **Recommended Fields**: Materials, processes, documentation
- **Optional Fields**: Advanced metadata, detailed requirements
- **Strategy**: Start with basics, improve iteratively

### Quality Control
- **Field Confidence Scoring**: Each extracted field gets a confidence score
- **User Review Interface**: Present extracted data for validation/editing
- **Partial Success Handling**: Extract what's possible, flag what's missing

## Implementation Roadmap

### Phase 1: Foundation (GitHub Focus)
**Duration**: 4-6 weeks
**Goals**:
- URL validation and GitHub detection
- Basic GitHub project extraction (API + file system)
- Direct matching layer (title, description, license)
- Simple manifest generation
- User review interface

**Deliverables**:
- GitHub URL detection and validation
- Basic project extraction (title, description, license)
- Minimum viable manifest generation
- User review interface
- CLI integration: `ome okh extract-from-url <url>`

### Phase 2: Intelligence (GitHub Enhancement)
**Duration**: 6-8 weeks
**Goals**:
- Heuristic matching rules (README parsing, file structure analysis)
- NLP integration (spaCy for content analysis)
- Field confidence scoring
- Enhanced user review with confidence indicators
- Proper OKH manifest format output
- Enhanced field extraction (materials, processes, documentation)

**Deliverables**:
- 80%+ field extraction accuracy for common GitHub projects
- Heuristic rules for README parsing
- NLP-based content analysis
- Confidence scoring system
- Enhanced user interface
- Proper OKH manifest format (not API wrapper)
- Enhanced field extraction for materials, processes, documentation

**Phase 2 Implementation Plan**:

#### 2.1 Fix Response Format Issue
**Problem**: Current output is API wrapper format, not proper OKH manifest
**Solution**: 
- Modify CLI to output proper OKH manifest format
- Keep API wrapper for HTTP responses
- Add `--format` option: `okh` (default) vs `api` (wrapper format)

#### 2.2 Implement Heuristic Matching Layer
**Location**: `src/core/generation/layers/heuristic.py`
**Features**:
- README.md parsing for description, function, intended_use
- File structure analysis (docs/, stl/, openscad/ folders)
- License file detection and parsing
- BOM file detection and parsing
- Manufacturing file detection

#### 2.3 Implement NLP Matching Layer  
**Location**: `src/core/generation/layers/nlp.py`
**Dependencies**: Add `spacy>=3.7.0` to requirements.txt
**Features**:
- Content analysis using spaCy
- Entity recognition for materials, processes
- Semantic understanding of descriptions
- Requirements extraction from documentation

#### 2.4 Enhanced Field Extraction
**Target Fields**:
- `materials`: Extract from BOM files, README, documentation
- `manufacturing_processes`: Detect from file structure and content
- `tool_list`: Extract from documentation and instructions
- `manufacturing_files`: Detect and categorize design/manufacturing files
- `design_files`: Identify CAD files, STL files, etc.
- `making_instructions`: Extract assembly and build instructions

#### 2.5 Progressive Enhancement Logic
**Implementation**: Update `GenerationEngine` to use multiple layers
**Strategy**:
1. Direct matching (existing)
2. Heuristic matching (new)
3. NLP matching (new)
4. Stop when confidence threshold reached
5. User review for low-confidence fields

### Phase 3: AI Enhancement (GitHub + LLM)
**Duration**: 8-10 weeks
**Goals**:
- LLM integration for complex field extraction
- Development workflow using LLM as reference standard
- Advanced validation and quality assessment
- Learning from user corrections
- Performance optimizations

**Deliverables**:
- 90%+ field extraction accuracy
- LLM integration for complex fields
- Development mode: LLM reference generation for comparison
- Learning from user feedback
- Performance optimizations
- Advanced quality assessment

**LLM Development Strategy**:
- **Reference Generation**: Use LLM to create high-quality manifests for development
- **Layer Comparison**: Compare Direct/Heuristic/NLP layers against LLM "ground truth"
- **Quality Benchmarking**: Measure extraction accuracy using LLM-generated references
- **Rule Refinement**: Improve heuristic and NLP rules based on LLM comparison
- **Production Use**: LLM only for critical missing fields when other layers fail

### Phase 4: Platform Expansion
**Duration**: 10-12 weeks
**Goals**:
- GitLab extractor
- Codeberg extractor
- Hackaday.io extractor
- Platform-specific optimizations

**Deliverables**:
- Multi-platform support (GitHub, GitLab, Codeberg, Hackaday)
- Platform-specific optimizations
- Extensible architecture for future platforms
- Comprehensive testing suite

## Technical Architecture

### Core Classes

```python
class URLRouter:
    def detect_platform(url: str) -> PlatformType
    def validate_url(url: str) -> bool
    def route_to_extractor(platform: PlatformType) -> ProjectExtractor

class ProjectExtractor(ABC):
    @abstractmethod
    async def extract_project(self, url: str) -> ProjectData

class GitHubExtractor(ProjectExtractor):
    async def extract_project(self, url: str) -> ProjectData

class ExtractionEngine:
    def __init__(self, layer_config: LayerConfig):
        self.direct_matcher = DirectMatcher()
        self.heuristic_matcher = HeuristicMatcher()
        self.nlp_matcher = NLPMatcher()
        self.llm_matcher = LLMMatcher()
        self.config = layer_config
    
    async def extract_manifest(self, project_data: ProjectData) -> ManifestExtraction
    async def extract_with_layers(self, project_data: ProjectData, layers: List[ExtractionLayer]) -> ManifestExtraction
    async def generate_reference_manifest(self, project_data: ProjectData) -> OKHManifest

@dataclass
class LayerConfig:
    use_direct: bool = True
    use_heuristic: bool = True
    use_nlp: bool = True
    use_llm: bool = False
    min_confidence: float = 0.7
    progressive_enhancement: bool = True
    save_reference: bool = False

class QualityAssessor:
    def assess_field_confidence(self, field: str, value: Any) -> float
    def validate_required_fields(self, manifest: Manifest) -> ValidationResult
    def generate_quality_report(self, extraction: ManifestExtraction) -> QualityReport

class ReviewInterface:
    def present_extraction(self, extraction: ManifestExtraction) -> ReviewResult
    def collect_user_corrections(self, extraction: ManifestExtraction) -> UserCorrections
    def generate_final_manifest(self, extraction: ManifestExtraction, corrections: UserCorrections) -> OKHManifest
```

### Data Models

```python
@dataclass
class ProjectData:
    platform: PlatformType
    url: str
    metadata: Dict[str, Any]
    files: List[FileInfo]
    documentation: List[DocumentInfo]
    raw_content: Dict[str, str]

@dataclass
class ManifestExtraction:
    project_data: ProjectData
    extracted_fields: Dict[str, FieldExtraction]
    confidence_scores: Dict[str, float]
    quality_report: QualityReport
    missing_fields: List[str]

@dataclass
class FieldExtraction:
    value: Any
    confidence: float
    source_layer: ExtractionLayer
    extraction_method: str
    raw_source: str
```

## Integration Points

### CLI Integration
```bash
# Extract manifest from GitHub project (default progressive enhancement)
ome okh extract-from-url https://github.com/user/project

# Extract with specific layer control
ome okh extract-from-url https://github.com/user/project --use-llm
ome okh extract-from-url https://github.com/user/project --use-heuristic --use-nlp
ome okh extract-from-url https://github.com/user/project --use-direct --use-llm

# Extract with quality control
ome okh extract-from-url https://github.com/user/project --min-confidence 0.8
ome okh extract-from-url https://github.com/user/project --quality-level premium --review-mode interactive

# Extract and immediately build package
ome okh extract-from-url https://github.com/user/project --build-package

# Development mode: Generate LLM reference for comparison
ome okh extract-from-url https://github.com/user/project --use-llm --save-reference
```

### API Integration
```python
# FastAPI endpoint
@router.post("/okh/extract-from-url")
async def extract_from_url(request: ExtractFromURLRequest):
    # Implementation
```

### Package Management Integration
- Generated manifests can be built into packages
- Extracted requirements can feed into matching system
- Seamless workflow from extraction to package management

## Quality Metrics & Success Criteria

### Phase 1 Success Criteria
- ✅ GitHub URL detection and validation (100% accuracy)
- ✅ Basic project extraction (title, description, license) (90%+ accuracy)
- ✅ Minimum viable manifest generation (100% required fields)
- ✅ User review interface (functional)
- ✅ CLI integration: `ome okh generate-from-url <url>`
- ✅ API integration: `POST /okh/generate-from-url`
- ✅ End-to-end testing (11 comprehensive tests passing)

### Phase 2 Success Criteria
- [x] **Heuristic Matching Layer**: README parsing, file structure analysis, manufacturing process detection
- [x] **BOM Normalization System**: Structured BOM extraction, processing, and export
- [x] **Built Directory Export**: Multiple BOM formats (JSON, Markdown, CSV, components)
- [x] **Manifest Size Optimization**: Compressed BOM summary with external file references (69% size reduction)
- [ ] **NLP-based content analysis** (60%+ accuracy)
- [ ] **Enhanced field extraction** (materials, processes, documentation)
- [ ] **Progressive enhancement logic** (multi-layer generation with confidence thresholds)

### Phase 3 Success Criteria
- [ ] 90%+ field extraction accuracy
- [ ] LLM integration for complex fields (80%+ accuracy)
- [ ] Learning from user feedback (functional)
- [ ] Performance optimizations (sub-30s extraction time)

### Phase 4 Success Criteria
- [ ] Multi-platform support (GitHub, GitLab, Codeberg, Hackaday)
- [ ] Platform-specific optimizations (80%+ accuracy per platform)
- [ ] Extensible architecture for future platforms
- [ ] Comprehensive testing suite (90%+ test coverage)

## Error Handling & Fallback Strategy

### Partial Success Handling
- Extract what's possible, flag what's missing
- Present clear indicators of extraction confidence
- Provide guidance for manual completion

### User Intervention
- Interactive review interface for extracted data
- Easy correction and validation workflow
- Clear feedback on extraction quality

### Learning System (Future)
- Improve extraction based on user corrections
- Build platform-specific knowledge base
- Adaptive extraction rules

## Risk Mitigation

### Technical Risks
- **API Rate Limits**: Implement caching and rate limiting
- **Platform Changes**: Abstract platform-specific code
- **Extraction Quality**: Multiple validation layers and user review

### User Experience Risks
- **Complexity**: Progressive disclosure and clear interfaces
- **Accuracy**: Confidence indicators and easy correction
- **Performance**: Async processing and progress indicators

## Dependencies

### External Libraries
- **spaCy**: NLP processing
- **httpx**: HTTP client for API calls
- **pydantic**: Data validation
- **click**: CLI interface (existing)
- **BeautifulSoup4**: HTML parsing for platforms without clean APIs
- **requests**: Additional HTTP client support

### Internal Dependencies
- **OKH Manifest Model**: Existing manifest structure
- **CLI Framework**: Existing CLI infrastructure
- **Package Management**: Existing package system

## Future Enhancements

### Advanced Features
- **Batch Processing**: Extract multiple projects simultaneously
- **Template System**: Project type-specific extraction templates
- **Community Contributions**: User-submitted extraction rules
- **Analytics**: Extraction quality metrics and improvements

### Platform Expansion
- **Thingiverse**: 3D model focus, different metadata
- **Instructables**: Step-by-step format, rich media
- **Custom Websites**: Unpredictable structure
- **Local Projects**: File system-based extraction

## Conclusion

This plan provides a comprehensive roadmap for building an intelligent OKH manifest extraction system. The phased approach ensures we can validate the concept with GitHub before expanding to other platforms, while the quality-first strategy ensures high-value output for users.

The system will significantly lower the barrier to OKH adoption by automating the most time-consuming aspect of manifest creation while maintaining quality through intelligent extraction and user review processes.

## Next Steps

### Phase 1 Complete ✅
- ✅ **URL Router & Platform Detection**: GitHub and GitLab support
- ✅ **Direct Matching Layer**: Basic field mapping (title, description, license, repo)
- ✅ **Generation Engine**: Orchestrates the generation process
- ✅ **Quality Assessment**: Confidence scoring and quality reports
- ✅ **User Review Interface**: CLI-based interactive review
- ✅ **CLI Integration**: `ome okh generate-from-url <url>` command
- ✅ **API Integration**: `POST /okh/generate-from-url` endpoint
- ✅ **End-to-End Testing**: 11 comprehensive tests passing
- ✅ **Proper OKH Manifest Format**: CLI outputs standard OKH manifest structure

### Phase 2 Next Steps
1. ✅ **Implement Heuristic Matching Layer**: README parsing, file structure analysis
2. ✅ **BOM Normalization System**: Structured BOM extraction and export
3. **Implement NLP Matching Layer**: Content analysis using spaCy
4. **Enhanced Field Extraction**: Materials, processes, documentation, tool lists
5. **Progressive Enhancement Logic**: Multi-layer generation with confidence thresholds
6. **Advanced Quality Assessment**: Field-specific confidence scoring
7. **Enhanced User Review**: Confidence indicators and field-specific editing

## NLP Matching Layer Implementation Plan

### Overview
The NLP Matching Layer will use spaCy for semantic understanding of project content, focusing on extracting structured information from unstructured text in README files, documentation, and other project content.

### Target Fields for NLP Extraction
1. **Function & Intended Use**: Semantic understanding of project purpose
2. **Materials**: Named Entity Recognition for material types and specifications
3. **Manufacturing Processes**: Text classification for process identification
4. **Tool Requirements**: Extraction of required tools and equipment
5. **Assembly Instructions**: Structured parsing of build steps
6. **Technical Specifications**: Parameter extraction from documentation

### Implementation Strategy

#### 1. spaCy Integration
```python
# Add to requirements.txt
spacy>=3.7.0
```

#### 2. NLP Processing Pipeline
```python
class NLPMatcher(BaseGenerationLayer):
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.material_patterns = self._load_material_patterns()
        self.process_patterns = self._load_process_patterns()
        self.tool_patterns = self._load_tool_patterns()
    
    async def process(self, project_data: ProjectData) -> LayerResult:
        # Process README and documentation content
        # Extract entities and classify content
        # Generate field extractions with confidence scores
```

#### 3. Named Entity Recognition (NER)
- **Materials**: PLA, ABS, metal, wood, electronics components
- **Processes**: 3D printing, CNC machining, soldering, assembly
- **Tools**: 3D printer, soldering iron, multimeter, drill
- **Measurements**: dimensions, tolerances, specifications

#### 4. Text Classification
- **Content Type**: Assembly instructions, specifications, troubleshooting
- **Process Type**: Manufacturing, assembly, testing, calibration
- **Complexity Level**: Beginner, intermediate, advanced

#### 5. Semantic Understanding
- **Intent Recognition**: What is this project for?
- **Requirement Extraction**: What do you need to build this?
- **Process Flow**: How is this assembled/manufactured?

### Success Metrics
- **60%+ accuracy** for material extraction from README content
- **70%+ accuracy** for manufacturing process identification
- **50%+ accuracy** for tool requirement extraction
- **Confidence scoring** for all extracted fields
- **Integration** with existing heuristic and direct matching layers

### Phase 3 Future Steps
1. **LLM Integration**: AI-powered field extraction for complex cases
2. **Learning System**: Improve extraction based on user corrections
3. **Performance Optimization**: Caching, parallel processing
4. **Advanced Validation**: Cross-field consistency checking

### Phase 4 Platform Expansion
1. **GitLab Enhancement**: Full GitLab API integration
2. **Codeberg Support**: Add Codeberg platform support
3. **Hackaday.io Integration**: HTML parsing for hardware-focused platform
4. **Extensible Architecture**: Plugin system for new platforms
