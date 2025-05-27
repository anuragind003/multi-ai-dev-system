import logging
from typing import List, Dict, Any, Optional
import httpx
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import datetime

# Assuming these modules exist and contain necessary classes/functions
# from app.db.session import get_db_session # Not directly used in the service class init
from app.models import models as db_models # For type hinting if needed, but services handle actual DB models
from app.services.deduplication import DeduplicationService
from app.services.customer_offer import CustomerOfferService
from app.core.config import settings as app_settings # For general app settings like API keys, if any shared

logger = logging.getLogger(__name__)

# --- Configuration for Offermart Integration ---
class OffermartSettings(BaseSettings):
    OFFERMART_API_BASE_URL: str = "http://localhost:8001/offermart_api" # Placeholder URL for Offermart's API
    OFFERMART_API_KEY: str = "your_offermart_api_key" # Placeholder API key for authentication with Offermart

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_prefix="OFFERMART_")

offermart_settings = OffermartSettings()

# --- Pydantic Models for Offermart Data ---
class OffermartCustomerData(BaseModel):
    mobile_number: str
    pan_number: Optional[str] = None
    aadhaar_ref_number: Optional[str] = None
    ucid_number: Optional[str] = None
    previous_loan_app_number: Optional[str] = None
    customer_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict)
    customer_segments: Optional[List[str]] = Field(default_factory=list)
    propensity_flag: Optional[str] = None
    dnd_status: bool = False # Assuming Offermart might provide this

class OffermartOfferData(BaseModel):
    # Assuming offer data comes linked to a customer identifier
    mobile_number: str # Or pan_number, aadhaar_ref_number, ucid_number
    offer_type: str # e.g., 'Fresh', 'Enrich', 'New-old', 'New-new'
    product_type: str # e.g., 'Loyalty', 'Preapproved', 'E-aggregator', 'Insta', 'Top-up', 'Employee Loan'
    offer_details: Dict[str, Any] # Flexible storage for offer specific data
    offer_start_date: datetime.date # YYYY-MM-DD
    offer_end_date: datetime.date # YYYY-MM-DD
    # Add other fields as per Offermart's data structure (e.g., offer_id from Offermart if they have one)

class CDPOfferUpdateToOffermart(BaseModel):
    # Data structure for reverse feed/real-time updates to Offermart
    customer_identifier: str # Mobile, PAN, Aadhaar, UCID
    identifier_type: str # 'mobile', 'pan', 'aadhaar', 'ucid'
    cdp_offer_id: str # CDP's internal offer_id
    offer_status: str # e.g., 'Active', 'Expired', 'Converted', 'Rejected'
    loan_application_id: Optional[str] = None # If applicable
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now) # ISO format datetime

# --- Offermart Integration Service ---
class OffermartIntegrationService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.deduplication_service = DeduplicationService(db_session)
        self.customer_offer_service = CustomerOfferService(db_session)
        self.http_client = httpx.AsyncClient(base_url=offermart_settings.OFFERMART_API_BASE_URL)

    async def _validate_offermart_customer_data(self, data: Dict[str, Any]) -> Optional[OffermartCustomerData]:
        """
        Performs basic column-level validation for customer data received from Offermart. (FR1, NFR3)
        """
        try:
            # Ensure at least one primary identifier is present for a valid customer
            if not any([data.get('mobile_number'), data.get('pan_number'), data.get('aadhaar_ref_number'), data.get('ucid_number')]):
                logger.warning(f"Customer data missing primary identifier. Skipping: {data}")
                return None

            # Use Pydantic model for validation and type conversion
            validated_data = OffermartCustomerData(**data)
            return validated_data
        except Exception as e:
            logger.error(f"Validation failed for Offermart customer data {data}: {e}")
            return None

    async def _validate_offermart_offer_data(self, data: Dict[str, Any]) -> Optional[OffermartOfferData]:
        """
        Performs basic column-level validation for offer data received from Offermart. (FR1, NFR3)
        """
        try:
            # Ensure required fields are present
            if not all([data.get('mobile_number'), data.get('offer_type'), data.get('product_type'), data.get('offer_start_date'), data.get('offer_end_date')]):
                logger.warning(f"Offer data missing required fields. Skipping: {data}")
                return None

            # Convert date strings to datetime.date objects if they are strings
            if isinstance(data.get('offer_start_date'), str):
                data['offer_start_date'] = datetime.date.fromisoformat(data['offer_start_date'])
            if isinstance(data.get('offer_end_date'), str):
                data['offer_end_date'] = datetime.date.fromisoformat(data['offer_end_date'])

            # Use Pydantic model for validation and type conversion
            validated_data = OffermartOfferData(**data)
            return validated_data
        except ValueError as e:
            logger.error(f"Date format error in offer data {data}: {e}. Expected YYYY-MM-DD.")
            return None
        except Exception as e:
            logger.error(f"Validation failed for Offermart offer data {data}: {e}")
            return None

    async def ingest_daily_offermart_data(self, customer_data_list: List[Dict[str, Any]], offer_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ingests daily customer and offer data from Offermart's staging area into CDP.
        This function orchestrates the processing, validation, deduplication, and saving of data.
        (FR9, FR1, FR22, FR24, NFR3)

        Args:
            customer_data_list: A list of dictionaries, each representing a customer record from Offermart.
            offer_data_list: A list of dictionaries, each representing an offer record from Offermart.

        Returns:
            A dictionary summarizing the ingestion results (e.g., counts of processed, unique, duplicate, errors).
        """
        logger.info(f"Starting daily data ingestion from Offermart. Customers: {len(customer_data_list)}, Offers: {len(offer_data_list)}")
        results = {
            "total_customers_received": len(customer_data_list),
            "processed_customers": 0,
            "failed_customer_validations": 0,
            "total_offers_received": len(offer_data_list),
            "processed_offers": 0,
            "failed_offer_validations": 0,
            "new_customers_created": 0,
            "existing_customers_updated": 0,
            "new_offers_created": 0,
            "offers_marked_duplicate": 0,
            "offers_not_processed_due_to_journey": 0,
            "errors": []
        }

        # --- Phase 1: Process Customer Data ---
        # Prioritize processing customers to ensure they exist before offers are linked
        for customer_raw_data in customer_data_list:
            validated_customer = await self._validate_offermart_customer_data(customer_raw_data)
            if not validated_customer:
                results["failed_customer_validations"] += 1
                results["errors"].append({"type": "customer_validation_failed", "data": customer_raw_data})
                continue

            try:
                # Deduplicate and create/update customer in CDP
                customer_record, is_new_customer = await self.deduplication_service.deduplicate_and_get_customer(
                    mobile_number=validated_customer.mobile_number,
                    pan_number=validated_customer.pan_number,
                    aadhaar_ref_number=validated_customer.aadhaar_ref_number,
                    ucid_number=validated_customer.ucid_number,
                    previous_loan_app_number=validated_customer.previous_loan_app_number,
                    customer_attributes=validated_customer.customer_attributes,
                    customer_segments=validated_customer.customer_segments, # FR24
                    propensity_flag=validated_customer.propensity_flag,     # FR22
                    dnd_status=validated_customer.dnd_status
                )

                if is_new_customer:
                    results["new_customers_created"] += 1
                else:
                    results["existing_customers_updated"] += 1
                results["processed_customers"] += 1

            except Exception as e:
                logger.error(f"Error processing customer data from Offermart (mobile: {validated_customer.mobile_number}): {e}")
                results["errors"].append({"type": "customer_processing_error", "data": customer_raw_data, "error": str(e)})
                # Rollback session if an error occurs during a batch, or handle per-record
                await self.db_session.rollback()
                continue

        # --- Phase 2: Process Offer Data ---
        for offer_raw_data in offer_data_list:
            validated_offer = await self._validate_offermart_offer_data(offer_raw_data)
            if not validated_offer:
                results["failed_offer_validations"] += 1
                results["errors"].append({"type": "offer_validation_failed", "data": offer_raw_data})
                continue

            try:
                # Find the customer for this offer using primary identifiers
                customer = await self.deduplication_service.get_customer_by_identifiers(
                    mobile_number=validated_offer.mobile_number,
                    pan_number=None, # Assuming mobile is the primary link for offers from Offermart
                    aadhaar_ref_number=None,
                    ucid_number=None
                )

                if not customer:
                    logger.warning(f"Offer received for unknown or unprocessed customer (mobile: {validated_offer.mobile_number}). Skipping offer.")
                    results["errors"].append({"type": "offer_no_matching_customer", "data": offer_raw_data})
                    continue

                # Apply offer precedence and update logic (FR8, FR15, FR20, FR21, FR25-FR32)
                # This complex business logic is delegated to CustomerOfferService
                offer_processing_status = await self.customer_offer_service.process_new_offermart_offer(
                    customer_id=customer.customer_id,
                    offer_type=validated_offer.offer_type,
                    product_type=validated_offer.product_type,
                    offer_details=validated_offer.offer_details,
                    offer_start_date=validated_offer.offer_start_date,
                    offer_end_date=validated_offer.offer_end_date
                )

                if offer_processing_status == "created":
                    results["new_offers_created"] += 1
                elif offer_processing_status == "duplicate":
                    results["offers_marked_duplicate"] += 1
                elif offer_processing_status == "not_processed_journey_started":
                    results["offers_not_processed_due_to_journey"] += 1
                # Other statuses like 'updated' could also be tracked if CustomerOfferService returns them

                results["processed_offers"] += 1

            except Exception as e:
                logger.error(f"Error processing offer data from Offermart for customer (mobile: {validated_offer.mobile_number}): {e}")
                results["errors"].append({"type": "offer_processing_error", "data": offer_raw_data, "error": str(e)})
                await self.db_session.rollback() # Rollback if an error occurs during a record processing
                continue

        await self.db_session.commit() # Commit all changes after successful processing of a batch
        logger.info(f"Offermart data ingestion completed. Summary: {results}")
        return results

    async def push_realtime_offer_to_offermart(self, offer_update: CDPOfferUpdateToOffermart) -> bool:
        """
        Pushes real-time offer updates (e.g., for Insta or E-aggregator conversions/status changes)
        from CDP to Analytics Offermart. (FR7, NFR8)

        Args:
            offer_update: A Pydantic model containing the offer update details.

        Returns:
            True if the push was successful, False otherwise.
        """
        logger.info(f"Pushing real-time offer update to Offermart for customer {offer_update.customer_identifier}, offer {offer_update.cdp_offer_id}")
        try:
            response = await self.http_client.post(
                "/realtime_offer_update", # Assuming Offermart has an endpoint for real-time updates
                json=offer_update.model_dump(mode='json'), # Use model_dump(mode='json') for datetime serialization
                headers={"X-API-Key": offermart_settings.OFFERMART_API_KEY}
            )
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses
            logger.info(f"Successfully pushed real-time offer update to Offermart. Response: {response.json()}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error pushing real-time offer to Offermart: {e.response.status_code} - {e.response.text}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Network error pushing real-time offer to Offermart: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error pushing real-time offer to Offermart: {e}")
            return False

    async def push_daily_reverse_feed_to_offermart(self, updated_offers: List[CDPOfferUpdateToOffermart]) -> bool:
        """
        Pushes daily reverse feed of aggregated offer data updates from CDP to Offermart.
        This typically includes status changes, conversions, or other relevant metrics. (FR10, NFR6)

        Args:
            updated_offers: A list of Pydantic models, each representing an offer update.

        Returns:
            True if the push was successful, False otherwise.
        """
        logger.info(f"Pushing daily reverse feed to Offermart. Total updates: {len(updated_offers)}")
        if not updated_offers:
            logger.info("No offer updates to send in daily reverse feed.")
            return True

        try:
            # Assuming Offermart has a batch endpoint for daily reverse feeds.
            # If not, this would involve iterating and calling push_realtime_offer_to_offermart for each.
            payload = [update.model_dump(mode='json') for update in updated_offers]
            response = await self.http_client.post(
                "/daily_reverse_feed", # Assuming Offermart has an endpoint for daily batch updates
                json=payload,
                headers={"X-API-Key": offermart_settings.OFFERMART_API_KEY}
            )
            response.raise_for_status()
            logger.info(f"Successfully pushed daily reverse feed to Offermart. Response: {response.json()}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error pushing daily reverse feed to Offermart: {e.response.status_code} - {e.response.text}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Network error pushing daily reverse feed to Offermart: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error pushing daily reverse feed to Offermart: {e}")
            return False