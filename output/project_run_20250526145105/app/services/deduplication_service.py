import logging
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.customer import Customer
from app.models.offer import Offer
from app.models.offer_history import OfferHistory
from app.schemas.customer import CustomerCreate
from app.schemas.offer import OfferCreate
from app.core.config import settings

logger = logging.getLogger(__name__)

class DeduplicationService:
    def __init__(self, db: Session):
        self.db = db

    def _find_existing_customer_in_cdp(self, customer_data: CustomerCreate) -> Customer | None:
        """
        Finds an existing customer in the CDP database based on unique identifiers.
        """
        query = self.db.query(Customer)
        conditions = []

        if customer_data.mobile_number:
            conditions.append(Customer.mobile_number == customer_data.mobile_number)
        if customer_data.pan_number:
            conditions.append(Customer.pan_number == customer_data.pan_number)
        if customer_data.aadhaar_ref_number:
            conditions.append(Customer.aadhaar_ref_number == customer_data.aadhaar_ref_number)
        if customer_data.ucid_number:
            conditions.append(Customer.ucid_number == customer_data.ucid_number)
        if customer_data.previous_loan_app_number:
            conditions.append(Customer.previous_loan_app_number == customer_data.previous_loan_app_number)

        if not conditions:
            logger.warning("No identifiable information provided for customer lookup.")
            return None

        # Use or_ to find a match on any of the provided unique identifiers
        existing_customer = query.filter(or_(*conditions)).first()
        return existing_customer

    def _check_customer_360_live_book(self, customer_data: CustomerCreate) -> bool:
        """
        Simulates/integrates with Customer 360 live book check (FR5).
        In a real scenario, this would involve an API call to Customer 360.
        For MVP, we might assume C360 data is mirrored or a simple placeholder.
        Returns True if customer exists in C360, False otherwise.
        """
        if not settings.ENABLE_CUSTOMER_360_CHECK:
            logger.debug("Customer 360 check is disabled by configuration.")
            return False

        # Placeholder for actual Customer 360 integration.
        # This could be a call to an external service or a query to a mirrored C360 table.
        # For demonstration, let's assume a customer is in C360 if their mobile number
        # starts with '999' or PAN is 'C360PAN'.
        if (customer_data.mobile_number and customer_data.mobile_number.startswith('999')) or \
           (customer_data.pan_number and customer_data.pan_number == 'C360PAN'):
            logger.info(f"Customer (mobile: {customer_data.mobile_number}, PAN: {customer_data.pan_number}) found in simulated C360 live book.")
            return True
        return False

    def _handle_offer_precedence(self, new_offer: OfferCreate, existing_offers: list[Offer]) -> tuple[str, Offer | None]:
        """
        Applies offer precedence rules (FR25-FR32) to determine if a new offer
        should be accepted, rejected, or if an existing offer should be updated.

        Returns:
            tuple[str, Offer | None]: A tuple where the first element is a status string
            ('ACCEPT_NEW', 'REJECT_NEW_EXISTING_PREVAILS', 'MARK_PREVIOUS_DUPLICATE_ACCEPT_NEW',
            'MARK_PREVIOUS_EXPIRED_ACCEPT_NEW')
            and the second element is the existing offer to be modified if applicable.
        """
        active_existing_offers = [offer for offer in existing_offers if offer.offer_status == 'Active']
        existing_product_types = {offer.product_type for offer in active_existing_offers}

        # FR29-FR32: Strict rejection rules based on existing product types
        # FR29: If customer has existing Preapproved/E-aggregator/Prospect and new is Loyalty/Top-up/EL/Preapproved/E-aggregator/Prospect
        if ('Preapproved' in existing_product_types or 'E-aggregator' in existing_product_types or 'Prospect' in existing_product_types) and \
           new_offer.product_type in ['Loyalty', 'Top-up', 'Employee Loan', 'Preapproved', 'E-aggregator', 'Prospect']:
            logger.info(f"FR29: Rejecting new offer '{new_offer.product_type}' due to existing pre-approved/prospect/E-aggregator offer.")
            return 'REJECT_NEW_EXISTING_PREVAILS', None

        # FR30: If customer has existing Employee Loan and new is Loyalty/Top-up/Preapproved/E-aggregator/Prospect
        if 'Employee Loan' in existing_product_types and \
           new_offer.product_type in ['Loyalty', 'Top-up', 'Preapproved', 'E-aggregator', 'Prospect']:
            logger.info(f"FR30: Rejecting new offer '{new_offer.product_type}' due to existing Employee Loan offer.")
            return 'REJECT_NEW_EXISTING_PREVAILS', None

        # FR31: If customer has existing TW Loyalty and new is Top-up/Employee loan/Preapproved/E-aggregator/Prospect
        if 'Loyalty' in existing_product_types and \
           new_offer.product_type in ['Top-up', 'Employee Loan', 'Preapproved', 'E-aggregator', 'Prospect']:
            logger.info(f"FR31: Rejecting new offer '{new_offer.product_type}' due to existing TW Loyalty offer.")
            return 'REJECT_NEW_EXISTING_PREVAILS', None

        # FR32: If customer has existing Prospect and new is TW Loyalty/Top-up/Employee loan/Pre-approved E-aggregator
        if 'Prospect' in existing_product_types and \
           new_offer.product_type in ['Loyalty', 'Top-up', 'Employee Loan', 'Preapproved', 'E-aggregator']:
            logger.info(f"FR32: Rejecting new offer '{new_offer.product_type}' due to existing Prospect offer.")
            return 'REJECT_NEW_EXISTING_PREVAILS', None

        # FR6: Deduplicate Top-up loan offers only against other Top-up offers.
        if new_offer.product_type == 'Top-up':
            for existing_offer in active_existing_offers:
                if existing_offer.product_type == 'Top-up':
                    logger.info(f"FR6: Rejecting new Top-up offer due to existing active Top-up offer {existing_offer.offer_id}.")
                    return 'REJECT_NEW_EXISTING_PREVAILS', None

        # FR20, FR21: Enrich offer logic
        if new_offer.offer_type == 'Enrich':
            # Assuming an 'Enrich' offer targets an existing active offer of the same product type.
            target_existing_offer = next(
                (o for o in active_existing_offers if o.product_type == new_offer.product_type),
                None
            )
            if target_existing_offer:
                if target_existing_offer.is_journey_started:
                    logger.info(f"FR21: Rejecting Enrich offer as existing offer {target_existing_offer.offer_id} journey has started.")
                    return 'REJECT_NEW_EXISTING_PREVAILS', None
                else:
                    logger.info(f"FR20: Accepting Enrich offer, marking previous offer {target_existing_offer.offer_id} as Duplicate.")
                    return 'MARK_PREVIOUS_DUPLICATE_ACCEPT_NEW', target_existing_offer
            else:
                logger.warning(f"Enrich offer received for '{new_offer.product_type}' but no active offer to enrich found. Treating as new.")
                # If no offer to enrich, it's effectively a new offer of type 'Enrich'
                return 'ACCEPT_NEW', None

        # FR25-FR28: Precedence rules based on journey status and source
        existing_cleag_insta_offers = [
            o for o in active_existing_offers if o.product_type in ['Insta', 'E-aggregator']
        ]
        existing_preapproved_prospect_offers = [
            o for o in active_existing_offers if o.product_type in ['Preapproved', 'Prospect']
        ]
        existing_twl_topup_el_offers = [
            o for o in active_existing_offers if o.product_type in ['Loyalty', 'Top-up', 'Employee Loan']
        ]

        # FR28: If existing TWL/Top-up/EL and new is CLEAG/Insta, existing prevails.
        if existing_twl_topup_el_offers and new_offer.product_type in ['Insta', 'E-aggregator']:
            logger.info(f"FR28: Rejecting new CLEAG/Insta offer due to existing TWL/Top-up/EL offer.")
            return 'REJECT_NEW_EXISTING_PREVAILS', None

        # FR25: If existing Pre-approved/Prospect (no journey) and new is CLEAG/Insta, new prevails, old expires.
        if new_offer.product_type in ['Insta', 'E-aggregator']:
            for existing_pa_offer in existing_preapproved_prospect_offers:
                if not existing_pa_offer.is_journey_started:
                    logger.info(f"FR25: Accepting new CLEAG/Insta offer, marking existing pre-approved offer {existing_pa_offer.offer_id} as Expired.")
                    return 'MARK_PREVIOUS_EXPIRED_ACCEPT_NEW', existing_pa_offer

        # FR26: If existing Pre-approved/Prospect (journey started) and new is CLEAG/Insta, existing prevails.
        if new_offer.product_type in ['Insta', 'E-aggregator']:
            for existing_pa_offer in existing_preapproved_prospect_offers:
                if existing_pa_offer.is_journey_started:
                    logger.info(f"FR26: Rejecting new CLEAG/Insta offer due to existing pre-approved offer {existing_pa_offer.offer_id} with journey started.")
                    return 'REJECT_NEW_EXISTING_PREVAILS', None

        # FR27: If existing CLEAG/Insta and new is CLEAG/Insta, existing prevails.
        if new_offer.product_type in ['Insta', 'E-aggregator'] and existing_cleag_insta_offers:
            logger.info(f"FR27: Rejecting new CLEAG/Insta offer due to existing CLEAG/Insta offer.")
            return 'REJECT_NEW_EXISTING_PREVAILS', None

        # FR4: Deduplication within all Consumer Loan (CL) products.
        # If the new offer is of the same product type as an existing active offer,
        # and no other rule has handled it, it's likely a duplicate.
        if new_offer.product_type in existing_product_types:
            logger.info(f"FR4: Rejecting new offer '{new_offer.product_type}' as an active offer of the same product type already exists.")
            return 'REJECT_NEW_EXISTING_PREVAILS', None

        # If no specific rejection or modification rule applies, accept the new offer.
        logger.info(f"New offer '{new_offer.product_type}' accepted as no conflicting precedence rule applied.")
        return 'ACCEPT_NEW', None

    def deduplicate_and_process_offer(self, customer_data: CustomerCreate, offer_data: OfferCreate) -> dict:
        """
        Main method to perform deduplication and process a new customer offer.
        """
        if customer_data.dnd_status: # FR34
            logger.info(f"Customer {customer_data.mobile_number} is DND. Offer rejected.")
            return {
                "status": "rejected",
                "message": "Customer is marked as Do Not Disturb (DND).",
                "customer_id": None,
                "offer_id": None
            }

        existing_customer = self._find_existing_customer_in_cdp(customer_data)
        
        if not existing_customer:
            # If not found in CDP, check Customer 360 live book (FR5)
            is_in_c360_live_book = self._check_customer_360_live_book(customer_data)
            if is_in_c360_live_book:
                # If found in C360 but not CDP, we consider them an existing customer.
                # A new customer record will be created in CDP, but subsequent offer
                # processing will treat them as an existing entity.
                logger.info(f"Customer identified in Customer 360 live book. Proceeding to create new CDP record for existing C360 customer.")
                # Create the customer record in CDP based on C360 presence
                new_customer_id = uuid4()
                existing_customer = Customer(**customer_data.model_dump(exclude_unset=True), customer_id=new_customer_id)
                self.db.add(existing_customer)
                self.db.flush() # Flush to get customer_id before creating offer
                logger.info(f"New CDP customer record {existing_customer.customer_id} created based on C360 match.")
            else:
                # Truly a new customer, not found in CDP or C360
                logger.info("No existing customer found in CDP or C360. Creating new customer and offer.")
                new_customer_id = uuid4()
                new_customer_db = Customer(**customer_data.model_dump(exclude_unset=True), customer_id=new_customer_id)
                self.db.add(new_customer_db)
                self.db.flush()
                existing_customer = new_customer_db # Set existing_customer to the newly created one

        # Now, existing_customer is guaranteed to be a Customer object (either found or newly created)
        customer_id_to_use = existing_customer.customer_id

        # Retrieve all active offers for this customer (if any)
        existing_active_offers = self.db.query(Offer).filter(
            Offer.customer_id == customer_id_to_use,
            Offer.offer_status == 'Active'
        ).all()

        precedence_status, offer_to_modify = self._handle_offer_precedence(offer_data, existing_active_offers)

        if precedence_status == 'REJECT_NEW_EXISTING_PREVAILS':
            logger.info(f"New offer rejected due to existing offer precedence for customer {customer_id_to_use}.")
            return {
                "status": "rejected",
                "message": "New offer rejected: Existing offer takes precedence.",
                "customer_id": customer_id_to_use,
                "offer_id": None
            }
        elif precedence_status == 'MARK_PREVIOUS_DUPLICATE_ACCEPT_NEW':
            if offer_to_modify:
                # Update the status of the previous offer to 'Duplicate'
                offer_to_modify.offer_status = 'Duplicate'
                offer_to_modify.updated_at = datetime.now()
                self.db.add(offer_to_modify)
                # Add to offer history
                self.db.add(offer_to_modify.to_history(
                    old_status='Active',
                    new_status='Duplicate',
                    reason='New Enrich offer accepted (FR20)'
                ))
                self.db.flush()
                logger.info(f"Previous offer {offer_to_modify.offer_id} marked as Duplicate for customer {customer_id_to_use}.")

            # Create the new offer
            new_offer_db = Offer(**offer_data.model_dump(exclude_unset=True), customer_id=customer_id_to_use, offer_id=uuid4())
            self.db.add(new_offer_db)
            self.db.commit()
            self.db.refresh(new_offer_db)
            logger.info(f"New offer {new_offer_db.offer_id} created for customer {customer_id_to_use}.")
            return {
                "status": "accepted_previous_marked_duplicate",
                "message": "New offer accepted, previous offer marked as duplicate.",
                "customer_id": customer_id_to_use,
                "offer_id": new_offer_db.offer_id
            }
        elif precedence_status == 'MARK_PREVIOUS_EXPIRED_ACCEPT_NEW':
            if offer_to_modify:
                # Update the status of the previous offer to 'Expired'
                offer_to_modify.offer_status = 'Expired'
                offer_to_modify.updated_at = datetime.now()
                self.db.add(offer_to_modify)
                # Add to offer history
                self.db.add(offer_to_modify.to_history(
                    old_status='Active',
                    new_status='Expired',
                    reason='New CLEAG/Insta offer accepted (FR25)'
                ))
                self.db.flush()
                logger.info(f"Previous offer {offer_to_modify.offer_id} marked as Expired for customer {customer_id_to_use}.")

            # Create the new offer
            new_offer_db = Offer(**offer_data.model_dump(exclude_unset=True), customer_id=customer_id_to_use, offer_id=uuid4())
            self.db.add(new_offer_db)
            self.db.commit()
            self.db.refresh(new_offer_db)
            logger.info(f"New offer {new_offer_db.offer_id} created for customer {customer_id_to_use}.")
            return {
                "status": "accepted_previous_marked_expired",
                "message": "New offer accepted, previous offer marked as expired.",
                "customer_id": customer_id_to_use,
                "offer_id": new_offer_db.offer_id
            }
        else: # 'ACCEPT_NEW'
            # Create the new offer for the existing customer
            new_offer_db = Offer(**offer_data.model_dump(exclude_unset=True), customer_id=customer_id_to_use, offer_id=uuid4())
            self.db.add(new_offer_db)
            self.db.commit()
            self.db.refresh(new_offer_db)
            logger.info(f"New offer {new_offer_db.offer_id} created for customer {customer_id_to_use}.")
            return {
                "status": "accepted_for_existing_customer",
                "message": "New offer accepted for existing customer.",
                "customer_id": customer_id_to_use,
                "offer_id": new_offer_db.offer_id
            }