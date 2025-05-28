import logging
from datetime import datetime, timezone
import uuid

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_, and_

# Configure logging for this service
logger = logging.getLogger(__name__)
# Set default logging level if not configured by the main application
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Model Imports / Fallback Definitions ---
# In a typical Flask application, models would be imported from a central models.py file.
# For robustness and to allow this service file to be more self-contained for testing,
# we include a fallback definition if the primary import fails.
# The project context suggests `backend.models` or `backend.src.models`.
try:
    # Assuming models are defined in backend.src.models
    from backend.src.models import Customer, Offer, OfferHistory
except ImportError:
    logger.warning("Could not import models from backend.src.models. Defining basic models for attribution_service.py as fallback.")
    # Fallback definitions for demonstration or if models.py isn't set up yet
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
    from sqlalchemy.dialects.postgresql import UUID, JSONB
    from sqlalchemy.orm import relationship

    Base = declarative_base()

    class Customer(Base):
        __tablename__ = 'customers'
        customer_id = Column(UUID(as_uuid=True), primary_key=True)
        mobile_number = Column(String(20), unique=True)
        pan_number = Column(String(10), unique=True)
        aadhaar_number = Column(String(12), unique=True)
        ucid_number = Column(String(50), unique=True)
        customer_360_id = Column(String(50))
        is_dnd = Column(Boolean, default=False)
        segment = Column(String(50))
        attributes = Column(JSONB)
        created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
        updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

        offers = relationship("Offer", back_populates="customer")

    class Offer(Base):
        __tablename__ = 'offers'
        offer_id = Column(UUID(as_uuid=True), primary_key=True)
        customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id'), nullable=False)
        source_offer_id = Column(String(100))
        offer_type = Column(String(50)) # 'Fresh', 'Enrich', 'New-old', 'New-new'
        offer_status = Column(String(50)) # 'Active', 'Inactive', 'Expired'
        propensity = Column(String(50)) # Stored as string, convert to int/float for comparison if needed
        loan_application_number = Column(String(100))
        valid_until = Column(DateTime(timezone=True))
        source_system = Column(String(50)) # 'Offermart', 'E-aggregator'
        channel = Column(String(50))
        is_duplicate = Column(Boolean, default=False)
        original_offer_id = Column(UUID(as_uuid=True), ForeignKey('offers.offer_id'))
        created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
        updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

        customer = relationship("Customer", back_populates="offers")
        # Define a relationship for original_offer to handle self-referencing for duplicates
        original_offer = relationship("Offer", remote_side=[offer_id], backref="duplicated_offers")

    class OfferHistory(Base):
        __tablename__ = 'offer_history'
        history_id = Column(UUID(as_uuid=True), primary_key=True)
        offer_id = Column(UUID(as_uuid=True), ForeignKey('offers.offer_id'), nullable=False)
        status_change_date = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
        old_status = Column(String(50))
        new_status = Column(String(50))
        change_reason = Column(String)

        offer = relationship("Offer")

# --- Attribution Service Implementation ---
class AttributionService:
    """
    Service responsible for applying attribution logic to customer offers.
    This determines which offer prevails when a customer has multiple offers,
    and updates the status of non-prevailing offers.
    """
    def __init__(self, db_session: Session):
        """
        Initializes the AttributionService with a SQLAlchemy database session.
        Args:
            db_session: An active SQLAlchemy session for database interactions.
        """
        self.db_session = db_session

    def _log_offer_status_change(self, offer: Offer, old_status: str, new_status: str, reason: str):
        """
        Logs a status change for an offer in the offer_history table (FR20).
        Only logs if the status has actually changed.
        """
        if old_status != new_status:
            history_entry = OfferHistory(
                offer_id=offer.offer_id,
                old_status=old_status,
                new_status=new_status,
                change_reason=reason
            )
            self.db_session.add(history_entry)
            logger.info(f"Offer {offer.offer_id} status changed from '{old_status}' to '{new_status}' due to: {reason}")

    def _get_offer_priority_score(self, offer: Offer) -> int:
        """
        Assigns a numerical priority score to an offer based on defined business rules (FR22).
        Higher score indicates higher priority.
        """
        score = 0

        # Rule 1: Active Loan Journey Priority (FR13, FR36)
        # Offers with an active loan application number that are not yet expired by LAN validity
        if offer.loan_application_number and offer.offer_status == 'Active':
            # Check if LAN validity is over (FR36)
            if offer.valid_until and offer.valid_until < datetime.now(timezone.utc):
                # Offer is expired by LAN validity, so it doesn't get journey priority
                pass
            else:
                score += 1000 # Highest priority for active journey

        # Rule 2: Offer Type Priority (FR17)
        # Prioritization: 'Fresh' > 'New-new' > 'New-old' > 'Enrich'
        if offer.offer_type == 'Fresh':
            score += 400
        elif offer.offer_type == 'New-new':
            score += 300
        elif offer.offer_type == 'New-old':
            score += 200
        elif offer.offer_type == 'Enrich':
            score += 100 # 'Enrich' offers have specific handling (FR18)

        # Rule 3: Propensity Score (FR19)
        # Assuming propensity can be a numerical string or categorical ('High', 'Medium', 'Low')
        try:
            propensity_val = int(offer.propensity)
            score += propensity_val # Add numerical propensity directly
        except (ValueError, TypeError):
            if offer.propensity and offer.propensity.lower() == 'high':
                score += 50
            elif offer.propensity and offer.propensity.lower() == 'medium':
                score += 30
            elif offer.propensity and offer.propensity.lower() == 'low':
                score += 10

        # Rule 4: Recency (Newer offers get a slight boost for tie-breaking)
        # Within the 3-month data retention period (FR29)
        if offer.created_at:
            age_days = (datetime.now(timezone.utc) - offer.created_at).days
            if age_days >= 0 and age_days < 90: # Offers within the last 90 days
                score += (90 - age_days) / 10 # Max 9 points for brand new, decreasing to 0.1 for 89-day old

        # Rule 5: Channel/Source System Priority (Implied by FR22, example rule)
        # E-aggregator offers might be prioritized for real-time leads
        if offer.source_system == 'E-aggregator':
            score += 20
        elif offer.source_system == 'Offermart':
            score += 10

        return score

    def apply_attribution_for_customer(self, customer_id: uuid.UUID) -> Offer | None:
        """
        Applies attribution logic for a single customer to determine the prevailing offer.
        Marks other offers as 'Inactive' or 'Duplicate' as per business rules.
        Returns the prevailing offer, or None if no relevant offers are found.
        """
        customer = self.db_session.query(Customer).get(customer_id)
        if not customer:
            logger.warning(f"Customer with ID {customer_id} not found for attribution.")
            return None

        # Fetch all offers for the customer that are 'Active' or 'Enrich'
        # 'Enrich' offers need to be considered for FR18 processing.
        # Order by creation date descending to use as a tie-breaker if scores are equal.
        offers = self.db_session.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.offer_status.in_(['Active', 'Enrich'])
        ).order_by(
            desc(Offer.created_at)
        ).all()

        if not offers:
            logger.info(f"No active or enrich offers found for customer {customer_id} for attribution.")
            return None

        prevailing_offer = None
        max_score = -1

        # First pass: Identify the prevailing offer based on priority rules
        for offer in offers:
            # FR36: Mark offers as expired if LAN validity is over
            if offer.loan_application_number and offer.valid_until and offer.valid_until < datetime.now(timezone.utc):
                if offer.offer_status != 'Expired':
                    old_status = offer.offer_status
                    offer.offer_status = 'Expired'
                    self._log_offer_status_change(offer, old_status, 'Expired', 'Loan Application Number validity expired (FR36)')
                continue # This offer is now expired, skip it for prevailing logic

            # FR13: Offers with an active loan application journey take highest precedence.
            # If an offer has an active LAN and is not expired, it is the prevailing offer.
            if offer.loan_application_number and offer.offer_status == 'Active':
                prevailing_offer = offer
                logger.info(f"Customer {customer_id}: Offer {offer.offer_id} is prevailing due to active loan journey (FR13).")
                break # Found the highest priority offer, no need to check others for score

            score = self._get_offer_priority_score(offer)
            if score > max_score:
                max_score = score
                prevailing_offer = offer
            elif score == max_score and prevailing_offer and offer.created_at > prevailing_offer.created_at:
                # Tie-breaker: if scores are equal, the more recent offer prevails
                prevailing_offer = offer

        if not prevailing_offer:
            logger.warning(f"No prevailing offer determined for customer {customer_id} after initial scoring. All offers might be expired or invalid.")
            return None

        # Second pass: Update statuses of non-prevailing offers
        for offer in offers:
            if offer.offer_id != prevailing_offer.offer_id:
                old_status = offer.offer_status
                old_is_duplicate = offer.is_duplicate

                # FR18: Handle 'Enrich' offers specifically
                if offer.offer_type == 'Enrich':
                    # If the prevailing offer has an active loan journey, the 'Enrich' offer is ignored.
                    # This implies it should not become active or modify the existing journey.
                    if prevailing_offer.loan_application_number and prevailing_offer.offer_status == 'Active':
                        if offer.offer_status != 'Inactive':
                            offer.offer_status = 'Inactive'
                            self._log_offer_status_change(offer, old_status, 'Inactive',
                                                           f"Enrich offer {offer.offer_id} inactivated because prevailing offer {prevailing_offer.offer_id} has an active journey (FR18).")
                        # Also ensure it's marked as duplicate if it was meant to enrich a journey
                        if not old_is_duplicate:
                            offer.is_duplicate = True
                            offer.original_offer_id = prevailing_offer.offer_id
                            logger.info(f"Enrich offer {offer.offer_id} marked as duplicate of {prevailing_offer.offer_id} (FR18).")
                    else:
                        # If the enrich offer is not prevailing and no active journey on prevailing,
                        # it should be marked as duplicate/inactive.
                        if offer.offer_status != 'Inactive':
                            offer.offer_status = 'Inactive'
                            self._log_offer_status_change(offer, old_status, 'Inactive',
                                                           f"Enrich offer {offer.offer_id} inactivated by prevailing offer {prevailing_offer.offer_id} (FR18).")
                        if not old_is_duplicate:
                            offer.is_duplicate = True
                            offer.original_offer_id = prevailing_offer.offer_id
                            logger.info(f"Enrich offer {offer.offer_id} marked as duplicate of {prevailing_offer.offer_id} (FR18).")
                else:
                    # For other offer types, if not the prevailing offer, mark as 'Inactive'
                    if offer.offer_status == 'Active': # Only change if currently active
                        offer.offer_status = 'Inactive'
                        self._log_offer_status_change(offer, old_status, 'Inactive',
                                                       f"Inactivated by attribution logic; {prevailing_offer.offer_id} is prevailing.")
                    # Ensure non-prevailing offers are marked as duplicates if applicable
                    if not old_is_duplicate:
                        offer.is_duplicate = True
                        offer.original_offer_id = prevailing_offer.offer_id
                        logger.info(f"Offer {offer.offer_id} marked as duplicate of {prevailing_offer.offer_id}.")
            else:
                # Ensure the prevailing offer is 'Active' and not marked as 'is_duplicate'
                if offer.offer_status != 'Active':
                    old_status = offer.offer_status
                    offer.offer_status = 'Active'
                    self._log_offer_status_change(offer, old_status, 'Active', "Set as prevailing offer by attribution logic.")
                if offer.is_duplicate:
                    offer.is_duplicate = False
                    offer.original_offer_id = None # It is now the primary offer
                    logger.info(f"Prevailing offer {offer.offer_id} cleared of duplicate flag.")

        try:
            self.db_session.commit()
            logger.info(f"Attribution completed for customer {customer_id}. Prevailing offer: {prevailing_offer.offer_id}")
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to commit attribution changes for customer {customer_id}: {e}", exc_info=True)
            raise # Re-raise to indicate failure

        return prevailing_offer

    def apply_attribution_batch(self):
        """
        Applies attribution logic for all customers who have active or enrich offers.
        This method is suitable for a scheduled batch job.
        """
        logger.info("Starting batch attribution process for all relevant customers.")

        # Get distinct customer IDs that have offers that are 'Active' or 'Enrich'
        # We only need to process customers who might have offers that need attribution.
        customer_ids_to_process = self.db_session.query(Customer.customer_id).join(Offer).filter(
            Offer.offer_status.in_(['Active', 'Enrich'])
        ).distinct().all()

        processed_count = 0
        error_count = 0

        for (customer_id,) in customer_ids_to_process:
            try:
                self.apply_attribution_for_customer(customer_id)
                processed_count += 1
            except Exception as e:
                # The individual customer attribution function handles its own rollback on error
                # but we catch here to continue processing other customers.
                logger.error(f"Error applying attribution for customer {customer_id}: {e}", exc_info=True)
                error_count += 1

        logger.info(f"Batch attribution process completed. Processed {processed_count} customers, {error_count} errors.")