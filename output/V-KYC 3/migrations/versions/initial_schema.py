"""initial_schema

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
    # Create UUID extension if not exists
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # Create 'users' table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('username', sa.VARCHAR(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.VARCHAR(255), nullable=False),
        sa.Column('role', sa.VARCHAR(50), nullable=False),
        sa.Column('email', sa.VARCHAR(255), unique=True, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("role IN ('Team Lead', 'Process Manager', 'Administrator')", name='chk_user_role')
    )
    op.create_comment(op.get_table_comment('users'), 'Stores user authentication and authorization details.')
    op.create_comment(op.get_column_comment('users', 'id'), 'Unique identifier for the user.')
    op.create_comment(op.get_column_comment('users', 'username'), 'Unique username for login.')
    op.create_comment(op.get_column_comment('users', 'password_hash'), 'Hashed password for security.')
    op.create_comment(op.get_column_comment('users', 'role'), 'User role (e.g., Team Lead, Process Manager, Administrator).')
    op.create_comment(op.get_column_comment('users', 'email'), 'Unique email address of the user.')
    op.create_comment(op.get_column_comment('users', 'created_at'), 'Timestamp when the user record was created.')


    # Create 'vkyc_recordings' table
    op.create_table(
        'vkyc_recordings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('vkyc_case_id', sa.VARCHAR(100), unique=True, nullable=False),
        sa.Column('customer_name', sa.VARCHAR(255), nullable=False),
        sa.Column('recording_date', sa.DATE(), nullable=False),
        sa.Column('duration_seconds', sa.INTEGER(), nullable=False),
        sa.Column('file_path', sa.TEXT(), unique=True, nullable=False),
        sa.Column('status', sa.VARCHAR(50), nullable=False, server_default=sa.text("'completed'")),
        sa.Column('uploaded_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('metadata_json', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], name='fk_uploaded_by_user', ondelete='RESTRICT', onupdate='CASCADE'),
        sa.CheckConstraint("duration_seconds > 0", name='chk_duration_positive'),
        sa.CheckConstraint("status IN ('completed', 'processing', 'failed', 'reviewed', 'pending_review')", name='chk_vkyc_status')
    )
    op.create_comment(op.get_table_comment('vkyc_recordings'), 'Stores metadata for V-KYC recordings.')
    op.create_comment(op.get_column_comment('vkyc_recordings', 'id'), 'Unique identifier for the V-KYC recording.')
    op.create_comment(op.get_column_comment('vkyc_recordings', 'vkyc_case_id'), 'Unique identifier for the V-KYC case.')
    op.create_comment(op.get_column_comment('vkyc_recordings', 'customer_name'), 'Name of the customer associated with the recording.')
    op.create_comment(op.get_column_comment('vkyc_recordings', 'recording_date'), 'Date when the recording was made.')
    op.create_comment(op.get_column_comment('vkyc_recordings', 'duration_seconds'), 'Duration of the recording in seconds.')
    op.create_comment(op.get_column_comment('vkyc_recordings', 'file_path'), 'Path or URL to the actual recording file.')
    op.create_comment(op.get_column_comment('vkyc_recordings', 'status'), 'Current status of the recording (e.g., completed, processing, failed).')
    op.create_comment(op.get_column_comment('vkyc_recordings', 'uploaded_by_user_id'), 'ID of the user who uploaded this recording.')
    op.create_comment(op.get_column_comment('vkyc_recordings', 'created_at'), 'Timestamp when the recording metadata was created.')
    op.create_comment(op.get_column_comment('vkyc_recordings', 'metadata_json'), 'Additional metadata in JSONB format.')


    # Create 'audit_logs' table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.VARCHAR(100), nullable=False),
        sa.Column('resource_type', sa.VARCHAR(100), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_audit_user', ondelete='CASCADE', onupdate='CASCADE'),
        sa.CheckConstraint("action IN ('CREATE', 'READ', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'PASSWORD_CHANGE', 'STATUS_CHANGE')", name='chk_audit_action'),
        sa.CheckConstraint("resource_type IN ('USER', 'VKYC_RECORDING', 'SYSTEM')", name='chk_audit_resource_type')
    )
    op.create_comment(op.get_table_comment('audit_logs'), 'Records all significant user actions for auditing purposes.')
    op.create_comment(op.get_column_comment('audit_logs', 'id'), 'Unique identifier for the audit log entry.')
    op.create_comment(op.get_column_comment('audit_logs', 'user_id'), 'ID of the user who performed the action.')
    op.create_comment(op.get_column_comment('audit_logs', 'action'), 'Description of the action performed.')
    op.create_comment(op.get_column_comment('audit_logs', 'resource_type'), 'Type of resource affected by the action.')
    op.create_comment(op.get_column_comment('audit_logs', 'resource_id'), 'ID of the resource affected by the action.')
    op.create_comment(op.get_column_comment('audit_logs', 'timestamp'), 'Timestamp when the action occurred.')
    op.create_comment(op.get_column_comment('audit_logs', 'ip_address'), 'IP address from which the action originated.')
    op.create_comment(op.get_column_comment('audit_logs', 'details'), 'Additional details about the action in JSONB format.')


def downgrade():
    # Drop tables in reverse order of creation to respect foreign key constraints
    op.drop_table('audit_logs')
    op.drop_table('vkyc_recordings')
    op.drop_table('users')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp";')