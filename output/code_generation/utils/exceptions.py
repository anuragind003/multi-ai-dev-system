from typing import List, Dict, Any

class BaseAppException(Exception):
    """Base class for custom application exceptions."""
    def __init__(self, detail: str, code: str = None):
        self.detail = detail
        self.code = code
        super().__init__(self.detail)

class NotFoundException(BaseAppException):
    """Exception raised when a requested resource is not found."""
    def __init__(self, detail: str = "Resource not found."):
        super().__init__(detail, code="NOT_FOUND")

class UnauthorizedException(BaseAppException):
    """Exception raised for authentication failures."""
    def __init__(self, detail: str = "Authentication required or invalid credentials."):
        super().__init__(detail, code="UNAUTHORIZED")

class ForbiddenException(BaseAppException):
    """Exception raised for authorization failures (insufficient permissions)."""
    def __init__(self, detail: str = "You do not have permission to perform this action."):
        super().__init__(detail, code="FORBIDDEN")

class CustomValidationException(BaseAppException):
    """Exception raised for business logic validation errors."""
    def __init__(self, detail: str = "Validation failed.", errors: List[Dict[str, Any]] = None):
        super().__init__(detail, code="VALIDATION_ERROR")
        self.errors = errors if errors is not None else []

class ServiceException(BaseAppException):
    """Generic exception for errors occurring in the business logic/service layer."""
    def __init__(self, detail: str = "An error occurred in the service layer."):
        super().__init__(detail, code="SERVICE_ERROR")

class FileOperationException(BaseAppException):
    """Exception raised for errors during file system operations (e.g., NFS access)."""
    def __init__(self, detail: str = "A file operation failed."):
        super().__init__(detail, code="FILE_OPERATION_ERROR")