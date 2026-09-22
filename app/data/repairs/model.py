"""Persistente Reparaturen, Schritte und Arbeitswerte; Kosten werden nicht gespeichert."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Repair(db.Model):
    __tablename__ = "repairs"
    __table_args__ = (
        CheckConstraint(
            "description ~ '[^[:space:]]' AND char_length(description) <= 10000",
            name="ck_repairs_description",
        ),
        CheckConstraint("status IN ('open', 'in_progress', 'completed')", name="ck_repairs_status"),
        Index("ix_repairs_device_id_id", "device_id", "id"),
        CheckConstraint("hours >= 0 AND hours <= 999999.99", name="ck_repairs_hours"),
        CheckConstraint(
            "hourly_rate >= 0 AND hourly_rate <= 999999999.99", name="ck_repairs_hourly_rate"
        ),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    device_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("devices.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="open")
    hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, server_default="0")
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(11, 2), nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RepairStep(db.Model):
    __tablename__ = "repair_steps"
    __table_args__ = (
        CheckConstraint(
            "description ~ '[^[:space:]]' AND char_length(description) <= 2000",
            name="ck_repair_steps_description",
        ),
        Index("ix_repair_steps_repair_id_id", "repair_id", "id"),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    repair_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("repairs.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
