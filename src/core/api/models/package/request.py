from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Optional, Any

from ..base import BaseAPIRequest, LLMRequestMixin

class PackageBuildRequest(BaseAPIRequest, LLMRequestMixin):
    """Request model for building a package from manifest data"""
    # Core package fields
    manifest_data: Dict[str, Any] = Field(..., min_length=1, description="OKH manifest data")
    options: Optional[Dict[str, Any]] = Field(None, description="Build options")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "manifest_data": {
                    "title": "Test Package",
                    "version": "1.0.0",
                    "manufacturing_specs": {
                        "process_requirements": [
                            {"process_name": "3D Printing", "parameters": {}}
                        ]
                    }
                },
                "options": {
                    "include_dependencies": True,
                    "compress_output": True
                },
                "use_llm": True,
                "llm_provider": "anthropic",
                "llm_model": "claude-sonnet-4-5",
                "quality_level": "professional",
                "strict_mode": False
            }
        }
    )

class PackagePushRequest(BaseModel):
    """Request model for pushing a package to remote storage"""
    # Required fields
    package_name: str = Field(..., description="Package name (e.g., 'org/project')")
    version: str = Field(..., description="Package version")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "package_name": "example/test-package",
                "version": "1.0.0"
            }
        }
    )

class PackagePullRequest(BaseModel):
    """Request model for pulling a package from remote storage"""
    # Required fields
    package_name: str = Field(..., description="Package name (e.g., 'org/project')")
    version: str = Field(..., description="Package version")
    
    # Optional fields
    output_dir: Optional[str] = Field(None, description="Output directory for the pulled package")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "package_name": "example/test-package",
                "version": "1.0.0",
                "output_dir": "/path/to/output"
            }
        }
    )
