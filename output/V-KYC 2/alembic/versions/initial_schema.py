# alembic/versions/initial_schema.py
# Alembic migration script for initial database schema creation.

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create uuid-ossp extension if not exists
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('username', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("role IN ('Team Lead', 'Process Manager', 'Admin')", name='chk_users_role'),
        comment='Stores user authentication and authorization information.'
    )
    op.create_index('idx_users_username', 'users', ['username'], unique=True)
    op.create_index('idx_users_email', 'users', ['email'], unique=True)

    # Create recordings table
    op.create_table(
        'recordings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('vkyc_id', sa.String(100), unique=True, nullable=False),
        sa.Column('customer_name', sa.String(255), nullable=False),
        sa.Column('recording_date', sa.Date(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('storage_path', sa.Text(), nullable=False),
        sa.Column('uploaded_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('uploaded_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('status', sa.String(50), server_default='available'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], name='fk_uploaded_by_user', ondelete='RESTRICT'),
        sa.CheckConstraint("duration_seconds > 0", name='chk_recordings_duration_seconds'),
        sa.CheckConstraint("status IN ('available', 'processing', 'archived', 'deleted', 'error')", name='chk_recordings_status'),
        comment='Stores metadata for each V-KYC recording.'
    )
    op.create_index('idx_recordings_vkyc_id', 'recordings', ['vkyc_id'], unique=True)
    op.create_index('idx_recordings_uploaded_by_user_id', 'recordings', ['uploaded_by_user_id'])
    op.create_index('idx_recordings_recording_date', 'recordings', ['recording_date'])

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('recording_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_audit_user', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recording_id'], ['recordings.id'], name='fk_audit_recording', ondelete='SET NULL'),
        comment='Records all significant user actions for auditing purposes.'
    )
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_logs_recording_id', 'audit_logs', ['recording_id'])

    # Add trigger for vkyc_id format validation
    op.execute("""
        CREATE OR REPLACE FUNCTION validate_vkyc_id_format()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.vkyc_id !~ '^[A-Z]{3}[0-9]{6}$' THEN
                RAISE EXCEPTION 'Invalid VKYC ID format. Must be 3 uppercase letters followed by 6 digits (e.g., ABC123456).';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_validate_vkyc_id
        BEFORE INSERT OR UPDATE ON recordings
        FOR EACH ROW
        EXECUTE FUNCTION validate_vkyc_id_format();
    """)


def downgrade():
    # Drop trigger
    op.execute('DROP TRIGGER IF EXISTS trg_validate_vkyc_id ON recordings;')
    op.execute('DROP FUNCTION IF EXISTS validate_vkyc_id_format();')

    # Drop tables in reverse order of creation to respect foreign key dependencies
    op.drop_table('audit_logs')
    op.drop_table('recordings')
    op.drop_table('users')

    # Drop uuid-ossp extension if no longer needed by other parts of the database
    # (This is generally not recommended in a downgrade unless you're sure it's safe)
    # op.execute('DROP EXTENSION IF EXISTS "uuid-ossp";')