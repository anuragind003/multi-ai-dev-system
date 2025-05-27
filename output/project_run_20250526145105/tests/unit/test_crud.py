import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select
import uuid
from datetime import datetime, date, timedelta
import json

# Assuming models are defined in app.models
from app.models import Base, Customer, Offer, OfferHistory, CampaignEvent
# Assuming CRUD functions are defined in app.crud
from app.crud import (
    create_customer, get_customer, update_customer,
    create_offer, get_offer, update_offer_status,
    create_campaign_event, get_offer_history_by_offer_id
)
# Assuming Pydantic schemas are defined in app.schemas
from app.schemas import (
    CustomerCreate, CustomerUpdate,
    OfferCreate, OfferUpdateStatus,
    CampaignEventCreate
)

# --- Test Database Setup ---
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def async_session_test_db():
    """
    Fixture for an asynchronous SQLAlchemy session connected to an in-memory SQLite database.
    Creates tables before each test and drops them after.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncTestingSessionLocal = async_sessionmaker(
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
        bind=engine,
        class_=AsyncSession
    )

    async with AsyncTestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

# --- Test Data Fixtures ---

@pytest.fixture
def customer_create_data_payload():
    """Pydantic payload for creating a new customer."""
    return CustomerCreate(
        mobile_number="9876543210",
        pan_number="ABCDE1234F",
        aadhaar_ref_number="123456789012",
        ucid_number="UCID12345",
        previous_loan_app_number="PLN001",
        customer_attributes={"age": 30, "city": "Mumbai"},
        customer_segments=["C1", "C5"],
        propensity_flag="High",
        dnd_status=False
    )

@pytest.fixture
def customer_update_data_payload():
    """Pydantic payload for updating an existing customer."""
    return CustomerUpdate(
        customer_attributes={"age": 31, "city": "Delhi"},
        customer_segments=["C1", "C2"],
        propensity_flag="Medium",
        dnd_status=True
    )

@pytest_asyncio.fixture
async def created_customer(async_session_test_db, customer_create_data_payload):
    """Fixture to create and return a customer in the test database."""
    session = async_session_test_db
    customer = await create_customer(session, customer_create_data_payload)
    return customer

@pytest.fixture
def offer_create_data_payload(created_customer: Customer):
    """Pydantic payload for creating a new offer, dependent on a created customer."""
    return OfferCreate(
        customer_id=created_customer.customer_id,
        offer_type="Fresh",
        offer_status="Active",
        product_type="Preapproved",
        offer_details={"loan_amount": 100000, "interest_rate": 9.5},
        offer_start_date=date.today(),
        offer_end_date=date.today() + timedelta(days=30),
        is_journey_started=False,
        loan_application_id=None
    )

@pytest_asyncio.fixture
async def created_offer(async_session_test_db, offer_create_data_payload):
    """Fixture to create and return an offer in the test database."""
    session = async_session_test_db
    offer = await create_offer(session, offer_create_data_payload)
    return offer

@pytest.fixture
def offer_update_status_payload():
    """Pydantic payload for updating an offer's status."""
    return OfferUpdateStatus(
        new_status="Expired",
        change_reason="Offer end date passed"
    )

@pytest.fixture
def campaign_event_create_data_payload(created_customer: Customer, created_offer: Offer):
    """Pydantic payload for creating a new campaign event, dependent on created customer and offer."""
    return CampaignEventCreate(
        customer_id=created_customer.customer_id,
        offer_id=created_offer.offer_id,
        event_source="Moengage",
        event_type="SMS_DELIVERED",
        event_details={"campaign_id": "CMP001", "message": "Your loan offer is delivered."}
    )

# --- Tests ---

@pytest.mark.asyncio
async def test_create_and_get_customer(async_session_test_db, customer_create_data_payload):
    """Test creating a customer and then retrieving it."""
    session = async_session_test_db
    customer = await create_customer(session, customer_create_data_payload)

    assert customer.customer_id is not None
    assert customer.mobile_number == customer_create_data_payload.mobile_number
    assert customer.pan_number == customer_create_data_payload.pan_number
    assert customer.customer_attributes == customer_create_data_payload.customer_attributes
    assert customer.customer_segments == customer_create_data_payload.customer_segments

    retrieved_customer = await get_customer(session, customer.customer_id)
    assert retrieved_customer is not None
    assert retrieved_customer.customer_id == customer.customer_id
    assert retrieved_customer.mobile_number == customer.mobile_number

@pytest.mark.asyncio
async def test_update_customer(async_session_test_db, created_customer, customer_update_data_payload):
    """Test updating an existing customer's details."""
    session = async_session_test_db
    
    updated_customer = await update_customer(session, created_customer.customer_id, customer_update_data_payload)

    assert updated_customer is not None
    assert updated_customer.customer_id == created_customer.customer_id
    assert updated_customer.customer_attributes == customer_update_data_payload.customer_attributes
    assert updated_customer.dnd_status == customer_update_data_payload.dnd_status
    assert updated_customer.propensity_flag == customer_update_data_payload.propensity_flag
    assert updated_customer.customer_segments == customer_update_data_payload.customer_segments

    # Verify changes persisted in the database
    retrieved_customer = await get_customer(session, created_customer.customer_id)
    assert retrieved_customer.customer_attributes == customer_update_data_payload.customer_attributes
    assert retrieved_customer.dnd_status == customer_update_data_payload.dnd_status

@pytest.mark.asyncio
async def test_create_and_get_offer(async_session_test_db, created_customer, offer_create_data_payload):
    """Test creating an offer and then retrieving it."""
    session = async_session_test_db
    # offer_create_data_payload already includes created_customer.customer_id from its fixture dependency
    offer = await create_offer(session, offer_create_data_payload)

    assert offer.offer_id is not None
    assert offer.customer_id == created_customer.customer_id
    assert offer.offer_status == "Active"
    assert offer.product_type == "Preapproved"
    assert offer.offer_details == offer_create_data_payload.offer_details

    retrieved_offer = await get_offer(session, offer.offer_id)
    assert retrieved_offer is not None
    assert retrieved_offer.offer_id == offer.offer_id
    assert retrieved_offer.customer_id == created_customer.customer_id

@pytest.mark.asyncio
async def test_update_offer_status_and_history(async_session_test_db, created_customer, created_offer, offer_update_status_payload):
    """Test updating an offer's status and verifying that offer history is recorded."""
    session = async_session_test_db
    
    updated_offer = await update_offer_status(session, created_offer.offer_id, offer_update_status_payload)

    assert updated_offer is not None
    assert updated_offer.offer_id == created_offer.offer_id
    assert updated_offer.offer_status == "Expired"

    # Verify offer history record
    history_records = await get_offer_history_by_offer_id(session, created_offer.offer_id)
    assert len(history_records) == 1
    history_record = history_records[0]
    assert history_record.offer_id == created_offer.offer_id
    assert history_record.customer_id == created_customer.customer_id
    assert history_record.old_offer_status == "Active" # Initial status from created_offer fixture
    assert history_record.new_offer_status == "Expired"
    assert history_record.change_reason == "Offer end date passed"
    # The snapshot should be of the offer details *before* the status update
    assert history_record.snapshot_offer_details == created_offer.offer_details

@pytest.mark.asyncio
async def test_create_campaign_event(async_session_test_db, created_customer, created_offer, campaign_event_create_data_payload):
    """Test creating a campaign event."""
    session = async_session_test_db
    
    campaign_event = await create_campaign_event(session, campaign_event_create_data_payload)

    assert campaign_event.event_id is not None
    assert campaign_event.customer_id == created_customer.customer_id
    assert campaign_event.offer_id == created_offer.offer_id
    assert campaign_event.event_source == "Moengage"
    assert campaign_event.event_type == "SMS_DELIVERED"
    assert campaign_event.event_details == campaign_event_create_data_payload.event_details

    # Verify retrieval by querying directly (assuming no specific get_campaign_event function for simplicity)
    result = await session.execute(
        select(CampaignEvent).where(CampaignEvent.event_id == campaign_event.event_id)
    )
    retrieved_event = result.scalar_one_or_none()
    assert retrieved_event is not None
    assert retrieved_event.event_id == campaign_event.event_id
    assert retrieved_event.event_details == campaign_event_create_data_payload.event_details