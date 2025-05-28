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
# Assuming migrations/env.py is located at project_root/migrations/env.py
project_root = abspath(join(dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Import your Flask app's db instance and models
# This is crucial for Alembic to detect changes in your models.
# Based on the provided context (e.g., app/routes/reports.py, app/tasks/data_cleanup.py),
# 'db' is expected to be in 'app.extensions' and models in 'app.models'.
from app.extensions import db
import app.models  # Import the models module to ensure all models are loaded and registered with db.metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up logging based on the configuration in alembic.ini.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# This is where Alembic gets the current state of your SQLAlchemy models.
target_metadata = db.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired here.
# For example, if you have different sections in alembic.ini for different environments
# you might get the URL from a specific section.

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

# Determine whether to run in offline or online mode based on Alembic's context.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()