import uuid
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound

# Assuming these are defined in backend/database.py and backend/models.py
from backend.database import db
from backend.models import Customer, Offer, OfferHistory, Event # Event might be needed for journey status check

class IngestionService:
    """
    Service class for handling data ingestion into the CDP.
    This service focuses on processing individual customer and offer records,
    managing their creation, updates, and history. It is designed to be called
    by higher-level services (e.g., deduplication service, batch processors)
    after initial data validation.
    """

    @staticmethod
    def process_customer_and_offer_data(customer_payload: dict, offer_payload: dict, source_system: str) -> (Customer, Offer):
        """
        Processes a single customer and offer record from an ingestion source (e.g., E-aggregator, Offermart).
        This function handles finding/creating customers, processing offers, and recording history.
        It assumes basic payload validation has already occurred.

        Args:
            customer_payload (dict): Dictionary containing customer data (e.g., mobile_number, pan_number, etc.).
            offer_payload (dict): Dictionary containing offer data (e.g., offer_type, propensity, valid_until, etc.).
            source_system (str): The system from which the data originated (e.g., 'E-aggregator', 'Offermart').

        Returns:
            tuple[Customer, Offer]: The created or updated Customer and Offer objects.

        Raises:
            ValueError: If critical data is missing or invalid.
            Exception: For other unexpected database or processing errors.
        """
        try:
            # 1. Find or Create Customer (FR1, FR3, FR4, FR5)
            customer = IngestionService._find_or_create_customer(customer_payload)

            # 2. Process Offer (FR13, FR14, FR16, FR17, FR18, FR19, FR20)
            offer = IngestionService._process_offer(customer.customer_id, offer_payload, source_system)

            db.session.commit()
            return customer, offer

        except IntegrityError as e:
            db.session.rollback()
            # This could happen if a unique constraint is violated during concurrent inserts
            # or if a record already exists that violates a unique constraint.
            # In a real system, this might trigger a retry or more specific handling.
            raise ValueError(f"Database integrity error during ingestion: {e}")
        except Exception as e:
            db.session.rollback()
            raise Exception(f"An unexpected error occurred during ingestion: {e}")

    @staticmethod
    def _find_or_create_customer(customer_data: dict) -> Customer:
        """
        Finds an existing customer based on unique identifiers (Mobile, PAN, Aadhaar, UCID)
        or creates a new one. Updates existing customer attributes if found.
        (Addresses FR1, FR3, FR4, FR5, FR15, FR21)

        Args:
            customer_data (dict): Dictionary containing customer identifiers and attributes.

        Returns:
            Customer: The found or newly created Customer object.
        """
        mobile_number = customer_data.get('mobile_number')
        pan_number = customer_data.get('pan_number')
        aadhaar_number = customer_data.get('aadhaar_number')
        ucid_number = customer_data.get('ucid_number')

        # Try to find customer by any unique identifier (FR3)
        customer = None
        if mobile_number:
            customer = Customer.query.filter_by(mobile_number=mobile_number).first()
        if not customer and pan_number:
            customer = Customer.query.filter_by(pan_number=pan_number).first()
        if not customer and aadhaar_number:
            customer = Customer.query.filter_by(aadhaar_number=aadhaar_number).first()
        if not customer and ucid_number:
            customer = Customer.query.filter_by(ucid_number=ucid_number).first()

        if customer:
            # Update existing customer's attributes if provided (FR15, FR21)
            customer.mobile_number = mobile_number if mobile_number else customer.mobile_number
            customer.pan_number = pan_number if pan_number else customer.pan_number
            customer.aadhaar_number = aadhaar_number if aadhaar_number else customer.aadhaar_number
            customer.ucid_number = ucid_number if ucid_number else customer.ucid_number
            customer.segment = customer_data.get('segment', customer.segment)
            customer.is_dnd = customer_data.get('is_dnd', customer.is_dnd) # FR24
            # Merge or update JSONB attributes
            if 'attributes' in customer_data and isinstance(customer_data['attributes'], dict):
                if customer.attributes is None:
                    customer.attributes = {}
                customer.attributes.update(customer_data['attributes'])
            customer.updated_at = datetime.now(timezone.utc)
            db.session.add(customer)
            return customer
        else:
            # Create new customer
            new_customer = Customer(
                customer_id=uuid.uuid4(),
                mobile_number=mobile_number,
                pan_number=pan_number,
                aadhaar_number=aadhaar_number,
                ucid_number=ucid_number,
                segment=customer_data.get('segment'),
                is_dnd=customer_data.get('is_dnd', False),
                attributes=customer_data.get('attributes', {}),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.session.add(new_customer)
            return new_customer

    @staticmethod
    def _process_offer(customer_id: uuid.UUID, offer_data: dict, source_system: str) -> Offer:
        """
        Processes an offer for a given customer. Handles offer creation, updates,
        status changes, and specific logic for 'Enrich' offers (FR18).
        Prevents modification of offers with an active loan application journey (FR13).
        (Addresses FR13, FR14, FR16, FR17, FR18, FR19, FR20)

        Args:
            customer_id (uuid.UUID): The ID of the customer associated with the offer.
            offer_data (dict): Dictionary containing offer details.
            source_system (str): The system from which the data originated.

        Returns:
            Offer: The created or updated Offer object.

        Raises:
            ValueError: If 'source_offer_id' is missing.
        """
        source_offer_id = offer_data.get('source_offer_id')
        offer_type = offer_data.get('offer_type') # FR17
        loan_application_number = offer_data.get('loan_application_number')
        new_offer_status = offer_data.get('offer_status', 'Active') # Default to Active (FR16)
        valid_until_str = offer_data.get('valid_until')
        valid_until = datetime.fromisoformat(valid_until_str) if valid_until_str else None
        propensity = offer_data.get('propensity') # FR19
        channel = offer_data.get('channel')

        if not source_offer_id:
            raise ValueError("Offer payload must contain 'source_offer_id'.")

        # Try to find an existing offer for this customer based on source_offer_id and source_system
        existing_offer = Offer.query.filter_by(
            customer_id=customer_id,
            source_offer_id=source_offer_id,
            source_system=source_system
        ).first()

        # Check for any active journey offer for this customer (FR13)
        active_journey_offer = None
        if loan_application_number:
            # An offer is considered part of an active journey if it has a LAN and is not 'Expired'
            active_journey_offer = Offer.query.filter_by(
                customer_id=customer_id,
                loan_application_number=loan_application_number
            ).filter(Offer.offer_status != 'Expired').first()

        old_status = None
        offer_to_return = None

        if existing_offer:
            old_status = existing_offer.offer_status

            # FR13: Prevent modification of customer offers with an active loan application journey
            # If there's an active journey offer for this customer, and the incoming offer is *not*
            # an update to that specific active journey offer (i.e., different source_offer_id or LAN),
            # then we should prevent processing this new offer.
            if active_journey_offer and (active_journey_offer.offer_id != existing_offer.offer_id or \
                                         (loan_application_number and active_journey_offer.loan_application_number != loan_application_number)):
                print(f"Skipping new offer (source_offer_id: {source_offer_id}) for customer {customer_id} due to active loan journey for offer {active_journey_offer.offer_id}.")
                return active_journey_offer # Return the active journey offer, don't process the new one.

            # FR18: Handle 'Enrich' offers
            if offer_type == 'Enrich':
                # If journey not started for the existing offer (no LAN or LAN is not active/expired)
                if not existing_offer.loan_application_number or existing_offer.offer_status == 'Expired':
                    # Mark previous offer as Duplicate and Inactive
                    existing_offer.is_duplicate = True
                    existing_offer.offer_status = 'Inactive' # Superseded by the new 'Enrich' offer
                    existing_offer.updated_at = datetime.now(timezone.utc)
                    db.session.add(existing_offer)
                    # The new 'Enrich' offer will be created below as a new record.
                    # This implies an 'Enrich' offer is a *new* offer that supersedes an old one.
                    existing_offer = None # Force creation of a new offer for 'Enrich' type
                else:
                    # If journey started for the existing offer, do not flow 'Enrich' offer to CDP (FR18)
                    print(f"Skipping 'Enrich' offer for customer {customer_id} as journey already started for offer {existing_offer.offer_id}")
                    return existing_offer # Do not process this new 'Enrich' offer

            # If existing_offer is still valid (not marked for replacement by 'Enrich' logic)
            if existing_offer:
                # FR14: Allow replenishment of offers for non-journey started customers after their existing offers expire.
                # This is implicitly handled: if an existing offer is expired, a new one can be created or the existing one updated.
                # The logic below will update the existing offer.

                # Update existing offer (FR16, FR17, FR19)
                existing_offer.offer_type = offer_type if offer_type else existing_offer.offer_type
                existing_offer.offer_status = new_offer_status
                existing_offer.propensity = propensity if propensity else existing_offer.propensity
                existing_offer.loan_application_number = loan_application_number if loan_application_number else existing_offer.loan_application_number
                existing_offer.valid_until = valid_until if valid_until else existing_offer.valid_until
                existing_offer.channel = channel if channel else existing_offer.channel
                existing_offer.updated_at = datetime.now(timezone.utc)
                db.session.add(existing_offer)
                offer_to_return = existing_offer
        else:
            # If no existing offer found by source_offer_id, create a new one.
            # This also covers the case where an 'Enrich' offer caused the existing_offer to be set to None.
            new_offer = Offer(
                offer_id=uuid.uuid4(),
                customer_id=customer_id,
                source_offer_id=source_offer_id,
                offer_type=offer_type, # FR17
                offer_status=new_offer_status, # FR16
                propensity=propensity, # FR19
                loan_application_number=loan_application_number,
                valid_until=valid_until,
                source_system=source_system,
                channel=channel,
                is_duplicate=False, # This will be updated by deduplication service if needed
                original_offer_id=None, # This will be updated by deduplication service if needed
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.session.add(new_offer)
            offer_to_return = new_offer

        # FR20: Maintain Offer history for the past 6 months.
        # Record offer status change if it occurred
        if old_status != new_offer_status and offer_to_return:
            IngestionService._record_offer_history(
                offer_to_return.offer_id,
                old_status,
                new_offer_status,
                f"Offer status changed by {source_system} ingestion."
            )
        return offer_to_return

    @staticmethod
    def _record_offer_history(offer_id: uuid.UUID, old_status: str, new_status: str, reason: str):
        """
        Records a change in offer status to the offer_history table (FR20).
        """
        history_entry = OfferHistory(
            history_id=uuid.uuid4(),
            offer_id=offer_id,
            status_change_date=datetime.now(timezone.utc),
            old_status=old_status,
            new_status=new_status,
            change_reason=reason
        )
        db.session.add(history_entry)

    @staticmethod
    def mark_offer_expired_by_lan(loan_application_number: str, customer_id: uuid.UUID = None):
        """
        FR36: Marks offers as expired if the loan application number (LAN) validity is over
        for journey-started customers. This function is intended to be called by an external
        process (e.g., an LOS event handler or a scheduled job).

        Args:
            loan_application_number (str): The LAN whose associated offers should be expired.
            customer_id (uuid.UUID, optional): Optional customer_id to narrow down the search.
        """
        query = Offer.query.filter_by(loan_application_number=loan_application_number)
        if customer_id:
            query = query.filter_by(customer_id=customer_id)

        # Only expire offers that are not already expired
        offers_to_expire = query.filter(Offer.offer_status != 'Expired').all()

        if not offers_to_expire:
            print(f"No active offers found for LAN: {loan_application_number} to expire.")
            return

        for offer in offers_to_expire:
            old_status = offer.offer_status
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.now(timezone.utc)
            db.session.add(offer)
            IngestionService._record_offer_history(
                offer.offer_id,
                old_status,
                'Expired',
                f"Offer expired due to LAN {loan_application_number} validity end (FR36)."
            )
        db.session.commit() # Commit changes for this specific operation
        print(f"Successfully marked {len(offers_to_expire)} offers as 'Expired' for LAN: {loan_application_number}.")