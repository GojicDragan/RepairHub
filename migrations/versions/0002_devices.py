"""Eigene Geräte aus den T06-Anwendungsfällen dauerhaft speichern."""

import sqlalchemy as sa
from alembic import op

revision = "0002_devices"
down_revision = "0001_register_user"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "devices",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("owner_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("manufacturer", sa.String(120), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.CheckConstraint("name ~ '[^[:space:]]'", name="ck_devices_name"),
        sa.CheckConstraint("manufacturer ~ '[^[:space:]]'", name="ck_devices_manufacturer"),
        sa.CheckConstraint("model ~ '[^[:space:]]'", name="ck_devices_model"),
    )
    # Eigentumsfilter und stabile ID-Reihenfolge der Fensterabfragen gemeinsam stützen.
    op.create_index("ix_devices_owner_id_id", "devices", ["owner_id", "id"])


def downgrade():
    raise RuntimeError(
        "Datenlöschendes Downgrade nicht unterstützt; Wiederherstellungsplan nutzen."
    )
