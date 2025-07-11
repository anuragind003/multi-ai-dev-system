"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2023-10-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create UUID extension if not exists
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # Create ENUM types
    user_role_enum = postgresql.ENUM('admin', 'auditor', 'viewer', name='user_role_enum')
    user_role_enum.create(op.get_bind(), checkfirst=True)

    audit_action_enum = postgresql.ENUM('login', 'view_recording_metadata', 'download_recording', 'user_created', 'user_updated', 'user_deleted', 'recording_uploaded', 'recording_status_updated', name='audit_action_enum')
    audit_action_enum.create(op.get_bind(), checkfirst=True)

    recording_status_enum = postgresql.ENUM('pending_upload', 'uploaded', 'processing', 'completed', 'failed', 'archived', name='recording_status_enum')
    recording_status_enum.create(op.get_bind(), checkfirst=True)

    # Create 'users' table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('username', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', user_role_enum, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False)
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_role', 'users', ['role'])

    # Create 'vkyc_recordings' table
    op.create_table(
        'vkyc_recordings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('customer_id', sa.String(255), nullable=False),
        sa.Column('recording_name', sa.String(255), nullable=False),
        sa.Column('recording_path', sa.Text(), unique=True, nullable=False),
        sa.Column('duration_seconds', sa.Integer()),
        sa.Column('recording_timestamp', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('status', recording_status_enum, nullable=False, server_default='uploaded'),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], name='fk_uploaded_by', ondelete='RESTRICT'),
        sa.CheckConstraint('duration_seconds IS NULL OR duration_seconds >= 0', name='chk_duration_positive')
    )
    op.create_index('ix_vkyc_recordings_customer_id', 'vkyc_recordings', ['customer_id'])
    op.create_index('ix_vkyc_recordings_recording_timestamp', 'vkyc_recordings', ['recording_timestamp'])
    op.create_index('ix_vkyc_recordings_status', 'vkyc_recordings', ['status'])
    op.create_index('ix_vkyc_recordings_uploaded_by', 'vkyc_recordings', ['uploaded_by'])


    # Create 'audit_logs' table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', audit_action_enum, nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True)),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('details', postgresql.JSONB()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_audit_user_id', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['resource_id'], ['vkyc_recordings.id'], name='fk_audit_resource_id', ondelete='SET NULL')
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_resource_id', 'audit_logs', ['resource_id'])
    op.create_index('ix_audit_logs_user_action_timestamp', 'audit_logs', ['user_id', 'action', 'timestamp'])


    # Create trigger function for 'updated_at' column
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Apply trigger to 'users' table
    op.execute("""
        CREATE TRIGGER set_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade():
    # Drop trigger
    op.execute('DROP TRIGGER IF EXISTS set_updated_at ON users;')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column();')

    # Drop tables in reverse order of dependency
    op.drop_table('audit_logs')
    op.drop_table('vkyc_recordings')
    op.drop_table('users')

    # Drop ENUM types
    audit_action_enum = postgresql.ENUM('login', 'view_recording_metadata', 'download_recording', 'user_created', 'user_updated', 'user_deleted', 'recording_uploaded', 'recording_status_updated', name='audit_action_enum')
    audit_action_enum.drop(op.get_bind(), checkfirst=True)

    recording_status_enum = postgresql.ENUM('pending_upload', 'uploaded', 'processing', 'completed', 'failed', 'archived', name='recording_status_enum')
    recording_status_enum.drop(op.get_bind(), checkfirst=True)

    user_role_enum = postgresql.ENUM('admin', 'auditor', 'viewer', name='user_role_enum')
    user_role_enum.drop(op.get_bind(), checkfirst=True)

    # Drop UUID extension (optional, usually kept)
    # op.execute('DROP EXTENSION IF EXISTS "uuid-ossp";')