import uuid
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import joinedload
from flask import current_app

# Assuming db is initialized in app.extensions and models are defined in app.models
from app.extensions import db
from app.models import Customer, Offer, CustomerEvent


class CustomerService:
    """
    Service layer for managing customer-related business logic.
    Handles customer creation, updates, deduplication, segmentation,
    and retrieval of customer profiles.
    """

    @staticmethod
    def _find_existing_customer(customer_data: dict) -> Customer | None:
        """
        Attempts to find an existing customer based on various identifiers.
        Prioritizes unique identifiers as per FR2, FR3, FR4.
        If multiple identifiers are provided, it checks them in a defined order
        and returns the first customer found.
        """
        query = db.session.query(Customer)

        # FR2: single profile view based on mobile number, PAN, Aadhaar reference number, UCID, or previous loan application number.
        # FR3: deduplication within all Consumer Loan products.
        # FR4: deduplication against the live book (Customer 360) - assuming CDP's Customer table is the live book.

        # Order of priority for deduplication
        identifiers = [
            ('mobile_number', customer_data.get('mobile_number')),
            ('pan', customer_data.get('pan')),
            ('aadhaar_ref_number', customer_data.get('aadhaar_ref_number')),
            ('ucid', customer_data.get('ucid')),
            ('previous_loan_app_number', customer_data.get('previous_loan_app_number'))
        ]

        for key, value in identifiers:
            if value:
                customer = query.filter(getattr(Customer, key) == value).first()
                if customer:
                    current_app.logger.debug(f"Found existing customer {customer.customer_id} by {key}: {value}")
                    return customer
        
        current_app.logger.debug("No existing customer found with provided identifiers.")
        return None

    @staticmethod
    def _update_customer_attributes(customer: Customer, new_data: dict) -> bool:
        """
        Updates customer attributes from new data.
        Handles JSONB fields for 'customer_attributes'.
        FR14: The system shall maintain different customer attributes.
        Returns True if any attribute was updated, False otherwise.
        """
        updated = False
        for key, value in new_data.items():
            # Only update if the key exists as an attribute on the Customer model
            # and the new value is not None (to avoid overwriting with None unless explicitly desired)
            if hasattr(customer, key) and value is not None:
                if key == 'customer_attributes':
                    # Special handling for JSONB customer_attributes: merge dictionaries
                    if customer.customer_attributes is None:
                        customer.customer_attributes = {}
                    
                    # Check if any attribute within the JSONB needs updating
                    jsonb_updated = False
                    for attr_key, attr_value in value.items():
                        if customer.customer_attributes.get(attr_key) != attr_value:
                            customer.customer_attributes[attr_key] = attr_value
                            jsonb_updated = True
                    if jsonb_updated:
                        updated = True
                elif getattr(customer, key) != value:
                    setattr(customer, key, value)
                    updated = True
        
        if updated:
            customer.updated_at = datetime.now()
            current_app.logger.debug(f"Customer {customer.customer_id} attributes updated.")
        return updated

    @staticmethod
    def create_or_update_customer(customer_data: dict) -> tuple[Customer, bool]:
        """
        Creates a new customer record or updates an existing one based on deduplication logic.
        This is a core function for data ingestion from various sources (APIs, file uploads).
        FR2, FR3, FR4, FR5, FR14, FR19.
        
        Args:
            customer_data (dict): A dictionary containing customer details.
                                  Expected keys: mobile_number, pan, aadhaar_ref_number,
                                  ucid, previous_loan_app_number, customer_attributes,
                                  customer_segment, is_dnd.
        
        Returns:
            tuple[Customer, bool]: A tuple containing the Customer object and a boolean
                                   indicating if a new customer was created (True) or
                                   an existing one was updated (False).
        
        Raises:
            ValueError: If required data for new customer creation is missing or invalid.
            RuntimeError: For database-related errors or unexpected issues.
        """
        current_app.logger.info(f"Processing customer data for mobile: {customer_data.get('mobile_number')}")
        existing_customer = CustomerService._find_existing_customer(customer_data)
        is_new_customer = False

        try:
            if existing_customer:
                current_app.logger.info(f"Updating existing customer: {existing_customer.customer_id}")
                CustomerService._update_customer_attributes(existing_customer, customer_data)
                customer = existing_customer
            else:
                current_app.logger.info("Creating new customer record.")
                # FR1: Basic column-level validation. Assuming mobile_number is mandatory for new customers.
                if not customer_data.get('mobile_number'):
                    raise ValueError("Mobile number is required for new customer creation.")

                customer = Customer(
                    mobile_number=customer_data['mobile_number'],
                    pan=customer_data.get('pan'),
                    aadhaar_ref_number=customer_data.get('aadhaar_ref_number'),
                    ucid=customer_data.get('ucid'),
                    previous_loan_app_number=customer_data.get('previous_loan_app_number'),
                    customer_attributes=customer_data.get('customer_attributes', {}),
                    customer_segment=customer_data.get('customer_segment'),
                    is_dnd=customer_data.get('is_dnd', False)
                )
                db.session.add(customer)
                is_new_customer = True

            db.session.commit()
            current_app.logger.info(f"Customer {customer.customer_id} processed successfully. New record: {is_new_customer}")
            return customer, is_new_customer
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.warning(f"Integrity error during customer creation/update, attempting retry: {e}")
            # This can happen in a race condition where _find_existing_customer didn't find
            # a record, but another process inserted it before this one committed.
            # Attempt to find and update again.
            existing_customer_after_error = CustomerService._find_existing_customer(customer_data)
            if existing_customer_after_error:
                current_app.logger.info(f"Found customer {existing_customer_after_error.customer_id} on retry, updating.")
                CustomerService._update_customer_attributes(existing_customer_after_error, customer_data)
                db.session.commit()
                return existing_customer_after_error, False
            else:
                current_app.logger.error(f"Failed to create/update customer due to unresolvable data conflict: {e}")
                raise ValueError(f"Failed to create/update customer due to data conflict: {e}") from e
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error during customer creation/update: {e}", exc_info=True)
            raise RuntimeError(f"Database operation failed for customer: {e}") from e
        except ValueError as e:
            db.session.rollback() # Rollback if validation fails before commit
            current_app.logger.error(f"Validation error for customer data: {e}")
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"An unexpected error occurred during customer creation/update: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred: {e}") from e

    @staticmethod
    def get_customer_profile(customer_id: uuid.UUID) -> Customer | None:
        """
        Retrieves a single customer's profile view with associated offers and application stages.
        FR2: The system shall provide a single profile view of the customer for Consumer Loan Products.
        FR36: The system shall provide a front-end for customer level view with stages.
        
        Args:
            customer_id (uuid.UUID): The UUID of the customer to retrieve.
            
        Returns:
            Customer | None: The Customer object if found, otherwise None.
        
        Raises:
            RuntimeError: For database-related errors.
        """
        try:
            customer = db.session.query(Customer).options(
                joinedload(Customer.offers),
                joinedload(Customer.events)
            ).filter_by(customer_id=customer_id).first()
            
            if customer:
                current_app.logger.debug(f"Retrieved customer profile for {customer_id}.")
            else:
                current_app.logger.debug(f"Customer profile for {customer_id} not found.")
            return customer
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error retrieving customer {customer_id}: {e}", exc_info=True)
            raise RuntimeError(f"Could not retrieve customer profile: {e}") from e

    @staticmethod
    def is_customer_dnd(customer_id: uuid.UUID) -> bool:
        """
        Checks if a customer is marked as 'Do Not Disturb'.
        FR21: The system shall store event data from Moengage and LOS in the LTFS Offer CDP, avoiding DND Customers.
        
        Args:
            customer_id (uuid.UUID): The UUID of the customer.
            
        Returns:
            bool: True if the customer is DND, False otherwise.
        
        Raises:
            RuntimeError: For database-related errors.
        """
        try:
            customer = db.session.query(Customer).filter_by(customer_id=customer_id).first()
            if customer:
                current_app.logger.debug(f"DND status for customer {customer_id}: {customer.is_dnd}")
                return customer.is_dnd
            current_app.logger.warning(f"Customer {customer_id} not found when checking DND status. Assuming not DND.")
            return False # If customer not found, assume not DND for safety, or raise an error depending on strictness
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error checking DND status for customer {customer_id}: {e}", exc_info=True)
            raise RuntimeError(f"Could not check DND status: {e}") from e

    @staticmethod
    def update_customer_dnd_status(customer_id: uuid.UUID, is_dnd: bool) -> Customer:
        """
        Updates the DND (Do Not Disturb) status for a specific customer.
        
        Args:
            customer_id (uuid.UUID): The UUID of the customer.
            is_dnd (bool): The new DND status (True for DND, False otherwise).
            
        Returns:
            Customer: The updated Customer object.
            
        Raises:
            ValueError: If the customer is not found.
            RuntimeError: For database-related errors.
        """
        try:
            customer = db.session.query(Customer).filter_by(customer_id=customer_id).first()
            if not customer:
                raise ValueError(f"Customer with ID {customer_id} not found.")
            
            if customer.is_dnd != is_dnd:
                customer.is_dnd = is_dnd
                customer.updated_at = datetime.now()
                db.session.commit()
                current_app.logger.info(f"Customer {customer_id} DND status updated to {is_dnd}.")
            else:
                current_app.logger.info(f"Customer {customer_id} DND status already {is_dnd}, no update needed.")
            return customer
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error updating DND status for customer {customer_id}: {e}", exc_info=True)
            raise RuntimeError(f"Could not update DND status: {e}") from e
        except ValueError as e:
            db.session.rollback() # Rollback if customer not found (though no DB change, good practice)
            current_app.logger.warning(f"Failed to update DND status: {e}")
            raise e

    @staticmethod
    def update_customer_segment(customer_id: uuid.UUID, segment: str) -> Customer:
        """
        Updates the customer segment for a specific customer.
        FR14: The system shall maintain different customer attributes and customer segments.
        FR19: The system shall maintain customer segments like C1 to C8.
        
        Args:
            customer_id (uuid.UUID): The UUID of the customer.
            segment (str): The new customer segment (e.g., 'C1', 'C8').
            
        Returns:
            Customer: The updated Customer object.
            
        Raises:
            ValueError: If the customer is not found.
            RuntimeError: For database-related errors.
        """
        try:
            customer = db.session.query(Customer).filter_by(customer_id=customer_id).first()
            if not customer:
                raise ValueError(f"Customer with ID {customer_id} not found.")

            if customer.customer_segment != segment:
                customer.customer_segment = segment
                customer.updated_at = datetime.now()
                db.session.commit()
                current_app.logger.info(f"Customer {customer_id} segment updated to {segment}.")
            else:
                current_app.logger.info(f"Customer {customer_id} segment already {segment}, no update needed.")
            return customer
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error updating customer segment for {customer_id}: {e}", exc_info=True)
            raise RuntimeError(f"Could not update customer segment: {e}") from e
        except ValueError as e:
            db.session.rollback() # Rollback if customer not found
            current_app.logger.warning(f"Failed to update customer segment: {e}")
            raise e