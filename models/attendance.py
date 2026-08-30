from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin


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
