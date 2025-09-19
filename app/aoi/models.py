"""Database models for AOI inspection forms."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


@dataclass
class AoiProblemCode(db.Model):
    """Authoritative list of AOI problem codes."""

    __tablename__ = "aoi_problem_codes"

    code: int = mapped_column(db.Integer, primary_key=True)
    name: str = mapped_column(db.String(120), nullable=False, unique=True)
    part_type: str | None = mapped_column(db.String(120), nullable=True)

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "code": self.code,
            "name": self.name,
            "part_type": self.part_type,
        }


@dataclass
class AoiForm(db.Model):
    """Master record of an AOI inspection form."""

    __tablename__ = "aoi_forms"

    id: str = mapped_column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    date: date = mapped_column(db.Date, nullable=False)
    type: str = mapped_column(db.String(8), nullable=False)
    form_number: str = mapped_column(db.String(32), nullable=False, default="Form-114")
    form_rev: str = mapped_column(db.String(64), nullable=False, default="Rev. 17 (9/9/2025)")
    customer: str | None = mapped_column(db.String(255), nullable=True)
    assembly: str | None = mapped_column(db.String(255), nullable=True)
    job_number: str | None = mapped_column(db.String(255), nullable=True)
    revision: str | None = mapped_column(db.String(255), nullable=True)
    panels_count: int | None = mapped_column(db.Integer, nullable=True)
    boards_count: int | None = mapped_column(db.Integer, nullable=True)
    inspector: str | None = mapped_column(db.String(255), nullable=True)
    qty_inspected: int = mapped_column(db.Integer, nullable=False, default=0)
    qty_rejected: int = mapped_column(db.Integer, nullable=False, default=0)
    qty_accepted: int = mapped_column(db.Integer, nullable=False, default=0)
    comments: str | None = mapped_column(db.Text, nullable=True)
    status: str = mapped_column(db.String(16), nullable=False, default="submitted")
    created_at: datetime = mapped_column(
        db.DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: datetime = mapped_column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    rejections: Mapped[list["AoiRejection"]] = relationship(
        "AoiRejection", cascade="all, delete-orphan", back_populates="form"
    )
    board_data: Mapped[list["AoiBoardData"]] = relationship(
        "AoiBoardData", cascade="all, delete-orphan", back_populates="form"
    )

    __table_args__ = (
        CheckConstraint("qty_inspected >= 0", name="aoi_qty_inspected_non_negative"),
        CheckConstraint("qty_rejected >= 0", name="aoi_qty_rejected_non_negative"),
        CheckConstraint("qty_accepted >= 0", name="aoi_qty_accepted_non_negative"),
        CheckConstraint("status in ('draft','submitted')", name="aoi_status_valid"),
        CheckConstraint("type in ('SMT','TH')", name="aoi_type_valid"),
    )


@dataclass
class AoiRejection(db.Model):
    """Line items for rejection reasons."""

    __tablename__ = "aoi_rejections"

    id: str = mapped_column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    form_id: str = mapped_column(
        db.String(36),
        ForeignKey("aoi_forms.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity: int = mapped_column(db.Integer, nullable=False)
    problem_code: int = mapped_column(
        db.Integer, ForeignKey("aoi_problem_codes.code"), nullable=False
    )
    reference_designators: str | None = mapped_column(db.Text, nullable=True)

    form: Mapped[AoiForm] = relationship("AoiForm", back_populates="rejections")
    problem: Mapped[AoiProblemCode] = relationship("AoiProblemCode")

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="aoi_rejection_quantity_positive"),
    )


@dataclass
class AoiBoardData(db.Model):
    """Optional board-level inspection details."""

    __tablename__ = "aoi_board_data"

    id: str = mapped_column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    form_id: str = mapped_column(
        db.String(36),
        ForeignKey("aoi_forms.id", ondelete="CASCADE"),
        nullable=False,
    )
    board_id: str | None = mapped_column(db.String(255), nullable=True)
    reference_designators: str | None = mapped_column(db.Text, nullable=True)
    problem_code: int | None = mapped_column(
        db.Integer, ForeignKey("aoi_problem_codes.code"), nullable=True
    )
    comments: str | None = mapped_column(db.Text, nullable=True)

    form: Mapped[AoiForm] = relationship("AoiForm", back_populates="board_data")
    problem: Mapped[AoiProblemCode] = relationship("AoiProblemCode")
