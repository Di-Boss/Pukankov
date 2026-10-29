"""Allowlisted educational RFID cards and one authorization per booking."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rfid_cards",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("uid_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("uid_suffix", sa.String(4), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "rfid_payments",
        sa.Column(
            "booking_id", sa.String(64), sa.ForeignKey("bookings.id"), primary_key=True
        ),
        sa.Column(
            "card_id", sa.String(40), sa.ForeignKey("rfid_cards.id"), nullable=False
        ),
        sa.Column(
            "device_id", sa.String(40), sa.ForeignKey("devices.id"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_rfid_payments_card_id", "rfid_payments", ["card_id"])
    op.create_index("ix_rfid_payments_device_id", "rfid_payments", ["device_id"])


def downgrade():
    raise RuntimeError(
        "RFID authorizations are part of purchase history. Restore a backup instead."
    )
