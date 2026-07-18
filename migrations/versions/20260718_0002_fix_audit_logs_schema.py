"""fix audit_logs schema drift

The audit_logs table was created by an earlier admin-audit feature with
columns (admin_id, action, old_value, new_value, ip_address, created_at,
request_id). backend/models.py's AuditLog was later rewritten for the
device/terminal provisioning flow to use (event_type, actor_type, actor_id,
notes, occurred_at) instead, but startup only runs
Base.metadata.create_all(), which never alters existing tables - so the
live table never picked up the new columns. Every write_audit_log() call
(device register/assign/deactivate, terminal deactivate, order
create/complete) was throwing UndefinedColumnError, which surfaced to the
Expo app as a generic "Network error" on first launch after install.

Revision ID: 20260718_0002
Revises: 20260612_0001
Create Date: 2026-07-18
"""

from alembic import op

revision = "20260718_0002"
down_revision = "20260612_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE ekart_prod.audit_logs
            ADD COLUMN IF NOT EXISTS event_type VARCHAR(80),
            ADD COLUMN IF NOT EXISTS actor_type VARCHAR(20) DEFAULT 'system',
            ADD COLUMN IF NOT EXISTS actor_id UUID,
            ADD COLUMN IF NOT EXISTS notes TEXT,
            ADD COLUMN IF NOT EXISTS occurred_at TIMESTAMP DEFAULT NOW()
        """
    )
    op.execute(
        "UPDATE ekart_prod.audit_logs SET event_type = COALESCE(event_type, action) WHERE event_type IS NULL"
    )
    op.execute(
        "UPDATE ekart_prod.audit_logs SET occurred_at = COALESCE(occurred_at, created_at) WHERE occurred_at IS NULL"
    )
    # Legacy admin-audit columns aren't populated by the current AuditLog
    # model - relax their NOT NULL constraints so new inserts don't fail.
    op.execute("ALTER TABLE ekart_prod.audit_logs ALTER COLUMN action DROP NOT NULL")
    op.execute("ALTER TABLE ekart_prod.audit_logs ALTER COLUMN created_at SET DEFAULT NOW()")


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE ekart_prod.audit_logs
            DROP COLUMN IF EXISTS event_type,
            DROP COLUMN IF EXISTS actor_type,
            DROP COLUMN IF EXISTS actor_id,
            DROP COLUMN IF EXISTS notes,
            DROP COLUMN IF EXISTS occurred_at
        """
    )
    op.execute("ALTER TABLE ekart_prod.audit_logs ALTER COLUMN action SET NOT NULL")
