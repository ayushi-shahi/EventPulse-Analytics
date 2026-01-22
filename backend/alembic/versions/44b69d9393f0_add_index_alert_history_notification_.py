"""Performance: Add alert_history index for faster notification queries

Revision ID: 44b69d9393f0
Revises: bc45ac0e7528
Create Date: 2026-01-20 00:49
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '44b69d9393f0'
down_revision = 'bc45ac0e7528'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_alert_history_notification_sent
        ON alert_history (notification_sent, triggered_at)
    """)



def downgrade() -> None:
    # Safe rollback
    op.execute(
        """
        DROP INDEX IF EXISTS ix_alert_history_notification_sent
        """
    )
