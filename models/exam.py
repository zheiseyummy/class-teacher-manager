from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin


class Exam(TimestampMixin, SoftDeleteMixin, Base):
    """A reusable exam batch; one batch may contain multiple classes and subjects."""

    __tablename__ = "exams"
    __table_args__ = (
        Index("ix_exams_name_date", "name", "exam_date"),
        Index("ix_exams_grade_date", "grade", "exam_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    exam_date: Mapped[date | None] = mapped_column(Date)
    semester: Mapped[str | None] = mapped_column(String(80))
    grade: Mapped[str | None] = mapped_column(String(40))
    note: Mapped[str | None] = mapped_column(Text)

    scores = relationship("ExamScore", back_populates="exam")


class ExamScore(TimestampMixin, SoftDeleteMixin, Base):
    """One subject score for one student in one exam batch."""

    __tablename__ = "exam_scores"
    __table_args__ = (
        Index(
            "ux_exam_scores_exam_student_subject",
            "exam_id",
            "student_id",
            "subject",
            unique=True,
            sqlite_where=text("is_deleted = 0"),
        ),
        Index("ix_exam_scores_exam_student", "exam_id", "student_id"),
        Index("ix_exam_scores_student_subject", "student_id", "subject"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(40), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    full_score: Mapped[float | None] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text)

    exam = relationship("Exam", back_populates="scores")
    student = relationship("Student", back_populates="exam_scores")
