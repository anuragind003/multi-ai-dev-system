from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import or_

# Assuming db and models are defined in app.extensions and app.models respectively
from app.extensions import db
from app.models import Customer, Offer, CustomerEvent


class OfferService:
    """
    Service layer for managing customer offers.
    Encapsulates business logic related to offer creation, updates,
    status management (expiry), and attribution.
    """

    @staticmethod
    def create_or_update_offer(customer_id: str, offer_details: dict) -> Offer:
        """
        Creates a new offer or updates an existing one for a given customer.
        Applies FR13: Prevents modification of customer offers with started loan
        application journeys until the loan application is either expired or rejected.

        Args:
            customer_id (str): The UUID of the customer.
            offer_details (dict): Dictionary containing offer data.
                                  Expected keys: offer_id (optional, for update),
                                  offer_type, offer_status, propensity_flag,
                                  offer_start_date, offer_end_date,
                                  loan_application_number, attribution_channel.
                                  Dates should be in 'YYYY-MM-DD' string format.

        Returns:
            Offer: The created or updated Offer object.

        Raises:
            ValueError: If customer_id is invalid or offer data is missing/invalid.
            PermissionError: If an attempt is made to modify an offer with an
                             active loan application journey.
            SQLAlchemyError: For database-related errors.
        """
        logger = current_app.logger

        customer = Customer.query.get(customer_id)
        if not customer:
            logger.error(f"Customer with ID {customer_id} not found.")
            raise ValueError(f"Customer with ID {customer_id} not found.")

        offer_id = offer_details.get('offer_id')
        loan_application_number = offer_details.get('loan_application_number')
        offer = None

        if offer_id:
            offer = Offer.query.get(offer_id)
            if not offer:
                logger.error(f"Offer with ID {offer_id} not found for update.")
                raise ValueError(f"Offer with ID {offer_id} not found.")

            # FR13: Prevent modification if loan application journey started and not expired/rejected
            # This is a simplification. A more robust check would involve querying
            # CustomerEvent for application stages and their final status for the given LAN.
            # For now, if LAN is present and the offer is not 'Expired', we assume the journey is active.
            if offer.loan_application_number and offer.offer_status != 'Expired':
                # Placeholder for actual logic to check if loan application is active/pending
                # Example: Check CustomerEvent for latest status of this loan_application_number
                # is_loan_active = CustomerEvent.query.filter(
                #     CustomerEvent.customer_id == customer_id,
                #     CustomerEvent.event_details.op('->>')('loan_application_number') == offer.loan_application_number
                # ).order_by(CustomerEvent.event_timestamp.desc()).first()
                # if is_loan_active and is_loan_active.event_type not in ['LOAN_REJECTED', 'LOAN_EXPIRED']:
                logger.warning(f"Attempt to modify offer {offer_id} with active loan application {offer.loan_application_number}.")
                raise PermissionError(
                    f"Offer {offer_id} cannot be modified as its loan application "
                    f"{offer.loan_application_number} journey is active."
                )

            logger.info(f"Updating offer {offer_id} for customer {customer_id}.")
            for key, value in offer_details.items():
                if key not in ['offer_id', 'customer_id'] and hasattr(offer, key):
                    if 'date' in key and isinstance(value, str):
                        setattr(offer, key, datetime.strptime(value, '%Y-%m-%d').date())
                    else:
                        setattr(offer, key, value)
            offer.updated_at = datetime.now()
        else:
            logger.info(f"Creating new offer for customer {customer_id}.")
            offer = Offer(customer_id=customer_id)
            for key, value in offer_details.items():
                if hasattr(offer, key):
                    if 'date' in key and isinstance(value, str):
                        setattr(offer, key, datetime.strptime(value, '%Y-%m-%d').date())
                    else:
                        setattr(offer, key, value)
            offer.created_at = datetime.now()
            offer.updated_at = datetime.now()

        try:
            db.session.add(offer)
            db.session.commit()
            logger.info(f"Offer {offer.offer_id} successfully {'updated' if offer_id else 'created'}.")
            return offer
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error creating/updating offer: {e}")
            raise ValueError("Invalid data provided for offer creation/update.") from e
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error creating/updating offer: {e}")
            raise SQLAlchemyError("Failed to create/update offer due to a database error.") from e

    @staticmethod
    def apply_attribution_logic(customer_id: str) -> Offer | None:
        """
        Applies attribution logic (FR20) to determine the prevailing offer/channel
        when a customer has multiple offers or comes through different channels.
        This is a simplified implementation. Real-world logic would be more complex
        and depend on specific business rules (e.g., channel priority, recency,
        offer value, customer segment).

        Rules (example simplification):
        1. Prioritize 'Active' offers.
        2. Among active offers, prioritize by 'New-new', then 'New-old', 'Fresh', 'Enrich'.
        3. If still multiple, pick the one with the latest 'offer_start_date'.
        4. Mark other active offers as 'Inactive' if a prevailing one is found.

        Args:
            customer_id (str): The UUID of the customer.

        Returns:
            Offer: The prevailing Offer object, or None if no active offers.
        """
        logger = current_app.logger
        logger.info(f"Applying attribution logic for customer {customer_id}.")

        active_offers = Offer.query.filter_by(
            customer_id=customer_id,
            offer_status='Active'
        ).all()

        if not active_offers:
            logger.info(f"No active offers found for customer {customer_id}.")
            return None

        # Define a simple priority for offer types (FR16)
        offer_type_priority = {
            'New-new': 4,
            'New-old': 3,
            'Fresh': 2,
            'Enrich': 1
        }

        # Sort offers based on defined priority, then by offer_start_date, then by creation date
        sorted_offers = sorted(
            active_offers,
            key=lambda o: (
                offer_type_priority.get(o.offer_type, 0),
                o.offer_start_date if o.offer_start_date else datetime.min.date(),
                o.created_at
            ),
            reverse=True
        )

        prevailing_offer = sorted_offers[0]
        logger.info(f"Prevailing offer identified: {prevailing_offer.offer_id} (Type: {prevailing_offer.offer_type})")

        # Mark other active offers as 'Inactive'
        for offer in sorted_offers[1:]:
            if offer.offer_status == 'Active':
                offer.offer_status = 'Inactive'
                offer.updated_at = datetime.now()
                db.session.add(offer)
                logger.info(f"Marked offer {offer.offer_id} as Inactive due to attribution.")

        try:
            db.session.commit()
            return prevailing_offer
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error during attribution logic for customer {customer_id}: {e}")
            raise SQLAlchemyError("Failed to apply attribution logic due to a database error.") from e

    @staticmethod
    def update_expired_offers() -> int:
        """
        Updates offer statuses to 'Expired' based on defined business logic (FR15, FR37, FR38).
        This function is intended to be called by a scheduled task.

        Logic:
        1. Mark offers as 'Expired' if their offer_end_date is in the past (FR37).
        2. Mark offers as 'Expired' if their associated Loan Application Number (LAN)
           journey is over (expired or rejected) (FR38). This part requires checking
           CustomerEvent or an external system for LAN status.
        """
        logger = current_app.logger
        logger.info("Starting update of expired offers...")
        now_date = datetime.now().date()
        offers_to_expire = set() # Use a set to avoid duplicates if an offer matches multiple criteria

        # FR37: Offers for non-journey started customers depend on offer end dates
        # Find active offers whose end date has passed and have no associated LAN
        expired_by_date = Offer.query.filter(
            Offer.offer_status == 'Active',
            Offer.offer_end_date < now_date,
            Offer.loan_application_number.is_(None)
        ).all()
        offers_to_expire.update(expired_by_date)
        logger.info(f"Found {len(expired_by_date)} offers expired by date.")

        # FR38: Mark offers as expired if LAN validity post loan application journey start date is over.
        # This requires checking the status of the loan application number.
        # This is a simplified check, assuming CustomerEvent provides 'LOAN_REJECTED' or 'LOAN_EXPIRED' events.
        offers_with_lan = Offer.query.filter(
            Offer.offer_status == 'Active',
            Offer.loan_application_number.isnot(None)
        ).all()

        for offer in offers_with_lan:
            # Check if there's a 'LOAN_REJECTED' or 'LOAN_EXPIRED' event for this LAN
            # This assumes event_details stores the loan_application_number
            loan_status_event = CustomerEvent.query.filter(
                CustomerEvent.customer_id == offer.customer_id,
                CustomerEvent.event_source == 'LOS', # Assuming LOS provides final status
                CustomerEvent.event_details.op('->>')('loan_application_number') == offer.loan_application_number,
                CustomerEvent.event_type.in_(['LOAN_REJECTED', 'LOAN_EXPIRED']) # Hypothetical event types
            ).first()

            if loan_status_event:
                offers_to_expire.add(offer)
                logger.info(f"Offer {offer.offer_id} expired due to LAN {offer.loan_application_number} status.")

        if not offers_to_expire:
            logger.info("No offers found to expire.")
            return 0

        updated_count = 0
        for offer in offers_to_expire:
            if offer.offer_status != 'Expired': # Avoid re-updating already expired offers
                offer.offer_status = 'Expired'
                offer.updated_at = datetime.now()
                db.session.add(offer)
                updated_count += 1

        try:
            db.session.commit()
            logger.info(f"Successfully expired {updated_count} offers.")
            return updated_count
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error updating expired offers: {e}")
            raise SQLAlchemyError("Failed to update expired offers due to a database error.") from e

    @staticmethod
    def get_customer_offers(customer_id: str, status: str = None, include_history: bool = False) -> list[Offer]:
        """
        Retrieves offers for a given customer.

        Args:
            customer_id (str): The UUID of the customer.
            status (str, optional): Filter by offer status (e.g., 'Active', 'Expired').
                                    Defaults to None (all statuses).
            include_history (bool, optional): If True, includes all offers available for the customer.
                                              If False, filters for offers that are 'Active'
                                              or have been updated/ended within the last 6 months.
                                              (FR18: offer history for past 06 months).
                                              Note: The data cleanup task is expected to remove
                                              offers older than 6 months.

        Returns:
            list[Offer]: A list of Offer objects.
        """
        logger = current_app.logger
        logger.info(f"Retrieving offers for customer {customer_id} (status: {status}, history: {include_history}).")

        query = Offer.query.filter_by(customer_id=customer_id)

        if status:
            query = query.filter_by(offer_status=status)

        # FR18: maintain offer history for the past 06 months.
        # Assuming data cleanup ensures offers older than 6 months are removed.
        # If include_history is False, we filter for currently relevant offers.
        if not include_history:
            six_months_ago = datetime.now() - timedelta(days=6 * 30) # Approximate 6 months
            query = query.filter(
                or_(
                    Offer.offer_status == 'Active',
                    Offer.updated_at >= six_months_ago,
                    Offer.offer_end_date >= six_months_ago.date() # Also include offers that ended recently
                )
            )

        try:
            offers = query.order_by(Offer.created_at.desc()).all()
            logger.info(f"Found {len(offers)} offers for customer {customer_id}.")
            return offers
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving offers for customer {customer_id}: {e}")
            raise SQLAlchemyError("Failed to retrieve offers due to a database error.") from e