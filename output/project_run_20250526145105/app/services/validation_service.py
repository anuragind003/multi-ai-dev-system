from datetime import date
import re
from typing import Dict, Any, List, Optional, Tuple

from pydantic import BaseModel, Field, ValidationError, validator


class CustomerBaseData(BaseModel):
    """
    Pydantic model for basic customer identification data.
    Used for strict validation of real-time API inputs.
    """
    mobile_number: Optional[str] = Field(None, min_length=10, max_length=10)
    pan_number: Optional[str] = Field(None, min_length=10, max_length=10)
    aadhaar_ref_number: Optional[str] = Field(None, min_length=12, max_length=12)
    ucid_number: Optional[str] = Field(None, max_length=50)
    previous_loan_app_number: Optional[str] = Field(None, max_length=50)

    @validator('mobile_number')
    def validate_mobile_number_format(cls, v):
        if v is not None and not v.isdigit():
            raise ValueError('Mobile number must contain only digits.')
        return v

    @validator('pan_number')
    def validate_pan_number_format(cls, v):
        # PAN format: 5 uppercase alphabets, 4 digits, 1 uppercase alphabet
        if v is not None and not re.fullmatch(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', v):
            raise ValueError('PAN number must be 10 alphanumeric characters (e.g., ABCDE1234F).')
        return v.upper() if v else v

    @validator('aadhaar_ref_number')
    def validate_aadhaar_ref_number_format(cls, v):
        if v is not None and not v.isdigit():
            raise ValueError('Aadhaar reference number must contain only digits.')
        return v


class OfferBaseData(BaseModel):
    """
    Pydantic model for basic offer data.
    Used for strict validation of real-time API inputs or internal offer creation.
    All fields are required for this base model.
    """
    offer_type: str = Field(..., max_length=50)
    offer_status: str = Field(..., max_length=50)
    product_type: str = Field(..., max_length=50)
    offer_start_date: date
    offer_end_date: date

    @validator('offer_end_date')
    def validate_offer_dates(cls, v, values):
        if 'offer_start_date' in values and values['offer_start_date'] and v < values['offer_start_date']:
            raise ValueError('Offer end date cannot be before offer start date.')
        return v

    @validator('offer_type')
    def validate_offer_type_enum(cls, v):
        valid_types = ['Fresh', 'Enrich', 'New-old', 'New-new']
        if v not in valid_types:
            raise ValueError(f"Invalid offer_type. Must be one of {valid_types}")
        return v

    @validator('offer_status')
    def validate_offer_status_enum(cls, v):
        valid_statuses = ['Active', 'Inactive', 'Expired', 'Duplicate']
        if v not in valid_statuses:
            raise ValueError(f"Invalid offer_status. Must be one of {valid_statuses}")
        return v

    @validator('product_type')
    def validate_product_type_enum(cls, v):
        # Based on FRs like FR19, FR25, FR43
        valid_products = ['Loyalty', 'Preapproved', 'E-aggregator', 'Insta', 'Top-up', 'Employee Loan', 'Prospect', 'TW-L']
        if v not in valid_products:
            raise ValueError(f"Invalid product_type. Must be one of {valid_products}")
        return v


class CustomerOfferUploadRow(BaseModel):
    """
    Pydantic model for a single row from an uploaded customer offer file.
    All fields are Optional here to allow Pydantic to parse rows even with missing data,
    so that the service can report specific errors for each missing/invalid field.
    Specific business rules (e.g., required fields) are applied in the service method.
    """
    mobile_number: Optional[str] = Field(None, min_length=10, max_length=10)
    pan_number: Optional[str] = Field(None, min_length=10, max_length=10)
    aadhaar_ref_number: Optional[str] = Field(None, min_length=12, max_length=12)
    ucid_number: Optional[str] = Field(None, max_length=50)
    previous_loan_app_number: Optional[str] = Field(None, max_length=50)
    offer_type: Optional[str] = Field(None, max_length=50)
    offer_status: Optional[str] = Field(None, max_length=50)
    product_type: Optional[str] = Field(None, max_length=50)
    offer_start_date: Optional[date] = None
    offer_end_date: Optional[date] = None

    @validator('mobile_number')
    def validate_mobile_number_format_upload(cls, v):
        if v is not None and not v.isdigit():
            raise ValueError('Mobile number must contain only digits.')
        return v

    @validator('pan_number')
    def validate_pan_number_format_upload(cls, v):
        if v is not None and not re.fullmatch(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', v):
            raise ValueError('PAN number must be 10 alphanumeric characters (e.g., ABCDE1234F).')
        return v.upper() if v else v

    @validator('aadhaar_ref_number')
    def validate_aadhaar_ref_number_format_upload(cls, v):
        if v is not None and not v.isdigit():
            raise ValueError('Aadhaar reference number must contain only digits.')
        return v

    @validator('offer_end_date')
    def validate_offer_dates_upload(cls, v, values):
        # This validator runs if offer_end_date is successfully parsed as a date.
        if 'offer_start_date' in values and values['offer_start_date'] and v and v < values['offer_start_date']:
            raise ValueError('Offer end date cannot be before offer start date.')
        return v

    @validator('offer_type')
    def validate_offer_type_enum_upload(cls, v):
        if v is not None:
            valid_types = ['Fresh', 'Enrich', 'New-old', 'New-new']
            if v not in valid_types:
                raise ValueError(f"Invalid offer_type. Must be one of {valid_types}")
        return v

    @validator('offer_status')
    def validate_offer_status_enum_upload(cls, v):
        if v is not None:
            valid_statuses = ['Active', 'Inactive', 'Expired', 'Duplicate']
            if v not in valid_statuses:
                raise ValueError(f"Invalid offer_status. Must be one of {valid_statuses}")
        return v

    @validator('product_type')
    def validate_product_type_enum_upload(cls, v):
        if v is not None:
            valid_products = ['Loyalty', 'Preapproved', 'E-aggregator', 'Insta', 'Top-up', 'Employee Loan', 'Prospect', 'TW-L']
            if v not in valid_products:
                raise ValueError(f"Invalid product_type. Must be one of {valid_products}")
        return v


class ValidationService:
    """
    Service class responsible for performing data validation based on business rules
    and data formats.
    """
    def __init__(self):
        pass

    def _format_validation_errors(self, e: ValidationError) -> str:
        """Helper to format Pydantic validation errors into a single string."""
        errors = []
        for error in e.errors():
            field = error['loc'][0] if error['loc'] else 'unknown_field'
            errors.append(f"{field}: {error['msg']}")
        return "; ".join(errors)

    def validate_customer_data(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates basic customer identification data for real-time API inputs.
        Requires at least one identifier (mobile_number, pan_number, aadhaar_ref_number,
        ucid_number, or previous_loan_app_number).
        """
        # Check for presence of at least one identifier first (FR3)
        customer_identifiers = [
            data.get('mobile_number'),
            data.get('pan_number'),
            data.get('aadhaar_ref_number'),
            data.get('ucid_number'),
            data.get('previous_loan_app_number')
        ]
        if not any(identifier for identifier in customer_identifiers if identifier is not None and identifier != ''):
            return False, "At least one customer identifier (mobile_number, pan_number, aadhaar_ref_number, ucid_number, or previous_loan_app_number) must be provided."

        try:
            CustomerBaseData(**data)
            return True, None
        except ValidationError as e:
            return False, self._format_validation_errors(e)
        except Exception as e:
            return False, f"Unexpected validation error: {str(e)}"

    def validate_offer_data(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates basic offer data for real-time API inputs or internal offer creation.
        All fields in OfferBaseData are required and validated for format/enum.
        """
        try:
            OfferBaseData(**data)
            return True, None
        except ValidationError as e:
            return False, self._format_validation_errors(e)
        except Exception as e:
            return False, f"Unexpected validation error: {str(e)}"

    def validate_customer_offer_upload_row(self, row_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates a single row from an uploaded customer offer file (e.g., CSV/Excel).
        This method is designed to be robust for file uploads, capturing all possible errors
        and returning a single, consolidated error description (FR46).
        """
        errors = []

        # Pre-process date strings to date objects or None for Pydantic parsing.
        # Pydantic's date type expects ISO format (YYYY-MM-DD) by default.
        processed_row_data = row_data.copy()
        for date_field in ['offer_start_date', 'offer_end_date']:
            if isinstance(processed_row_data.get(date_field), str) and processed_row_data[date_field]:
                try:
                    processed_row_data[date_field] = date.fromisoformat(processed_row_data[date_field])
                except ValueError:
                    errors.append(f"{date_field}: Invalid date format. Expected YYYY-MM-DD.")
                    processed_row_data[date_field] = None  # Set to None to allow Pydantic to continue parsing other fields
            elif processed_row_data.get(date_field) == '':  # Handle empty strings for dates
                processed_row_data[date_field] = None

        # 1. Pydantic parsing for basic type, format, and enum validation (FR1, NFR3)
        validated_data: Optional[CustomerOfferUploadRow] = None
        try:
            validated_data = CustomerOfferUploadRow(**processed_row_data)
        except ValidationError as e:
            errors.extend([f"{error['loc'][0] if error['loc'] else 'unknown_field'}: {error['msg']}" for error in e.errors()])
            # If Pydantic validation fails, some fields might be missing or invalid.
            # We still need to proceed with business logic checks based on what could be parsed.
            # `construct` creates a model without validation, allowing access to parsed (or None) values.
            validated_data = CustomerOfferUploadRow.construct(**{k: v for k, v in processed_row_data.items() if k in CustomerOfferUploadRow.__fields__})
        except Exception as e:
            return False, f"Unexpected error during initial row parsing: {str(e)}"

        # 2. Business-specific validations (required fields, cross-field logic)
        if validated_data:
            # FR3: At least one customer identifier must be present for a valid customer record
            customer_identifiers = [
                validated_data.mobile_number,
                validated_data.pan_number,
                validated_data.aadhaar_ref_number,
                validated_data.ucid_number,
                validated_data.previous_loan_app_number
            ]
            if not any(identifier for identifier in customer_identifiers if identifier is not None and identifier != ''):
                errors.append("At least one customer identifier (Mobile, PAN, Aadhaar, UCID, Previous Loan App No.) is required.")

            # FR1, NFR3: Basic column-level validation for offer fields - check for presence
            required_offer_fields = ['offer_type', 'offer_status', 'product_type', 'offer_start_date', 'offer_end_date']
            missing_offer_fields = [f for f in required_offer_fields if getattr(validated_data, f) is None or getattr(validated_data, f) == '']
            if missing_offer_fields:
                errors.append(f"Missing required offer fields: {', '.join(missing_offer_fields)}")

        if errors:
            # Use set to remove duplicates, then sort for consistent output
            return False, "; ".join(sorted(list(set(errors))))
        else:
            return True, None