"""Keep RFID on ESP32; remove the unused server card registry.

Bookings and Payment records are retained. Any previous RFID authorization is
represented by a non-card audit event before the obsolete tables are removed.
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
        INSERT INTO audit_logs (user_id, action, object_id, created_at)
        SELECT d.user_id, 'legacy.terminal_payment', r.booking_id, r.created_at
        FROM rfid_payments r JOIN devices d ON d.id = r.device_id
    """
        )
    )
    op.drop_index("ix_rfid_payments_device_id", table_name="rfid_payments")
    op.drop_index("ix_rfid_payments_card_id", table_name="rfid_payments")
    op.drop_table("rfid_payments")
    op.drop_table("rfid_cards")


def downgrade():
    raise RuntimeError("Card data was removed by design. Restore a backup instead.")
