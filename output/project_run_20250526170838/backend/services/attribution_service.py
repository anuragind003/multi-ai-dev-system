import uuid
from datetime import datetime, date
import logging

# Corrected import for JSONB and other types
from sqlalchemy import Column, String, Boolean, DateTime, Date, Integer, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB # Specific to PostgreSQL for JSONB type

# Assuming db object and Base are defined in backend.database
# And models are defined in backend.models
# This assumes a project structure where models are separate files
from backend.database import db, Base
from backend.models.customer import Customer
from backend.models.offer import Offer
# from backend.models.event import Event # Not directly used in attribution logic for now

logger = logging.getLogger(__name__)

class AttributionService:
    """
    Service responsible for applying attribution logic to customer offers.
    Determines which channel/offer prevails when a customer has multiple
    interactions or existing offers, based on defined business rules (FR21).
    """

    def __init__(self):
        # No specific initialization needed for now, db session is managed by Flask-SQLAlchemy
        pass

    def _get_customer_active_offers(self, customer_id: str):
        """
        Retrieves all active offers for a given customer.
        """
        return db.session.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.offer_status == 'Active'
        ).all()

    def _has_active_journey_offer(self, customer_id: str) -> bool:
        """
        Checks if the customer has any active offer with a started loan application journey.
        (FR14: The system shall prevent modification of customer offers with a started
        loan application journey until the application is expired or rejected.)
        """
        return db.session.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.is_journey_started == True,
            Offer.offer_status == 'Active'
        ).first() is not None

    def apply_attribution_logic(self, customer_id: str, new_offer_data: dict = None) -> Offer | None:
        """
        Applies attribution logic to determine the prevailing offer for a customer.
        This method can be called when:
        1. A new offer is ingested for a customer.
        2. An existing offer's status needs re-evaluation.

        Args:
            customer_id (str): The ID of the customer.
            new_offer_data (dict, optional): Data for a potential new offer to be evaluated.
                                             Expected keys: 'offer_type', 'propensity', 'channel',
                                             'start_date' (date object), 'end_date' (date object), etc.
                                             If None, only existing offers are re-evaluated.

        Returns:
            Offer: The prevailing offer after applying attribution, or None if no active offers.
        """
        logger.info(f"Applying attribution logic for customer_id: {customer_id}")

        # FR14: If customer has an active loan application journey, prevent modification of existing offers.
        # In this scenario, new offers might still be created but marked 'Inactive' or 'Pending'.
        # The prevailing offer will be the one tied to the active journey.
        if self._has_active_journey_offer(customer_id):
            logger.warning(f"Customer {customer_id} has an active loan application journey. "
                           "New offers will not supersede the journey offer.")
            journey_offer = db.session.query(Offer).filter(
                Offer.customer_id == customer_id,
                Offer.is_journey_started == True,
                Offer.offer_status == 'Active'
            ).first()

            # If a new offer data is provided, create it but mark as 'Inactive'
            # as it cannot supersede the journey offer.
            if new_offer_data:
                new_offer = Offer(
                    offer_id=str(uuid.uuid4()),
                    customer_id=customer_id,
                    offer_type=new_offer_data.get('offer_type'),
                    offer_status='Inactive', # Cannot be active if journey offer exists
                    propensity=new_offer_data.get('propensity'),
                    start_date=new_offer_data.get('start_date'),
                    end_date=new_offer_data.get('end_date'),
                    channel=new_offer_data.get('channel'),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(new_offer)
                logger.info(f"New offer {new_offer.offer_id} created as 'Inactive' for customer {customer_id} "
                            "due to active journey.")
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error committing new inactive offer for customer {customer_id}: {e}")
                raise
            return journey_offer # The journey offer remains the prevailing one

        existing_offers = self._get_customer_active_offers(customer_id)
        prevailing_offer = None

        # Define priority for offer types (higher value means higher priority)
        # FR17: 'Fresh', 'Enrich', 'New-old', 'New-new'
        offer_type_priority = {
            'Fresh': 3,
            'Enrich': 2,
            'New-new': 1,
            'New-old': 1,
            # Add other types as needed based on business rules
        }

        # Helper to get priority for an offer (or new offer data)
        def get_offer_priority_tuple(offer_obj):
            offer_type = offer_obj.offer_type if isinstance(offer_obj, Offer) else offer_obj.get('offer_type')
            propensity = offer_obj.propensity if isinstance(offer_obj, Offer) else offer_obj.get('propensity')
            updated_at = offer_obj.updated_at if isinstance(offer_obj, Offer) else datetime.utcnow() # New offers are most recent

            # Convert propensity to a comparable format if it's text.
            # Assuming 'propensity' is a string that can be ordered lexicographically.
            # If it's numerical, it should be stored as NUMERIC in DB and cast here.
            # For categorical (e.g., 'High', 'Medium', 'Low'), a mapping would be needed.
            propensity_val = propensity if propensity else ''

            return (
                offer_type_priority.get(offer_type, 0),
                propensity_val,
                updated_at
            )

        # Step 1: Determine the initial prevailing offer among existing active ones
        if existing_offers:
            # Sort existing offers by priority:
            # 1. Offer Type (higher priority value first)
            # 2. Propensity (lexicographical comparison, assuming higher is better or specific values are preferred)
            # 3. Recency (most recently updated/created first)
            sorted_offers = sorted(
                existing_offers,
                key=get_offer_priority_tuple,
                reverse=True
            )
            prevailing_offer = sorted_offers[0]
            logger.debug(f"Initial prevailing offer for {customer_id} is {prevailing_offer.offer_id} "
                         f"({prevailing_offer.offer_type}, {prevailing_offer.propensity})")

            # Deactivate all other active offers for this customer
            for offer in existing_offers:
                if offer.offer_id != prevailing_offer.offer_id:
                    if offer.offer_status == 'Active':
                        offer.offer_status = 'Inactive'
                        offer.updated_at = datetime.utcnow()
                        db.session.add(offer) # Mark for update
                        logger.info(f"Deactivated offer {offer.offer_id} for customer {customer_id}")

        # Step 2: Evaluate a potential new offer against the prevailing one
        if new_offer_data:
            logger.debug(f"Evaluating new offer data for customer {customer_id}: {new_offer_data.get('offer_type')}")

            # If no prevailing offer exists, the new one automatically becomes prevailing
            if not prevailing_offer:
                new_offer = Offer(
                    offer_id=str(uuid.uuid4()),
                    customer_id=customer_id,
                    offer_type=new_offer_data.get('offer_type'),
                    offer_status='Active',
                    propensity=new_offer_data.get('propensity'),
                    start_date=new_offer_data.get('start_date'),
                    end_date=new_offer_data.get('end_date'),
                    channel=new_offer_data.get('channel'),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(new_offer)
                prevailing_offer = new_offer
                logger.info(f"New offer {new_offer.offer_id} became prevailing for {customer_id} (no prior active offer).")
            else:
                # Compare new offer with current prevailing offer
                new_offer_priority_tuple = get_offer_priority_tuple(new_offer_data)
                current_prevailing_priority_tuple = get_offer_priority_tuple(prevailing_offer)

                # If the new offer is strictly better based on the defined priority
                if new_offer_priority_tuple > current_prevailing_priority_tuple:
                    logger.info(f"New offer data is better than current prevailing offer {prevailing_offer.offer_id}")
                    # Deactivate the old prevailing offer
                    prevailing_offer.offer_status = 'Inactive'
                    prevailing_offer.updated_at = datetime.utcnow()
                    db.session.add(prevailing_offer)

                    # Create and activate the new offer
                    new_offer = Offer(
                        offer_id=str(uuid.uuid4()),
                        customer_id=customer_id,
                        offer_type=new_offer_data.get('offer_type'),
                        offer_status='Active',
                        propensity=new_offer_data.get('propensity'),
                        start_date=new_offer_data.get('start_date'),
                        end_date=new_offer_data.get('end_date'),
                        channel=new_offer_data.get('channel'),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(new_offer)
                    prevailing_offer = new_offer
                    logger.info(f"New offer {new_offer.offer_id} became prevailing for {customer_id}")
                else:
                    logger.info(f"New offer data is not better than current prevailing offer {prevailing_offer.offer_id}. "
                                "New offer will not be activated as prevailing.")
                    # Business decision: If not prevailing, should it still be stored as 'Inactive'?
                    # For now, we assume it's not stored if it doesn't become active.
                    # If it needs to be stored, it should be created here with 'Inactive' status.
                    # Example:
                    # new_offer_to_store = Offer(
                    #     offer_id=str(uuid.uuid4()),
                    #     customer_id=customer_id,
                    #     offer_type=new_offer_data.get('offer_type'),
                    #     offer_status='Inactive', # Store as inactive
                    #     propensity=new_offer_data.get('propensity'),
                    #     start_date=new_offer_data.get('start_date'),
                    #     end_date=new_offer_data.get('end_date'),
                    #     channel=new_offer_data.get('channel'),
                    #     created_at=datetime.utcnow(),
                    #     updated_at=datetime.utcnow()
                    # )
                    # db.session.add(new_offer_to_store)

        try:
            db.session.commit()
            logger.info(f"Attribution logic committed for customer {customer_id}.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error applying attribution logic for customer {customer_id}: {e}")
            raise

        return prevailing_offer