# db_connection.py
# Module for managing PostgreSQL database connections using psycopg2.
# Includes connection pooling (basic implementation) and robust error handling.

import psycopg2
from psycopg2 import pool
from psycopg2 import Error as Psycopg2Error
from db_config import DBConfig
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DBConnection:
    """
    Manages database connections, providing a context manager for easy usage
    and basic connection pooling.
    """
    _connection_pool = None

    @classmethod
    def initialize_pool(cls, min_conn=1, max_conn=10):
        """
        Initializes the connection pool. Should be called once at application startup.
        """
        if cls._connection_pool is None:
            try:
                cls._connection_pool = pool.SimpleConnectionPool(
                    min_conn,
                    max_conn,
                    DBConfig.get_connection_string()
                )
                logging.info(f"Database connection pool initialized with min={min_conn}, max={max_conn} connections.")
            except Psycopg2Error as e:
                logging.error(f"Error initializing connection pool: {e}")
                raise

    @classmethod
    def close_pool(cls):
        """
        Closes all connections in the pool. Should be called at application shutdown.
        """
        if cls._connection_pool:
            cls._connection_pool.closeall()
            cls._connection_pool = None
            logging.info("Database connection pool closed.")

    def __init__(self):
        self.conn = None
        self.cursor = None

    def __enter__(self):
        """
        Acquires a connection from the pool and creates a cursor.
        """
        if DBConnection._connection_pool is None:
            raise RuntimeError("Database connection pool not initialized. Call DBConnection.initialize_pool() first.")
        try:
            self.conn = DBConnection._connection_pool.getconn()
            self.cursor = self.conn.cursor()
            return self
        except Psycopg2Error as e:
            logging.error(f"Error acquiring connection from pool: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Commits or rolls back the transaction, closes the cursor, and returns
        the connection to the pool.
        """
        if self.cursor:
            self.cursor.close()
        if self.conn:
            if exc_type:
                self.conn.rollback()
                logging.error(f"Transaction rolled back due to exception: {exc_val}")
            else:
                self.conn.commit()
                logging.info("Transaction committed.")
            DBConnection._connection_pool.putconn(self.conn)
            self.conn = None # Clear connection reference
            logging.debug("Connection returned to pool.")

    def execute_query(self, query, params=None, fetch_results=False):
        """
        Executes a SQL query.
        :param query: The SQL query string.
        :param params: A tuple or dictionary of parameters for the query.
        :param fetch_results: If True, fetches all results after execution.
        :return: List of rows if fetch_results is True, otherwise None.
        """
        try:
            self.cursor.execute(query, params)
            if fetch_results:
                return self.cursor.fetchall()
            return None
        except Psycopg2Error as e:
            logging.error(f"Error executing query: {query} with params {params}. Error: {e}")
            self.conn.rollback() # Ensure rollback on query error
            raise

    def fetch_one(self):
        """Fetches one row from the last executed query."""
        return self.cursor.fetchone()

    def fetch_all(self):
        """Fetches all rows from the last executed query."""
        return self.cursor.fetchall()

# Example Usage:
if __name__ == "__main__":
    # 1. Initialize the pool at application start
    try:
        DBConnection.initialize_pool(min_conn=1, max_conn=3)

        # 2. Use the connection manager
        logging.info("--- Testing DB Operations ---")

        # Test INSERT (create a dummy user)
        try:
            with DBConnection() as db:
                # Using a stored procedure for user creation
                user_id = db.execute_query(
                    "SELECT create_user(%s, %s, %s, %s);",
                    ('test_user_conn', 'hashed_password_test', 'test_conn@example.com', 'Team Lead'),
                    fetch_results=True
                )[0][0]
                logging.info(f"User 'test_user_conn' created with ID: {user_id}")
        except Psycopg2Error as e:
            logging.error(f"Failed to create user: {e}")

        # Test SELECT
        try:
            with DBConnection() as db:
                users = db.execute_query("SELECT id, username, email, role FROM users WHERE username = %s;", ('test_user_conn',), fetch_results=True)
                if users:
                    logging.info(f"Found user: {users[0]}")
                else:
                    logging.info("User 'test_user_conn' not found.")
        except Psycopg2Error as e:
            logging.error(f"Failed to fetch user: {e}")

        # Test UPDATE
        try:
            with DBConnection() as db:
                db.execute_query("UPDATE users SET email = %s WHERE username = %s;", ('updated_test_conn@example.com', 'test_user_conn'))
                logging.info("User 'test_user_conn' email updated.")
        except Psycopg2Error as e:
            logging.error(f"Failed to update user: {e}")

        # Test DELETE
        try:
            with DBConnection() as db:
                # First, delete any recordings associated with this user if they exist
                # (This is to satisfy ON DELETE RESTRICT on recordings.uploaded_by_user_id)
                db.execute_query("DELETE FROM recordings WHERE uploaded_by_user_id = (SELECT id FROM users WHERE username = %s);", ('test_user_conn',))
                logging.info("Deleted test recordings for 'test_user_conn' if any.")

                # Then delete the user using the stored procedure
                admin_user_id = db.execute_query("SELECT id FROM users WHERE username = 'admin_user';", fetch_results=True)[0][0]
                success = db.execute_query(
                    "SELECT delete_user_and_audit(%s, %s, %s);",
                    (user_id, admin_user_id, '127.0.0.1'),
                    fetch_results=True
                )[0][0]
                if success:
                    logging.info(f"User 'test_user_conn' (ID: {user_id}) deleted successfully.")
                else:
                    logging.warning(f"Failed to delete user 'test_user_conn' (ID: {user_id}).")
        except Psycopg2Error as e:
            logging.error(f"Failed to delete user: {e}")

    except Exception as e:
        logging.critical(f"Application error: {e}")
    finally:
        # 3. Close the pool at application shutdown
        DBConnection.close_pool()