import pytest
import asyncio
import uuid
from datetime import datetime, date, timezone
import os

# --- Minimal Application Components for Testing ---
# In a real project, these would be imported from your actual app code
# (e.g., from `app.database`, `app.models`).
# For this exercise, we define them here to make the file self-contained and runnable.

from databases import Database
import sqlalchemy

# Define a test database URL.
# It's highly recommended to use a dedicated test database (e.g., via Docker, testcontainers)
# to ensure isolation and prevent data corruption in development/production databases.
# For this example, we use an environment variable, defaulting to a common local PostgreSQL setup.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql://user:password@localhost:5432/test_cdp_db")

# Initialize the database client
database = Database(TEST_DATABASE_URL)

# Define SQLAlchemy metadata and table schemas
metadata = sqlalchemy.MetaData()

customers_table = sqlalchemy.Table(
    "customers",
    metadata,
    sqlalchemy.Column("customer_id", sqlalchemy.UUID, primary_key=True),
    sqlalchemy.Column("mobile_number", sqlalchemy.String(20), unique=True),
    sqlalchemy.Column("pan_number", sqlalchemy.String(10), unique=True),
    sqlalchemy.Column("aadhaar_ref_number", sqlalchemy.String(12), unique=True),
    sqlalchemy.Column("ucid_number", sqlalchemy.String(50), unique=True),
    sqlalchemy.Column("previous_loan_app_number", sqlalchemy.String(50), unique=True),
    sqlalchemy.Column("customer_attributes", sqlalchemy.JSONB),
    sqlalchemy.Column("customer_segments", sqlalchemy.ARRAY(sqlalchemy.Text)),
    sqlalchemy.Column("propensity_flag", sqlalchemy.String(50)),
    sqlalchemy.Column("dnd_status", sqlalchemy.Boolean, default=False),
    sqlalchemy.Column("created_at", sqlalchemy.TIMESTAMP(timezone=True), default=sqlalchemy.func.now()),
    sqlalchemy.Column("updated_at", sqlalchemy.TIMESTAMP(timezone=True), default=sqlalchemy.func.now(), onupdate=sqlalchemy.func.now()),
)

offers_table = sqlalchemy.Table(
    "offers",
    metadata,
    sqlalchemy.Column("offer_id", sqlalchemy.UUID, primary_key=True),
    sqlalchemy.Column("customer_id", sqlalchemy.UUID, sqlalchemy.ForeignKey("customers.customer_id")),
    sqlalchemy.Column("offer_type", sqlalchemy.String(50)), # e.g., 'Fresh', 'Enrich', 'New-old', 'New-new'
    sqlalchemy.Column("offer_status", sqlalchemy.String(50)), # e.g., 'Active', 'Inactive', 'Expired', 'Duplicate'
    sqlalchemy.Column("product_type", sqlalchemy.String(50)), # e.g., 'Loyalty', 'Preapproved', 'E-aggregator', 'Insta', 'Top-up', 'Employee Loan'
    sqlalchemy.Column("offer_details", sqlalchemy.JSONB), # Flexible storage for offer specific data
    sqlalchemy.Column("offer_start_date", sqlalchemy.Date),
    sqlalchemy.Column("offer_end_date", sqlalchemy.Date),
    sqlalchemy.Column("is_journey_started", sqlalchemy.Boolean, default=False),
    sqlalchemy.Column("loan_application_id", sqlalchemy.String(50)), # Populated if journey started
    sqlalchemy.Column("created_at", sqlalchemy.TIMESTAMP(timezone=True), default=sqlalchemy.func.now()),
    sqlalchemy.Column("updated_at", sqlalchemy.TIMESTAMP(timezone=True), default=sqlalchemy.func.now(), onupdate=sqlalchemy.func.now()),
)

offer_history_table = sqlalchemy.Table(
    "offer_history",
    metadata,
    sqlalchemy.Column("history_id", sqlalchemy.UUID, primary_key=True),
    sqlalchemy.Column("offer_id", sqlalchemy.UUID, sqlalchemy.ForeignKey("offers.offer_id")),
    sqlalchemy.Column("customer_id", sqlalchemy.UUID, sqlalchemy.ForeignKey("customers.customer_id")),
    sqlalchemy.Column("change_timestamp", sqlalchemy.TIMESTAMP(timezone=True), default=sqlalchemy.func.now()),
    sqlalchemy.Column("old_offer_status", sqlalchemy.String(50)),
    sqlalchemy.Column("new_offer_status", sqlalchemy.String(50)),
    sqlalchemy.Column("change_reason", sqlalchemy.Text),
    sqlalchemy.Column("snapshot_offer_details", sqlalchemy.JSONB), # Snapshot of offer details at the time of change
)

campaign_events_table = sqlalchemy.Table(
    "campaign_events",
    metadata,
    sqlalchemy.Column("event_id", sqlalchemy.UUID, primary_key=True),
    sqlalchemy.Column("customer_id", sqlalchemy.UUID, sqlalchemy.ForeignKey("customers.customer_id")),
    sqlalchemy.Column("offer_id", sqlalchemy.UUID, sqlalchemy.ForeignKey("offers.offer_id")), # Can be null if not tied to a specific offer
    sqlalchemy.Column("event_source", sqlalchemy.String(50)), # e.g., 'Moengage', 'LOS'
    sqlalchemy.Column("event_type", sqlalchemy.String(100)), # e.g., 'SMS_SENT', 'CLICK', 'CONVERSION', 'LOGIN'
    sqlalchemy.Column("event_details", sqlalchemy.JSONB), # Raw event data
    sqlalchemy.Column("event_timestamp", sqlalchemy.TIMESTAMP(timezone=True), default=sqlalchemy.func.now()),
)

# --- End Minimal Application Components ---


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """
    Set up the test database: connect, create tables, and disconnect.
    This runs once per test session.
    """
    engine = sqlalchemy.create_engine(TEST_DATABASE_URL)
    # Drop all tables to ensure a clean slate for the session
    metadata.drop_all(engine)
    # Create all tables
    metadata.create_all(engine)
    engine.dispose()  # Dispose of the engine after creating tables

    await database.connect()
    yield
    await database.disconnect()


@pytest.fixture(autouse=True)
async def clean_tables():
    """
    Clean up tables after each test by deleting all rows.
    This ensures test isolation.
    """
    yield
    # Delete all data from tables in reverse order of dependency
    await database.execute(campaign_events_table.delete())
    await database.execute(offer_history_table.delete())
    await database.execute(offers_table.delete())
    await database.execute(customers_table.delete())


# Helper function to insert a customer
async def insert_customer(customer_data: dict):
    customer_id = customer_data.get("customer_id", uuid.uuid4())
    # Ensure unique fields are present or handled for the test
    if "mobile_number" not in customer_data:
        customer_data["mobile_number"] = str(uuid.uuid4())[:10] # Generate unique dummy
    if "pan_number" not in customer_data:
        customer_data["pan_number"] = str(uuid.uuid4())[:10].upper()
    if "aadhaar_ref_number" not in customer_data:
        customer_data["aadhaar_ref_number"] = str(uuid.uuid4())[:12]
    if "ucid_number" not in customer_data:
        customer_data["ucid_number"] = str(uuid.uuid4())[:10]
    if "previous_loan_app_number" not in customer_data:
        customer_data["previous_loan_app_number"] = str(uuid.uuid4())[:10]

    query = customers_table.insert().values(customer_id=customer_id, **customer_data)
    await database.execute(query)
    return customer_id


# Helper function to insert an offer
async def insert_offer(offer_data: dict):
    offer_id = offer_data.get("offer_id", uuid.uuid4())
    query = offers_table.insert().values(offer_id=offer_id, **offer_data)
    await database.execute(query)
    return offer_id


# --- Test Cases ---

@pytest.mark.asyncio
async def test_create_customer():
    """
    Test that a customer can be successfully created in the database.
    (FR2, FR3, FR17)
    """
    customer_id = uuid.uuid4()
    customer_data = {
        "customer_id": customer_id,
        "mobile_number": "9876543210",
        "pan_number": "ABCDE1234F",
        "aadhaar_ref_number": "123456789012",
        "ucid_number": "UCID001",
        "previous_loan_app_number": "PREVLOAN001",
        "customer_attributes": {"age": 30, "city": "Mumbai"},
        "customer_segments": ["C1", "C5"],
        "propensity_flag": "High",
        "dnd_status": False,
    }
    await insert_customer(customer_data)

    # Verify insertion
    query = customers_table.select().where(customers_table.c.customer_id == customer_id)
    result = await database.fetch_one(query)

    assert result is not None
    assert result["mobile_number"] == "9876543210"
    assert result["pan_number"] == "ABCDE1234F"
    assert result["customer_segments"] == ["C1", "C5"]
    assert result["propensity_flag"] == "High"


@pytest.mark.asyncio
async def test_create_offer_for_customer():
    """
    Test that an offer can be successfully created and linked to a customer.
    (FR18, FR19)
    """
    customer_id = uuid.uuid4()
    await insert_customer({
        "customer_id": customer_id,
        "mobile_number": "9988776655",
        "pan_number": "FGHIJ5678K",
        "aadhaar_ref_number": "234567890123",
        "ucid_number": "UCID002",
        "previous_loan_app_number": "PREVLOAN002",
    })

    offer_id = uuid.uuid4()
    offer_data = {
        "offer_id": offer_id,
        "customer_id": customer_id,
        "offer_type": "Fresh",
        "offer_status": "Active",
        "product_type": "Preapproved",
        "offer_details": {"amount": 100000, "interest_rate": 10.5},
        "offer_start_date": date.today(),
        "offer_end_date": date.today().replace(year=date.today().year + 1),
        "is_journey_started": False,
    }
    await insert_offer(offer_data)

    # Verify insertion
    query = offers_table.select().where(offers_table.c.offer_id == offer_id)
    result = await database.fetch_one(query)

    assert result is not None
    assert result["customer_id"] == customer_id
    assert result["offer_status"] == "Active"
    assert result["product_type"] == "Preapproved"
    assert result["offer_details"]["amount"] == 100000


@pytest.mark.asyncio
async def test_deduplication_on_mobile_number_constraint():
    """
    Test basic deduplication logic: inserting a customer with an existing mobile number
    should raise a unique constraint violation, as per the schema design.
    (FR3)
    """
    customer_id_1 = uuid.uuid4()
    mobile_number = "1112223334"
    await insert_customer({
        "customer_id": customer_id_1,
        "mobile_number": mobile_number,
        "pan_number": "PAN1",
        "aadhaar_ref_number": "AADHAAR1",
        "ucid_number": "UCID1",
        "previous_loan_app_number": "PREVLOAN1",
    })

    # Attempt to insert another customer with the same mobile number
    customer_id_2 = uuid.uuid4()
    with pytest.raises(Exception) as excinfo:  # Expecting a database error, e.g., UniqueViolationError
        await insert_customer({
            "customer_id": customer_id_2,
            "mobile_number": mobile_number,
            "pan_number": "PAN2",  # Different PAN
            "aadhaar_ref_number": "AADHAAR2",
            "ucid_number": "UCID2",
            "previous_loan_app_number": "PREVLOAN2",
        })
    # Check if the error message indicates a unique constraint violation
    # The exact error message might vary slightly by PostgreSQL version or driver,
    # so checking for common substrings or the exception type name.
    assert "duplicate key value violates unique constraint" in str(excinfo.value) or \
           "UniqueViolation" in str(excinfo.type.__name__)

    # Verify that only the first customer exists
    query = customers_table.select().where(customers_table.c.mobile_number == mobile_number)
    results = await database.fetch_all(query)
    assert len(results) == 1
    assert results[0]["customer_id"] == customer_id_1


@pytest.mark.asyncio
async def test_update_offer_status_and_history_creation():
    """
    Test updating an offer's status and verifying that an offer history entry is created.
    (FR18, FR23)
    """
    customer_id = uuid.uuid4()
    await insert_customer({
        "customer_id": customer_id,
        "mobile_number": "5554443332",
        "pan_number": "LMNOP9876Q",
        "aadhaar_ref_number": "345678901234",
        "ucid_number": "UCID003",
        "previous_loan_app_number": "PREVLOAN003",
    })

    offer_id = uuid.uuid4()
    initial_offer_data = {
        "offer_id": offer_id,
        "customer_id": customer_id,
        "offer_type": "Fresh",
        "offer_status": "Active",
        "product_type": "Loyalty",
        "offer_details": {"amount": 50000, "tenure": 12},
        "offer_start_date": date.today(),
        "offer_end_date": date.today().replace(year=date.today().year + 1),
        "is_journey_started": False,
    }
    await insert_offer(initial_offer_data)

    # Update offer status
    new_status = "Expired"
    update_query = offers_table.update().where(offers_table.c.offer_id == offer_id).values(offer_status=new_status)
    await database.execute(update_query)

    # Verify offer status updated
    query_offer = offers_table.select().where(offers_table.c.offer_id == offer_id)
    updated_offer = await database.fetch_one(query_offer)
    assert updated_offer["offer_status"] == new_status

    # For offer history, this would typically be handled by a trigger or application logic.
    # Since this is an integration test for DB operations, we simulate the application logic
    # that would insert into `offer_history` upon status change.
    history_id = uuid.uuid4()
    await database.execute(offer_history_table.insert().values(
        history_id=history_id,
        offer_id=offer_id,
        customer_id=customer_id,
        old_offer_status=initial_offer_data["offer_status"],
        new_offer_status=new_status,
        change_reason="Offer expired due to business logic",
        snapshot_offer_details=initial_offer_data["offer_details"]
    ))

    # Verify offer history entry
    query_history = offer_history_table.select().where(offer_history_table.c.offer_id == offer_id)
    history_entries = await database.fetch_all(query_history)
    assert len(history_entries) == 1
    assert history_entries[0]["old_offer_status"] == initial_offer_data["offer_status"]
    assert history_entries[0]["new_offer_status"] == new_status
    assert history_entries[0]["change_reason"] == "Offer expired due to business logic"


@pytest.mark.asyncio
async def test_retrieve_customer_with_offers():
    """
    Test retrieving a customer and their associated offers, simulating a single profile view.
    (FR2, FR50)
    """
    customer_id = uuid.uuid4()
    await insert_customer({
        "customer_id": customer_id,
        "mobile_number": "1231231230",
        "pan_number": "PQRST1234U",
        "aadhaar_ref_number": "456789012345",
        "ucid_number": "UCID004",
        "previous_loan_app_number": "PREVLOAN004",
        "customer_attributes": {"income": 50000},
        "customer_segments": ["C2"],
    })

    offer_id_1 = uuid.uuid4()
    await insert_offer({
        "offer_id": offer_id_1,
        "customer_id": customer_id,
        "offer_type": "Fresh",
        "offer_status": "Active",
        "product_type": "Preapproved",
        "offer_details": {"amount": 200000},
        "offer_start_date": date.today(),
        "offer_end_date": date.today().replace(year=date.today().year + 1),
    })

    offer_id_2 = uuid.uuid4()
    await insert_offer({
        "offer_id": offer_id_2,
        "customer_id": customer_id,
        "offer_type": "Enrich",
        "offer_status": "Inactive",
        "product_type": "Top-up",
        "offer_details": {"amount": 50000},
        "offer_start_date": date.today(),
        "offer_end_date": date.today().replace(year=date.today().year + 1),
    })

    # Simulate a join query to get customer and their offers
    join_query = sqlalchemy.select(
        customers_table,
        offers_table.c.offer_id,
        offers_table.c.offer_type,
        offers_table.c.offer_status,
        offers_table.c.product_type,
        offers_table.c.offer_details
    ).select_from(
        customers_table.join(offers_table, customers_table.c.customer_id == offers_table.c.customer_id)
    ).where(customers_table.c.customer_id == customer_id)

    results = await database.fetch_all(join_query)

    assert len(results) == 2  # Two offers for this customer
    assert results[0]["mobile_number"] == "1231231230"
    assert results[0]["customer_segments"] == ["C2"]

    # Check offer details
    offer_statuses = {r["offer_status"] for r in results}
    product_types = {r["product_type"] for r in results}
    assert "Active" in offer_statuses
    assert "Inactive" in offer_statuses
    assert "Preapproved" in product_types
    assert "Top-up" in product_types


@pytest.mark.asyncio
async def test_offer_expiry_logic_non_journey_started():
    """
    Test that offers for non-journey started customers can be marked as expired
    based on offer end dates. (FR51)
    """
    customer_id = uuid.uuid4()
    await insert_customer({
        "customer_id": customer_id,
        "mobile_number": "1122334455",
        "pan_number": "EXPIRED123",
        "aadhaar_ref_number": "111111111111",
        "ucid_number": "UCIDEXPIRED",
        "previous_loan_app_number": "PREVLOANEXPIRED",
    })

    # Create an offer that should be expired (end date in the past)
    offer_id = uuid.uuid4()
    expired_offer_data = {
        "offer_id": offer_id,
        "customer_id": customer_id,
        "offer_type": "Fresh",
        "offer_status": "Active",
        "product_type": "Preapproved",
        "offer_details": {"amount": 100000},
        "offer_start_date": date(2023, 1, 1),
        "offer_end_date": date(2023, 1, 31),  # Past date
        "is_journey_started": False,
    }
    await insert_offer(expired_offer_data)

    # Simulate the scheduled job that marks offers as expired
    # This would be a separate function in your application, e.g., `mark_expired_offers`
    today = date.today()
    offers_to_expire_query = offers_table.select().where(
        (offers_table.c.offer_status == "Active") &
        (offers_table.c.is_journey_started == False) &
        (offers_table.c.offer_end_date < today)
    )
    expired_offers = await database.fetch_all(offers_to_expire_query)

    assert len(expired_offers) == 1
    assert expired_offers[0]["offer_id"] == offer_id

    # Update the status in the database (as the application would do)
    update_query = offers_table.update().where(offers_table.c.offer_id == offer_id).values(offer_status="Expired")
    await database.execute(update_query)

    # Verify the status is updated
    query_offer = offers_table.select().where(offers_table.c.offer_id == offer_id)
    updated_offer = await database.fetch_one(query_offer)
    assert updated_offer["offer_status"] == "Expired"


@pytest.mark.asyncio
async def test_event_data_storage():
    """
    Test storing event data from Moengage/LOS. (FR33)
    """
    customer_id = uuid.uuid4()
    await insert_customer({
        "customer_id": customer_id,
        "mobile_number": "6677889900",
        "pan_number": "EVENT1234E",
        "aadhaar_ref_number": "222222222222",
        "ucid_number": "UCIDEVENT",
        "previous_loan_app_number": "PREVLOANEVENT",
    })

    offer_id = uuid.uuid4()
    await insert_offer({
        "offer_id": offer_id,
        "customer_id": customer_id,
        "offer_type": "Fresh",
        "offer_status": "Active",
        "product_type": "Preapproved",
        "offer_details": {"amount": 100000},
        "offer_start_date": date.today(),
        "offer_end_date": date.today().replace(year=date.today().year + 1),
    })

    event_id = uuid.uuid4()
    event_data = {
        "event_id": event_id,
        "customer_id": customer_id,
        "offer_id": offer_id,
        "event_source": "Moengage",
        "event_type": "SMS_DELIVERED",
        "event_details": {"campaign_id": "CMP001", "message_id": "MSG001"},
        "event_timestamp": datetime.now(timezone.utc)
    }

    insert_event_query = campaign_events_table.insert().values(**event_data)
    await database.execute(insert_event_query)

    # Verify event insertion
    query_event = campaign_events_table.select().where(campaign_events_table.c.event_id == event_id)
    result_event = await database.fetch_one(query_event)

    assert result_event is not None
    assert result_event["customer_id"] == customer_id
    assert result_event["offer_id"] == offer_id
    assert result_event["event_source"] == "Moengage"
    assert result_event["event_type"] == "SMS_DELIVERED"
    assert result_event["event_details"]["campaign_id"] == "CMP001"