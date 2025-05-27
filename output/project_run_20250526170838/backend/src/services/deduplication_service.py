import uuid
from datetime import datetime
from sqlalchemy import or_
from src.models import db, Customer # Assuming src.models is the correct path for models

class DeduplicationService:
    """
    Service responsible for deduplicating customer data based on unique identifiers.
    Implements FR3, FR4, FR5 from the BRD.
    """

    def __init__(self):
        pass

    def _find_existing_customer(self, mobile_number: str = None, pan_number: str = None,
                                aadhaar_number: str = None, ucid_number: str = None,
                                loan_application_number: str = None):
        """
        Helper method to find an existing customer in the database based on any
        of the provided unique identifiers.

        Args:
            mobile_number (str): Customer's mobile number.
            pan_number (str): Customer's PAN number.
            aadhaar_number (str): Customer's Aadhaar reference number.
            ucid_number (str): Customer's UCID number.
            loan_application_number (str): Customer's previous loan application number.

        Returns:
            Customer: The existing Customer object if found, otherwise None.
        """
        query_conditions = []
        if mobile_number:
            query_conditions.append(Customer.mobile_number == mobile_number)
        if pan_number:
            query_conditions.append(Customer.pan_number == pan_number)
        if aadhaar_number:
            query_conditions.append(Customer.aadhaar_number == aadhaar_number)
        if ucid_number:
            query_conditions.append(Customer.ucid_number == ucid_number)
        if loan_application_number:
            query_conditions.append(Customer.loan_application_number == loan_application_number)

        if not query_conditions:
            # No identifiers provided, cannot search for a customer
            return None

        # Use or_ to find a customer matching any of the provided identifiers
        # This ensures that if a new record matches an existing customer by any key,
        # it's considered a duplicate of that customer.
        existing_customer = Customer.query.filter(or_(*query_conditions)).first()
        return existing_customer

    def deduplicate_customer(self, customer_data: dict) -> (str, bool):
        """
        Deduplicates a new incoming customer record against existing customer data.
        If a duplicate is found based on any unique identifier (mobile, PAN, Aadhaar, UCID, LAN),
        the existing customer's record is updated with any new non-conflicting information,
        and its customer_id is returned.
        If no duplicate is found, a new customer record is created, and its customer_id is returned.

        This function implements FR3, FR4 (across products via identifiers), and FR5 (against live book).

        Args:
            customer_data (dict): A dictionary containing customer details from an incoming source.
                                  Expected keys: 'mobile_number', 'pan_number', 'aadhaar_number',
                                  'ucid_number', 'loan_application_number', 'dnd_flag', 'segment', etc.

        Returns:
            tuple: (customer_id: str, is_duplicate: bool)
                   - customer_id: The UUID of the unique customer profile (existing or newly created).
                   - is_duplicate: True if the incoming data matched an existing customer, False otherwise.
        """
        mobile_number = customer_data.get('mobile_number')
        pan_number = customer_data.get('pan_number')
        aadhaar_number = customer_data.get('aadhaar_number')
        ucid_number = customer_data.get('ucid_number')
        loan_application_number = customer_data.get('loan_application_number')

        existing_customer = self._find_existing_customer(
            mobile_number=mobile_number,
            pan_number=pan_number,
            aadhaar_number=aadhaar_number,
            ucid_number=ucid_number,
            loan_application_number=loan_application_number
        )

        if existing_customer:
            # Duplicate found. Update the existing customer's record with new information.
            # This ensures a "single profile view" (FR2) is maintained and enriched.
            updated = False
            if mobile_number and existing_customer.mobile_number is None:
                existing_customer.mobile_number = mobile_number
                updated = True
            if pan_number and existing_customer.pan_number is None:
                existing_customer.pan_number = pan_number
                updated = True
            if aadhaar_number and existing_customer.aadhaar_number is None:
                existing_customer.aadhaar_number = aadhaar_number
                updated = True
            if ucid_number and existing_customer.ucid_number is None:
                existing_customer.ucid_number = ucid_number
                updated = True
            if loan_application_number and existing_customer.loan_application_number is None:
                existing_customer.loan_application_number = loan_application_number
                updated = True
            
            # Update other relevant customer attributes if they are new or different
            # For simplicity, only update if existing is None or new value is provided
            if customer_data.get('dnd_flag') is not None and existing_customer.dnd_flag != customer_data['dnd_flag']:
                existing_customer.dnd_flag = customer_data['dnd_flag']
                updated = True
            if customer_data.get('segment') and existing_customer.segment is None:
                existing_customer.segment = customer_data['segment']
                updated = True

            if updated:
                existing_customer.updated_at = datetime.utcnow()
                db.session.commit()

            return existing_customer.customer_id, True
        else:
            # No duplicate found, create a new customer record.
            new_customer_id = str(uuid.uuid4())
            new_customer = Customer(
                customer_id=new_customer_id,
                mobile_number=mobile_number,
                pan_number=pan_number,
                aadhaar_number=aadhaar_number,
                ucid_number=ucid_number,
                loan_application_number=loan_application_number,
                dnd_flag=customer_data.get('dnd_flag', False), # Default to False if not provided
                segment=customer_data.get('segment')
            )
            db.session.add(new_customer)
            db.session.commit()
            return new_customer_id, False

    def get_duplicate_customer_data(self):
        """
        This method is intended to support FR32: "The system shall provide a screen
        for users to download a Duplicate Data File."

        Given the current database schema where unique identifiers (mobile, PAN, etc.)
        are marked as UNIQUE, the `customers` table itself should not contain
        "duplicate" customer records. Deduplication happens *before* insertion
        or by updating an existing master record.

        Therefore, a "Duplicate Data File" would typically refer to a log of
        *incoming records* that were identified as duplicates and either rejected
        or merged into an existing customer profile. This would require a dedicated
        `deduplication_log` table (not present in the provided schema) to store
        these incoming duplicate records.

        Without such a log table, this method cannot directly query for "duplicate data"
        from the `customers` table in a meaningful way that aligns with FR32.

        For the purpose of this file, and adhering strictly to the provided schema,
        this method will return an empty list and print a warning, as the data
        it's supposed to retrieve is not stored in the current schema.
        A proper implementation would require a `deduplication_log` table.
        """
        print("WARNING: `get_duplicate_customer_data` cannot be fully implemented "
              "without a dedicated `deduplication_log` table in the schema to store "
              "incoming records identified as duplicates (FR32).")
        return []

    def get_unique_customer_data(self):
        """
        This method is intended to support FR33: "The system shall provide a screen
        for users to download a Unique Data File."

        Since the `customers` table, after deduplication, is designed to hold
        only unique customer profiles, this method simply retrieves all records
        from the `customers` table.

        Returns:
            list: A list of dictionaries, each representing a unique customer profile.
        """
        unique_customers = Customer.query.all()
        # Convert SQLAlchemy objects to dictionaries for easier consumption by API/CSV export
        return [
            {
                'customer_id': customer.customer_id,
                'mobile_number': customer.mobile_number,
                'pan_number': customer.pan_number,
                'aadhaar_number': customer.aadhaar_number,
                'ucid_number': customer.ucid_number,
                'loan_application_number': customer.loan_application_number,
                'dnd_flag': customer.dnd_flag,
                'segment': customer.segment,
                'created_at': customer.created_at.isoformat() if customer.created_at else None,
                'updated_at': customer.updated_at.isoformat() if customer.updated_at else None,
                # Add other customer attributes as needed for the unique data file
            }
            for customer in unique_customers
        ]