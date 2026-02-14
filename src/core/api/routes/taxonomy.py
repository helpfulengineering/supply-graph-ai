"""
API routes for process taxonomy management.

Provides endpoints to query and reload the canonical manufacturing
process taxonomy at runtime.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status

from ....core.taxonomy import (
    DEFAULT_TAXONOMY_PATH,
    taxonomy,
    validate_definitions,
    load_from_yaml,
)
from ...utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/taxonomy",
    tags=["taxonomy"],
    responses={
        400: {"description": "Bad Request"},
        500: {"description": "Internal Server Error"},
    },
)


@router.get(
    "",
    summary="Get current taxonomy",
    description="Returns all processes in the current taxonomy with their definitions.",
)
async def get_taxonomy() -> Dict[str, Any]:
    """Return the full taxonomy as JSON."""
    all_ids = sorted(taxonomy.get_all_canonical_ids())

    processes = []
    for cid in all_ids:
        defn = taxonomy.get_definition(cid)
        if not defn:
            continue
        processes.append(
            {
                "canonical_id": defn.canonical_id,
                "display_name": defn.display_name,
                "tsdc_code": defn.tsdc_code,
                "parent": defn.parent,
                "aliases": sorted(defn.aliases),
                "children": sorted(taxonomy.get_children(cid)),
            }
        )

    return {
        "status": "ok",
        "data": {
            "total": len(processes),
            "source": str(taxonomy._source_path or "built-in"),
            "processes": processes,
        },
    }


@router.post(
    "/reload",
    summary="Reload taxonomy from YAML",
    description=(
        "Reload the process taxonomy from the YAML configuration file. "
        "The reload is atomic: if validation fails, the current taxonomy "
        "is preserved."
    ),
)
async def reload_taxonomy() -> Dict[str, Any]:
    """Reload the taxonomy from the default YAML file."""
    try:
        result = taxonomy.reload()
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Taxonomy YAML file not found: {e}",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Taxonomy validation failed: {e}",
        )
    except Exception as e:
        logger.error("Unexpected error reloading taxonomy: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload taxonomy: {e}",
        )

    return {
        "status": "ok",
        "message": "Taxonomy reloaded successfully",
        "data": result,
    }


@router.get(
    "/validate",
    summary="Validate taxonomy YAML",
    description="Validate the current taxonomy YAML file without applying changes.",
)
async def validate_taxonomy() -> Dict[str, Any]:
    """Validate the default YAML file and return results."""
    path = DEFAULT_TAXONOMY_PATH

    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Taxonomy YAML file not found: {path}",
        )

    try:
        definitions = load_from_yaml(path)
    except Exception as e:
        return {
            "status": "error",
            "valid": False,
            "errors": [f"Failed to parse YAML: {e}"],
        }

    errors = validate_definitions(definitions)

    return {
        "status": "ok" if not errors else "error",
        "valid": len(errors) == 0,
        "total_processes": len(definitions),
        "errors": errors,
        "source": str(path),
    }
