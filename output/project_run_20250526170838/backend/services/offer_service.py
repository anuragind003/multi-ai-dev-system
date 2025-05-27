import uuid
from datetime import datetime, date, timedelta
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OfferService:
    """
    Service layer for managing customer offers.
    Handles creation, retrieval, status updates, and expiration logic
    for offers based on business requirements.
    """

    def __init__(self, db_connection_pool):
        """
        Initializes the OfferService with a database connection pool.
        This pool is expected to provide connections that can execute SQL queries.
        """
        self.db_connection_pool = db_connection_pool

    def _execute_query(self, query: str, params: tuple = None,
                       fetch_one: bool = False, fetch_all: bool = False):
        """
        Helper method to execute database queries.
        Manages connection acquisition, cursor creation, execution,
        commit/rollback, and connection release.
        """
        conn = None
        cursor = None
        try:
            conn = self.db_connection_pool.getconn()
            cursor = conn.cursor()
            cursor.execute(query, params)
            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
            conn.commit()
            return True  # Indicate successful DML operation
        except Exception as e:
            logger.error(f"Database error during query execution: {e}")
            if conn:
                conn.rollback()
            raise  # Re-raise the exception after logging and rollback
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db_connection_pool.putconn(conn)

    def create_offer(self, customer_id: str, offer_data: dict) -> dict:
        """
        Creates a new offer for a given customer.

        Args:
            customer_id: The ID of the customer.
            offer_data: Dictionary containing offer details.
                        Expected keys: 'offer_type', 'propensity',
                        'start_date' (YYYY-MM-DD), 'end_date' (YYYY-MM-DD),
                        'channel'. 'offer_status' defaults to 'Active'.

        Returns:
            A dictionary of the created offer, including its new offer_id,
            or None if creation fails.
        Raises:
            ValueError: If date formats are invalid.
            Exception: For database-related errors.
        """
        offer_id = str(uuid.uuid4())
        offer_type = offer_data.get('offer_type')
        offer_status = offer_data.get('offer_status', 'Active')
        propensity = offer_data.get('propensity')
        start_date_str = offer_data.get('start_date')
        end_date_str = offer_data.get('end_date')
        channel = offer_data.get('channel')

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() \
                if start_date_str else date.today()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() \
                if end_date_str else date.today() + timedelta(days=30)
        except ValueError as e:
            logger.error(f"Invalid date format for offer creation: {e}")
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")

        query = """
            INSERT INTO offers (
                offer_id, customer_id, offer_type, offer_status, propensity,
                start_date, end_date, channel
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING offer_id, customer_id, offer_type, offer_status,
                      propensity, start_date, end_date, channel,
                      created_at, updated_at;
        """
        params = (
            offer_id, customer_id, offer_type, offer_status, propensity,
            start_date, end_date, channel
        )
        try:
            result = self._execute_query(query, params, fetch_one=True)
            if result:
                columns = [
                    "offer_id", "customer_id", "offer_type", "offer_status",
                    "propensity", "start_date", "end_date", "channel",
                    "created_at", "updated_at"
                ]
                return dict(zip(columns, result))
            return None
        except Exception as e:
            logger.error(f"Failed to create offer for customer {customer_id}: {e}")
            raise

    def get_offer_by_id(self, offer_id: str) -> dict | None:
        """
        Retrieves a single offer by its ID.

        Args:
            offer_id: The unique identifier of the offer.

        Returns:
            A dictionary representing the offer, or None if not found.
        """
        query = """
            SELECT offer_id, customer_id, offer_type, offer_status,
                   propensity, start_date, end_date, channel,
                   created_at, updated_at
            FROM offers
            WHERE offer_id = %s;
        """
        params = (offer_id,)
        try:
            result = self._execute_query(query, params, fetch_one=True)
            if result:
                columns = [
                    "offer_id", "customer_id", "offer_type", "offer_status",
                    "propensity", "start_date", "end_date", "channel",
                    "created_at", "updated_at"
                ]
                return dict(zip(columns, result))
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve offer {offer_id}: {e}")
            raise

    def get_offers_by_customer(self, customer_id: str,
                               status: str = None) -> list[dict]:
        """
        Retrieves all offers for a given customer, optionally filtered by status.

        Args:
            customer_id: The ID of the customer.
            status: Optional. Filter offers by this status ('Active',
                    'Inactive', 'Expired').

        Returns:
            A list of dictionaries, each representing an offer.
            Returns an empty list if no offers are found.
        """
        query = """
            SELECT offer_id, customer_id, offer_type, offer_status,
                   propensity, start_date, end_date, channel,
                   created_at, updated_at
            FROM offers
            WHERE customer_id = %s
        """
        params = [customer_id]
        if status:
            query += " AND offer_status = %s"
            params.append(status)
        query += " ORDER BY created_at DESC;"

        try:
            results = self._execute_query(query, tuple(params), fetch_all=True)
            if results:
                columns = [
                    "offer_id", "customer_id", "offer_type", "offer_status",
                    "propensity", "start_date", "end_date", "channel",
                    "created_at", "updated_at"
                ]
                return [dict(zip(columns, row)) for row in results]
            return []
        except Exception as e:
            logger.error(f"Failed to retrieve offers for customer "
                         f"{customer_id}: {e}")
            raise

    def update_offer_status(self, offer_id: str, new_status: str) -> bool:
        """
        Updates the status of an offer. (FR16)
        Prevents modification if a loan application journey has started. (FR14)

        Args:
            offer_id: The ID of the offer to update.
            new_status: The new status ('Active', 'Inactive', 'Expired').

        Returns:
            True if the status was updated successfully, False otherwise.
        Raises:
            ValueError: If the new_status is invalid.
            Exception: For database-related errors.
        """
        if new_status not in ['Active', 'Inactive', 'Expired']:
            raise ValueError("Invalid offer status. Must be 'Active', "
                             "'Inactive', or 'Expired'.")

        if not self.can_modify_offer(offer_id):
            logger.warning(f"Offer {offer_id} cannot be modified due to "
                           f"an active loan application journey. (FR14)")
            return False

        query = """
            UPDATE offers
            SET offer_status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE offer_id = %s;
        """
        params = (new_status, offer_id)
        try:
            return self._execute_query(query, params)
        except Exception as e:
            logger.error(f"Failed to update status for offer {offer_id}: {e}")
            raise

    def can_modify_offer(self, offer_id: str) -> bool:
        """
        Checks if an offer can be modified based on FR14.
        An offer cannot be modified if its associated customer has a
        'LOAN_LOGIN' or similar 'journey started' event, and the
        corresponding loan application is not yet expired or rejected.
        (Simplified for MVP: checks for any journey-start event within 6 months).

        Args:
            offer_id: The ID of the offer to check.

        Returns:
            True if the offer can be modified, False otherwise.
        """
        offer = self.get_offer_by_id(offer_id)
        if not offer:
            logger.warning(f"Offer {offer_id} not found for modification check.")
            return True  # If offer doesn't exist, no journey to block

        customer_id = offer['customer_id']

        # Check for 'LOAN_LOGIN' or similar events indicating journey started (FR26)
        # Assuming a journey is considered active for 6 months unless explicitly
        # marked as rejected/disbursed. This interval needs refinement (Q16).
        query = """
            SELECT EXISTS (
                SELECT 1 FROM events
                WHERE customer_id = %s
                AND event_type IN (
                    'LOAN_LOGIN', 'BUREAU_CHECK', 'EKYC_ACHIEVED'
                )
                AND event_timestamp > (CURRENT_TIMESTAMP - INTERVAL '6 months')
                AND NOT EXISTS (
                    SELECT 1 FROM events
                    WHERE customer_id = %s
                    AND event_type IN ('REJECTED', 'DISBURSEMENT')
                    AND event_timestamp > (
                        SELECT MAX(event_timestamp) FROM events
                        WHERE customer_id = %s
                        AND event_type IN ('LOAN_LOGIN', 'BUREAU_CHECK', 'EKYC_ACHIEVED')
                    )
                )
            );
        """
        params = (customer_id, customer_id, customer_id)
        try:
            has_active_journey = self._execute_query(
                query, params, fetch_one=True
            )[0]
            return not has_active_journey
        except Exception as e:
            logger.error(f"Error checking modification eligibility for "
                         f"offer {offer_id} (customer {customer_id}): {e}")
            # Default to allowing modification if check fails to avoid blocking
            return True

    def expire_offers_based_on_end_date(self) -> int:
        """
        Marks offers as 'Expired' if their end_date is in the past
        and they are not associated with an active loan application journey. (FR41)
        This method is intended to be called by a scheduled background job.

        Returns:
            The number of offers that were marked as 'Expired'.
        """
        query = """
            UPDATE offers o
            SET offer_status = 'Expired', updated_at = CURRENT_TIMESTAMP
            WHERE o.offer_status = 'Active'
            AND o.end_date < CURRENT_DATE
            AND NOT EXISTS (
                SELECT 1 FROM events e
                WHERE e.customer_id = o.customer_id
                AND e.event_type IN (
                    'LOAN_LOGIN', 'BUREAU_CHECK', 'EKYC_ACHIEVED'
                )
                AND e.event_timestamp > (CURRENT_TIMESTAMP - INTERVAL '6 months')
                -- This interval needs to be defined by Q16 (LAN validity)
                AND NOT EXISTS (
                    SELECT 1 FROM events e2
                    WHERE e2.customer_id = o.customer_id
                    AND e2.event_type IN ('REJECTED', 'DISBURSEMENT')
                    AND e2.event_timestamp > (
                        SELECT MAX(event_timestamp) FROM events
                        WHERE customer_id = o.customer_id
                        AND event_type IN ('LOAN_LOGIN', 'BUREAU_CHECK', 'EKYC_ACHIEVED')
                    )
                )
            );
        """
        conn = None
        cursor = None
        try:
            conn = self.db_connection_pool.getconn()
            cursor = conn.cursor()
            cursor.execute(query)
            rows_affected = cursor.rowcount
            conn.commit()
            logger.info(f"Expired {rows_affected} offers based on end date. (FR41)")
            return rows_affected
        except Exception as e:
            logger.error(f"Failed to expire offers based on end date: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db_connection_pool.putconn(conn)

    def expire_journey_started_offers_by_lan_validity(self) -> int:
        """
        Marks offers as 'Expired' for customers whose loan application journey
        (LAN) validity is over. (FR43)
        (Simplified for MVP: assumes journey is over if no new relevant events
        for 30 days and no disbursement). This needs specific business logic (Q16).
        This method is intended to be called by a scheduled background job.

        Returns:
            The number of offers that were marked as 'Expired'.
        """
        query = """
            UPDATE offers o
            SET offer_status = 'Expired', updated_at = CURRENT_TIMESTAMP
            WHERE o.offer_status = 'Active'
            AND EXISTS (
                SELECT 1 FROM events e
                WHERE e.customer_id = o.customer_id
                AND e.event_type IN (
                    'LOAN_LOGIN', 'BUREAU_CHECK', 'OFFER_DETAILS', 'EKYC_ACHIEVED'
                )
                GROUP BY e.customer_id
                HAVING MAX(e.event_timestamp) < (CURRENT_TIMESTAMP - INTERVAL '30 days')
                AND NOT EXISTS (
                    SELECT 1 FROM events e2
                    WHERE e2.customer_id = o.customer_id
                    AND e2.event_type = 'DISBURSEMENT'
                )
            );
        """
        conn = None
        cursor = None
        try:
            conn = self.db_connection_pool.getconn()
            cursor = conn.cursor()
            cursor.execute(query)
            rows_affected = cursor.rowcount
            conn.commit()
            logger.info(f"Expired {rows_affected} offers based on LAN validity. (FR43)")
            return rows_affected
        except Exception as e:
            logger.error(f"Failed to expire journey-started offers: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db_connection_pool.putconn(conn)

    def check_and_replenish_offers(self, customer_id: str) -> bool:
        """
        Checks if a customer needs new offers to be replenished. (FR42)
        A customer needs replenishment if they do not have an active loan
        application journey and all their previous offers have expired.
        This method only checks the condition, it does not create new offers.

        Args:
            customer_id: The ID of the customer to check.

        Returns:
            True if the customer needs offers replenished, False otherwise.
        """
        # 1. Check if customer has any active loan journey
        # Reusing the logic from can_modify_offer for active journey check
        # Note: can_modify_offer checks if an *offer* can be modified,
        # here we need to check if the *customer* has an active journey.
        # The underlying query is similar.
        customer_has_active_journey_query = """
            SELECT EXISTS (
                SELECT 1 FROM events
                WHERE customer_id = %s
                AND event_type IN (
                    'LOAN_LOGIN', 'BUREAU_CHECK', 'EKYC_ACHIEVED'
                )
                AND event_timestamp > (CURRENT_TIMESTAMP - INTERVAL '6 months')
                AND NOT EXISTS (
                    SELECT 1 FROM events
                    WHERE customer_id = %s
                    AND event_type IN ('REJECTED', 'DISBURSEMENT')
                    AND event_timestamp > (
                        SELECT MAX(event_timestamp) FROM events
                        WHERE customer_id = %s
                        AND event_type IN ('LOAN_LOGIN', 'BUREAU_CHECK', 'EKYC_ACHIEVED')
                    )
                )
            );
        """
        try:
            has_active_journey = self._execute_query(
                customer_has_active_journey_query,
                (customer_id, customer_id, customer_id),
                fetch_one=True
            )[0]

            if has_active_journey:
                logger.info(f"Customer {customer_id} has an active journey. "
                            f"No replenishment needed. (FR42)")
                return False

            # 2. Check if all previous offers are expired (no active offers)
            all_offers_expired_query = """
                SELECT NOT EXISTS (
                    SELECT 1 FROM offers
                    WHERE customer_id = %s
                    AND offer_status = 'Active'
                );
            """
            all_offers_expired = self._execute_query(
                all_offers_expired_query, (customer_id,), fetch_one=True
            )[0]

            if all_offers_expired:
                logger.info(f"Customer {customer_id} has no active offers "
                            f"and no active journey. Replenishment needed. (FR42)")
                return True
            else:
                logger.info(f"Customer {customer_id} still has active offers. "
                            f"No replenishment needed. (FR42)")
                return False
        except Exception as e:
            logger.error(f"Error checking replenishment for customer "
                         f"{customer_id}: {e}")
            raise

    def apply_attribution_logic(self, customer_id: str) -> dict | None:
        """
        Implements attribution logic to determine which channel/offer prevails
        when a customer has multiple interactions or existing offers. (FR21)
        (Simplified for MVP: Prioritizes based on disbursement, then latest
        journey start, then latest active offer).

        Args:
            customer_id: The ID of the customer for whom to apply attribution.

        Returns:
            A dictionary representing the attributed offer, or None if no
            clear attribution can be made.
        """
        offers = self.get_offers_by_customer(customer_id)
        if not offers:
            return None

        events_query = """
            SELECT event_type, event_timestamp, event_details
            FROM events
            WHERE customer_id = %s
            ORDER BY event_timestamp DESC;
        """
        try:
            raw_events = self._execute_query(
                events_query, (customer_id,), fetch_all=True
            )
            event_columns = ["event_type", "event_timestamp", "event_details"]
            events = [dict(zip(event_columns, row)) for row in raw_events]
        except Exception as e:
            logger.error(f"Failed to retrieve events for attribution for "
                         f"customer {customer_id}: {e}")
            events = []

        # Rule 1: Prioritize offers leading to 'DISBURSEMENT'
        disbursement_events = [
            e for e in events if e['event_type'] == 'DISBURSEMENT'
        ]
        if disbursement_events:
            # In a real system, event_details might contain offer_id or LAN
            # to directly link. For MVP, we'll assume the latest active offer
            # is the one that led to disbursement if one exists.
            active_offers = [o for o in offers if o['offer_status'] == 'Active']
            if active_offers:
                logger.info(f"Attribution: Customer {customer_id} has "
                            f"disbursement. Attributing to latest active offer.")
                return max(active_offers, key=lambda x: x['updated_at'])
            return None

        # Rule 2: Prioritize the latest 'Active' offer that led to a
        # 'LOAN_LOGIN' or similar journey start event.
        journey_started_events = [
            e for e in events if e['event_type'] in (
                'LOAN_LOGIN', 'EKYC_ACHIEVED', 'OFFER_DETAILS'
            )
        ]
        if journey_started_events:
            latest_journey_event_time = max(
                e['event_timestamp'] for e in journey_started_events
            )
            # Find active offers that were valid around the time of the event
            relevant_offers = [
                o for o in offers
                if o['offer_status'] == 'Active'
                and o['start_date'] <= latest_journey_event_time.date()
                and o['end_date'] >= latest_journey_event_time.date()
            ]
            if relevant_offers:
                logger.info(f"Attribution: Customer {customer_id} has "
                            f"journey started. Attributing to latest relevant offer.")
                return max(relevant_offers, key=lambda x: x['updated_at'])

        # Rule 3: If no journey started, prioritize the latest 'Active' offer.
        active_offers = [o for o in offers if o['offer_status'] == 'Active']
        if active_offers:
            logger.info(f"Attribution: Customer {customer_id} has no journey. "
                        f"Attributing to latest active offer.")
            return max(active_offers, key=lambda x: x['updated_at'])

        logger.info(f"No specific attribution found for customer {customer_id}. "
                    f"Returning None. (FR21)")
        return None

    def get_offer_history(self, customer_id: str,
                          months: int = 6) -> list[dict]:
        """
        Retrieves offer history for a customer for the past N months. (FR19)

        Args:
            customer_id: The ID of the customer.
            months: The number of months for which to retrieve history.
                    Defaults to 6 months.

        Returns:
            A list of dictionaries, each representing an offer from the history.
            Returns an empty list if no history is found.
        """
        past_date = datetime.now() - timedelta(days=months * 30)
        query = """
            SELECT offer_id, customer_id, offer_type, offer_status,
                   propensity, start_date, end_date, channel,
                   created_at, updated_at
            FROM offers
            WHERE customer_id = %s
            AND created_at >= %s
            ORDER BY created_at DESC;
        """
        params = (customer_id, past_date)
        try:
            results = self._execute_query(query, params, fetch_all=True)
            if results:
                columns = [
                    "offer_id", "customer_id", "offer_type", "offer_status",
                    "propensity", "start_date", "end_date", "channel",
                    "created_at", "updated_at"
                ]
                return [dict(zip(columns, row)) for row in results]
            return []
        except Exception as e:
            logger.error(f"Failed to retrieve offer history for customer "
                         f"{customer_id}: {e}")
            raise

# Mock database connection pool for demonstration purposes.
# In a real Flask application, this would typically be a proper
# connection pool (e.g., psycopg2.pool.SimpleConnectionPool)
# or managed by an ORM like Flask-SQLAlchemy.
class MockDBConnectionPool:
    """
    A mock database connection pool for testing the OfferService
    without a real PostgreSQL database.
    """
    def getconn(self):
        class MockCursor:
            def __init__(self):
                self._last_result = None
                self.rowcount = 0

            def execute(self, query, params=None):
                logger.debug(f"Mock DB: Executing query: {query} with params: {params}")
                if "INSERT INTO offers" in query:
                    # Simulate returning inserted data
                    self._last_result = (
                        str(uuid.uuid4()), params[0], params[1], params[2],
                        params[3], params[4], params[5], params[6],
                        datetime.now(), datetime.now()
                    )
                    self.rowcount = 1
                elif "SELECT" in query and "FROM offers" in query:
                    if "WHERE offer_id" in query:
                        # Simulate a single offer retrieval
                        self._last_result = (
                            params[0], "cust_mock_123", "Fresh", "Active",
                            "High", date.today(), date.today() + timedelta(30),
                            "Web", datetime.now(), datetime.now()
                        )
                    elif "WHERE customer_id" in query:
                        # Simulate multiple offers for a customer
                        self._last_result = [
                            (
                                str(uuid.uuid4()), params[0], "Fresh",
                                "Active", "High", date.today(),
                                date.today() + timedelta(30), "Web",
                                datetime.now(), datetime.now()
                            ),
                            (
                                str(uuid.uuid4()), params[0], "Enrich",
                                "Expired", "Medium",
                                date.today() - timedelta(60),
                                date.today() - timedelta(30), "App",
                                datetime.now() - timedelta(60),
                                datetime.now() - timedelta(30)
                            )
                        ]
                    elif "SELECT NOT EXISTS" in query and "FROM offers" in query:
                        # Simulate check for no active offers
                        self._last_result = (True,) # No active offers
                elif "SELECT EXISTS" in query and "FROM events" in query:
                    # Simulate check for active journey (False = no active journey)
                    self._last_result = (False,)
                elif "UPDATE offers" in query:
                    self.rowcount = 1 # Simulate one row affected
                else:
                    self._last_result = None
                    self.rowcount = 0

            def fetchone(self):
                return self._last_result if isinstance(self._last_result, tuple) else None

            def fetchall(self):
                return self._last_result if isinstance(self._last_result, list) else []

            def close(self):
                pass

        class MockConnection:
            def cursor(self):
                return MockCursor()

            def commit(self):
                logger.debug("Mock DB: Commit")

            def rollback(self):
                logger.debug("Mock DB: Rollback")

        return MockConnection()

    def putconn(self, conn):
        logger.debug("Mock DB: Connection returned to pool")

# Example usage (for demonstration and testing this file directly)
if __name__ == "__main__":
    # Initialize the service with a mock DB connection pool
    mock_db_pool = MockDBConnectionPool()
    offer_service = OfferService(mock_db_pool)

    customer_id_test = str(uuid.uuid4())
    offer_data_test = {
        "offer_type": "Fresh",
        "propensity": "High",
        "start_date": "2023-01-01",
        "end_date": "2023-01-31",
        "channel": "Web"
    }

    print("--- Creating Offer ---")
    try:
        new_offer = offer_service.create_offer(customer_id_test, offer_data_test)
        print(f"Created Offer: {new_offer}")
        offer_id_test = new_offer['offer_id']
    except Exception as e:
        print(f"Error creating offer: {e}")
        offer_id_test = None

    if offer_id_test:
        print("\n--- Getting Offer by ID ---")
        retrieved_offer = offer_service.get_offer_by_id(offer_id_test)
        print(f"Retrieved Offer: {retrieved_offer}")

        print("\n--- Getting Offers by Customer ---")
        customer_offers = offer_service.get_offers_by_customer(customer_id_test)
        print(f"Customer Offers: {customer_offers}")

        print("\n--- Updating Offer Status (Inactive) ---")
        try:
            # Temporarily modify mock to allow modification for testing
            # (as default mock has no journey events)
            status_updated = offer_service.update_offer_status(
                offer_id_test, 'Inactive'
            )
            print(f"Status updated to Inactive: {status_updated}")
            retrieved_offer_after_update = offer_service.get_offer_by_id(
                offer_id_test
            )
            print(f"Offer after update: {retrieved_offer_after_update}")
        except Exception as e:
            print(f"Error updating offer status: {e}")

        print("\n--- Checking if offer can be modified (simulating journey) ---")
        # Simulate an active journey by creating a new service instance
        # with a mock that returns True for active journey check
        class MockCursorWithJourney:
            def execute(self, query, params=None):
                if "SELECT EXISTS" in query and "FROM events" in query:
                    self._last_result = (True,) # Simulate active journey
                else:
                    self._last_result = None
            def fetchone(self): return self._last_result
            def fetchall(self): return []
            def close(self): pass
        class MockConnectionWithJourney:
            def cursor(self): return MockCursorWithJourney()
            def commit(self): pass
            def rollback(self): pass
        class MockDBConnectionPoolWithJourney:
            def getconn(self): return MockConnectionWithJourney()
            def putconn(self, conn): pass

        offer_service_with_journey = OfferService(
            MockDBConnectionPoolWithJourney()
        )
        can_modify = offer_service_with_journey.can_modify_offer(offer_id_test)
        print(f"Can modify offer with simulated active journey: {can_modify}")

        print("\n--- Expiring Offers based on End Date ---")
        # Use a mock that simulates offers being expired
        class MockCursorForExpiry:
            def execute(self, query, params=None):
                if "UPDATE offers" in query and "end_date < CURRENT_DATE" in query:
                    self.rowcount = 2 # Simulate 2 offers expired
                elif "SELECT EXISTS" in query and "FROM events" in query:
                    self._last_result = (False,) # No active journey
                else:
                    self._last_result = None
            def fetchone(self): return self._last_result
            def fetchall(self): return []
            def close(self): pass
        class MockConnectionForExpiry:
            def cursor(self): return MockCursorForExpiry()
            def commit(self): pass
            def rollback(self): pass
        class MockDBConnectionPoolForExpiry:
            def getconn(self): return MockConnectionForExpiry()
            def putconn(self, conn): pass

        offer_service_for_expiry = OfferService(
            MockDBConnectionPoolForExpiry()
        )
        expired_count = offer_service_for_expiry.expire_offers_based_on_end_date()
        print(f"Offers expired by end date: {expired_count}")

        print("\n--- Expiring Journey Started Offers by LAN Validity ---")
        expired_lan_count = \
            offer_service_for_expiry.expire_journey_started_offers_by_lan_validity()
        print(f"Offers expired by LAN validity: {expired_lan_count}")

        print("\n--- Checking and Replenishing Offers ---")
        # Use a mock that simulates no active offers and no active journey
        class MockCursorForReplenish:
            def execute(self, query, params=None):
                if "SELECT EXISTS" in query and "FROM events" in query:
                    self._last_result = (False,) # No active journey
                elif "SELECT NOT EXISTS" in query and "FROM offers" in query:
                    self._last_result = (True,) # All offers expired
                else:
                    self._last_result = None
            def fetchone(self): return self._last_result
            def fetchall(self): return []
            def close(self): pass
        class MockConnectionForReplenish:
            def cursor(self): return MockCursorForReplenish()
            def commit(self): pass
            def rollback(self): pass
        class MockDBConnectionPoolForReplenish:
            def getconn(self): return MockConnectionForReplenish()
            def putconn(self, conn): pass

        offer_service_for_replenish = OfferService(
            MockDBConnectionPoolForReplenish()
        )
        needs_replenishment = \
            offer_service_for_replenish.check_and_replenish_offers(
                customer_id_test
            )
        print(f"Customer {customer_id_test} needs replenishment: "
              f"{needs_replenishment}")

        print("\n--- Applying Attribution Logic ---")
        # Re-initialize with default mock for attribution test
        offer_service_for_attribution = OfferService(mock_db_pool)
        attributed_offer = offer_service_for_attribution.apply_attribution_logic(
            customer_id_test
        )
        print(f"Attributed Offer: {attributed_offer}")

        print("\n--- Getting Offer History ---")
        offer_history = offer_service.get_offer_history(customer_id_test, months=3)
        print(f"Offer History (last 3 months): {offer_history}")