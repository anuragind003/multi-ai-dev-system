from datetime import date, datetime
import re
from typing import Optional, Literal, Dict, Any, List

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

# Define allowed values for enums/literals based on BRD and DB schema
OFFER_STATUS_TYPES = Literal["Active", "Inactive", "Expired", "Duplicate"]
OFFER_TYPES = Literal["Fresh", "Enrich", "New-old", "New-new"]
PRODUCT_TYPES = Literal[
    "Loyalty", "Preapproved", "E-aggregator", "Insta", "Top-up", "Employee Loan"
]

class CustomerBase(BaseModel):
    """Base Pydantic model for customer identification data."""
    mobile_number: Optional[str] = Field(
        None,
        pattern=r"^\d{10}$",
        description="10-digit mobile number"
    )
    pan_number: Optional[str] = Field(
        None,
        pattern=r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$",
        description="10-character PAN number (e.g., ABCDE1234F)"
    )
    aadhaar_ref_number: Optional[str] = Field(
        None,
        pattern=r"^\d{12}$",
        description="12-digit Aadhaar reference number"
    )
    ucid_number: Optional[str] = Field(
        None,
        max_length=50,
        description="Unique Customer ID number"
    )
    previous_loan_app_number: Optional[str] = Field(
        None,
        max_length=50,
        description="Previous loan application number"
    )

    @model_validator(mode='after')
    def check_at_least_one_identifier(self) -> 'CustomerBase':
        """
        Ensures at least one primary customer identifier is provided.
        (FR3: deduplication based on Mobile, PAN, Aadhaar, UCID, or previous loan app number)
        """
        if not any([self.mobile_number, self.pan_number, self.aadhaar_ref_number, self.ucid_number, self.previous_loan_app_number]):
            raise ValueError("At least one customer identifier (mobile, PAN, Aadhaar, UCID, previous loan app number) must be provided.")
        return self

class OfferBase(BaseModel):
    """Base Pydantic model for offer details."""
    offer_type: OFFER_TYPES
    offer_status: OFFER_STATUS_TYPES
    product_type: PRODUCT_TYPES
    offer_start_date: date
    offer_end_date: date
    offer_details: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Flexible storage for offer specific data"
    )

    @field_validator('offer_start_date', 'offer_end_date', mode='before')
    @classmethod
    def parse_date_strings(cls, v: Any) -> date:
        """
        Parses date strings into date objects, supporting YYYY-MM-DD and DD-MM-YYYY formats.
        """
        if isinstance(v, str):
            # Try YYYY-MM-DD first (ISO format)
            try:
                return date.fromisoformat(v)
            except ValueError:
                # Then try DD-MM-YYYY
                try:
                    return datetime.strptime(v, "%d-%m-%Y").date()
                except ValueError:
                    raise ValueError(f"Invalid date format: {v}. Expected YYYY-MM-DD or DD-MM-YYYY.")
        if isinstance(v, date):
            return v
        raise ValueError(f"Expected date or date string, got {type(v)}")

    @model_validator(mode='after')
    def check_offer_dates(self) -> 'OfferBase':
        """
        Ensures offer end date is not before offer start date.
        """
        if self.offer_start_date and self.offer_end_date and self.offer_start_date > self.offer_end_date:
            raise ValueError("Offer end date cannot be before offer start date.")
        return self

class LeadCreate(CustomerBase):
    """Pydantic model for the /api/v1/leads endpoint request body."""
    loan_product: PRODUCT_TYPES
    offer_details: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Flexible storage for offer specific data"
    )

class AdminOfferUploadRow(CustomerBase, OfferBase):
    """
    Pydantic model for a single row in the admin portal's customer offer upload file.
    Combines customer identification and offer details.
    """
    pass

class DataValidator:
    """
    Utility class for performing data validation using Pydantic models.
    This class encapsulates validation logic for various data inputs,
    ensuring data integrity as per FR1 and NFR3.
    """

    def validate_lead_data(self, data: Dict[str, Any]) -> tuple[Optional[LeadCreate], Optional[List[Dict[str, Any]]]]:
        """
        Validates lead creation data against the LeadCreate Pydantic model.
        Used for real-time data from Insta or E-aggregators (FR11, FR12).

        Args:
            data (Dict[str, Any]): The raw data dictionary to validate.

        Returns:
            tuple[Optional[LeadCreate], Optional[List[Dict[str, Any]]]]:
                A tuple containing the validated LeadCreate object if successful,
                and a list of error dictionaries if validation fails.
        """
        try:
            validated_data = LeadCreate(**data)
            return validated_data, None
        except ValidationError as e:
            return None, e.errors()
        except Exception as e:
            # Catch any other unexpected errors during model instantiation
            return None, [{"loc": ["_general"], "msg": str(e), "type": "unexpected_error"}]

    def validate_admin_offer_upload_row(self, row_data: Dict[str, Any], row_number: int = 0) -> tuple[Optional[AdminOfferUploadRow], Optional[List[Dict[str, Any]]]]:
        """
        Validates a single row of data from an admin offer upload file.
        Used for bulk uploads via Admin Portal (FR43, FR46).

        Args:
            row_data (Dict[str, Any]): The raw data dictionary for a single row.
            row_number (int): The row number in the original file for error reporting.

        Returns:
            tuple[Optional[AdminOfferUploadRow], Optional[List[Dict[str, Any]]]]:
                A tuple containing the validated AdminOfferUploadRow object if successful,
                and a list of error dictionaries if validation fails, formatted for error file generation.
        """
        try:
            validated_data = AdminOfferUploadRow(**row_data)
            return validated_data, None
        except ValidationError as e:
            errors = []
            for error in e.errors():
                error_loc = error.get("loc", [])
                error_msg = error.get("msg", "Validation error")
                error_type = error.get("type", "value_error")
                errors.append({
                    "row": row_number,
                    "field": ".".join(map(str, error_loc)),
                    "error_description": error_msg,
                    "error_type": error_type
                })
            return None, errors
        except Exception as e:
            return None, [{
                "row": row_number,
                "field": "_general",
                "error_description": str(e),
                "error_type": "unexpected_error"
            }]