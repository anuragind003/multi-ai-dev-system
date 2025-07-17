# src/db_connection.py
import psycopg2
from psycopg2 import Error, sql
from psycopg2.extras import DictCursor
import configparser
import os

class DBConnection:
    """
    Manages database connections for the VKYC Recordings system.
    Uses psycopg2 for PostgreSQL connectivity and configparser for reading database settings.
    Includes robust error handling and connection pooling (basic).
    """
    _instance = None
    _pool = []
    _pool_size = 5 # Basic connection pooling

    def __new__(cls, config_file='config/database.ini', section='postgresql'):
        if cls._instance is None:
            cls._instance = super(DBConnection, cls).__new__(cls)
            cls._instance.config_file = config_file
            cls._instance.section = section
            cls._instance._load_config()
            cls._instance._initialize_pool()
        return cls._instance

    def _load_config(self):
        """Loads database configuration from the INI file."""
        parser = configparser.ConfigParser()
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        parser.read(self.config_file)

        if not parser.has_section(self.section):
            raise ValueError(f"Section '{self.section}' not found in {self.config_file}")

        self.db_config = {
            'host': parser.get(self.section, 'host'),
            'port': parser.getint(self.section, 'port'),
            'database': parser.get(self.section, 'database'),
            'user': parser.get(self.section, 'user'),
            'password': parser.get(self.section, 'password')
        }
        # Optional: Read pool size if defined in config
        # self._pool_size = parser.getint(self.section, 'max_connections', fallback=5)

    def _create_connection(self):
        """Establishes a new database connection."""
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.autocommit = False # Ensure transactions are managed explicitly
            return conn
        except Error as e:
            print(f"Database connection error: {e}")
            raise

    def _initialize_pool(self):
        """Initializes a basic connection pool."""
        for _ in range(self._pool_size):
            try:
                self._pool.append(self._create_connection())
            except Exception as e:
                print(f"Failed to initialize connection pool: {e}")
                # Decide whether to raise or continue with fewer connections

    def get_connection(self):
        """Retrieves a connection from the pool or creates a new one if pool is empty."""
        if self._pool:
            return self._pool.pop()
        else:
            print("Connection pool exhausted, creating a new connection.")
            return self._create_connection()

    def release_connection(self, conn):
        """Returns a connection to the pool."""
        if conn:
            if len(self._pool) < self._pool_size:
                self._pool.append(conn)
            else:
                conn.close() # Close if pool is full

    def execute_query(self, query, params=None, fetch_type=None):
        """
        Executes a SQL query.
        :param query: SQL query string.
        :param params: Tuple or list of parameters for the query.
        :param fetch_type: 'one', 'all', or None (for DDL/DML operations).
        :return: Fetched data or None.
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=DictCursor) as cur: # DictCursor for dict-like rows
                cur.execute(query, params)
                if fetch_type == 'one':
                    return cur.fetchone()
                elif fetch_type == 'all':
                    return cur.fetchall()
                else:
                    conn.commit() # Commit DDL/DML operations
                    return None
        except Error as e:
            if conn:
                conn.rollback() # Rollback on error
            print(f"Database query error: {e}")
            raise
        finally:
            if conn:
                self.release_connection(conn)

    def close_all_connections(self):
        """Closes all connections in the pool."""
        while self._pool:
            conn = self._pool.pop()
            try:
                conn.close()
            except Error as e:
                print(f"Error closing connection: {e}")
        print("All database connections closed.")

# Example Usage:
if __name__ == "__main__":
    try:
        db = DBConnection()

        # Test connection and simple query
        print("Testing connection and fetching users...")
        users = db.execute_query("SELECT id, username, email, role FROM users LIMIT 2;", fetch_type='all')
        if users:
            for user in users:
                print(f"User: {user['username']}, Email: {user['email']}, Role: {user['role']}")
        else:
            print("No users found or error occurred.")

        # Test inserting a new recording using a stored procedure
        print("\nTesting create_vkyc_recording procedure...")
        try:
            new_recording_id = db.execute_query(
                "SELECT create_vkyc_recording(%s, %s, %s, %s, %s, %s, %s);",
                ('CUST_TEST_001', '2023-10-27', '15:00:00', 'PENDING', '/test/path/test_rec.mp4', 100, 'AGENT_TEST'),
                fetch_type='one'
            )
            print(f"New recording created with ID: {new_recording_id['create_vkyc_recording']}")
        except Exception as e:
            print(f"Failed to create recording: {e}")

        # Test updating a recording status
        if new_recording_id:
            print(f"\nUpdating status for recording {new_recording_id['create_vkyc_recording']}...")
            update_success = db.execute_query(
                "SELECT update_vkyc_recording_status(%s, %s);",
                (new_recording_id['create_vkyc_recording'], 'APPROVED'),
                fetch_type='one'
            )
            print(f"Update successful: {update_success['update_vkyc_recording_status']}")

        # Test fetching recordings by customer
        print("\nFetching recordings for CUST001...")
        cust_recordings = db.execute_query(
            "SELECT * FROM get_vkyc_recordings_by_customer(%s);",
            ('CUST001',),
            fetch_type='all'
        )
        if cust_recordings:
            for rec in cust_recordings:
                print(f"Recording: ID={rec['id']}, Status={rec['status']}, Path={rec['file_path']}")
        else:
            print("No recordings found for CUST001.")

    except Exception as e:
        print(f"An unhandled error occurred during DB operations: {e}")
    finally:
        # Ensure all connections are closed when done
        if 'db' in locals() and db:
            db.close_all_connections()