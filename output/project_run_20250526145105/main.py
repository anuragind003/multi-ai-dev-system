import os
import uuid
import csv
from datetime import datetime, date, timedelta
from io import StringIO
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Date, Text, ForeignKey, or_, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, Field

# --- Configuration ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/cdp_db")

# --- SQLAlchemy Setup ---
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Database Models ---
class Customer(Base):
    __tablename__ = "customers"
    customer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = Column(String(20), unique=True, nullable=True)
    pan_number = Column(String(10), unique=True, nullable=True)
    aadhaar_ref_number = Column(String(12), unique=True, nullable=True)
    ucid_number = Column(String(50), unique=True, nullable=True)
    previous_loan_app_number = Column(String(50), unique=True, nullable=True)
    customer_attributes = Column(JSONB, default={})
    customer_segments = Column(ARRAY(Text), default=[])
    propensity_flag = Column(String(50), nullable=True)
    dnd_status = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

class Offer(Base):
    __tablename__ = "offers"
    offer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=False)
    offer_type = Column(String(50), nullable=True) # e.g., 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status = Column(String(50), default="Active") # e.g., 'Active', 'Inactive', 'Expired', 'Duplicate'
    product_type = Column(String(50), nullable=False) # e.g., 'Loyalty', 'Preapproved', 'E-aggregator', 'Insta', 'Top-up', 'Employee Loan'
    offer_details = Column(JSONB, default={})
    offer_start_date = Column(Date, nullable=True)
    offer_end_date = Column(Date, nullable=True)
    is_journey_started = Column(Boolean, default=False)
    loan_application_id = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

class OfferHistory(Base):
    __tablename__ = "offer_history"
    history_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.offer_id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=False)
    change_timestamp = Column(DateTime(timezone=True), default=datetime.now)
    old_offer_status = Column(String(50), nullable=True)
    new_offer_status = Column(String(50), nullable=True)
    change_reason = Column(Text, nullable=True)
    snapshot_offer_details = Column(JSONB, default={})

class CampaignEvent(Base):
    __tablename__ = "campaign_events"
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=False)
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.offer_id"), nullable=True)
    event_source = Column(String(50), nullable=False) # e.g., 'Moengage', 'LOS'
    event_type = Column(String(100), nullable=False) # e.g., 'SMS_SENT', 'CLICK', 'CONVERSION', 'LOGIN'
    event_details = Column(JSONB, default={})
    event_timestamp = Column(DateTime(timezone=True), default=datetime.now)

# Create database tables
Base.metadata.create_all(bind=engine)

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Models ---
class LeadCreate(BaseModel):
    mobile_number: Optional[str] = None
    pan_number: Optional[str] = None
    aadhaar_ref_number: Optional[str] = None
    loan_product: str
    offer_details: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        schema_extra = {
            "example": {
                "mobile_number": "9876543210",
                "pan_number": "ABCDE1234F",
                "loan_product": "Insta",
                "offer_details": {
                    "loan_amount": 50000,
                    "interest_rate": 10.5
                }
            }
        }

class CustomerResponse(BaseModel):
    customer_id: uuid.UUID
    mobile_number: Optional[str]
    pan_number: Optional[str]
    current_offer: Optional[Dict[str, Any]]
    offer_history_summary: List[Dict[str, Any]]
    journey_status: Optional[str]
    segments: List[str]

    class Config:
        orm_mode = True

class DailyTallyReport(BaseModel):
    report_date: date
    total_customers: int
    active_offers: int
    new_leads_today: int
    conversions_today: int

# --- FastAPI App ---
app = FastAPI(
    title="LTFS Offer Customer Data Platform (CDP)",
    description="API for managing consumer loan offers, customer data, and campaign insights.",
    version="1.0.0"
)

# --- Helper Functions (Simplified for MVP) ---
def find_existing_customer(db: Session, mobile: Optional[str], pan: Optional[str], aadhaar: Optional[str], ucid: Optional[str], prev_loan_app: Optional[str]):
    query_conditions = []
    if mobile:
        query_conditions.append(Customer.mobile_number == mobile)
    if pan:
        query_conditions.append(Customer.pan_number == pan)
    if aadhaar:
        query_conditions.append(Customer.aadhaar_ref_number == aadhaar)
    if ucid:
        query_conditions.append(Customer.ucid_number == ucid)
    if prev_loan_app:
        query_conditions.append(Customer.previous_loan_app_number == prev_loan_app)

    if not query_conditions:
        return None

    return db.query(Customer).filter(or_(*query_conditions)).first()

def handle_offer_precedence(db: Session, customer: Customer, new_product_type: str, new_offer_details: Dict[str, Any]):
    """
    Simplified offer precedence logic (FR25-FR32).
    This is a placeholder and needs detailed business rule implementation.
    For MVP: If customer has an active offer and new offer is of a 'lower' priority type,
    the new offer might be marked as duplicate or rejected.
    If new offer is 'higher' priority and existing journey not started, existing offer expires.
    """
    existing_active_offer = db.query(Offer).filter(
        Offer.customer_id == customer.customer_id,
        Offer.offer_status == "Active"
    ).first()

    if not existing_active_offer:
        return "Fresh", None # No existing active offer, new offer is 'Fresh'

    # Example simplified precedence: Insta/E-aggregator generally prevails if no journey started
    # This is a very basic interpretation of FR25-FR32
    if existing_active_offer.is_journey_started:
        # FR15, FR26, FR27, FR28: If journey started, existing offer prevails.
        # New offer is effectively ignored or marked as duplicate.
        return "Duplicate", existing_active_offer.offer_id
    else:
        # FR25: If customer in pre-approved base (prospect/E-aggregator) with no journey,
        # and same customer comes via CLEAG/Insta, CLEAG/Insta prevails.
        # Mark existing offer as expired.
        if new_product_type in ["Insta", "E-aggregator"] and \
           existing_active_offer.product_type in ["Preapproved", "Prospect"]:
            existing_active_offer.offer_status = "Expired"
            db.add(OfferHistory(
                offer_id=existing_active_offer.offer_id,
                customer_id=customer.customer_id,
                old_offer_status="Active",
                new_offer_status="Expired",
                change_reason=f"Expired by new {new_product_type} offer (FR25)",
                snapshot_offer_details=existing_active_offer.offer_details
            ))
            db.commit()
            db.refresh(existing_active_offer)
            return "Fresh", None # New offer is 'Fresh' and active

        # FR29-FR32: If customer has certain offers first, new offers cannot be uploaded.
        # This implies the new offer should be rejected or marked as duplicate.
        # This is a simplified check. A full implementation would need a defined hierarchy.
        priority_products = ["TWL", "Top-up", "Employee Loan"]
        if existing_active_offer.product_type in priority_products and \
           new_product_type not in priority_products:
            return "Duplicate", existing_active_offer.offer_id # New offer cannot be uploaded

    return "Enrich", existing_active_offer.offer_id # Default: new offer enriches/updates existing

def process_uploaded_offer(db: Session, row: Dict[str, Any], line_num: int):
    mobile = row.get("mobile_number")
    pan = row.get("pan_number")
    aadhaar = row.get("aadhaar_ref_number")
    product_type = row.get("product_type")

    if not product_type:
        return False, f"Row {line_num}: 'product_type' is required."

    customer = find_existing_customer(db, mobile, pan, aadhaar, None, None)
    customer_id = None
    offer_status = "Active"
    offer_type = "Fresh"
    error_message = None

    if customer:
        customer_id = customer.customer_id
        offer_type, existing_offer_id = handle_offer_precedence(db, customer, product_type, row)
        if offer_type == "Duplicate":
            offer_status = "Duplicate"
            error_message = f"Offer for existing customer marked as Duplicate due to precedence rules."
        elif offer_type == "Enrich":
            # Find the existing offer to enrich
            existing_offer = db.query(Offer).filter(Offer.offer_id == existing_offer_id).first()
            if existing_offer:
                # FR20: If Enrich offer's journey not started, flow to CDP, previous offer to Duplicate.
                if not existing_offer.is_journey_started:
                    existing_offer.offer_status = "Duplicate"
                    db.add(OfferHistory(
                        offer_id=existing_offer.offer_id,
                        customer_id=customer.customer_id,
                        old_offer_status="Active",
                        new_offer_status="Duplicate",
                        change_reason="Enriched by new offer (FR20)",
                        snapshot_offer_details=existing_offer.offer_details
                    ))
                    db.commit()
                    db.refresh(existing_offer)
                else:
                    # FR21: If Enrich offer's journey started, it shall not flow into CDP.
                    return False, f"Row {line_num}: Enrich offer's journey already started, cannot process new offer (FR21)."
    else:
        customer_id = uuid.uuid4()
        customer = Customer(
            customer_id=customer_id,
            mobile_number=mobile,
            pan_number=pan,
            aadhaar_ref_number=aadhaar,
            customer_attributes=row # Store all row data as attributes for new customer
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

    new_offer = Offer(
        customer_id=customer_id,
        product_type=product_type,
        offer_details=row, # Store all row data as offer details
        offer_status=offer_status,
        offer_type=offer_type,
        offer_start_date=datetime.strptime(row["offer_start_date"], "%Y-%m-%d").date() if row.get("offer_start_date") else None,
        offer_end_date=datetime.strptime(row["offer_end_date"], "%Y-%m-%d").date() if row.get("offer_end_date") else None,
    )
    db.add(new_offer)
    db.commit()
    db.refresh(new_offer)

    if offer_status == "Active":
        # FR44: Generate leads for customers upon successful upload
        # This is a placeholder for actual lead generation logic
        print(f"Lead generated for customer {customer_id} with offer {new_offer.offer_id}")

    return True, error_message

async def process_csv_upload(db: Session, file_content: bytes):
    success_records = []
    error_records = []
    file_stream = StringIO(file_content.decode('utf-8'))
    reader = csv.DictReader(file_stream)
    headers = reader.fieldnames

    if not headers:
        return [], [{"row_data": {}, "error_desc": "Empty CSV file or no headers."}]

    for i, row in enumerate(reader):
        line_num = i + 2 # +1 for 0-indexed, +1 for header row
        try:
            success, error_desc = process_uploaded_offer(db, row, line_num)
            if success:
                success_records.append(row)
            else:
                error_records.append({"row_data": row, "error_desc": error_desc})
        except Exception as e:
            error_records.append({"row_data": row, "error_desc": f"Processing error: {str(e)}"})
            db.rollback() # Rollback any partial changes for this row

    return success_records, error_records

# --- API Endpoints ---

@app.post("/api/v1/leads", summary="Receive real-time lead generation data")
async def receive_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    """
    Receives real-time lead generation data from external aggregators/Insta,
    processes it, and stores it in CDP.
    Performs deduplication and offer precedence checks.
    """
    customer = find_existing_customer(db, lead.mobile_number, lead.pan_number, lead.aadhaar_ref_number, None, None)
    customer_id = None
    offer_status = "Active"
    offer_type = "Fresh"
    message = "Lead processed and stored"

    if customer:
        customer_id = customer.customer_id
        offer_type, existing_offer_id = handle_offer_precedence(db, customer, lead.loan_product, lead.offer_details)
        if offer_type == "Duplicate":
            offer_status = "Duplicate"
            message = "Lead processed, but new offer marked as Duplicate due to precedence rules."
        elif offer_type == "Enrich":
            existing_offer = db.query(Offer).filter(Offer.offer_id == existing_offer_id).first()
            if existing_offer and not existing_offer.is_journey_started:
                existing_offer.offer_status = "Duplicate"
                db.add(OfferHistory(
                    offer_id=existing_offer.offer_id,
                    customer_id=customer.customer_id,
                    old_offer_status="Active",
                    new_offer_status="Duplicate",
                    change_reason="Enriched by new real-time offer (FR20)",
                    snapshot_offer_details=existing_offer.offer_details
                ))
                db.commit()
                db.refresh(existing_offer)
                message = "Lead processed, existing offer enriched and marked duplicate."
            elif existing_offer and existing_offer.is_journey_started:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                    detail="Enrich offer's journey already started, cannot process new offer (FR21).")
    else:
        customer_id = uuid.uuid4()
        customer = Customer(
            customer_id=customer_id,
            mobile_number=lead.mobile_number,
            pan_number=lead.pan_number,
            aadhaar_ref_number=lead.aadhaar_ref_number,
            customer_attributes=lead.offer_details # Store initial lead details as attributes
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

    new_offer = Offer(
        customer_id=customer_id,
        product_type=lead.loan_product,
        offer_details=lead.offer_details,
        offer_status=offer_status,
        offer_type=offer_type,
        offer_start_date=date.today(), # Assuming real-time offers start today
        offer_end_date=date.today() + timedelta(days=30) # Example: 30 days validity
    )
    db.add(new_offer)
    db.commit()
    db.refresh(new_offer)

    return {"status": "success", "message": message, "customer_id": customer_id}

@app.post("/api/v1/admin/customer_offers/upload", summary="Upload customer offer details via Admin Portal")
async def upload_customer_offers(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Allows administrators to upload a file (e.g., CSV) containing customer offer details
    for bulk processing and lead generation.
    Generates success and error files.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV files are allowed.")

    file_content = await file.read()

    # Process the file in a background task to avoid blocking the API response
    # For simplicity, this example processes synchronously, but for large files,
    # a dedicated worker (e.g., Celery) would be better.
    success_records, error_records = await process_csv_upload(db, file_content)

    # Generate success and error files
    success_file_path = f"uploads/success_{uuid.uuid4()}.csv"
    error_file_path = f"uploads/error_{uuid.uuid4()}.csv"

    os.makedirs("uploads", exist_ok=True)

    if success_records:
        with open(success_file_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=success_records[0].keys())
            writer.writeheader()
            writer.writerows(success_records)

    if error_records:
        error_fieldnames = list(error_records[0]["row_data"].keys()) + ["error_desc"]
        with open(error_file_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=error_fieldnames)
            writer.writeheader()
            for record in error_records:
                row_with_error = record["row_data"]
                row_with_error["error_desc"] = record["error_desc"]
                writer.writerow(row_with_error)

    return {
        "status": "success",
        "message": "File uploaded and processing completed.",
        "total_records": len(success_records) + len(error_records),
        "successful_records": len(success_records),
        "failed_records": len(error_records),
        "success_file_download_link": f"/api/v1/admin/downloads?file_type=success&file_id={os.path.basename(success_file_path)}" if success_records else None,
        "error_file_download_link": f"/api/v1/admin/downloads?file_type=error&file_id={os.path.basename(error_file_path)}" if error_records else None,
    }

@app.get("/api/v1/admin/downloads", summary="Download generated files (Success/Error)")
async def download_generated_file(file_type: str, file_id: str):
    """
    Allows users to download generated success or error files.
    """
    if file_type not in ["success", "error"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type.")

    file_path = os.path.join("uploads", file_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

    def iterfile():
        with open(file_path, mode="rb") as f:
            yield from f

    return StreamingResponse(iterfile(), media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename={file_id}"
    })

@app.get("/api/v1/admin/campaigns/moengage_file", summary="Generate and download Moengage-formatted CSV file")
async def get_moengage_file(db: Session = Depends(get_db)):
    """
    Generates and provides the latest Moengage-formatted campaign file in CSV format for download.
    (FR54, FR55)
    """
    # For MVP, fetch all active offers and relevant customer data
    # In a real scenario, this would involve specific campaign criteria and data transformation.
    customers_with_offers = db.query(Customer, Offer).join(Offer, Customer.customer_id == Offer.customer_id).filter(
        Offer.offer_status == "Active",
        Customer.dnd_status == False # FR34: Avoid DND customers
    ).all()

    if not customers_with_offers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active offers found for Moengage file generation.")

    output = StringIO()
    # Define Moengage specific headers (example, needs actual template from FR54)
    fieldnames = [
        "customer_id", "mobile_number", "pan_number", "product_type",
        "offer_amount", "offer_expiry_date", "campaign_segment", "propensity_score"
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for customer, offer in customers_with_offers:
        row = {
            "customer_id": str(customer.customer_id),
            "mobile_number": customer.mobile_number,
            "pan_number": customer.pan_number,
            "product_type": offer.product_type,
            "offer_amount": offer.offer_details.get("loan_amount"), # Example
            "offer_expiry_date": offer.offer_end_date.isoformat() if offer.offer_end_date else None,
            "campaign_segment": customer.customer_segments[0] if customer.customer_segments else None, # Example: first segment
            "propensity_score": customer.propensity_flag
        }
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=moengage_campaign_file.csv"}
    )

@app.get("/api/v1/customers/{customer_id}", response_model=CustomerResponse, summary="Retrieve a single customer profile")
async def get_customer_profile(customer_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieves a single profile view of a customer, including their current offers,
    attributes, segments, and journey stages. (FR2, FR50)
    """
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    current_offer = db.query(Offer).filter(
        Offer.customer_id == customer_id,
        Offer.offer_status == "Active"
    ).first()

    offer_history_summary = db.query(OfferHistory).filter(
        OfferHistory.customer_id == customer_id
    ).order_by(OfferHistory.change_timestamp.desc()).limit(10).all() # Limit for summary

    # Determine journey status (simplified)
    journey_status = "No Active Journey"
    if current_offer and current_offer.is_journey_started:
        # In a real system, this would query LOS events or a dedicated journey table
        journey_status = "Journey Started"
        if current_offer.loan_application_id:
            journey_status += f" (LAN: {current_offer.loan_application_id})"

    return CustomerResponse(
        customer_id=customer.customer_id,
        mobile_number=customer.mobile_number,
        pan_number=customer.pan_number,
        current_offer={
            "offer_id": current_offer.offer_id,
            "product_type": current_offer.product_type,
            "offer_status": current_offer.offer_status,
            "is_journey_started": current_offer.is_journey_started,
            "loan_application_id": current_offer.loan_application_id,
            **current_offer.offer_details # Include all offer details
        } if current_offer else None,
        offer_history_summary=[
            {
                "history_id": h.history_id,
                "offer_id": h.offer_id,
                "change_timestamp": h.change_timestamp,
                "old_status": h.old_offer_status,
                "new_status": h.new_offer_status,
                "reason": h.change_reason
            } for h in offer_history_summary
        ],
        journey_status=journey_status,
        segments=customer.customer_segments
    )

@app.get("/api/v1/reports/daily_tally", response_model=DailyTallyReport, summary="Get daily summary reports")
async def get_daily_tally_report(report_date: Optional[date] = None, db: Session = Depends(get_db)):
    """
    Provides daily summary reports for data tally, including counts of unique customers,
    offers, and processed records. (FR49)
    """
    if report_date is None:
        report_date = date.today()

    # Total customers
    total_customers = db.query(Customer).count()

    # Active offers
    active_offers = db.query(Offer).filter(Offer.offer_status == "Active").count()

    # New leads today (simplified: customers created today)
    new_leads_today = db.query(Customer).filter(func.date(Customer.created_at) == report_date).count()

    # Conversions today (simplified: offers with journey started today)
    conversions_today = db.query(Offer).filter(
        Offer.is_journey_started == True,
        func.date(Offer.updated_at) == report_date # Assuming updated_at changes when journey starts
    ).count()

    return DailyTallyReport(
        report_date=report_date,
        total_customers=total_customers,
        active_offers=active_offers,
        new_leads_today=new_leads_today,
        conversions_today=conversions_today
    )

# --- Scheduled Tasks (Placeholder) ---
# In a real application, these would be handled by a separate scheduler (e.g., Celery Beat, cron)
# For demonstration, a simple endpoint could trigger them, but they shouldn't be part of main API flow.

@app.post("/api/v1/internal/run_daily_jobs", summary="Trigger daily scheduled jobs (for testing/manual trigger)")
async def run_daily_jobs(db: Session = Depends(get_db)):
    """
    This endpoint is for internal/testing purposes to simulate daily scheduled jobs.
    In production, these would run via a dedicated scheduler.
    """
    # Offer Expiry (FR51, FR53)
    expired_offers = db.query(Offer).filter(
        Offer.offer_status == "Active",
        Offer.offer_end_date < date.today(),
        Offer.is_journey_started == False # FR51: only for non-journey started
    ).all()

    for offer in expired_offers:
        old_status = offer.offer_status
        offer.offer_status = "Expired"
        db.add(OfferHistory(
            offer_id=offer.offer_id,
            customer_id=offer.customer_id,
            old_offer_status=old_status,
            new_offer_status="Expired",
            change_reason="Offer end date passed (FR51)",
            snapshot_offer_details=offer.offer_details
        ))
    db.commit()

    # Data Retention (FR37, NFR10) - Delete data older than 3 months
    # This is a soft delete or a more complex archival process in real systems
    three_months_ago = datetime.now() - timedelta(days=90)
    # For simplicity, we'll just log for now. Actual deletion needs careful consideration.
    # db.query(CampaignEvent).filter(CampaignEvent.event_timestamp < three_months_ago).delete()
    # db.query(OfferHistory).filter(OfferHistory.change_timestamp < three_months_ago).delete()
    # db.query(Offer).filter(Offer.created_at < three_months_ago, Offer.offer_status != "Active").delete() # Be careful with offer deletion
    print(f"Simulated daily cleanup: Offers expired, data older than {three_months_ago} considered for deletion.")

    return {"status": "success", "message": "Daily jobs simulated successfully."}

# Root endpoint for health check
@app.get("/")
async def root():
    return {"message": "LTFS Offer CDP Backend is running!"}