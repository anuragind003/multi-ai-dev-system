import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, Date, or_, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

# Base for SQLAlchemy declarative models. In a larger Flask application,
# this would typically be imported from a central `models.py` or `app.py`
# where `db = SQLAlchemy(app)` is initialized.
Base = declarative_base()


class Customer(Base):
    """
    SQLAlchemy model for the 'customers' table.
    Corresponds to FR2 (single profile view) and stores core customer identifiers.
    """
    __tablename__ = 'customers'
    customer_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    mobile_number = Column(String, unique=True)
    pan_number = Column(String, unique=True)
    aadhaar_number = Column(String, unique=True)
    ucid_number = Column(String, unique=True)
    loan_application_number = Column(String, unique=True)
    dnd_flag = Column(Boolean, default=False)
    segment = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    offers = relationship("Offer", back_populates="customer")

    def __repr__(self):
        return (f"<Customer(id='{self.customer_id}', "
                f"mobile='{self.mobile_number}', "
                f"pan='{self.pan_number}')>")


class Offer(Base):
    """
    SQLAlchemy model for the 'offers' table.
    Stores details about customer offers, including type and status.
    Relevant for FR6 (Top-up deduplication logic).
    """
    __tablename__ = 'offers'
    offer_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey('customers.customer_id'), nullable=False)
    offer_type = Column(String)  # 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status = Column(String)  # 'Active', 'Inactive', 'Expired'
    propensity = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    channel = Column(String)  # For attribution logic
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="offers")

    def __repr__(self):
        return (f"<Offer(id='{self.offer_id}', customer_id='{self.customer_id}', "
                f"type='{self.offer_type}')>")


class DeduplicationService:
    """
    Service responsible for deduplicating customer data based on various identifiers
    as per FR3, FR4, FR5, and FR6.
    """

    def __init__(self, db_session):
        """
        Initializes the DeduplicationService with a SQLAlchemy database session.

        Args:
            db_session: An active SQLAlchemy session object.
        """
        self.db_session = db_session

    def find_duplicate_customer(self, customer_data: dict) -> tuple[bool, str | None, list[str]]:
        """
        Checks for existing customer records based on provided identifiers.

        Implements FR3: Deduplicate customer data based on Mobile number, Pan number,
        Aadhaar reference number, UCID number, or previous loan application number.
        Implements FR4: Applies deduplication logic across all Consumer Loan products.
        Implements FR5: Deduplicates against the 'live book' (Customer 360) by querying
                       the existing 'customers' table.
        Implements FR6: Deduplicates Top-up loan offers only within other Top-up offers.

        Args:
            customer_data (dict): A dictionary containing potential customer identifiers
                                  like 'mobile_number', 'pan_number', 'aadhaar_number',
                                  'ucid_number', 'loan_application_number', and optionally
                                  'loan_type' (for Top-up specific logic).

        Returns:
            tuple: (is_duplicate, existing_customer_id, matched_identifiers)
                   - is_duplicate (bool): True if a duplicate is found, False otherwise.
                   - existing_customer_id (str | None): The ID of the existing customer
                                                        if a duplicate is found, otherwise None.
                   - matched_identifiers (list[str]): A list of identifiers that caused the match
                                                      (e.g., ['mobile_number', 'pan_number']).
        """
        query_filters = []
        matched_identifiers = []

        # FR3: Deduplicate based on Mobile number, Pan number, Aadhaar reference number, UCID number
        if customer_data.get('mobile_number'):
            query_filters.append(Customer.mobile_number == customer_data['mobile_number'])
        if customer_data.get('pan_number'):
            query_filters.append(Customer.pan_number == customer_data['pan_number'])
        if customer_data.get('aadhaar_number'):
            query_filters.append(Customer.aadhaar_number == customer_data['aadhaar_number'])
        if customer_data.get('ucid_number'):
            query_filters.append(Customer.ucid_number == customer_data['ucid_number'])

        # FR3 & FR6: Deduplicate based on previous loan application number,
        # with Top-up specific logic
        if customer_data.get('loan_application_number'):
            loan_app_num = customer_data['loan_application_number']
            incoming_loan_type = customer_data.get('loan_type')

            if incoming_loan_type and incoming_loan_type.lower() == 'top-up':
                # FR6: Deduplicate Top-up loan offers only within other Top-up offers.
                # Find customer by loan_application_number first.
                customer_by_lan = self.db_session.query(Customer).filter_by(
                    loan_application_number=loan_app_num
                ).first()

                if customer_by_lan:
                    # Check if this existing customer has any 'Top-up' offers associated.
                    has_top_up_offer = self.db_session.query(Offer).filter(
                        Offer.customer_id == customer_by_lan.customer_id,
                        Offer.offer_type.ilike('%top-up%')  # Case-insensitive match
                    ).first()
                    if has_top_up_offer:
                        # If existing customer with this LAN also has a Top-up offer,
                        # then this LAN match is considered a duplicate.
                        query_filters.append(Customer.loan_application_number == loan_app_num)
                    # Else: If existing customer with this LAN does NOT have a Top-up offer,
                    # this LAN match is NOT considered a duplicate for the Top-up rule.
                    # So, we do not add it to query_filters.
            else:
                # For non-Top-up loans, or if loan_type is not provided,
                # a match on loan_application_number is always a duplicate.
                query_filters.append(Customer.loan_application_number == loan_app_num)

        if not query_filters:
            # No identifiable information provided to perform deduplication
            return False, None, []

        # Combine all filters with OR logic to find any matching customer
        duplicate_customer = self.db_session.query(Customer).filter(or_(*query_filters)).first()

        if duplicate_customer:
            existing_customer_id = duplicate_customer.customer_id
            # Determine which identifiers actually matched the found duplicate
            if (customer_data.get('mobile_number') and
                    duplicate_customer.mobile_number == customer_data['mobile_number']):
                matched_identifiers.append('mobile_number')
            if (customer_data.get('pan_number') and
                    duplicate_customer.pan_number == customer_data['pan_number']):
                matched_identifiers.append('pan_number')
            if (customer_data.get('aadhaar_number') and
                    duplicate_customer.aadhaar_number == customer_data['aadhaar_number']):
                matched_identifiers.append('aadhaar_number')
            if (customer_data.get('ucid_number') and
                    duplicate_customer.ucid_number == customer_data['ucid_number']):
                matched_identifiers.append('ucid_number')

            # Re-evaluate loan_application_number match for matched_identifiers list
            if (customer_data.get('loan_application_number') and
                    duplicate_customer.loan_application_number ==
                    customer_data['loan_application_number']):
                incoming_loan_type = customer_data.get('loan_type')
                if incoming_loan_type and incoming_loan_type.lower() == 'top-up':
                    # If incoming is Top-up, confirm existing customer has a Top-up offer
                    has_top_up_offer = self.db_session.query(Offer).filter(
                        Offer.customer_id == duplicate_customer.customer_id,
                        Offer.offer_type.ilike('%top-up%')
                    ).first()
                    if has_top_up_offer:
                        matched_identifiers.append('loan_application_number')
                else:
                    # For non-Top-up, always add if LAN matches
                    matched_identifiers.append('loan_application_number')

            return True, existing_customer_id, matched_identifiers
        else:
            return False, None, []

    def get_unique_customer_data(self, customer_data: dict) -> dict:
        """
        Processes incoming customer data to ensure uniqueness.
        If a duplicate is found, it returns the existing customer's ID.
        If unique, it prepares the data for a new customer entry.

        This method is a higher-level wrapper that uses find_duplicate_customer.
        It's useful for ingestion processes where you either link to an existing
        customer or create a new one.

        Args:
            customer_data (dict): The incoming customer data.

        Returns:
            dict: A dictionary containing 'customer_id' (existing or new UUID),
                  'is_new_customer' (bool), and 'matched_identifiers' (list).
        """
        is_duplicate, existing_customer_id, matched_identifiers = \
            self.find_duplicate_customer(customer_data)

        if is_duplicate:
            return {
                'customer_id': existing_customer_id,
                'is_new_customer': False,
                'matched_identifiers': matched_identifiers
            }
        else:
            # Generate a new customer ID for a truly unique customer
            new_customer_id = str(uuid.uuid4())
            return {
                'customer_id': new_customer_id,
                'is_new_customer': True,
                'matched_identifiers': []
            }


# Example Usage (for testing/demonstration purposes)
if __name__ == '__main__':
    # Setup an in-memory SQLite database for demonstration.
    # In a real Flask application, you would use your configured
    # PostgreSQL database and get the session from your Flask-SQLAlchemy `db` object.
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)  # Create tables based on models
    Session = sessionmaker(bind=engine)
    session = Session()

    dedup_service = DeduplicationService(session)

    print("--- Initializing Test Data ---")
    # Create some initial customers for testing deduplication
    customer1 = Customer(
        mobile_number='9876543210',
        pan_number='ABCDE1234F',
        aadhaar_number='111122223333',
        segment='C1'
    )
    customer2 = Customer(
        mobile_number='9988776655',
        ucid_number='UCID001',
        segment='C2'
    )
    customer3_topup = Customer(
        mobile_number='9999999999',
        loan_application_number='LAN_TOPUP_001',
        segment='C3'
    )
    # Add a Top-up offer for customer3_topup to satisfy FR6 condition
    offer_topup = Offer(
        customer_id=customer3_topup.customer_id,
        offer_type='Top-up Loan',
        offer_status='Active',
        start_date=datetime.now().date(),
        end_date=datetime.now().date()
    )

    session.add_all([customer1, customer2, customer3_topup, offer_topup])
    session.commit()
    print("Test customers and offers added.")

    print("\n--- Testing Deduplication ---")

    # Test Case 1: New customer, truly unique
    new_data_unique = {
        'mobile_number': '1112223333',
        'pan_number': 'FGHIJ5678K',
        'aadhaar_number': '444455556666',
        'ucid_number': 'UCID002',
        'loan_application_number': 'LAN_NEW_001',
        'loan_type': 'Personal Loan'
    }
    is_dup, existing_id, matched_ids = dedup_service.find_duplicate_customer(
        new_data_unique
    )
    print(f"Test 1 (Unique): Is Duplicate? {is_dup}, Existing ID: {existing_id}, "
          f"Matched: {matched_ids}")
    assert not is_dup
    assert existing_id is None
    assert not matched_ids

    # Test Case 2: Duplicate by mobile number
    new_data_dup_mobile = {
        'mobile_number': '9876543210',  # Matches customer1
        'pan_number': 'XYZAB9876C'  # Different PAN
    }
    is_dup, existing_id, matched_ids = dedup_service.find_duplicate_customer(
        new_data_dup_mobile
    )
    print(f"Test 2 (Dup Mobile): Is Duplicate? {is_dup}, Existing ID: {existing_id}, "
          f"Matched: {matched_ids}")
    assert is_dup
    assert existing_id == customer1.customer_id
    assert 'mobile_number' in matched_ids

    # Test Case 3: Duplicate by PAN number
    new_data_dup_pan = {
        'pan_number': 'ABCDE1234F',  # Matches customer1
        'mobile_number': '1234567890'  # Different mobile
    }
    is_dup, existing_id, matched_ids = dedup_service.find_duplicate_customer(
        new_data_dup_pan
    )
    print(f"Test 3 (Dup PAN): Is Duplicate? {is_dup}, Existing ID: {existing_id}, "
          f"Matched: {matched_ids}")
    assert is_dup
    assert existing_id == customer1.customer_id
    assert 'pan_number' in matched_ids

    # Test Case 4: Duplicate by UCID
    new_data_dup_ucid = {
        'ucid_number': 'UCID001',  # Matches customer2
        'mobile_number': '5554443333'
    }
    is_dup, existing_id, matched_ids = dedup_service.find_duplicate_customer(
        new_data_dup_ucid
    )
    print(f"Test 4 (Dup UCID): Is Duplicate? {is_dup}, Existing ID: {existing_id}, "
          f"Matched: {matched_ids}")
    assert is_dup
    assert existing_id == customer2.customer_id
    assert 'ucid_number' in matched_ids

    # Test Case 5: Duplicate by loan_application_number (non-Top-up)
    customer4_non_topup = Customer(
        mobile_number='1010101010',
        loan_application_number='LAN_NON_TOPUP_001',
        segment='C4'
    )
    session.add(customer4_non_topup)
    session.commit()

    new_data_dup_lan_non_topup = {
        'loan_application_number': 'LAN_NON_TOPUP_001',  # Matches customer4
        'mobile_number': '2020202020',
        'loan_type': 'Personal Loan'
    }
    is_dup, existing_id, matched_ids = dedup_service.find_duplicate_customer(
        new_data_dup_lan_non_topup
    )
    print(f"Test 5 (Dup LAN Non-Top-up): Is Duplicate? {is_dup}, Existing ID: {existing_id}, "
          f"Matched: {matched_ids}")
    assert is_dup
    assert existing_id == customer4_non_topup.customer_id
    assert 'loan_application_number' in matched_ids

    # Test Case 6: Duplicate by loan_application_number (Top-up to Top-up)
    new_data_dup_lan_topup = {
        'loan_application_number': 'LAN_TOPUP_001',  # Matches customer3_topup
        'mobile_number': '8888888888',
        'loan_type': 'Top-up'
    }
    is_dup, existing_id, matched_ids = dedup_service.find_duplicate_customer(
        new_data_dup_lan_topup
    )
    print(f"Test 6 (Dup LAN Top-up to Top-up): Is Duplicate? {is_dup}, Existing ID: {existing_id}, "
          f"Matched: {matched_ids}")
    assert is_dup
    assert existing_id == customer3_topup.customer_id
    assert 'loan_application_number' in matched_ids

    # Test Case 7: Duplicate by loan_application_number (Top-up to Non-Top-up)
    # Should NOT be a duplicate by LAN due to FR6
    customer5_non_topup_lan = Customer(
        mobile_number='7777777777',
        loan_application_number='LAN_TOPUP_002',
        segment='C5'
    )
    # This customer has a loan_application_number but it's associated with a non-Top-up offer
    offer_non_topup_for_lan = Offer(
        customer_id=customer5_non_topup_lan.customer_id,
        offer_type='Personal Loan',
        offer_status='Active',
        start_date=datetime.now().date(),
        end_date=datetime.now().date()
    )
    session.add_all([customer5_non_topup_lan, offer_non_topup_for_lan])
    session.commit()

    new_data_topup_to_non_topup_lan = {
        'loan_application_number': 'LAN_TOPUP_002',  # Matches customer5_non_topup_lan
        'mobile_number': '6666666666',
        'loan_type': 'Top-up'  # Incoming is Top-up
    }
    is_dup, existing_id, matched_ids = dedup_service.find_duplicate_customer(
        new_data_topup_to_non_topup_lan
    )
    print(f"Test 7 (Dup LAN Top-up to Non-Top-up): Is Duplicate? {is_dup}, "
          f"Existing ID: {existing_id}, Matched: {matched_ids}")
    assert not is_dup  # Should not be a duplicate based on LAN for Top-up rule
    assert existing_id is None
    assert not matched_ids

    # Test Case 8: Using get_unique_customer_data for a new customer
    result_unique = dedup_service.get_unique_customer_data(new_data_unique)
    print(f"Test 8 (get_unique_customer_data Unique): {result_unique}")
    assert result_unique['is_new_customer']
    assert result_unique['customer_id'] is not None
    assert not result_unique['matched_identifiers']

    # Test Case 9: Using get_unique_customer_data for a duplicate customer
    result_dup = dedup_service.get_unique_customer_data(new_data_dup_mobile)
    print(f"Test 9 (get_unique_customer_data Duplicate): {result_dup}")
    assert not result_dup['is_new_customer']
    assert result_dup['customer_id'] == customer1.customer_id
    assert 'mobile_number' in result_dup['matched_identifiers']

    session.close()
    print("\nAll tests passed!")