import uuid
from datetime import datetime
from sqlalchemy import or_
from flask import current_app

# Assuming these are defined in backend/extensions.py and backend/models.py
# For a real Flask application, ensure these imports are correctly configured.
from backend.extensions import db
from backend.models import Customer, Offer, OfferHistory

class DeduplicationService:
    def __init__(self):
        """
        Initializes the DeduplicationService.
        """
        pass

    def _find_existing_customer_by_identifiers(self, mobile_number, pan_number, aadhaar_number, ucid_number):
        """
        Finds an existing customer based on direct identifiers (mobile, pan, aadhaar, ucid).
        Prioritizes existing Customer 360 ID if available, otherwise picks the oldest match.
        (FR3, FR5)
        """
        filters = []
        if mobile_number:
            filters.append(Customer.mobile_number == mobile_number)
        if pan_number:
            filters.append(Customer.pan_number == pan_number)
        if aadhaar_number:
            filters.append(Customer.aadhaar_number == aadhaar_number)
        if ucid_number:
            filters.append(Customer.ucid_number == ucid_number)

        if not filters:
            return None

        # Search for customers matching any of the provided identifiers
        # Order by customer_360_id presence (non-null first) to prioritize live book matches (FR5)
        # Then by created_at to pick the oldest if multiple non-360 matches exist
        existing_customer = Customer.query.filter(or_(*filters)).order_by(
            Customer.customer_360_id.isnot(None).desc(),
            Customer.created_at.asc()
        ).first()

        return existing_customer

    def _update_customer_profile(self, customer, new_data):
        """
        Updates an existing customer's profile with new data, prioritizing non-null values
        from the new data to fill gaps in existing customer data.
        (FR7)
        """
        updated = False
        if new_data.get('mobile_number') and not customer.mobile_number:
            customer.mobile_number = new_data['mobile_number']
            updated = True
        if new_data.get('pan_number') and not customer.pan_number:
            customer.pan_number = new_data['pan_number']
            updated = True
        if new_data.get('aadhaar_number') and not customer.aadhaar_number:
            customer.aadhaar_number = new_data['aadhaar_number']
            updated = True
        if new_data.get('ucid_number') and not customer.ucid_number:
            customer.ucid_number = new_data['ucid_number']
            updated = True
        if new_data.get('segment') and customer.segment != new_data['segment']:
            customer.segment = new_data['segment']
            updated = True
        if new_data.get('is_dnd') is not None and customer.is_dnd != new_data['is_dnd']:
            customer.is_dnd = new_data['is_dnd']
            updated = True
        
        # Merge attributes JSONB
        if new_data.get('attributes'):
            if customer.attributes is None:
                customer.attributes = new_data['attributes']
                updated = True
            else:
                # Iterate through new attributes and update/add to existing
                for key, value in new_data['attributes'].items():
                    if customer.attributes.get(key) != value:
                        customer.attributes[key] = value
                        updated = True

        if updated:
            customer.updated_at = datetime.now()
            db.session.add(customer) # Mark for update

        return customer

    def _handle_offer_deduplication(self, customer_id, new_offer_data):
        """
        Handles deduplication logic for a new offer against existing offers for a customer.
        Marks existing offers as duplicate/inactive if superseded by a new offer.
        Returns the original_offer_id if the new offer is a duplicate, and a boolean flag.
        (FR6, FR7, FR18)
        """
        new_offer_type = new_offer_data.get('offer_type')
        new_source_offer_id = new_offer_data.get('source_offer_id')
        new_loan_application_number = new_offer_data.get('loan_application_number')
        new_source_system = new_offer_data.get('source_system')

        # Find existing active offers for this customer
        existing_active_offers = Offer.query.filter_by(
            customer_id=customer_id,
            offer_status='Active'
        ).all()

        original_offer_id_for_new_offer = None
        is_new_offer_duplicate = False
        offers_to_deactivate = []

        for existing_offer in existing_active_offers:
            # FR6: Deduplicate Top-up loan offers only against other Top-up offers
            if new_offer_type == 'Top-up' and existing_offer.offer_type == 'Top-up':
                # Assuming a match if source_offer_id or loan_application_number matches for Top-up
                if (new_source_offer_id and existing_offer.source_offer_id == new_source_offer_id) or \
                   (new_loan_application_number and existing_offer.loan_application_number == new_loan_application_number):
                    current_app.logger.info(f"Top-up offer (new: {new_source_offer_id}) duplicates existing Top-up offer {existing_offer.offer_id}. Marking old as inactive.")
                    offers_to_deactivate.append(existing_offer)
                    original_offer_id_for_new_offer = existing_offer.offer_id
                    is_new_offer_duplicate = True
                    break # Found a direct duplicate, no need to check further for this new offer

            # FR18: 'Enrich' offers logic
            if new_offer_type == 'Enrich':
                # If journey not started (no LAN or LAN is not active/expired), mark previous offer as Duplicate
                # Assuming 'journey started' means loan_application_number is present and associated with an active journey.
                # The BRD states "if journey started, do not flow to CDP" for Enrich offers.
                # This implies the ingestion layer should ideally filter such offers.
                # If an 'Enrich' offer *does* flow and the existing offer has an active LAN, we do not supersede.
                # Otherwise, if no LAN or LAN is not active, we mark the old offer as duplicate.
                if not existing_offer.loan_application_number: # No LAN means journey not started for this offer
                    current_app.logger.info(f"Enrich offer for customer {customer_id} supersedes existing offer {existing_offer.offer_id} (no active journey). Marking old as inactive.")
                    offers_to_deactivate.append(existing_offer)
                    original_offer_id_for_new_offer = existing_offer.offer_id
                    is_new_offer_duplicate = True
                    break
                else:
                    current_app.logger.debug(f"Enrich offer received for customer {customer_id} with active journey ({existing_offer.loan_application_number}). Not marking old offer {existing_offer.offer_id} as duplicate.")
                    # If journey started, we don't mark the old offer as duplicate.
                    # The new 'Enrich' offer might still be created as a distinct offer if it's truly new.

            # General case: If a new offer from the same source system with the same source_offer_id
            # and same offer_type, it's considered a duplicate. (FR7)
            if new_source_offer_id and existing_offer.source_offer_id == new_source_offer_id and \
               new_source_system == existing_offer.source_system and \
               new_offer_type == existing_offer.offer_type:
                current_app.logger.info(f"New offer {new_source_offer_id} duplicates existing offer {existing_offer.offer_id}. Marking old as inactive.")
                offers_to_deactivate.append(existing_offer)
                original_offer_id_for_new_offer = existing_offer.offer_id
                is_new_offer_duplicate = True
                break

        # Deactivate identified old offers and record history
        for offer_to_deactivate in offers_to_deactivate:
            old_status = offer_to_deactivate.offer_status
            offer_to_deactivate.offer_status = 'Inactive'
            offer_to_deactivate.is_duplicate = True # Mark the old one as duplicate
            offer_to_deactivate.updated_at = datetime.now()
            db.session.add(offer_to_deactivate)

            # Record history for the deactivated offer
            history = OfferHistory(
                offer_id=offer_to_deactivate.offer_id,
                old_status=old_status,
                new_status='Inactive',
                change_reason=f"Superseded by new offer from {new_offer_data.get('source_system')}"
            )
            db.session.add(history)

        return original_offer_id_for_new_offer, is_new_offer_duplicate

    def deduplicate_customer_and_offer(self, customer_data, offer_data):
        """
        Main method to deduplicate customer and offer data.
        This method orchestrates finding/creating a unique customer profile
        and handling offer-level deduplication.
        (FR1, FR3, FR4)

        Args:
            customer_data (dict): Dictionary containing customer details
                                  (e.g., mobile_number, pan_number, aadhaar_number, ucid_number, segment, is_dnd, attributes).
            offer_data (dict): Dictionary containing offer details
                               (e.g., source_offer_id, offer_type, offer_status, propensity,
                               loan_application_number, valid_until, source_system, channel).

        Returns:
            tuple: A tuple containing the Customer object and the newly created/updated Offer object.
                   Returns (None, None) if an unrecoverable error occurs.
        Raises:
            Exception: If any database operation or critical logic fails.
        """
        mobile_number = customer_data.get('mobile_number')
        pan_number = customer_data.get('pan_number')
        aadhaar_number = customer_data.get('aadhaar_number')
        ucid_number = customer_data.get('ucid_number')
        loan_application_number = offer_data.get('loan_application_number') # FR3: LAN is also a dedupe key

        customer = None
        customer_id = None

        try:
            # Step 1: Find existing customer by direct identifiers (Mobile, PAN, Aadhaar, UCID)
            customer = self._find_existing_customer_by_identifiers(
                mobile_number, pan_number, aadhaar_number, ucid_number
            )

            # Step 2: If not found by direct identifiers, try finding customer via existing loan application number
            # This covers cases where a new offer comes in for an existing customer identified only by LAN.
            if not customer and loan_application_number:
                existing_offer_by_lan = Offer.query.filter_by(
                    loan_application_number=loan_application_number
                ).first()
                if existing_offer_by_lan:
                    customer = Customer.query.get(existing_offer_by_lan.customer_id)
                    if customer:
                        current_app.logger.info(f"Found existing customer {customer.customer_id} via loan application number {loan_application_number}.")
                        # Update customer profile with new data if found via LAN
                        customer = self._update_customer_profile(customer, customer_data)

            # Step 3: If still no customer found, create a new one
            if not customer:
                customer_id = uuid.uuid4()
                customer = Customer(
                    customer_id=customer_id,
                    mobile_number=mobile_number,
                    pan_number=pan_number,
                    aadhaar_number=aadhaar_number,
                    ucid_number=ucid_number,
                    segment=customer_data.get('segment'),
                    is_dnd=customer_data.get('is_dnd', False),
                    attributes=customer_data.get('attributes', {})
                )
                db.session.add(customer)
                current_app.logger.info(f"Created new customer {customer_id}.")
            else:
                customer_id = customer.customer_id
                current_app.logger.info(f"Using existing customer {customer_id} for incoming data.")


            # Step 4: Handle offer deduplication and creation
            # This function determines if the new offer duplicates an existing one
            # and marks the old one as inactive/duplicate if necessary.
            original_offer_id_for_new_offer, is_new_offer_duplicate = self._handle_offer_deduplication(
                customer_id, offer_data
            )

            # Create the new offer record
            new_offer = Offer(
                offer_id=uuid.uuid4(),
                customer_id=customer_id,
                source_offer_id=offer_data.get('source_offer_id'),
                offer_type=offer_data.get('offer_type'),
                offer_status=offer_data.get('offer_status', 'Active'), # Default to Active
                propensity=offer_data.get('propensity'),
                loan_application_number=loan_application_number,
                valid_until=offer_data.get('valid_until'),
                source_system=offer_data.get('source_system'),
                channel=offer_data.get('channel'),
                is_duplicate=is_new_offer_duplicate,
                original_offer_id=original_offer_id_for_new_offer
            )
            db.session.add(new_offer)

            db.session.commit()
            current_app.logger.info(f"Deduplication and offer creation successful for customer {customer_id}, offer {new_offer.offer_id}.")
            return customer, new_offer

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Deduplication failed: {e}", exc_info=True)
            raise # Re-raise the exception after rollback to be handled by calling context