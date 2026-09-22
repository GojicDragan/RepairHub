"""Persistente Positionen; Eigentum wird ausschliesslich über Fall und Gerät abgeleitet."""

from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class PartItem(db.Model):
    __tablename__ = "part_items"
    __table_args__ = (
        CheckConstraint("name ~ '[^[:space:]]'", name="ck_part_items_name"),
        CheckConstraint(
            "unit_price >= 0 AND unit_price <= 999999999.99", name="ck_part_items_price"
        ),
        CheckConstraint("quantity > 0", name="ck_part_items_quantity"),
        Index("ix_part_items_repair_id_id", "repair_id", "id"),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    repair_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("repairs.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(11, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
