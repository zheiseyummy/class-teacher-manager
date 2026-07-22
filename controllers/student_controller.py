from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from database.connection import get_session
from models.class_group import ClassGroup
from models.guardian import Guardian
from models.import_record import ImportBatch, ImportError as ImportRowError
from models.student import Student
from utils.excel_service import (
    ExcelImportError,
    ParsedStudentRow,
    read_student_import_file,
    write_guardian_directory,
    write_student_export,
)


class StudentDataError(ValueError):
    """Raised when data entered in the student center is incomplete or duplicated."""


class StudentDuplicateError(StudentDataError):
    """Raised when an import row matches an active student record."""


@dataclass(frozen=True)
class ImportIssue:
    row_number: int
    field_name: str
    raw_value: str
    message: str
    skipped: bool = False


@dataclass(frozen=True)
class StudentImportResult:
    batch_id: int
    file_name: str
    total_rows: int
    success_rows: int
    failed_rows: int
    skipped_rows: int
    issues: list[ImportIssue]


class StudentController:
    """Business operations for classes, students, and guardians."""

    def list_classes(self) -> list[dict[str, Any]]:
        with get_session() as session:
            classes = session.scalars(
                select(ClassGroup)
                .where(ClassGroup.is_deleted.is_(False))
                .order_by(ClassGroup.grade, ClassGroup.name)
            ).all()
            student_counts = dict(
                session.execute(
                    select(Student.class_id, func.count(Student.id))
                    .where(Student.is_deleted.is_(False))
                    .group_by(Student.class_id)
                ).all()
            )
            return [
                {
                    "id": class_group.id,
                    "name": class_group.name,
                    "grade": class_group.grade or "",
                    "school_year": class_group.school_year or "",
                    "head_teacher": class_group.head_teacher or "",
                    "note": class_group.note or "",
                    "student_count": student_counts.get(class_group.id, 0),
                }
                for class_group in classes
            ]

    def create_class(self, data: dict[str, Any]) -> int:
        values = self._class_values(data)
        with get_session() as session:
            class_group = ClassGroup(**values)
            session.add(class_group)
            session.flush()
            return class_group.id

    def update_class(self, class_id: int, data: dict[str, Any]) -> None:
        values = self._class_values(data)
        with get_session() as session:
            class_group = self._active_class(session, class_id)
            for key, value in values.items():
                setattr(class_group, key, value)

    def delete_class(self, class_id: int) -> None:
        with get_session() as session:
            class_group = self._active_class(session, class_id)
            student_count = session.scalar(
                select(func.count(Student.id)).where(
                    Student.class_id == class_id,
                    Student.is_deleted.is_(False),
                )
            )
            if student_count:
                raise StudentDataError("该班级仍有学生档案，无法删除。请先转移或删除学生。")
            class_group.is_deleted = True

    def search_students(self, keyword: str = "", class_id: int | None = None) -> list[dict[str, str]]:
        keyword = (keyword or "").strip()
        with get_session() as session:
            stmt = (
                select(Student, ClassGroup)
                .join(ClassGroup, Student.class_id == ClassGroup.id)
                .where(Student.is_deleted.is_(False), ClassGroup.is_deleted.is_(False))
                .options(selectinload(Student.guardians))
                .order_by(ClassGroup.grade, ClassGroup.name, Student.seat_no, Student.name)
            )
            if class_id:
                stmt = stmt.where(Student.class_id == class_id)
            if keyword:
                like = f"%{keyword}%"
                guardian_phone_match = exists(
                    select(Guardian.id).where(
                        Guardian.student_id == Student.id,
                        Guardian.is_deleted.is_(False),
                        Guardian.phone.like(like),
                    )
                )
                stmt = stmt.where(
                    or_(
                        Student.name.like(like),
                        Student.student_no.like(like),
                        guardian_phone_match,
                    )
                )

            rows = session.execute(stmt).all()
            return [self._student_row(student, class_group) for student, class_group in rows]

    def count_classes(self) -> int:
        with get_session() as session:
            stmt = select(func.count()).select_from(ClassGroup).where(ClassGroup.is_deleted.is_(False))
            return int(session.execute(stmt).scalar_one())

    def count_students(self, class_id: int | None = None) -> int:
        with get_session() as session:
            stmt = select(func.count()).select_from(Student).where(Student.is_deleted.is_(False))
            if class_id:
                stmt = stmt.where(Student.class_id == class_id)
            return int(session.execute(stmt).scalar_one())

    def get_student_detail(self, student_id: int) -> dict[str, Any]:
        with get_session() as session:
            student = session.scalar(
                select(Student)
                .options(joinedload(Student.class_group), selectinload(Student.guardians))
                .where(Student.id == student_id, Student.is_deleted.is_(False))
            )
            if student is None:
                raise StudentDataError("未找到该学生档案。")
            return {
                "id": student.id,
                "class_id": student.class_id,
                "class_name": student.class_group.name,
                "class_grade": student.class_group.grade or "",
                "name": student.name,
                "gender": student.gender or "",
                "student_no": student.student_no or "",
                "grade": student.grade or "",
                "display_grade": student.grade or student.class_group.grade or "",
                "seat_no": student.seat_no or "",
                "birth_date": student.birth_date,
                "id_card": student.id_card or "",
                "ethnicity": student.ethnicity or "",
                "note": student.note or "",
                "guardians": [
                    {
                        "id": guardian.id,
                        "name": guardian.name,
                        "relationship": guardian.relationship or "",
                        "phone": guardian.phone or "",
                        "wechat": guardian.wechat or "",
                        "workplace": guardian.workplace or "",
                        "address": guardian.address or "",
                        "note": guardian.note or "",
                        "is_primary": guardian.is_primary,
                    }
                    for guardian in student.guardians
                    if not guardian.is_deleted
                ],
            }

    def create_student(self, data: dict[str, Any], guardians: list[dict[str, Any]]) -> int:
        values = self._student_values(data)
        guardian_values = self._guardian_values(guardians)
        with get_session() as session:
            self._active_class(session, values["class_id"])
            self._ensure_student_is_unique(session, values)
            student = Student(**values)
            session.add(student)
            session.flush()
            self._sync_guardians(session, student, guardian_values)
            return student.id

    def update_student(self, student_id: int, data: dict[str, Any], guardians: list[dict[str, Any]]) -> None:
        values = self._student_values(data)
        guardian_values = self._guardian_values(guardians)
        with get_session() as session:
            student = session.scalar(
                select(Student)
                .options(selectinload(Student.guardians))
                .where(Student.id == student_id, Student.is_deleted.is_(False))
            )
            if student is None:
                raise StudentDataError("未找到该学生档案。")
            self._active_class(session, values["class_id"])
            self._ensure_student_is_unique(session, values, student_id)
            for key, value in values.items():
                setattr(student, key, value)
            self._sync_guardians(session, student, guardian_values)

    def delete_student(self, student_id: int) -> None:
        with get_session() as session:
            student = session.scalar(
                select(Student)
                .options(selectinload(Student.guardians))
                .where(Student.id == student_id, Student.is_deleted.is_(False))
            )
            if student is None:
                raise StudentDataError("未找到该学生档案。")
            student.is_deleted = True
            for guardian in student.guardians:
                guardian.is_deleted = True

    def import_students_from_excel(self, file_path: str | Path) -> StudentImportResult:
        try:
            parsed_rows = read_student_import_file(file_path)
        except ExcelImportError as exc:
            raise StudentDataError(str(exc)) from exc

        source_path = Path(file_path)
        with get_session() as session:
            batch = ImportBatch(file_name=source_path.name, total_rows=len(parsed_rows))
            session.add(batch)
            session.flush()
            batch_id = batch.id

        success_rows = 0
        failed_rows = 0
        skipped_rows = 0
        issues: list[ImportIssue] = []
        for row in parsed_rows:
            try:
                self._validate_import_row(row)
                class_id = self._resolve_import_class(row.student.get("class_name", ""), row.student.get("grade", ""))
                student_data = dict(row.student)
                student_data["class_id"] = class_id
                student_data.pop("class_name", None)
                self.create_student(student_data, [row.guardian])
                success_rows += 1
            except StudentDuplicateError as exc:
                skipped_rows += 1
                issues.append(self._import_issue(row, str(exc), skipped=True))
            except StudentDataError as exc:
                failed_rows += 1
                issues.append(self._import_issue(row, str(exc)))
            except Exception:
                failed_rows += 1
                issues.append(self._import_issue(row, "该行数据保存失败，请检查字段内容。"))

        with get_session() as session:
            batch = session.get(ImportBatch, batch_id)
            if batch is not None:
                batch.success_rows = success_rows
                batch.failed_rows = failed_rows
                batch.skipped_rows = skipped_rows
                batch.message = f"成功 {success_rows} 行，失败 {failed_rows} 行，跳过 {skipped_rows} 行"
            for issue in issues:
                session.add(
                    ImportRowError(
                        batch_id=batch_id,
                        row_number=issue.row_number,
                        field_name=issue.field_name,
                        raw_value=issue.raw_value,
                        error_message=issue.message,
                    )
                )
        return StudentImportResult(
            batch_id=batch_id,
            file_name=source_path.name,
            total_rows=len(parsed_rows),
            success_rows=success_rows,
            failed_rows=failed_rows,
            skipped_rows=skipped_rows,
            issues=issues,
        )

    def export_students_to_excel(self, file_path: str | Path, class_id: int | None = None) -> Path:
        records = self._export_student_records(class_id)
        title = "班级学生信息" if class_id else "全部学生信息"
        return write_student_export(file_path, records, title)

    def export_guardian_directory_to_excel(self, file_path: str | Path, class_id: int | None = None) -> Path:
        return write_guardian_directory(file_path, self._export_student_records(class_id))

    def _active_class(self, session, class_id: int) -> ClassGroup:
        class_group = session.scalar(
            select(ClassGroup).where(ClassGroup.id == class_id, ClassGroup.is_deleted.is_(False))
        )
        if class_group is None:
            raise StudentDataError("请选择一个有效班级。")
        return class_group

    def _resolve_import_class(self, class_name: Any, grade: Any) -> int:
        normalized_name = self._required_text(class_name, "班级")
        with get_session() as session:
            class_group = session.scalar(
                select(ClassGroup)
                .where(ClassGroup.name == normalized_name, ClassGroup.is_deleted.is_(False))
                .order_by(ClassGroup.id.desc())
            )
            if class_group is None:
                class_group = ClassGroup(name=normalized_name, grade=self._optional_text(grade))
                session.add(class_group)
                session.flush()
            return class_group.id

    def _validate_import_row(self, row: ParsedStudentRow) -> None:
        self._required_text(row.student.get("name"), "学生姓名")
        self._required_text(row.student.get("class_name"), "班级")
        birth_date = row.student.get("birth_date")
        if birth_date is not None and not isinstance(birth_date, date):
            raise StudentDataError("出生日期格式不正确，请使用 YYYY-MM-DD。")
        self._guardian_values([row.guardian])

    def _class_values(self, data: dict[str, Any]) -> dict[str, str | None]:
        name = self._required_text(data.get("name"), "班级名称")
        return {
            "name": name,
            "grade": self._optional_text(data.get("grade")),
            "school_year": self._optional_text(data.get("school_year")),
            "head_teacher": self._optional_text(data.get("head_teacher")),
            "note": self._optional_text(data.get("note")),
        }

    def _student_values(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            class_id = int(data.get("class_id"))
        except (TypeError, ValueError) as exc:
            raise StudentDataError("请选择学生所属班级。") from exc
        birth_date = data.get("birth_date")
        if birth_date is not None and not isinstance(birth_date, date):
            raise StudentDataError("出生日期格式不正确。")
        return {
            "class_id": class_id,
            "name": self._required_text(data.get("name"), "学生姓名"),
            "gender": self._optional_text(data.get("gender")),
            "student_no": self._optional_text(data.get("student_no")),
            "grade": self._optional_text(data.get("grade")),
            "seat_no": self._optional_text(data.get("seat_no")),
            "birth_date": birth_date,
            "id_card": self._optional_text(data.get("id_card")),
            "ethnicity": self._optional_text(data.get("ethnicity")),
            "note": self._optional_text(data.get("note")),
        }

    def _guardian_values(self, guardians: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        seen_contacts: set[tuple[str, str]] = set()
        for raw in guardians:
            name = self._optional_text(raw.get("name"))
            phone = self._optional_text(raw.get("phone"))
            meaningful = any(self._optional_text(raw.get(key)) for key in ("relationship", "wechat", "workplace", "address", "note"))
            if not name and not phone and not meaningful:
                continue
            if not name:
                raise StudentDataError("每位联系人都需要填写姓名。")
            pair = (name, phone or "")
            if phone and pair in seen_contacts:
                raise StudentDataError("同一学生不能重复添加相同姓名和电话的联系人。")
            seen_contacts.add(pair)
            normalized.append(
                {
                    "id": raw.get("id"),
                    "name": name,
                    "relationship": self._optional_text(raw.get("relationship")),
                    "phone": phone,
                    "wechat": self._optional_text(raw.get("wechat")),
                    "workplace": self._optional_text(raw.get("workplace")),
                    "address": self._optional_text(raw.get("address")),
                    "note": self._optional_text(raw.get("note")),
                    "is_primary": bool(raw.get("is_primary")),
                }
            )
        if normalized and not any(item["is_primary"] for item in normalized):
            normalized[0]["is_primary"] = True
        primary_seen = False
        for item in normalized:
            if item["is_primary"] and primary_seen:
                item["is_primary"] = False
            elif item["is_primary"]:
                primary_seen = True
        return normalized

    def _ensure_student_is_unique(self, session, values: dict[str, Any], student_id: int | None = None) -> None:
        if values["student_no"]:
            stmt = select(Student.id).where(
                Student.class_id == values["class_id"],
                Student.student_no == values["student_no"],
                Student.is_deleted.is_(False),
            )
            if student_id:
                stmt = stmt.where(Student.id != student_id)
            if session.scalar(stmt) is not None:
                raise StudentDuplicateError("该班级已存在相同学号的学生。")
        elif values["seat_no"]:
            stmt = select(Student.id).where(
                Student.class_id == values["class_id"],
                Student.name == values["name"],
                Student.seat_no == values["seat_no"],
                Student.is_deleted.is_(False),
            )
            if student_id:
                stmt = stmt.where(Student.id != student_id)
            if session.scalar(stmt) is not None:
                raise StudentDuplicateError("该班级已存在相同姓名和座号的学生。")
        if values["id_card"]:
            stmt = select(Student.id).where(
                Student.id_card == values["id_card"],
                Student.is_deleted.is_(False),
            )
            if student_id:
                stmt = stmt.where(Student.id != student_id)
            if session.scalar(stmt) is not None:
                raise StudentDuplicateError("该身份证号已存在于其他学生档案中。")

    def _sync_guardians(self, session, student: Student, guardian_values: list[dict[str, Any]]) -> None:
        existing = {guardian.id: guardian for guardian in student.guardians if not guardian.is_deleted}
        kept_ids = {int(item["id"]) for item in guardian_values if item.get("id") in existing}
        for guardian_id, guardian in existing.items():
            if guardian_id not in kept_ids:
                guardian.is_deleted = True
        session.flush()

        for values in guardian_values:
            guardian_id = values.pop("id", None)
            if guardian_id in existing:
                guardian = existing[guardian_id]
                for key, value in values.items():
                    setattr(guardian, key, value)
            else:
                student.guardians.append(Guardian(**values))

    @staticmethod
    def _student_row(student: Student, class_group: ClassGroup) -> dict[str, str]:
        phones = [guardian.phone for guardian in student.guardians if guardian.phone and not guardian.is_deleted]
        return {
            "_id": str(student.id),
            "ID": str(student.id),
            "姓名": student.name or "",
            "性别": student.gender or "",
            "学号": student.student_no or "",
            "班级": class_group.name or "",
            "年级": student.grade or class_group.grade or "",
            "座号": student.seat_no or "",
            "家长电话": " / ".join(phones),
            "备注": student.note or "",
        }

    def _export_student_records(self, class_id: int | None = None) -> list[dict[str, Any]]:
        with get_session() as session:
            stmt = (
                select(Student)
                .join(ClassGroup, Student.class_id == ClassGroup.id)
                .where(Student.is_deleted.is_(False), ClassGroup.is_deleted.is_(False))
                .options(joinedload(Student.class_group), selectinload(Student.guardians))
                .order_by(ClassGroup.grade, ClassGroup.name, Student.seat_no, Student.name)
            )
            if class_id:
                stmt = stmt.where(Student.class_id == class_id)
            students = session.scalars(stmt).all()
            return [
                {
                    "name": student.name,
                    "gender": student.gender or "",
                    "student_no": student.student_no or "",
                    "class_name": student.class_group.name,
                    "grade": student.grade or student.class_group.grade or "",
                    "seat_no": student.seat_no or "",
                    "birth_date": student.birth_date.isoformat() if student.birth_date else "",
                    "id_card": student.id_card or "",
                    "ethnicity": student.ethnicity or "",
                    "note": student.note or "",
                    "guardians": [
                        {
                            "name": guardian.name,
                            "relationship": guardian.relationship or "",
                            "phone": guardian.phone or "",
                            "wechat": guardian.wechat or "",
                            "workplace": guardian.workplace or "",
                            "address": guardian.address or "",
                            "note": guardian.note or "",
                        }
                        for guardian in student.guardians
                        if not guardian.is_deleted
                    ],
                }
                for student in students
            ]

    @staticmethod
    def _import_issue(row: ParsedStudentRow, message: str, skipped: bool = False) -> ImportIssue:
        return ImportIssue(
            row_number=row.row_number,
            field_name="学生信息",
            raw_value=f"{row.student.get('name', '')} / {row.student.get('class_name', '')}",
            message=message,
            skipped=skipped,
        )

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    @classmethod
    def _required_text(cls, value: Any, label: str) -> str:
        text = cls._optional_text(value)
        if not text:
            raise StudentDataError(f"请填写{label}。")
        return text
