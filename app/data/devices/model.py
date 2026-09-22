"""Persistenz folgt den Gerätewerten und sichert ihre Grenzen zusätzlich ab."""

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Device(db.Model):
    __tablename__ = "devices"
    __table_args__ = (
        CheckConstraint("name ~ '[^[:space:]]'", name="ck_devices_name"),
        CheckConstraint("manufacturer ~ '[^[:space:]]'", name="ck_devices_manufacturer"),
        CheckConstraint("model ~ '[^[:space:]]'", name="ck_devices_model"),
        Index("ix_devices_owner_id_id", "owner_id", "id"),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(120), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
