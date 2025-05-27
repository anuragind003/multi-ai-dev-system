from sqlalchemy.orm import Session
from sqlalchemy import or_
from uuid import UUID
from datetime import date, datetime, timedelta

from app.models.customer import Customer
from app.models.offer import Offer
from app.models.offer_history import OfferHistory
from app.schemas.customer import CustomerProfileResponse, OfferSummary
from app.schemas.offer import OfferCreate, OfferStatus, OfferType, ProductType
from app.core.exceptions import NotFoundException, ConflictException
from app.core.config import settings


class CustomerService:
    def __init__(self, db: Session):
        self.db = db

    def get_customer_profile(self, customer_id: UUID) -> CustomerProfileResponse:
        """
        Retrieves a single profile view of a customer (FR2, FR50).
        Includes current active offer, offer history summary (FR23), and journey status.
        """
        customer = self.db.query(Customer).filter(Customer.customer_id == customer_id).first()
        if not customer:
            raise NotFoundException(detail=f"Customer with ID {customer_id} not found.")

        current_offer_db = self.db.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.offer_status == OfferStatus.ACTIVE
        ).order_by(Offer.created_at.desc()).first()

        current_offer_summary = None
        if current_offer_db:
            current_offer_summary = OfferSummary(
                offer_id=current_offer_db.offer_id,
                product_type=current_offer_db.product_type,
                offer_status=current_offer_db.offer_status,
                offer_type=current_offer_db.offer_type,
                is_journey_started=current_offer_db.is_journey_started,
                loan_application_id=current_offer_db.loan_application_id
            )

        six_months_ago = datetime.now() - timedelta(days=settings.OFFER_HISTORY_RETENTION_DAYS)
        offer_history_db = self.db.query(OfferHistory).filter(
            OfferHistory.customer_id == customer_id,
            OfferHistory.change_timestamp >= six_months_ago
        ).order_by(OfferHistory.change_timestamp.desc()).all()

        offer_history_summary = [
            {
                "offer_id": h.offer_id,
                "change_timestamp": h.change_timestamp,
                "old_status": h.old_offer_status,
                "new_status": h.new_offer_status,
                "reason": h.change_reason
            }
            for h in offer_history_db
        ]

        journey_status = "No Active Journey"
        if current_offer_summary and current_offer_summary.is_journey_started:
            journey_status = "Journey Started"
            if current_offer_summary.loan_application_id:
                journey_status += f" (LAN: {current_offer_summary.loan_application_id})"
        elif current_offer_summary:
            journey_status = "Offer Active, Journey Not Started"

        return CustomerProfileResponse(
            customer_id=customer.customer_id,
            mobile_number=customer.mobile_number,
            pan_number=customer.pan_number,
            aadhaar_ref_number=customer.aadhaar_ref_number,
            ucid_number=customer.ucid_number,
            previous_loan_app_number=customer.previous_loan_app_number,
            customer_attributes=customer.customer_attributes,
            customer_segments=customer.customer_segments,
            propensity_flag=customer.propensity_flag,
            dnd_status=customer.dnd_status,
            current_offer=current_offer_summary,
            offer_history_summary=offer_history_summary,
            journey_status=journey_status
        )

    def create_or_update_customer_and_offer(
        self,
        mobile_number: str,
        pan_number: str,
        aadhaar_ref_number: str,
        ucid_number: str,
        previous_loan_app_number: str,
        offer_data: OfferCreate,
        is_realtime_api_lead: bool = False
    ) -> Customer:
        """
        Handles creation or update of customer and their offers,
        incorporating deduplication (FR3, FR4, FR5, FR6) and offer precedence logic
        (FR15, FR20, FR21, FR25-FR32, FR8).
        """
        customer = self.get_customer_by_identifiers(
            mobile_number=mobile_number,
            pan_number=pan_number,
            aadhaar_ref_number=aadhaar_ref_number,
            ucid_number=ucid_number,
            previous_loan_app_number=previous_loan_app_number
        )

        if not customer:
            customer = Customer(
                mobile_number=mobile_number,
                pan_number=pan_number,
                aadhaar_ref_number=aadhaar_ref_number,
                ucid_number=ucid_number,
                previous_loan_app_number=previous_loan_app_number,
                customer_attributes={},
                customer_segments=[],
                propensity_flag=None,
                dnd_status=False
            )
            self.db.add(customer)
            self.db.flush()

        existing_offers = self.db.query(Offer).filter(
            Offer.customer_id == customer.customer_id,
            Offer.offer_status == OfferStatus.ACTIVE
        ).all()

        new_offer_status = OfferStatus.ACTIVE
        new_offer_reason = "Fresh Offer"

        for existing_offer in existing_offers:
            if existing_offer.is_journey_started:
                if offer_data.offer_type == OfferType.ENRICH:
                    raise ConflictException(
                        detail=f"Cannot process Enrich offer for customer {customer.customer_id} "
                               f"as an existing offer ({existing_offer.offer_id}) has a started journey (FR21)."
                    )
                else:
                    new_offer_status = OfferStatus.DUPLICATE
                    new_offer_reason = (
                        f"Existing offer {existing_offer.offer_id} has started journey. "
                        f"New offer marked as Duplicate (FR26, FR27, FR28)."
                    )
                    break

            if is_realtime_api_lead and \
               existing_offer.product_type in [ProductType.PREAPPROVED, ProductType.E_AGGREGATOR, ProductType.PROSPECT] and \
               not existing_offer.is_journey_started:
                self._update_offer_status(
                    existing_offer,
                    OfferStatus.EXPIRED,
                    "Expired by new CLEAG/Insta offer (FR25)"
                )
                new_offer_status = OfferStatus.ACTIVE
                new_offer_reason = "New CLEAG/Insta offer prevails (FR25)"
                continue

            if offer_data.offer_type == OfferType.ENRICH and \
               not existing_offer.is_journey_started:
                self._update_offer_status(
                    existing_offer,
                    OfferStatus.DUPLICATE,
                    "Replaced by new Enrich offer (FR20)"
                )
                new_offer_status = OfferStatus.ACTIVE
                new_offer_reason = "New Enrich offer replaces old (FR20)"
                continue

            # FR29, FR30, FR31, FR32: Product type precedence rules
            # If an existing offer of a higher precedence type exists, the new offer cannot be uploaded.
            # This is a simplified interpretation.
            product_precedence_block = False
            if existing_offer.product_type in [ProductType.TW_LOYALTY, ProductType.TOP_UP, ProductType.EMPLOYEE_LOAN]:
                if offer_data.product_type in [ProductType.PREAPPROVED, ProductType.E_AGGREGATOR, ProductType.PROSPECT]:
                    product_precedence_block = True
            elif existing_offer.product_type == ProductType.EMPLOYEE_LOAN:
                if offer_data.product_type in [ProductType.TW_LOYALTY, ProductType.TOP_UP, ProductType.PREAPPROVED, ProductType.E_AGGREGATOR, ProductType.PROSPECT]:
                    product_precedence_block = True
            elif existing_offer.product_type == ProductType.TW_LOYALTY:
                if offer_data.product_type in [ProductType.TOP_UP, ProductType.EMPLOYEE_LOAN, ProductType.PREAPPROVED, ProductType.E_AGGREGATOR, ProductType.PROSPECT]:
                    product_precedence_block = True
            elif existing_offer.product_type == ProductType.PROSPECT:
                if offer_data.product_type in [ProductType.TW_LOYALTY, ProductType.TOP_UP, ProductType.EMPLOYEE_LOAN, ProductType.PREAPPROVED, ProductType.E_AGGREGATOR]:
                    product_precedence_block = True

            if product_precedence_block:
                new_offer_status = OfferStatus.DUPLICATE
                new_offer_reason = (
                    f"New offer type '{offer_data.product_type}' cannot be uploaded "
                    f"due to existing '{existing_offer.product_type}' (FR29-FR32)."
                )
                break

        new_offer = Offer(
            customer_id=customer.customer_id,
            offer_type=offer_data.offer_type,
            offer_status=new_offer_status,
            product_type=offer_data.product_type,
            offer_details=offer_data.offer_details,
            offer_start_date=offer_data.offer_start_date,
            offer_end_date=offer_data.offer_end_date,
            is_journey_started=False,
            loan_application_id=None
        )
        self.db.add(new_offer)
        self.db.flush()

        self._record_offer_history(
            new_offer.offer_id,
            customer.customer_id,
            None,
            new_offer.offer_status,
            new_offer_reason,
            new_offer.offer_details
        )

        self.db.commit()
        self.db.refresh(customer)
        return customer

    def _update_offer_status(self, offer: Offer, new_status: OfferStatus, reason: str):
        """Helper to update offer status and record history."""
        old_status = offer.offer_status
        offer.offer_status = new_status
        offer.updated_at = datetime.now()
        self.db.add(offer)
        self.db.flush()

        self._record_offer_history(
            offer.offer_id,
            offer.customer_id,
            old_status,
            new_status,
            reason,
            offer.offer_details
        )

    def _record_offer_history(
        self,
        offer_id: UUID,
        customer_id: UUID,
        old_status: str | None,
        new_status: str,
        reason: str,
        snapshot_details: dict
    ):
        """Records an entry in the offer_history table."""
        history_entry = OfferHistory(
            offer_id=offer_id,
            customer_id=customer_id,
            old_offer_status=old_status,
            new_offer_status=new_status,
            change_reason=reason,
            snapshot_offer_details=snapshot_details
        )
        self.db.add(history_entry)
        self.db.flush()

    def update_offer_journey_status(
        self, offer_id: UUID, is_journey_started: bool, loan_application_id: str | None = None
    ):
        """
        Updates the journey status of an offer.
        FR15: Prevents modification of customer offers with a started loan application journey.
        """
        offer = self.db.query(Offer).filter(Offer.offer_id == offer_id).first()
        if not offer:
            raise NotFoundException(detail=f"Offer with ID {offer_id} not found.")

        if offer.is_journey_started and not is_journey_started:
            raise ConflictException(
                detail=f"Cannot revert journey status for offer {offer_id} once started (FR15)."
            )

        old_journey_status = offer.is_journey_started
        old_loan_app_id = offer.loan_application_id

        offer.is_journey_started = is_journey_started
        offer.loan_application_id = loan_application_id
        offer.updated_at = datetime.now()
        self.db.add(offer)

        reason = f"Journey status changed from {old_journey_status} to {is_journey_started}"
        if loan_application_id and loan_application_id != old_loan_app_id:
            reason += f", LAN updated from {old_loan_app_id} to {loan_application_id}"

        self._record_offer_history(
            offer.offer_id,
            offer.customer_id,
            offer.offer_status,
            offer.offer_status,
            reason,
            offer.offer_details
        )
        self.db.commit()
        self.db.refresh(offer)
        return offer

    def expire_offers_by_date(self) -> int:
        """
        Marks offers as expired based on offer end dates for non-journey started customers (FR51).
        This method is intended to be called by a scheduled job.
        """
        today = date.today()
        offers_to_expire = self.db.query(Offer).filter(
            Offer.offer_status == OfferStatus.ACTIVE,
            Offer.is_journey_started == False,
            Offer.offer_end_date < today
        ).all()

        for offer in offers_to_expire:
            self._update_offer_status(
                offer,
                OfferStatus.EXPIRED,
                f"Offer expired based on end date {offer.offer_end_date} (FR51)"
            )
        self.db.commit()
        return len(offers_to_expire)

    def expire_offers_by_lan_validity(self) -> int:
        """
        Marks offers as expired if LAN validity post loan application journey start date is over (FR53).
        Assumes LAN validity period is defined in settings.
        This method is intended to be called by a scheduled job.
        """
        offers_to_expire = self.db.query(Offer).filter(
            Offer.offer_status == OfferStatus.ACTIVE,
            Offer.is_journey_started == True,
            Offer.loan_application_id.isnot(None),
            Offer.updated_at < (datetime.now() - timedelta(days=settings.LAN_VALIDITY_DAYS))
        ).all()

        for offer in offers_to_expire:
            self._update_offer_status(
                offer,
                OfferStatus.EXPIRED,
                f"Offer expired based on LAN validity period ({settings.LAN_VALIDITY_DAYS} days) (FR53)"
            )
        self.db.commit()
        return len(offers_to_expire)

    def check_and_replenish_expired_offers(self, customer_id: UUID) -> dict:
        """
        Checks for new replenishment offers for loan applications that have expired or been rejected (FR16, FR52).
        This is a placeholder for a more complex integration with an offer generation system.
        """
        expired_offers = self.db.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.offer_status.in_([OfferStatus.EXPIRED, OfferStatus.REJECTED])
        ).all()

        if expired_offers:
            # In a real system, this would trigger a call to Offermart or an internal
            # offer generation logic to find and potentially create new offers.
            return {
                "message": f"Customer {customer_id} has {len(expired_offers)} expired/rejected offers. "
                           "Replenishment check initiated (placeholder)."
            }
        else:
            return {"message": f"Customer {customer_id} has no expired/rejected offers requiring replenishment."}

    def get_customer_by_identifiers(
        self,
        mobile_number: str | None = None,
        pan_number: str | None = None,
        aadhaar_ref_number: str | None = None,
        ucid_number: str | None = None,
        previous_loan_app_number: str | None = None
    ) -> Customer | None:
        """
        Helper to find a customer by any of their unique identifiers for deduplication (FR3).
        """
        filters = []
        if mobile_number:
            filters.append(Customer.mobile_number == mobile_number)
        if pan_number:
            filters.append(Customer.pan_number == pan_number)
        if aadhaar_ref_number:
            filters.append(Customer.aadhaar_ref_number == aadhaar_ref_number)
        if ucid_number:
            filters.append(Customer.ucid_number == ucid_number)
        if previous_loan_app_number:
            filters.append(Customer.previous_loan_app_number == previous_loan_app_number)

        if not filters:
            return None

        return self.db.query(Customer).filter(or_(*filters)).first()