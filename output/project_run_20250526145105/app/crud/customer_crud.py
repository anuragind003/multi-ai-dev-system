import uuid
from typing import List, Optional, Dict, Any
from datetime import date, datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy import Column, String, Boolean, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm import relationship

# Base for SQLAlchemy declarative models
Base = declarative_base()

# --- SQLAlchemy Models (typically in app/models/) ---
# Defined here for self-containment as per instructions, but in a real project
# these would be imported from a dedicated `app/models/` module.

class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = Column(String(20), unique=True, nullable=True)
    pan_number = Column(String(10), unique=True, nullable=True)
    aadhaar_ref_number = Column(String(12), unique=True, nullable=True)
    ucid_number = Column(String(50), unique=True, nullable=True)
    previous_loan_app_number = Column(String(50), unique=True, nullable=True)
    customer_attributes = Column(JSONB, default={})
    customer_segments = Column(ARRAY(String), default=[])
    propensity_flag = Column(String(50), nullable=True)
    dnd_status = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    offers = relationship("Offer", back_populates="customer")

    def __repr__(self):
        return f"<Customer(id={self.customer_id}, mobile={self.mobile_number})>"


class Offer(Base):
    __tablename__ = "offers"

    offer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=False)
    offer_type = Column(String(50), nullable=True)
    offer_status = Column(String(50), default="Active") # e.g., 'Active', 'Inactive', 'Expired', 'Duplicate'
    product_type = Column(String(50), nullable=True) # e.g., 'Loyalty', 'Preapproved', 'E-aggregator', 'Insta', 'Top-up', 'Employee Loan'
    offer_details = Column(JSONB, default={})
    offer_start_date = Column(Date, nullable=True)
    offer_end_date = Column(Date, nullable=True)
    is_journey_started = Column(Boolean, default=False)
    loan_application_id = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="offers")

    def __repr__(self):
        return f"<Offer(id={self.offer_id}, customer_id={self.customer_id}, status={self.offer_status})>"


# --- Pydantic Schemas (typically in app/schemas/) ---
# Defined here for self-containment, but in a real project
# these would be imported from a dedicated `app/schemas/` module.
from pydantic import BaseModel, Field

class CustomerCreate(BaseModel):
    mobile_number: Optional[str] = Field(None, max_length=20)
    pan_number: Optional[str] = Field(None, max_length=10)
    aadhaar_ref_number: Optional[str] = Field(None, max_length=12)
    ucid_number: Optional[str] = Field(None, max_length=50)
    previous_loan_app_number: Optional[str] = Field(None, max_length=50)
    customer_attributes: Dict[str, Any] = Field({})
    customer_segments: List[str] = Field([])
    propensity_flag: Optional[str] = Field(None, max_length=50)
    dnd_status: bool = False

    class Config:
        from_attributes = True # For Pydantic v2, or orm_mode = True for Pydantic v1

class CustomerUpdate(CustomerCreate):
    # All fields are optional for update
    pass

class OfferCreate(BaseModel):
    offer_type: Optional[str] = Field(None, max_length=50)
    offer_status: str = Field("Active", max_length=50)
    product_type: Optional[str] = Field(None, max_length=50)
    offer_details: Dict[str, Any] = Field({})
    offer_start_date: Optional[date] = None
    offer_end_date: Optional[date] = None
    is_journey_started: bool = False
    loan_application_id: Optional[str] = Field(None, max_length=50)

    class Config:
        from_attributes = True

class CustomerProfile(BaseModel):
    customer_id: uuid.UUID
    mobile_number: Optional[str]
    pan_number: Optional[str]
    aadhaar_ref_number: Optional[str]
    ucid_number: Optional[str]
    previous_loan_app_number: Optional[str]
    customer_attributes: Dict[str, Any]
    customer_segments: List[str]
    propensity_flag: Optional[str]
    dnd_status: bool
    current_offer: Optional[OfferCreate] # Reusing OfferCreate for simplicity, might need a dedicated OfferRead
    offer_history_summary: List[Dict[str, Any]] # Placeholder for summary
    journey_status: Optional[str] # Derived from offers
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- CRUD Operations ---

class CustomerCRUD:
    def __init__(self, db: Session):
        self.db = db

    def _get_customer_by_identifiers(
        self,
        mobile_number: Optional[str] = None,
        pan_number: Optional[str] = None,
        aadhaar_ref_number: Optional[str] = None,
        ucid_number: Optional[str] = None,
        previous_loan_app_number: Optional[str] = None,
    ) -> Optional[Customer]:
        """
        Helper to find an existing customer by any of the unique identifiers (FR3).
        """
        filters = []
        if mobile_number:
            filters.append(Customer.mobile_number == mobile_number)
        if pan_number:
            filters.append(Customer.pan_number == pan_number)
        if aadhaar_ref_number:
            filters.append(Customer.aadhaar_ref_number == aadhaar_ref_number)
        if ucid_number:
            filters.append(Customer.ucid_number == ucid_number)
        if previous_loan_app_number:
            filters.append(Customer.previous_loan_app_number == previous_loan_app_number)

        if not filters:
            return None

        # Use or_ to find if any identifier matches
        customer = self.db.query(Customer).filter(or_(*filters)).first()
        return customer

    def get_customer_by_id(self, customer_id: uuid.UUID) -> Optional[Customer]:
        """
        Retrieves a customer by their UUID.
        """
        return self.db.query(Customer).filter(Customer.customer_id == customer_id).first()

    def create_or_update_customer(
        self, customer_data: CustomerCreate, offer_data: Optional[OfferCreate] = None
    ) -> Customer:
        """
        Creates a new customer or updates an existing one based on deduplication logic (FR3, FR4, FR5).
        If an offer is provided, it's associated with the customer, applying basic offer precedence (FR20, FR21).
        """
        existing_customer = self._get_customer_by_identifiers(
            mobile_number=customer_data.mobile_number,
            pan_number=customer_data.pan_number,
            aadhaar_ref_number=customer_data.aadhaar_ref_number,
            ucid_number=customer_data.ucid_number,
            previous_loan_app_number=customer_data.previous_loan_app_number,
        )

        if existing_customer:
            # Update existing customer
            for key, value in customer_data.model_dump(exclude_unset=True).items():
                # Only update if the new value is not None and different from existing
                if value is not None and getattr(existing_customer, key) != value:
                    setattr(existing_customer, key, value)
            self.db.add(existing_customer)
            customer = existing_customer
        else:
            # Create new customer
            customer = Customer(**customer_data.model_dump())
            self.db.add(customer)

        self.db.flush()  # Flush to get the customer_id if new

        if offer_data:
            # Basic offer precedence: If an 'Enrich' offer comes in and no journey started,
            # mark previous active offers as 'Duplicate' or 'Inactive' (FR20, FR21).
            # More complex offer precedence rules (FR25-FR32) would typically reside
            # in a dedicated service layer to maintain separation of concerns and reduce
            # cyclomatic complexity in the CRUD layer.
            if offer_data.offer_type == 'Enrich' and not offer_data.is_journey_started:
                # Find existing active offers for this customer that haven't started a journey
                existing_active_offers = self.db.query(Offer).filter(
                    Offer.customer_id == customer.customer_id,
                    Offer.offer_status == 'Active',
                    Offer.is_journey_started == False
                ).all()

                for offer_to_expire in existing_active_offers:
                    offer_to_expire.offer_status = 'Duplicate' # FR20: previous offer moved to Duplicate
                    self.db.add(offer_to_expire)
            elif offer_data.offer_type == 'Enrich' and offer_data.is_journey_started:
                # FR21: If an Enrich offer's journey has started, it shall not flow into CDP.
                # In this CRUD, we'll simply skip adding it. A service layer might raise an error.
                pass # Do not add the offer if it's an Enrich offer with journey started
            
            # Create the new offer if it's not an excluded Enrich offer
            if not (offer_data.offer_type == 'Enrich' and offer_data.is_journey_started):
                new_offer = Offer(customer_id=customer.customer_id, **offer_data.model_dump())
                self.db.add(new_offer)

        self.db.commit()
        self.db.refresh(customer)
        # If new_offer was added, refresh it too.
        # This part is tricky if new_offer was conditionally added.
        # For simplicity, we assume the caller will handle refreshing if needed.
        return customer

    def get_customer_profile(self, customer_id: uuid.UUID) -> Optional[CustomerProfile]:
        """
        Retrieves a comprehensive single profile view of a customer (FR2, FR50).
        Includes current offers, attributes, segments, and journey stages.
        """
        customer = self.db.query(Customer).filter(Customer.customer_id == customer_id).first()

        if not customer:
            return None

        # Get current active offer (simplified: most recently created active offer)
        current_offer_db = self.db.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.offer_status == 'Active'
        ).order_by(Offer.created_at.desc()).first()

        current_offer_schema = None
        if current_offer_db:
            current_offer_schema = OfferCreate.model_validate(current_offer_db)

        # Offer history summary (FR23: past 6 months)
        # This example fetches all offers and provides a basic summary.
        # A more detailed history would query the `offer_history` table.
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        offer_history_summary = []
        recent_offers = self.db.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.created_at >= six_months_ago
        ).order_by(Offer.created_at.desc()).all()

        for offer in recent_offers:
            offer_history_summary.append({
                "offer_id": offer.offer_id,
                "product_type": offer.product_type,
                "offer_status": offer.offer_status,
                "offer_start_date": offer.offer_start_date,
                "offer_end_date": offer.offer_end_date,
                "is_journey_started": offer.is_journey_started,
                "created_at": offer.created_at
            })

        # Determine journey status (simplified)
        journey_status = "No active journey"
        if current_offer_db and current_offer_db.is_journey_started:
            journey_status = f"Journey started for {current_offer_db.product_type} (LAN: {current_offer_db.loan_application_id or 'N/A'})"
        elif current_offer_db:
            journey_status = f"Active offer for {current_offer_db.product_type}, journey not started"

        return CustomerProfile(
            customer_id=customer.customer_id,
            mobile_number=customer.mobile_number,
            pan_number=customer.pan_number,
            aadhaar_ref_number=customer.aadhaar_ref_number,
            ucid_number=customer.ucid_number,
            previous_loan_app_number=customer.previous_loan_app_number,
            customer_attributes=customer.customer_attributes,
            customer_segments=customer.customer_segments,
            propensity_flag=customer.propensity_flag,
            dnd_status=customer.dnd_status,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
            current_offer=current_offer_schema,
            offer_history_summary=offer_history_summary,
            journey_status=journey_status,
        )

    def update_customer_dnd_status(self, customer_id: uuid.UUID, dnd_status: bool) -> Optional[Customer]:
        """
        Updates the DND status for a customer (FR34).
        """
        customer = self.db.query(Customer).filter(Customer.customer_id == customer_id).first()
        if customer:
            customer.dnd_status = dnd_status
            customer.updated_at = datetime.utcnow()
            self.db.add(customer)
            self.db.commit()
            self.db.refresh(customer)
        return customer

    def update_offer_journey_status(self, offer_id: uuid.UUID, is_journey_started: bool, loan_application_id: Optional[str] = None) -> Optional[Offer]:
        """
        Updates the journey status of an offer (FR15, FR16).
        """
        offer = self.db.query(Offer).filter(Offer.offer_id == offer_id).first()
        if offer:
            # FR15: Prevent modification of customer offers with a started loan application journey
            # until the application is either expired or rejected.
            # This logic implies that if is_journey_started is already True, we might not allow
            # changing it back to False or changing loan_application_id unless specific conditions are met.
            # For simplicity in CRUD, we allow direct update. A service layer would enforce FR15.
            offer.is_journey_started = is_journey_started
            offer.loan_application_id = loan_application_id
            offer.updated_at = datetime.utcnow()
            self.db.add(offer)
            self.db.commit()
            self.db.refresh(offer)
        return offer

    def mark_offers_as_expired(self) -> List[Offer]:
        """
        Marks offers as 'Expired' based on offer end dates for non-journey started customers (FR51).
        This function is intended to be called by a scheduled background job.
        """
        expired_offers = self.db.query(Offer).filter(
            Offer.offer_status == 'Active',
            Offer.is_journey_started == False,
            Offer.offer_end_date < date.today()
        ).all()

        for offer in expired_offers:
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.utcnow()
            self.db.add(offer)
        self.db.commit()
        # Refresh all expired offers to reflect their new status
        for offer in expired_offers:
            self.db.refresh(offer)
        return expired_offers

    # Note on FR53: "mark offers as expired within the offers data if the LAN validity post loan application journey start date is over."
    # This requires a clear definition of "LAN validity period" (Ambiguity 9).
    # This function would be similar to `mark_offers_as_expired` but would filter by `is_journey_started=True`
    # and check against a calculated expiry date based on `loan_application_id` and the defined validity period.
    # It is not implemented here due to the lack of a defined validity period.

from datetime import timedelta # Added for FR23 (6 months history)