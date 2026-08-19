from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class TeacherProfile(TimestampMixin, Base):
    """Singleton local preferences for the teacher using this installation."""

    __tablename__ = "teacher_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_name: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    school_name: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    subjects_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    common_class_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    default_semester_id: Mapped[int | None] = mapped_column(Integer)
    personal_mark: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
