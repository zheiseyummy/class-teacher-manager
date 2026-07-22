from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin


class MoralPoint(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "moral_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    event_date: Mapped[date | None] = mapped_column(Date)
    category: Mapped[str | None] = mapped_column(String(80))
    points: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)

    student = relationship("Student", back_populates="moral_points")


class LeaveRecord(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "leave_records"
    __table_args__ = (
        Index("ix_leave_records_student_start", "student_id", "start_time"),
        Index("ix_leave_records_start_time", "start_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    leave_type: Mapped[str | None] = mapped_column(String(80))
    start_time: Mapped[datetime | None] = mapped_column(DateTime)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    reason: Mapped[str | None] = mapped_column(Text)
    approval_status: Mapped[str | None] = mapped_column(String(80))
    note: Mapped[str | None] = mapped_column(Text)

    student = relationship("Student", back_populates="leave_records")


class DisciplineRecord(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "discipline_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    event_date: Mapped[date | None] = mapped_column(Date)
    category: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    handling_result: Mapped[str | None] = mapped_column(Text)

    student = relationship("Student", back_populates="discipline_records")


class CounselingRecord(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "counseling_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    talk_date: Mapped[date | None] = mapped_column(Date)
    topic: Mapped[str | None] = mapped_column(String(160))
    content: Mapped[str | None] = mapped_column(Text)
    follow_up: Mapped[str | None] = mapped_column(Text)

    student = relationship("Student", back_populates="counseling_records")


class HomeVisitRecord(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "home_visit_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    visit_date: Mapped[date | None] = mapped_column(Date)
    visit_method: Mapped[str | None] = mapped_column(String(80))
    content: Mapped[str | None] = mapped_column(Text)
    feedback: Mapped[str | None] = mapped_column(Text)

    student = relationship("Student", back_populates="home_visit_records")


class ClassCadre(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "class_cadres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    position: Mapped[str] = mapped_column(String(80), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text)

    class_group = relationship("ClassGroup", back_populates="cadres")
    student = relationship("Student")


class CommentTemplate(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "comment_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    tags: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, nullable=False)
