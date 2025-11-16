# File Processing Implementation Specification

## Overview

This specification defines the implementation plan for completing PDF and DOCX text extraction functionality in the file content parser. These features are needed to extract text content from binary document files for LLM-based categorization and analysis.

## Current State Analysis

### Issue 1: PDF Text Extraction Not Implemented

**Location**: `src/core/generation/utils/file_content_parser.py:97`

**Current Implementation:**
```python
# PDF extraction (TODO: implement with PyPDF2 or similar)
if file_ext == '.pdf':
    logger.debug(f"PDF text extraction not yet implemented for {file_info.path}")
    # TODO: Implement PDF text extraction
    # try:
    #     import PyPDF2
    #     # Extract text from PDF
    #     return extracted_text
    # except Exception as e:
    #     logger.warning(f"Failed to extract text from PDF {file_info.path}: {e}")
    return None
```

**Problems:**
- No PDF extraction logic implemented
- Returns None for all PDF files
- PDF content cannot be analyzed by LLM categorization
- Comment suggests PyPDF2 but library not in requirements

**Context:**
- Called from `extract_binary_text()` when `file_info.content` is None
- Used for LLM-based file categorization
- Needs to handle file paths (FileInfo.path contains file path)

### Issue 2: DOCX Text Extraction Not Implemented

**Location**: `src/core/generation/utils/file_content_parser.py:109`

**Current Implementation:**
```python
# DOCX extraction (TODO: implement with python-docx or similar)
if file_ext in ['.docx', '.doc']:
    logger.debug(f"DOCX text extraction not yet implemented for {file_info.path}")
    # TODO: Implement DOCX text extraction
    # try:
    #     from docx import Document
    #     # Extract text from DOCX
    #     return extracted_text
    # except Exception as e:
    #     logger.warning(f"Failed to extract text from DOCX {file_info.path}: {e}")
    return None
```

**Problems:**
- No DOCX extraction logic implemented
- Returns None for all DOCX/DOC files
- DOCX content cannot be analyzed by LLM categorization
- Comment suggests python-docx but library not in requirements
- Note: `.doc` (old format) may need different handling

**Context:**
- Called from `extract_binary_text()` when `file_info.content` is None
- Used for LLM-based file categorization
- Needs to handle file paths

### FileInfo Structure

**From `src/core/generation/models.py`:**
```python
@dataclass
class FileInfo:
    path: str  # Relative path to the file
    size: int  # File size in bytes
    content: str  # File content as string (for text files)
    file_type: str  # Detected file type
```

**Usage Pattern:**
- When file is binary, `content` is None or empty
- `extract_binary_text()` is called with FileInfo
- Method needs to read file from `path` and extract text
- Returns extracted text string or None

## Requirements

### Functional Requirements

1. **PDF Text Extraction**
   - Extract text content from PDF files
   - Handle multi-page PDFs
   - Preserve basic text structure (paragraphs, line breaks)
   - Handle encrypted/protected PDFs gracefully
   - Handle corrupted PDFs gracefully
   - Support common PDF versions

2. **DOCX Text Extraction**
   - Extract text content from DOCX files
   - Extract text from paragraphs
   - Handle tables, lists, headers/footers
   - Preserve basic text structure
   - Handle corrupted DOCX files gracefully
   - Note: `.doc` (old format) may not be supported initially

3. **Error Handling**
   - Graceful degradation on extraction failures
   - Log errors with context
   - Return None on failure (existing behavior)
   - Don't crash on corrupted files

4. **Performance**
   - Reasonable extraction time (<5s for typical documents)
   - Memory efficient (stream processing where possible)
   - Handle large files appropriately

### Non-Functional Requirements

1. **Dependencies**
   - Use well-maintained libraries
   - Minimal dependencies
   - Compatible with existing Python version

2. **Maintainability**
   - Clear error messages
   - Well-documented code
   - Easy to extend for other formats

3. **Compatibility**
   - Works with existing FileInfo structure
   - Doesn't break existing functionality
   - Backward compatible

## Design Decisions

### Library Selection

**PDF Extraction: `pypdf` (formerly PyPDF2)**
- Modern, actively maintained fork of PyPDF2
- Pure Python, no external dependencies
- Good performance and reliability
- Supports most PDF features
- Package name: `pypdf` (PyPI)

**DOCX Extraction: `python-docx`**
- Standard library for DOCX manipulation
- Well-documented and maintained
- Pure Python
- Good performance
- Package name: `python-docx` (PyPI)

**Note on `.doc` (Old Format):**
- Old Microsoft Word format (binary)
- Requires different library (`python-docx` only handles `.docx`)
- For Phase 1, only support `.docx`
- Document limitation, can add `.doc` support later if needed

### Implementation Strategy

**File Reading:**
- Read file from `file_info.path`
- Handle both absolute and relative paths
- Use async file I/O where possible (aiofiles)
- Handle file not found errors

**Text Extraction:**
- Extract all text content
- Preserve paragraph structure (double newlines)
- Remove excessive whitespace
- Limit extracted text length (for very large documents)

**Error Handling:**
- Try/except around extraction logic
- Log errors with file path and error details
- Return None on any failure
- Don't propagate exceptions

### Integration with Existing Code

**No Changes to Interface:**
- `extract_binary_text()` signature stays the same
- Returns `Optional[str]` as before
- Called from same places

**File Path Handling:**
- FileInfo.path may be relative or absolute
- Need to resolve path correctly
- Handle cases where file doesn't exist

## Implementation Specification

### 1. Update Requirements

**File: `requirements.txt`**

**Add dependencies:**

```txt
# Document text extraction
pypdf>=3.0.0  # PDF text extraction (formerly PyPDF2)
python-docx>=1.0.0  # DOCX text extraction
```

**Note:** `pypdf` is the modern fork of PyPDF2. The package name on PyPI is `pypdf`, but it's imported as `pypdf` (not `PyPDF2`).

### 2. Update File Content Parser

**File: `src/core/generation/utils/file_content_parser.py`**

**Update `extract_binary_text` method:**

```python
def extract_binary_text(
    self,
    file_info: FileInfo
) -> Optional[str]:
    """
    Attempt to extract text from binary files.
    
    Args:
        file_info: Binary file to extract text from
        
    Returns:
        Extracted text or None if extraction fails
        
    Supported formats:
        - PDF: Extract text content using pypdf
        - DOCX: Extract text content using python-docx
        - Other binary: Returns None, logs attempt
    """
    file_path = Path(file_info.path)
    file_ext = file_path.suffix.lower()
    
    # Resolve file path (handle both absolute and relative)
    try:
        if not file_path.is_absolute():
            # If relative, try to resolve from current working directory
            # This may need adjustment based on how FileInfo.path is set
            resolved_path = file_path.resolve()
        else:
            resolved_path = file_path
        
        # Check if file exists
        if not resolved_path.exists():
            logger.warning(f"File not found for text extraction: {resolved_path}")
            return None
        
        # Check file size (skip very large files to avoid memory issues)
        file_size = resolved_path.stat().st_size
        max_file_size = 50 * 1024 * 1024  # 50 MB limit
        if file_size > max_file_size:
            logger.warning(
                f"File too large for text extraction: {resolved_path} ({file_size} bytes)"
            )
            return None
        
    except Exception as e:
        logger.warning(
            f"Error resolving file path {file_info.path}: {e}",
            exc_info=True
        )
        return None
    
    # PDF extraction
    if file_ext == '.pdf':
        return self._extract_pdf_text(resolved_path)
    
    # DOCX extraction
    if file_ext in ['.docx']:
        return self._extract_docx_text(resolved_path)
    
    # DOC (old format) - not supported yet
    if file_ext == '.doc':
        logger.debug(
            f"Old .doc format not supported for text extraction: {file_info.path}. "
            "Only .docx format is supported."
        )
        return None
    
    # Other binary formats - not supported yet
    logger.debug(
        f"Binary file type {file_ext} not supported for text extraction: {file_info.path}"
    )
    return None

def _extract_pdf_text(self, file_path: Path) -> Optional[str]:
    """
    Extract text from PDF file.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Extracted text or None if extraction fails
    """
    try:
        import pypdf
        
        text_parts = []
        
        with open(file_path, 'rb') as pdf_file:
            try:
                pdf_reader = pypdf.PdfReader(pdf_file)
                
                # Check if PDF is encrypted
                if pdf_reader.is_encrypted:
                    logger.warning(
                        f"PDF is encrypted, cannot extract text: {file_path}"
                    )
                    return None
                
                # Extract text from each page
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    except Exception as e:
                        logger.warning(
                            f"Error extracting text from PDF page {page_num + 1} "
                            f"in {file_path}: {e}"
                        )
                        # Continue with other pages
                        continue
                
                if not text_parts:
                    logger.debug(f"No text found in PDF: {file_path}")
                    return None
                
                # Combine all pages with double newline separator
                extracted_text = "\n\n".join(text_parts)
                
                # Clean up excessive whitespace
                extracted_text = self._clean_extracted_text(extracted_text)
                
                logger.debug(
                    f"Successfully extracted {len(extracted_text)} characters "
                    f"from PDF: {file_path}"
                )
                
                return extracted_text
                
            except pypdf.errors.PdfReadError as e:
                logger.warning(
                    f"Error reading PDF file {file_path}: {e}",
                    exc_info=True
                )
                return None
            except Exception as e:
                logger.warning(
                    f"Unexpected error extracting text from PDF {file_path}: {e}",
                    exc_info=True
                )
                return None
                
    except ImportError:
        logger.warning(
            "pypdf library not installed. Install with: pip install pypdf"
        )
        return None
    except Exception as e:
        logger.warning(
            f"Failed to extract text from PDF {file_path}: {e}",
            exc_info=True
        )
        return None

def _extract_docx_text(self, file_path: Path) -> Optional[str]:
    """
    Extract text from DOCX file.
    
    Args:
        file_path: Path to DOCX file
        
    Returns:
        Extracted text or None if extraction fails
    """
    try:
        from docx import Document
        
        text_parts = []
        
        try:
            doc = Document(file_path)
            
            # Extract text from paragraphs
            for paragraph in doc.paragraphs:
                para_text = paragraph.text.strip()
                if para_text:
                    text_parts.append(para_text)
            
            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_texts = []
                    for cell in row.cells:
                        cell_text = cell.text.strip()
                        if cell_text:
                            row_texts.append(cell_text)
                    if row_texts:
                        text_parts.append(" | ".join(row_texts))
            
            if not text_parts:
                logger.debug(f"No text found in DOCX: {file_path}")
                return None
            
            # Combine all text parts with double newline separator
            extracted_text = "\n\n".join(text_parts)
            
            # Clean up excessive whitespace
            extracted_text = self._clean_extracted_text(extracted_text)
            
            logger.debug(
                f"Successfully extracted {len(extracted_text)} characters "
                f"from DOCX: {file_path}"
            )
            
            return extracted_text
            
        except Exception as e:
            logger.warning(
                f"Error reading DOCX file {file_path}: {e}",
                exc_info=True
            )
            return None
            
    except ImportError:
        logger.warning(
            "python-docx library not installed. Install with: pip install python-docx"
        )
        return None
    except Exception as e:
        logger.warning(
            f"Failed to extract text from DOCX {file_path}: {e}",
            exc_info=True
        )
        return None

def _clean_extracted_text(self, text: str) -> str:
    """
    Clean up extracted text by removing excessive whitespace.
    
    Args:
        text: Raw extracted text
        
    Returns:
        Cleaned text
    """
    import re
    
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    
    # Replace multiple newlines (3+) with double newline
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # Remove excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()
```

### 3. Handle Async File Reading (Optional Enhancement)

**If files are read asynchronously elsewhere, consider async version:**

```python
async def _extract_pdf_text_async(self, file_path: Path) -> Optional[str]:
    """Async version of PDF text extraction."""
    import aiofiles
    import pypdf
    import io
    
    try:
        async with aiofiles.open(file_path, 'rb') as pdf_file:
            pdf_bytes = await pdf_file.read()
            pdf_stream = io.BytesIO(pdf_bytes)
            
            pdf_reader = pypdf.PdfReader(pdf_stream)
            # ... rest of extraction logic ...
```

**Note:** For Phase 1, synchronous file reading is acceptable. Async can be added later if needed.

### 4. Update Documentation

**File: `src/core/generation/utils/file_content_parser.py`**

**Update docstrings:**

```python
"""
File Content Parser utility for file categorization.

This module provides utilities for parsing file content at different
analysis depths for LLM-based file categorization.

Supported file formats:
- Text files: .md, .txt, .rst (direct content extraction)
- PDF files: .pdf (text extraction using pypdf)
- DOCX files: .docx (text extraction using python-docx)
- Other binary files: Not supported (returns None)

Note: Old .doc format is not supported. Only .docx format is supported.
"""
```

### 5. Configuration (Optional)

**File: `src/config/settings.py`**

**Add optional settings for file extraction:**

```python
# File Processing Configuration
FILE_EXTRACTION_ENABLED = os.getenv("FILE_EXTRACTION_ENABLED", "true").lower() in ("true", "1", "t")
FILE_EXTRACTION_MAX_SIZE = int(os.getenv("FILE_EXTRACTION_MAX_SIZE", "52428800"))  # 50 MB default
```

**File: `env.template`**

**Add:**

```bash
# File Processing Configuration
FILE_EXTRACTION_ENABLED=true
FILE_EXTRACTION_MAX_SIZE=52428800  # 50 MB
```

## Integration Points

### 1. FileInfo Structure

- Uses existing `FileInfo` dataclass
- Reads from `file_info.path`
- Returns text string compatible with `file_info.content`

### 2. File Loading

- Works with files loaded by project extractors (GitHub, GitLab, Local)
- Handles both absolute and relative paths
- Compatible with async file operations

### 3. LLM Categorization

- Extracted text is used by `FileCategorizationService`
- Text is analyzed at different depths (Shallow/Medium/Deep)
- Supports LLM-based file categorization

### 4. Error Handling

- Follows existing error handling patterns
- Logs errors but doesn't crash
- Returns None on failure (existing behavior)

## Testing Considerations

### Unit Tests

1. **PDF Extraction Tests:**
   - Test basic PDF text extraction
   - Test multi-page PDF
   - Test encrypted PDF (should return None)
   - Test corrupted PDF (should return None gracefully)
   - Test file not found
   - Test large file handling

2. **DOCX Extraction Tests:**
   - Test basic DOCX text extraction
   - Test DOCX with tables
   - Test DOCX with multiple paragraphs
   - Test corrupted DOCX (should return None gracefully)
   - Test file not found

3. **Text Cleaning Tests:**
   - Test whitespace cleanup
   - Test newline normalization
   - Test empty text handling

### Integration Tests

1. **End-to-End File Processing:**
   - Test PDF file through full categorization pipeline
   - Test DOCX file through full categorization pipeline
   - Verify extracted text is used by LLM categorization

2. **Error Handling:**
   - Test missing dependencies (pypdf, python-docx)
   - Test file access errors
   - Test corrupted files

### Test Data

- Create test PDF files (simple, multi-page, encrypted)
- Create test DOCX files (simple, with tables, with formatting)
- Test with real-world documents if available

## Migration Plan

### Phase 1: Implementation (Current)
- Add pypdf and python-docx to requirements
- Implement PDF extraction
- Implement DOCX extraction
- Add error handling
- Add tests

### Phase 2: Enhancement (Future)
- Support for `.doc` format (old Word format)
- Support for other formats (ODT, RTF, etc.)
- Async file reading
- Streaming for very large files
- OCR support for scanned PDFs (optional)

## Success Criteria

1. ✅ PDF text extraction works for standard PDFs
2. ✅ DOCX text extraction works for standard DOCX files
3. ✅ Error handling is graceful (no crashes)
4. ✅ Extracted text is used by LLM categorization
5. ✅ All TODOs are resolved
6. ✅ Tests pass
7. ✅ Dependencies are documented
8. ✅ Performance is acceptable

## Open Questions / Future Enhancements

1. **Old .doc Format:**
   - Should we support old `.doc` format?
   - Would require additional library (e.g., `textract` or `antiword`)
   - For Phase 1, document limitation

2. **Other Formats:**
   - ODT (OpenDocument Text)
   - RTF (Rich Text Format)
   - XLSX (Excel) - extract text from cells
   - PPTX (PowerPoint) - extract text from slides

3. **OCR Support:**
   - Scanned PDFs (image-based)
   - Would require OCR library (e.g., `pytesseract`)
   - Significant additional complexity

4. **Performance Optimization:**
   - Caching extracted text
   - Parallel extraction for multiple files
   - Streaming for very large files

## Dependencies

### New Dependencies

- `pypdf>=3.0.0` - PDF text extraction
- `python-docx>=1.0.0` - DOCX text extraction

### Existing Dependencies

- `pathlib` - Path handling (stdlib)
- `aiofiles` - Async file I/O (already in requirements)
- `logging` - Logging (stdlib)

## Implementation Order

1. Add dependencies to `requirements.txt`
2. Implement `_extract_pdf_text()` method
3. Implement `_extract_docx_text()` method
4. Implement `_clean_extracted_text()` helper
5. Update `extract_binary_text()` to use new methods
6. Update docstrings
7. Add configuration (optional)
8. Write unit tests
9. Write integration tests
10. Update documentation

## Notes

### Library Naming

- **pypdf**: The package name on PyPI is `pypdf`, but it's the successor to PyPDF2
- Import: `import pypdf` (not `import PyPDF2`)
- The old PyPDF2 package is deprecated

### File Path Resolution

- FileInfo.path may be relative or absolute depending on context
- Need to handle both cases
- May need to adjust based on how project extractors set paths
- Consider adding path resolution helper if needed

### Memory Considerations

- PDF and DOCX files can be large
- Current implementation loads entire file into memory
- For very large files, consider streaming (Phase 2)
- 50 MB limit is reasonable for most documents

