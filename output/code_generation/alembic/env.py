# alembic/env.py
# Alembic environment configuration.

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import Base
# target_metadata = Base.metadata
from sqlalchemy import MetaData, Table, Column, String, DateTime, UUID, Integer, Date, Time, Text
from sqlalchemy.dialects import postgresql

# Define a dummy MetaData for autogenerate if you were using SQLAlchemy ORM models.
# Since we're defining schema directly in the migration, this isn't strictly needed
# for initial setup, but good practice for future autogenerate.
# For this project, we're using raw SQL for schema definition in the migration itself.
# If you were to use SQLAlchemy ORM models, you'd import them here and set target_metadata.
# Example:
# from your_app.models import Base
# target_metadata = Base.metadata

# For a "schema-first" approach where the initial migration is hand-written,
# target_metadata can be None or an empty MetaData.
target_metadata = MetaData()

# Define tables explicitly if not using ORM models for autogenerate,
# or just keep target_metadata = None if you only use hand-written migrations.
# For this exercise, we'll define them here for clarity, though the actual
# create_table calls are in the migration script.
Table(
    'users', target_metadata,
    Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
    Column('username', String(255), unique=True, nullable=False),
    Column('password_hash', String(255), nullable=False),
    Column('email', String(255), unique=True, nullable=False),
    Column('role', String(50), nullable=False),
    Column('created_at', DateTime(timezone=True)),
    Column('updated_at', DateTime(timezone=True))
)

Table(
    'vkyc_recordings', target_metadata,
    Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
    Column('customer_id', String(255), nullable=False),
    Column('recording_date', Date, nullable=False),
    Column('recording_time', Time, nullable=False),
    Column('status', String(50), nullable=False),
    Column('file_path', Text, nullable=False),
    Column('duration_seconds', Integer),
    Column('agent_id', String(255)),
    Column('created_at', DateTime(timezone=True))
)

Table(
    'audit_logs', target_metadata,
    Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
    Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    Column('action', String(255), nullable=False),
    Column('resource_type', String(255)),
    Column('resource_id', postgresql.UUID(as_uuid=True)),
    Column('timestamp', DateTime(timezone=True)),
    Column('ip_address', postgresql.INET)
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

    In this scenario, we need to create an Engine
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
            target_metadata=target_metadata,
            # For PostgreSQL, ensure UUID type is handled correctly
            # by providing a custom render_item for autogenerate if needed.
            # For hand-written migrations, this is less critical.
            # include_object=include_object, # Example for filtering objects
            # process_revision_directives=process_revision_directives, # Example for custom directives
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()