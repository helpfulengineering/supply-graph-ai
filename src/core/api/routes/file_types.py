"""API routes for file type taxonomy."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from src.core.api.constants.openapi import RESPONSES_400_500
from src.core.api.error_handlers import create_success_response
from src.core.taxonomy.file_type_taxonomy import (
    DEFAULT_FILE_TYPES_PATH,
    file_type_taxonomy,
    load_from_yaml,
    validate_definitions,
)

router = APIRouter(
    prefix="/api/file-types",
    tags=["file-types"],
    responses=RESPONSES_400_500,
)


@router.get(
    "",
    summary="Get file type taxonomy",
    description="Returns all file types in the current taxonomy.",
)
async def get_file_types(http_request: Request = None) -> Any:
    all_ids = sorted(file_type_taxonomy.get_all_canonical_ids())
    file_types = []
    for cid in all_ids:
        defn = file_type_taxonomy.get_definition(cid)
        if not defn:
            continue
        file_types.append(
            {
                "canonical_id": defn.canonical_id,
                "display_name": defn.display_name,
                "parent": defn.parent,
                "extensions": sorted(defn.extensions),
                "mime_types": sorted(defn.mime_types),
                "okh_role": defn.okh_role,
                "render_tier": defn.render_tier,
            }
        )

    return create_success_response(
        message="File type taxonomy retrieved successfully",
        data={
            "total": len(file_types),
            "source": str(file_type_taxonomy._source_path or "built-in"),
            "file_types": file_types,
        },
        request_id=(
            getattr(http_request.state, "request_id", None) if http_request else None
        ),
    )


@router.get(
    "/validate",
    summary="Validate file type taxonomy YAML",
)
async def validate_file_types(http_request: Request = None) -> Any:
    path = DEFAULT_FILE_TYPES_PATH
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File types YAML not found: {path}",
        )

    try:
        definitions = load_from_yaml(path)
    except Exception as e:
        return create_success_response(
            message="File type taxonomy validation completed",
            data={
                "valid": False,
                "total_file_types": 0,
                "errors": [f"Failed to parse YAML: {e}"],
                "source": str(path),
            },
            request_id=(
                getattr(http_request.state, "request_id", None)
                if http_request
                else None
            ),
        )

    errors = validate_definitions(definitions)
    return create_success_response(
        message="File type taxonomy validation completed",
        data={
            "valid": len(errors) == 0,
            "total_file_types": len(definitions),
            "errors": errors,
            "source": str(path),
        },
        request_id=(
            getattr(http_request.state, "request_id", None) if http_request else None
        ),
    )
