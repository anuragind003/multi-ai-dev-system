import uuid
from datetime import datetime
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Customer, CustomerEvent, Offer

class EventService:
    @staticmethod
    def record_customer_event(
        customer_id: uuid.UUID,
        event_type: str,
        event_source: str,
        event_details: dict = None
    ) -> CustomerEvent:
        """
        Records a customer event in the database.
        Checks for DND status for specific event sources (Moengage, LOS) as per FR21.
        """
        logger = current_app.logger
        try:
            customer = Customer.query.get(customer_id)
            if not customer:
                logger.warning(f"Customer with ID {customer_id} not found for event recording.")
                raise ValueError(f"Customer with ID {customer_id} not found.")

            # FR21: Store event data from Moengage and LOS in the LTFS Offer CDP, avoiding DND Customers.
            # This implies that if a customer is DND, we should not store events from these sources
            # that are primarily for communication or campaign tracking.
            if customer.is_dnd and event_source in ['Moengage', 'LOS']:
                logger.info(
                    f"Skipping event recording for DND customer {customer_id} "
                    f"from source '{event_source}' for event type '{event_type}'."
                )
                # Return None to indicate that the event was intentionally skipped due to DND.
                return None

            event = CustomerEvent(
                customer_id=customer_id,
                event_type=event_type,
                event_source=event_source,
                event_details=event_details if event_details is not None else {}
            )
            db.session.add(event)
            db.session.commit()
            logger.info(f"Recorded event '{event_type}' for customer {customer_id} from '{event_source}'.")
            return event
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error recording event for customer {customer_id}: {e}")
            raise
        except ValueError as e:
            logger.error(f"Validation error recording event: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error recording event for customer {customer_id}: {e}")
            raise

    @staticmethod
    def handle_realtime_eligibility_event(
        mobile_number: str,
        loan_application_number: str,
        eligibility_status: str,
        offer_id: str
    ) -> CustomerEvent:
        """
        Processes real-time eligibility check data from Insta/E-aggregators.
        (FR9, FR10: Modify existing APIs to insert data into CDP DB)
        """
        logger = current_app.logger
        try:
            customer = Customer.query.filter_by(mobile_number=mobile_number).first()
            if not customer:
                logger.warning(f"Customer with mobile number {mobile_number} not found for eligibility event. "
                               f"This customer should ideally be created via Lead Generation API first.")
                raise ValueError(f"Customer with mobile number {mobile_number} not found.")

            # Find the associated offer using offer_id
            try:
                offer_uuid = uuid.UUID(offer_id)
            except ValueError:
                raise ValueError(f"Invalid offer_id format: {offer_id}")

            offer = Offer.query.get(offer_uuid)

            if not offer or offer.customer_id != customer.customer_id:
                logger.warning(f"Offer {offer_id} not found or does not belong to customer {customer.customer_id} "
                               f"for eligibility event.")
                raise ValueError(f"Offer {offer_id} not found or mismatch for customer {customer.customer_id}.")

            event_details = {
                "loan_application_number": loan_application_number,
                "eligibility_status": eligibility_status,
                "offer_id": str(offer.offer_id)
            }

            # Record the event
            event = EventService.record_customer_event(
                customer_id=customer.customer_id,
                event_type="ELIGIBILITY_CHECK",
                event_source="E-Aggregator", # Generic source for Insta/E-aggregators
                event_details=event_details
            )

            # Update offer status if applicable (FR15)
            # This logic might be more complex based on business rules.
            if eligibility_status.upper() == "ELIGIBLE" and offer.offer_status == "Inactive":
                offer.offer_status = "Active" # Or 'Eligible' if that's a defined status
                db.session.add(offer)
                db.session.commit()
                logger.info(f"Updated offer {offer.offer_id} status to 'Active' based on eligibility.")
            elif eligibility_status.upper() == "NOT_ELIGIBLE" and offer.offer_status == "Active":
                offer.offer_status = "Inactive" # Or 'Rejected'
                db.session.add(offer)
                db.session.commit()
                logger.info(f"Updated offer {offer.offer_id} status to 'Inactive' based on ineligibility.")

            return event
        except ValueError as e:
            logger.error(f"Data validation error for eligibility event: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing eligibility event for mobile {mobile_number}: {e}")
            raise

    @staticmethod
    def handle_realtime_status_event(
        loan_application_number: str,
        application_stage: str,
        status_details: dict,
        event_timestamp_str: str
    ) -> CustomerEvent:
        """
        Processes real-time loan application status updates from Insta/E-aggregators/LOS.
        (FR9, FR10: Modify existing APIs to insert data into CDP DB)
        (FR22: Event data shall include application stages from LOS)
        (FR13, FR38: Prevent modification of offers with started loan journeys, mark expired)
        """
        logger = current_app.logger
        try:
            # Convert timestamp string to datetime object
            try:
                event_timestamp = datetime.fromisoformat(event_timestamp_str)
            except ValueError:
                raise ValueError(f"Invalid event_timestamp format: {event_timestamp_str}. Expected ISO format.")

            # Find the associated offer using loan_application_number
            offer = Offer.query.filter_by(loan_application_number=loan_application_number).first()

            if not offer:
                logger.warning(f"Offer with loan application number {loan_application_number} not found for status update.")
                raise ValueError(f"Offer with loan application number {loan_application_number} not found.")

            customer_id = offer.customer_id
            if not customer_id:
                logger.error(f"Offer {offer.offer_id} has no associated customer_id.")
                raise ValueError(f"Offer {offer.offer_id} has no associated customer_id.")

            event_details = {
                "loan_application_number": loan_application_number,
                "application_stage": application_stage,
                "status_details": status_details,
                "event_timestamp_source": event_timestamp_str # Store original string for lineage
            }

            # Record the event
            # Event source is 'LOS' as per FR22 for application stages
            event = EventService.record_customer_event(
                customer_id=customer_id,
                event_type=f"APP_STAGE_{application_stage.upper().replace(' ', '_')}", # e.g., APP_STAGE_LOGIN
                event_source="LOS",
                event_details=event_details
            )

            # FR13: Prevent modification of customer offers with started loan application journeys
            # until the loan application is either expired or rejected.
            # FR38: The system shall mark offers as expired within the offers data if the Loan Application Number (LAN) validity post loan application journey start date is over.
            if application_stage.lower() in ["rejected", "expired", "cancelled", "withdrawn"]:
                offer.offer_status = "Expired" # FR15: Maintain flags for Offer statuses: Active, Inactive, and Expired
                db.session.add(offer)
                db.session.commit()
                logger.info(f"Offer {offer.offer_id} marked as 'Expired' due to application stage: {application_stage}.")
            elif application_stage.lower() == "approved":
                # If an offer is approved, it might transition to a 'Converted' or 'Fulfilled' status.
                # This needs more specific BRD clarification.
                pass # No direct status change for 'Approved' without more specific instruction

            return event
        except ValueError as e:
            logger.error(f"Data validation error for status event: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing status event for LAN {loan_application_number}: {e}")
            raise

    @staticmethod
    def handle_moengage_event(
        customer_id: uuid.UUID,
        event_type: str, # e.g., SMS_SENT, SMS_DELIVERED, SMS_CLICK
        event_details: dict
    ) -> CustomerEvent:
        """
        Handles events specifically from Moengage.
        (FR21, FR22: Event data shall include SMS sent, SMS delivered, SMS click)
        """
        logger = current_app.logger
        try:
            # The record_customer_event already handles DND for 'Moengage' source
            event = EventService.record_customer_event(
                customer_id=customer_id,
                event_type=event_type,
                event_source="Moengage",
                event_details=event_details
            )
            return event
        except Exception as e:
            logger.error(f"Error handling Moengage event for customer {customer_id}: {e}")
            raise

    @staticmethod
    def handle_los_conversion_event(
        customer_id: uuid.UUID,
        loan_application_number: str,
        conversion_details: dict
    ) -> CustomerEvent:
        """
        Handles conversion events from LOS.
        (FR22: Event data shall include conversions from LOS/Moengage)
        """
        logger = current_app.logger
        try:
            event_details = {
                "loan_application_number": loan_application_number,
                "conversion_details": conversion_details
            }
            # The record_customer_event already handles DND for 'LOS' source
            event = EventService.record_customer_event(
                customer_id=customer_id,
                event_type="CONVERSION",
                event_source="LOS",
                event_details=event_details
            )
            # Optionally, update offer status to 'Converted' or similar (FR15)
            offer = Offer.query.filter_by(loan_application_number=loan_application_number, customer_id=customer_id).first()
            if offer:
                # Assuming 'Converted' is a valid offer status in the system
                offer.offer_status = "Converted"
                db.session.add(offer)
                db.session.commit()
                logger.info(f"Offer {offer.offer_id} marked as 'Converted' due to LOS conversion event.")
            return event
        except Exception as e:
            logger.error(f"Error handling LOS conversion event for customer {customer_id}: {e}")
            raise