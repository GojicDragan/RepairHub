"""Fälle und Schritte entstehen mit den T07-Anwendungsfällen; additive Migration."""

import sqlalchemy as sa
from alembic import op

revision = "0003_repairs"
down_revision = "0002_devices"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "repairs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("device_id", sa.BigInteger(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "description ~ '[^[:space:]]' AND char_length(description) <= 10000",
            name="ck_repairs_description",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'in_progress', 'completed')", name="ck_repairs_status"
        ),
    )
    op.create_index("ix_repairs_device_id_id", "repairs", ["device_id", "id"])
    op.create_table(
        "repair_steps",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("repair_id", sa.BigInteger(), sa.ForeignKey("repairs.id"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("completed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint(
            "description ~ '[^[:space:]]' AND char_length(description) <= 2000",
            name="ck_repair_steps_description",
        ),
    )
    op.create_index("ix_repair_steps_repair_id_id", "repair_steps", ["repair_id", "id"])


def downgrade():
    raise RuntimeError(
        "Datenlöschendes Downgrade nicht unterstützt; Wiederherstellungsplan nutzen."
    )
