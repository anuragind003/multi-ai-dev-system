from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool

# The 'context' object is provided by Alembic's runtime environment.
# It is NOT imported directly from 'alembic.context' as a variable named 'context'.
# If you see 'from alembic import context', remove it to avoid
# 'AttributeError: module 'alembic.context' has no attribute 'config''.

import os
import sys
from os.path import abspath, dirname, join

# Add the project root to the sys.path to allow importing application modules.
# Assuming alembic/env.py is located at project_root/alembic/env.py
project_root = abspath(join(dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Import your SQLAlchemy metadata.
# This is crucial for Alembic's 'autogenerate' feature to detect model changes.
# Given Flask-SQLAlchemy, we typically import the 'db' instance and use its metadata.
try:
    # Import the db instance from app.routes where it's initialized
    # All models should be defined using this 'db' instance (e.g., class MyModel(db.Model):)
    from app.routes import db
    target_metadata = db.metadata
except ImportError as e:
    print(f"Error importing app.routes.db: {e}")
    print("Please ensure 'app/routes/__init__.py' exists and initializes a 'db' object for SQLAlchemy.")
    print("Alembic autogenerate will not work without target_metadata.")
    target_metadata = None # Set to None, or raise an error if strict.

# This is the Alembic Config object, which provides
# access to values within the .ini file in use (e.g., alembic.ini).
# The 'context' variable is made available globally by Alembic's runtime.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers based on the configuration in alembic.ini.
fileConfig(config.config_file_name)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

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
    # Get the SQLAlchemy URL and other connection parameters from the alembic.ini
    # The `config.config_ini_section` typically refers to the main section (e.g., '[alembic]')
    # where sqlalchemy.url and other options are defined.
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Optionally, include compare_type=True for more robust type comparison
            # when autogenerating migrations.
            # compare_type=True
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()