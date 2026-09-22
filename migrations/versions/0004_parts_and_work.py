"""T08 ergänzt Ersatzteile und Arbeitswerte; vorhandene Reparaturen bleiben erhalten."""

import sqlalchemy as sa
from alembic import op

revision = "0004_parts_and_work"
down_revision = "0003_repairs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "repairs", sa.Column("hours", sa.Numeric(8, 2), nullable=False, server_default="0")
    )
    op.add_column(
        "repairs", sa.Column("hourly_rate", sa.Numeric(11, 2), nullable=False, server_default="0")
    )
    op.create_check_constraint("ck_repairs_hours", "repairs", "hours >= 0 AND hours <= 999999.99")
    op.create_check_constraint(
        "ck_repairs_hourly_rate", "repairs", "hourly_rate >= 0 AND hourly_rate <= 999999999.99"
    )
    op.create_table(
        "part_items",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("repair_id", sa.BigInteger(), sa.ForeignKey("repairs.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("unit_price", sa.Numeric(11, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("name ~ '[^[:space:]]'", name="ck_part_items_name"),
        sa.CheckConstraint(
            "unit_price >= 0 AND unit_price <= 999999999.99", name="ck_part_items_price"
        ),
        sa.CheckConstraint("quantity > 0", name="ck_part_items_quantity"),
    )
    op.create_index("ix_part_items_repair_id_id", "part_items", ["repair_id", "id"])


def downgrade():
    raise RuntimeError(
        "Datenlöschendes Downgrade nicht unterstützt; Wiederherstellungsplan nutzen."
    )
