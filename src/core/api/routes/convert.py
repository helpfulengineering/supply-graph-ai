"""
Convert API routes for the Open Hardware Manager.

Provides endpoints for bi-directional conversion between OKH manifests
and external document formats (currently MSF datasheets).
"""

import io
import os
import tempfile

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from ...models.okh import OKHManifest
from ...services.datasheet_converter import (
    DatasheetConversionError,
    DatasheetConverter,
)
from ...utils.logging import get_logger
from ..error_handlers import create_error_response
from ..models.convert.request import ConvertToDatasheetRequest
from ..models.convert.response import ConvertFromDatasheetResponse

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/convert",
    tags=["convert"],
    responses={
        400: {"description": "Bad Request"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"},
    },
)


def _get_converter(template_path: str = None) -> DatasheetConverter:
    """Create a DatasheetConverter instance."""
    try:
        return DatasheetConverter(template_path=template_path)
    except DatasheetConversionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Converter initialisation failed: {exc}",
        )


@router.post(
    "/to-datasheet",
    summary="Convert OKH Manifest to MSF Datasheet",
    description="""
    Convert an OKH manifest (JSON) to a populated MSF 3D-printed product
    technical specification datasheet (.docx).

    The OKH manifest is the canonical source of truth.  The response
    streams back the generated .docx file for download.

    **Workflow:**
    1. Submit the OKH manifest as the request body.
    2. Receive the populated .docx datasheet as a file download.
    """,
    responses={
        200: {
            "content": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}},
            "description": "Generated MSF datasheet as .docx download",
        },
    },
)
async def convert_to_datasheet(
    request: ConvertToDatasheetRequest,
    http_request: Request,
):
    """Convert an OKH manifest to an MSF datasheet (.docx)."""
    request_id = getattr(http_request.state, "request_id", None)

    try:
        # Build an OKHManifest from the request payload
        manifest_data = request.model_dump(
            mode="json",
            exclude={"request_id", "client_info", "quality_level", "strict_mode"},
        )
        manifest = OKHManifest.from_dict(manifest_data)

        logger.info(
            "Converting OKH manifest to datasheet",
            extra={
                "request_id": request_id,
                "manifest_title": manifest.title,
            },
        )

        # Generate the datasheet into a temporary file
        converter = _get_converter()

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            converter.okh_to_datasheet(manifest, tmp_path)

            # Read the file into memory and stream it back
            with open(tmp_path, "rb") as f:
                docx_bytes = f.read()
        finally:
            # Clean up the temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        # Build a sensible filename
        safe_title = "".join(
            c if c.isalnum() or c in "-_ " else "" for c in manifest.title
        ).strip().replace(" ", "-").lower()
        filename = f"{safe_title}-datasheet.docx" if safe_title else "datasheet.docx"

        return StreamingResponse(
            io.BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Manifest-Title": manifest.title,
                "X-Manifest-Version": manifest.version,
            },
        )

    except DatasheetConversionError as exc:
        error_response = create_error_response(
            error=exc,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            request_id=request_id,
            suggestion="Check the manifest data and try again",
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as exc:
        error_response = create_error_response(
            error=exc,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support",
        )
        logger.error(
            f"Error converting to datasheet: {exc}",
            extra={"request_id": request_id, "error": str(exc)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.post(
    "/from-datasheet",
    response_model=ConvertFromDatasheetResponse,
    summary="Convert MSF Datasheet to OKH Manifest",
    description="""
    Convert a populated MSF 3D-printed product technical specification
    datasheet (.docx) to a canonical OKH manifest.

    Upload the .docx file and receive the OKH manifest as JSON in the
    response body.

    **Workflow:**
    1. Upload the .docx datasheet file.
    2. Receive the parsed OKH manifest as JSON.
    """,
)
async def convert_from_datasheet(
    http_request: Request,
    datasheet_file: UploadFile = File(
        ..., description="MSF datasheet (.docx) to convert"
    ),
):
    """Convert an MSF datasheet (.docx) to an OKH manifest."""
    request_id = getattr(http_request.state, "request_id", None)

    try:
        # Validate file type
        if not datasheet_file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided",
            )

        if not datasheet_file.filename.lower().endswith(".docx"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .docx files are supported. Please upload an MSF datasheet.",
            )

        # Save uploaded file to a temporary location
        content = await datasheet_file.read()

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Parse the datasheet
            converter = _get_converter()
            manifest = converter.datasheet_to_okh(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        manifest_dict = manifest.to_dict()

        # Count populated fields
        fields_populated = sum(
            1
            for v in manifest_dict.values()
            if v is not None and v != "" and v != [] and v != {}
        )

        logger.info(
            "Datasheet converted to OKH manifest",
            extra={
                "request_id": request_id,
                "manifest_title": manifest.title,
                "fields_populated": fields_populated,
            },
        )

        return ConvertFromDatasheetResponse(
            success=True,
            message="Datasheet converted to OKH manifest successfully",
            manifest=manifest_dict,
            manifest_title=manifest.title,
            fields_populated=fields_populated,
            warnings=[],
        )

    except HTTPException:
        raise
    except DatasheetConversionError as exc:
        error_response = create_error_response(
            error=exc,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            request_id=request_id,
            suggestion="Ensure the file is a valid MSF datasheet (.docx)",
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as exc:
        error_response = create_error_response(
            error=exc,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support",
        )
        logger.error(
            f"Error converting from datasheet: {exc}",
            extra={"request_id": request_id, "error": str(exc)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )
