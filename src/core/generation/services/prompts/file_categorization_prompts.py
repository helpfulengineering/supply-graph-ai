"""
Structured prompt templates for LLM file categorization.

This module provides structured prompts for categorizing files using LLM content analysis.
The prompts include comprehensive DocumentationType definitions, examples, and decision criteria.
"""

from pathlib import Path
from typing import Optional

from ...models import FileInfo, AnalysisDepth
from ...utils.file_categorization import FileCategorizationResult
from ....models.okh import DocumentationType


class FileCategorizationPrompts:
    """
    Structured prompt templates for LLM file categorization.

    This class provides comprehensive prompts that include:
    - File metadata (path, extension, directory)
    - Content preview (based on analysis depth)
    - Layer 1 suggestions and confidence scores
    - DocumentationType definitions and examples
    - Decision criteria and edge cases
    """

    @staticmethod
    def build_categorization_prompt(
        file_info: FileInfo,
        layer1_suggestion: FileCategorizationResult,
        content_preview: str,
        analysis_depth: AnalysisDepth,
    ) -> str:
        """
        Build structured prompt for file categorization.

        Args:
            file_info: File information (path, size, type)
            layer1_suggestion: Layer 1 heuristic suggestion
            content_preview: Content preview based on analysis depth
            analysis_depth: Analysis depth used (Shallow/Medium/Deep)

        Returns:
            Complete prompt string for LLM categorization
        """
        file_path = Path(file_info.path)
        filename = file_path.name
        directory = str(file_path.parent) if file_path.parent != Path(".") else "root"
        file_ext = file_path.suffix.lower()

        # Build prompt sections
        sections = []

        # Section 1: Task Description
        sections.append(FileCategorizationPrompts._build_task_section())

        # Section 2: File Information
        sections.append(
            FileCategorizationPrompts._build_file_info_section(
                file_path=file_info.path,
                filename=filename,
                directory=directory,
                file_ext=file_ext,
                file_size=file_info.size,
            )
        )

        # Section 3: Content Preview
        sections.append(
            FileCategorizationPrompts._build_content_section(
                content_preview=content_preview, analysis_depth=analysis_depth
            )
        )

        # Section 4: Layer 1 Suggestion
        sections.append(
            FileCategorizationPrompts._build_layer1_suggestion_section(
                layer1_suggestion=layer1_suggestion
            )
        )

        # Section 5: DocumentationType Rules
        sections.append(FileCategorizationPrompts._build_documentation_type_rules())

        # Section 6: Decision Criteria
        sections.append(FileCategorizationPrompts._build_decision_criteria_section())

        # Section 7: Output Format
        sections.append(FileCategorizationPrompts._build_output_format_section())

        return "\n\n".join(sections)

    @staticmethod
    def _build_task_section() -> str:
        """Build the task description section."""
        return """# File Categorization Task

You are an expert file categorization specialist for open-source hardware projects. Your task is to categorize files into appropriate DocumentationType categories based on their content, purpose, and context.

Your goal is to ensure files are correctly categorized to maximize interoperability and discoverability in the open-source hardware ecosystem."""

    @staticmethod
    def _build_file_info_section(
        file_path: str, filename: str, directory: str, file_ext: str, file_size: int
    ) -> str:
        """Build the file information section."""
        return f"""## File Information

- **Path**: `{file_path}`
- **Filename**: `{filename}`
- **Directory**: `{directory}`
- **Extension**: `{file_ext}` (if any)
- **Size**: {file_size} bytes"""

    @staticmethod
    def _build_content_section(
        content_preview: str, analysis_depth: AnalysisDepth
    ) -> str:
        """Build the content preview section."""
        depth_descriptions = {
            AnalysisDepth.SHALLOW: "first 500 characters",
            AnalysisDepth.MEDIUM: "first 2000 characters",
            AnalysisDepth.DEEP: "full document content",
        }

        depth_desc = depth_descriptions.get(analysis_depth, "content preview")

        if not content_preview or not content_preview.strip():
            content_text = "*[No text content available - binary or empty file]*"
        else:
            content_text = f"```\n{content_preview}\n```"

        # Build note about analysis depth
        if analysis_depth == AnalysisDepth.DEEP:
            depth_note = "Full document content is provided above."
        else:
            depth_note = f"Only the {depth_desc} are shown. Use this preview to understand the file's purpose and content."

        return f"""## Content Preview ({depth_desc})

{content_text}

**Note**: This is a {analysis_depth.value} analysis. {depth_note}"""

    @staticmethod
    def _build_layer1_suggestion_section(
        layer1_suggestion: FileCategorizationResult,
    ) -> str:
        """Build the Layer 1 suggestion section."""
        if layer1_suggestion.excluded:
            return f"""## Layer 1 Heuristic Suggestion

**Status**: EXCLUDED
**Reason**: {layer1_suggestion.reason}

**Note**: Layer 1 heuristics suggest this file should be excluded from OKH documentation. Review this decision carefully - only exclude if the file is truly not relevant to OKH documentation (e.g., workflow files, CI/CD configs, raw test data)."""

        return f"""## Layer 1 Heuristic Suggestion

**Suggested Type**: `{layer1_suggestion.documentation_type.value}` ({layer1_suggestion.documentation_type.name})
**Confidence**: {layer1_suggestion.confidence:.1%}
**Reason**: {layer1_suggestion.reason}

**Note**: This is a heuristic-based suggestion. Review the file content and context to make the final decision. You may override this suggestion if the content indicates a different category."""

    @staticmethod
    def _build_documentation_type_rules() -> str:
        """Build the DocumentationType rules section."""
        return """## DocumentationType Rules and Definitions

### MAKING_INSTRUCTIONS
**Purpose**: Step-by-step instructions for humans to build/assemble the hardware
**Target Audience**: People making or assembling the object
**Examples**:
- `ASSEMBLY.md`, `BUILD.md`, `manual/assembly_guide.pdf`
- `instructions/step_by_step.md`, `build_instructions.txt`
- Files in `manual/`, `instructions/`, `build/`, `assembly/` directories
**Key Indicators**: Instructions, steps, assembly, build, making, fabrication
**Distinction**: For **humans** to read and follow (vs MANUFACTURING_FILES for machines)

### MANUFACTURING_FILES
**Purpose**: Files for machines to use as instructions (3D printers, CNC mills, etc.)
**Target Audience**: Manufacturing machines and equipment
**Examples**:
- `.stl`, `.3mf`, `.gcode`, `.nc` files
- `part.stl`, `assembly.3mf`, `toolpath.gcode`
- Files in `manufacturing/`, `gcode/`, `toolpaths/` directories
**Key Indicators**: Manufacturing-ready formats, machine-readable files
**Distinction**: For **machines** to use (vs MAKING_INSTRUCTIONS for humans)

### DESIGN_FILES
**Purpose**: Source design files (CAD, schematics, design documents)
**Target Audience**: Engineers, designers, manufacturers
**Examples**:
- `.scad`, `.fcstd`, `.blend`, `.f3d` (CAD source files)
- `.kicad_pcb`, `.sch`, `.brd` (PCB design files)
- Files in `source_files/`, `cad/`, `design/` directories
**Key Indicators**: Source CAD files, design documents, editable formats
**Distinction**: Source files that can be edited (vs MANUFACTURING_FILES which are output formats)

### DOCUMENTATION_HOME
**Purpose**: Main project documentation and entry point
**Target Audience**: Anyone discovering the project
**Examples**:
- `README.md` (root only)
- `docs/index.md`, `documentation/home.md`
**Key Indicators**: README, index, home, overview, getting started
**Note**: Only root-level README files should be DOCUMENTATION_HOME

### TECHNICAL_SPECIFICATIONS
**Purpose**: Technical specifications, dimensions, tolerances, parameters
**Target Audience**: Engineers, designers, manufacturers
**Examples**:
- `specs.md`, `technical_specs.pdf`, `dimensions.csv`
- `testing/validation_report.md`, `quality/standards.md`
- Files in `testing/`, `validation/`, `specs/` directories (if documentation)
**Key Indicators**: Specs, specifications, dimensions, tolerances, parameters, validation
**Note**: Raw test data files should be excluded, but validation reports are TECHNICAL_SPECIFICATIONS

### OPERATING_INSTRUCTIONS
**Purpose**: How to use the device (separate from how to build it)
**Target Audience**: End users operating the hardware
**Examples**:
- `USER_MANUAL.md`, `OPERATING_GUIDE.pdf`
- `usage.md`, `how_to_use.txt`
**Key Indicators**: Operating, usage, user manual, how to use
**Distinction**: How to **use** the device (vs MAKING_INSTRUCTIONS which is how to **build** it)

### PUBLICATIONS
**Purpose**: Research papers, academic publications related to the hardware
**Target Audience**: Researchers, academics, documentation readers
**Examples**:
- Papers in `publication/` directory
- `research_paper.pdf`, `academic_publication.docx`
- Files in `publication/`, `papers/`, `research/` directories
**Key Indicators**: Publication, paper, research, academic, journal
**Note**: These are included in OKH manifests (not excluded)

### SOFTWARE
**Purpose**: Software code and scripts associated with the hardware
**Target Audience**: Developers, software engineers
**Examples**:
- Standalone scripts: `standalone_script.py`, `utility.rb`
- Software in `code/`, `software/`, `firmware/` directories
**Key Indicators**: Code files, scripts, software, firmware
**Note**: Code as part of larger structure should be kept in context (may exclude)

### SCHEMATICS
**Purpose**: Electrical schematics and circuit diagrams
**Target Audience**: Electrical engineers, designers
**Examples**:
- `.sch`, `.brd`, `.kicad_sch` files
- Circuit diagrams, wiring diagrams
**Key Indicators**: Schematic, circuit, wiring, electrical diagram

### MAINTENANCE_INSTRUCTIONS
**Purpose**: Instructions for maintaining the hardware
**Target Audience**: Users maintaining the hardware
**Examples**:
- `MAINTENANCE.md`, `maintenance_guide.pdf`
- Files in `maintenance/` directory
**Key Indicators**: Maintenance, repair, upkeep, servicing

### DISPOSAL_INSTRUCTIONS
**Purpose**: Instructions for disposing of the hardware
**Target Audience**: End users disposing of the hardware
**Examples**:
- `DISPOSAL.md`, `disposal_guide.pdf`
- Files in `disposal/` directory
**Key Indicators**: Disposal, recycling, end-of-life

### RISK_ASSESSMENT
**Purpose**: Risk assessment and safety documentation
**Target Audience**: Safety officers, users
**Examples**:
- `RISK_ASSESSMENT.md`, `safety_analysis.pdf`
- Files in `safety/`, `risk/` directories
**Key Indicators**: Risk, safety, hazard, assessment

## Exclusion Rules

**EXCLUDE** the following files (do not categorize them):
- **Workflow files**: `.github/workflows/`, `.gitlab-ci.yml`, CI/CD configs
- **Correspondence**: Cover letters, responses to reviewers (unless they're publications)
- **Raw test data**: Spectrum files, test results (unless they're validation reports)
- **Build artifacts**: Compiled files, generated files (unless they're manufacturing outputs)
- **Version control**: `.git/`, `.gitignore`, `.gitattributes`
- **IDE files**: `.vscode/`, `.idea/`, editor configs

**INCLUDE** the following (do not exclude):
- Academic publications (categorize as PUBLICATIONS)
- Validation reports (categorize as TECHNICAL_SPECIFICATIONS)
- Documentation files (categorize appropriately)"""

    @staticmethod
    def _build_decision_criteria_section() -> str:
        """Build the decision criteria section."""
        return """## Decision Criteria

When making your categorization decision, consider:

1. **Content Analysis**: What does the file content actually say? Does it match the suggested category?
2. **Context**: What directory is it in? What other files are nearby?
3. **Purpose**: What is the file's intended purpose? Who is the target audience?
4. **File Type**: What is the file extension? Is it a source file or output file?
5. **Layer 1 Confidence**: If Layer 1 confidence is high (>0.8), the suggestion is likely correct. If low (<0.5), review carefully.
6. **Edge Cases**: 
   - `.scad` files → DESIGN_FILES (source CAD)
   - `.stl` files → MANUFACTURING_FILES (3D printing format)
   - `.3mf` files → MANUFACTURING_FILES (manufacturing format)
   - `README.md` in root → DOCUMENTATION_HOME
   - `README.md` in subdirectory → May be DOCUMENTATION_HOME or MAKING_INSTRUCTIONS depending on content
   - Files in `publication/` → PUBLICATIONS (unless they're correspondence)
   - Files in `testing/` → TECHNICAL_SPECIFICATIONS if documentation, EXCLUDE if raw data

**Priority Order**:
1. **High-confidence Layer 1 suggestions (>0.8)**: These are usually correct based on clear patterns (file extensions, directory paths). Only override if content clearly contradicts the suggestion.
2. Content purpose: What does the file content actually say?
3. Directory context: What directory is it in? What other files are nearby?
4. Filename patterns: What does the filename suggest?
5. File extension: What does the extension indicate?
6. **Low-confidence Layer 1 suggestions (<0.5)**: These are fallback defaults. Review carefully and override if needed.

**Critical Rules**:
- If Layer 1 suggests MANUFACTURING_FILES with confidence >0.8 (e.g., `.stl`, `.3mf` files), **DO NOT override** unless content clearly shows it's not a manufacturing file.
- If Layer 1 suggests PUBLICATIONS with confidence >0.8 (e.g., files in `publication/` directory), **DO NOT override** unless it's clearly correspondence (cover letters, responses to reviewers).
- If Layer 1 suggests DESIGN_FILES with confidence >0.8 (e.g., `.scad` files), **DO NOT override** unless content clearly shows it's not a design file.
- If Layer 1 suggests exclusion, **DO NOT override** - excluded files should not be categorized."""

    @staticmethod
    def _build_output_format_section() -> str:
        """Build the output format section."""
        return """## Output Format

Provide your categorization decision in the following JSON format:

```json
{
  "documentation_type": "making-instructions",
  "confidence": 0.9,
  "excluded": false,
  "reason": "File contains step-by-step assembly instructions for humans to follow",
  "overrides_layer1": false
}
```

**Fields**:
- `documentation_type`: One of the DocumentationType values (e.g., "making-instructions", "manufacturing-files", "design-files", etc.)
- `confidence`: Your confidence in this categorization (0.0 to 1.0)
- `excluded`: `true` if file should be excluded from OKH documentation, `false` otherwise
- `reason`: Brief explanation of your decision
- `overrides_layer1`: `true` if you're overriding Layer 1 suggestion, `false` if you agree with it

**Important**:
- Return ONLY valid JSON, no additional text
- Use the exact DocumentationType values (lowercase with hyphens)
- If excluded=true, documentation_type can be any value (it won't be used)
- Be specific in your reason - it helps with debugging and improvement"""
