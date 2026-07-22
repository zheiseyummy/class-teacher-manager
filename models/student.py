from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin


class Student(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "students"
    __table_args__ = (
        Index(
            "ux_students_class_student_no",
            "class_id",
            "student_no",
            unique=True,
            sqlite_where=text("student_no IS NOT NULL AND student_no <> '' AND is_deleted = 0"),
        ),
        Index(
            "ux_students_id_card",
            "id_card",
            unique=True,
            sqlite_where=text("id_card IS NOT NULL AND id_card <> '' AND is_deleted = 0"),
        ),
        Index("ix_students_name", "name"),
        Index("ix_students_student_no", "student_no"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(20))
    student_no: Mapped[str | None] = mapped_column(String(60))
    grade: Mapped[str | None] = mapped_column(String(40))
    seat_no: Mapped[str | None] = mapped_column(String(40))
    birth_date: Mapped[date | None] = mapped_column(Date)
    id_card: Mapped[str | None] = mapped_column(String(32))
    ethnicity: Mapped[str | None] = mapped_column(String(40))
    note: Mapped[str | None] = mapped_column(Text)

    class_group = relationship("ClassGroup", back_populates="students")
    guardians = relationship("Guardian", back_populates="student", cascade="all, delete-orphan")
    exam_scores = relationship("ExamScore", back_populates="student")
    moral_points = relationship("MoralPoint", back_populates="student")
    moral_records = relationship("MoralRecord", back_populates="student")
    leave_records = relationship("LeaveRecord", back_populates="student")
    discipline_records = relationship("DisciplineRecord", back_populates="student")
    counseling_records = relationship("CounselingRecord", back_populates="student")
    home_visit_records = relationship("HomeVisitRecord", back_populates="student")
    quality_records = relationship("QualityRecord", back_populates="student")
    quality_roster_entries = relationship("QualityRosterEntry", back_populates="student")
    quality_final_results = relationship("QualityFinalResult", back_populates="student")
