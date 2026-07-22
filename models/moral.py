from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin


class MoralRecord(TimestampMixin, SoftDeleteMixin, Base):
    """One positive moral-development activity, honor, or service record."""

    __tablename__ = "moral_records"
    __table_args__ = (
        Index("ix_moral_records_student_date", "student_id", "record_date"),
        Index("ix_moral_records_category_date", "category", "record_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    award_level: Mapped[str | None] = mapped_column(String(80))
    organizer: Mapped[str | None] = mapped_column(String(180))
    points: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    student = relationship("Student", back_populates="moral_records")
