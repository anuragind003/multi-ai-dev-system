class CDPException(Exception):
    """Base exception for the CDP application."""
    def __init__(self, message: str = "An unexpected error occurred in CDP.", status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class CustomerNotFoundException(CDPException):
    """Exception raised when a customer is not found."""
    def __init__(self, customer_identifier: str = "customer", status_code: int = 404):
        super().__init__(f"Customer with identifier '{customer_identifier}' not found.", status_code)

class OfferNotFoundException(CDPException):
    """Exception raised when an offer is not found."""
    def __init__(self, offer_identifier: str = "offer", status_code: int = 404):
        super().__init__(f"Offer with identifier '{offer_identifier}' not found.", status_code)

class DeduplicationConflictException(CDPException):
    """Exception raised when a new customer/offer conflicts with existing records due to deduplication rules."""
    def __init__(self, message: str = "Deduplication conflict detected. Customer already exists.", status_code: int = 409):
        super().__init__(message, status_code)

class OfferPrecedenceConflictException(CDPException):
    """Exception raised when a new offer violates offer precedence rules."""
    def __init__(self, message: str = "New offer violates existing offer precedence rules.", status_code: int = 409):
        super().__init__(message, status_code)

class OfferModificationForbiddenException(CDPException):
    """Exception raised when an attempt is made to modify an offer with an active loan application journey."""
    def __init__(self, message: str = "Offer modification forbidden: Loan application journey has started.", status_code: int = 403):
        super().__init__(message, status_code)

class DNDCustomerException(CDPException):
    """Exception raised when an operation is attempted on a Do Not Disturb (DND) customer."""
    def __init__(self, message: str = "Operation forbidden for DND customer.", status_code: int = 403):
        super().__init__(message, status_code)

class InvalidFileFormatException(CDPException):
    """Exception raised for invalid file formats during upload/download."""
    def __init__(self, message: str = "Invalid file format. Please upload a valid file.", status_code: int = 400):
        super().__init__(message, status_code)

class DataValidationException(CDPException):
    """Exception raised for business-level data validation failures."""
    def __init__(self, message: str = "Data validation failed.", status_code: int = 400):
        super().__init__(message, status_code)

class ExternalServiceException(CDPException):
    """Exception raised when there's an issue communicating with an external service."""
    def __init__(self, service_name: str = "External Service", detail: str = "Communication error.", status_code: int = 503):
        super().__init__(f"{service_name} error: {detail}", status_code)

class FileProcessingException(CDPException):
    """Exception raised for errors during file processing (e.g., reading, writing, parsing)."""
    def __init__(self, message: str = "Error processing file.", status_code: int = 500):
        super().__init__(message, status_code)

class DatabaseOperationException(CDPException):
    """Exception raised for specific database operation failures."""
    def __init__(self, message: str = "Database operation failed.", status_code: int = 500):
        super().__init__(message, status_code)