"""Nur die von Flask-Security benötigte Identitätspersistenz anlegen."""

import sqlalchemy as sa
from alembic import op

revision = "0001_register_user"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("fs_uniquifier", sa.String(64), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fs_uniquifier"),
        sa.CheckConstraint("char_length(btrim(username)) > 0", name="ck_users_username"),
        sa.CheckConstraint("char_length(btrim(email)) > 0", name="ck_users_email"),
        sa.CheckConstraint("char_length(password) > 0", name="ck_users_password"),
    )
    op.create_index("uq_users_username", "users", [sa.text("lower(username)")], unique=True)
    op.create_index("uq_users_email", "users", [sa.text("lower(email)")], unique=True)
    op.create_table(
        "roles",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.String(255)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "roles_users",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role_id", sa.BigInteger(), sa.ForeignKey("roles.id"), primary_key=True),
    )


def downgrade():
    # Kein blindes Löschen registrierter Konten bei einem Image-Rollback.
    raise RuntimeError(
        "Datenlöschendes Downgrade nicht unterstützt; Wiederherstellungsplan nutzen."
    )
