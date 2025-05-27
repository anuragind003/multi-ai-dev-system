import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from datetime import date, timedelta
import uuid

# Assuming these imports exist in your project structure
# You might need to adjust paths based on your actual project layout
from app.main import app
from app.database import Base, get_db
from app.models import Customer, Offer

# --- Database Setup for Tests ---
# Use an in-memory SQLite database for faster and isolated tests.
# This is suitable for integration tests focusing on application logic and ORM interactions.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """
    Fixture to set up and tear down the test database.
    Creates tables before tests, drops them after.
    This runs once per test session.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session():
    """
    Fixture to provide a new database session for each test.
    Rolls back changes after each test to ensure isolation.
    """
    connection = await engine.connect()
    transaction = await connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Override the get_db dependency in FastAPI to use the test session
    app.dependency_overrides[get_db] = lambda: session

    yield session

    await transaction.rollback()
    await connection.close()
    # Clear overrides after the test
    app.dependency_overrides = {}

@pytest.fixture
async def client(db_session):
    """
    Fixture to provide an AsyncClient for testing FastAPI endpoints.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

# --- Helper functions for creating and querying test data ---

async def create_customer_and_offer_in_db(
    session: AsyncSession,
    mobile_number: str = None,
    pan_number: str = None,
    aadhaar_ref_number: str = None,
    ucid_number: str = None,
    previous_loan_app_number: str = None,
    product_type: str = "Preapproved",
    offer_status: str = "Active",
    is_journey_started: bool = False,
    offer_details: dict = None,
    customer_id: uuid.UUID = None # Allow pre-existing customer_id for linking
):
    """Helper to create a customer and an offer directly in the database."""
    if customer_id:
        customer = await session.get(Customer, customer_id)
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} not found.")
    else:
        customer_data = {
            "customer_id": uuid.uuid4(),
            "mobile_number": mobile_number or f"987654321{uuid.uuid4().hex[:4]}",
            "pan_number": pan_number or f"ABCDE123{uuid.uuid4().hex[:2]}F",
            "aadhaar_ref_number": aadhaar_ref_number or f"{uuid.uuid4().hex[:12]}",
            "ucid_number": ucid_number or f"UCID{uuid.uuid4().hex[:8]}",
            "previous_loan_app_number": previous_loan_app_number or f"LAN{uuid.uuid4().hex[:8]}"
        }
        customer = Customer(**customer_data)
        session.add(customer)
        await session.flush() # To ensure customer_id is available for offer

    offer_data = {
        "offer_id": uuid.uuid4(),
        "customer_id": customer.customer_id,
        "offer_type": "Fresh", # Default to Fresh for initial offers
        "offer_status": offer_status,
        "product_type": product_type,
        "offer_details": offer_details or {"amount": 100000},
        "offer_start_date": date.today(),
        "offer_end_date": date.today() + timedelta(days=30),
        "is_journey_started": is_journey_started
    }
    offer = Offer(**offer_data)
    session.add(offer)
    await session.commit()
    await session.refresh(customer)
    await session.refresh(offer)
    return customer, offer

async def get_customer_and_offers_by_identifier(session: AsyncSession, **kwargs):
    """
    Helper to retrieve a customer and all their offers by any unique identifier.
    Kwargs can be mobile_number, pan_number, aadhaar_ref_number, ucid_number, previous_loan_app_number.
    """
    query = select(Customer)
    for key, value in kwargs.items():
        if value:
            query = query.where(getattr(Customer, key) == value)
            break # Assuming only one identifier is needed to find the customer

    result = await session.execute(query)
    customer = result.scalar_one_or_none()

    if customer:
        offers_result = await session.execute(
            select(Offer).where(Offer.customer_id == customer.customer_id).order_by(Offer.created_at.desc())
        )
        offers = offers_result.scalars().all()
        return customer, offers
    return None, []

# --- Integration Tests for Deduplication Flow ---

@pytest.mark.asyncio
async def test_new_customer_and_offer_creation(client: AsyncClient, db_session: AsyncSession):
    """
    Test FR3: A completely new customer and offer should be created when no matching identifiers exist.
    """
    mobile = "9999900001"
    pan = "ABCDE1111A"
    aadhaar = "111122223333"
    ucid = "UCID00001"
    loan_app_num = "LAN00001"

    payload = {
        "mobile_number": mobile,
        "pan_number": pan,
        "aadhaar_ref_number": aadhaar,
        "ucid_number": ucid,
        "previous_loan_app_number": loan_app_num,
        "loan_product": "Preapproved",
        "offer_details": {"amount": 150000}
    }

    response = await client.post("/api/v1/leads", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    customer_id = uuid.UUID(response.json()["customer_id"])

    customer, offers = await get_customer_and_offers_by_identifier(db_session, mobile_number=mobile)
    assert customer is not None
    assert customer.customer_id == customer_id
    assert len(offers) == 1
    assert offers[0].product_type == "Preapproved"
    assert offers[0].offer_status == "Active"

@pytest.mark.asyncio
async def test_duplicate_customer_mobile_number_new_offer_prevails_fr25(client: AsyncClient, db_session: AsyncSession):
    """
    Test FR3, FR5, FR25: Existing Pre-approved (no journey) + New CLEAG/Insta -> New CLEAG/Insta prevails, old expires.
    """
    mobile = "9999900002"
    pan = "ABCDE2222B"

    # Create an existing Preapproved offer with no journey started
    existing_customer, existing_offer = await create_customer_and_offer_in_db(
        db_session,
        mobile_number=mobile,
        pan_number=pan,
        product_type="Preapproved",
        is_journey_started=False,
        offer_status="Active"
    )
    await db_session.refresh(existing_offer)
    assert existing_offer.offer_status == "Active"

    # Submit a new Insta offer for the same customer (matching by mobile)
    new_payload = {
        "mobile_number": mobile,
        "pan_number": "ABCDE2222B_NEW", # PAN might be different, mobile is the key
        "loan_product": "Insta",
        "offer_details": {"amount": 200000}
    }
    response = await client.post("/api/v1/leads", json=new_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    new_customer_id = uuid.UUID(response.json()["customer_id"])

    # Verify that the customer ID is the same
    assert new_customer_id == existing_customer.customer_id

    # Verify the old offer is expired and the new offer is active
    customer, offers = await get_customer_and_offers_by_identifier(db_session, mobile_number=mobile)
    assert customer is not None
    assert len(offers) == 2 # Should have both offers now

    # Find the offers by their original IDs or properties
    updated_existing_offer = next((o for o in offers if o.offer_id == existing_offer.offer_id), None)
    newly_created_offer = next((o for o in offers if o.product_type == "Insta" and o.offer_status == "Active"), None)

    assert updated_existing_offer is not None
    assert newly_created_offer is not None

    assert updated_existing_offer.offer_status == "Expired" # FR25: old pre-approved expires
    assert newly_created_offer.offer_status == "Active"
    assert newly_created_offer.product_type == "Insta"

@pytest.mark.asyncio
async def test_duplicate_customer_pan_number_existing_offer_prevails_fr26(client: AsyncClient, db_session: AsyncSession):
    """
    Test FR3, FR5, FR26: Existing Pre-approved (journey started) + New CLEAG/Insta -> Existing Pre-approved prevails.
    """
    mobile = "9999900003"
    pan = "ABCDE3333C"

    # Create an existing Preapproved offer with journey started
    existing_customer, existing_offer = await create_customer_and_offer_in_db(
        db_session,
        mobile_number=mobile,
        pan_number=pan,
        product_type="Preapproved",
        is_journey_started=True, # Journey started
        offer_status="Active"
    )
    await db_session.refresh(existing_offer)
    assert existing_offer.offer_status == "Active"
    assert existing_offer.is_journey_started is True

    # Submit a new E-aggregator offer for the same customer (matching by PAN)
    new_payload = {
        "mobile_number": "9999900003_NEW", # Mobile might be different, PAN is the key
        "pan_number": pan,
        "loan_product": "E-aggregator",
        "offer_details": {"amount": 250000}
    }
    response = await client.post("/api/v1/leads", json=new_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    new_customer_id = uuid.UUID(response.json()["customer_id"])

    # Verify that the customer ID is the same
    assert new_customer_id == existing_customer.customer_id

    # Verify the old offer remains active and the new offer is marked as duplicate/inactive
    customer, offers = await get_customer_and_offers_by_identifier(db_session, pan_number=pan)
    assert customer is not None
    assert len(offers) == 2 # Should have both offers now

    updated_existing_offer = next((o for o in offers if o.offer_id == existing_offer.offer_id), None)
    newly_created_offer = next((o for o in offers if o.product_type == "E-aggregator"), None)

    assert updated_existing_offer is not None
    assert newly_created_offer is not None

    assert updated_existing_offer.offer_status == "Active" # FR26: existing pre-approved prevails
    assert newly_created_offer.offer_status == "Duplicate" # New offer should be marked as duplicate/inactive
    assert newly_created_offer.product_type == "E-aggregator"

@pytest.mark.asyncio
async def test_duplicate_customer_aadhaar_cleag_insta_prevails_fr27(client: AsyncClient, db_session: AsyncSession):
    """
    Test FR3, FR5, FR27: Existing CLEAG/Insta + New CLEAG/Insta (another channel) -> Previous prevails.
    """
    mobile = "9999900004"
    aadhaar = "444455556666"

    # Create an existing Insta offer
    existing_customer, existing_offer = await create_customer_and_offer_in_db(
        db_session,
        mobile_number=mobile,
        aadhaar_ref_number=aadhaar,
        product_type="Insta",
        is_journey_started=False, # Journey status doesn't matter for FR27
        offer_status="Active"
    )
    await db_session.refresh(existing_offer)
    assert existing_offer.offer_status == "Active"

    # Submit a new E-aggregator offer for the same customer (matching by Aadhaar)
    new_payload = {
        "mobile_number": "9999900004_NEW",
        "aadhaar_ref_number": aadhaar,
        "loan_product": "E-aggregator",
        "offer_details": {"amount": 300000}
    }
    response = await client.post("/api/v1/leads", json=new_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    new_customer_id = uuid.UUID(response.json()["customer_id"])

    # Verify that the customer ID is the same
    assert new_customer_id == existing_customer.customer_id

    # Verify the old offer remains active and the new offer is marked as duplicate/inactive
    customer, offers = await get_customer_and_offers_by_identifier(db_session, aadhaar_ref_number=aadhaar)
    assert customer is not None
    assert len(offers) == 2

    updated_existing_offer = next((o for o in offers if o.offer_id == existing_offer.offer_id), None)
    newly_created_offer = next((o for o in offers if o.product_type == "E-aggregator"), None)

    assert updated_existing_offer is not None
    assert newly_created_offer is not None

    assert updated_existing_offer.offer_status == "Active" # FR27: previous CLEAG/Insta prevails
    assert newly_created_offer.offer_status == "Duplicate"
    assert newly_created_offer.product_type == "E-aggregator"

@pytest.mark.asyncio
async def test_duplicate_customer_ucid_existing_twl_prevails_fr28(client: AsyncClient, db_session: AsyncSession):
    """
    Test FR3, FR5, FR28: Existing TWL + New CLEAG/Insta -> Existing TWL prevails.
    """
    mobile = "9999900005"
    ucid = "UCID00005"

    # Create an existing TW Loyalty offer
    existing_customer, existing_offer = await create_customer_and_offer_in_db(
        db_session,
        mobile_number=mobile,
        ucid_number=ucid,
        product_type="Loyalty", # TW Loyalty
        is_journey_started=False,
        offer_status="Active"
    )
    await db_session.refresh(existing_offer)
    assert existing_offer.offer_status == "Active"

    # Submit a new Insta offer for the same customer (matching by UCID)
    new_payload = {
        "mobile_number": "9999900005_NEW",
        "ucid_number": ucid,
        "loan_product": "Insta",
        "offer_details": {"amount": 350000}
    }
    response = await client.post("/api/v1/leads", json=new_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    new_customer_id = uuid.UUID(response.json()["customer_id"])

    # Verify that the customer ID is the same
    assert new_customer_id == existing_customer.customer_id

    # Verify the old offer remains active and the new offer is marked as duplicate/inactive
    customer, offers = await get_customer_and_offers_by_identifier(db_session, ucid_number=ucid)
    assert customer is not None
    assert len(offers) == 2

    updated_existing_offer = next((o for o in offers if o.offer_id == existing_offer.offer_id), None)
    newly_created_offer = next((o for o in offers if o.product_type == "Insta"), None)

    assert updated_existing_offer is not None
    assert newly_created_offer is not None

    assert updated_existing_offer.offer_status == "Active" # FR28: existing TWL prevails
    assert newly_created_offer.offer_status == "Duplicate"
    assert newly_created_offer.product_type == "Insta"

@pytest.mark.asyncio
async def test_duplicate_customer_loan_app_num_new_offer_not_uploaded_fr29(client: AsyncClient, db_session: AsyncSession):
    """
    Test FR3, FR5, FR29: Existing Pre-approved + New TW Loyalty -> New offer cannot be uploaded.
    This implies the new offer is rejected or not created.
    """
    mobile = "9999900006"
    loan_app_num = "LAN00006"

    # Create an existing Preapproved offer
    existing_customer, existing_offer = await create_customer_and_offer_in_db(
        db_session,
        mobile_number=mobile,
        previous_loan_app_number=loan_app_num,
        product_type="Preapproved",
        offer_status="Active"
    )
    await db_session.refresh(existing_offer)
    assert existing_offer.offer_status == "Active"

    # Submit a new TW Loyalty offer for the same customer (matching by previous_loan_app_number)
    new_payload = {
        "mobile_number": "9999900006_NEW",
        "previous_loan_app_number": loan_app_num,
        "loan_product": "Loyalty", # TW Loyalty
        "offer_details": {"amount": 400000}
    }
    response = await client.post("/api/v1/leads", json=new_payload)
    assert response.status_code == 200 # Assuming success status even if offer is rejected/not created
    assert response.json()["status"] == "success" # Or "rejected" / "ignored" depending on implementation
    customer_id_from_response = uuid.UUID(response.json()["customer_id"])

    assert customer_id_from_response == existing_customer.customer_id

    # Verify that only the original offer exists and is still active
    customer, offers = await get_customer_and_offers_by_identifier(db_session, previous_loan_app_number=loan_app_num)
    assert customer is not None
    assert len(offers) == 1 # Only the original offer should exist
    assert offers[0].offer_id == existing_offer.offer_id
    assert offers[0].offer_status == "Active"
    assert offers[0].product_type == "Preapproved"

@pytest.mark.asyncio
async def test_top_up_deduplication_fr6(client: AsyncClient, db_session: AsyncSession):
    """
    Test FR6: Top-up loan offers only against other Top-up offers, removing matches found.
    If a new Top-up offer comes for a customer who already has an active Top-up offer,
    the new one should be marked as duplicate/inactive.
    """
    mobile = "9999900007"
    pan = "ABCDE7777G"

    # Create an existing active Top-up offer
    existing_customer, existing_topup_offer = await create_customer_and_offer_in_db(
        db_session,
        mobile_number=mobile,
        pan_number=pan,
        product_type="Top-up",
        offer_status="Active"
    )
    await db_session.refresh(existing_topup_offer)
    assert existing_topup_offer.offer_status == "Active"

    # Submit a new Top-up offer for the same customer
    new_payload = {
        "mobile_number": mobile,
        "pan_number": pan,
        "loan_product": "Top-up",
        "offer_details": {"amount": 500000}
    }
    response = await client.post("/api/v1/leads", json=new_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    new_customer_id = uuid.UUID(response.json()["customer_id"])

    assert new_customer_id == existing_customer.customer_id

    # Verify that the new Top-up offer is marked as duplicate/inactive, and the old one remains active
    customer, offers = await get_customer_and_offers_by_identifier(db_session, mobile_number=mobile)
    assert customer is not None
    assert len(offers) == 2

    updated_existing_offer = next((o for o in offers if o.offer_id == existing_topup_offer.offer_id), None)
    newly_created_offer = next((o for o in offers if o.product_type == "Top-up" and o.offer_id != existing_topup_offer.offer_id), None)

    assert updated_existing_offer is not None
    assert newly_created_offer is not None

    assert updated_existing_offer.offer_status == "Active" # Existing Top-up should remain active
    assert newly_created_offer.offer_status == "Duplicate" # New Top-up should be marked duplicate

@pytest.mark.asyncio
async def test_top_up_deduplication_against_non_top_up_fr6_negative(client: AsyncClient, db_session: AsyncSession):
    """
    Test FR6 (negative case): Top-up offer should NOT deduplicate against a non-Top-up offer.
    Both should remain active (assuming no other precedence rules apply).
    """
    mobile = "9999900008"
    pan = "ABCDE8888H"

    # Create an existing active Preapproved offer
    existing_customer, existing_preapproved_offer = await create_customer_and_offer_in_db(
        db_session,
        mobile_number=mobile,
        pan_number=pan,
        product_type="Preapproved",
        offer_status="Active"
    )
    await db_session.refresh(existing_preapproved_offer)
    assert existing_preapproved_offer.offer_status == "Active"

    # Submit a new Top-up offer for the same customer
    new_payload = {
        "mobile_number": mobile,
        "pan_number": pan,
        "loan_product": "Top-up",
        "offer_details": {"amount": 600000}
    }
    response = await client.post("/api/v1/leads", json=new_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    new_customer_id = uuid.UUID(response.json()["customer_id"])

    assert new_customer_id == existing_customer.customer_id

    # Verify that both offers remain active (as Top-up only deduplicates against other Top-ups)
    customer, offers = await get_customer_and_offers_by_identifier(db_session, mobile_number=mobile)
    assert customer is not None
    assert len(offers) == 2

    updated_existing_offer = next((o for o in offers if o.offer_id == existing_preapproved_offer.offer_id), None)
    newly_created_offer = next((o for o in offers if o.product_type == "Top-up"), None)

    assert updated_existing_offer is not None
    assert newly_created_offer is not None

    assert updated_existing_offer.offer_status == "Active"
    assert newly_created_offer.offer_status == "Active" # New Top-up should be active

@pytest.mark.asyncio
async def test_enrich_offer_no_journey_fr20(client: AsyncClient, db_session: AsyncSession):
    """
    Test FR20: If an Enrich offer's journey has not started, it shall flow to CDP,
    and the previous offer will be moved to Duplicate.
    """
    mobile = "9999900009"
    pan = "ABCDE9999I"

    # Create an existing active Preapproved offer (which will be the "previous" offer)
    existing_customer, previous_offer = await create_customer_and_offer_in_db(
        db_session,
        mobile_number=mobile,
        pan_number=pan,
        product_type="Preapproved",
        offer_status="Active",
        is_journey_started=False
    )
    await db_session.refresh(previous_offer)
    assert previous_offer.offer_status == "Active"

    # Submit a new Enrich offer for the same customer
    new_payload = {
        "mobile_number": mobile,
        "pan_number": pan,
        "loan_product": "Preapproved", # Enrich offers are typically for the same product
        "offer_type": "Enrich", # Assuming API can specify offer_type
        "offer_details": {"amount": 700000, "new_detail": "enriched"}
    }
    response = await client.post("/api/v1/leads", json=new_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    new_customer_id = uuid.UUID(response.json()["customer_id"])

    assert new_customer_id == existing_customer.customer_id

    # Verify that the new Enrich offer is active and the previous one is duplicated
    customer, offers = await get_customer_and_offers_by_identifier(db_session, mobile_number=mobile)
    assert customer is not None
    assert len(offers) == 2

    updated_previous_offer = next((o for o in offers if o.offer_id == previous_offer.offer_id), None)
    newly_created_enrich_offer = next((o for o in offers if o.offer_type == "Enrich"), None)

    assert updated_previous_offer is not None
    assert newly_created_enrich_offer is not None

    assert updated_previous_offer.offer_status == "Duplicate" # Previous offer moved to Duplicate
    assert newly_created_enrich_offer.offer_status == "Active" # New Enrich offer is active
    assert newly_created_enrich_offer.offer_type == "Enrich"

@pytest.mark.asyncio
async def test_enrich_offer_journey_started_fr21(client: AsyncClient, db_session: AsyncSession):
    """
    Test FR21: If an Enrich offer's journey has started, it shall not flow into CDP.
    This means the new offer should be rejected/not created, and the existing one remains active.
    """
    mobile = "9999900010"
    pan = "ABCDE0000J"

    # Create an existing active Preapproved offer with journey started
    existing_customer, existing_offer = await create_customer_and_offer_in_db(
        db_session,
        mobile_number=mobile,
        pan_number=pan,
        product_type="Preapproved",
        offer_status="Active",
        is_journey_started=True # Journey started
    )
    await db_session.refresh(existing_offer)
    assert existing_offer.offer_status == "Active"
    assert existing_offer.is_journey_started is True

    # Submit a new Enrich offer for the same customer
    new_payload = {
        "mobile_number": mobile,
        "pan_number": pan,
        "loan_product": "Preapproved",
        "offer_type": "Enrich",
        "offer_details": {"amount": 800000, "new_detail": "enriched_attempt"}
    }
    response = await client.post("/api/v1/leads", json=new_payload)
    assert response.status_code == 200 # Assuming success status even if offer is rejected/not created
    assert response.json()["status"] == "success" # Or "rejected" / "ignored" depending on implementation
    customer_id_from_response = uuid.UUID(response.json()["customer_id"])

    assert customer_id_from_response == existing_customer.customer_id

    # Verify that only the original offer exists and is still active
    customer, offers = await get_customer_and_offers_by_identifier(db_session, mobile_number=mobile)
    assert customer is not None
    assert len(offers) == 1 # Only the original offer should exist
    assert offers[0].offer_id == existing_offer.offer_id
    assert offers[0].offer_status == "Active"
    assert offers[0].is_journey_started is True

@pytest.mark.asyncio
async def test_new_prospect_offer_rejected_by_existing_twl_fr31(client: AsyncClient, db_session: AsyncSession):
    """
    Test FR31: If a customer receives a TW Loyalty offer first and then receives a Prospect offer,
    the new offer cannot be uploaded. (Assuming TW Loyalty is 'stronger' than Prospect)
    """
    mobile = "9999900011"
    pan = "ABCDE1111K"

    # Create an existing TW Loyalty offer
    existing_customer, existing_offer = await create_customer_and_offer_in_db(
        db_session,
        mobile_number=mobile,
        pan_number=pan,
        product_type="Loyalty", # TW Loyalty
        offer_status="Active"
    )
    await db_session.refresh(existing_offer)
    assert existing_offer.offer_status == "Active"

    # Submit a new Prospect offer for the same customer
    new_payload = {
        "mobile_number": mobile,
        "pan_number": pan,
        "loan_product": "Prospect",
        "offer_details": {"amount": 50000}
    }
    response = await client.post("/api/v1/leads", json=new_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    customer_id_from_response = uuid.UUID(response.json()["customer_id"])

    assert customer_id_from_response == existing_customer.customer_id

    # Verify that only the original TW Loyalty offer exists and is still active
    customer, offers = await get_customer_and_offers_by_identifier(db_session, mobile_number=mobile)
    assert customer is not None
    assert len(offers) == 1
    assert offers[0].offer_id == existing_offer.offer_id
    assert offers[0].offer_status == "Active"
    assert offers[0].product_type == "Loyalty"

@pytest.mark.asyncio
async def test_new_employee_loan_offer_rejected_by_existing_topup_fr30(client: AsyncClient, db_session: AsyncSession):
    """
    Test FR30: If a customer receives a Topup offer first and then receives an Employee loan offer,
    the new offer cannot be uploaded. (Assuming Topup is 'stronger' than Employee Loan)
    """
    mobile = "9999900012"
    pan = "ABCDE2222L"

    # Create an existing Top-up offer
    existing_customer, existing_offer = await create_customer_and_offer_in_db(
        db_session,
        mobile_number=mobile,
        pan_number=pan,
        product_type="Top-up",
        offer_status="Active"
    )
    await db_session.refresh(existing_offer)
    assert existing_offer.offer_status == "Active"

    # Submit a new Employee Loan offer for the same customer
    new_payload = {
        "mobile_number": mobile,
        "pan_number": pan,
        "loan_product": "Employee Loan",
        "offer_details": {"amount": 100000}
    }
    response = await client.post("/api/v1/leads", json=new_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    customer_id_from_response = uuid.UUID(response.json()["customer_id"])

    assert customer_id_from_response == existing_customer.customer_id

    # Verify that only the original Top-up offer exists and is still active
    customer, offers = await get_customer_and_offers_by_identifier(db_session, mobile_number=mobile)
    assert customer is not None
    assert len(offers) == 1
    assert offers[0].offer_id == existing_offer.offer_id
    assert offers[0].offer_status == "Active"
    assert offers[0].product_type == "Top-up"