import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the project root to sys.path to enable importing application modules.
# Assuming alembic/env.py is located at <project_root>/alembic/env.py
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(project_root)

# Load environment variables from the .env file at the project root.
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'))

# Import your application's settings and SQLAlchemy declarative base.
# These imports are crucial for Alembic to understand your database models
# and connect to the database using your application's configuration.
try:
    from app.core.config import settings
    from app.db.base import Base
except ImportError as e:
    print(f"Error importing application modules: {e}")
    print("Please ensure your `app` directory structure and `PYTHONPATH` are correct.")
    print(f"Current sys.path: {sys.path}")
    # Re-raise the exception to halt execution if core modules are not found,
    # as Alembic cannot proceed without them.
    raise

# This is the Alembic Config object, which provides
# access to values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support.
# This tells Alembic which SQLAlchemy models define your database schema.
target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    # Use the database URL from application settings for offline mode.
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Get the database URL from application settings.
    database_url = settings.DATABASE_URL

    # Override the 'sqlalchemy.url' option in alembic.ini with the URL
    # from our application's settings. This ensures consistency and allows
    # dynamic configuration (e.g., via environment variables).
    config.set_main_option("sqlalchemy.url", database_url)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

# Determine whether to run migrations in offline or online mode.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()