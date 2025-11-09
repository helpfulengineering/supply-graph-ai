"""
File Content Parser utility for file categorization.

This module provides utilities for parsing file content at different
analysis depths for LLM-based file categorization.
"""

import logging
from typing import Optional
from pathlib import Path

from ..models import FileInfo, AnalysisDepth

logger = logging.getLogger(__name__)


class FileContentParser:
    """
    Utility for parsing file content based on analysis depth.
    
    This class provides methods to extract file content at different
    depth levels (Shallow/Medium/Deep) for LLM-based categorization.
    It handles both text files and binary files (with text extraction).
    """
    
    # Depth limits in characters
    SHALLOW_LIMIT = 500
    MEDIUM_LIMIT = 2000
    
    def parse_content(
        self,
        file_info: FileInfo,
        depth: AnalysisDepth
    ) -> Optional[str]:
        """
        Parse file content based on analysis depth.
        
        Args:
            file_info: File to parse
            depth: Analysis depth level (Shallow/Medium/Deep)
            
        Returns:
            Parsed content string or None if not parseable
            
        Behavior:
            - Text files (.md, .txt, .rst): Extract content based on depth
            - Binary files (PDF, DOCX): Attempt text extraction, return None if fails
            - Logs skipped files for visibility
        """
        # Handle None content
        if file_info.content is None:
            # Try binary extraction for binary file types
            if self._is_binary_file(file_info):
                return self.extract_binary_text(file_info)
            return None
        
        # Handle empty content
        if not file_info.content:
            return ""
        
        # Apply depth limits
        if depth == AnalysisDepth.SHALLOW:
            return file_info.content[:self.SHALLOW_LIMIT]
        elif depth == AnalysisDepth.MEDIUM:
            return file_info.content[:self.MEDIUM_LIMIT]
        elif depth == AnalysisDepth.DEEP:
            return file_info.content
        else:
            # Default to shallow
            logger.warning(f"Unknown depth {depth}, defaulting to shallow")
            return file_info.content[:self.SHALLOW_LIMIT]
    
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
            - PDF: Extract text content (TODO: implement PDF extraction)
            - DOCX: Extract text content (TODO: implement DOCX extraction)
            - Other binary: Returns None, logs attempt
        """
        file_path = Path(file_info.path)
        file_ext = file_path.suffix.lower()
        
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
        
        # Other binary formats - not supported yet
        logger.debug(f"Binary file type {file_ext} not supported for text extraction: {file_info.path}")
        return None
    
    def _is_binary_file(self, file_info: FileInfo) -> bool:
        """
        Check if file is a binary file type.
        
        Args:
            file_info: File to check
            
        Returns:
            True if file is binary, False otherwise
        """
        file_path = Path(file_info.path)
        file_ext = file_path.suffix.lower()
        
        # Binary file extensions
        binary_extensions = {
            '.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt',
            '.zip', '.tar', '.gz', '.rar', '.7z',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',
            '.mp3', '.mp4', '.avi', '.mov',
            '.exe', '.dll', '.so', '.dylib',
            '.bin', '.dat'
        }
        
        # Check file type
        binary_file_types = {'pdf', 'image', 'binary', 'archive', 'video', 'audio'}
        
        return file_ext in binary_extensions or file_info.file_type in binary_file_types

