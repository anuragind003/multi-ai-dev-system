# alembic/versions/initial_schema.py
"""Initial schema creation for users, vkyc_recordings, and audit_logs tables.

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
    # Create the 'users' table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('username', sa.VARCHAR(length=255), nullable=False, unique=True),
        sa.Column('password_hash', sa.VARCHAR(length=255), nullable=False),
        sa.Column('role', sa.VARCHAR(length=50), nullable=False),
        sa.Column('email', sa.VARCHAR(length=255), nullable=False, unique=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("role IN ('Team Lead', 'Process Manager', 'Administrator', 'Auditor')", name='users_role_check')
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create the 'vkyc_recordings' table
    op.create_table(
        'vkyc_recordings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vkyc_case_id', sa.VARCHAR(length=100), nullable=False, unique=True),
        sa.Column('customer_name', sa.VARCHAR(length=255), nullable=False),
        sa.Column('recording_date', sa.DATE(), nullable=False),
        sa.Column('duration_seconds', sa.INTEGER(), nullable=False),
        sa.Column('file_path', sa.TEXT(), nullable=False, unique=True),
        sa.Column('status', sa.VARCHAR(length=50), nullable=False, server_default='completed'),
        sa.Column('uploaded_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint("duration_seconds > 0", name='vkyc_recordings_duration_check'),
        sa.CheckConstraint("status IN ('completed', 'processing', 'failed', 'archived')", name='vkyc_recordings_status_check'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], name='fk_uploaded_by_user', ondelete='RESTRICT')
    )
    op.create_index(op.f('ix_vkyc_recordings_vkyc_case_id'), 'vkyc_recordings', ['vkyc_case_id'], unique=True)
    op.create_index(op.f('ix_vkyc_recordings_uploaded_by_user_id'), 'vkyc_recordings', ['uploaded_by_user_id'])
    op.create_index(op.f('ix_vkyc_recordings_recording_date'), 'vkyc_recordings', ['recording_date'])

    # Create the 'audit_logs' table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.VARCHAR(length=100), nullable=False),
        sa.Column('resource_type', sa.VARCHAR(length=100), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_audit_user', ondelete='RESTRICT')
    )
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'])
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'])
    op.create_index(op.f('ix_audit_logs_resource_type_id'), 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'])

    # Add the audit trigger function and trigger for vkyc_recordings
    # Note: Alembic's `op.execute` is used for raw SQL statements.
    op.execute("""
        CREATE OR REPLACE FUNCTION log_vkyc_recording_changes()
        RETURNS TRIGGER AS $$
        DECLARE
            _user_id UUID;
            _action TEXT;
            _details JSONB;
        BEGIN
            BEGIN
                _user_id := current_setting('app.current_user_id', TRUE)::UUID;
            EXCEPTION
                WHEN OTHERS THEN
                    _user_id := (SELECT id FROM users WHERE username = 'system_auditor' LIMIT 1);
                    IF _user_id IS NULL THEN
                        RAISE EXCEPTION 'Audit trigger failed: app.current_user_id not set and system_auditor user not found.';
                    END IF;
            END;

            IF TG_OP = 'INSERT' THEN
                _action := 'CREATE';
                _details := jsonb_build_object('new_data', to_jsonb(NEW));
            ELSIF TG_OP = 'UPDATE' THEN
                _action := 'UPDATE';
                _details := jsonb_build_object('old_data', to_jsonb(OLD), 'new_data', to_jsonb(NEW));
            ELSIF TG_OP = 'DELETE' THEN
                _action := 'DELETE';
                _details := jsonb_build_object('old_data', to_jsonb(OLD));
            END IF;

            INSERT INTO audit_logs (user_id, action, resource_type, resource_id, ip_address, details)
            VALUES (
                _user_id,
                _action,
                'vkyc_recording',
                COALESCE(NEW.id, OLD.id),
                inet_client_addr(),
                _details
            );

            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER vkyc_recording_audit_trigger
        AFTER INSERT OR UPDATE OR DELETE ON vkyc_recordings
        FOR EACH ROW EXECUTE FUNCTION log_vkyc_recording_changes();
    """)


def downgrade():
    # Drop the audit trigger and function first
    op.execute("DROP TRIGGER IF EXISTS vkyc_recording_audit_trigger ON vkyc_recordings;")
    op.execute("DROP FUNCTION IF EXISTS log_vkyc_recording_changes();")

    # Drop tables in reverse order of dependency
    op.drop_table('audit_logs')
    op.drop_table('vkyc_recordings')
    op.drop_table('users')