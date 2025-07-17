# db_connection.py
# Python module for managing PostgreSQL database connections using psycopg2.

import configparser
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DBConnectionManager:
    """
    Manages database connections using a connection pool.
    Provides a context manager for easy connection handling.
    """
    _instance = None

    def __new__(cls, config_file='database_config.ini'):
        if cls._instance is None:
            cls._instance = super(DBConnectionManager, cls).__new__(cls)
            cls._instance._initialized = False
            cls._instance.config_file = config_file
            cls._instance.conn_pool = None
            cls._instance._initialize_pool()
        return cls._instance

    def _initialize_pool(self):
        """Initializes the connection pool from the configuration file."""
        if self._initialized:
            return

        config = configparser.ConfigParser()
        try:
            config.read(self.config_file)
            db_config = config['database']
        except KeyError:
            logging.error(f"Error: 'database' section not found in {self.config_file}")
            raise ValueError(f"Missing 'database' section in {self.config_file}")
        except Exception as e:
            logging.error(f"Error reading config file {self.config_file}: {e}")
            raise

        try:
            self.conn_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=db_config.get('host', 'localhost'),
                port=db_config.get('port', '5432'),
                database=db_config.get('dbname', 'vkyc_db'),
                user=db_config.get('user', 'vkyc_user'),
                password=db_config.get('password', 'vkyc_password')
            )
            logging.info("Database connection pool initialized successfully.")
            self._initialized = True
        except psycopg2.Error as e:
            logging.critical(f"Failed to initialize database connection pool: {e}")
            raise ConnectionError(f"Database connection error: {e}")

    @contextmanager
    def get_connection(self):
        """
        Provides a database connection from the pool using a context manager.
        Ensures the connection is returned to the pool after use.
        """
        if not self._initialized or self.conn_pool is None:
            self._initialize_pool() # Re-initialize if somehow uninitialized

        conn = None
        try:
            conn = self.conn_pool.getconn()
            yield conn
            conn.commit() # Commit changes if no exceptions
        except psycopg2.Error as e:
            if conn:
                conn.rollback() # Rollback on error
            logging.error(f"Database operation failed: {e}")
            raise
        finally:
            if conn:
                self.conn_pool.putconn(conn)
                logging.debug("Connection returned to pool.")

    def close_all_connections(self):
        """Closes all connections in the pool."""
        if self.conn_pool:
            self.conn_pool.closeall()
            logging.info("All database connections closed.")
            self._initialized = False # Mark as uninitialized
        else:
            logging.info("No connection pool to close.")

# Example Usage:
if __name__ == "__main__":
    db_manager = DBConnectionManager()

    try:
        # Test fetching users
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, username, email, role FROM users LIMIT 5;")
                users = cur.fetchall()
                logging.info("Fetched users:")
                for user in users:
                    logging.info(user)

        # Test inserting an audit log using the stored procedure
        # Ensure a valid user_id exists in your 'users' table for this to work
        # For demonstration, we'll use a dummy UUID. In a real app, you'd get it from an authenticated user.
        dummy_user_id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11' # Replace with an actual user ID from your seed data
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT log_audit_event(%s, %s, %s, %s, %s::INET);",
                        (dummy_user_id, 'test_action_from_python', 'system', None, '127.0.0.1')
                    )
                    logging.info(f"Audit event logged successfully for user {dummy_user_id}.")
        except psycopg2.Error as e:
            logging.error(f"Error logging audit event: {e}")

        # Test fetching audit logs
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id, action, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT 5;")
                logs = cur.fetchall()
                logging.info("Fetched audit logs:")
                for log in logs:
                    logging.info(log)

    except ConnectionError as e:
        logging.error(f"Application failed to connect to database: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        db_manager.close_all_connections()