"""API-Key-Verwaltung ergänzt nur gehashte Schlüssel bestätigter Konten."""

import sqlalchemy as sa
from alembic import op

revision = "0005_api_keys"
down_revision = "0004_parts_and_work"
branch_labels = None
depends_on = None


def upgrade():
    # Bestehende Konten starten ohne API-Key. PostgreSQL erlaubt mehrere NULL-Werte
    # im Unique-Constraint, aber niemals denselben gespeicherten Schlüsselhash.
    op.add_column("users", sa.Column("api_key_hash", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("api_key_identity", sa.String(64), nullable=True))
    op.add_column(
        "users", sa.Column("api_key_created_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_unique_constraint("uq_users_api_key_hash", "users", ["api_key_hash"])


def downgrade():
    raise RuntimeError(
        "Datenlöschendes Downgrade nicht unterstützt; Wiederherstellungsplan nutzen."
    )
