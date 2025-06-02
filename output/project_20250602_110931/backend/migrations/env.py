import os
import sys
from pathlib import Path
from logging.config import fileConfig
import logging

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# Configure basic logging for env.py itself, separate from fileConfig which sets up Alembic's logging.
# This ensures messages from env.py are visible even before Alembic's full logging setup.
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to sys.path to allow importing application modules.
# This assumes env.py is located at `PROJECT_ROOT/backend/migrations/env.py`.
# The project root is two levels up from the current file.
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file.
# This is crucial for loading the DATABASE_URL, which specifies the database connection string.
load_dotenv()

# This is the Alembic Config object, which provides access to the values within the .ini file.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers defined in alembic.ini, allowing migration logs to be configured.
fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support.
# This imports the Base from your application's models.py.
# Importing `backend.models` ensures that all defined SQLAlchemy models (User, Task, etc.)
# are loaded and registered with `Base.metadata`, which Alembic uses to compare
# your current database schema with your model definitions for autogeneration.
from backend.models import Base
target_metadata = Base.metadata

# Set the database URL for SQLAlchemy.
# Prioritize DATABASE_URL from environment variables for production/deployment flexibility.
# This allows the database connection to be easily changed without modifying alembic.ini.
db_url = os.environ.get("DATABASE_URL")

if db_url:
    logger.info("Using DATABASE_URL from environment variables.")
else:
    # If DATABASE_URL is not set in environment variables, check if alembic.ini has one.
    db_url = config.get_main_option("sqlalchemy.url")
    if not db_url:
        # If neither is found, provide a default SQLite URL for local development convenience.
        db_url = "sqlite:///./instance/app.db"
        logger.warning(f"DATABASE_URL environment variable not set and no URL in alembic.ini. Using default SQLite URL for development: {db_url}")
    else:
        logger.info("DATABASE_URL environment variable not set. Using URL from alembic.ini.")

config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This mode generates SQL scripts without connecting to the database.
    It configures the context with just a URL and not an Engine.
    By skipping the Engine creation, a DBAPI (database driver) is not required.
    Calls to context.execute() here emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,  # Render literal values in the generated SQL
        dialect_opts={"paramstyle": "named"}, # Use named parameters for dialect
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario, Alembic connects to the actual database.
    It creates an SQLAlchemy Engine and associates a connection with the context.
    This is used for applying migrations directly to the database.
    """
    # Create an SQLAlchemy engine from the configuration.
    # `poolclass=pool.NullPool` is often used for migrations as connections are short-lived
    # and not typically reused across multiple migration steps.
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Establish a connection to the database.
    with connectable.connect() as connection:
        # Configure the Alembic context with the active database connection and target metadata.
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Optionally, include include_schemas=True if your application uses database schemas
            # include_schemas=True,
        )

        # Begin a transaction for the migration process.
        # All migration operations within this block will be part of a single transaction,
        # ensuring atomicity (all or nothing).
        with context.begin_transaction():
            context.run_migrations()

# Determine whether to run migrations offline or online based on Alembic's context.
# This is typically controlled by the `alembic` command line arguments (e.g., `alembic upgrade head`).
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()