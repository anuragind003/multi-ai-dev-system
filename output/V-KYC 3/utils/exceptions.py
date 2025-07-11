from fastapi import HTTPException, status

class HTTPUnauthorized(HTTPException):
    """Custom exception for 401 Unauthorized errors."""
    def __init__(self, detail: str = "Not authenticated", headers: dict = None):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers=headers)

class HTTPForbidden(HTTPException):
    """Custom exception for 403 Forbidden errors."""
    def __init__(self, detail: str = "Not authorized"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class HTTPNotFound(HTTPException):
    """Custom exception for 404 Not Found errors."""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class HTTPConflict(HTTPException):
    """Custom exception for 409 Conflict errors (e.g., duplicate resource)."""
    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class HTTPBadRequest(HTTPException):
    """Custom exception for 400 Bad Request errors."""
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)