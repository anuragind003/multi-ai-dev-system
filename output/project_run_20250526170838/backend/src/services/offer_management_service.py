import uuid
from datetime import datetime, date, timedelta
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_, and_

# --- Mock Database and Models for direct runnability ---
# In a real Flask application, you would typically have:
# from backend.src.extensions import db
# from backend.src.models import Customer, Offer, Event
# And the models would be defined using db.Model (e.g., class Customer(db.Model): ...)

class MockDB:
    """A mock database object to simulate Flask-SQLAlchemy's db."""
    def __init__(self):
        self.session = MockSession()
        self._data = {
            'Customer': {},
            'Offer': {},
            'Event': {}
        }

    def init_app(self, app):
        pass # No-op for mock

class MockSession:
    """A mock session object to simulate SQLAlchemy's session."""
    def __init__(self):
        self._added = []
        self._deleted = []
        self._mock_data = {
            'Customer': {},
            'Offer': {},
            'Event': {}
        }

    def add(self, obj):
        self._added.append(obj)

    def commit(self):
        for obj in self._added:
            model_name = obj.__class__.__name__
            if model_name not in self._mock_data:
                self._mock_data[model_name] = {}
            # Assuming primary key is the first attribute for simplicity
            pk_attr = next(iter(obj.__dict__))
            pk_value = getattr(obj, pk_attr)
            self._mock_data[model_name][pk_value] = obj
        self._added = []
        # print("Mock DB: Committed transaction")

    def rollback(self):
        self._added = []
        # print("Mock DB: Rolled back transaction")

    def query(self, model):
        return MockQuery(model, self._mock_data)

    def close(self):
        pass # print("Mock DB: Session closed")

class MockQuery:
    """A mock query object to simulate SQLAlchemy's query."""
    def __init__(self, model, mock_data):
        self.model = model
        self._filters = []
        self._order_by = []
        self._mock_data = mock_data[model.__name__]

    def filter(self, *args):
        self._filters.extend(args)
        return self

    def filter_by(self, **kwargs):
        self._filters.append(kwargs)
        return self

    def join(self, other_model):
        # For mock, we just pass through. Actual join logic is complex.
        # We'll handle join logic manually in the service for mock data.
        return self

    def order_by(self, *args):
        self._order_by.extend(args)
        return self

    def first(self):
        results = self._apply_filters(list(self._mock_data.values()))
        if self._order_by:
            # Simple mock for order_by, assuming it's a single attribute
            attr = self._order_by[0].key if hasattr(self._order_by[0], 'key') else str(self._order_by[0]).split('.')[-1]
            reverse = 'desc' in str(self._order_by[0]).lower()
            results.sort(key=lambda x: getattr(x, attr, None), reverse=reverse)
        return results[0] if results else None

    def all(self):
        results = self._apply_filters(list(self._mock_data.values()))
        if self._order_by:
            attr = self._order_by[0].key if hasattr(self._order_by[0], 'key') else str(self._order_by[0]).split('.')[-1]
            reverse = 'desc' in str(self._order_by[0]).lower()
            results.sort(key=lambda x: getattr(x, attr, None), reverse=reverse)
        return results

    def _apply_filters(self, data_list):
        filtered_data = []
        for item in data_list:
            match = True
            for f in self._filters:
                if isinstance(f, dict): # filter_by(key=value)
                    for k, v in f.items():
                        if not hasattr(item, k) or getattr(item, k) != v:
                            match = False
                            break
                elif hasattr(f, 'left') and hasattr(f, 'right'): # filter(Column == value)
                    # This is a very basic mock for comparison operators
                    col_name = f.left.key if hasattr(f.left, 'key') else str(f.left).split('.')[-1]
                    if not hasattr(item, col_name):
                        match = False
                        break
                    item_value = getattr(item, col_name)
                    if hasattr(f, 'operator'):
                        op = f.operator.__name__
                        if op == '__eq__':
                            if item_value != f.right: match = False
                        elif op == '__lt__':
                            if not (item_value < f.right): match = False
                        elif op == 'in_': # For .in_() operator
                            if item_value not in f.right: match = False
                        # Add more operators as needed
                    else: # Assume direct comparison if no operator
                        if item_value != f.right: match = False
                elif isinstance(f, (or_, and_)):
                    # Mock for OR/AND. This is highly simplified.
                    # For a real mock, you'd parse the expression tree.
                    # For now, assume simple OR/AND of direct comparisons.
                    sub_match = False
                    if isinstance(f, or_):
                        for clause in f.clauses:
                            col_name = clause.left.key if hasattr(clause.left, 'key') else str(clause.left).split('.')[-1]
                            if hasattr(item, col_name) and getattr(item, col_name) == clause.right:
                                sub_match = True
                                break
                        if not sub_match: match = False
                    elif isinstance(f, and_):
                        for clause in f.clauses:
                            col_name = clause.left.key if hasattr(clause.left, 'key') else str(clause.left).split('.')[-1]
                            if not (hasattr(item, col_name) and getattr(item, col_name) == clause.right):
                                sub_match = False
                                break
                        if not sub_match: match = True # If all clauses match, sub_match remains True
                        if not sub_match: match = False # If any clause didn't match, overall match is False
                else:
                    # Fallback for unhandled filter types
                    pass # print(f"Warning: Unhandled filter type {type(f)}")

            if match:
                filtered_data.append(item)
        return filtered_data

# Mock Models (simplified classes to hold data)
class Customer:
    def __init__(self, customer_id, mobile_number, pan_number, aadhaar_number=None, ucid_number=None, loan_application_number=None, dnd_flag=False, segment=None, created_at=None, updated_at=None):
        self.customer_id = customer_id
        self.mobile_number = mobile_number
        self.pan_number = pan_number
        self.aadhaar_number = aadhaar_number
        self.ucid_number = ucid_number
        self.loan_application_number = loan_application_number
        self.dnd_flag = dnd_flag
        self.segment = segment
        self.created_at = created_at if created_at else datetime.now()
        self.updated_at = updated_at if updated_at else datetime.now()
    def __repr__(self):
        return f"<Customer {self.customer_id}>"
    # For mock query filter
    @property
    def key(self): return 'customer_id'

class Offer:
    def __init__(self, offer_id, customer_id, offer_type=None, offer_status='Active', propensity=None, start_date=None, end_date=None, channel=None, created_at=None, updated_at=None):
        self.offer_id = offer_id
        self.customer_id = customer_id
        self.offer_type = offer_type
        self.offer_status = offer_status
        self.propensity = propensity
        self.start_date = start_date if start_date else date.today()
        self.end_date = end_date
        self.channel = channel
        self.created_at = created_at if created_at else datetime.now()
        self.updated_at = updated_at if updated_at else datetime.now()
    def __repr__(self):
        return f"<Offer {self.offer_id} for Customer {self.customer_id}>"
    # For mock query filter
    @property
    def key(self): return 'offer_id'

class Event:
    def __init__(self, event_id, customer_id, event_type, event_source, event_timestamp, event_details=None, created_at=None):
        self.event_id = event_id
        self.customer_id = customer_id
        self.event_type = event_type
        self.event_source = event_source
        self.event_timestamp = event_timestamp
        self.event_details = event_details if event_details else {}
        self.created_at = created_at if created_at else datetime.now()
    def __repr__(self):
        return f"<Event {self.event_id} Type: {self.event_type}>"
    # For mock query filter
    @property
    def key(self): return 'event_id'

# Initialize the mock db object
db = MockDB()

# --- End Mock Database and Models ---


class OfferManagementService:
    def __init__(self, db_session):
        """
        Initializes the OfferManagementService with a database session.
        Args:
            db_session: The SQLAlchemy session object (e.g., db.session from Flask-SQLAlchemy).
        """
        self.db = db_session

    def create_or_update_offer(self, customer_id: str, offer_data: dict) -> dict:
        """
        Creates a new offer or updates an existing one for a customer.
        Implements FR8 (update old offers) and FR14 (prevent modification if journey started).

        Args:
            customer_id (str): The ID of the customer.
            offer_data (dict): A dictionary containing offer details.
                               Expected keys: 'offer_id' (optional for update), 'offer_type',
                               'offer_status', 'propensity', 'start_date', 'end_date', 'channel'.

        Returns:
            dict: A dictionary indicating success/failure and relevant messages/IDs.
        """
        try:
            customer = self.db.query(Customer).filter_by(customer_id=customer_id).first()
            if not customer:
                return {"status": "failed", "message": f"Customer with ID {customer_id} not found."}

            # FR14: Prevent modification of customer offers with a started loan application journey
            # until the application is expired or rejected.
            # This requires checking the latest status of any active loan application journey for the customer.
            # We assume 'LOAN_LOGIN' or similar marks the start of a journey.
            # 'LOAN_REJECTED', 'LOAN_EXPIRED', 'LOAN_DISBURSED' mark the end.
            journey_start_events = self.db.query(Event).filter(
                Event.customer_id == customer_id,
                Event.event_type.in_(['LOAN_LOGIN', 'BUREAU_CHECK', 'OFFER_DETAILS', 'EKYC_ACHIEVED', 'BANK_DETAILS', 'E_SIGN'])
            ).order_by(Event.event_timestamp.desc()).first()

            if journey_start_events:
                # Check if the latest event indicates the journey has ended
                journey_end_events = self.db.query(Event).filter(
                    Event.customer_id == customer_id,
                    Event.event_type.in_(['LOAN_REJECTED', 'LOAN_EXPIRED', 'LOAN_DISBURSED'])
                ).order_by(Event.event_timestamp.desc()).first()

                if not journey_end_events or journey_end_events.event_timestamp < journey_start_events.event_timestamp:
                    # If there's a journey start event and no subsequent end event, or end event is older,
                    # then the journey is considered active.
                    return {"status": "failed", "message": "Cannot modify offer: Customer has an active loan application journey."}

            offer_id = offer_data.get('offer_id')
            existing_offer = None
            if offer_id:
                existing_offer = self.db.query(Offer).filter_by(offer_id=offer_id, customer_id=customer_id).first()

            if existing_offer:
                # FR8: Update old offers
                for key, value in offer_data.items():
                    # Prevent updating primary key or creation timestamp
                    if hasattr(existing_offer, key) and key not in ['offer_id', 'customer_id', 'created_at']:
                        setattr(existing_offer, key, value)
                existing_offer.updated_at = datetime.now()
                self.db.add(existing_offer) # SQLAlchemy tracks changes to objects in session
                message = "Offer updated successfully."
            else:
                # Create new offer
                new_offer_id = str(uuid.uuid4())
                new_offer = Offer(
                    offer_id=new_offer_id,
                    customer_id=customer_id,
                    offer_type=offer_data.get('offer_type'),  # FR17
                    offer_status=offer_data.get('offer_status', 'Active'),  # FR16
                    propensity=offer_data.get('propensity'),  # FR18
                    start_date=offer_data.get('start_date', date.today()),
                    end_date=offer_data.get('end_date'),
                    channel=offer_data.get('channel')  # For attribution logic (FR21)
                )
                self.db.add(new_offer)
                offer_id = new_offer_id
                message = "Offer created successfully."

            self.db.commit()
            return {"status": "success", "offer_id": offer_id, "message": message}

        except SQLAlchemyError as e:
            self.db.rollback()
            print(f"Database error during offer creation/update: {e}")
            return {"status": "failed", "message": "Database error during offer operation."}
        except Exception as e:
            self.db.rollback()
            print(f"An unexpected error occurred during offer creation/update: {e}")
            return {"status": "failed", "message": "An unexpected error occurred."}

    def get_customer_offers(self, customer_id: str) -> list:
        """
        Retrieves all offers for a given customer.
        Used for FR2 (single profile view) and /customers/{customer_id} API.

        Args:
            customer_id (str): The ID of the customer.

        Returns:
            list: A list of dictionaries, each representing an offer.
        """
        try:
            offers = self.db.query(Offer).filter_by(customer_id=customer_id).all()
            return [
                {
                    "offer_id": offer.offer_id,
                    "offer_type": offer.offer_type,
                    "offer_status": offer.offer_status,
                    "propensity": offer.propensity,
                    "start_date": offer.start_date.isoformat() if offer.start_date else None,
                    "end_date": offer.end_date.isoformat() if offer.end_date else None,
                    "channel": offer.channel
                } for offer in offers
            ]
        except SQLAlchemyError as e:
            print(f"Database error retrieving customer offers: {e}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred while retrieving customer offers: {e}")
            return []

    def update_expired_offers_batch(self) -> dict:
        """
        Scheduled job to update offer statuses to 'Expired'.
        Implements FR41 (non-journey started) and FR43 (journey started LAN validity).
        Note: The distinction between FR41 and FR43 based on LAN validity is complex
        without a direct LAN-to-offer link in the schema or clear LAN validity rules.
        For MVP, offers are marked expired if their end_date is in the past.
        """
        try:
            today = date.today()
            updated_count = 0

            # Find all active offers whose end_date is in the past
            offers_to_expire = self.db.query(Offer).filter(
                Offer.offer_status == 'Active',
                Offer.end_date < today
            ).all()

            for offer in offers_to_expire:
                # Mark offer as expired
                offer.offer_status = 'Expired'
                offer.updated_at = datetime.now()
                self.db.add(offer)
                updated_count += 1

            self.db.commit()
            return {"status": "success", "message": f"Successfully expired {updated_count} offers."}

        except SQLAlchemyError as e:
            self.db.rollback()
            print(f"Database error during batch offer expiry: {e}")
            return {"status": "failed", "message": "Database error during batch offer expiry."}
        except Exception as e:
            self.db.rollback()
            print(f"An unexpected error occurred during batch offer expiry: {e}")
            return {"status": "failed", "message": "An unexpected error occurred."}

    def apply_attribution_logic(self, customer_id: str, new_offer_data: dict) -> dict:
        """
        Implements FR21: Determine which channel/offer prevails when a customer has multiple interactions
        or existing offers. This function helps determine the 'offer_type' or 'offer_status'
        for a new offer based on existing offers.

        Args:
            customer_id (str): The ID of the customer.
            new_offer_data (dict): The data for the new offer, which might be modified by this logic.

        Returns:
            dict: A dictionary indicating success and a message. The `new_offer_data` dict is modified in place.
        """
        existing_active_offers = self.db.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.offer_status == 'Active'
        ).all()

        if not existing_active_offers:
            # If no active offers, the new offer is 'Fresh' (FR17)
            new_offer_data['offer_type'] = 'Fresh'
            new_offer_data['offer_status'] = 'Active'
            message = "New offer determined as 'Fresh' due to no existing active offers."
        else:
            # Complex business logic for 'Enrich', 'New-old', 'New-new' (FR17)
            # This is a placeholder. Actual rules would be defined by business.
            # Example: If the new offer is from the same channel as an existing active offer,
            # it might be an 'Enrich' offer. If it's a completely new offer for a customer
            # who had previous offers but no current active ones, it might be 'New-new'.
            # If an old offer is being re-sent, it might be 'New-old'.
            # For MVP, if there are existing active offers, default to 'Enrich' unless specified.
            new_offer_data['offer_type'] = new_offer_data.get('offer_type', 'Enrich')
            new_offer_data['offer_status'] = new_offer_data.get('offer_status', 'Active')
            message = "Attribution logic applied, offer type potentially set based on existing offers."

            # Further logic could involve comparing propensity, channel preference, etc.
            # For example, if a new offer has a significantly higher propensity, it might
            # supersede or be prioritized over existing ones. This would impact campaign generation.

        return {"status": "success", "message": message}

    def get_offers_for_moengage_export(self) -> list:
        """
        Retrieves offers suitable for Moengage export.
        This typically involves active offers, excluding DND customers (FR23).

        Returns:
            list: A list of dictionaries, each representing an offer formatted for export.
        """
        try:
            # Join Offers with Customers to filter out DND customers (FR23)
            # In a real SQLAlchemy setup, this would be a proper join.
            # For mock, we'll fetch all and filter in Python.
            all_active_offers = self.db.query(Offer).filter(Offer.offer_status == 'Active').all()
            
            formatted_offers = []
            for offer in all_active_offers:
                customer = self.db.query(Customer).filter_by(customer_id=offer.customer_id).first()
                if customer and not customer.dnd_flag: # Exclude DND customers
                    formatted_offers.append({
                        "customer_id": offer.customer_id,
                        "mobile_number": customer.mobile_number,
                        "pan_number": customer.pan_number,
                        "offer_id": offer.offer_id,
                        "offer_type": offer.offer_type,
                        "propensity": offer.propensity,
                        "start_date": offer.start_date.isoformat() if offer.start_date else '',
                        "end_date": offer.end_date.isoformat() if offer.end_date else '',
                        "channel": offer.channel,
                        # Add other fields required by Moengage (e.g., loan amount, product type)
                        # These would need to be part of the Offer or Customer schema or derived.
                    })
            return formatted_offers
        except SQLAlchemyError as e:
            print(f"Database error retrieving offers for Moengage export: {e}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred while retrieving offers for Moengage export: {e}")
            return []

# --- Example Usage (for testing the service logic) ---
if __name__ == '__main__':
    # Initialize the service with the mock db session
    offer_service = OfferManagementService(db.session)

    print("\n--- Test Case 1: Create a new offer for a non-existent customer (should fail) ---")
    result = offer_service.create_or_update_offer(
        customer_id="non_existent_cust",
        offer_data={
            "offer_type": "Fresh",
            "propensity": "High",
            "end_date": date.today() + timedelta(days=90),
            "channel": "Web"
        }
    )
    print(result)

    print("\n--- Test Case 2: Create a new offer for an existing customer ---")
    # Simulate adding a customer first
    db.session.add(Customer(customer_id='cust123', mobile_number='1234567890', pan_number='ABCDE1234F', dnd_flag=False, segment='C1'))
    db.session.commit()
    result = offer_service.create_or_update_offer(
        customer_id="cust123",
        offer_data={
            "offer_type": "Fresh",
            "propensity": "High",
            "end_date": date.today() + timedelta(days=90),
            "channel": "Web"
        }
    )
    print(result)
    new_offer_id = result.get('offer_id')

    print("\n--- Test Case 3: Update an existing offer ---")
    if new_offer_id:
        result = offer_service.create_or_update_offer(
            customer_id="cust123",
            offer_data={
                "offer_id": new_offer_id,
                "offer_status": "Active",
                "propensity": "Very High",
                "end_date": date.today() + timedelta(days=120)
            }
        )
        print(result)

    print("\n--- Test Case 4: Get offers for a customer ---")
    offers = offer_service.get_customer_offers("cust123")
    print(f"Offers for cust123: {offers}")

    print("\n--- Test Case 5: Attempt to modify offer for customer with active journey (should fail) ---")
    # Simulate a customer with an active journey
    db.session.add(Customer(customer_id='cust_journey_started', mobile_number='9876543210', pan_number='FGHIJ5678K', dnd_flag=False, segment='C2'))
    db.session.add(Event(event_id=str(uuid.uuid4()), customer_id='cust_journey_started', event_type='LOAN_LOGIN', event_source='LOS', event_timestamp=datetime.now() - timedelta(hours=1)))
    db.session.commit()
    result = offer_service.create_or_update_offer(
        customer_id="cust_journey_started",
        offer_data={
            "offer_type": "Fresh",
            "propensity": "High",
            "end_date": date.today() + timedelta(days=90),
            "channel": "Web"
        }
    )
    print(result)

    print("\n--- Test Case 5b: Attempt to modify offer for customer with completed/rejected journey (should succeed) ---")
    db.session.add(Event(event_id=str(uuid.uuid4()), customer_id='cust_journey_started', event_type='LOAN_REJECTED', event_source='LOS', event_timestamp=datetime.now()))
    db.session.commit()
    result = offer_service.create_or_update_offer(
        customer_id="cust_journey_started",
        offer_data={
            "offer_type": "Fresh",
            "propensity": "High",
            "end_date": date.today() + timedelta(days=90),
            "channel": "Web"
        }
    )
    print(result)


    print("\n--- Test Case 6: Apply attribution logic ---")
    offer_data_for_attribution = {"channel": "MobileApp", "propensity": "Medium"}
    result = offer_service.apply_attribution_logic("cust123", offer_data_for_attribution)
    print(f"Attribution result for cust123: {result}, modified offer_data: {offer_data_for_attribution}")

    offer_data_for_attribution_new_cust = {"channel": "Email", "propensity": "Low"}
    # Simulate a new customer with no existing offers
    db.session.add(Customer(customer_id='cust_new', mobile_number='1112223333', pan_number='KLMNO9876P', dnd_flag=False, segment='C3'))
    db.session.commit()
    result = offer_service.apply_attribution_logic("cust_new", offer_data_for_attribution_new_cust)
    print(f"Attribution result for cust_new: {result}, modified offer_data: {offer_data_for_attribution_new_cust}")


    print("\n--- Test Case 7: Update expired offers batch ---")
    # Simulate an expired offer
    db.session.add(Offer(offer_id=str(uuid.uuid4()), customer_id='cust123', offer_type='Fresh', offer_status='Active', end_date=date.today() - timedelta(days=1)))
    db.session.add(Offer(offer_id=str(uuid.uuid4()), customer_id='cust_journey_started', offer_type='Fresh', offer_status='Active', end_date=date.today() - timedelta(days=1)))
    db.session.commit()
    result = offer_service.update_expired_offers_batch()
    print(result)
    offers_after_expiry = offer_service.get_customer_offers("cust123")
    print(f"Offers for cust123 after expiry batch: {offers_after_expiry}")

    print("\n--- Test Case 8: Get offers for Moengage export ---")
    # Simulate a DND customer
    db.session.add(Customer(customer_id='cust_dnd', mobile_number='4445556666', pan_number='QRSTU1234V', dnd_flag=True, segment='C4'))
    db.session.add(Offer(offer_id=str(uuid.uuid4()), customer_id='cust_dnd', offer_type='Fresh', offer_status='Active', end_date=date.today() + timedelta(days=30)))
    db.session.commit()
    moengage_offers = offer_service.get_offers_for_moengage_export()
    print(f"Offers for Moengage export (should exclude DND): {moengage_offers}")
    # Verify that 'cust_dnd' is not in the export
    dnd_customer_in_export = any(o['customer_id'] == 'cust_dnd' for o in moengage_offers)
    print(f"Is DND customer in export? {dnd_customer_in_export}")