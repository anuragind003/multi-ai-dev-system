import datetime
from sqlalchemy import and_, or_
from app.extensions import db
from app.models import Offer, Customer, CustomerEvent # Assuming Customer and CustomerEvent models are defined

class OfferLogic:
    """
    Encapsulates business logic related to offer management, including
    attribution, status updates, and modification checks.
    """

    def __init__(self):
        pass

    def apply_attribution_logic(self, customer_id: str) -> Offer | None:
        """
        FR20: Applies attribution logic to determine which offer/channel prevails
        when a customer has multiple offers or comes through different channels.

        Prioritization (example, based on FR16 and general business sense):
        1. Offers with 'New-new' type
        2. Offers with 'New-old' type
        3. Offers with 'Fresh' type
        4. Offers with 'Enrich' type
        5. If types are equal, prioritize by latest offer_start_date.
        """
        customer_offers = db.session.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.offer_status == 'Active'
        ).all()

        if not customer_offers:
            return None

        # Define a simple priority for offer types (higher value = higher priority)
        offer_type_priority = {
            'New-new': 4,
            'New-old': 3,
            'Fresh': 2,
            'Enrich': 1
        }

        # Sort offers based on defined priority
        # This is a simplified example. Real attribution logic can be very complex
        # and might involve more attributes like offer value, product type, etc.
        customer_offers.sort(key=lambda offer: (
            offer_type_priority.get(offer.offer_type, 0),
            offer.offer_start_date if offer.offer_start_date else datetime.date.min,
            # Add more criteria here if available, e.g., offer value, channel priority
        ), reverse=True)

        # The first offer after sorting is considered the prevailing one
        prevailing_offer = customer_offers[0]

        # Optional: If only one offer should be active, deactivate others.
        # This depends on specific business rules not fully detailed.
        # For now, we just identify the prevailing one.
        # for offer in customer_offers:
        #     if offer.offer_id != prevailing_offer.offer_id and offer.offer_status == 'Active':
        #         offer.offer_status = 'Inactive'
        #         db.session.add(offer)
        # db.session.commit() # Commit if changes are made here

        return prevailing_offer

    def update_offer_statuses(self) -> int:
        """
        FR15: The system shall maintain flags for Offer statuses: Active, Inactive, and Expired.
        FR37: Expiry logic for non-journey started customers based on offer end dates.
        FR38: Mark offers as expired if LAN validity post loan application journey start date is over.

        This function is intended to be called periodically (e.g., daily by a scheduled job).
        Returns the number of offers updated.
        """
        current_date = datetime.date.today()
        offers_to_update = []

        # Rule 1: Offers for non-journey started customers expire if offer_end_date is past (FR37)
        expired_offers_no_journey = db.session.query(Offer).filter(
            Offer.loan_application_number.is_(None),
            Offer.offer_status == 'Active',
            Offer.offer_end_date < current_date
        ).all()

        for offer in expired_offers_no_journey:
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.datetime.now(datetime.timezone.utc)
            offers_to_update.append(offer)

        # Rule 2: Offers with started loan application journey expire if LAN validity is over (FR38)
        # Interpretation: If the associated loan application has reached a terminal state (Rejected/Expired)
        # OR if the offer_end_date is past and the application is not in a successful state.
        offers_with_journey = db.session.query(Offer).filter(
            Offer.loan_application_number.isnot(None),
            Offer.offer_status == 'Active'
        ).all()

        for offer in offers_with_journey:
            # Check for terminal application events (Rejected, Expired)
            terminal_event_types = ['APP_STAGE_REJECTED', 'APP_STAGE_EXPIRED', 'CONVERSION_REJECTED']
            terminal_event = db.session.query(CustomerEvent).filter(
                CustomerEvent.customer_id == offer.customer_id,
                CustomerEvent.event_source == 'LOS', # Assuming LOS provides final status
                CustomerEvent.event_details.op('->>')('loan_application_number').astext == offer.loan_application_number,
                CustomerEvent.event_type.in_(terminal_event_types)
            ).first()

            if terminal_event:
                offer.offer_status = 'Expired'
                offer.updated_at = datetime.datetime.now(datetime.timezone.utc)
                offers_to_update.append(offer)
            elif offer.offer_end_date and offer.offer_end_date < current_date:
                # If offer_end_date is past, and no terminal event, check for successful conversion.
                # If no successful conversion, then expire.
                successful_event_types = ['APP_STAGE_APPROVED', 'CONVERSION_SUCCESS']
                successful_event = db.session.query(CustomerEvent).filter(
                    CustomerEvent.customer_id == offer.customer_id,
                    CustomerEvent.event_source == 'LOS',
                    CustomerEvent.event_details.op('->>')('loan_application_number').astext == offer.loan_application_number,
                    CustomerEvent.event_type.in_(successful_event_types)
                ).first()

                if not successful_event:
                    offer.offer_status = 'Expired'
                    offer.updated_at = datetime.datetime.now(datetime.timezone.utc)
                    offers_to_update.append(offer)

        if offers_to_update:
            db.session.bulk_save_objects(offers_to_update)
            db.session.commit()
            return len(offers_to_update)
        return 0

    def can_modify_offer(self, offer_id: str) -> bool:
        """
        FR13: The system shall prevent modification of customer offers with started loan application journeys
              until the loan application is either expired or rejected.
        """
        offer = db.session.query(Offer).filter(Offer.offer_id == offer_id).first()

        if not offer:
            return False # Offer not found

        if not offer.loan_application_number:
            return True # No loan journey started, can modify

        # Check if the associated loan application is in a terminal state (Expired or Rejected)
        terminal_event_types = ['APP_STAGE_REJECTED', 'APP_STAGE_EXPIRED', 'CONVERSION_REJECTED']

        terminal_event_exists = db.session.query(CustomerEvent).filter(
            CustomerEvent.customer_id == offer.customer_id,
            CustomerEvent.event_source == 'LOS',
            CustomerEvent.event_details.op('->>')('loan_application_number').astext == offer.loan_application_number,
            CustomerEvent.event_type.in_(terminal_event_types)
        ).first()

        if terminal_event_exists:
            return True # Loan application is expired or rejected, so offer can be modified
        else:
            return False # Loan application journey has started and is not yet expired/rejected

    def get_offer_history(self, customer_id: str, months: int = 6) -> list[Offer]:
        """
        FR18: The system shall maintain offer history for the past 06 months for reference purposes.
        NFR3: The system shall retain offer history data for 06 months.
        """
        # Using datetime.timedelta(days=months * 30) is an approximation.
        # For more precision, consider calendar months or specific date calculations.
        # Using timezone.utc for consistency with database timestamps.
        six_months_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=months * 30)

        offers_history = db.session.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.created_at >= six_months_ago
        ).order_by(Offer.created_at.desc()).all()

        return offers_history

    def get_customer_active_offers(self, customer_id: str) -> list[Offer]:
        """
        Retrieves all active offers for a given customer.
        """
        active_offers = db.session.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.offer_status == 'Active'
        ).all()
        return active_offers

    def create_or_update_offer(self, customer_id: str, offer_data: dict) -> Offer:
        """
        Creates a new offer or updates an existing one for a customer.
        This function would be called after deduplication and other checks.
        It incorporates the can_modify_offer logic.
        """
        offer_id = offer_data.get('offer_id')
        offer = None

        if offer_id:
            offer = db.session.query(Offer).filter(Offer.offer_id == offer_id).first()
            if offer and not self.can_modify_offer(str(offer.offer_id)):
                raise ValueError("Cannot modify offer as loan application journey has started and is active.")

        if offer:
            # Update existing offer
            for key, value in offer_data.items():
                # Only update fields that are part of the Offer model and not primary/foreign keys
                if hasattr(offer, key) and key not in ['offer_id', 'customer_id', 'created_at', 'updated_at']:
                    setattr(offer, key, value)
            offer.updated_at = datetime.datetime.now(datetime.timezone.utc)
        else:
            # Create new offer
            offer = Offer(
                customer_id=customer_id,
                offer_type=offer_data.get('offer_type'),
                offer_status=offer_data.get('offer_status', 'Active'), # Default to Active
                propensity_flag=offer_data.get('propensity_flag'),
                offer_start_date=offer_data.get('offer_start_date'),
                offer_end_date=offer_data.get('offer_end_date'),
                loan_application_number=offer_data.get('loan_application_number'),
                attribution_channel=offer_data.get('attribution_channel')
            )
            # created_at and updated_at will be set by default in the model

        db.session.add(offer)
        db.session.commit()
        db.session.refresh(offer) # Refresh to get default values like UUID and timestamps
        return offer