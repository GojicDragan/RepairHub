"""Technische Identitätsmodelle für Flask-Security, keine RepairHub-Fachobjekte."""

from datetime import datetime

from flask_security import RoleMixin, UserMixin
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

roles_users = db.Table(
    "roles_users",
    db.Column("user_id", BigInteger, ForeignKey("users.id"), primary_key=True),
    db.Column("role_id", BigInteger, ForeignKey("roles.id"), primary_key=True),
)


class Role(db.Model, RoleMixin):
    # Vom Bibliotheksvertrag benötigt; keine Rollenverwaltung oder Admin-Funktion.
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))


class User(db.Model, UserMixin):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("char_length(btrim(username)) > 0", name="ck_users_username"),
        CheckConstraint("char_length(btrim(email)) > 0", name="ck_users_email"),
        CheckConstraint("char_length(password) > 0", name="ck_users_password"),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    # Funktionale Indizes sichern Eindeutigkeit unabhängig von Gross-/Kleinschreibung.
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Die Bibliothek bindet Sitzungen an diesen Wert; Passwortwechsel können ihn
    # ersetzen und damit bestehende Sitzungen ungültig machen.
    fs_uniquifier: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    roles: Mapped[list[Role]] = relationship(secondary=roles_users, lazy="selectin")


Index("uq_users_username", func.lower(User.username), unique=True)
Index("uq_users_email", func.lower(User.email), unique=True)
