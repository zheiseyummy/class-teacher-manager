from __future__ import annotations

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin


class ClassGroup(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "classes"
    __table_args__ = (
        UniqueConstraint("name", "school_year", name="uq_classes_name_school_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    grade: Mapped[str | None] = mapped_column(String(40))
    school_year: Mapped[str | None] = mapped_column(String(40))
    head_teacher: Mapped[str | None] = mapped_column(String(80))
    color: Mapped[str | None] = mapped_column(String(16))
    note: Mapped[str | None] = mapped_column(Text)

    students = relationship("Student", back_populates="class_group")
    course_schedules = relationship("CourseSchedule", back_populates="class_group")
    calendar_events = relationship("CalendarEvent", back_populates="class_group")

    def display_name(self) -> str:
        """Return the class name exactly as entered by the user."""
        return self.name
