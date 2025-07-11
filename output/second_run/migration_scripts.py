# migration_scripts.py
# Alembic migration scripts for database schema changes.

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# Define the upgrade function (executed when migrating up).
def upgrade():
    op.create_table(
        'tasks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
        sa.Column('metadata', JSONB)
    )

# Define the downgrade function (executed when migrating down).
def downgrade():
    op.drop_table('tasks')