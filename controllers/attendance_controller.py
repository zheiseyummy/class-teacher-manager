from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload

from database.connection import get_session
from models.class_group import ClassGroup
from models.attendance import LeaveRecord
from models.student import Student
from utils.excel_service import write_attendance_export


class AttendanceDataError(ValueError):
    """Raised when a leave or attendance record cannot be saved safely."""


class AttendanceController:
    """Manage leave, tardiness, early-leave, and absence records locally."""

    RECORD_TYPES = ("病假", "事假", "迟到", "早退", "缺勤", "其他")
    LEAVE_TYPES = frozenset(("病假", "事假", "其他"))
    APPROVAL_STATUSES = ("已登记", "待审批", "已批准", "未批准")

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

    def list_students(self, class_id: int | None = None, keyword: str = "") -> list[dict[str, Any]]:
        keyword = keyword.strip()
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
            if keyword:
                like = f"%{keyword}%"
                stmt = stmt.where(or_(Student.name.like(like), Student.student_no.like(like)))
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
        record_type: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        with get_session() as session:
            records = session.scalars(
                self._records_statement(class_id, keyword, record_type, start_date, end_date)
            ).all()
            return [self._record_dict(record) for record in records]

    def get_record(self, record_id: int) -> dict[str, Any]:
        with get_session() as session:
            record = session.scalar(
                select(LeaveRecord)
                .options(joinedload(LeaveRecord.student).joinedload(Student.class_group))
                .where(LeaveRecord.id == record_id, LeaveRecord.is_deleted.is_(False))
            )
            if record is None:
                raise AttendanceDataError("未找到这条请假或考勤记录。")
            return self._record_dict(record)

    def create_record(self, data: dict[str, Any]) -> int:
        values = self._record_values(data)
        with get_session() as session:
            self._active_student(session, values["student_id"])
            record = LeaveRecord(**values)
            session.add(record)
            session.flush()
            return record.id

    def update_record(self, record_id: int, data: dict[str, Any]) -> None:
        values = self._record_values(data)
        with get_session() as session:
            record = session.scalar(
                select(LeaveRecord).where(LeaveRecord.id == record_id, LeaveRecord.is_deleted.is_(False))
            )
            if record is None:
                raise AttendanceDataError("未找到这条请假或考勤记录。")
            self._active_student(session, values["student_id"])
            for key, value in values.items():
                setattr(record, key, value)

    def delete_record(self, record_id: int) -> None:
        with get_session() as session:
            record = session.scalar(
                select(LeaveRecord).where(LeaveRecord.id == record_id, LeaveRecord.is_deleted.is_(False))
            )
            if record is None:
                raise AttendanceDataError("未找到这条请假或考勤记录。")
            record.is_deleted = True

    def get_summary(
        self,
        class_id: int | None = None,
        keyword: str = "",
        record_type: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, int]:
        records = self.list_records(class_id, keyword, record_type, start_date, end_date)
        return {
            "total": len(records),
            "leave": sum(record["record_type"] in self.LEAVE_TYPES for record in records),
            "late": sum(record["record_type"] == "迟到" for record in records),
            "early_leave": sum(record["record_type"] == "早退" for record in records),
            "absence": sum(record["record_type"] == "缺勤" for record in records),
        }

    def export_records_to_excel(
        self,
        file_path: str | Path,
        class_id: int | None = None,
        keyword: str = "",
        record_type: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Path:
        records = self.list_records(class_id, keyword, record_type, start_date, end_date)
        return write_attendance_export(file_path, records)

    def _records_statement(
        self,
        class_id: int | None,
        keyword: str,
        record_type: str | None,
        start_date: date | None,
        end_date: date | None,
    ):
        stmt = (
            select(LeaveRecord)
            .join(Student, LeaveRecord.student_id == Student.id)
            .join(ClassGroup, Student.class_id == ClassGroup.id)
            .options(joinedload(LeaveRecord.student).joinedload(Student.class_group))
            .where(
                LeaveRecord.is_deleted.is_(False),
                Student.is_deleted.is_(False),
                ClassGroup.is_deleted.is_(False),
            )
            .order_by(LeaveRecord.start_time.desc(), LeaveRecord.id.desc())
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
                    LeaveRecord.reason.like(like),
                    LeaveRecord.note.like(like),
                )
            )
        if record_type:
            stmt = stmt.where(LeaveRecord.leave_type == record_type)
        if start_date is not None:
            stmt = stmt.where(LeaveRecord.start_time >= datetime.combine(start_date, time.min))
        if end_date is not None:
            stmt = stmt.where(LeaveRecord.start_time <= datetime.combine(end_date, time.max))
        return stmt

    def _record_values(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            student_id = int(data.get("student_id"))
        except (TypeError, ValueError) as exc:
            raise AttendanceDataError("请选择学生。") from exc

        record_type = self._choice(data.get("record_type"), self.RECORD_TYPES, "记录类型")
        status = self._choice(
            data.get("approval_status") or self.APPROVAL_STATUSES[0],
            self.APPROVAL_STATUSES,
            "处理状态",
        )
        start_time = self._datetime_value(data.get("start_time"), "开始时间")
        end_time = self._datetime_value(data.get("end_time"), "结束时间")
        if end_time < start_time:
            raise AttendanceDataError("结束时间不能早于开始时间。")
        return {
            "student_id": student_id,
            "leave_type": record_type,
            "start_time": start_time,
            "end_time": end_time,
            "reason": self._optional_text(data.get("reason")),
            "approval_status": status,
            "note": self._optional_text(data.get("note")),
        }

    @staticmethod
    def _active_student(session, student_id: int) -> Student:
        student = session.scalar(select(Student).where(Student.id == student_id, Student.is_deleted.is_(False)))
        if student is None:
            raise AttendanceDataError("请选择一名有效学生。")
        return student

    @staticmethod
    def _datetime_value(value: Any, label: str) -> datetime:
        if not isinstance(value, datetime):
            raise AttendanceDataError(f"请填写有效的{label}。")
        return value.replace(second=0, microsecond=0)

    @staticmethod
    def _choice(value: Any, choices: tuple[str, ...], label: str) -> str:
        text = str(value or "").strip()
        if text not in choices:
            raise AttendanceDataError(f"请选择有效的{label}。")
        return text

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _duration_minutes(start_time: datetime | None, end_time: datetime | None) -> int:
        if start_time is None or end_time is None or end_time <= start_time:
            return 0
        return max(0, round((end_time - start_time).total_seconds() / 60))

    @classmethod
    def _duration_display(cls, start_time: datetime | None, end_time: datetime | None) -> str:
        minutes = cls._duration_minutes(start_time, end_time)
        if minutes == 0:
            return "—"
        days, remaining = divmod(minutes, 24 * 60)
        hours, remaining = divmod(remaining, 60)
        parts: list[str] = []
        if days:
            parts.append(f"{days}天")
        if hours:
            parts.append(f"{hours}小时")
        if remaining:
            parts.append(f"{remaining}分钟")
        return "".join(parts)

    @classmethod
    def _record_dict(cls, record: LeaveRecord) -> dict[str, Any]:
        student = record.student
        start_time = record.start_time
        end_time = record.end_time
        return {
            "id": record.id,
            "student_id": record.student_id,
            "student_name": student.name,
            "student_no": student.student_no or "",
            "class_id": student.class_id,
            "class_name": student.class_group.name,
            "record_type": record.leave_type or "其他",
            "start_time": start_time,
            "end_time": end_time,
            "start_time_display": start_time.strftime("%Y-%m-%d %H:%M") if start_time else "",
            "end_time_display": end_time.strftime("%Y-%m-%d %H:%M") if end_time else "",
            "reason": record.reason or "",
            "approval_status": record.approval_status or "已登记",
            "note": record.note or "",
            "duration_minutes": cls._duration_minutes(start_time, end_time),
            "duration_display": cls._duration_display(start_time, end_time),
        }
