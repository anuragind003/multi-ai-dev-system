import csv
import io
from datetime import datetime
from typing import List, Dict, Any, Generator
import uuid # For UUID types

from sqlalchemy.orm import Session
from sqlalchemy import select, and_

# Assuming these models are defined in app/models.py
from app.models import Customer, Offer, UploadError 

class ExportService:
    def __init__(self, db: Session):
        """
        Initializes the ExportService with a database session.

        Args:
            db: The SQLAlchemy database session.
        """
        self.db = db

    def _generate_csv_content(self, data: List[Dict[str, Any]]) -> Generator[str, None, None]:
        """
        Helper to generate CSV content from a list of dictionaries for streaming.
        This function assumes the entire data list is available in memory.
        For extremely large datasets, a different streaming approach would be needed
        that fetches data in chunks and writes directly to the stream.

        Args:
            data: A list of dictionaries, where each dictionary represents a row.

        Yields:
            CSV content as strings.
        """
        if not data:
            yield ""
            return

        output = io.StringIO()
        
        # Collect all unique keys from all dictionaries to form comprehensive headers
        all_keys = set()
        for row in data:
            all_keys.update(row.keys())
        fieldnames = sorted(list(all_keys)) # Sort for consistent column order

        writer = csv.DictWriter(output, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(data)

        output.seek(0) # Go to the beginning of the StringIO buffer
        yield output.getvalue() # Yield the entire CSV content as one chunk

    def get_moengage_file_data(self) -> List[Dict[str, Any]]:
        """
        Generates data for the Moengage-formatted campaign file.
        Filters for active offers and non-DND customers.
        (FR39, FR54, NFR12, NFR13)

        Returns:
            A list of dictionaries, each representing a row for the Moengage CSV.
        """
        stmt = select(
            Customer.customer_id,
            Customer.mobile_number,
            Customer.pan_number,
            Customer.aadhaar_ref_number,
            Customer.ucid_number,
            Customer.customer_segments,
            Customer.propensity_flag,
            Offer.offer_id,
            Offer.offer_type,
            Offer.offer_status,
            Offer.product_type,
            Offer.offer_details,
            Offer.offer_end_date
        ).join(Offer, Customer.customer_id == Offer.customer_id).where(
            and_(
                Offer.offer_status == 'Active',
                Customer.dnd_status == False # FR34: Avoid DND customers
            )
        )
        
        results = self.db.execute(stmt).fetchall()

        moengage_data = []
        for row in results:
            row_dict = row._asdict()
            
            customer_attributes = row_dict.get('customer_attributes', {})
            offer_details = row_dict.get('offer_details', {})
            
            moengage_entry = {
                "customer_id": str(row_dict['customer_id']),
                "mobile_number": row_dict['mobile_number'],
                "pan_number": row_dict['pan_number'],
                "aadhaar_ref_number": row_dict['aadhaar_ref_number'],
                "ucid_number": row_dict['ucid_number'],
                "offer_id": str(row_dict['offer_id']),
                "offer_type": row_dict['offer_type'],
                "product_type": row_dict['product_type'],
                "offer_status": row_dict['offer_status'],
                "offer_end_date": row_dict['offer_end_date'].isoformat() if row_dict['offer_end_date'] else None,
                "customer_segments": ", ".join(row_dict['customer_segments']) if row_dict['customer_segments'] else "",
                "propensity_flag": row_dict['propensity_flag'],
                # Example of flattening offer_details and customer_attributes for Moengage
                "loan_amount": offer_details.get("loan_amount"),
                "interest_rate": offer_details.get("interest_rate"),
                "tenure": offer_details.get("tenure"),
                "customer_name": customer_attributes.get("name"),
                "customer_email": customer_attributes.get("email"),
            }
            moengage_data.append(moengage_entry)
        return moengage_data

    def get_unique_data_file_data(self) -> List[Dict[str, Any]]:
        """
        Generates data for the Unique Data File.
        (FR41, NFR13)

        Returns:
            A list of dictionaries, each representing a unique customer row.
        """
        # Select all unique customers. Since customer_id is primary key, all entries are unique customers.
        stmt = select(
            Customer.customer_id,
            Customer.mobile_number,
            Customer.pan_number,
            Customer.aadhaar_ref_number,
            Customer.ucid_number,
            Customer.previous_loan_app_number,
            Customer.customer_attributes,
            Customer.customer_segments,
            Customer.propensity_flag,
            Customer.dnd_status,
            Customer.created_at
        )
        results = self.db.execute(stmt).fetchall()

        unique_data = []
        for row in results:
            row_dict = row._asdict()
            unique_entry = {
                "customer_id": str(row_dict['customer_id']),
                "mobile_number": row_dict['mobile_number'],
                "pan_number": row_dict['pan_number'],
                "aadhaar_ref_number": row_dict['aadhaar_ref_number'],
                "ucid_number": row_dict['ucid_number'],
                "previous_loan_app_number": row_dict['previous_loan_app_number'],
                "customer_segments": ", ".join(row_dict['customer_segments']) if row_dict['customer_segments'] else "",
                "propensity_flag": row_dict['propensity_flag'],
                "dnd_status": row_dict['dnd_status'],
                "created_at": row_dict['created_at'].isoformat() if row_dict['created_at'] else None,
                # Include relevant customer attributes, flattening JSONB
                "customer_name": row_dict['customer_attributes'].get("name") if row_dict['customer_attributes'] else None,
                "customer_email": row_dict['customer_attributes'].get("email") if row_dict['customer_attributes'] else None,
            }
            unique_data.append(unique_entry)
        return unique_data

    def get_duplicate_data_file_data(self) -> List[Dict[str, Any]]:
        """
        Generates data for the Duplicate Data File.
        This is interpreted as offers marked with 'Duplicate' status based on FR20.
        (FR40, NFR13)

        Returns:
            A list of dictionaries, each representing a duplicate offer row.
        """
        stmt = select(
            Customer.customer_id,
            Customer.mobile_number,
            Customer.pan_number,
            Offer.offer_id,
            Offer.offer_type,
            Offer.product_type,
            Offer.offer_status,
            Offer.created_at
        ).join(Offer, Customer.customer_id == Offer.customer_id).where(
            Offer.offer_status == 'Duplicate'
        )
        results = self.db.execute(stmt).fetchall()

        duplicate_data = []
        for row in results:
            row_dict = row._asdict()
            duplicate_entry = {
                "customer_id": str(row_dict['customer_id']),
                "mobile_number": row_dict['mobile_number'],
                "pan_number": row_dict['pan_number'],
                "offer_id": str(row_dict['offer_id']),
                "offer_type": row_dict['offer_type'],
                "product_type": row_dict['product_type'],
                "offer_status": row_dict['offer_status'],
                "offer_created_at": row_dict['created_at'].isoformat() if row_dict['created_at'] else None,
            }
            duplicate_data.append(duplicate_entry)
        return duplicate_data

    def get_error_excel_data(self, job_id: str = None) -> List[Dict[str, Any]]:
        """
        Generates data for the Error Excel file.
        If job_id is provided, filters errors for that specific job.
        (FR42, FR46, NFR13)

        Args:
            job_id: Optional UUID string to filter errors by a specific upload job.

        Returns:
            A list of dictionaries, each representing an upload error row.
        """
        stmt = select(
            UploadError.error_id,
            UploadError.job_id,
            UploadError.row_data,
            UploadError.error_description,
            UploadError.error_timestamp
        )
        if job_id:
            try:
                job_uuid = uuid.UUID(job_id)
                stmt = stmt.where(UploadError.job_id == job_uuid)
            except ValueError:
                # If job_id is not a valid UUID, return an empty list as no matching errors can be found.
                return []
        
        results = self.db.execute(stmt).fetchall()

        error_data = []
        for row in results:
            row_dict = row._asdict()
            error_entry = {
                "error_id": str(row_dict['error_id']),
                "job_id": str(row_dict['job_id']),
                "row_data_snapshot": str(row_dict['row_data']), # Stringify JSONB for CSV
                "error_description": row_dict['error_description'],
                "error_timestamp": row_dict['error_timestamp'].isoformat() if row_dict['error_timestamp'] else None,
            }
            error_data.append(error_entry)
        return error_data