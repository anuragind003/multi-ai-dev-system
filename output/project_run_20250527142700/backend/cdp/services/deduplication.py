import uuid
from datetime import datetime
from sqlalchemy import or_
from flask import current_app

# Assuming these are defined in backend/extensions.py and backend/models.py
from backend.extensions import db
from backend.models import Customer, Offer, OfferHistory, Event


class DeduplicationService:
    def __init__(self):
        """
        Initializes the DeduplicationService.
        """
        pass

    def _find_existing_customer(self, customer_identifiers, offer_loan_application_number=None):
        """
        Finds an existing customer based on Mobile number, Pan number, Aadhaar reference number,
        UCID number, or previous loan application number. (FR3)
        `customer_identifiers` is a dict containing potential customer identifying fields.
        `offer_loan_application_number` is the LAN from the incoming offer.
        """
        mobile_number = customer_identifiers.get('mobile_number')
        pan_number = customer_identifiers.get('pan_number')
        aadhaar_number = customer_identifiers.get('aadhaar_number')
        ucid_number = customer_identifiers.get('ucid_number')

        conditions = []
        if mobile_number:
            conditions.append(Customer.mobile_number == mobile_number)
        if pan_number:
            conditions.append(Customer.pan_number == pan_number)
        if aadhaar_number:
            conditions.append(Customer.aadhaar_number == aadhaar_number)
        if ucid_number:
            conditions.append(Customer.ucid_number == ucid_number)

        existing_customer = None
        if conditions:
            existing_customer = Customer.query.filter(or_(*conditions)).first()

        # If no customer found by direct identifiers, check by loan application number from the offer
        if not existing_customer and offer_loan_application_number:
            # Find an offer with this LAN, then get its customer
            offer_with_lan = Offer.query.filter_by(loan_application_number=offer_loan_application_number).first()
            if offer_with_lan:
                existing_customer = Customer.query.get(offer_with_lan.customer_id)
                if existing_customer:
                    current_app.logger.info(f"Found existing customer {existing_customer.customer_id} via loan application number {offer_loan_application_number}.")

        return existing_customer

    def _update_customer_profile(self, existing_customer, new_customer_data):
        """
        Updates an existing customer's profile with new data, prioritizing non-null values.
        This helps in consolidating a 'single profile view' (FR1).
        """
        updated = False
        # Only update if new data is present and existing field is null or different (for segment)
        if new_customer_data.get('mobile_number') and not existing_customer.mobile_number:
            existing_customer.mobile_number = new_customer_data['mobile_number']
            updated = True
        if new_customer_data.get('pan_number') and not existing_customer.pan_number:
            existing_customer.pan_number = new_customer_data['pan_number']
            updated = True
        if new_customer_data.get('aadhaar_number') and not existing_customer.aadhaar_number:
            existing_customer.aadhaar_number = new_customer_data['aadhaar_number']
            updated = True
        if new_customer_data.get('ucid_number') and not existing_customer.ucid_number:
            existing_customer.ucid_number = new_customer_data['ucid_number']
            updated = True
        
        # Update segment if new data is provided and different
        if new_customer_data.get('segment') and new_customer_data['segment'] != existing_customer.segment:
            existing_customer.segment = new_customer_data['segment']
            updated = True
        
        # Update customer_360_id if new data is provided and existing is null
        if new_customer_data.get('customer_360_id') and not existing_customer.customer_360_id:
            existing_customer.customer_360_id = new_customer_data['customer_360_id']
            updated = True
        
        # Update DND status if provided
        if 'is_dnd' in new_customer_data and new_customer_data['is_dnd'] != existing_customer.is_dnd:
            existing_customer.is_dnd = new_customer_data['is_dnd']
            updated = True

        # Merge attributes (JSONB field)
        if new_customer_data.get('attributes'):
            if existing_customer.attributes is None:
                existing_customer.attributes = {}
            # Simple merge, new values overwrite old ones
            for key, value in new_customer_data['attributes'].items():
                if existing_customer.attributes.get(key) != value:
                    existing_customer.attributes[key] = value
                    updated = True

        if updated:
            existing_customer.updated_at = datetime.now()
            db.session.add(existing_customer) # Mark for update
            current_app.logger.info(f"Customer {existing_customer.customer_id} profile updated.")
        return existing_customer

    def _log_offer_history(self, offer_id, old_status, new_status, reason):
        """
        Logs changes to offer status in the offer_history table.
        FR20: The CDP system shall maintain Offer history for the past 6 months.
        """
        history_entry = OfferHistory(
            history_id=uuid.uuid4(),
            offer_id=offer_id,
            old_status=old_status,
            new_status=new_status,
            change_reason=reason
        )
        db.session.add(history_entry)
        current_app.logger.debug(f"Logged offer history for offer {offer_id}: {old_status} -> {new_status} ({reason})")

    def _handle_top_up_offer_deduplication(self, customer_id, new_offer_id, new_offer_type):
        """
        FR6: The CDP system shall deduplicate Top-up loan offers only against other Top-up offers, removing matches.
        This implies if a new Top-up offer comes in, existing active Top-up offers for the same customer should be marked inactive/duplicate.
        """
        if new_offer_type == 'Top-up':
            # Find existing active Top-up offers for this customer, excluding the new offer itself
            existing_top_up_offers = Offer.query.filter(
                Offer.customer_id == customer_id,
                Offer.offer_type == 'Top-up',
                Offer.offer_status == 'Active',
                Offer.offer_id != new_offer_id # Exclude the current new offer
            ).all()

            for offer in existing_top_up_offers:
                old_status = offer.offer_status
                offer.offer_status = 'Inactive' # Or 'Expired' or 'Duplicate' based on exact business rule
                offer.is_duplicate = True
                offer.original_offer_id = new_offer_id # Link to the new prevailing offer
                offer.updated_at = datetime.now()
                db.session.add(offer)
                self._log_offer_history(offer.offer_id, old_status, offer.offer_status, 'Top-up offer superseded by new Top-up offer')
                current_app.logger.info(f"Marked old Top-up offer {offer.offer_id} as inactive/duplicate for customer {customer_id}.")
            return True
        return False

    def _is_journey_started(self, customer_id, loan_application_number):
        """
        Helper to determine if a loan application journey has started for a given LAN.
        This would typically involve checking the 'events' table for specific journey stages.
        FR18: if journey started, do not flow to CDP.
        FR13: prevent modification of customer offers with an active loan application journey.
        """
        if not loan_application_number:
            return False

        # Check for any 'journey started' events for this LAN
        # Example event types: 'JOURNEY_LOGIN', 'BUREAU_CHECK', 'OFFER_DETAILS', 'EKYC', etc.
        # This is a simplified check. A more robust solution might involve a state machine or specific flags.
        journey_events = Event.query.filter(
            Event.customer_id == customer_id,
            Event.event_type.in_(['JOURNEY_LOGIN', 'EKYC_ACHIEVED', 'DISBURSEMENT']), # Example journey events
            Event.event_details.op('->>')('loan_application_number') == loan_application_number # Assuming LAN is in event_details
        ).first()

        # Also check if there's an active offer with this LAN, which might imply a journey is active/pending
        active_offer_with_lan = Offer.query.filter(
            Offer.customer_id == customer_id,
            Offer.loan_application_number == loan_application_number,
            Offer.offer_status == 'Active' # Assuming active means journey started or pending
        ).first()

        return journey_events is not None or active_offer_with_lan is not None

    def _handle_enrich_offer(self, customer_id, new_offer_id, new_offer_data):
        """
        FR18: The CDP system shall handle 'Enrich' offers: if journey not started, flow to CDP and mark previous offer as Duplicate;
              if journey started, do not flow to CDP.
        Returns True if the new offer should be processed/saved, False otherwise.
        """
        if new_offer_data.get('offer_type') == 'Enrich':
            loan_application_number = new_offer_data.get('loan_application_number')
            
            if self._is_journey_started(customer_id, loan_application_number):
                current_app.logger.warning(f"Enrich offer for customer {customer_id} with LAN {loan_application_number} not processed: Journey already started (FR18).")
                return False # Indicate that the offer should not be processed/saved
            else:
                # If journey not started, mark previous active offers as Duplicate
                previous_offers = Offer.query.filter(
                    Offer.customer_id == customer_id,
                    Offer.offer_status == 'Active',
                    Offer.offer_id != new_offer_id # Exclude the current new offer
                ).all()

                for offer in previous_offers:
                    old_status = offer.offer_status
                    offer.offer_status = 'Inactive' # Or 'Expired' or 'Duplicate'
                    offer.is_duplicate = True
                    offer.original_offer_id = new_offer_id # Link to the new prevailing offer
                    offer.updated_at = datetime.now()
                    db.session.add(offer)
                    self._log_offer_history(offer.offer_id, old_status, offer.offer_status, 'Enrich offer superseded by new Enrich offer')
                    current_app.logger.info(f"Marked old offer {offer.offer_id} as inactive/duplicate for customer {customer_id} due to Enrich offer.")
                return True # Indicate that the offer should be processed/saved
        return True # Not an enrich offer, proceed

    def process_incoming_data(self, customer_data, offer_data):
        """
        Main method to process incoming customer and offer data, applying deduplication logic.
        FR1: Perform customer deduplication to create a single profile view.
        FR3: Deduplicate customers based on Mobile, Pan, Aadhaar, UCID, or previous loan application number.
        FR4: Apply deduplication logic across all Consumer Loan products.
        FR5: Deduplicate against 'live book' (Customer 360 data).
        FR7: Update old offers with new real-time data.
        """
        current_app.logger.info(f"Processing incoming data for customer: {customer_data.get('mobile_number')}, offer: {offer_data.get('source_offer_id')}")

        try:
            # 1. Find existing customer based on identifiers (including LAN from offer_data)
            existing_customer = self._find_existing_customer(
                customer_identifiers=customer_data,
                offer_loan_application_number=offer_data.get('loan_application_number')
            )

            customer_id = None
            if existing_customer:
                customer_id = existing_customer.customer_id
                current_app.logger.info(f"Found existing customer: {customer_id}. Updating profile.")
                # Update existing customer profile with any new/missing data
                self._update_customer_profile(existing_customer, customer_data)
            else:
                # No existing customer found, create a new one
                customer_id = uuid.uuid4()
                new_customer = Customer(
                    customer_id=customer_id,
                    mobile_number=customer_data.get('mobile_number'),
                    pan_number=customer_data.get('pan_number'),
                    aadhaar_number=customer_data.get('aadhaar_number'),
                    ucid_number=customer_data.get('ucid_number'),
                    customer_360_id=customer_data.get('customer_360_id'),
                    is_dnd=customer_data.get('is_dnd', False),
                    segment=customer_data.get('segment'),
                    attributes=customer_data.get('attributes', {})
                )
                db.session.add(new_customer)
                current_app.logger.info(f"Created new customer: {customer_id}.")

            # 2. Determine if the incoming offer is an update to an existing one or a new offer
            incoming_source_offer_id = offer_data.get('source_offer_id')
            existing_offer_for_update = None
            if incoming_source_offer_id:
                existing_offer_for_update = Offer.query.filter(
                    Offer.customer_id == customer_id,
                    Offer.source_offer_id == incoming_source_offer_id
                ).first()

            current_offer_id = existing_offer_for_update.offer_id if existing_offer_for_update else uuid.uuid4()
            
            # Add the determined offer_id to offer_data for use in handlers
            # This is crucial for handlers to link superseded offers to the new one
            offer_data['offer_id'] = current_offer_id 

            # 3. Handle offer-specific deduplication and processing rules
            # Check for Enrich offer first, as it might prevent further processing
            should_process_offer = self._handle_enrich_offer(customer_id, current_offer_id, offer_data)

            if not should_process_offer:
                # If enrich offer was not processed, rollback any changes made in this transaction
                # (e.g., customer updates, other offer status changes)
                db.session.rollback() 
                return {"status": "skipped", "message": "Enrich offer not processed due to active journey."}

            # Handle Top-up offer deduplication
            self._handle_top_up_offer_deduplication(customer_id, current_offer_id, offer_data.get('offer_type'))

            # 4. Create or Update the incoming offer
            if existing_offer_for_update:
                # Update existing offer (FR7)
                current_app.logger.info(f"Updating existing offer {existing_offer_for_update.offer_id} for customer {customer_id}.")
                old_status = existing_offer_for_update.offer_status
                
                # Update fields from incoming offer_data
                existing_offer_for_update.offer_type = offer_data.get('offer_type', existing_offer_for_update.offer_type)
                existing_offer_for_update.offer_status = offer_data.get('offer_status', existing_offer_for_update.offer_status)
                existing_offer_for_update.propensity = offer_data.get('propensity', existing_offer_for_update.propensity)
                existing_offer_for_update.loan_application_number = offer_data.get('loan_application_number', existing_offer_for_update.loan_application_number)
                existing_offer_for_update.valid_until = offer_data.get('valid_until', existing_offer_for_update.valid_until)
                existing_offer_for_update.source_system = offer_data.get('source_system', existing_offer_for_update.source_system)
                existing_offer_for_update.channel = offer_data.get('channel', existing_offer_for_update.channel)
                # is_duplicate and original_offer_id are managed by specific deduplication rules,
                # so we don't blindly overwrite them from incoming data unless explicitly required.
                existing_offer_for_update.updated_at = datetime.now()
                db.session.add(existing_offer_for_update)
                
                if old_status != existing_offer_for_update.offer_status:
                    self._log_offer_history(existing_offer_for_update.offer_id, old_status, existing_offer_for_update.offer_status, 'Offer updated with new real-time data')
                offer_id_result = existing_offer_for_update.offer_id
            else:
                # Create new offer
                new_offer = Offer(
                    offer_id=current_offer_id,
                    customer_id=customer_id,
                    source_offer_id=incoming_source_offer_id,
                    offer_type=offer_data.get('offer_type'),
                    offer_status=offer_data.get('offer_status', 'Active'), # Default to Active if not provided
                    propensity=offer_data.get('propensity'),
                    loan_application_number=offer_data.get('loan_application_number'),
                    valid_until=offer_data.get('valid_until'),
                    source_system=offer_data.get('source_system'),
                    channel=offer_data.get('channel'),
                    is_duplicate=False, # Initially not duplicate, will be set by specific rules if needed
                    original_offer_id=None
                )
                db.session.add(new_offer)
                self._log_offer_history(new_offer.offer_id, None, new_offer.offer_status, 'New offer created')
                current_app.logger.info(f"Created new offer: {current_offer_id} for customer {customer_id}.")
                offer_id_result = new_offer.offer_id

            db.session.commit()
            return {"status": "success", "customer_id": str(customer_id), "offer_id": str(offer_id_result)}

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error during deduplication process: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}