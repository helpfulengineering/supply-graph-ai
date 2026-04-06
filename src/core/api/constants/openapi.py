"""Reusable OpenAPI response maps for API routers."""

BAD_REQUEST = {400: {"description": "Bad Request"}}
UNAUTHORIZED = {401: {"description": "Unauthorized"}}
NOT_FOUND = {404: {"description": "Not Found"}}
VALIDATION_ERROR = {422: {"description": "Validation Error"}}
INTERNAL_SERVER_ERROR = {500: {"description": "Internal Server Error"}}

RESPONSES_400_500 = {
    **BAD_REQUEST,
    **INTERNAL_SERVER_ERROR,
}

RESPONSES_400_401_500 = {
    **BAD_REQUEST,
    **UNAUTHORIZED,
    **INTERNAL_SERVER_ERROR,
}

RESPONSES_400_422_500 = {
    **BAD_REQUEST,
    **VALIDATION_ERROR,
    **INTERNAL_SERVER_ERROR,
}

RESPONSES_400_401_422_500 = {
    **BAD_REQUEST,
    **UNAUTHORIZED,
    **VALIDATION_ERROR,
    **INTERNAL_SERVER_ERROR,
}

RESPONSES_400_401_404_422_500 = {
    **BAD_REQUEST,
    **UNAUTHORIZED,
    **NOT_FOUND,
    **VALIDATION_ERROR,
    **INTERNAL_SERVER_ERROR,
}
