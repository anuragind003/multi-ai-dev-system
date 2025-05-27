import os
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the project root to sys.path to allow importing app modules.
# This assumes env.py is located at `app/db/alembic/env.py`.
# So, `Path(__file__).parent.parent.parent` points to the project root.
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import your Base from your models file.
# Assuming SQLAlchemy models are defined in `app/db/models.py`
# and a `Base` object (e.g., from `declarative_base` or `MappedAsDataclass`) is exposed.
try:
    from app.db.models import Base
except ImportError as e:
    print(f"Error importing app.db.models.Base: {e}")
    print("Please ensure 'app/db/models.py' exists and defines a 'Base' object for SQLAlchemy.")
    # Re-raise the error as it's critical for Alembic to function correctly.
    raise

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

def get_database_url():
    """
    Retrieves the database URL for Alembic.
    Prioritizes the `DATABASE_URL` environment variable,
    then falls back to `sqlalchemy.url` from `alembic.ini`.
    """
    # Get from environment variable first (best practice for production)
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url

    # Fallback to alembic.ini if not found in environment
    # This assumes alembic.ini has a [alembic:main] section with sqlalchemy.url
    ini_url = config.get_main_option("sqlalchemy.url")
    if ini_url:
        return ini_url
    
    raise ValueError(
        "Database URL not found. "
        "Please set the 'DATABASE_URL' environment variable "
        "or configure 'sqlalchemy.url' in your 'alembic.ini' file."
    )

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Set compare_type=True for better type comparison in autogenerate
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    database_url = get_database_url()

    # Create a connectable engine from the URL
    connectable = engine_from_config(
        {"sqlalchemy.url": database_url}, # Pass the URL directly
        prefix="sqlalchemy.", # This prefix is applied to keys in the dict
        poolclass=pool.NullPool, # Use NullPool for migrations
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            # Set compare_type=True for better type comparison in autogenerate
            compare_type=True,
            # You can specify a schema for the Alembic version table if needed
            # version_table_schema="public", 
        )

        with context.begin_transaction():
            context.run_migrations()

# Determine whether to run offline or online based on Alembic's context
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()