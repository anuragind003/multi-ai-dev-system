import uuid
from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy import create_engine, Column, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

# Assuming models are defined in backend.models
# In a real Flask app, models would be imported from a central models.py
# For standalone execution or if backend.models is not yet structured,
# we define basic models here as a fallback.
try:
    from backend.models import Base, Customer, Offer, OfferHistory
except ImportError:
    logging.warning("Could not import models from backend.models. Defining basic models for attribution_service.py.")
    Base = declarative_base()

    class Customer(Base):
        __tablename__ = 'customers'
        customer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        mobile_number = Column(String(20), unique=True)
        pan_number = Column(String(10), unique=True)
        aadhaar_number = Column(String(12), unique=True)
        ucid_number = Column(String(50), unique=True)
        customer_360_id = Column(String(50))
        is_dnd = Column(Boolean, default=False)
        segment = Column(String(50))
        attributes = Column(JSONB)
        created_at = Column(DateTime(timezone=True), default=func.now())
        updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

        offers = relationship("Offer", back_populates="customer")

    class Offer(Base):
        __tablename__ = 'offers'
        offer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id'), nullable=False)
        source_offer_id = Column(String(100))
        offer_type = Column(String(50)) # 'Fresh', 'Enrich', 'New-old', 'New-new'
        offer_status = Column(String(50)) # 'Active', 'Inactive', 'Expired'
        propensity = Column(String(50))
        loan_application_number = Column(String(100))
        valid_until = Column(DateTime(timezone=True))
        source_system = Column(String(50)) # 'Offermart', 'E-aggregator'
        channel = Column(String(50))
        is_duplicate = Column(Boolean, default=False)
        original_offer_id = Column(UUID(as_uuid=True), ForeignKey('offers.offer_id')) # Points to the offer it duplicated/enriched
        created_at = Column(DateTime(timezone=True), default=func.now())
        updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

        customer = relationship("Customer", back_populates="offers")
        history = relationship("OfferHistory", back_populates="offer")

    class OfferHistory(Base):
        __tablename__ = 'offer_history'
        history_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        offer_id = Column(UUID(as_uuid=True), ForeignKey('offers.offer_id'), nullable=False)
        status_change_date = Column(DateTime(timezone=True), default=func.now())
        old_status = Column(String(50))
        new_status = Column(String(50))
        change_reason = Column(String)

        offer = relationship("Offer", back_populates="history")


# Assuming config is available for DATABASE_URI
try:
    from backend.config import DATABASE_URI
except ImportError:
    logging.error("backend.config.DATABASE_URI not found. Please ensure config.py is set up.")
    # Fallback for development/testing if config is not yet available
    DATABASE_URI = "postgresql://user:password@localhost:5432/cdp_db" # Placeholder for local testing

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AttributionService:
    def __init__(self, db_uri=None):
        self.engine = create_engine(db_uri or DATABASE_URI)
        self.Session = sessionmaker(bind=self.engine)
        logger.info("AttributionService initialized with database engine.")

    def _get_offer_priority(self, offer: Offer) -> int:
        """
        Determines the priority of an offer based on defined business logic.
        Higher return value means higher priority.
        """
        priority = 0

        # Rule 1: Offers with active loan application journey (FR13)
        # Assuming 'Active' status and presence of LAN means active journey
        if offer.loan_application_number and offer.offer_status == 'Active':
            priority += 1000 # High priority for active journeys

        # Rule 2: Offer Type Priority (FR17)
        # 'New-new' > 'Fresh' > 'Enrich' (if not journey started) > 'New-old'
        if offer.offer_type == 'New-new':
            priority += 500
        elif offer.offer_type == 'Fresh':
            priority += 400
        elif offer.offer_type == 'Enrich':
            # FR18: if journey not started, flow to CDP and mark previous as Duplicate; if journey started, do not flow to CDP.
            # For attribution, an 'Enrich' offer might be lower priority than 'Fresh' unless it's the only active one.
            # We give it a moderate priority if it's active and not tied to a journey.
            if not offer.loan_application_number:
                priority += 300
            else: # If journey started, it shouldn't flow to CDP, so it's lower priority for new attribution
                priority -= 100 # Effectively de-prioritize if it somehow made it here with a journey
        elif offer.offer_type == 'New-old':
            priority += 200

        # Rule 3: Source System/Channel Priority
        # E-aggregator (real-time) might be higher priority than Offermart (batch)
        if offer.source_system == 'E-aggregator':
            priority += 50
        elif offer.source_system == 'Offermart':
            priority += 20

        # Rule 4: Propensity (higher propensity is better)
        # Assuming propensity is a string that can be ordered or mapped to a score
        # Example: 'High' > 'Medium' > 'Low'
        if offer.propensity:
            propensity_map = {'High': 30, 'Medium': 20, 'Low': 10}
            priority += propensity_map.get(offer.propensity, 0)

        # Rule 5: Recency (more recent active offers might be preferred)
        # This is a tie-breaker, so it should be a smaller increment
        if offer.created_at:
            # Add seconds since epoch to prioritize newer offers, but scale it down
            priority += int(offer.created_at.timestamp() / 100000) # Scale to avoid overwhelming other rules

        return priority

    def apply_attribution_for_customer(self, customer_id: uuid.UUID):
        """
        Applies attribution logic for a single customer to determine the prevailing offer.
        Marks other offers as 'Inactive' or 'Duplicate' as per logic.
        """
        session = self.Session()
        try:
            customer = session.query(Customer).filter_by(customer_id=customer_id).first()
            if not customer:
                logger.warning(f"Customer with ID {customer_id} not found for attribution.")
                return

            # Get all active offers for the customer that are not already marked as duplicate
            # and are not expired.
            active_offers = session.query(Offer).filter(
                Offer.customer_id == customer_id,
                Offer.offer_status == 'Active',
                Offer.is_duplicate == False,
                Offer.valid_until >= datetime.now(timezone.utc) # Ensure offer is still valid
            ).order_by(Offer.created_at.desc()).all() # Order by creation date as a default tie-breaker

            if not active_offers:
                logger.info(f"No active offers found for customer {customer_id}. No attribution needed.")
                return

            # Sort offers by priority
            # We use a tuple for sorting to ensure consistent tie-breaking:
            # (priority_score, created_at_timestamp) - higher score first, then newer offer
            sorted_offers = sorted(
                active_offers,
                key=lambda o: (self._get_offer_priority(o), o.created_at.timestamp() if o.created_at else 0),
                reverse=True
            )

            prevailing_offer = sorted_offers[0]
            logger.info(f"Customer {customer_id}: Prevailing offer identified: {prevailing_offer.offer_id} (Type: {prevailing_offer.offer_type}, Source: {prevailing_offer.source_system}, LAN: {prevailing_offer.loan_application_number})")

            # Mark other offers as 'Inactive' or 'Duplicate'
            for offer in sorted_offers:
                if offer.offer_id == prevailing_offer.offer_id:
                    continue # Skip the prevailing offer itself

                old_status = offer.offer_status
                new_status = 'Inactive'
                change_reason = f"Superseded by prevailing offer {prevailing_offer.offer_id} due to attribution logic."

                # Special handling for 'Enrich' offers (FR18)
                # If the prevailing offer is an 'Enrich' offer, and it points to an 'original_offer_id',
                # then that original offer should be marked as duplicate/inactive.
                # This logic should ideally be handled when the 'Enrich' offer is ingested,
                # but we can reinforce it here.
                if prevailing_offer.offer_type == 'Enrich' and prevailing_offer.original_offer_id == offer.offer_id:
                    # This 'offer' is the one that the prevailing 'Enrich' offer is superseding.
                    new_status = 'Inactive' # Or 'Superseded' if we add that status
                    offer.is_duplicate = True # Mark as duplicate as per FR18
                    change_reason = f"Marked as duplicate/inactive by prevailing Enrich offer {prevailing_offer.offer_id}."
                    logger.info(f"Offer {offer.offer_id} marked as Inactive/Duplicate by Enrich offer {prevailing_offer.offer_id}.")

                # Mark the non-prevailing offer as inactive if it's currently active
                if offer.offer_status == 'Active':
                    offer.offer_status = new_status
                    session.add(OfferHistory(
                        offer_id=offer.offer_id,
                        old_status=old_status,
                        new_status=new_status,
                        change_reason=change_reason
                    ))
                    logger.info(f"Offer {offer.offer_id} for customer {customer_id} marked as '{new_status}'. Reason: {change_reason}")

            session.commit()
            logger.info(f"Attribution logic applied successfully for customer {customer_id}.")

        except Exception as e:
            session.rollback()
            logger.error(f"Error applying attribution for customer {customer_id}: {e}", exc_info=True)
        finally:
            session.close()

    def apply_attribution_batch(self, customer_ids: list[uuid.UUID] = None):
        """
        Applies attribution logic for a batch of customers.
        If customer_ids is None, applies to all customers with active offers.
        This method could be called by a scheduled job.
        """
        session = self.Session()
        try:
            if customer_ids:
                customers_to_process = session.query(Customer).filter(Customer.customer_id.in_(customer_ids)).all()
            else:
                # Find all customers who have at least one active, non-duplicate offer
                customers_to_process = session.query(Customer).join(Offer).filter(
                    Offer.offer_status == 'Active',
                    Offer.is_duplicate == False,
                    Offer.valid_until >= datetime.now(timezone.utc)
                ).distinct().all()

            logger.info(f"Starting batch attribution for {len(customers_to_process)} customers.")
            for customer in customers_to_process:
                self.apply_attribution_for_customer(customer.customer_id)
            logger.info("Batch attribution completed.")
        except Exception as e:
            logger.error(f"Error during batch attribution: {e}", exc_info=True)
        finally:
            session.close()

# Example usage (for testing purposes, typically called from a Flask route or a scheduled task)
if __name__ == "__main__":
    # This block is for testing the service in isolation.
    # Ensure you have a PostgreSQL database running and DATABASE_URI is correctly set.
    # For this example, we'll use the placeholder DATABASE_URI.

    # Create tables if they don't exist (for testing purposes)
    # In a real app, migrations (e.g., Alembic) would handle this.
    engine = create_engine(DATABASE_URI)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    # Initialize service
    attribution_service = AttributionService(db_uri=DATABASE_URI)

    # --- Test Data Setup ---
    session = Session()
    try:
        # Clear existing data for clean test
        session.query(OfferHistory).delete()
        session.query(Offer).delete()
        session.query(Customer).delete()
        session.commit()

        # Create a test customer
        test_customer_id = uuid.uuid4()
        customer = Customer(
            customer_id=test_customer_id,
            mobile_number='9876543210',
            pan_number='ABCDE1234F',
            segment='C1',
            is_dnd=False
        )
        session.add(customer)
        session.commit()
        logger.info(f"Created test customer: {customer.customer_id}")

        # Create multiple offers for the customer
        offer1_id = uuid.uuid4()
        offer1 = Offer(
            offer_id=offer1_id,
            customer_id=test_customer_id,
            source_offer_id='OFFER001',
            offer_type='New-old',
            offer_status='Active',
            propensity='Low',
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
            source_system='Offermart',
            created_at=datetime.now(timezone.utc) - timedelta(days=5)
        )

        offer2_id = uuid.uuid4()
        offer2 = Offer(
            offer_id=offer2_id,
            customer_id=test_customer_id,
            source_offer_id='OFFER002',
            offer_type='Fresh',
            offer_status='Active',
            propensity='Medium',
            valid_until=datetime.now(timezone.utc) + timedelta(days=60),
            source_system='Offermart',
            created_at=datetime.now(timezone.utc) - timedelta(days=2)
        )

        offer3_id = uuid.uuid4()
        offer3 = Offer(
            offer_id=offer3_id,
            customer_id=test_customer_id,
            source_offer_id='OFFER003',
            offer_type='New-new',
            offer_status='Active',
            propensity='High',
            valid_until=datetime.now(timezone.utc) + timedelta(days=90),
            source_system='E-aggregator',
            created_at=datetime.now(timezone.utc) - timedelta(days=1) # Most recent
        )

        offer4_id = uuid.uuid4()
        offer4 = Offer(
            offer_id=offer4_id,
            customer_id=test_customer_id,
            source_offer_id='OFFER004',
            offer_type='Enrich',
            offer_status='Active',
            propensity='Medium',
            valid_until=datetime.now(timezone.utc) + timedelta(days=45),
            source_system='Offermart',
            original_offer_id=offer1_id, # This enrich offer is for offer1
            created_at=datetime.now(timezone.utc) - timedelta(days=3)
        )

        offer5_id = uuid.uuid4()
        offer5 = Offer(
            offer_id=offer5_id,
            customer_id=test_customer_id,
            source_offer_id='OFFER005',
            offer_type='Fresh',
            offer_status='Active',
            propensity='High',
            loan_application_number='LAN12345', # This one has an active journey
            valid_until=datetime.now(timezone.utc) + timedelta(days=120),
            source_system='Offermart',
            created_at=datetime.now(timezone.utc) - timedelta(hours=1) # Very recent
        )

        session.add_all([offer1, offer2, offer3, offer4, offer5])
        session.commit()
        logger.info("Added test offers.")

        # --- Run Attribution ---
        logger.info("\n--- Running attribution for test customer ---")
        attribution_service.apply_attribution_for_customer(test_customer_id)

        # --- Verify Results ---
        logger.info("\n--- Verifying results ---")
        updated_offers = session.query(Offer).filter_by(customer_id=test_customer_id).all()
        for offer in updated_offers:
            logger.info(f"Offer ID: {offer.offer_id}, Type: {offer.offer_type}, Status: {offer.offer_status}, "
                        f"Propensity: {offer.propensity}, Source: {offer.source_system}, "
                        f"LAN: {offer.loan_application_number}, Is Duplicate: {offer.is_duplicate}")

        offer_history_entries = session.query(OfferHistory).filter(OfferHistory.offer_id.in_([o.offer_id for o in updated_offers])).all()
        logger.info("\n--- Offer History ---")
        for entry in offer_history_entries:
            logger.info(f"History ID: {entry.history_id}, Offer ID: {entry.offer_id}, "
                        f"Old Status: {entry.old_status}, New Status: {entry.new_status}, "
                        f"Reason: {entry.change_reason}")

        # Test with a customer having no active offers
        test_customer_no_offers_id = uuid.uuid4()
        customer_no_offers = Customer(
            customer_id=test_customer_no_offers_id,
            mobile_number='1111111111',
            pan_number='ABCDE5432G',
            segment='C2'
        )
        session.add(customer_no_offers)
        session.commit()
        logger.info(f"\n--- Running attribution for customer with no offers ({test_customer_no_offers_id}) ---")
        attribution_service.apply_attribution_for_customer(test_customer_no_offers_id)

        # Test batch attribution (e.g., for all customers)
        logger.info("\n--- Running batch attribution for all customers ---")
        attribution_service.apply_attribution_batch()

    except Exception as e:
        session.rollback()
        logger.error(f"An error occurred during test execution: {e}", exc_info=True)
    finally:
        session.close()
        logger.info("Test execution finished.")