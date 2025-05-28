import uuid
from datetime import datetime
from sqlalchemy import or_
from flask import current_app
from sqlalchemy.exc import IntegrityError

# Assuming these are defined in backend/src/extensions.py and backend/src/models.py
from backend.src.extensions import db
from backend.src.models import Customer, Offer, OfferHistory


class DeduplicationService:
    def __init__(self):
        """
        Initializes the DeduplicationService.
        """
        pass

    def _find_existing_customer(self, mobile_number=None, pan_number=None, aadhaar_number=None, ucid_number=None, loan_application_number=None):
        """
        Helper method to find an existing customer based on multiple identifiers.
        FR3: Deduplicate customers based on Mobile number, Pan number, Aadhaar reference number, UCID number,
             or previous loan application number.
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

        customer = None
        if filters:
            customer = Customer.query.filter(or_(*filters)).first()

        # If no customer found by direct identifiers, try by loan_application_number
        # This implies that a loan_application_number can uniquely identify a customer.
        if not customer and loan_application_number:
            # Find an offer with this loan_application_number
            existing_offer_by_lan = Offer.query.filter_by(loan_application_number=loan_application_number).first()
            if existing_offer_by_lan:
                customer = Customer.query.get(existing_offer_by_lan.customer_id)
                if customer:
                    current_app.logger.info(f"Customer found via loan_application_number: {customer.customer_id}")

        return customer

    def _handle_top_up_deduplication(self, new_offer_data, existing_customer_id):
        """
        FR6: Deduplicate Top-up loan offers only against other Top-up offers, removing matches.
        This implies marking existing Top-up offers as inactive/duplicate if a new one comes in.
        Returns a list of offers that were inactivated.
        """
        inactivated_offers = []
        # Assuming 'offer_type' can be 'Top-up' or a similar indicator.
        if new_offer_data.get('offer_type') == 'Top-up':
            existing_top_up_offers = Offer.query.filter(
                Offer.customer_id == existing_customer_id,
                Offer.offer_type == 'Top-up',
                Offer.offer_status == 'Active'
            ).all()

            for offer in existing_top_up_offers:
                offer.offer_status = 'Inactive'
                offer.is_duplicate = True
                history = OfferHistory(
                    offer_id=offer.offer_id,
                    old_status='Active',
                    new_status='Inactive',
                    change_reason='New Top-up offer received, marked existing as duplicate.'
                )
                db.session.add(history)
                inactivated_offers.append(offer)
            current_app.logger.info(f"Marked {len(existing_top_up_offers)} existing Top-up offers as Inactive for customer {existing_customer_id}")
        return inactivated_offers

    def process_e_aggregator_offer(self, payload):
        """
        Processes real-time lead, eligibility, or status data from E-aggregators.
        Performs deduplication logic and inserts/updates customer and offer data.

        Functional Requirements Addressed:
        - FR1: Single profile view.
        - FR3: Deduplication based on Mobile, PAN, Aadhaar, UCID, or previous loan application number.
        - FR4: Deduplication across all Consumer Loan products.
        - FR5: Deduplication against 'live book' (Customer 360 data).
        - FR6: Deduplicate Top-up loan offers only against other Top-up offers.
        - FR7: Update old offers with new real-time data.
        - FR13: Prevent modification if active loan application journey.
        - FR18: Handle 'Enrich' offers.
        """
        customer_data = payload.get('customer_data', {})
        offer_data = payload.get('offer_data', {})

        mobile_number = customer_data.get('mobile_number')
        pan_number = customer_data.get('pan_number')
        aadhaar_number = customer_data.get('aadhaar_number')
        ucid_number = customer_data.get('ucid_number')
        loan_application_number = offer_data.get('loan_application_number')

        existing_customer = self._find_existing_customer(
            mobile_number=mobile_number,
            pan_number=pan_number,
            aadhaar_number=aadhaar_number,
            ucid_number=ucid_number,
            loan_application_number=loan_application_number
        )

        try:
            offers_to_link_to_new_offer = [] # To store offers that will point to the new offer as their original_offer_id

            if existing_customer:
                current_app.logger.info(f"Existing customer found: {existing_customer.customer_id}")

                # Update existing customer attributes if new data is more complete/different
                if customer_data.get('segment') and existing_customer.segment != customer_data['segment']:
                    existing_customer.segment = customer_data['segment']
                if customer_data.get('is_dnd') is not None and existing_customer.is_dnd != customer_data['is_dnd']:
                    existing_customer.is_dnd = customer_data['is_dnd']
                if customer_data.get('attributes'):
                    # Merge or replace attributes. For simplicity, let's merge.
                    existing_customer.attributes.update(customer_data['attributes'])
                existing_customer.updated_at = datetime.now()

                # FR6: Handle Top-up loan offers deduplication
                top_up_inactivated = self._handle_top_up_deduplication(offer_data, existing_customer.customer_id)
                offers_to_link_to_new_offer.extend(top_up_inactivated)

                new_offer_type = offer_data.get('offer_type')
                new_offer_source_id = offer_data.get('source_offer_id')

                # Check if this exact offer already exists for this customer (e.g., re-ingestion)
                existing_specific_offer = Offer.query.filter_by(
                    customer_id=existing_customer.customer_id,
                    source_offer_id=new_offer_source_id,
                    source_system=offer_data.get('source_system')
                ).first()

                if existing_specific_offer:
                    current_app.logger.info(f"Offer {new_offer_source_id} already exists for customer {existing_customer.customer_id}. Updating status/details.")
                    existing_specific_offer.offer_status = offer_data.get('offer_status', existing_specific_offer.offer_status)
                    existing_specific_offer.propensity = offer_data.get('propensity', existing_specific_offer.propensity)
                    existing_specific_offer.valid_until = datetime.fromisoformat(offer_data['valid_until']) if 'valid_until' in offer_data else existing_specific_offer.valid_until
                    existing_specific_offer.updated_at = datetime.now()
                    db.session.commit()
                    return existing_customer.customer_id, "Existing offer updated successfully."

                # FR18: Handle 'Enrich' offers
                active_journey_offers = None
                if new_offer_type == 'Enrich':
                    # Check if customer has an active loan application journey (FR13)
                    # An active journey is defined by an offer with a non-null LAN and 'Active' status.
                    active_journey_offers = Offer.query.filter(
                        Offer.customer_id == existing_customer.customer_id,
                        Offer.loan_application_number.isnot(None),
                        Offer.offer_status == 'Active'
                    ).first()

                    if active_journey_offers:
                        current_app.logger.info(f"Customer {existing_customer.customer_id} has an active loan journey (LAN: {active_journey_offers.loan_application_number}). 'Enrich' offer will not flow to CDP (FR13).")
                        return existing_customer.customer_id, "Enrich offer not processed due to active loan journey."
                    else:
                        # If journey not started, flow to CDP and mark previous offer as Duplicate (FR18)
                        previous_active_offers_for_enrich = Offer.query.filter(
                            Offer.customer_id == existing_customer.customer_id,
                            Offer.offer_status == 'Active'
                        ).all()
                        for prev_offer in previous_active_offers_for_enrich:
                            prev_offer.offer_status = 'Inactive'
                            prev_offer.is_duplicate = True
                            history = OfferHistory(
                                offer_id=prev_offer.offer_id,
                                old_status='Active',
                                new_status='Inactive',
                                change_reason=f"Marked duplicate by new 'Enrich' offer from {offer_data.get('source_system')}"
                            )
                            db.session.add(history)
                            offers_to_link_to_new_offer.append(prev_offer)
                        current_app.logger.info(f"Marked {len(previous_active_offers_for_enrich)} previous offers as Inactive/Duplicate for customer {existing_customer.customer_id} due to 'Enrich' offer.")

                # FR7: Update old offers in Analytics Offermart with new real-time data from CDP
                # This logic applies if the new offer is 'Fresh', 'New-new', or a processed 'Enrich' offer.
                if new_offer_type in ['Fresh', 'New-new'] or (new_offer_type == 'Enrich' and not active_journey_offers):
                    offers_to_inactivate_by_new_offer = Offer.query.filter(
                        Offer.customer_id == existing_customer.customer_id,
                        Offer.offer_status == 'Active',
                        Offer.offer_id != new_offer_source_id # Ensure we don't inactivate the current offer if it's an update
                    ).all()

                    for prev_offer in offers_to_inactivate_by_new_offer:
                        # Only inactivate if it's not a Top-up (handled separately)
                        # and not already marked for inactivation by Enrich logic (to avoid double counting/history)
                        if prev_offer not in offers_to_link_to_new_offer:
                            prev_offer.offer_status = 'Inactive'
                            prev_offer.is_duplicate = True
                            history = OfferHistory(
                                offer_id=prev_offer.offer_id,
                                old_status='Active',
                                new_status='Inactive',
                                change_reason=f"Superseded by new offer of type '{new_offer_type}' from {offer_data.get('source_system')}"
                            )
                            db.session.add(history)
                            offers_to_link_to_new_offer.append(prev_offer)
                    current_app.logger.info(f"Marked {len(offers_to_inactivate_by_new_offer)} previous offers as Inactive/Duplicate for customer {existing_customer.customer_id} due to new offer.")

                # Create a new offer linked to the existing customer
                new_offer_uuid = uuid.uuid4()
                new_offer = Offer(
                    offer_id=new_offer_uuid,
                    customer_id=existing_customer.customer_id,
                    source_offer_id=new_offer_source_id,
                    offer_type=new_offer_type,
                    offer_status=offer_data.get('offer_status', 'Active'), # Default to Active
                    propensity=offer_data.get('propensity'),
                    loan_application_number=loan_application_number,
                    valid_until=datetime.fromisoformat(offer_data['valid_until']) if 'valid_until' in offer_data else None,
                    source_system=offer_data.get('source_system'),
                    channel=offer_data.get('channel'),
                    is_duplicate=False # New offer is not a duplicate itself
                )
                db.session.add(new_offer)

                # Update original_offer_id for offers that were inactivated by this new offer
                for prev_offer in offers_to_link_to_new_offer:
                    prev_offer.original_offer_id = new_offer_uuid

                db.session.commit()
                current_app.logger.info(f"New offer {new_offer.offer_id} created for existing customer {existing_customer.customer_id}.")
                return existing_customer.customer_id, "Customer and offer updated/created successfully."

            else:
                current_app.logger.info("No existing customer found. Creating new customer and offer.")
                new_customer_uuid = uuid.uuid4()
                new_customer = Customer(
                    customer_id=new_customer_uuid,
                    mobile_number=mobile_number,
                    pan_number=pan_number,
                    aadhaar_number=aadhaar_number,
                    ucid_number=ucid_number,
                    segment=customer_data.get('segment'),
                    is_dnd=customer_data.get('is_dnd', False),
                    attributes=customer_data.get('attributes', {})
                )
                db.session.add(new_customer)
                db.session.flush() # Flush to get customer_id before committing

                new_offer_uuid = uuid.uuid4()
                new_offer = Offer(
                    offer_id=new_offer_uuid,
                    customer_id=new_customer.customer_id,
                    source_offer_id=offer_data.get('source_offer_id'),
                    offer_type=offer_data.get('offer_type'),
                    offer_status=offer_data.get('offer_status', 'Active'),
                    propensity=offer_data.get('propensity'),
                    loan_application_number=loan_application_number,
                    valid_until=datetime.fromisoformat(offer_data['valid_until']) if 'valid_until' in offer_data else None,
                    source_system=offer_data.get('source_system'),
                    channel=offer_data.get('channel'),
                    is_duplicate=False
                )
                db.session.add(new_offer)
                db.session.commit()
                current_app.logger.info(f"New customer {new_customer.customer_id} and offer {new_offer.offer_id} created.")
                return new_customer.customer_id, "New customer and offer created successfully."

        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Database Integrity Error during E-aggregator offer processing: {e}")
            return None, f"Integrity error: {e}"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error processing E-aggregator offer: {e}")
            return None, f"An unexpected error occurred: {e}"

    def deduplicate_offermart_data(self, customer_offers_batch):
        """
        Processes a batch of customer and offer data from Offermart for deduplication.
        This would typically be called by a scheduled job.

        Functional Requirements Addressed:
        - FR1: Single profile view.
        - FR3: Deduplication based on Mobile, PAN, Aadhaar, UCID, or previous loan application number.
        - FR4: Deduplication across all Consumer Loan products.
        - FR5: Deduplication against 'live book' (Customer 360 data).
        - FR6: Deduplicate Top-up loan offers only against other Top-up offers.
        - FR7: Update old offers with new real-time data.
        - FR13: Prevent modification if active loan application journey.
        - FR18: Handle 'Enrich' offers.
        """
        processed_results = []
        for item in customer_offers_batch:
            customer_data = item.get('customer_data', {})
            offer_data = item.get('offer_data', {})

            mobile_number = customer_data.get('mobile_number')
            pan_number = customer_data.get('pan_number')
            aadhaar_number = customer_data.get('aadhaar_number')
            ucid_number = customer_data.get('ucid_number')
            loan_application_number = offer_data.get('loan_application_number')

            existing_customer = self._find_existing_customer(
                mobile_number=mobile_number,
                pan_number=pan_number,
                aadhaar_number=aadhaar_number,
                ucid_number=ucid_number,
                loan_application_number=loan_application_number
            )

            try:
                offers_to_link_to_new_offer = []

                if existing_customer:
                    current_app.logger.info(f"Offermart: Existing customer found: {existing_customer.customer_id}")

                    # Update existing customer attributes
                    if customer_data.get('segment') and existing_customer.segment != customer_data['segment']:
                        existing_customer.segment = customer_data['segment']
                    if customer_data.get('is_dnd') is not None and existing_customer.is_dnd != customer_data['is_dnd']:
                        existing_customer.is_dnd = customer_data['is_dnd']
                    if customer_data.get('attributes'):
                        existing_customer.attributes.update(customer_data['attributes'])
                    existing_customer.updated_at = datetime.now()

                    # FR6: Handle Top-up loan offers deduplication
                    top_up_inactivated = self._handle_top_up_deduplication(offer_data, existing_customer.customer_id)
                    offers_to_link_to_new_offer.extend(top_up_inactivated)

                    new_offer_type = offer_data.get('offer_type')
                    new_offer_source_id = offer_data.get('source_offer_id')

                    # Check if this exact offer already exists for this customer (e.g., re-ingestion)
                    existing_specific_offer = Offer.query.filter_by(
                        customer_id=existing_customer.customer_id,
                        source_offer_id=new_offer_source_id,
                        source_system=offer_data.get('source_system')
                    ).first()

                    if existing_specific_offer:
                        current_app.logger.info(f"Offermart: Offer {new_offer_source_id} already exists for customer {existing_customer.customer_id}. Updating status/details.")
                        existing_specific_offer.offer_status = offer_data.get('offer_status', existing_specific_offer.offer_status)
                        existing_specific_offer.propensity = offer_data.get('propensity', existing_specific_offer.propensity)
                        existing_specific_offer.valid_until = datetime.fromisoformat(offer_data['valid_until']) if 'valid_until' in offer_data else existing_specific_offer.valid_until
                        existing_specific_offer.updated_at = datetime.now()
                        processed_results.append({
                            'original_data': item,
                            'status': 'updated_existing_offer',
                            'customer_id': str(existing_customer.customer_id),
                            'offer_id': str(existing_specific_offer.offer_id),
                            'message': 'Existing offer updated successfully.'
                        })
                        continue

                    # FR18: Handle 'Enrich' offers
                    active_journey_offers = None
                    if new_offer_type == 'Enrich':
                        active_journey_offers = Offer.query.filter(
                            Offer.customer_id == existing_customer.customer_id,
                            Offer.loan_application_number.isnot(None),
                            Offer.offer_status == 'Active'
                        ).first()

                        if active_journey_offers:
                            current_app.logger.info(f"Offermart: Customer {existing_customer.customer_id} has an active loan journey. 'Enrich' offer will not flow to CDP (FR13).")
                            processed_results.append({
                                'original_data': item,
                                'status': 'skipped',
                                'reason': 'Enrich offer not processed due to active loan journey.'
                            })
                            continue
                        else:
                            previous_active_offers_for_enrich = Offer.query.filter(
                                Offer.customer_id == existing_customer.customer_id,
                                Offer.offer_status == 'Active'
                            ).all()
                            for prev_offer in previous_active_offers_for_enrich:
                                prev_offer.offer_status = 'Inactive'
                                prev_offer.is_duplicate = True
                                history = OfferHistory(
                                    offer_id=prev_offer.offer_id,
                                    old_status='Active',
                                    new_status='Inactive',
                                    change_reason=f"Marked duplicate by new 'Enrich' offer from {offer_data.get('source_system')}"
                                )
                                db.session.add(history)
                                offers_to_link_to_new_offer.append(prev_offer)
                            current_app.logger.info(f"Offermart: Marked {len(previous_active_offers_for_enrich)} previous offers as Inactive/Duplicate for customer {existing_customer.customer_id} due to 'Enrich' offer.")

                    # FR7: Update old offers in Analytics Offermart with new real-time data from CDP
                    if new_offer_type in ['Fresh', 'New-new'] or (new_offer_type == 'Enrich' and not active_journey_offers):
                        offers_to_inactivate_by_new_offer = Offer.query.filter(
                            Offer.customer_id == existing_customer.customer_id,
                            Offer.offer_status == 'Active',
                            Offer.offer_id != new_offer_source_id
                        ).all()

                        for prev_offer in offers_to_inactivate_by_new_offer:
                            # Only inactivate if it's not a Top-up (handled separately)
                            # and not already marked for inactivation by Enrich logic (to avoid double counting/history)
                            if prev_offer not in offers_to_link_to_new_offer:
                                prev_offer.offer_status = 'Inactive'
                                prev_offer.is_duplicate = True
                                history = OfferHistory(
                                    offer_id=prev_offer.offer_id,
                                    old_status='Active',
                                    new_status='Inactive',
                                    change_reason=f"Superseded by new offer of type '{new_offer_type}' from {offer_data.get('source_system')}"
                                )
                                db.session.add(history)
                                offers_to_link_to_new_offer.append(prev_offer)
                        current_app.logger.info(f"Offermart: Marked {len(offers_to_inactivate_by_new_offer)} previous offers as Inactive/Duplicate for customer {existing_customer.customer_id} due to new offer.")

                    # Create a new offer linked to the existing customer
                    new_offer_uuid = uuid.uuid4()
                    new_offer = Offer(
                        offer_id=new_offer_uuid,
                        customer_id=existing_customer.customer_id,
                        source_offer_id=new_offer_source_id,
                        offer_type=new_offer_type,
                        offer_status=offer_data.get('offer_status', 'Active'),
                        propensity=offer_data.get('propensity'),
                        loan_application_number=loan_application_number,
                        valid_until=datetime.fromisoformat(offer_data['valid_until']) if 'valid_until' in offer_data else None,
                        source_system=offer_data.get('source_system'),
                        channel=offer_data.get('channel'),
                        is_duplicate=False
                    )
                    db.session.add(new_offer)

                    # Update original_offer_id for offers that were inactivated by this new offer
                    for prev_offer in offers_to_link_to_new_offer:
                        prev_offer.original_offer_id = new_offer_uuid

                    processed_results.append({
                        'original_data': item,
                        'status': 'processed',
                        'customer_id': str(existing_customer.customer_id),
                        'offer_id': str(new_offer.offer_id),
                        'message': 'Customer and offer updated/created successfully.'
                    })

                else:
                    current_app.logger.info("Offermart: No existing customer found. Creating new customer and offer.")
                    new_customer_uuid = uuid.uuid4()
                    new_customer = Customer(
                        customer_id=new_customer_uuid,
                        mobile_number=mobile_number,
                        pan_number=pan_number,
                        aadhaar_number=aadhaar_number,
                        ucid_number=ucid_number,
                        segment=customer_data.get('segment'),
                        is_dnd=customer_data.get('is_dnd', False),
                        attributes=customer_data.get('attributes', {})
                    )
                    db.session.add(new_customer)
                    db.session.flush()

                    new_offer_uuid = uuid.uuid4()
                    new_offer = Offer(
                        offer_id=new_offer_uuid,
                        customer_id=new_customer.customer_id,
                        source_offer_id=offer_data.get('source_offer_id'),
                        offer_type=offer_data.get('offer_type'),
                        offer_status=offer_data.get('offer_status', 'Active'),
                        propensity=offer_data.get('propensity'),
                        loan_application_number=loan_application_number,
                        valid_until=datetime.fromisoformat(offer_data['valid_until']) if 'valid_until' in offer_data else None,
                        source_system=offer_data.get('source_system'),
                        channel=offer_data.get('channel'),
                        is_duplicate=False
                    )
                    db.session.add(new_offer)
                    processed_results.append({
                        'original_data': item,
                        'status': 'processed',
                        'customer_id': str(new_customer.customer_id),
                        'offer_id': str(new_offer.offer_id),
                        'message': 'New customer and offer created successfully.'
                    })
            except Exception as e:
                current_app.logger.error(f"Error processing Offermart item: {item}. Error: {e}")
                processed_results.append({
                    'original_data': item,
                    'status': 'failed',
                    'reason': str(e)
                })
                # Continue processing other items in the batch even if one fails

        try:
            db.session.commit()
            current_app.logger.info(f"Offermart batch deduplication committed. Processed {len(processed_results)} items.")
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Database Integrity Error during Offermart batch deduplication: {e}")
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error during Offermart batch deduplication: {e}")
            raise e

        return processed_results