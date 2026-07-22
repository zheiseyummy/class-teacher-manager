from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from database.connection import get_session
from models.class_group import ClassGroup
from models.moral import MoralRecord
from models.student import Student
from utils.excel_service import write_moral_export


class MoralDataError(ValueError):
    """Raised when a moral-development record cannot be saved consistently."""


class MoralController:
    """Manage local activity, award, service, and moral-point records."""

    CATEGORIES = ("集体活动", "获奖荣誉", "志愿服务", "班级服务", "社会实践", "其他")
    AWARD_LEVELS = ("", "校级", "区县级", "市级", "省级", "国家级", "其他")

    def list_classes(self) -> list[dict[str, str | int]]:
        with get_session() as session:
            classes = session.scalars(
                select(ClassGroup)
                .where(ClassGroup.is_deleted.is_(False))
                .order_by(ClassGroup.grade, ClassGroup.name)
            ).all()
            return [
                {"id": class_group.id, "name": class_group.name, "grade": class_group.grade or ""}
                for class_group in classes
            ]

    def list_students(self, class_id: int | None = None) -> list[dict[str, Any]]:
        with get_session() as session:
            stmt = (
                select(Student)
                .join(ClassGroup, Student.class_id == ClassGroup.id)
                .options(joinedload(Student.class_group))
                .where(Student.is_deleted.is_(False), ClassGroup.is_deleted.is_(False))
                .order_by(ClassGroup.grade, ClassGroup.name, Student.seat_no, Student.name)
            )
            if class_id is not None:
                stmt = stmt.where(Student.class_id == class_id)
            return [
                {
                    "id": student.id,
                    "name": student.name,
                    "student_no": student.student_no or "",
                    "class_id": student.class_id,
                    "class_name": student.class_group.name,
                }
                for student in session.scalars(stmt).all()
            ]

    def list_records(
        self,
        class_id: int | None = None,
        keyword: str = "",
        category: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        with get_session() as session:
            records = session.scalars(
                self._records_statement(class_id, keyword, category, start_date, end_date)
            ).all()
            return [self._record_dict(record) for record in records]

    def get_record(self, record_id: int) -> dict[str, Any]:
        with get_session() as session:
            record = session.scalar(
                select(MoralRecord)
                .options(joinedload(MoralRecord.student).joinedload(Student.class_group))
                .where(MoralRecord.id == record_id, MoralRecord.is_deleted.is_(False))
            )
            if record is None:
                raise MoralDataError("未找到这条德育记录。")
            return self._record_dict(record)

    def create_record(self, data: dict[str, Any]) -> int:
        values = self._record_values(data)
        with get_session() as session:
            self._active_student(session, values["student_id"])
            record = MoralRecord(**values)
            session.add(record)
            session.flush()
            return record.id

    def update_record(self, record_id: int, data: dict[str, Any]) -> None:
        values = self._record_values(data)
        with get_session() as session:
            record = session.scalar(
                select(MoralRecord).where(MoralRecord.id == record_id, MoralRecord.is_deleted.is_(False))
            )
            if record is None:
                raise MoralDataError("未找到这条德育记录。")
            self._active_student(session, values["student_id"])
            for key, value in values.items():
                setattr(record, key, value)

    def delete_record(self, record_id: int) -> None:
        with get_session() as session:
            record = session.scalar(
                select(MoralRecord).where(MoralRecord.id == record_id, MoralRecord.is_deleted.is_(False))
            )
            if record is None:
                raise MoralDataError("未找到这条德育记录。")
            record.is_deleted = True

    def get_summary(
        self,
        class_id: int | None = None,
        keyword: str = "",
        category: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, float | int]:
        records = self.list_records(class_id, keyword, category, start_date, end_date)
        return {
            "total": len(records),
            "activities": sum(record["category"] == "集体活动" for record in records),
            "awards": sum(record["category"] == "获奖荣誉" for record in records),
            "points": round(sum(float(record["points"]) for record in records), 2),
        }

    def get_student_summary(self, student_id: int) -> dict[str, float | int]:
        with get_session() as session:
            totals = session.execute(
                select(
                    func.count(MoralRecord.id),
                    func.coalesce(func.sum(MoralRecord.points), 0),
                    func.sum(MoralRecord.category == "集体活动"),
                    func.sum(MoralRecord.category == "获奖荣誉"),
                ).where(MoralRecord.student_id == student_id, MoralRecord.is_deleted.is_(False))
            ).one()
            return {
                "total": int(totals[0] or 0),
                "points": round(float(totals[1] or 0), 2),
                "activities": int(totals[2] or 0),
                "awards": int(totals[3] or 0),
            }

    def export_records_to_excel(
        self,
        file_path: str | Path,
        class_id: int | None = None,
        keyword: str = "",
        category: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Path:
        records = self.list_records(class_id, keyword, category, start_date, end_date)
        return write_moral_export(file_path, records)

    def _records_statement(
        self,
        class_id: int | None,
        keyword: str,
        category: str | None,
        start_date: date | None,
        end_date: date | None,
    ):
        stmt = (
            select(MoralRecord)
            .join(Student, MoralRecord.student_id == Student.id)
            .join(ClassGroup, Student.class_id == ClassGroup.id)
            .options(joinedload(MoralRecord.student).joinedload(Student.class_group))
            .where(
                MoralRecord.is_deleted.is_(False),
                Student.is_deleted.is_(False),
                ClassGroup.is_deleted.is_(False),
            )
            .order_by(MoralRecord.record_date.desc(), MoralRecord.id.desc())
        )
        if class_id is not None:
            stmt = stmt.where(Student.class_id == class_id)
        clean_keyword = keyword.strip()
        if clean_keyword:
            like = f"%{clean_keyword}%"
            stmt = stmt.where(
                or_(
                    Student.name.like(like),
                    Student.student_no.like(like),
                    MoralRecord.title.like(like),
                    MoralRecord.organizer.like(like),
                    MoralRecord.note.like(like),
                )
            )
        if category:
            stmt = stmt.where(MoralRecord.category == category)
        if start_date is not None:
            stmt = stmt.where(MoralRecord.record_date >= start_date)
        if end_date is not None:
            stmt = stmt.where(MoralRecord.record_date <= end_date)
        return stmt

    def _record_values(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            student_id = int(data.get("student_id"))
        except (TypeError, ValueError) as exc:
            raise MoralDataError("请选择学生。") from exc
        record_date = data.get("record_date")
        if not isinstance(record_date, date):
            raise MoralDataError("请选择有效日期。")
        category = self._choice(data.get("category"), self.CATEGORIES, "类别")
        title = self._required_text(data.get("title"), "活动或奖项名称")
        award_level = self._optional_text(data.get("award_level"))
        if award_level and award_level not in self.AWARD_LEVELS:
            raise MoralDataError("请选择有效的奖项级别。")
        return {
            "student_id": student_id,
            "record_date": record_date,
            "category": category,
            "title": title,
            "award_level": award_level,
            "organizer": self._optional_text(data.get("organizer")),
            "points": self._points_value(data.get("points")),
            "note": self._optional_text(data.get("note")),
        }

    @staticmethod
    def _active_student(session, student_id: int) -> Student:
        student = session.scalar(select(Student).where(Student.id == student_id, Student.is_deleted.is_(False)))
        if student is None:
            raise MoralDataError("请选择一名有效学生。")
        return student

    @staticmethod
    def _choice(value: Any, choices: tuple[str, ...], label: str) -> str:
        text = str(value or "").strip()
        if text not in choices:
            raise MoralDataError(f"请选择有效的{label}。")
        return text

    @staticmethod
    def _required_text(value: Any, label: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise MoralDataError(f"请填写{label}。")
        return text

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _points_value(value: Any) -> float:
        try:
            points = float(value or 0)
        except (TypeError, ValueError) as exc:
            raise MoralDataError("德育积分必须是数字。") from exc
        if not -1000 <= points <= 1000:
            raise MoralDataError("德育积分应在 -1000 到 1000 之间。")
        return round(points, 2)

    @staticmethod
    def _format_points(points: float) -> str:
        return f"{points:.2f}".rstrip("0").rstrip(".")

    @classmethod
    def _record_dict(cls, record: MoralRecord) -> dict[str, Any]:
        student = record.student
        return {
            "id": record.id,
            "student_id": record.student_id,
            "student_name": student.name,
            "student_no": student.student_no or "",
            "class_id": student.class_id,
            "class_name": student.class_group.name,
            "record_date": record.record_date,
            "record_date_display": record.record_date.isoformat(),
            "category": record.category,
            "title": record.title,
            "award_level": record.award_level or "",
            "organizer": record.organizer or "",
            "points": record.points,
            "points_display": cls._format_points(record.points),
            "note": record.note or "",
        }
