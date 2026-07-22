from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin


class Guardian(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "guardians"
    __table_args__ = (
        Index(
            "ux_guardians_student_phone_name",
            "student_id",
            "phone",
            "name",
            unique=True,
            sqlite_where=text("phone IS NOT NULL AND phone <> '' AND is_deleted = 0"),
        ),
        Index("ix_guardians_phone", "phone"),
        Index("ix_guardians_student_id", "student_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    relationship: Mapped[str | None] = mapped_column(String(40))
    phone: Mapped[str | None] = mapped_column(String(40))
    wechat: Mapped[str | None] = mapped_column(String(80))
    workplace: Mapped[str | None] = mapped_column(String(160))
    address: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    student = orm_relationship("Student", back_populates="guardians")
