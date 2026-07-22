from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin


class QualityDimension(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "quality_dimensions"
    __table_args__ = (Index("ux_quality_dimensions_sort_order", "sort_order", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class QualityRecord(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "quality_records"
    __table_args__ = (
        Index(
            "ux_quality_records_student_semester_dimension",
            "student_id",
            "semester",
            "dimension",
            unique=True,
            sqlite_where=text("is_deleted = 0"),
        ),
        Index("ix_quality_records_student_semester", "student_id", "semester"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    semester: Mapped[str] = mapped_column(String(40), nullable=False)
    dimension: Mapped[str] = mapped_column(String(80), nullable=False)
    level_or_score: Mapped[str] = mapped_column(String(4), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)

    student = relationship("Student", back_populates="quality_records")


class QualityRosterEntry(TimestampMixin, SoftDeleteMixin, Base):
    """Records that a student actually appeared in a semester source roster."""

    __tablename__ = "quality_roster_entries"
    __table_args__ = (
        Index(
            "ux_quality_roster_student_semester",
            "student_id",
            "semester",
            unique=True,
            sqlite_where=text("is_deleted = 0"),
        ),
        Index("ix_quality_roster_semester", "semester"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    semester: Mapped[str] = mapped_column(String(40), nullable=False)

    student = relationship("Student", back_populates="quality_roster_entries")


class QualityFinalization(TimestampMixin, Base):
    """Stores the review and lock state for one class's final assessment."""

    __tablename__ = "quality_finalizations"
    __table_args__ = (UniqueConstraint("class_id", name="uq_quality_finalizations_class"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime)


class QualityFinalResult(TimestampMixin, Base):
    """Snapshot of one student's final score, rank, and reviewed level in a dimension."""

    __tablename__ = "quality_final_results"
    __table_args__ = (
        UniqueConstraint("student_id", "dimension", name="uq_quality_final_results_student_dimension"),
        Index("ix_quality_final_results_class_dimension", "class_id", "dimension"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    dimension: Mapped[str] = mapped_column(String(80), nullable=False)
    cumulative_score: Mapped[float] = mapped_column(Float, nullable=False)
    class_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    automatic_level: Mapped[str] = mapped_column(String(1), nullable=False)
    final_level: Mapped[str] = mapped_column(String(1), nullable=False)
    is_manually_adjusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    available_terms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    contains_na: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    student = relationship("Student", back_populates="quality_final_results")
