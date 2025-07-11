# alembic/versions/initial_schema.py
"""Initial schema creation for VKYC Portal

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
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('username', sa.VARCHAR(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.VARCHAR(255), nullable=False),
        sa.Column('email', sa.VARCHAR(255), unique=True, nullable=False),
        sa.Column('role', sa.VARCHAR(50), nullable=False, server_default='user'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        comment='Stores user accounts for the VKYC portal.'
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create vkyc_recordings table
    op.create_table(
        'vkyc_recordings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('customer_id', sa.VARCHAR(255), nullable=False),
        sa.Column('recording_date', sa.DATE(), nullable=False),
        sa.Column('recording_time', sa.TIME(), nullable=False),
        sa.Column('status', sa.VARCHAR(50), nullable=False),
        sa.Column('file_path', sa.TEXT(), nullable=False),
        sa.Column('duration_seconds', sa.INTEGER()),
        sa.Column('agent_id', sa.VARCHAR(255)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        comment='Stores metadata for each V-KYC recording.'
    )
    op.create_index('ix_vkyc_recordings_customer_id', 'vkyc_recordings', ['customer_id'])
    op.create_index('ix_vkyc_recordings_date_time', 'vkyc_recordings', ['recording_date', 'recording_time'])
    op.create_index('ix_vkyc_recordings_status', 'vkyc_recordings', ['status'])

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.VARCHAR(255), nullable=False),
        sa.Column('resource_type', sa.VARCHAR(255)),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True)),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('ip_address', postgresql.INET()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        comment='Records user actions for auditing purposes.'
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])

    # Add trigger for updated_at column on users table
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER update_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade():
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS update_users_updated_at ON users;")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")

    # Drop tables in reverse order of creation to respect foreign key constraints
    op.drop_table('audit_logs')
    op.drop_table('vkyc_recordings')
    op.drop_table('users')