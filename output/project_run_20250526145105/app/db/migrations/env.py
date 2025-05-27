import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add the project root to the sys.path to allow importing app modules.
# This assumes the project structure is:
# project_root/
# ├── app/
# │   ├── core/
# │   │   └── config.py
# │   ├── db/
# │   │   ├── base.py
# │   │   ├── models/
# │   │   │   ├── __init__.py
# │   │   │   ├── customer.py
# │   │   │   ├── offer.py
# │   │   │   ├── offer_history.py
# │   │   │   └── campaign_event.py
# │   │   └── migrations/
# │   │       └── env.py  <-- This file
# └── alembic.ini
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", "..")) # Go up three levels to reach project root
sys.path.insert(0, project_root)

# Import your models' Base and all models to ensure metadata is loaded for autogenerate.
from app.db.base import Base
# Import all model modules so that their definitions are registered with Base.metadata.
# Adjust these imports based on where your SQLAlchemy models are actually defined.
# Assuming models are in app/db/models/ and each is a separate file.
from app.db.models import customer, offer, offer_history, campaign_event

# Import application settings to get the database URL.
from app.core.config import settings

# this is the Alembic Config object, which provides
# access to values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    # Get the database URL from application settings.
    # This ensures consistency with the application's database configuration.
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
    # This overrides any sqlalchemy.url in alembic.ini, ensuring the correct DB.
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=settings.DATABASE_URL, # Explicitly pass URL from settings
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # compare_type=True helps Alembic detect changes in column types more accurately
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()