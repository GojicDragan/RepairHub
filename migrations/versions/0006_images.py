"""Eigentumsgebundene Bildverweise; Pixeldateien liegen ausschliesslich in Garage."""

import sqlalchemy as sa
from alembic import op

revision = "0006_images"
down_revision = "0005_api_keys"
branch_labels = None
depends_on = None


def upgrade():
    for domain in ("devices", "repairs"):
        table = domain + "_images"
        op.create_table(
            table,
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("id", sa.String(32), primary_key=True),
            sa.Column("parent_id", sa.BigInteger(), sa.ForeignKey(domain + ".id"), nullable=False),
            sa.Column("filename", sa.String(200), nullable=False),
            sa.Column("width", sa.Integer(), nullable=False),
            sa.Column("height", sa.Integer(), nullable=False),
            sa.CheckConstraint(
                "width > 0 AND height > 0 AND width::bigint * height <= 20000000",
                name=f"ck_{table}_dimensions",
            ),
            sa.CheckConstraint("id ~ '^[a-f0-9]{32}$'", name=f"ck_{table}_id"),
            sa.CheckConstraint("length(trim(filename)) > 0", name=f"ck_{table}_filename"),
        )
        op.create_index(f"ix_{table}_parent_id_id", table, ["parent_id", "id"])


def downgrade():
    raise RuntimeError(
        "Datenlöschendes Downgrade nicht unterstützt; Wiederherstellungsplan nutzen."
    )
