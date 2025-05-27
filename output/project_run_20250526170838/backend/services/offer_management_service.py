from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from backend.models import Customer, Offer, Event  # Assuming these models are defined in backend/models.py


class OfferManagementService:
    """
    Service class for managing customer offers and their lifecycle.
    Handles offer creation, updates, status changes, history, and attribution logic.
    """

    def __init__(self, db_session: Session):
        """
        Initializes the OfferManagementService with a SQLAlchemy database session.

        Args:
            db_session: The SQLAlchemy session object for database interactions.
        """
        self.db = db_session

    def create_or_update_offer(self, customer_id: str, offer_data: dict) -> Offer:
        """
        Creates a new offer or updates an existing one for a customer.
        Ensures offer types, statuses, and propensity are correctly set.
        (FR16, FR17, FR18)

        Args:
            customer_id: The ID of the customer for whom to create/update the offer.
            offer_data: A dictionary containing offer details.
                        Expected keys: 'offer_id' (optional), 'offer_type', 'offer_status',
                        'propensity', 'start_date', 'end_date', 'channel'.

        Returns:
            The created or updated Offer object.

        Raises:
            ValueError: If the customer with the given ID is not found.
            PermissionError: If an attempt is made to modify an offer linked to an
                             active loan application journey (FR14).
        """
        customer = self.db.query(Customer).filter_by(customer_id=customer_id).first()
        if not customer:
            raise ValueError(f"Customer with ID '{customer_id}' not found.")

        offer_id = offer_data.get('offer_id')
        offer = None
        if offer_id:
            offer = self.db.query(Offer).filter_by(offer_id=offer_id, customer_id=customer_id).first()

        if offer:
            # FR14: Prevent modification if loan application journey started and not expired/rejected
            # This check is broad (customer-level). If FR14 implies offer-specific journey,
            # then the schema needs to link offers to loan application numbers.
            if self._is_loan_journey_started_and_active(customer_id):
                raise PermissionError(
                    "Cannot modify offer: customer has an active loan application journey."
                )

            offer.offer_type = offer_data.get('offer_type', offer.offer_type)
            offer.offer_status = offer_data.get('offer_status', offer.offer_status)
            offer.propensity = offer_data.get('propensity', offer.propensity)
            offer.start_date = offer_data.get('start_date', offer.start_date)
            offer.end_date = offer_data.get('end_date', offer.end_date)
            offer.channel = offer_data.get('channel', offer.channel)
            offer.updated_at = datetime.utcnow()
        else:
            # Create new offer
            offer = Offer(
                customer_id=customer_id,
                offer_type=offer_data.get('offer_type', 'Fresh'),
                offer_status=offer_data.get('offer_status', 'Active'),
                propensity=offer_data.get('propensity'),
                start_date=offer_data.get('start_date', date.today()),
                end_date=offer_data.get('end_date', date.today() + timedelta(days=30)),
                channel=offer_data.get('channel')
            )
            self.db.add(offer)

        self.db.commit()
        self.db.refresh(offer)
        return offer

    def _is_loan_journey_started_and_active(self, customer_id: str) -> bool:
        """
        Helper method to check if a customer has an active loan application journey.
        (Related to FR14, FR43)

        This implementation assumes that an active journey is indicated by recent
        'LOAN_LOGIN' or 'APPLICATION_STARTED' events that have not been followed
        by 'EXPIRED' or 'REJECTED' events for the same loan application.
        The current schema lacks explicit `loan_application_number` on `Offer`
        and detailed status in `Event.event_details` for a robust check.
        This is a simplified check.

        Args:
            customer_id: The ID of the customer.

        Returns:
            True if an active loan journey is detected, False otherwise.
        """
        # Check for recent events indicating a started journey
        # Assuming 'event_details' might contain 'loan_application_number' and 'status'
        # For a more robust check, a dedicated `LoanApplication` table would be ideal.
        recent_journey_events = self.db.query(Event).filter(
            Event.customer_id == customer_id,
            Event.event_type.in_(['LOAN_LOGIN', 'APPLICATION_STARTED', 'BUREAU_CHECK', 'OFFER_DETAILS_VIEWED']),
            Event.event_timestamp >= datetime.utcnow() - timedelta(days=90)  # Arbitrary recent period (e.g., 3 months)
        ).order_by(Event.event_timestamp.desc()).first()

        if not recent_journey_events:
            return False

        # Further logic would be needed here to check if the *specific* loan application
        # associated with these events is still active (not expired/rejected).
        # This would involve parsing `event_details` or joining with a `LoanApplication` table.
        # For now, if any such recent event exists, we consider a journey active.
        return True

    def update_offer_statuses_batch(self):
        """
        Updates offer statuses based on expiry dates and LAN validity.
        This method is intended to be run as a scheduled task.
        (FR41, FR43)
        """
        today = date.today()
        updated_count = 0

        # Subquery to identify customer_ids that have an active loan journey
        customers_with_active_journeys_subquery = self.db.query(Event.customer_id).filter(
            Event.event_type.in_(['LOAN_LOGIN', 'APPLICATION_STARTED']),
            Event.event_timestamp >= datetime.utcnow() - timedelta(days=90)  # Recent journey
        ).distinct().subquery()

        # FR41: Mark offers as expired based on offer end dates for non-journey started customers.
        offers_to_expire_by_date = self.db.query(Offer).filter(
            Offer.offer_status == 'Active',
            Offer.end_date < today,
            ~Offer.customer_id.in_(customers_with_active_journeys_subquery)  # Exclude customers with active journeys
        ).all()

        for offer in offers_to_expire_by_date:
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.utcnow()
            updated_count += 1

        # FR43: Mark offers as expired for journey started customers whose LAN validity is over.
        # This requires a `loan_application_number` field on the `offers` table or a robust
        # way to link offers to loan applications and check their validity.
        # Given the current schema, this is a conceptual placeholder.
        # A more complete implementation would involve:
        # 1. Identifying offers linked to a specific LAN.
        # 2. Checking the validity status of that LAN (e.g., from LOS data in `events` or a dedicated table).
        # For now, this part is implicitly handled by the exclusion in the above query,
        # meaning offers for customers with active journeys are *not* expired by `end_date`.
        # The actual LAN validity check would be a separate process or part of the
        # `_is_loan_journey_started_and_active` if it were more sophisticated.

        self.db.commit()
        return updated_count

    def check_and_replenish_offers(self):
        """
        Checks for and replenishes new offers for non-journey started customers
        whose previous offers have expired. (FR42)
        This method is intended to be run as a scheduled task after expiry updates.
        """
        replenished_count = 0

        # Subquery to identify customer_ids that currently have at least one 'Active' offer
        customers_with_active_offers_subquery = self.db.query(Offer.customer_id).filter(
            Offer.offer_status == 'Active'
        ).distinct().subquery()

        # Subquery to identify customer_ids that have an active loan journey
        customers_with_active_journeys_subquery = self.db.query(Event.customer_id).filter(
            Event.event_type.in_(['LOAN_LOGIN', 'APPLICATION_STARTED']),
            Event.event_timestamp >= datetime.utcnow() - timedelta(days=90)
        ).distinct().subquery()

        # Identify customers who do NOT have any active offers AND do NOT have an active loan journey
        customers_to_replenish = self.db.query(Customer).filter(
            ~Customer.customer_id.in_(customers_with_active_offers_subquery),
            ~Customer.customer_id.in_(customers_with_active_journeys_subquery)
        ).all()

        for customer in customers_to_replenish:
            # Replenish new offers (FR42)
            # This logic would typically involve calling an analytics service or applying
            # specific business rules to generate a relevant offer.
            try:
                new_offer_data = {
                    'offer_type': 'Fresh',
                    'offer_status': 'Active',
                    'propensity': 'Medium',  # Placeholder value
                    'start_date': date.today(),
                    'end_date': date.today() + timedelta(days=60),  # New offer valid for 60 days
                    'channel': 'System_Replenishment'
                }
                self.create_or_update_offer(customer.customer_id, new_offer_data)
                replenished_count += 1
            except Exception as e:
                # Log the error, but continue processing other customers
                print(f"Error replenishing offer for customer {customer.customer_id}: {e}")

        self.db.commit()
        return replenished_count

    def get_offer_history(self, customer_id: str, months: int = 6) -> list[Offer]:
        """
        Retrieves offer history for a customer for the past 'months'.
        (FR19, NFR8)

        Args:
            customer_id: The ID of the customer.
            months: The number of months for which to retrieve history. Defaults to 6.

        Returns:
            A list of Offer objects, ordered by creation date (descending).
        """
        history_start_date = datetime.utcnow() - timedelta(days=months * 30)  # Approximate
        offers = self.db.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.created_at >= history_start_date
        ).order_by(Offer.created_at.desc()).all()
        return offers

    def apply_attribution_logic(self, customer_id: str) -> Offer | None:
        """
        Applies attribution logic to determine which channel/offer prevails
        when a customer has multiple interactions or existing offers. (FR21)

        This implementation prioritizes offers based on a predefined channel hierarchy
        and then by the most recently updated active offer.

        Args:
            customer_id: The ID of the customer.

        Returns:
            The prevailing Offer object, or None if no active offers are found.
        """
        active_offers = self.db.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.offer_status == 'Active'
        ).all()

        if not active_offers:
            return None

        # Example channel hierarchy (needs to be defined by business, Q21)
        # Lower number means higher priority.
        channel_priority = {
            'Insta': 1,
            'E-aggregator': 2,
            'Preapproved': 3,
            'Loyalty': 4,
            'Offermart': 5,
            'System_Replenishment': 99  # Lowest priority for system-generated offers
        }

        def get_channel_priority_value(offer):
            return channel_priority.get(offer.channel, 100)  # Default low priority for unknown channels

        # Sort by channel priority (ascending) then by updated_at (descending)
        # This ensures higher priority channels come first, and within the same channel,
        # the most recent offer prevails.
        sorted_offers = sorted(active_offers,
                               key=lambda o: (get_channel_priority_value(o), o.updated_at),
                               reverse=True)

        prevailing_offer = sorted_offers[0]
        return prevailing_offer

    def get_customer_offers(self, customer_id: str) -> list[Offer]:
        """
        Retrieves all offers for a given customer, regardless of status.

        Args:
            customer_id: The ID of the customer.

        Returns:
            A list of Offer objects.
        """
        offers = self.db.query(Offer).filter_by(customer_id=customer_id).all()
        return offers

    def get_offer_details(self, offer_id: str) -> Offer | None:
        """
        Retrieves details for a specific offer by its ID.

        Args:
            offer_id: The ID of the offer.

        Returns:
            The Offer object if found, otherwise None.
        """
        offer = self.db.query(Offer).filter_by(offer_id=offer_id).first()
        return offer