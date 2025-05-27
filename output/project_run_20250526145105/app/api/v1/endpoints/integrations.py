from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import uuid
import datetime

# --- Pydantic Models (Ideally these would be in app/schemas) ---
class LeadCreateRequest(BaseModel):
    """
    Schema for incoming real-time lead generation data.
    Corresponds to FR11 (real-time data from Insta/E-aggregators).
    """
    mobile_number: str = Field(..., max_length=20, description="Customer's mobile number.")
    pan_number: Optional[str] = Field(None, max_length=10, description="Customer's PAN number.")
    aadhaar_ref_number: Optional[str] = Field(None, max_length=12, description="Customer's Aadhaar reference number.")
    loan_product: str = Field(..., max_length=50, description="Type of loan product (e.g., 'Insta', 'E-aggregator').")
    offer_details: Dict[str, Any] = Field(default_factory=dict, description="JSON object for offer-specific details.")
    ucid_number: Optional[str] = Field(None, max_length=50, description="Customer's UCID number.")
    previous_loan_app_number: Optional[str] = Field(None, max_length=50, description="Previous loan application number.")
    customer_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional customer attributes.")


class LeadCreateResponse(BaseModel):
    """
    Schema for the response after processing a lead creation request.
    """
    status: str = Field(..., description="Status of the operation (e.g., 'success', 'failed').")
    message: str = Field(..., description="Descriptive message about the operation result.")
    customer_id: uuid.UUID = Field(..., description="Unique identifier for the customer.")


# --- Mock/Placeholder for Database Session and ORM Models ---
# In a real application, these would be imported from `app.database` and `app.models`.
# For this standalone file, we define mocks to make the code runnable.

class MockDBSession:
    """A mock database session for demonstration purposes."""
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def query(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None  # Simulate no existing customer by default

    def add(self, *args, **kwargs):
        pass

    def commit(self):
        pass

    def refresh(self, *args, **kwargs):
        pass

    def close(self):
        pass

def get_db():
    """
    Dependency to get a database session.
    In a real application, this would yield a SQLAlchemy session.
    """
    yield MockDBSession()


class MockCustomer:
    """A mock ORM model for the 'customers' table."""
    def __init__(self, **kwargs):
        self.customer_id = kwargs.get("customer_id", uuid.uuid4())
        self.mobile_number = kwargs.get("mobile_number")
        self.pan_number = kwargs.get("pan_number")
        self.aadhaar_ref_number = kwargs.get("aadhaar_ref_number")
        self.ucid_number = kwargs.get("ucid_number")
        self.previous_loan_app_number = kwargs.get("previous_loan_app_number")
        self.customer_attributes = kwargs.get("customer_attributes", {})
        self.customer_segments = kwargs.get("customer_segments", [])
        self.propensity_flag = kwargs.get("propensity_flag")
        self.dnd_status = kwargs.get("dnd_status", False)
        self.created_at = kwargs.get("created_at", datetime.datetime.now(datetime.timezone.utc))
        self.updated_at = kwargs.get("updated_at", datetime.datetime.now(datetime.timezone.utc))


class MockOffer:
    """A mock ORM model for the 'offers' table."""
    def __init__(self, **kwargs):
        self.offer_id = kwargs.get("offer_id", uuid.uuid4())
        self.customer_id = kwargs.get("customer_id")
        self.offer_type = kwargs.get("offer_type")
        self.offer_status = kwargs.get("offer_status")
        self.product_type = kwargs.get("product_type")
        self.offer_details = kwargs.get("offer_details", {})
        self.offer_start_date = kwargs.get("offer_start_date", datetime.date.today())
        self.offer_end_date = kwargs.get("offer_end_date", datetime.date.today() + datetime.timedelta(days=90))
        self.is_journey_started = kwargs.get("is_journey_started", False)
        self.loan_application_id = kwargs.get("loan_application_id")
        self.created_at = kwargs.get("created_at", datetime.datetime.now(datetime.timezone.utc))
        self.updated_at = kwargs.get("updated_at", datetime.datetime.now(datetime.timezone.utc))


# --- Mock/Placeholder for Service Layer ---
# In a real application, these would be in `app.services`.
# They encapsulate business logic and database interactions.

class MockCustomerService:
    """
    A mock service for customer-related operations, including deduplication.
    """
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_customer(
        self,
        mobile_number: str,
        pan_number: Optional[str],
        aadhaar_ref_number: Optional[str],
        ucid_number: Optional[str],
        previous_loan_app_number: Optional[str],
        customer_attributes: Optional[Dict[str, Any]]
    ) -> MockCustomer:
        """
        Performs deduplication (FR3, FR4, FR5, FR6) and returns an existing
        customer or creates a new one.
        """
        # Simulate checking for existing customer based on multiple identifiers.
        # In a real scenario, this would involve complex DB queries and potentially
        # integration with Customer 360 (FR5).
        existing_customer = None
        if mobile_number and mobile_number.endswith('00'):
            # This is a simplified mock to simulate finding an existing customer
            # based on a specific mobile number pattern.
            existing_customer = MockCustomer(
                customer_id=uuid.UUID("a1b2c3d4-e5f6-7890-1234-567890abcdef"),
                mobile_number=mobile_number,
                pan_number=pan_number,
                aadhaar_ref_number=aadhaar_ref_number,
                customer_attributes={"existing_attr": "value"},
                dnd_status=False # For testing DND, set to True if needed
            )
            print(f"Mock: Existing customer found with ID {existing_customer.customer_id}")

        if existing_customer:
            return existing_customer
        else:
            print("Mock: Creating new customer.")
            new_customer = MockCustomer(
                mobile_number=mobile_number,
                pan_number=pan_number,
                aadhaar_ref_number=aadhaar_ref_number,
                ucid_number=ucid_number,
                previous_loan_app_number=previous_loan_app_number,
                customer_attributes=customer_attributes
            )
            # In a real scenario: self.db.add(new_customer); self.db.commit(); self.db.refresh(new_customer)
            return new_customer

    def check_dnd_status(self, customer_id: uuid.UUID) -> bool:
        """
        Mocks checking DND status for a customer (FR34).
        In a real system, this would query the customer record.
        """
        # For mock, let's assume customer with specific ID is DND
        if str(customer_id) == "a1b2c3d4-e5f6-7890-1234-567890abcdef":
            return False # Example: this specific customer is not DND
        return False # Default to not DND for other mock customers


class MockOfferService:
    """
    A mock service for offer-related operations, including precedence rules.
    """
    def __init__(self, db: Session):
        self.db = db

    def process_new_offer(
        self,
        customer: MockCustomer,
        loan_product: str,
        offer_details: Dict[str, Any]
    ) -> MockOffer:
        """
        Processes a new offer, applying precedence rules (FR25-FR32)
        and updating/creating offers (FR8, FR20, FR21).
        """
        print(f"Mock: Processing new offer for customer {customer.customer_id} "
              f"for product {loan_product}")

        offer_status = "Active"
        offer_type = "Fresh"

        # Simulate complex offer precedence logic (FR25-FR32)
        # This is a highly simplified mock. Real logic would involve:
        # 1. Querying existing active offers for the customer.
        # 2. Applying a hierarchy of product types (e.g., Employee Loan > TW Loyalty > Prospect).
        # 3. Checking if a journey has started for existing offers (FR15, FR21, FR26).
        # 4. Determining if the new offer should prevail, be rejected, or mark old as duplicate.

        # Example: If an "Enrich" offer comes and no journey has started for a previous offer,
        # the previous offer is moved to "Duplicate" (FR20).
        if loan_product.lower() == "enrich":
            # Simulate finding an old offer and marking it duplicate
            print("Mock: Found an 'Enrich' offer. Simulating marking previous offer as 'Duplicate'.")
            offer_type = "Enrich"
            # In real code: update_old_offer_status(customer.customer_id, "Duplicate")
            # For this mock, we'll just create the new 'Enrich' offer.

        # Example: If a customer has an existing TWL offer and a new Insta offer comes,
        # the customer is directed to the existing offer (FR28).
        # For this mock, we'll just create the new offer, but in a real scenario,
        # this might lead to the new offer being marked 'Inactive' or 'Rejected'.
        if loan_product.lower() == "insta" and customer.mobile_number.startswith("99"):
            print("Mock: Customer has existing offer, new Insta offer might be rejected/redirected (FR28).")
            # For demonstration, we'll still create it as active, but a real system
            # might set status to 'Inactive' or raise an error.

        new_offer = MockOffer(
            customer_id=customer.customer_id,
            offer_type=offer_type,
            offer_status=offer_status,
            product_type=loan_product,
            offer_details=offer_details
        )
        # In a real scenario: self.db.add(new_offer); self.db.commit(); self.db.refresh(new_offer)
        print(f"Mock: Offer created with ID {new_offer.offer_id} and status {new_offer.offer_status}")
        return new_offer


# --- FastAPI Router and Endpoint Definition ---

router = APIRouter(
    prefix="/integrations",
    tags=["Integrations"]
)


@router.post(
    "/leads",
    response_model=LeadCreateResponse,
    status_code=status.HTTP_200_OK,
    summary="Receive real-time lead generation data",
    description="Receives real-time lead generation data from external aggregators/Insta, "
                "performs deduplication, applies offer precedence rules, and stores data in CDP. "
                "This endpoint is part of FR7, FR11, FR12."
)
async def receive_lead_data(
    lead_data: LeadCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint to receive and process real-time lead data from external sources
    like Insta or E-aggregators.

    - **Deduplication**: Identifies existing customers based on mobile, PAN,
      Aadhaar, UCID, or previous loan application number (FR2, FR3, FR4, FR5, FR6).
    - **Customer Management**: Creates a new customer record if no match is found,
      or retrieves the existing one.
    - **DND Check**: Prevents processing for customers on the Do Not Disturb list (FR34).
    - **Offer Processing**: Applies complex business rules for offer precedence
      and validity (FR15, FR16, FR18, FR19, FR20, FR21, FR25-FR32).
    - **Data Storage**: Stores the customer and offer details in the CDP database (FR12).
    """
    try:
        customer_service = MockCustomerService(db)
        offer_service = MockOfferService(db)

        # 1. Deduplication and Customer Creation/Retrieval
        customer = customer_service.get_or_create_customer(
            mobile_number=lead_data.mobile_number,
            pan_number=lead_data.pan_number,
            aadhaar_ref_number=lead_data.aadhaar_ref_number,
            ucid_number=lead_data.ucid_number,
            previous_loan_app_number=lead_data.previous_loan_app_number,
            customer_attributes=lead_data.customer_attributes
        )

        # 2. Check DND status (FR34)
        if customer_service.check_dnd_status(customer.customer_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customer is on Do Not Disturb (DND) list. Lead cannot be processed."
            )

        # 3. Process Offer
        # This logic is complex and delegated to OfferService to handle
        # offer precedence, updates (FR8, FR20, FR21), and creation.
        processed_offer = offer_service.process_new_offer(
            customer=customer,
            loan_product=lead_data.loan_product,
            offer_details=lead_data.offer_details
        )

        message = "Lead processed and stored successfully."
        if processed_offer.offer_status == "Duplicate":
            message = "Lead processed, but offer marked as duplicate due to precedence rules."
        elif processed_offer.offer_status == "Inactive":
            message = "Lead processed, but offer marked as inactive based on business rules."

        return LeadCreateResponse(
            status="success",
            message=message,
            customer_id=customer.customer_id
        )

    except HTTPException as e:
        # Re-raise FastAPI HTTPExceptions directly
        raise e
    except Exception as e:
        # Catch any other unexpected errors and return a 500
        print(f"An unexpected error occurred during lead processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred: {e}"
        )