import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add the project root to sys.path to allow importing backend modules.
# This is necessary because env.py is located in backend/migrations/,
# and it needs to import modules from the 'backend' package (e.g., backend.models).
# The project root is two levels up from the current file.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use (alembic.ini).
# This line is fundamental to Alembic's operation and assumes Alembic is running this script.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers based on the configuration in alembic.ini.
fileConfig(config.config_file_name)

# Initialize target_metadata to None. It will be populated if Flask app loads successfully.
target_metadata = None

# Import the Flask application's `db` instance and `create_app` function.
# This is crucial for Alembic's 'autogenerate' feature to discover your SQLAlchemy models
# and for setting the database connection URI consistently with your Flask app.
try:
    from backend.app import create_app
    from backend.models import db

    # Create a dummy Flask app instance. This loads the application's configuration,
    # including the SQLALCHEMY_DATABASE_URI, and initializes the `db` object.
    app = create_app()

    # Push an application context. This is necessary for Flask-SQLAlchemy's `db` object
    # to be fully initialized and associated with the application's configuration.
    app.app_context().push()

    # Set the SQLAlchemy URL in Alembic's configuration using the URL from the Flask app.
    # This ensures that Alembic connects to the same database as your Flask application.
    config.set_main_option("sqlalchemy.url", app.config['SQLALCHEMY_DATABASE_URI'])

    # This is the MetaData object from your Flask-SQLAlchemy `db` instance.
    # Alembic uses this `target_metadata` to compare against the actual database schema
    # when generating migrations (e.g., `alembic revision --autogenerate`).
    target_metadata = db.metadata

except Exception as e:
    # If there's an error importing or initializing the Flask app (e.g., missing dependencies,
    # incorrect paths, or issues with app configuration), print a warning.
    # In such cases, Alembic will fall back to using the database URL configured directly
    # in `alembic.ini` (if present). `target_metadata` will remain `None`, which means
    # autogenerate functionality will not work correctly.
    print(f"WARNING: Could not load Flask app or database models for Alembic. Error: {e}")
    print("Alembic will proceed using configuration from alembic.ini only. Autogenerate might not work.")

# The rest of the env.py file defines how migrations are run,
# both in 'offline' (generating SQL scripts) and 'online' (applying to DB) modes.

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is still acceptable
    here as a source of SQL support.

    By skipping the Engine creation we don't even need a DBAPI to be
    available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # `compare_type=True` helps Alembic detect changes in column types
            # during autogenerate operations.
            compare_type=True
        )

        with context.begin_transaction():
            context.run_migrations()


# Determine whether to run migrations in offline or online mode
# based on the Alembic context.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()