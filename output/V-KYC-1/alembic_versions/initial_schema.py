# alembic_versions/initial_schema.py
# This is an Alembic migration script for the initial database schema.
# It creates tables, custom types, and sets up relationships.

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create custom ENUM types
    user_role_enum = postgresql.ENUM('admin', 'auditor', 'viewer', name='user_role_enum')
    user_role_enum.create(op.get_bind(), checkfirst=True)

    audit_action_enum = postgresql.ENUM(
        'login', 'view_recording_metadata', 'download_recording',
        'create_user', 'update_user', 'delete_user',
        'upload_recording', 'update_recording', 'delete_recording',
        name='audit_action_enum'
    )
    audit_action_enum.create(op.get_bind(), checkfirst=True)

    # Create 'users' table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('username', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', user_role_enum, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        comment='Stores user accounts for the VKYC team with their roles.'
    )
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
        CREATE TRIGGER set_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)
    op.create_index('ix_users_username', 'users', ['username'], unique=True) # Redundant with unique=True on column, but explicit for clarity.

    # Create 'vkyc_recordings' table
    op.create_table(
        'vkyc_recordings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('customer_id', sa.String(255), nullable=False),
        sa.Column('recording_name', sa.String(255), nullable=False),
        sa.Column('recording_path', sa.Text(), nullable=False, unique=True, comment='Path/key in object storage'),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('recording_timestamp', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='completed'),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], name='fk_uploaded_by', ondelete='SET NULL'),
        comment='Stores metadata about each V-KYC recording.'
    )
    op.create_index('ix_vkyc_recordings_customer_id', 'vkyc_recordings', ['customer_id'])
    op.create_index('ix_vkyc_recordings_recording_timestamp', 'vkyc_recordings', ['recording_timestamp'])

    # Create 'audit_logs' table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', audit_action_enum, nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True, comment='Additional context for the action'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_audit_user', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resource_id'], ['vkyc_recordings.id'], name='fk_audit_resource', ondelete='SET NULL'),
        comment='Records all significant user actions, especially access and download of recordings.'
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])


def downgrade():
    # Drop tables in reverse order of creation to handle foreign key dependencies
    op.drop_table('audit_logs')
    op.drop_table('vkyc_recordings')
    op.drop_table('users')

    # Drop custom ENUM types
    audit_action_enum = postgresql.ENUM(
        'login', 'view_recording_metadata', 'download_recording',
        'create_user', 'update_user', 'delete_user',
        'upload_recording', 'update_recording', 'delete_recording',
        name='audit_action_enum'
    )
    audit_action_enum.drop(op.get_bind(), checkfirst=True)

    user_role_enum = postgresql.ENUM('admin', 'auditor', 'viewer', name='user_role_enum')
    user_role_enum.drop(op.get_bind(), checkfirst=True)

    # Drop the trigger function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;")