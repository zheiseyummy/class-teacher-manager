from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin


class TeachingGroup(TimestampMixin, SoftDeleteMixin, Base):
    """An independent teaching group used only by the timetable module."""

    __tablename__ = "teaching_groups"
    __table_args__ = (
        Index(
            "ux_teaching_groups_name_active",
            "name",
            unique=True,
            sqlite_where=text("is_deleted = 0"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    color: Mapped[str | None] = mapped_column(String(16))
    linked_class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text)

    linked_class_group = relationship("ClassGroup", foreign_keys=[linked_class_id])
    courses = relationship("TeachingCourse", back_populates="teaching_group")


class AcademicSemester(TimestampMixin, SoftDeleteMixin, Base):
    """A date-bounded term that owns its own period configuration."""

    __tablename__ = "academic_semesters"
    __table_args__ = (
        Index(
            "ux_academic_semesters_name_active",
            "name",
            unique=True,
            sqlite_where=text("is_deleted = 0"),
        ),
        Index("ix_academic_semesters_date_range", "start_date", "end_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    periods = relationship("SchedulePeriod", back_populates="semester")
    courses = relationship("TeachingCourse", back_populates="semester")


class SchedulePeriod(TimestampMixin, SoftDeleteMixin, Base):
    """One configurable teaching period in a semester."""

    __tablename__ = "schedule_periods"
    __table_args__ = (
        Index(
            "ux_schedule_periods_semester_order_active",
            "semester_id",
            "sort_order",
            unique=True,
            sqlite_where=text("is_deleted = 0"),
        ),
        Index("ix_schedule_periods_semester", "semester_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    semester_id: Mapped[int] = mapped_column(ForeignKey("academic_semesters.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    start_time: Mapped[str | None] = mapped_column(String(5))
    end_time: Mapped[str | None] = mapped_column(String(5))
    note: Mapped[str | None] = mapped_column(Text)

    semester = relationship("AcademicSemester", back_populates="periods")
    courses = relationship("TeachingCourse", back_populates="period")


class TeachingCourse(TimestampMixin, SoftDeleteMixin, Base):
    """A recurring course for one teaching group, semester, weekday and period."""

    __tablename__ = "teaching_courses"
    __table_args__ = (
        Index(
            "ux_teaching_courses_group_term_slot_active",
            "teaching_group_id",
            "semester_id",
            "weekday",
            "period_id",
            unique=True,
            sqlite_where=text("is_deleted = 0"),
        ),
        Index("ix_teaching_courses_semester_group", "semester_id", "teaching_group_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teaching_group_id: Mapped[int] = mapped_column(ForeignKey("teaching_groups.id"), nullable=False)
    semester_id: Mapped[int] = mapped_column(ForeignKey("academic_semesters.id"), nullable=False)
    period_id: Mapped[int] = mapped_column(ForeignKey("schedule_periods.id"), nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    subject: Mapped[str] = mapped_column(String(80), nullable=False)
    teacher: Mapped[str | None] = mapped_column(String(80))
    location: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)

    teaching_group = relationship("TeachingGroup", back_populates="courses")
    semester = relationship("AcademicSemester", back_populates="courses")
    period = relationship("SchedulePeriod", back_populates="courses")
