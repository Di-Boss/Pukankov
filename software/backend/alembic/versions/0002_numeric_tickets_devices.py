"""Six-digit ticket codes, original catalog visibility and device credentials."""

import secrets
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "movies",
        sa.Column("in_catalog", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_movies_in_catalog", "movies", ["in_catalog"])
    op.add_column("tickets", sa.Column("ticket_code", sa.String(6), nullable=True))
    connection = op.get_bind()
    ids = connection.execute(sa.text("SELECT id FROM tickets")).scalars().all()
    if len(ids) > 900000:
        raise RuntimeError("The six-digit ticket code namespace is exhausted.")
    assigned = set()
    for ticket_id in ids:
        code = str(100000 + secrets.randbelow(900000))
        while code in assigned:
            code = str(100000 + secrets.randbelow(900000))
        assigned.add(code)
        connection.execute(
            sa.text("UPDATE tickets SET ticket_code=:code WHERE id=:id"),
            {"code": code, "id": ticket_id},
        )
    old_unique = next(
        c
        for c in sa.inspect(connection).get_unique_constraints("tickets")
        if c["column_names"] == ["scan_hash"]
    )
    with op.batch_alter_table(
        "tickets", naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"}
    ) as batch:
        batch.drop_constraint(
            old_unique["name"] or "uq_tickets_scan_hash", type_="unique"
        )
        batch.drop_column("scan_hash")
        batch.drop_column("qr_token")
        batch.alter_column("ticket_code", existing_type=sa.String(6), nullable=False)
        batch.create_unique_constraint("uq_tickets_ticket_code", ["ticket_code"])
    op.create_table(
        "devices",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "auditorium_id",
            sa.Integer(),
            sa.ForeignKey("auditoriums.id"),
            nullable=True,
        ),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    raise RuntimeError(
        "This migration converts ticket credentials and cannot be reversed safely. Restore a backup instead."
    )
