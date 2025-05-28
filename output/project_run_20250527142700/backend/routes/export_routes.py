from flask import Blueprint, make_response, jsonify
import io
import csv
import pandas as pd
import datetime

# This file defines the API routes for data export functionalities.
# It uses Flask Blueprints to organize routes related to exports.
# The actual data retrieval and processing logic is assumed to be handled
# by a separate service layer (e.g., `backend.services.export_service`).

# --- MOCK DATABASE/SERVICE LAYER ---
# In a real application, these classes and the ExportService would interact
# with a PostgreSQL database using an ORM like SQLAlchemy.
# For the purpose of demonstrating the Flask routes, we use mock data.

class MockCustomer:
    def __init__(self, customer_id, mobile_number, pan_number, is_dnd, segment, attributes):
        self.customer_id = customer_id
        self.mobile_number = mobile_number
        self.pan_number = pan_number
        self.is_dnd = is_dnd
        self.segment = segment
        self.attributes = attributes # This would be a JSONB field in DB

class MockOffer:
    def __init__(self, offer_id, customer_id, offer_type, offer_status, valid_until, is_duplicate):
        self.offer_id = offer_id
        self.customer_id = customer_id
        self.offer_type = offer_type
        self.offer_status = offer_status
        self.valid_until = valid_until
        self.is_duplicate = is_duplicate

class MockDataIngestionError:
    def __init__(self, error_id, timestamp, source_system, record_id, column_name, error_message):
        self.error_id = error_id
        self.timestamp = timestamp
        self.source_system = source_system
        self.record_id = record_id
        self.column_name = column_name
        self.error_message = error_message

# Sample mock data to simulate database records
mock_customers = [
    MockCustomer("cust1", "1234567890", "ABCDE1234F", False, "C1", {"city": "Mumbai", "age_group": "30-40"}),
    MockCustomer("cust2", "0987654321", "FGHIJ5678K", True, "C2", {"city": "Delhi", "occupation": "Salaried"}),
    MockCustomer("cust3", "1122334455", "KLMNO9012L", False, "C1", {"city": "Bangalore", "income_bracket": "High"}),
    MockCustomer("cust4", "1234567890", "ABCDE1234F", False, "C1", {"city": "Mumbai", "age_group": "30-40"}), # Duplicate of cust1 by mobile/pan
]

mock_offers = [
    MockOffer("offer1", "cust1", "Preapproved", "Active", datetime.datetime.now() + datetime.timedelta(days=30), False),
    MockOffer("offer2", "cust2", "Loyalty", "Active", datetime.datetime.now() + datetime.timedelta(days=15), False),
    MockOffer("offer3", "cust1", "Enrich", "Active", datetime.datetime.now() + datetime.timedelta(days=45), True), # Marked as duplicate offer for cust1
    MockOffer("offer4", "cust3", "Fresh", "Active", datetime.datetime.now() + datetime.timedelta(days=60), False),
    MockOffer("offer5", "cust4", "Preapproved", "Active", datetime.datetime.now() + datetime.timedelta(days=30), False), # Offer for a customer identified as duplicate
]

mock_errors = [
    MockDataIngestionError("err1", datetime.datetime.now(), "Offermart", "rec123", "mobile_number", "Invalid format: '123'"),
    MockDataIngestionError("err2", datetime.datetime.now(), "E-aggregator", "rec456", "pan_number", "Missing mandatory field"),
    MockDataIngestionError("err3", datetime.datetime.now() - datetime.timedelta(days=1), "Offermart", "rec789", "offer_amount", "Value out of range"),
]

class ExportService:
    """
    A mock service layer to simulate data retrieval from the database.
    In a real application, this would contain actual database queries.
    """

    @staticmethod
    def get_moengage_campaign_data():
        """
        Retrieves data for Moengage-formatted campaign file.
        Filters for active offers and non-DND customers.
        """
        data = []
        for customer in mock_customers:
            if not customer.is_dnd:
                # Assuming 'Active' and non-'is_duplicate' offers are eligible for Moengage
                customer_eligible_offers = [
                    o for o in mock_offers
                    if o.customer_id == customer.customer_id and o.offer_status == "Active" and not o.is_duplicate
                ]
                for offer in customer_eligible_offers:
                    data.append({
                        "customer_id": customer.customer_id,
                        "mobile_number": customer.mobile_number,
                        "pan_number": customer.pan_number,
                        "segment": customer.segment,
                        "offer_id": offer.offer_id,
                        "offer_type": offer.offer_type,
                        "valid_until": offer.valid_until.strftime("%Y-%m-%d") if offer.valid_until else None
                    })
        return data

    @staticmethod
    def get_duplicate_customer_data():
        """
        Retrieves data for identified duplicate customers.
        This mock identifies customers based on shared mobile/pan or offers marked as duplicate.
        In a real system, this would query a dedicated deduplication log or a flag on customer/offer records.
        """
        duplicate_customer_ids = set()

        # Identify customers with offers marked as 'is_duplicate'
        for offer in mock_offers:
            if offer.is_duplicate:
                duplicate_customer_ids.add(offer.customer_id)

        # Simple mock deduplication logic: find customers with same mobile/pan
        seen_identifiers = {} # (mobile, pan) -> customer_id
        for customer in mock_customers:
            identifier_tuple = (customer.mobile_number, customer.pan_number)
            if identifier_tuple in seen_identifiers and seen_identifiers[identifier_tuple] != customer.customer_id:
                # This customer (current) is a duplicate of the one already seen
                duplicate_customer_ids.add(customer.customer_id)
                # Also add the original customer if not already added
                duplicate_customer_ids.add(seen_identifiers[identifier_tuple])
            else:
                seen_identifiers[identifier_tuple] = customer.customer_id

        data = []
        for customer_id in duplicate_customer_ids:
            customer = next((c for c in mock_customers if c.customer_id == customer_id), None)
            if customer:
                data.append({
                    "customer_id": customer.customer_id,
                    "mobile_number": customer.mobile_number,
                    "pan_number": customer.pan_number,
                    "segment": customer.segment,
                    "is_dnd": customer.is_dnd,
                    "reason_for_duplication": "Example: Matched by mobile/pan or duplicate offer" # Placeholder
                })
        return data

    @staticmethod
    def get_unique_customer_data():
        """
        Retrieves data for unique customer profiles after deduplication.
        In a real system, this would typically be all records in the `customers` table,
        assuming the table itself represents the de-duplicated single customer view.
        """
        # For mock, we'll assume 'cust1', 'cust2', 'cust3' are the unique profiles
        # after 'cust4' was identified as a duplicate of 'cust1' and merged/discarded.
        unique_customer_ids = {"cust1", "cust2", "cust3"}
        data = []
        for customer in mock_customers:
            if customer.customer_id in unique_customer_ids:
                # Convert JSONB attributes to string for CSV compatibility
                attributes_str = str(customer.attributes) if customer.attributes else ""
                data.append({
                    "customer_id": customer.customer_id,
                    "mobile_number": customer.mobile_number,
                    "pan_number": customer.pan_number,
                    "aadhaar_number": "N/A", # Placeholder, if not in mock
                    "ucid_number": "N/A",    # Placeholder, if not in mock
                    "segment": customer.segment,
                    "is_dnd": customer.is_dnd,
                    "attributes": attributes_str
                })
        return data

    @staticmethod
    def get_data_error_data():
        """
        Retrieves data detailing data validation errors from ingestion processes.
        In a real system, this would query a dedicated `data_ingestion_errors` table.
        """
        data = []
        for error in mock_errors:
            data.append({
                "error_id": error.error_id,
                "timestamp": error.timestamp.isoformat(),
                "source_system": error.source_system,
                "record_id": error.record_id,
                "column_name": error.column_name,
                "error_message": error.error_message
            })
        return data

# --- END MOCK DATABASE/SERVICE LAYER ---


# Initialize Flask Blueprint for export routes
export_bp = Blueprint('export', __name__, url_prefix='/exports')

@export_bp.route('/moengage-campaign-file', methods=['GET'])
def export_moengage_campaign_file():
    """
    API Endpoint: /exports/moengage-campaign-file
    Method: GET
    Description: Generates and allows download of a Moengage-formatted CSV file
                 for eligible customers, excluding DND. (FR30)
    """
    try:
        data = ExportService.get_moengage_campaign_data()

        if not data:
            return jsonify({"message": "No eligible campaign data found for export."}), 404

        # Create a CSV file in-memory
        si = io.StringIO()
        # Ensure fieldnames are consistent, even if data is empty (though checked above)
        fieldnames = list(data[0].keys()) if data else []
        writer = csv.DictWriter(si, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=moengage_campaign_data.csv"
        output.headers["Content-type"] = "text/csv"
        return output
    except Exception as e:
        # Log the error for debugging in a real application
        print(f"Error exporting Moengage campaign file: {e}")
        return jsonify({"message": "An internal server error occurred during Moengage file generation.", "error": str(e)}), 500

@export_bp.route('/duplicate-customers', methods=['GET'])
def export_duplicate_customers():
    """
    API Endpoint: /exports/duplicate-customers
    Method: GET
    Description: Generates and allows download of a file containing identified
                 duplicate customer data. (FR31)
    """
    try:
        data = ExportService.get_duplicate_customer_data()

        if not data:
            return jsonify({"message": "No duplicate customer data found for export."}), 404

        # Create a CSV file in-memory
        si = io.StringIO()
        fieldnames = list(data[0].keys()) if data else []
        writer = csv.DictWriter(si, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=duplicate_customer_data.csv"
        output.headers["Content-type"] = "text/csv"
        return output
    except Exception as e:
        print(f"Error exporting duplicate customer data: {e}")
        return jsonify({"message": "An internal server error occurred during duplicate data export.", "error": str(e)}), 500

@export_bp.route('/unique-customers', methods=['GET'])
def export_unique_customers():
    """
    API Endpoint: /exports/unique-customers
    Method: GET
    Description: Generates and allows download of a file containing unique
                 customer data after deduplication. (FR32)
    """
    try:
        data = ExportService.get_unique_customer_data()

        if not data:
            return jsonify({"message": "No unique customer data found for export."}), 404

        # Create a CSV file in-memory
        si = io.StringIO()
        fieldnames = list(data[0].keys()) if data else []
        writer = csv.DictWriter(si, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=unique_customer_data.csv"
        output.headers["Content-type"] = "text/csv"
        return output
    except Exception as e:
        print(f"Error exporting unique customer data: {e}")
        return jsonify({"message": "An internal server error occurred during unique data export.", "error": str(e)}), 500

@export_bp.route('/data-errors', methods=['GET'])
def export_data_errors():
    """
    API Endpoint: /exports/data-errors
    Method: GET
    Description: Generates and allows download of an Excel file detailing
                 data validation errors from ingestion processes. (FR33)
    """
    try:
        data = ExportService.get_data_error_data()

        if not data:
            return jsonify({"message": "No data errors found for export."}), 404

        # Create a Pandas DataFrame and export to Excel in-memory
        df = pd.DataFrame(data)
        output = io.BytesIO()
        # Using 'openpyxl' engine for .xlsx format
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0) # Rewind to the beginning of the stream

        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=data_errors.xlsx"
        response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return response
    except ImportError:
        # This error occurs if pandas or openpyxl is not installed
        return jsonify({"message": "Required libraries (pandas, openpyxl) for Excel export are not installed."}), 500
    except Exception as e:
        print(f"Error exporting data errors: {e}")
        return jsonify({"message": "An internal server error occurred during error file generation.", "error": str(e)}), 500