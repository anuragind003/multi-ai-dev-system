# db_connection.py
# Module for managing PostgreSQL database connections using psycopg2.
# Includes connection pooling, error handling, and context management.

import psycopg2
from psycopg2 import pool
from psycopg2 import Error as PgError
import configparser
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseConnection:
    """
    Manages database connections using a connection pool.
    Provides methods to get and return connections, and execute queries.
    """
    _connection_pool = None
    _config = {}

    @classmethod
    def load_config(cls, config_file='config/database.ini', section='postgresql'):
        """Loads database configuration from an INI file."""
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        parser = configparser.ConfigParser()
        parser.read(config_file)

        if section not in parser:
            raise ValueError(f"Section '{section}' not found in {config_file}")

        cls._config = parser[section]
        logging.info("Database configuration loaded.")

    @classmethod
    def initialize_pool(cls, min_conn=1, max_conn=10):
        """Initializes the connection pool."""
        if not cls._config:
            cls.load_config() # Load default config if not already loaded

        if cls._connection_pool is None:
            try:
                cls._connection_pool = pool.SimpleConnectionPool(
                    min_conn,
                    max_conn,
                    host=cls._config.get('host'),
                    port=cls._config.getint('port'),
                    database=cls._config.get('database'),
                    user=cls._config.get('user'),
                    password=cls._config.get('password'),
                    # Add other parameters like sslmode if needed
                    # sslmode=cls._config.get('sslmode', 'prefer')
                )
                logging.info(f"Database connection pool initialized with {min_conn}-{max_conn} connections.")
            except PgError as e:
                logging.error(f"Error initializing connection pool: {e}")
                raise ConnectionError(f"Failed to initialize database pool: {e}") from e
        else:
            logging.info("Connection pool already initialized.")

    @classmethod
    def get_connection(cls):
        """Retrieves a connection from the pool."""
        if cls._connection_pool is None:
            cls.initialize_pool() # Initialize if not already done

        try:
            conn = cls._connection_pool.getconn()
            conn.autocommit = False # Ensure transactions are explicit
            logging.debug("Connection retrieved from pool.")
            return conn
        except PgError as e:
            logging.error(f"Error getting connection from pool: {e}")
            raise ConnectionError(f"Failed to get connection from pool: {e}") from e

    @classmethod
    def return_connection(cls, conn):
        """Returns a connection to the pool."""
        if cls._connection_pool:
            cls._connection_pool.putconn(conn)
            logging.debug("Connection returned to pool.")
        else:
            logging.warning("Connection pool not initialized, cannot return connection.")

    @classmethod
    def close_pool(cls):
        """Closes all connections in the pool."""
        if cls._connection_pool:
            cls._connection_pool.closeall()
            cls._connection_pool = None
            logging.info("Database connection pool closed.")

    @classmethod
    def execute_query(cls, query, params=None, fetch_one=False, fetch_all=False, commit=False):
        """
        Executes a SQL query.
        :param query: The SQL query string.
        :param params: A tuple or list of parameters for the query.
        :param fetch_one: If True, fetches one row.
        :param fetch_all: If True, fetches all rows.
        :param commit: If True, commits the transaction.
        :return: Fetched data (if any) or None.
        """
        conn = None
        try:
            conn = cls.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)

            if commit:
                conn.commit()
                logging.debug("Transaction committed.")

            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                return None # For DDL/DML without fetch

        except PgError as e:
            if conn:
                conn.rollback()
                logging.error("Transaction rolled back due to error.")
            logging.error(f"Database query error: {e} - Query: {query} - Params: {params}")
            raise RuntimeError(f"Database operation failed: {e}") from e
        finally:
            if conn:
                cls.return_connection(conn)
            logging.debug("Cursor and connection handled.")

# Context manager for easier connection handling
class ConnectionContext:
    """Context manager to get and return a database connection."""
    def __enter__(self):
        self.conn = DatabaseConnection.get_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            if self.conn:
                self.conn.rollback()
                logging.error(f"Transaction rolled back due to exception: {exc_val}")
        else:
            if self.conn:
                self.conn.commit()
                logging.debug("Transaction committed by context manager.")
        if self.conn:
            DatabaseConnection.return_connection(self.conn)

# Example Usage (for testing purposes)
if __name__ == "__main__":
    try:
        # Load configuration and initialize pool
        DatabaseConnection.load_config()
        DatabaseConnection.initialize_pool()

        # Example: Insert a new user (assuming 'system_auditor' exists or handle user_id)
        # For this example, let's assume we have a user ID from seed data
        # You would typically get this from your application's authentication context
        # For the trigger to work, we need to set a session variable.
        # This is usually done by the application layer after a user logs in.
        # For this test, we'll use a hardcoded ID or fetch 'system_auditor' ID.
        system_auditor_id_query = "SELECT id FROM users WHERE username = 'system_auditor';"
        system_auditor_id_row = DatabaseConnection.execute_query(system_auditor_id_query, fetch_one=True)
        system_auditor_id = system_auditor_id_row[0] if system_auditor_id_row else None

        if system_auditor_id:
            print(f"System Auditor ID: {system_auditor_id}")
            # Set session variable for the trigger
            with ConnectionContext() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SET SESSION \"app.current_user_id\" = '{system_auditor_id}';")
                conn.commit() # Commit the SET SESSION command

            # Insert a new V-KYC recording using the application logic (which will trigger the DB trigger)
            print("\nInserting a new V-KYC recording...")
            insert_vkyc_query = """
            INSERT INTO vkyc_recordings (vkyc_case_id, customer_name, recording_date, duration_seconds, file_path, uploaded_by_user_id, metadata_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;
            """
            new_vkyc_id_row = DatabaseConnection.execute_query(
                insert_vkyc_query,
                ('VKYC-TEST-001', 'Test Customer', '2023-10-28', 120, '/recordings/test_customer_001.mp4', system_auditor_id, {'test_key': 'test_value'}),
                fetch_one=True, commit=True
            )
            new_vkyc_id = new_vkyc_id_row[0] if new_vkyc_id_row else None
            print(f"New V-KYC Recording ID: {new_vkyc_id}")

            # Update the V-KYC recording to trigger another audit log
            print("\nUpdating the V-KYC recording...")
            update_vkyc_query = """
            UPDATE vkyc_recordings SET status = 'archived' WHERE id = %s;
            """
            DatabaseConnection.execute_query(update_vkyc_query, (new_vkyc_id,), commit=True)
            print(f"V-KYC Recording {new_vkyc_id} updated to 'archived'. Check audit_logs.")

            # Manually log a login event using the stored procedure
            print("\nLogging a manual audit event (login)...")
            login_audit_id_row = DatabaseConnection.execute_query(
                "SELECT log_audit_event(%s, %s, %s, %s, %s, %s);",
                (system_auditor_id, 'LOGIN', 'user_session', None, '127.0.0.1', {'user_agent': 'test_script'}),
                fetch_one=True, commit=True
            )
            print(f"Manual Login Audit ID: {login_audit_id_row[0]}")

            # Fetch V-KYC recording details with audit history using the stored procedure
            if new_vkyc_id:
                print(f"\nFetching details for V-KYC Recording {new_vkyc_id} with audit history...")
                vkyc_details = DatabaseConnection.execute_query(
                    "SELECT * FROM get_vkyc_recording_details(%s);",
                    (new_vkyc_id,),
                    fetch_one=True
                )
                if vkyc_details:
                    print(f"V-KYC Details: {vkyc_details[0]} - {vkyc_details[1]}")
                    print(f"Audit History: {vkyc_details[-1]}")
                else:
                    print("V-KYC recording not found.")

            # Reset session variable
            with ConnectionContext() as conn:
                cursor = conn.cursor()
                cursor.execute("RESET ALL;") # Resets all session variables
                conn.commit()

        else:
            print("System auditor user not found. Please run seed_data.sql first.")

    except ConnectionError as ce:
        print(f"Connection Error: {ce}")
    except RuntimeError as re:
        print(f"Runtime Error: {re}")
    except FileNotFoundError as fnfe:
        print(f"Configuration Error: {fnfe}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        DatabaseConnection.close_pool()
        print("\nDatabase connection pool closed.")