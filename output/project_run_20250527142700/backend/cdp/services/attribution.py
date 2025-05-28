import logging
from datetime import datetime, timezone
from sqlalchemy import desc, or_
from sqlalchemy.orm import joinedload

# Assuming db and models are accessible from a central point
# In a Flask app, db is typically initialized in __init__.py and models import it.
# For this service file, we'll assume we can import them directly.
try:
    from backend.models import db, Customer, Offer, OfferHistory, Event
except ImportError:
    # This block is for robustness during development/testing if models aren't fully set up yet.
    # In a production Flask app, backend.models should always be correctly imported.
    logging.error("Could not import db, Customer, Offer, OfferHistory, Event from backend.models. "
                  "Please ensure backend.models is correctly defined and accessible.")
    # Define dummy classes for local testing/linting without full Flask context
    import uuid
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy import create_engine, Column, String, Boolean, DateTime, ForeignKey, JSONB
    from sqlalchemy.orm import sessionmaker

    Base = declarative_base()

    class MockCustomer(Base):
        __tablename__ = 'customers'
        customer_id = Column(String, primary_key=True)
        mobile_number = Column(String)
        pan_number = Column(String)
        # Add other necessary fields for attribution logic if needed

    class MockOffer(Base):
        __tablename__ = 'offers'
        offer_id = Column(String, primary_key=True)
        customer_id = Column(String, ForeignKey('customers.customer_id'))
        source_offer_id = Column(String)
        offer_type = Column(String)
        offer_status = Column(String)
        propensity = Column(String)
        loan_application_number = Column(String)
        valid_until = Column(DateTime(timezone=True))
        source_system = Column(String)
        channel = Column(String)
        is_duplicate = Column(Boolean)
        original_offer_id = Column(String, ForeignKey('offers.offer_id'))
        created_at = Column(DateTime(timezone=True))
        updated_at = Column(DateTime(timezone=True))

    class MockOfferHistory(Base):
        __tablename__ = 'offer_history'
        history_id = Column(String, primary_key=True)
        offer_id = Column(String, ForeignKey('offers.offer_id'))
        status_change_date = Column(DateTime(timezone=True))
        old_status = Column(String)
        new_status = Column(String)
        change_reason = Column(String)

    class MockEvent(Base):
        __tablename__ = 'events'
        event_id = Column(String, primary_key=True)
        customer_id = Column(String, ForeignKey('customers.customer_id'))
        offer_id = Column(String, ForeignKey('offers.offer_id'))
        event_type = Column(String)
        event_timestamp = Column(DateTime(timezone=True))
        source_system = Column(String)
        event_details = Column(JSONB)
        loan_application_number = Column(String) # Added for LAN-based event filtering

    # Setup a dummy in-memory SQLite for mocks to allow basic SQLAlchemy operations
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    class MockDB:
        def __init__(self):
            self._session = None
        def session(self):
            if not self._session:
                self._session = Session()
            return self._session
        def commit(self):
            if self._session: self._session.commit()
        def rollback(self):
            if self._session: self._session.rollback()
        def add(self, obj):
            self.session().add(obj)
        def add_all(self, objs):
            self.session().add_all(objs)
        def query(self, model):
            return self.session().query(model)
        def close(self):
            if self._session:
                self._session.close()
                self._session = None

    db = MockDB()
    Customer = MockCustomer
    Offer = MockOffer
    OfferHistory = MockOfferHistory
    Event = MockEvent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AttributionService:
    """
    Service responsible for applying attribution logic to customer offers.

    Functional Requirements Addressed:
    - FR22: The CDP system shall apply attribution logic to determine which offer/channel prevails
            when a customer has multiple offers or comes through different channels.
    - FR13: The CDP system shall prevent modification of customer offers with an active loan
            application journey until the application is expired or rejected.
    - FR16: The CDP system shall maintain flags for Offer statuses: Active, Inactive, and Expired
            based on defined business logic.
    - FR18: The CDP system shall handle 'Enrich' offers: if journey not started, flow to CDP and
            mark previous offer as Duplicate; if journey started, do not flow to CDP.
    - FR20: The CDP system shall maintain Offer history for the past 6 months.
    - FR36: The CDP system shall mark offers as expired if the loan application number (LAN)
            validity is over for journey-started customers.
    """

    def __init__(self, db_session_factory=None):
        """
        Initializes the AttributionService.
        Args:
            db_session_factory: A callable that returns a SQLAlchemy session object.
                                If None, uses the global 'db.session' from backend.models.
        """
        self._db_session_factory = db_session_factory if db_session_factory else db.session

    def _get_offer_priority_score(self, offer: Offer) -> int:
        """
        Assigns a priority score to an offer based on defined business rules.
        Higher score means higher priority.
        """
        score = 0

        # Rule 1: Offer Type Priority (Hypothetical order based on common sense for offers)
        # 'Fresh' > 'New-new' > 'Enrich' > 'New-old'
        # FR17: 'Fresh', 'Enrich', 'New-old', 'New-new'
        if offer.offer_type == 'Fresh':
            score += 400
        elif offer.offer_type == 'New-new':
            score += 300
        elif offer.offer_type == 'Enrich':
            score += 200
        elif offer.offer_type == 'New-old':
            score += 100

        # Rule 2: Propensity (Higher is better)
        # FR19: "maintain analytics-defined flags for Propensity"
        try:
            # Assuming propensity is a string that can be converted to an integer
            propensity_val = int(offer.propensity)
            score += propensity_val * 10 # Scale propensity impact
        except (ValueError, TypeError):
            pass # Propensity might be non-numeric or missing

        # Rule 3: Channel/Source System Priority (Hypothetical)
        # E-aggregator might be preferred for real-time leads
        if offer.source_system == 'E-aggregator':
            score += 50
        elif offer.source_system == 'Offermart':
            score += 20

        return score

    def _is_loan_journey_active(self, session, loan_application_number: str) -> bool:
        """
        Checks if a loan application journey is currently active.
        A journey is considered active if there's a LAN and no 'end' events (rejected, expired, disbursed).
        """
        if not loan_application_number:
            return False

        # Check for events that signify the end of a loan journey
        journey_end_event = session.query(Event).filter(
            Event.loan_application_number == loan_application_number,
            Event.event_type.in_(['LOAN_REJECTED', 'LOAN_EXPIRED', 'LOAN_DISBURSED'])
        ).first()

        return not bool(journey_end_event)

    def apply_attribution_for_customer(self, customer_id: str):
        """
        Applies attribution logic for a given customer to determine the prevailing offer.
        Marks other offers as 'Inactive' or 'Superseded' and updates history.
        """
        logging.info(f"Applying attribution for customer_id: {customer_id}")
        session = self._db_session_factory() # Get a new session for this operation

        try:
            # Fetch all non-expired offers for the customer
            # We need to consider 'Active' and 'Inactive' offers that might be reactivated
            offers = session.query(Offer).filter(
                Offer.customer_id == customer_id,
                Offer.offer_status != 'Expired'
            ).order_by(desc(Offer.created_at)).all() # Order by recency as a default tie-breaker

            if not offers:
                logging.info(f"No active/non-expired offers found for customer_id: {customer_id}. No attribution needed.")
                return

            # Separate offers based on active loan journey status (FR13)
            offers_with_active_journey = []
            offers_without_active_journey = []

            for offer in offers:
                if offer.loan_application_number and self._is_loan_journey_active(session, offer.loan_application_number):
                    offers_with_active_journey.append(offer)
                else:
                    offers_without_active_journey.append(offer)

            prevailing_offer = None
            offers_to_deactivate = []

            if offers_with_active_journey:
                # If there are offers with active journeys, the one with the highest score prevails.
                # If multiple, pick the one with highest score, then most recent.
                offers_with_active_journey.sort(key=lambda o: (self._get_offer_priority_score(o), o.created_at), reverse=True)
                prevailing_offer = offers_with_active_journey[0]
                logging.info(f"Prevailing offer identified (active journey): {prevailing_offer.offer_id}")

                # All other offers (both active journey and non-active journey) should be marked inactive
                # if they are not the prevailing one.
                for offer in offers:
                    if offer.offer_id != prevailing_offer.offer_id:
                        offers_to_deactivate.append(offer)

            else:
                # No offers with active loan journeys. Apply attribution on all available offers.
                # Sort offers by priority score, then by creation date (most recent first)
                offers_without_active_journey.sort(key=lambda o: (self._get_offer_priority_score(o), o.created_at), reverse=True)

                if offers_without_active_journey:
                    prevailing_offer = offers_without_active_journey[0]
                    logging.info(f"Prevailing offer identified (no active journey): {prevailing_offer.offer_id}")

                    # Mark all other offers as 'Inactive' and 'is_duplicate=True'
                    for offer in offers_without_active_journey[1:]:
                        offers_to_deactivate.append(offer)
                else:
                    logging.info(f"No offers to attribute for customer_id: {customer_id} after filtering.")
                    return # No offers to process

            # Update statuses based on identified prevailing offer
            if prevailing_offer:
                if prevailing_offer.offer_status != 'Active':
                    self._update_offer_status(session, prevailing_offer, 'Active', 'Attribution: Identified as prevailing offer.')
                # Ensure prevailing offer is not marked as duplicate of itself
                prevailing_offer.is_duplicate = False
                prevailing_offer.original_offer_id = None
                session.add(prevailing_offer)

            for offer_to_deactivate in offers_to_deactivate:
                if offer_to_deactivate.offer_status == 'Active': # Only change if currently active
                    self._update_offer_status(session, offer_to_deactivate, 'Inactive', 'Attribution: Superseded by a higher priority offer.')
                    offer_to_deactivate.is_duplicate = True
                    offer_to_deactivate.original_offer_id = prevailing_offer.offer_id if prevailing_offer else None
                    session.add(offer_to_deactivate) # Mark for update
                elif offer_to_deactivate.offer_status == 'Inactive':
                    # If already inactive, just ensure duplicate flags are set correctly
                    if not offer_to_deactivate.is_duplicate or offer_to_deactivate.original_offer_id != (prevailing_offer.offer_id if prevailing_offer else None):
                        offer_to_deactivate.is_duplicate = True
                        offer_to_deactivate.original_offer_id = prevailing_offer.offer_id if prevailing_offer else None
                        session.add(offer_to_deactivate)


            session.commit()
            logging.info(f"Attribution completed for customer_id: {customer_id}. Prevailing offer: {prevailing_offer.offer_id if prevailing_offer else 'None'}")

        except Exception as e:
            session.rollback()
            logging.error(f"Error applying attribution for customer_id {customer_id}: {e}", exc_info=True)
            raise # Re-raise to indicate failure

        finally:
            session.close() # Ensure session is closed

    def _update_offer_status(self, session, offer: Offer, new_status: str, reason: str):
        """
        Helper to update offer status and record history.
        """
        old_status = offer.offer_status
        if old_status != new_status:
            offer.offer_status = new_status
            offer.updated_at = datetime.now(timezone.utc)
            session.add(offer) # Mark for update

            history_entry = OfferHistory(
                offer_id=offer.offer_id,
                old_status=old_status,
                new_status=new_status,
                change_reason=reason
            )
            session.add(history_entry)
            logging.info(f"Offer {offer.offer_id} status changed from {old_status} to {new_status}. Reason: {reason}")

    def handle_new_offer_ingestion(self, new_offer_id: str):
        """
        Trigger attribution logic when a new offer is ingested.
        This is a wrapper to ensure the customer's offers are re-evaluated.
        """
        session = self._db_session_factory()
        try:
            new_offer = session.query(Offer).filter_by(offer_id=new_offer_id).first()
            if not new_offer:
                logging.warning(f"New offer with ID {new_offer_id} not found for attribution.")
                return

            customer_id = new_offer.customer_id
            logging.info(f"New offer {new_offer_id} ingested for customer {customer_id}. Triggering attribution.")
            session.close() # Close current session before calling main attribution logic
            self.apply_attribution_for_customer(customer_id)

        except Exception as e:
            logging.error(f"Error handling new offer ingestion for {new_offer_id}: {e}", exc_info=True)
            raise # Re-raise to indicate failure
        finally:
            # If session was opened here, ensure it's closed.
            # In this design, apply_attribution_for_customer handles its own transaction.
            pass

    def check_and_expire_offers_with_invalid_lan(self):
        """
        Periodically checks offers with loan application numbers and marks them 'Expired'
        if the associated journey is no longer active (e.g., rejected, expired, disbursed).
        This addresses FR36. This would typically be a scheduled task.
        """
        logging.info("Starting check for expiring offers with invalid LANs.")
        session = self._db_session_factory()
        try:
            # Find offers that have a loan_application_number and are currently 'Active'
            # or 'Inactive' but not 'Expired' yet.
            offers_to_check = session.query(Offer).filter(
                Offer.loan_application_number.isnot(None),
                Offer.offer_status.in_(['Active', 'Inactive'])
            ).all()

            offers_updated_count = 0
            for offer in offers_to_check:
                if not self._is_loan_journey_active(session, offer.loan_application_number):
                    if offer.offer_status != 'Expired':
                        self._update_offer_status(session, offer, 'Expired',
                                                  f"LAN {offer.loan_application_number} journey ended.")
                        offers_updated_count += 1
                    else:
                        logging.debug(f"Offer {offer.offer_id} with LAN {offer.loan_application_number} already expired.")
                else:
                    logging.debug(f"Offer {offer.offer_id} with LAN {offer.loan_application_number} journey still active.")

            session.commit()
            logging.info(f"Finished checking offers with LANs. {offers_updated_count} offers updated to 'Expired'.")

        except Exception as e:
            session.rollback()
            logging.error(f"Error during check_and_expire_offers_with_invalid_lan: {e}", exc_info=True)
            raise
        finally:
            session.close()