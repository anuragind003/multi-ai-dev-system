import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta
import uuid
import io

# --- Mock Pydantic Models (simplified for testing purposes) ---
# In a real project, these would be imported from `src.models.customer` or similar.
class CustomerCreate:
    def __init__(self, mobile_number: str, pan_number: str = None, aadhaar_ref_number: str = None, ucid_number: str = None, previous_loan_app_number: str = None, customer_attributes: dict = None, customer_segments: list = None, propensity_flag: str = None, dnd_status: bool = False):
        self.mobile_number = mobile_number
        self.pan_number = pan_number
        self.aadhaar_ref_number = aadhaar_ref_number
        self.ucid_number = ucid_number
        self.previous_loan_app_number = previous_loan_app_number
        self.customer_attributes = customer_attributes or {}
        self.customer_segments = customer_segments or []
        self.propensity_flag = propensity_flag
        self.dnd_status = dnd_status

class CustomerInDB(CustomerCreate):
    def __init__(self, customer_id: uuid.UUID, created_at: datetime = None, updated_at: datetime = None, **kwargs):
        super().__init__(**kwargs)
        self.customer_id = customer_id
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def model_dump(self): # Simulate Pydantic's .model_dump()
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

class OfferCreate:
    def __init__(self, customer_id: uuid.UUID, offer_type: str, offer_status: str, product_type: str, offer_details: dict = None, offer_start_date: date = None, offer_end_date: date = None, is_journey_started: bool = False, loan_application_id: str = None):
        self.customer_id = customer_id
        self.offer_type = offer_type
        self.offer_status = offer_status
        self.product_type = product_type
        self.offer_details = offer_details or {}
        self.offer_start_date = offer_start_date
        self.offer_end_date = offer_end_date
        self.is_journey_started = is_journey_started
        self.loan_application_id = loan_application_id

class OfferInDB(OfferCreate):
    def __init__(self, offer_id: uuid.UUID, created_at: datetime = None, updated_at: datetime = None, **kwargs):
        super().__init__(**kwargs)
        self.offer_id = offer_id
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        # Added for testing LAN validity expiry, ideally part of model if used
        self.lan_validity_end_date = None 

    def model_dump(self): # Simulate Pydantic's .model_dump()
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

class OfferHistoryCreate:
    def __init__(self, offer_id: uuid.UUID, customer_id: uuid.UUID, old_offer_status: str, new_offer_status: str, change_reason: str, snapshot_offer_details: dict = None):
        self.offer_id = offer_id
        self.customer_id = customer_id
        self.old_offer_status = old_offer_status
        self.new_offer_status = new_offer_status
        self.change_reason = change_reason
        self.snapshot_offer_details = snapshot_offer_details or {}

class CampaignEventCreate:
    def __init__(self, customer_id: uuid.UUID, event_source: str, event_type: str, offer_id: uuid.UUID = None, event_details: dict = None):
        self.customer_id = customer_id
        self.event_source = event_source
        self.event_type = event_type
        self.offer_id = offer_id
        self.event_details = event_details or {}

class LeadData:
    def __init__(self, mobile_number: str, pan_number: str = None, aadhaar_ref_number: str = None, loan_product: str = None, offer_details: dict = None):
        self.mobile_number = mobile_number
        self.pan_number = pan_number
        self.aadhaar_ref_number = aadhaar_ref_number
        self.loan_product = loan_product
        self.offer_details = offer_details or {}

class MoengageRecord:
    def __init__(self, customer_id: uuid.UUID, mobile_number: str, offer_id: uuid.UUID, product_type: str, offer_status: str, offer_details: dict):
        self.customer_id = customer_id
        self.mobile_number = mobile_number
        self.offer_id = offer_id
        self.product_type = product_type
        self.offer_status = offer_status
        self.offer_details = offer_details

    def to_csv_row(self):
        # Simplified for testing, real implementation would handle nested JSON
        return [
            str(self.customer_id),
            self.mobile_number,
            str(self.offer_id),
            self.product_type,
            self.offer_status,
            str(self.offer_details)
        ]

# --- Mock Repository Interfaces (simplified for testing) ---
# In a real project, these would be imported from `src.repositories`.
class CustomerRepository:
    async def get_by_identifiers(self, mobile_number: str = None, pan_number: str = None, aadhaar_ref_number: str = None, ucid_number: str = None, previous_loan_app_number: str = None) -> CustomerInDB | None:
        pass
    async def create(self, customer: CustomerCreate) -> CustomerInDB:
        pass
    async def update(self, customer_id: uuid.UUID, customer_update_data: dict) -> CustomerInDB:
        pass
    async def get_by_id(self, customer_id: uuid.UUID) -> CustomerInDB | None:
        pass

class OfferRepository:
    async def get_active_offers_for_customer(self, customer_id: uuid.UUID) -> list[OfferInDB]:
        pass
    async def create(self, offer: OfferCreate) -> OfferInDB:
        pass
    async def update(self, offer_id: uuid.UUID, offer_update_data: dict) -> OfferInDB:
        pass
    async def get_offers_by_status_and_end_date(self, status: str, end_date_before: date) -> list[OfferInDB]:
        pass
    async def get_offers_by_status_and_lan_validity(self, status: str, lan_validity_end_date_before: date) -> list[OfferInDB]:
        pass
    async def get_all_active_offers(self) -> list[OfferInDB]:
        pass

class OfferHistoryRepository:
    async def create(self, history: OfferHistoryCreate):
        pass

class CampaignEventRepository:
    async def create(self, event: CampaignEventCreate):
        pass

# --- Mock Service Classes (simplified for testing) ---
# In a real project, these would be imported from `src.services`.
class CustomerService:
    def __init__(self, customer_repo: CustomerRepository, offer_repo: OfferRepository, offer_history_repo: OfferHistoryRepository, campaign_event_repo: CampaignEventRepository):
        self.customer_repo = customer_repo
        self.offer_repo = offer_repo
        self.offer_history_repo = offer_history_repo
        self.campaign_event_repo = campaign_event_repo

    async def process_lead_data(self, lead_data: LeadData) -> CustomerInDB:
        # Simplified logic for testing, actual logic would be more complex (FR3-FR6, FR25-FR32)
        customer = await self.customer_repo.get_by_identifiers(
            mobile_number=lead_data.mobile_number,
            pan_number=lead_data.pan_number,
            aadhaar_ref_number=lead_data.aadhaar_ref_number
        )

        if customer and customer.dnd_status: # FR34
            raise ValueError("Customer is on DND list.")

        if not customer:
            customer_id = uuid.uuid4()
            customer_create = CustomerCreate(
                mobile_number=lead_data.mobile_number,
                pan_number=lead_data.pan_number,
                aadhaar_ref_number=lead_data.aadhaar_ref_number,
                customer_attributes={"source": "lead_api"}
            )
            customer = await self.customer_repo.create(customer_create)
        else:
            # In a real scenario, existing customer attributes might be updated here.
            pass

        # Simplified offer creation/precedence logic.
        # Real implementation would involve checking existing offers and applying FR25-FR32.
        offer_id = uuid.uuid4()
        offer_create = OfferCreate(
            customer_id=customer.customer_id,
            offer_type="Fresh", # Or "Enrich" based on logic
            offer_status="Active",
            product_type=lead_data.loan_product,
            offer_details=lead_data.offer_details
        )
        new_offer = await self.offer_repo.create(offer_create)

        await self.offer_history_repo.create(OfferHistoryCreate(
            offer_id=new_offer.offer_id,
            customer_id=customer.customer_id,
            old_offer_status="N/A",
            new_offer_status="Active",
            change_reason="New lead offer via API"
        ))

        await self.campaign_event_repo.create(CampaignEventCreate(
            customer_id=customer.customer_id,
            offer_id=new_offer.offer_id,
            event_source="API",
            event_type="LEAD_GENERATED"
        ))

        return customer

    async def get_customer_profile(self, customer_id: uuid.UUID) -> dict:
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            return None

        offers = await self.offer_repo.get_active_offers_for_customer(customer_id)
        # In a real scenario, offer history and campaign events would also be fetched (FR23, FR33)
        return {
            "customer_id": customer.customer_id,
            "mobile_number": customer.mobile_number,
            "pan_number": customer.pan_number,
            "current_offer": offers[0].model_dump() if offers else None,
            "offer_history_summary": [], # Placeholder for FR23
            "journey_status": "Not Started", # Placeholder for FR50
            "segments": customer.customer_segments # Placeholder for FR17, FR24
        }

class AdminService:
    def __init__(self, customer_repo: CustomerRepository, offer_repo: OfferRepository, offer_history_repo: OfferHistoryRepository):
        self.customer_repo = customer_repo
        self.offer_repo = offer_repo
        self.offer_history_repo = offer_history_repo

    async def upload_customer_offers(self, file_content: str) -> tuple[io.StringIO, io.StringIO]:
        success_output = io.StringIO()
        error_output = io.StringIO()
        
        lines = file_content.strip().split('\n')
        if not lines:
            return success_output, error_output

        header = lines[0].split(',')
        data_rows = lines[1:]

        success_output.write(','.join(header) + ',status\n')
        error_output.write(','.join(header) + ',Error Desc\n')

        for row_str in data_rows:
            row_data = dict(zip(header, row_str.split(',')))
            mobile_number = row_data.get('mobile_number')
            product_type = row_data.get('product_type')

            # Basic validation (FR1, FR46)
            if not mobile_number or not product_type:
                error_output.write(row_str + ',Missing mobile_number or product_type\n')
                continue

            try:
                customer = await self.customer_repo.get_by_identifiers(mobile_number=mobile_number)
                if not customer:
                    customer_id = uuid.uuid4()
                    customer_create = CustomerCreate(
                        mobile_number=mobile_number,
                        pan_number=row_data.get('pan_number'),
                        aadhaar_ref_number=row_data.get('aadhaar_ref_number')
                    )
                    customer = await self.customer_repo.create(customer_create)

                offer_id = uuid.uuid4()
                offer_create = OfferCreate(
                    customer_id=customer.customer_id,
                    offer_type="Fresh", # Admin uploads are typically 'Fresh' or 'Prospect'
                    offer_status="Active",
                    product_type=product_type,
                    offer_details={"amount": row_data.get('amount', 'N/A')}
                )
                await self.offer_repo.create(offer_create)

                await self.offer_history_repo.create(OfferHistoryCreate(
                    offer_id=offer_id,
                    customer_id=customer.customer_id,
                    old_offer_status="N/A",
                    new_offer_status="Active",
                    change_reason="Admin portal upload"
                ))
                success_output.write(row_str + ',SUCCESS\n') # FR45
            except Exception as e:
                error_output.write(row_str + f',{str(e)}\n') # FR46
        
        success_output.seek(0)
        error_output.seek(0)
        return success_output, error_output

class CampaignService:
    def __init__(self, offer_repo: OfferRepository):
        self.offer_repo = offer_repo

    async def generate_moengage_file(self) -> io.StringIO: # FR54
        active_offers = await self.offer_repo.get_all_active_offers()
        
        output = io.StringIO()
        # Moengage file header (simplified, actual would be more detailed)
        output.write("customer_id,mobile_number,offer_id,product_type,offer_status,offer_details\n")

        for offer in active_offers:
            # In a real scenario, the offer object returned by the repository
            # would likely include the associated customer's mobile_number
            # via a JOIN or a separate lookup. For this mock, we'll assume
            # the offer object has a 'customer' attribute with 'mobile_number'.
            mock_mobile_number = "UNKNOWN"
            if hasattr(offer, 'customer') and offer.customer and hasattr(offer.customer, 'mobile_number'):
                mock_mobile_number = offer.customer.mobile_number
            else:
                # Fallback for mock if customer not attached
                mock_mobile_number = "9999999999" # Placeholder

            record = MoengageRecord(
                customer_id=offer.customer_id,
                mobile_number=mock_mobile_number,
                offer_id=offer.offer_id,
                product_type=offer.product_type,
                offer_status=offer.offer_status,
                offer_details=offer.offer_details
            )
            output.write(','.join(record.to_csv_row()) + '\n')
        
        output.seek(0)
        return output

class OfferService:
    def __init__(self, offer_repo: OfferRepository, offer_history_repo: OfferHistoryRepository):
        self.offer_repo = offer_repo
        self.offer_history_repo = offer_history_repo

    async def update_expired_offers(self):
        today = date.today()
        updated_count = 0
        
        # FR51: Mark offers as expired based on offer end dates for non-journey started customers.
        offers_to_expire_by_date = await self.offer_repo.get_offers_by_status_and_end_date(
            status="Active", end_date_before=today
        )
        
        for offer in offers_to_expire_by_date:
            if not offer.is_journey_started:
                old_status = offer.offer_status
                await self.offer_repo.update(offer.offer_id, {"offer_status": "Expired"})
                await self.offer_history_repo.create(OfferHistoryCreate(
                    offer_id=offer.offer_id,
                    customer_id=offer.customer_id,
                    old_offer_status=old_status,
                    new_offer_status="Expired",
                    change_reason="Offer end date passed (FR51)"
                ))
                updated_count += 1
        
        # FR53: Mark offers as expired within the offers data if the LAN validity post loan application journey start date is over.
        # This assumes `lan_validity_end_date` is a field on the OfferInDB model or accessible via offer_details.
        offers_to_expire_by_lan = await self.offer_repo.get_offers_by_status_and_lan_validity(
            status="Active", lan_validity_end_date_before=today
        )

        for offer in offers_to_expire_by_lan:
            if offer.is_journey_started and offer.loan_application_id:
                old_status = offer.offer_status
                await self.offer_repo.update(offer.offer_id, {"offer_status": "Expired"})
                await self.offer_history_repo.create(OfferHistoryCreate(
                    offer_id=offer.offer_id,
                    customer_id=offer.customer_id,
                    old_offer_status=old_status,
                    new_offer_status="Expired",
                    change_reason="LAN validity expired (FR53)"
                ))
                updated_count += 1
        return updated_count


# --- Pytest Fixtures for Mock Repositories ---
@pytest.fixture
def mock_customer_repo():
    return AsyncMock(spec=CustomerRepository)

@pytest.fixture
def mock_offer_repo():
    return AsyncMock(spec=OfferRepository)

@pytest.fixture
def mock_offer_history_repo():
    return AsyncMock(spec=OfferHistoryRepository)

@pytest.fixture
def mock_campaign_event_repo():
    return AsyncMock(spec=CampaignEventRepository)

# --- Pytest Fixtures for Services ---
@pytest.fixture
def customer_service(mock_customer_repo, mock_offer_repo, mock_offer_history_repo, mock_campaign_event_repo):
    return CustomerService(mock_customer_repo, mock_offer_repo, mock_offer_history_repo, mock_campaign_event_repo)

@pytest.fixture
def admin_service(mock_customer_repo, mock_offer_repo, mock_offer_history_repo):
    return AdminService(mock_customer_repo, mock_offer_repo, mock_offer_history_repo)

@pytest.fixture
def campaign_service(mock_offer_repo):
    return CampaignService(mock_offer_repo)

@pytest.fixture
def offer_service(mock_offer_repo, mock_offer_history_repo):
    return OfferService(mock_offer_repo, mock_offer_history_repo)

# --- Unit Tests for CustomerService ---
@pytest.mark.asyncio
async def test_process_lead_data_new_customer_new_offer(customer_service, mock_customer_repo, mock_offer_repo, mock_offer_history_repo, mock_campaign_event_repo):
    lead_data = LeadData(mobile_number="9876543210", loan_product="Preapproved", offer_details={"amount": 50000})
    
    mock_customer_repo.get_by_identifiers.return_value = None
    
    new_customer_id = uuid.uuid4()
    mock_customer_repo.create.return_value = CustomerInDB(
        customer_id=new_customer_id, mobile_number="9876543210"
    )
    
    new_offer_id = uuid.uuid4()
    mock_offer_repo.create.return_value = OfferInDB(
        offer_id=new_offer_id, customer_id=new_customer_id, offer_type="Fresh",
        offer_status="Active", product_type="Preapproved"
    )

    result_customer = await customer_service.process_lead_data(lead_data)

    mock_customer_repo.get_by_identifiers.assert_called_once_with(
        mobile_number="9876543210", pan_number=None, aadhaar_ref_number=None
    )
    mock_customer_repo.create.assert_called_once()
    assert mock_customer_repo.create.call_args.args[0].mobile_number == "9876543210"
    
    mock_offer_repo.create.assert_called_once()
    assert mock_offer_repo.create.call_args.args[0].customer_id == new_customer_id
    assert mock_offer_repo.create.call_args.args[0].product_type == "Preapproved"
    
    mock_offer_history_repo.create.assert_called_once()
    mock_campaign_event_repo.create.assert_called_once()
    assert result_customer.customer_id == new_customer_id

@pytest.mark.asyncio
async def test_process_lead_data_existing_customer_dnd(customer_service, mock_customer_repo, mock_offer_repo, mock_offer_history_repo, mock_campaign_event_repo):
    lead_data = LeadData(mobile_number="9876543210", loan_product="Preapproved")
    
    existing_customer = CustomerInDB(
        customer_id=uuid.uuid4(), mobile_number="9876543210", dnd_status=True
    )
    mock_customer_repo.get_by_identifiers.return_value = existing_customer

    with pytest.raises(ValueError, match="Customer is on DND list."):
        await customer_service.process_lead_data(lead_data)

    mock_customer_repo.get_by_identifiers.assert_called_once()
    mock_customer_repo.create.assert_not_called()
    mock_offer_repo.create.assert_not_called()
    mock_offer_history_repo.create.assert_not_called()
    mock_campaign_event_repo.create.assert_not_called()

@pytest.mark.asyncio
async def test_get_customer_profile_success(customer_service, mock_customer_repo, mock_offer_repo):
    customer_id = uuid.uuid4()
    mock_customer = CustomerInDB(customer_id=customer_id, mobile_number="1112223333", pan_number="ABCDE1234F")
    mock_offer = OfferInDB(
        offer_id=uuid.uuid4(), customer_id=customer_id, offer_type="Fresh",
        offer_status="Active", product_type="Loyalty", offer_details={"amount": 100000}
    )

    mock_customer_repo.get_by_id.return_value = mock_customer
    mock_offer_repo.get_active_offers_for_customer.return_value = [mock_offer]

    profile = await customer_service.get_customer_profile(customer_id)

    mock_customer_repo.get_by_id.assert_called_once_with(customer_id)
    mock_offer_repo.get_active_offers_for_customer.assert_called_once_with(customer_id)

    assert profile is not None
    assert profile["customer_id"] == customer_id
    assert profile["mobile_number"] == "1112223333"
    assert profile["current_offer"]["offer_id"] == mock_offer.offer_id
    assert profile["current_offer"]["product_type"] == "Loyalty"

@pytest.mark.asyncio
async def test_get_customer_profile_not_found(customer_service, mock_customer_repo):
    customer_id = uuid.uuid4()
    mock_customer_repo.get_by_id.return_value = None

    profile = await customer_service.get_customer_profile(customer_id)

    mock_customer_repo.get_by_id.assert_called_once_with(customer_id)
    assert profile is None

# --- Unit Tests for AdminService ---
@pytest.mark.asyncio
async def test_upload_customer_offers_success(admin_service, mock_customer_repo, mock_offer_repo, mock_offer_history_repo):
    csv_content = "mobile_number,pan_number,product_type,amount\n9998887770,ABCDE1234G,Prospect,50000\n9998887771,ABCDE1234H,Top-up,75000"
    
    mock_customer_repo.get_by_identifiers.side_effect = [None, None] # Both new customers
    mock_customer_repo.create.side_effect = [
        CustomerInDB(customer_id=uuid.uuid4(), mobile_number="9998887770"),
        CustomerInDB(customer_id=uuid.uuid4(), mobile_number="9998887771")
    ]
    mock_offer_repo.create.side_effect = [
        OfferInDB(offer_id=uuid.uuid4(), customer_id=uuid.uuid4(), offer_type="Fresh", offer_status="Active", product_type="Prospect"),
        OfferInDB(offer_id=uuid.uuid4(), customer_id=uuid.uuid4(), offer_type="Fresh", offer_status="Active", product_type="Top-up")
    ]
    mock_offer_history_repo.create.return_value = None # No specific return needed

    success_file, error_file = await admin_service.upload_customer_offers(csv_content)

    success_content = success_file.read()
    error_content = error_file.read()

    assert "mobile_number,pan_number,product_type,amount,status\n9998887770,ABCDE1234G,Prospect,50000,SUCCESS\n9998887771,ABCDE1234H,Top-up,75000,SUCCESS" in success_content
    assert "Error Desc" not in error_content # No errors expected
    assert mock_customer_repo.get_by_identifiers.call_count == 2
    assert mock_customer_repo.create.call_count == 2
    assert mock_offer_repo.create.call_count == 2
    assert mock_offer_history_repo.create.call_count == 2

@pytest.mark.asyncio
async def test_upload_customer_offers_with_errors(admin_service, mock_customer_repo, mock_offer_repo, mock_offer_history_repo):
    csv_content = "mobile_number,pan_number,product_type,amount\n9998887770,ABCDE1234G,Prospect,50000\n,ABCDE1234H,Top-up,75000\n9998887772,ABCDE1234I,,100000" # Second and third rows have errors
    
    mock_customer_repo.get_by_identifiers.return_value = None
    mock_customer_repo.create.return_value = CustomerInDB(customer_id=uuid.uuid4(), mobile_number="9998887770")
    mock_offer_repo.create.return_value = OfferInDB(offer_id=uuid.uuid4(), customer_id=uuid.uuid4(), offer_type="Fresh", offer_status="Active", product_type="Prospect")

    success_file, error_file = await admin_service.upload_customer_offers(csv_content)

    success_content = success_file.read()
    error_content = error_file.read()

    assert "9998887770,ABCDE1234G,Prospect,50000,SUCCESS" in success_content
    assert ",ABCDE1234H,Top-up,75000,Missing mobile_number or product_type" in error_content
    assert "9998887772,ABCDE1234I,,100000,Missing mobile_number or product_type" in error_content
    assert mock_customer_repo.get_by_identifiers.call_count == 1 # Only called for the first valid row
    assert mock_customer_repo.create.call_count == 1
    assert mock_offer_repo.create.call_count == 1
    assert mock_offer_history_repo.create.call_count == 1

# --- Unit Tests for CampaignService ---
@pytest.mark.asyncio
async def test_generate_moengage_file_with_offers(campaign_service, mock_offer_repo):
    customer_id_1 = uuid.uuid4()
    customer_id_2 = uuid.uuid4()
    offer_id_1 = uuid.uuid4()
    offer_id_2 = uuid.uuid4()

    mock_offers = [
        OfferInDB(offer_id=offer_id_1, customer_id=customer_id_1, offer_type="Fresh", offer_status="Active", product_type="Preapproved", offer_details={"amount": 100000}),
        OfferInDB(offer_id=offer_id_2, customer_id=customer_id_2, offer_type="Enrich", offer_status="Active", product_type="Loyalty", offer_details={"amount": 200000})
    ]
    # Attach mock customer objects to offers for mobile_number lookup simulation
    mock_offers[0].customer = MagicMock(mobile_number="1111111111")
    mock_offers[1].customer = MagicMock(mobile_number="2222222222")

    mock_offer_repo.get_all_active_offers.return_value = mock_offers

    moengage_file = await campaign_service.generate_moengage_file()
    content = moengage_file.read()

    assert "customer_id,mobile_number,offer_id,product_type,offer_status,offer_details" in content
    assert f"{customer_id_1},1111111111,{offer_id_1},Preapproved,Active,{{'amount': 100000}}" in content
    assert f"{customer_id_2},2222222222,{offer_id_2},Loyalty,Active,{{'amount': 200000}}" in content
    mock_offer_repo.get_all_active_offers.assert_called_once()

@pytest.mark.asyncio
async def test_generate_moengage_file_no_offers(campaign_service, mock_offer_repo):
    mock_offer_repo.get_all_active_offers.return_value = []

    moengage_file = await campaign_service.generate_moengage_file()
    content = moengage_file.read()

    assert "customer_id,mobile_number,offer_id,product_type,offer_status,offer_details" in content
    assert len(content.strip().split('\n')) == 1 # Only header
    mock_offer_repo.get_all_active_offers.assert_called_once()

# --- Unit Tests for OfferService ---
@pytest.mark.asyncio
async def test_update_expired_offers_by_end_date(offer_service, mock_offer_repo, mock_offer_history_repo):
    today = date.today()
    expired_offer_id = uuid.uuid4()
    
    # Offer that should expire by end date (FR51)
    expired_offer = OfferInDB(
        offer_id=expired_offer_id,
        customer_id=uuid.uuid4(),
        offer_type="Fresh",
        offer_status="Active",
        product_type="Prospect",
        offer_end_date=today - timedelta(days=1),
        is_journey_started=False
    )
    
    # Offer that should NOT expire (journey started, FR15)
    active_offer_journey_started = OfferInDB(
        offer_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        offer_type="Fresh",
        offer_status="Active",
        product_type="Preapproved",
        offer_end_date=today - timedelta(days=1),
        is_journey_started=True,
        loan_application_id="LAN123"
    )

    mock_offer_repo.get_offers_by_status_and_end_date.return_value = [expired_offer, active_offer_journey_started]
    mock_offer_repo.get_offers_by_status_and_lan_validity.return_value = [] # No LAN expiry for this test

    updated_count = await offer_service.update_expired_offers()

    mock_offer_repo.get_offers_by_status_and_end_date.assert_called_once_with(status="Active", end_date_before=today)
    mock_offer_repo.update.assert_called_once_with(expired_offer_id, {"offer_status": "Expired"})
    mock_offer_history_repo.create.assert_called_once()
    assert mock_offer_history_repo.create.call_args.args[0].offer_id == expired_offer_id
    assert mock_offer_history_repo.create.call_args.args[0].new_offer_status == "Expired"
    assert updated_count == 1 # Only one offer should be updated

@pytest.mark.asyncio
async def test_update_expired_offers_by_lan_validity(offer_service, mock_offer_repo, mock_offer_history_repo):
    today = date.today()
    expired_lan_offer_id = uuid.uuid4()

    # Offer that should expire by LAN validity (FR53)
    expired_lan_offer = OfferInDB(
        offer_id=expired_lan_offer_id,
        customer_id=uuid.uuid4(),
        offer_type="Fresh",
        offer_status="Active",
        product_type="Insta",
        is_journey_started=True,
        loan_application_id="LAN456",
    )
    # Manually set lan_validity_end_date for the mock object to simulate the condition
    expired_lan_offer.lan_validity_end_date = today - timedelta(days=1)

    mock_offer_repo.get_offers_by_status_and_end_date.return_value = [] # No end date expiry for this test
    mock_offer_repo.get_offers_by_status_and_lan_validity.return_value = [expired_lan_offer]

    updated_count = await offer_service.update_expired_offers()

    mock_offer_repo.get_offers_by_status_and_lan_validity.assert_called_once_with(status="Active", lan_validity_end_date_before=today)
    mock_offer_repo.update.assert_called_once_with(expired_lan_offer_id, {"offer_status": "Expired"})
    mock_offer_history_repo.create.assert_called_once()
    assert mock_offer_history_repo.create.call_args.args[0].offer_id == expired_lan_offer_id
    assert mock_offer_history_repo.create.call_args.args[0].new_offer_status == "Expired"
    assert updated_count == 1

@pytest.mark.asyncio
async def test_update_expired_offers_no_offers_to_expire(offer_service, mock_offer_repo, mock_offer_history_repo):
    today = date.today()
    mock_offer_repo.get_offers_by_status_and_end_date.return_value = []
    mock_offer_repo.get_offers_by_status_and_lan_validity.return_value = []

    updated_count = await offer_service.update_expired_offers()

    mock_offer_repo.get_offers_by_status_and_end_date.assert_called_once_with(status="Active", end_date_before=today)
    mock_offer_repo.get_offers_by_status_and_lan_validity.assert_called_once_with(status="Active", lan_validity_end_date_before=today)
    mock_offer_repo.update.assert_not_called()
    mock_offer_history_repo.create.assert_not_called()
    assert updated_count == 0