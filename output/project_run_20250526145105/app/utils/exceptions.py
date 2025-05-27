class CDPException(Exception):
    """Base exception for the Customer Data Platform."""
    def __init__(self, detail: str = "An unexpected error occurred in CDP."):
        self.detail = detail
        super().__init__(self.detail)

class CustomerNotFoundException(CDPException):
    """Exception raised when a customer is not found."""
    def __init__(self, customer_identifier: str):
        super().__init__(f"Customer with identifier '{customer_identifier}' not found.")
        self.customer_identifier = customer_identifier

class OfferNotFoundException(CDPException):
    """Exception raised when an offer is not found."""
    def __init__(self, offer_id: str):
        super().__init__(f"Offer with ID '{offer_id}' not found.")
        self.offer_id = offer_id

class DuplicateCustomerException(CDPException):
    """Exception raised when a customer record already exists based on deduplication criteria."""
    def __init__(self, identifier_type: str, identifier_value: str):
        super().__init__(f"Customer already exists with {identifier_type}: '{identifier_value}'.")
        self.identifier_type = identifier_type
        self.identifier_value = identifier_value

class OfferAlreadyStartedException(CDPException):
    """Exception raised when an operation is attempted on an offer whose journey has already started."""
    def __init__(self, offer_id: str):
        super().__init__(f"Offer with ID '{offer_id}' has an ongoing journey and cannot be modified.")
        self.offer_id = offer_id

class InvalidOfferStateException(CDPException):
    """Exception raised when an operation is attempted on an offer in an invalid state."""
    def __init__(self, offer_id: str, current_state: str, required_state: str = None):
        if required_state:
            super().__init__(f"Offer with ID '{offer_id}' is in '{current_state}' state, but '{required_state}' is required.")
        else:
            super().__init__(f"Operation not allowed for offer with ID '{offer_id}' in '{current_state}' state.")
        self.offer_id = offer_id
        self.current_state = current_state
        self.required_state = required_state

class DNDCustomerException(CDPException):
    """Exception raised when an operation is attempted on a Do Not Disturb (DND) customer."""
    def __init__(self, customer_id: str):
        super().__init__(f"Operation not allowed for DND customer with ID '{customer_id}'.")
        self.customer_id = customer_id

class FileUploadException(CDPException):
    """Exception raised for errors during file upload processing."""
    def __init__(self, filename: str, reason: str = "unknown error"):
        super().__init__(f"File '{filename}' upload failed: {reason}.")
        self.filename = filename
        self.reason = reason

class DataValidationException(CDPException):
    """Exception raised for business-level data validation failures."""
    def __init__(self, field: str, value: any, reason: str):
        super().__init__(f"Data validation failed for field '{field}' with value '{value}': {reason}.")
        self.field = field
        self.value = value
        self.reason = reason

class ExternalServiceException(CDPException):
    """Exception raised when an external service integration fails."""
    def __init__(self, service_name: str, original_error: str = "unknown error"):
        super().__init__(f"External service '{service_name}' failed: {original_error}.")
        self.service_name = service_name
        self.original_error = original_error

class BusinessRuleViolationException(CDPException):
    """Exception raised when a core business rule is violated."""
    def __init__(self, rule_name: str, detail: str):
        super().__init__(f"Business rule '{rule_name}' violated: {detail}.")
        self.rule_name = rule_name
        self.detail = detail