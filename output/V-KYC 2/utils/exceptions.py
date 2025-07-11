from fastapi import HTTPException, status

class CustomHTTPException(HTTPException):
    """Base class for custom HTTP exceptions."""
    def __init__(self, status_code: int, detail: str, headers: dict = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)

class HTTPUnauthorized(CustomHTTPException):
    """Exception for unauthorized access (401)."""
    def __init__(self, detail: str = "Could not validate credentials", headers: dict = None):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers=headers)

class HTTPForbidden(CustomHTTPException):
    """Exception for forbidden access (403)."""
    def __init__(self, detail: str = "Not enough permissions", headers: dict = None):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail, headers=headers)

class HTTPNotFound(CustomHTTPException):
    """Exception for resource not found (404)."""
    def __init__(self, detail: str = "Resource not found", headers: dict = None):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail, headers=headers)

class HTTPBadRequest(CustomHTTPException):
    """Exception for bad request (400)."""
    def __init__(self, detail: str = "Bad request", headers: dict = None):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail, headers=headers)

class HTTPConflict(CustomHTTPException):
    """Exception for conflict (409)."""
    def __init__(self, detail: str = "Conflict", headers: dict = None):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail, headers=headers)