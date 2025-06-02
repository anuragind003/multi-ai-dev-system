import os
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add the project root to sys.path to allow importing app and config modules.
# This assumes migrations/env.py is located at project_root/migrations/env.py.
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# target_metadata will be populated by importing the models.
# For Flask-SQLAlchemy, this is typically `db.Model.metadata`.
# For a pure SQLAlchemy setup, it's `Base.metadata`.
# We assume a `Base` object exists in `app.models` that holds the metadata.
target_metadata = None
create_app = None
try:
    # Import the create_app function to get the Flask application instance
    # and the Base object from app.models to get the SQLAlchemy metadata.
    # Importing app.models ensures all model classes are loaded and registered
    # with Base.metadata, which is crucial for Alembic's autogenerate feature.
    from app import create_app
    from app.models import Base
    target_metadata = Base.metadata
except ImportError as e:
    # Log an error if imports fail, but allow env.py to proceed for offline mode
    # or if autogenerate is not being used.
    # For autogenerate to work, target_metadata MUST be correctly populated.
    print(f"WARNING: Could not import Flask app or models: {e}")
    print("Autogenerate feature might not work correctly without target_metadata.")
    print("Ensure 'app' directory is in sys.path and contains __init__.py and models.py.")

# This is the Alembic Config object, which provides
# access to values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers based on the configuration in alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    By skipping the Engine creation, we don't even need a DBAPI to be available.
    This mode is useful for generating SQL scripts without connecting to a database.
    """
    # Get the database URL from alembic.ini's main section.
    # This URL can also be overridden by an environment variable.
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        # As a fallback, try common environment variables for the database URL.
        url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
        if not url:
            raise ValueError(
                "Database URL not found. Set 'sqlalchemy.url' in alembic.ini "
                "or DATABASE_URL/SQLALCHEMY_DATABASE_URI environment variable."
            )

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,  # Render literal values in the SQL output
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario, we need to create a SQLAlchemy Engine
    and associate a connection with the Alembic context.
    This mode connects to the actual database to apply migrations.
    """
    if create_app is None:
        raise RuntimeError("Flask app 'create_app' function not available for online migrations. "
                           "Ensure 'app' module is importable and defines 'create_app'.")

    # Create a Flask application instance and push an application context.
    # This allows access to app.config, which holds the database URI.
    app = create_app()
    with app.app_context():
        # Retrieve the database URI from the Flask application's configuration.
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        if not db_uri:
            raise ValueError("SQLALCHEMY_DATABASE_URI not found in Flask app configuration. "
                             "Ensure your Flask app's config is properly loaded.")

        # Set the database URL in Alembic's config object.
        # This ensures engine_from_config uses the correct URI from the Flask app.
        config.set_main_option("sqlalchemy.url", db_uri)

        # Create the SQLAlchemy engine using the configuration.
        # NullPool is used to prevent connection pooling issues during migrations.
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            # Configure the Alembic context with the database connection.
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                # 'compare_type=True' helps Alembic detect changes in column types
                # more accurately during autogenerate operations.
                compare_type=True,
            )

            with context.begin_transaction():
                context.run_migrations()

# Determine whether to run migrations in offline or online mode
# based on the Alembic context.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()