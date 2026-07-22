from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin


class CourseSchedule(TimestampMixin, SoftDeleteMixin, Base):
    """A recurring course slot for one class and weekday."""

    __tablename__ = "course_schedules"
    __table_args__ = (
        Index(
            "ux_course_schedules_class_weekday_period",
            "class_id",
            "weekday",
            "period",
            unique=True,
            sqlite_where=text("is_deleted = 0"),
        ),
        Index("ix_course_schedules_class_weekday", "class_id", "weekday"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    period: Mapped[int] = mapped_column(Integer, nullable=False)
    subject: Mapped[str] = mapped_column(String(80), nullable=False)
    teacher: Mapped[str | None] = mapped_column(String(80))
    location: Mapped[str | None] = mapped_column(String(120))
    start_time: Mapped[str | None] = mapped_column(String(5))
    end_time: Mapped[str | None] = mapped_column(String(5))
    note: Mapped[str | None] = mapped_column(Text)

    class_group = relationship("ClassGroup", back_populates="course_schedules")


class CalendarEvent(TimestampMixin, SoftDeleteMixin, Base):
    """A dated global or class-specific calendar item."""

    __tablename__ = "calendar_events"
    __table_args__ = (
        Index("ix_calendar_events_date", "event_date"),
        Index("ix_calendar_events_class_date", "class_id", "event_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"), nullable=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    start_time: Mapped[str | None] = mapped_column(String(5))
    end_time: Mapped[str | None] = mapped_column(String(5))
    note: Mapped[str | None] = mapped_column(Text)

    class_group = relationship("ClassGroup", back_populates="calendar_events")
