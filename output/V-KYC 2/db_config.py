# db_config.py
# Database configuration file.
# Loads connection parameters from environment variables for security and flexibility.

import os

class DBConfig:
    """
    Configuration class for PostgreSQL database connection.
    Loads sensitive information from environment variables.
    """
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'vkyc_db')
    DB_USER = os.getenv('DB_USER', 'vkyc_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'vkyc_password') # Use a strong default or ensure env var is set

    @classmethod
    def get_connection_string(cls):
        """
        Returns the PostgreSQL connection string.
        """
        return (
            f"host={cls.DB_HOST} "
            f"port={cls.DB_PORT} "
            f"dbname={cls.DB_NAME} "
            f"user={cls.DB_USER} "
            f"password={cls.DB_PASSWORD}"
        )

    @classmethod
    def get_alembic_url(cls):
        """
        Returns the SQLAlchemy URL for Alembic.
        """
        return (
            f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@"
            f"{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )

    @classmethod
    def print_config(cls):
        """
        Prints the database configuration (excluding password for security).
        """
        print("--- Database Configuration ---")
        print(f"Host: {cls.DB_HOST}")
        print(f"Port: {cls.DB_PORT}")
        print(f"Database Name: {cls.DB_NAME}")
        print(f"User: {cls.DB_USER}")
        print("Password: [HIDDEN]")
        print("----------------------------")

# Example usage (for testing configuration loading)
if __name__ == "__main__":
    DBConfig.print_config()
    print(f"Connection String: {DBConfig.get_connection_string()}")
    print(f"Alembic URL: {DBConfig.get_alembic_url()}")

    # To test with environment variables:
    # export DB_HOST=my_db_host
    # export DB_USER=my_custom_user
    # python db_config.py