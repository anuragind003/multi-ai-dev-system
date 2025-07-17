# db/migrations/versions/initial_schema.py
"""Initial schema creation for VKYC Recordings system

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2023-10-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create the uuid-ossp extension if it doesn't exist
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # Create 'users' table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('username', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='user'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        comment='Stores user accounts for the VKYC portal.'
    )
    # Add trigger for 'updated_at' column on 'users' table
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER users_updated_at_trigger
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # Create 'vkyc_recordings' table
    op.create_table(
        'vkyc_recordings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('customer_id', sa.String(255), nullable=False),
        sa.Column('recording_date', sa.Date, nullable=False),
        sa.Column('recording_time', sa.Time, nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('file_path', sa.Text, nullable=False),
        sa.Column('duration_seconds', sa.Integer),
        sa.Column('agent_id', sa.String(255)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        comment='Stores metadata for each V-KYC recording.'
    )

    # Create 'audit_logs' table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(255), nullable=False),
        sa.Column('resource_type', sa.String(255)),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True)),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('ip_address', postgresql.INET),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='fk_user'),
        comment='Records user actions for auditing purposes.'
    )

    # Add comments to columns (Alembic doesn't directly support column comments in create_table, so execute raw SQL)
    op.execute("COMMENT ON COLUMN users.id IS 'Unique identifier for the user.';")
    op.execute("COMMENT ON COLUMN users.username IS 'Unique username for login.';")
    op.execute("COMMENT ON COLUMN users.password_hash IS 'Hashed password for security.';")
    op.execute("COMMENT ON COLUMN users.email IS 'Unique email address for the user.';")
    op.execute("COMMENT ON COLUMN users.role IS 'User role (e.g., admin, user, auditor) for access control.';")
    op.execute("COMMENT ON COLUMN users.created_at IS 'Timestamp when the user account was created.';")
    op.execute("COMMENT ON COLUMN users.updated_at IS 'Timestamp when the user account was last updated.';")

    op.execute("COMMENT ON COLUMN vkyc_recordings.id IS 'Unique identifier for the VKYC recording.';")
    op.execute("COMMENT ON COLUMN vkyc_recordings.customer_id IS 'Identifier for the customer associated with the recording.';")
    op.execute("COMMENT ON COLUMN vkyc_recordings.recording_date IS 'Date when the VKYC recording was made.';")
    op.execute("COMMENT ON COLUMN vkyc_recordings.recording_time IS 'Time when the VKYC recording was made.';")
    op.execute("COMMENT ON COLUMN vkyc_recordings.status IS 'Current status of the VKYC recording (e.g., PENDING, APPROVED, REJECTED).';")
    op.execute("COMMENT ON COLUMN vkyc_recordings.file_path IS 'Path or URL to the actual recording file storage.';")
    op.execute("COMMENT ON COLUMN vkyc_recordings.duration_seconds IS 'Duration of the recording in seconds.';")
    op.execute("COMMENT ON COLUMN vkyc_recordings.agent_id IS 'Identifier of the agent who conducted the VKYC.';")
    op.execute("COMMENT ON COLUMN vkyc_recordings.created_at IS 'Timestamp when the recording metadata was created.';")

    op.execute("COMMENT ON COLUMN audit_logs.id IS 'Unique identifier for the audit log entry.';")
    op.execute("COMMENT ON COLUMN audit_logs.user_id IS 'ID of the user who performed the action.';")
    op.execute("COMMENT ON COLUMN audit_logs.action IS 'Description of the action performed (e.g., LOGIN, CREATE_RECORDING).';")
    op.execute("COMMENT ON COLUMN audit_logs.resource_type IS 'Type of resource affected by the action (e.g., VKYC_RECORDING, USER).';")
    op.execute("COMMENT ON COLUMN audit_logs.resource_id IS 'ID of the specific resource affected by the action.';")
    op.execute("COMMENT ON COLUMN audit_logs.timestamp IS 'Timestamp when the action occurred.';")
    op.execute("COMMENT ON COLUMN audit_logs.ip_address IS 'IP address from which the action originated.';")


def downgrade():
    # Drop tables in reverse order of creation to respect foreign key constraints
    op.drop_table('audit_logs')
    op.drop_table('vkyc_recordings')
    op.drop_trigger('users_updated_at_trigger', 'users')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;')
    op.drop_table('users')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp";')