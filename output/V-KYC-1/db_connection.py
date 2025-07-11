# db_connection.py
# Python module for managing PostgreSQL database connections.
# Uses psycopg2 for database interaction and configparser for configuration.

import psycopg2
import configparser
from psycopg2 import Error
import os

class DBConnection:
    """
    Manages PostgreSQL database connections.
    Reads connection parameters from a configuration file.
    """

    def __init__(self, config_file='config/database.ini', section='postgresql'):
        """
        Initializes the DBConnection with configuration file path and section.
        """
        self.config_file = config_file
        self.section = section
        self.conn = None
        self.cursor = None
        self.db_params = {}
        self._load_config()

    def _load_config(self):
        """
        Loads database connection parameters from the specified INI file.
        """
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")

        parser = configparser.ConfigParser()
        parser.read(self.config_file)

        if parser.has_section(self.section):
            self.db_params = dict(parser.items(self.section))
        else:
            raise Exception(f'Section {self.section} not found in the {self.config_file} file')

    def connect(self):
        """
        Establishes a connection to the PostgreSQL database.
        """
        if self.conn is not None and not self.conn.closed:
            print("Database connection already open.")
            return

        try:
            print(f"Attempting to connect to database: {self.db_params.get('dbname')}@{self.db_params.get('host')}:{self.db_params.get('port')}")
            self.conn = psycopg2.connect(**self.db_params)
            self.cursor = self.conn.cursor()
            print("Database connection established successfully.")
        except Error as e:
            print(f"Error connecting to PostgreSQL database: {e}")
            self.conn = None
            self.cursor = None
            raise

    def disconnect(self):
        """
        Closes the database connection and cursor.
        """
        if self.cursor:
            self.cursor.close()
            self.cursor = None
            print("Database cursor closed.")
        if self.conn:
            self.conn.close()
            self.conn = None
            print("Database connection closed.")

    def execute_query(self, query, params=None, commit=False):
        """
        Executes a SQL query.
        :param query: The SQL query string.
        :param params: A tuple or list of parameters to pass to the query.
        :param commit: Boolean, if True, commits the transaction.
        :return: Number of rows affected for DML, None for SELECT.
        """
        if not self.conn or self.conn.closed:
            print("No active database connection. Attempting to reconnect...")
            self.connect() # Attempt to reconnect if connection is lost

        try:
            self.cursor.execute(query, params)
            if commit:
                self.conn.commit()
                print("Transaction committed.")
            return self.cursor.rowcount
        except Error as e:
            print(f"Error executing query: {e}")
            if self.conn:
                self.conn.rollback() # Rollback on error
                print("Transaction rolled back.")
            raise

    def fetch_one(self, query, params=None):
        """
        Executes a SELECT query and fetches one row.
        :param query: The SQL query string.
        :param params: A tuple or list of parameters.
        :return: A single row as a tuple, or None if no rows.
        """
        self.execute_query(query, params)
        return self.cursor.fetchone()

    def fetch_all(self, query, params=None):
        """
        Executes a SELECT query and fetches all rows.
        :param query: The SQL query string.
        :param params: A tuple or list of parameters.
        :return: A list of tuples, where each tuple is a row.
        """
        self.execute_query(query, params)
        return self.cursor.fetchall()

    def __enter__(self):
        """Context manager entry point."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.disconnect()

# Example Usage (for testing the module)
if __name__ == "__main__":
    # Create a dummy config file for testing if it doesn't exist
    if not os.path.exists('config'):
        os.makedirs('config')
    if not os.path.exists('config/database.ini'):
        with open('config/database.ini', 'w') as f:
            f.write("""
[postgresql]
host=localhost
port=5432
dbname=test_db
user=test_user
password=test_password
""")
        print("Created dummy config/database.ini for testing. Please ensure 'test_db' exists and 'test_user' has access.")

    try:
        # Using the context manager
        with DBConnection() as db:
            # Example: Create a dummy table for testing connection
            try:
                db.execute_query("CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY, name VARCHAR(50));", commit=True)
                print("test_table created or already exists.")

                # Example: Insert data
                db.execute_query("INSERT INTO test_table (name) VALUES (%s);", ('Test Name 1',), commit=True)
                db.execute_query("INSERT INTO test_table (name) VALUES (%s);", ('Test Name 2',), commit=True)
                print("Data inserted into test_table.")

                # Example: Fetch data
                rows = db.fetch_all("SELECT * FROM test_table;")
                print("Fetched data:")
                for row in rows:
                    print(row)

                # Example: Update data
                db.execute_query("UPDATE test_table SET name = %s WHERE id = %s;", ('Updated Name 1', 1), commit=True)
                print("Data updated.")

                # Example: Fetch one
                row = db.fetch_one("SELECT * FROM test_table WHERE id = %s;", (1,))
                print("Fetched updated row:", row)

            except Error as e:
                print(f"Error during test operations: {e}")
            finally:
                # Clean up dummy table
                db.execute_query("DROP TABLE IF EXISTS test_table;", commit=True)
                print("test_table dropped.")

    except Exception as e:
        print(f"An error occurred during DBConnection usage: {e}")
    finally:
        # Clean up dummy config file
        if os.path.exists('config/database.ini'):
            # os.remove('config/database.ini') # Uncomment to remove after testing
            pass