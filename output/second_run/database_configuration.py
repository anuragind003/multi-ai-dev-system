# database_configuration.py
# Manages database connection settings.

import os

class DatabaseConfig:
    """
    Configuration class for the PostgreSQL database.
    """
    def __init__(self):
        self.db_host = os.environ.get("DB_HOST", "localhost")
        self.db_port = os.environ.get("DB_PORT", "5432")
        self.db_name = os.environ.get("DB_NAME", "postgres")
        self.db_user = os.environ.get("DB_USER", "app_user")
        self.db_password = os.environ.get("DB_PASSWORD", "secure_password")  # Use a strong password in production.
        self.db_url = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    def get_db_url(self):
        return self.db_url

    def get_db_credentials(self):
        return {
            "host": self.db_host,
            "port": self.db_port,
            "database": self.db_name,
            "user": self.db_user,
            "password": self.db_password,
        }