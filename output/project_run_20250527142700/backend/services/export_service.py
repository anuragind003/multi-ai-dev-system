import csv
import io
from datetime import datetime
from uuid import UUID

# Corrected import for JSONB and UUID from PostgreSQL dialect
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Session, relationship
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# --- MOCK/PLACEHOLDER MODELS ---
# In a real Flask application, these models would typically be defined in `backend/models.py`
# and imported from there (e.g., `from backend.models import Customer, Offer, DataError`).
# They are included here to make this service file self-contained and runnable for demonstration
# or isolated testing purposes, as requested by the "complete code for this file" instruction.
# In a full project setup, these definitions would be removed from this file.

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True

    # Default columns for all models
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Customer(BaseModel):
    __tablename__ = 'customers'
    customer_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=UUID)
    mobile_number = Column(String(20), unique=True)
    pan_number = Column(String(10), unique=True)
    aadhaar_number = Column(String(12), unique=True)
    ucid_number = Column(String(50), unique=True)
    customer_360_id = Column(String(50))
    is_dnd = Column(Boolean, default=False)
    segment = Column(String(50))
    attributes = Column(JSONB)
    offers = relationship("Offer", backref="customer", lazy=True)

class Offer(BaseModel):
    __tablename__ = 'offers'
    offer_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=UUID)
    customer_id = Column(PG_UUID(as_uuid=True), ForeignKey('customers.customer_id'), nullable=False)
    source_offer_id = Column(String(100))
    offer_type = Column(String(50)) # 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status = Column(String(50)) # 'Active', 'Inactive', 'Expired'
    propensity = Column(String(50))
    loan_application_number = Column(String(100))
    valid_until = Column(DateTime(timezone=True))
    source_system = Column(String(50)) # 'Offermart', 'E-aggregator'
    channel = Column(String(50)) # For attribution
    is_duplicate = Column(Boolean, default=False) # Flagged by deduplication
    original_offer_id = Column(PG_UUID(as_uuid=True), ForeignKey('offers.offer_id')) # Points to the offer it duplicated/enriched

class DataError(BaseModel):
    __tablename__ = 'data_errors'
    error_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=UUID)
    source_file_name = Column(String(255), nullable=False)
    row_number = Column(Integer)
    column_name = Column(String(100))
    error_message = Column(Text, nullable=False)
    error_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    raw_data = Column(JSONB) # Store the raw data that caused the error

# --- END MOCK/PLACEHOLDER MODELS ---


class ExportService:
    def __init__(self, db_session: Session):
        """
        Initializes the ExportService with a database session.
        :param db_session: An active SQLAlchemy session object.
        """
        self.db_session = db_session

    def _generate_csv_content(self, data: list[dict], fieldnames: list[str]) -> str:
        """Helper to generate CSV content from a list of dictionaries."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    def export_moengage_campaign_data(self) -> str:
        """
        Generates a Moengage-formatted CSV file content for eligible customers.
        Eligible customers: Active offers, not DND.
        (FR30, FR24, User Story: Campaign Manager - Moengage file)
        """
        query = self.db_session.query(
            Customer.customer_id,
            Customer.mobile_number,
            Customer.segment,
            Offer.offer_id,
            Offer.offer_type,
            Offer.propensity,
            Offer.loan_application_number,
            Offer.valid_until,
            Offer.source_system,
            Offer.channel
        ).join(Offer, Customer.customer_id == Offer.customer_id)\
         .filter(Customer.is_dnd == False)\
         .filter(Offer.offer_status == 'Active')

        results = query.all()

        # Define Moengage specific fields. This is an assumption based on common Moengage requirements.
        # The BRD doesn't specify Moengage format, so we'll use relevant fields from our schema.
        fieldnames = [
            'customer_id', 'mobile_number', 'offer_id', 'offer_type', 'segment',
            'propensity', 'loan_application_number', 'valid_until', 'source_system', 'channel'
        ]

        data = []
        for row in results:
            data.append({
                'customer_id': str(row.customer_id) if row.customer_id else '',
                'mobile_number': row.mobile_number if row.mobile_number else '',
                'offer_id': str(row.offer_id) if row.offer_id else '',
                'offer_type': row.offer_type if row.offer_type else '',
                'segment': row.segment if row.segment else '',
                'propensity': row.propensity if row.propensity else '',
                'loan_application_number': row.loan_application_number if row.loan_application_number else '',
                'valid_until': row.valid_until.isoformat() if row.valid_until else '',
                'source_system': row.source_system if row.source_system else '',
                'channel': row.channel if row.channel else ''
            })

        return self._generate_csv_content(data, fieldnames)

    def export_duplicate_customer_data(self) -> str:
        """
        Generates a CSV file content containing identified duplicate customer data.
        (FR31, User Story: Data Quality Analyst - Duplicate file)
        """
        query = self.db_session.query(
            Customer.customer_id,
            Customer.mobile_number,
            Customer.pan_number,
            Offer.offer_id,
            Offer.offer_type,
            Offer.offer_status,
            Offer.is_duplicate,
            Offer.original_offer_id
        ).join(Customer, Customer.customer_id == Offer.customer_id)\
         .filter(Offer.is_duplicate == True)

        results = query.all()

        fieldnames = [
            'customer_id', 'mobile_number', 'pan_number', 'offer_id',
            'offer_type', 'offer_status', 'is_duplicate', 'original_offer_id'
        ]

        data = []
        for row in results:
            data.append({
                'customer_id': str(row.customer_id) if row.customer_id else '',
                'mobile_number': row.mobile_number if row.mobile_number else '',
                'pan_number': row.pan_number if row.pan_number else '',
                'offer_id': str(row.offer_id) if row.offer_id else '',
                'offer_type': row.offer_type if row.offer_type else '',
                'offer_status': row.offer_status if row.offer_status else '',
                'is_duplicate': row.is_duplicate,
                'original_offer_id': str(row.original_offer_id) if row.original_offer_id else ''
            })

        return self._generate_csv_content(data, fieldnames)

    def export_unique_customer_data(self) -> str:
        """
        Generates a CSV file content containing unique customer data after deduplication.
        (FR32)
        """
        # Query for all unique customers.
        # The definition of "unique data file" implies unique customer profiles.
        query = self.db_session.query(
            Customer.customer_id,
            Customer.mobile_number,
            Customer.pan_number,
            Customer.aadhaar_number,
            Customer.ucid_number,
            Customer.segment,
            Customer.is_dnd
        ).distinct(Customer.customer_id) # Ensure unique customer rows

        results = query.all()

        fieldnames = [
            'customer_id', 'mobile_number', 'pan_number', 'aadhaar_number',
            'ucid_number', 'segment', 'is_dnd'
        ]

        data = []
        for row in results:
            data.append({
                'customer_id': str(row.customer_id) if row.customer_id else '',
                'mobile_number': row.mobile_number if row.mobile_number else '',
                'pan_number': row.pan_number if row.pan_number else '',
                'aadhaar_number': row.aadhaar_number if row.aadhaar_number else '',
                'ucid_number': row.ucid_number if row.ucid_number else '',
                'segment': row.segment if row.segment else '',
                'is_dnd': row.is_dnd
            })

        return self._generate_csv_content(data, fieldnames)

    def export_data_errors(self) -> bytes:
        """
        Generates an Excel file content detailing data validation errors from ingestion processes.
        (FR33, User Story: Data Quality Analyst - Error file)
        Returns bytes representing an Excel file.
        """
        try:
            from openpyxl import Workbook
            from openpyxl.writer.excel import save_virtual_workbook
        except ImportError:
            # Fallback to CSV if openpyxl is not available.
            # Note: The return type changes from bytes (Excel) to str (CSV).
            # The calling API endpoint should handle this difference.
            print("Warning: openpyxl not found. Falling back to CSV for error export.")
            csv_content = self._export_data_errors_csv_fallback()
            return csv_content.encode('utf-8') # Encode CSV string to bytes for consistent return type

        query = self.db_session.query(DataError).order_by(DataError.error_timestamp.desc())
        results = query.all()

        fieldnames = [
            'Error ID', 'Source File Name', 'Row Number', 'Column Name',
            'Error Message', 'Error Timestamp', 'Raw Data'
        ]

        wb = Workbook()
        ws = wb.active
        ws.title = "Data Errors"

        # Write header row
        ws.append(fieldnames)

        # Write data rows
        for row in results:
            ws.append([
                str(row.error_id) if row.error_id else '',
                row.source_file_name if row.source_file_name else '',
                row.row_number if row.row_number is not None else '',
                row.column_name if row.column_name else '',
                row.error_message if row.error_message else '',
                row.error_timestamp.isoformat() if row.error_timestamp else '',
                str(row.raw_data) if row.raw_data else '' # JSONB data as string
            ])

        # Save to a virtual workbook (in-memory)
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    def _export_data_errors_csv_fallback(self) -> str:
        """Fallback to CSV for data errors if openpyxl is not available."""
        query = self.db_session.query(DataError).order_by(DataError.error_timestamp.desc())
        results = query.all()

        fieldnames = [
            'error_id', 'source_file_name', 'row_number', 'column_name',
            'error_message', 'error_timestamp', 'raw_data'
        ]

        data = []
        for row in results:
            data.append({
                'error_id': str(row.error_id) if row.error_id else '',
                'source_file_name': row.source_file_name if row.source_file_name else '',
                'row_number': row.row_number if row.row_number is not None else '',
                'column_name': row.column_name if row.column_name else '',
                'error_message': row.error_message if row.error_message else '',
                'error_timestamp': row.error_timestamp.isoformat() if row.error_timestamp else '',
                'raw_data': str(row.raw_data) if row.raw_data else ''
            })
        return self._generate_csv_content(data, fieldnames)