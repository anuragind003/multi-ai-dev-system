import uuid
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
import logging

# Assuming db and models are accessible from a central point like backend.src.models
# In a Flask app, db is typically initialized in __init__.py and models import it.
# For this service file, we'll assume we can import them directly.
try:
    from backend.src.models import db, Customer, Offer, OfferHistory, Event
except ImportError:
    # This block is for robustness during development/testing if models aren't fully set up yet.
    # In a production Flask app, backend.src.models should always be correctly imported.
    logging.error("Could not import db, Customer, Offer, OfferHistory, Event from backend.src.models. "
                  "Please ensure backend.src.models is correctly defined and accessible.")
    # Define dummy classes for local testing/linting without full Flask context
    class MockDB:
        def session(self):
            return self
        def add(self, obj): pass
        def commit(self): pass
        def rollback(self): pass
        def refresh(self, obj): pass
        def query(self, model): return self
        def get(self, id): return None
        def filter_by(self, **kwargs): return self
        def first(self): return None
        def all(self): return []
        def delete(self, obj): pass

    db = MockDB()

    class Customer:
        def __init__(self, customer_id=None, mobile_number=None, pan_number=None, aadhaar_number=None, ucid_number=None, is_dnd=False, segment=None, attributes=None):
            self.customer_id = customer_id or uuid.uuid4()
            self.mobile_number = mobile_number
            self.pan_number = pan_number
            self.aadhaar_number = aadhaar_number
            self.ucid_number = ucid_number
            self.is_dnd = is_dnd
            self.segment = segment
            self.attributes = attributes if attributes is not None else {}
            self.created_at = datetime.now(timezone.utc)
            self.updated_at = datetime.now(timezone.utc)

    class Offer:
        def __init__(self, offer_id=None, customer_id=None, source_offer_id=None, offer_type=None, offer_status=None, propensity=None, loan_application_number=None, valid_until=None, source_system=None, channel=None, is_duplicate=False, original_offer_id=None):
            self.offer_id = offer_id or uuid.uuid4()
            self.customer_id = customer_id
            self.source_offer_id = source_offer_id
            self.offer_type = offer_type
            self.offer_status = offer_status
            self.propensity = propensity
            self.loan_application_number = loan_application_number
            self.valid_until = valid_until
            self.source_system = source_system
            self.channel = channel
            self.is_duplicate = is_duplicate
            self.original_offer_id = original_offer_id
            self.created_at = datetime.now(timezone.utc)
            self.updated_at = datetime.now(timezone.utc)

    class OfferHistory:
        def __init__(self, history_id=None, offer_id=None, old_status=None, new_status=None, change_reason=None):
            self.history_id = history_id or uuid.uuid4()
            self.offer_id = offer_id
            self.status_change_date = datetime.now(timezone.utc)
            self.old_status = old_status
            self.new_status = new_status
            self.change_reason = change_reason

    class Event:
        def __init__(self, event_id=None, customer_id=None, offer_id=None, event_type=None, source_system=None, event_details=None):
            self.event_id = event_id or uuid.uuid4()
            self.customer_id = customer_id
            self.offer_id = offer_id
            self.event_type = event_type
            self.event_timestamp = datetime.now(timezone.utc)
            self.source_system = source_system
            self.event_details = event_details if event_details is not None else {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OfferService:
    def __init__(self, db_session):
        self.db = db_session

    def _record_offer_history(self, offer_id: uuid.UUID, old_status: str | None, new_status: str, reason: str):
        """Records a change in offer status to the offer_history table."""
        try:
            history_entry = OfferHistory(
                offer_id=offer_id,
                old_status=old_status,
                new_status=new_status,
                change_reason=reason
            )
            self.db.session.add(history_entry)
            self.db.session.commit()
            logger.info(f"Offer history recorded for offer {offer_id}: {old_status} -> {new_status}")
        except SQLAlchemyError as e:
            self.db.session.rollback()
            logger.error(f"Error recording offer history for offer {offer_id}: {e}")
            raise

    def get_offer_by_id(self, offer_id: uuid.UUID) -> Offer | None:
        """
        Retrieves details of a specific offer.

        Functional Requirements Addressed:
        - FR16: The CDP system shall maintain flags for Offer statuses: Active, Inactive, and Expired.
        - FR17: The CDP system shall maintain flags for Offer types: ‘Fresh’, ‘Enrich’, ‘New-old’, ‘New-new’.
        - FR19: The CDP system shall maintain analytics-defined flags for Propensity.
        """
        try:
            offer = self.db.session.query(Offer).get(offer_id)
            return offer
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving offer {offer_id}: {e}")
            return None

    def _is_customer_in_active_journey(self, customer_id: uuid.UUID) -> bool:
        """
        Checks if a customer has an active loan application journey.
        (FR13: Prevent modification of customer offers with an active loan application journey)
        This is a simplified check. A more robust check would involve looking at specific
        event types (e.g., 'JOURNEY_LOGIN', 'BUREAU_CHECK') and their completion status,
        or checking the `loan_application_number` status in the `offers` table.
        """
        # Check for any active offers with a loan_application_number that is not expired/rejected
        # Assuming 'Active' status for an offer with LAN means journey is ongoing.
        active_journey_offers = self.db.session.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.loan_application_number.isnot(None),
            Offer.offer_status == 'Active'
        ).first()

        if active_journey_offers:
            logger.info(f"Customer {customer_id} has an active loan application journey.")
            return True

        # A more robust check would involve querying the 'events' table for specific journey stages
        # without corresponding completion/rejection events. For MVP, the above is sufficient.
        return False

    def _apply_deduplication_logic(self, customer: Customer, new_offer_data: dict) -> tuple[bool, uuid.UUID | None]:
        """
        Applies simplified deduplication logic for offers.
        (FR1, FR3, FR4, FR5, FR6, FR18)
        This is a placeholder for a more complex deduplication service.
        For now, it checks for existing active offers for the same customer.
        If an 'Enrich' offer comes in and no journey started, it marks previous as duplicate.
        Returns (is_duplicate, original_offer_id_if_duplicate).
        """
        is_duplicate = False
        original_offer_id = None
        new_offer_type = new_offer_data.get('offer_type')

        # Find existing active offers for the customer
        existing_active_offers = self.db.session.query(Offer).filter(
            Offer.customer_id == customer.customer_id,
            Offer.offer_status == 'Active',
            Offer.is_duplicate == False
        ).all()

        if not existing_active_offers:
            return False, None

        # Simplified 'Enrich' offer logic (FR18)
        if new_offer_type == 'Enrich':
            for existing_offer in existing_active_offers:
                # Check if journey started for this existing offer (simplified check)
                if existing_offer.loan_application_number and \
                   self.db.session.query(Event).filter(
                       Event.offer_id == existing_offer.offer_id,
                       Event.event_type.in_(['JOURNEY_LOGIN', 'EKYC_ACHIEVED', 'DISBURSEMENT'])
                   ).first():
                    logger.warning(f"Rejecting 'Enrich' offer for customer {customer.customer_id} "
                                   f"as existing offer {existing_offer.offer_id} has an active journey.")
                    # Indicate that the new 'Enrich' offer should not be processed
                    return True, existing_offer.offer_id

                else:
                    # Journey not started for existing offer, mark it as duplicate/inactive
                    old_status = existing_offer.offer_status
                    existing_offer.offer_status = 'Inactive' # Or 'Duplicate' if we add that status
                    existing_offer.is_duplicate = True
                    existing_offer.updated_at = datetime.now(timezone.utc)
                    self.db.session.add(existing_offer)
                    self._record_offer_history(existing_offer.offer_id, old_status, existing_offer.offer_status,
                                               "Marked duplicate by new 'Enrich' offer")
                    logger.info(f"Marked existing offer {existing_offer.offer_id} as duplicate/inactive "
                                f"due to new 'Enrich' offer for customer {customer.customer_id}.")
                    is_duplicate = False # The new offer is NOT a duplicate, it replaces the old one
                    original_offer_id = existing_offer.offer_id # New offer replaces this one
                    break # Assuming one 'Enrich' offer replaces one previous active offer

        # General deduplication: If there's any active offer and the new one isn't meant to replace/enrich,
        # it might be considered a duplicate. This is a very basic interpretation.
        if not is_duplicate and existing_active_offers and new_offer_type not in ['Enrich', 'Fresh']:
            is_duplicate = True
            original_offer_id = existing_active_offers[0].offer_id # Point to the first active one

        return is_duplicate, original_offer_id

    def create_or_update_offer(self, customer_data: dict, offer_data: dict) -> tuple[Offer | None, str]:
        """
        Processes incoming offer data, creating or updating offers and customers.
        Handles deduplication, offer status, and history.

        Functional Requirements Addressed:
        - FR2: The CDP system shall validate basic column-level data. (Basic validation here)
        - FR7: The CDP system shall update old offers in Analytics Offermart with new real-time data from CDP.
        - FR13: Prevent modification of customer offers with an active loan application journey.
        - FR14: Allow replenishment of offers for non-journey started customers after their existing offers expire.
        - FR16: Maintain flags for Offer statuses: Active, Inactive, Expired.
        - FR17: Maintain flags for Offer types: ‘Fresh’, ‘Enrich’, ‘New-old’, ‘New-new’.
        - FR18: Handle 'Enrich' offers.
        - FR19: Maintain analytics-defined flags for Propensity.
        - FR20: Maintain Offer history for the past 6 months.
        - FR22: Apply attribution logic. (Placeholder)
        """
        try:
            # 1. Basic Data Validation (FR2, NFR8)
            required_customer_fields = ['mobile_number']
            if not all(customer_data.get(field) for field in required_customer_fields):
                return None, "Missing required customer data (e.g., mobile_number)."

            required_offer_fields = ['source_offer_id', 'offer_type', 'offer_status', 'valid_until', 'source_system']
            if not all(offer_data.get(field) for field in required_offer_fields):
                return None, "Missing required offer data."

            # Convert valid_until to datetime object
            try:
                offer_data['valid_until'] = datetime.fromisoformat(offer_data['valid_until']).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                return None, "Invalid 'valid_until' format. Must be ISO format."

            # 2. Find or Create Customer
            customer = self.db.session.query(Customer).filter(
                (Customer.mobile_number == customer_data['mobile_number']) |
                (Customer.pan_number == customer_data.get('pan_number')) |
                (Customer.aadhaar_number == customer_data.get('aadhaar_number')) |
                (Customer.ucid_number == customer_data.get('ucid_number'))
            ).first()

            if not customer:
                customer = Customer(
                    customer_id=uuid.uuid4(),
                    mobile_number=customer_data.get('mobile_number'),
                    pan_number=customer_data.get('pan_number'),
                    aadhaar_number=customer_data.get('aadhaar_number'),
                    ucid_number=customer_data.get('ucid_number'),
                    segment=customer_data.get('segment'),
                    attributes=customer_data.get('attributes', {})
                )
                self.db.session.add(customer)
                self.db.session.flush()
                logger.info(f"Created new customer: {customer.customer_id}")
            else:
                # Update customer attributes if necessary (FR7 implies updating customer data too)
                customer.pan_number = customer_data.get('pan_number') or customer.pan_number
                customer.aadhaar_number = customer_data.get('aadhaar_number') or customer.aadhaar_number
                customer.ucid_number = customer_data.get('ucid_number') or customer.ucid_number
                customer.segment = customer_data.get('segment') or customer.segment
                if customer_data.get('attributes'):
                    customer.attributes.update(customer_data['attributes'])
                customer.updated_at = datetime.now(timezone.utc)
                logger.info(f"Updated existing customer: {customer.customer_id}")

            # 3. Check for Active Loan Journey (FR13)
            if self._is_customer_in_active_journey(customer.customer_id):
                logger.warning(f"Customer {customer.customer_id} has an active loan journey. "
                               f"New offer from {offer_data.get('source_system')} for source_offer_id "
                               f"{offer_data.get('source_offer_id')} is rejected.")
                self.db.session.rollback()
                return None, "Customer has an active loan application journey. Offer cannot be processed."

            # 4. Apply Deduplication Logic (FR1, FR3, FR4, FR5, FR6, FR18)
            is_duplicate_flag, original_offer_id_ref = self._apply_deduplication_logic(customer, offer_data)

            # 5. Create or Update Offer
            existing_offer = self.db.session.query(Offer).filter_by(
                source_offer_id=offer_data['source_offer_id'],
                source_system=offer_data['source_system']
            ).first()

            if existing_offer:
                # Update existing offer (FR7)
                old_status = existing_offer.offer_status
                existing_offer.customer_id = customer.customer_id
                existing_offer.offer_type = offer_data.get('offer_type', existing_offer.offer_type)
                existing_offer.offer_status = offer_data.get('offer_status', existing_offer.offer_status)
                existing_offer.propensity = offer_data.get('propensity', existing_offer.propensity)
                existing_offer.loan_application_number = offer_data.get('loan_application_number', existing_offer.loan_application_number)
                existing_offer.valid_until = offer_data.get('valid_until', existing_offer.valid_until)
                existing_offer.channel = offer_data.get('channel', existing_offer.channel)
                existing_offer.is_duplicate = is_duplicate_flag
                existing_offer.original_offer_id = original_offer_id_ref
                existing_offer.updated_at = datetime.now(timezone.utc)
                self.db.session.add(existing_offer)
                logger.info(f"Updated existing offer: {existing_offer.offer_id}")
                if old_status != existing_offer.offer_status:
                    self._record_offer_history(existing_offer.offer_id, old_status, existing_offer.offer_status, "Offer data updated")
                created_offer = existing_offer
            else:
                if is_duplicate_flag:
                    logger.info(f"Incoming offer from {offer_data.get('source_system')} for source_offer_id "
                                f"{offer_data.get('source_offer_id')} is a duplicate and will not be created.")
                    self.db.session.rollback()
                    return None, "Offer identified as a duplicate and not created."

                # Create new offer
                new_offer = Offer(
                    offer_id=uuid.uuid4(),
                    customer_id=customer.customer_id,
                    source_offer_id=offer_data['source_offer_id'],
                    offer_type=offer_data['offer_type'],
                    offer_status=offer_data['offer_status'],
                    propensity=offer_data.get('propensity'),
                    loan_application_number=offer_data.get('loan_application_number'),
                    valid_until=offer_data['valid_until'],
                    source_system=offer_data['source_system'],
                    channel=offer_data.get('channel'),
                    is_duplicate=is_duplicate_flag,
                    original_offer_id=original_offer_id_ref
                )
                self.db.session.add(new_offer)
                self.db.session.flush()
                self._record_offer_history(new_offer.offer_id, None, new_offer.offer_status, "New offer created")
                logger.info(f"Created new offer: {new_offer.offer_id}")
                created_offer = new_offer

            # 6. Apply Attribution Logic (FR22) - Placeholder
            # This is a complex step. It would involve determining which offer "prevails"
            # if a customer has multiple active offers from different channels/sources.
            # This might update the 'channel' or 'offer_status' of other offers.
            # For MVP, we'll assume the latest valid offer is the primary one, or this logic
            # is applied during campaign file generation.

            self.db.session.commit()
            return created_offer, "Offer processed successfully."

        except SQLAlchemyError as e:
            self.db.session.rollback()
            logger.error(f"Database error during offer processing: {e}")
            return None, f"Database error: {e}"
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Unexpected error during offer processing: {e}")
            return None, f"Unexpected error: {e}"

    def update_offer_status(self, offer_id: uuid.UUID, new_status: str, reason: str = "Manual update") -> tuple[Offer | None, str]:
        """
        Updates the status of an existing offer and records the change in history.
        (FR16: Maintain flags for Offer statuses: Active, Inactive, and Expired)
        """
        try:
            offer = self.db.session.query(Offer).get(offer_id)
            if not offer:
                return None, "Offer not found."

            old_status = offer.offer_status
            if old_status == new_status:
                return offer, "Offer status is already the same."

            offer.offer_status = new_status
            offer.updated_at = datetime.now(timezone.utc)
            self.db.session.add(offer)
            self._record_offer_history(offer.offer_id, old_status, new_status, reason)
            self.db.session.commit()
            logger.info(f"Offer {offer_id} status updated from {old_status} to {new_status}.")
            return offer, "Offer status updated successfully."
        except SQLAlchemyError as e:
            self.db.session.rollback()
            logger.error(f"Error updating offer {offer_id} status: {e}")
            return None, f"Database error: {e}"
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Unexpected error updating offer {offer_id} status: {e}")
            return None, f"Unexpected error: {e}"

    def mark_offers_expired_by_lan_validity(self, loan_application_number: str) -> tuple[int, str]:
        """
        Marks offers as expired if their associated Loan Application Number (LAN) validity is over.
        (FR36: Mark offers as expired if the loan application number (LAN) validity is over for journey-started customers.)
        This function assumes an external trigger (e.g., LOS event) indicates LAN validity is over.
        It will mark all offers associated with this LAN as 'Expired'.
        """
        try:
            offers_to_expire = self.db.session.query(Offer).filter(
                Offer.loan_application_number == loan_application_number,
                Offer.offer_status != 'Expired'
            ).all()

            if not offers_to_expire:
                return 0, f"No active offers found for LAN: {loan_application_number} to expire."

            updated_count = 0
            for offer in offers_to_expire:
                old_status = offer.offer_status
                offer.offer_status = 'Expired'
                offer.updated_at = datetime.now(timezone.utc)
                self.db.session.add(offer)
                self._record_offer_history(offer.offer_id, old_status, 'Expired',
                                           f"LAN {loan_application_number} validity expired (FR36)")
                updated_count += 1

            self.db.session.commit()
            logger.info(f"Marked {updated_count} offers as 'Expired' for LAN: {loan_application_number}.")
            return updated_count, "Offers marked as expired successfully."
        except SQLAlchemyError as e:
            self.db.session.rollback()
            logger.error(f"Database error marking offers expired for LAN {loan_application_number}: {e}")
            return 0, f"Database error: {e}"
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Unexpected error marking offers expired for LAN {loan_application_number}: {e}")
            return 0, f"Unexpected error: {e}"

    def get_offer_history(self, offer_id: uuid.UUID) -> list[OfferHistory]:
        """
        Retrieves the history of status changes for a specific offer.
        (FR20: Maintain Offer history for the past 6 months.)
        (NFR10: Offer history shall be maintained for 6 months.)
        This function retrieves all history, but data retention policies (6 months)
        would be handled by a separate cleanup job.
        """
        try:
            history = self.db.session.query(OfferHistory).filter_by(offer_id=offer_id).order_by(
                OfferHistory.status_change_date.desc()
            ).all()
            return history
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving offer history for offer {offer_id}: {e}")
            return []