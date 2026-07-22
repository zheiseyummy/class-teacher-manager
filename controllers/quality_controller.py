from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from database.connection import get_session
from models.class_group import ClassGroup
from models.quality import (
    QualityDimension,
    QualityFinalization,
    QualityFinalResult,
    QualityRecord,
    QualityRosterEntry,
)
from models.student import Student
from utils.excel_service import write_quality_export
from utils.quality_excel_import import QualityExcelImportError, read_quality_import_file
from utils.quality_scoring import (
    DEFAULT_QUALITY_DIMENSIONS,
    FINAL_LEVELS,
    FINAL_SEMESTER_KEY,
    LEVELS,
    RULE_BY_KEY,
    SEMESTER_RULES,
    TOTAL_MAXIMUM_SCORE,
    allocate_final_levels,
    competition_ranks,
    formatted_score,
    score_for_level,
    score_by_semester,
)


class QualityDataError(ValueError):
    """Raised when a quality evaluation cannot be saved consistently."""


@dataclass(frozen=True)
class QualityImportIssue:
    sheet_name: str
    row_number: int
    student_name: str
    message: str


@dataclass(frozen=True)
class QualityImportResult:
    file_name: str
    total_rows: int
    matched_students: int
    created_students: int
    target_class_id: int
    target_class_name: str
    created_class: bool
    updated_evaluations: int
    na_evaluations: int
    issues: list[QualityImportIssue]
    semester_sheets: dict[str, str]


class QualityController:
    def list_dimensions(self) -> list[dict[str, Any]]:
        with get_session() as session:
            dimensions = self._ensure_dimensions(session)
            return [
                {"id": dimension.id, "name": dimension.name, "sort_order": dimension.sort_order}
                for dimension in dimensions
            ]

    def update_dimensions(self, names: list[str]) -> None:
        clean_names = [str(name or "").strip() for name in names]
        if len(clean_names) != len(DEFAULT_QUALITY_DIMENSIONS):
            raise QualityDataError("综合素质评价固定为 5 个维度。")
        if not all(clean_names):
            raise QualityDataError("请填写全部 5 个维度名称。")
        if len(set(clean_names)) != len(clean_names):
            raise QualityDataError("五个维度名称不能重复。")
        with get_session() as session:
            dimensions = self._ensure_dimensions(session)
            current_names = [dimension.name for dimension in dimensions]
            has_records = session.scalar(
                select(func.count(QualityRecord.id)).where(QualityRecord.is_deleted.is_(False))
            )
            if has_records and clean_names != current_names:
                raise QualityDataError("已有综合素质评价记录，不能再修改维度名称。")
            for dimension, name in zip(dimensions, clean_names, strict=True):
                dimension.name = name

    def list_classes(self) -> list[dict[str, Any]]:
        with get_session() as session:
            classes = session.scalars(
                select(ClassGroup)
                .where(ClassGroup.is_deleted.is_(False))
                .order_by(ClassGroup.grade, ClassGroup.name)
            ).all()
            return [{"id": item.id, "name": item.name, "grade": item.grade or ""} for item in classes]

    def list_student_overviews(
        self,
        class_id: int | None = None,
        keyword: str = "",
    ) -> list[dict[str, str]]:
        dimensions = [item["name"] for item in self.list_dimensions()]
        keyword = keyword.strip()
        with get_session() as session:
            stmt = (
                select(Student)
                .join(ClassGroup, Student.class_id == ClassGroup.id)
                .options(joinedload(Student.class_group), selectinload(Student.quality_records))
                .where(Student.is_deleted.is_(False), ClassGroup.is_deleted.is_(False))
                .order_by(ClassGroup.grade, ClassGroup.name, Student.seat_no, Student.name)
            )
            if class_id is not None:
                stmt = stmt.where(Student.class_id == class_id)
            if keyword:
                like = f"%{keyword}%"
                stmt = stmt.where(or_(Student.name.like(like), Student.student_no.like(like)))
            students = session.scalars(stmt).all()
            return [self._overview(student, dimensions) for student in students]

    def get_student_evaluation(self, student_id: int, semester_key: str) -> dict[str, Any]:
        self._rule_for(semester_key)
        dimensions = [item["name"] for item in self.list_dimensions()]
        with get_session() as session:
            student = session.scalar(
                select(Student)
                .options(joinedload(Student.class_group), selectinload(Student.quality_records))
                .where(Student.id == student_id, Student.is_deleted.is_(False))
            )
            if student is None:
                raise QualityDataError("未找到该学生档案。")
            ratings = {
                record.dimension: record.level_or_score
                for record in student.quality_records
                if not record.is_deleted and record.semester == semester_key and record.dimension in dimensions
            }
            summary = self._summary(student.quality_records, dimensions)
            return {
                "student_id": student.id,
                "name": student.name,
                "class_name": student.class_group.name,
                "semester_key": semester_key,
                "ratings": ratings,
                "dimensions": dimensions,
                **summary,
            }

    def save_evaluation(self, student_id: int, semester_key: str, ratings: dict[str, str]) -> None:
        self._rule_for(semester_key)
        dimensions = [item["name"] for item in self.list_dimensions()]
        normalized = self._normalize_ratings(ratings, dimensions)

        with get_session() as session:
            student = session.scalar(
                select(Student)
                .options(selectinload(Student.quality_records))
                .where(Student.id == student_id, Student.is_deleted.is_(False))
            )
            if student is None:
                raise QualityDataError("未找到该学生档案。")
            self._assert_class_unlocked(session, student.class_id)
            self._save_evaluation_in_session(session, student, semester_key, normalized, dimensions)
            self._backfill_roster_entries(session, student.class_id)
            self._upsert_roster_entry(session, student.id, semester_key)
            self._invalidate_final_results(session, student.class_id)

    def import_quality_from_excel(
        self,
        file_path: str | Path,
        class_id: int | None = None,
    ) -> QualityImportResult:
        dimensions = [item["name"] for item in self.list_dimensions()]
        try:
            parsed_workbook = read_quality_import_file(file_path, dimensions)
        except QualityExcelImportError as exc:
            raise QualityDataError(str(exc)) from exc

        issues: list[QualityImportIssue] = []
        source_path = Path(file_path)
        with get_session() as session:
            target_class, created_class = self._resolve_import_target_class(session, class_id)
            self._assert_class_unlocked(session, target_class.id)
            students_stmt = (
                select(Student)
                .options(selectinload(Student.quality_records))
                .where(Student.is_deleted.is_(False), Student.class_id == target_class.id)
                .order_by(Student.id)
            )
            students_by_name: dict[str, list[Student]] = defaultdict(list)
            students_by_no: dict[str, Student] = {}
            for student in session.scalars(students_stmt).all():
                students_by_name[student.name.strip()].append(student)
                if student.student_no:
                    students_by_no[student.student_no.strip()] = student

            self._clear_class_roster_entries(session, target_class.id)

            ratings_by_student_term: dict[tuple[int, str], dict[str, str]] = {}
            participants: dict[int, Student] = {}
            created_students = 0
            for row in parsed_workbook.rows:
                if not row.name:
                    issues.append(self._import_issue(row, "学生姓名为空，已跳过。"))
                    continue
                student_name = row.name.strip()
                student_no = row.student_no.strip()
                if student_no and student_no in students_by_no:
                    student = students_by_no[student_no]
                    if student.name.strip() != student_name:
                        issues.append(
                            self._import_issue(
                                row,
                                f"学号匹配到“{student.name}”，已按学号记录并保留原姓名。",
                            )
                        )
                else:
                    matches = students_by_name.get(student_name, [])
                    if len(matches) > 1:
                        issues.append(self._import_issue(row, "目标班级中存在同名学生，请补充学号后再导入。"))
                        continue
                    if matches:
                        student = matches[0]
                        if student_no and not student.student_no:
                            student.student_no = student_no
                            students_by_no[student_no] = student
                    else:
                        student = Student(
                            class_id=target_class.id,
                            name=student_name,
                            student_no=student_no or None,
                            grade=target_class.grade,
                        )
                        session.add(student)
                        session.flush()
                        students_by_name[student_name].append(student)
                        if student_no:
                            students_by_no[student_no] = student
                        created_students += 1
                key = (student.id, row.semester_key)
                if key in ratings_by_student_term:
                    issues.append(self._import_issue(row, "该学生在此学期重复出现，已跳过重复行。"))
                    continue
                participants[student.id] = student
                self._upsert_roster_entry(session, student.id, row.semester_key)
                try:
                    ratings = self._normalize_ratings(row.ratings, dimensions, blanks_as_na=True)
                except QualityDataError as exc:
                    issues.append(self._import_issue(row, str(exc)))
                    continue
                ratings_by_student_term[key] = ratings

            updated_evaluations = 0
            na_evaluations = 0
            missing_ratings = {dimension: "N/A" for dimension in dimensions}
            for student in participants.values():
                for rule in SEMESTER_RULES:
                    ratings = ratings_by_student_term.get((student.id, rule.key), missing_ratings)
                    if "N/A" in ratings.values():
                        na_evaluations += 1
                    self._save_evaluation_in_session(session, student, rule.key, ratings, dimensions)
                    updated_evaluations += 1
            self._invalidate_final_results(session, target_class.id)
            target_class_id = target_class.id
            target_class_name = target_class.name

        return QualityImportResult(
            file_name=source_path.name,
            total_rows=len(parsed_workbook.rows),
            matched_students=len(participants),
            created_students=created_students,
            target_class_id=target_class_id,
            target_class_name=target_class_name,
            created_class=created_class,
            updated_evaluations=updated_evaluations,
            na_evaluations=na_evaluations,
            issues=issues,
            semester_sheets=parsed_workbook.semester_sheets,
        )

    def export_quality_to_excel(
        self,
        file_path: str | Path,
        class_id: int | None = None,
        keyword: str = "",
    ) -> Path:
        dimensions = [item["name"] for item in self.list_dimensions()]
        keyword = keyword.strip()
        with get_session() as session:
            stmt = (
                select(Student)
                .join(ClassGroup, Student.class_id == ClassGroup.id)
                .options(joinedload(Student.class_group), selectinload(Student.quality_records))
                .where(Student.is_deleted.is_(False), ClassGroup.is_deleted.is_(False))
                .order_by(ClassGroup.grade, ClassGroup.name, Student.seat_no, Student.name)
            )
            if class_id is not None:
                stmt = stmt.where(Student.class_id == class_id)
            if keyword:
                like = f"%{keyword}%"
                stmt = stmt.where(or_(Student.name.like(like), Student.student_no.like(like)))
            students = session.scalars(stmt).all()
            final_export = self._build_final_export_data(session, students, dimensions)
            rows = []
            for student in students:
                ratings = {
                    (record.semester, record.dimension): record.level_or_score
                    for record in student.quality_records
                    if not record.is_deleted and record.semester in RULE_BY_KEY and record.dimension in dimensions
                }
                rows.append(
                    {
                        "name": student.name,
                        "student_no": student.student_no or "",
                        "class_name": student.class_group.name,
                        "ratings": ratings,
                        "summary": self._summary(student.quality_records, dimensions),
                        "final": final_export.get(student.id, self._empty_final_export()),
                    }
                )
        return write_quality_export(file_path, rows, dimensions)

    def generate_final_results(self, class_id: int) -> dict[str, Any]:
        dimensions = [item["name"] for item in self.list_dimensions()]
        with get_session() as session:
            class_group = self._class_or_error(session, class_id)
            state = self._finalization_state(session, class_id, create=True)
            if state.is_locked:
                raise QualityDataError("最终评定已经锁定，请先解锁后再重新计算。")

            candidates = self._final_candidates(session, class_id, dimensions)
            if not candidates:
                raise QualityDataError("九下名单中没有可参加最终评定的学生。")
            snapshots = self._candidate_snapshots(candidates, dimensions)
            existing_results = session.scalars(
                select(QualityFinalResult).where(QualityFinalResult.class_id == class_id)
            ).all()
            existing_by_key = {
                (result.student_id, result.dimension): result for result in existing_results
            }
            valid_keys: set[tuple[int, str]] = set()

            for dimension in dimensions:
                scores = {
                    student_id: snapshot["summary"]["dimension_scores"][dimension]
                    for student_id, snapshot in snapshots.items()
                }
                ranks = competition_ranks(scores)
                automatic_levels = allocate_final_levels(scores)
                for student_id, score in scores.items():
                    key = (student_id, dimension)
                    valid_keys.add(key)
                    result = existing_by_key.get(key)
                    if result is None:
                        result = QualityFinalResult(
                            class_id=class_id,
                            student_id=student_id,
                            dimension=dimension,
                            cumulative_score=score,
                            class_rank=ranks[student_id],
                            automatic_level=automatic_levels[student_id],
                            final_level=automatic_levels[student_id],
                        )
                        session.add(result)
                    result.cumulative_score = score
                    result.class_rank = ranks[student_id]
                    result.automatic_level = automatic_levels[student_id]
                    if not result.is_manually_adjusted or result.final_level not in FINAL_LEVELS:
                        result.final_level = automatic_levels[student_id]
                        result.is_manually_adjusted = False
                    available_terms = snapshots[student_id]["available_terms"][dimension]
                    result.available_terms = available_terms
                    result.contains_na = available_terms < len(SEMESTER_RULES)

            for result in existing_results:
                if (result.student_id, result.dimension) not in valid_keys:
                    session.delete(result)
            state.generated_at = datetime.now()
            state.locked_at = None
            session.flush()
            return {
                "class_id": class_id,
                "class_name": class_group.name,
                "student_count": len(candidates),
                "result_count": len(candidates) * len(dimensions),
            }

    def get_final_review(
        self,
        class_id: int,
        dimension: str,
        keyword: str = "",
    ) -> dict[str, Any]:
        dimensions = [item["name"] for item in self.list_dimensions()]
        if dimension not in dimensions:
            raise QualityDataError("请选择有效的评价维度。")
        keyword = keyword.strip().lower()
        with get_session() as session:
            class_group = self._class_or_error(session, class_id)
            candidates = self._final_candidates(session, class_id, dimensions)
            snapshots = self._candidate_snapshots(candidates, dimensions)
            total_ranks = competition_ranks(
                {
                    student_id: snapshot["summary"]["total_score"]
                    for student_id, snapshot in snapshots.items()
                }
            )
            state = self._finalization_state(session, class_id)
            results = session.scalars(
                select(QualityFinalResult).where(
                    QualityFinalResult.class_id == class_id,
                    QualityFinalResult.dimension == dimension,
                )
            ).all()
            rows: list[dict[str, Any]] = []
            for result in results:
                snapshot = snapshots.get(result.student_id)
                if snapshot is None:
                    continue
                student = snapshot["student"]
                rows.append(
                    {
                        "result_id": result.id,
                        "student_id": student.id,
                        "name": student.name,
                        "student_no": student.student_no or "",
                        "class_name": class_group.name,
                        "dimension": dimension,
                        "score": result.cumulative_score,
                        "rank": result.class_rank,
                        "automatic_level": result.automatic_level,
                        "final_level": result.final_level,
                        "is_manually_adjusted": result.is_manually_adjusted,
                        "available_terms": result.available_terms,
                        "contains_na": result.contains_na,
                        "total_score": snapshot["summary"]["total_score"],
                        "total_rank": total_ranks.get(student.id),
                    }
                )
            all_rows = rows
            if keyword:
                rows = [
                    row
                    for row in rows
                    if keyword in row["name"].lower() or keyword in row["student_no"].lower()
                ]
            rows.sort(key=lambda row: (not row["contains_na"], row["rank"], row["name"]))
            level_counts = {
                level: sum(1 for row in all_rows if row["final_level"] == level)
                for level in FINAL_LEVELS
            }
            candidate_count = len(candidates)
            generated = bool(
                state is not None
                and state.generated_at is not None
                and len(results) == candidate_count
            )
            return {
                "class_id": class_id,
                "class_name": class_group.name,
                "dimension": dimension,
                "candidate_count": candidate_count,
                "rows": rows,
                "generated": generated,
                "is_locked": bool(state and state.is_locked),
                "generated_at": self._format_datetime(state.generated_at if state else None),
                "locked_at": self._format_datetime(state.locked_at if state else None),
                "level_counts": level_counts,
                "incomplete_count": sum(1 for row in all_rows if row["contains_na"]),
                "manual_count": sum(1 for row in all_rows if row["is_manually_adjusted"]),
            }

    def update_final_level(self, result_id: int, level: str) -> None:
        normalized = str(level or "").upper().strip()
        if normalized not in FINAL_LEVELS:
            raise QualityDataError("最终等级只能选择 A、B 或 C。")
        with get_session() as session:
            result = session.get(QualityFinalResult, result_id)
            if result is None:
                raise QualityDataError("未找到该项最终评定，请重新计算后再试。")
            self._assert_class_unlocked(session, result.class_id)
            result.final_level = normalized
            result.is_manually_adjusted = normalized != result.automatic_level

    def set_finalization_locked(self, class_id: int, locked: bool) -> None:
        dimensions = [item["name"] for item in self.list_dimensions()]
        with get_session() as session:
            self._class_or_error(session, class_id)
            state = self._finalization_state(session, class_id, create=locked)
            if state is None:
                raise QualityDataError("尚未生成最终评定结果。")
            if not locked:
                state.is_locked = False
                state.locked_at = None
                return

            candidates = self._final_candidates(session, class_id, dimensions)
            expected_count = len(candidates) * len(dimensions)
            results = session.scalars(
                select(QualityFinalResult).where(QualityFinalResult.class_id == class_id)
            ).all()
            if not candidates or state.generated_at is None or len(results) != expected_count:
                raise QualityDataError("最终结果不完整，请先重新计算五个维度。")
            a_limit = int(len(candidates) * 0.60) + 1
            for dimension in dimensions:
                dimension_results = [result for result in results if result.dimension == dimension]
                if any(result.final_level not in FINAL_LEVELS for result in dimension_results):
                    raise QualityDataError(f"“{dimension}”仍有未确认的最终等级。")
                a_count = sum(1 for result in dimension_results if result.final_level == "A")
                if a_count > a_limit:
                    raise QualityDataError(
                        f"“{dimension}”的 A 等级为 {a_count} 人，最多允许 {a_limit} 人。"
                    )
            state.is_locked = True
            state.locked_at = datetime.now()

    @staticmethod
    def _class_or_error(session, class_id: int) -> ClassGroup:
        class_group = session.scalar(
            select(ClassGroup).where(ClassGroup.id == class_id, ClassGroup.is_deleted.is_(False))
        )
        if class_group is None:
            raise QualityDataError("请选择有效的目标班级。")
        return class_group

    @staticmethod
    def _finalization_state(
        session,
        class_id: int,
        *,
        create: bool = False,
    ) -> QualityFinalization | None:
        state = session.scalar(
            select(QualityFinalization).where(QualityFinalization.class_id == class_id)
        )
        if state is None and create:
            state = QualityFinalization(class_id=class_id)
            session.add(state)
            session.flush()
        return state

    def _assert_class_unlocked(self, session, class_id: int) -> None:
        state = self._finalization_state(session, class_id)
        if state is not None and state.is_locked:
            raise QualityDataError("该班最终评定已经锁定，请先在最终评定中解锁。")

    def _invalidate_final_results(self, session, class_id: int) -> None:
        for result in session.scalars(
            select(QualityFinalResult).where(QualityFinalResult.class_id == class_id)
        ).all():
            session.delete(result)
        state = self._finalization_state(session, class_id)
        if state is not None:
            state.generated_at = None
            state.is_locked = False
            state.locked_at = None

    @staticmethod
    def _clear_class_roster_entries(session, class_id: int) -> None:
        entries = session.scalars(
            select(QualityRosterEntry)
            .join(Student, QualityRosterEntry.student_id == Student.id)
            .where(Student.class_id == class_id, QualityRosterEntry.is_deleted.is_(False))
        ).all()
        for entry in entries:
            entry.is_deleted = True
        session.flush()

    @staticmethod
    def _upsert_roster_entry(session, student_id: int, semester_key: str) -> None:
        entry = session.scalar(
            select(QualityRosterEntry)
            .where(
                QualityRosterEntry.student_id == student_id,
                QualityRosterEntry.semester == semester_key,
            )
            .order_by(QualityRosterEntry.is_deleted, QualityRosterEntry.id.desc())
        )
        if entry is None:
            session.add(QualityRosterEntry(student_id=student_id, semester=semester_key))
        else:
            entry.is_deleted = False

    def _backfill_roster_entries(self, session, class_id: int) -> None:
        roster_count = session.scalar(
            select(func.count(QualityRosterEntry.id))
            .join(Student, QualityRosterEntry.student_id == Student.id)
            .where(Student.class_id == class_id, QualityRosterEntry.is_deleted.is_(False))
        )
        if roster_count:
            return
        source_rows = session.execute(
            select(QualityRecord.student_id, QualityRecord.semester)
            .join(Student, QualityRecord.student_id == Student.id)
            .where(
                Student.class_id == class_id,
                Student.is_deleted.is_(False),
                QualityRecord.is_deleted.is_(False),
                QualityRecord.semester.in_(RULE_BY_KEY),
                QualityRecord.level_or_score != "N/A",
            )
            .distinct()
        ).all()
        for student_id, semester_key in source_rows:
            self._upsert_roster_entry(session, student_id, semester_key)

    def _final_candidates(
        self,
        session,
        class_id: int,
        dimensions: list[str],
    ) -> list[Student]:
        students = session.scalars(
            select(Student)
            .options(joinedload(Student.class_group), selectinload(Student.quality_records))
            .where(Student.class_id == class_id, Student.is_deleted.is_(False))
            .order_by(Student.seat_no, Student.name, Student.id)
        ).all()
        roster_count = session.scalar(
            select(func.count(QualityRosterEntry.id))
            .join(Student, QualityRosterEntry.student_id == Student.id)
            .where(Student.class_id == class_id, QualityRosterEntry.is_deleted.is_(False))
        )
        if roster_count:
            final_ids = set(
                session.scalars(
                    select(QualityRosterEntry.student_id)
                    .join(Student, QualityRosterEntry.student_id == Student.id)
                    .where(
                        Student.class_id == class_id,
                        Student.is_deleted.is_(False),
                        QualityRosterEntry.semester == FINAL_SEMESTER_KEY,
                        QualityRosterEntry.is_deleted.is_(False),
                    )
                ).all()
            )
            return [student for student in students if student.id in final_ids]

        return [
            student
            for student in students
            if any(
                not record.is_deleted
                and record.semester == FINAL_SEMESTER_KEY
                and record.dimension in dimensions
                and record.level_or_score != "N/A"
                for record in student.quality_records
            )
        ]

    def _candidate_snapshots(
        self,
        candidates: list[Student],
        dimensions: list[str],
    ) -> dict[int, dict[str, Any]]:
        snapshots: dict[int, dict[str, Any]] = {}
        for student in candidates:
            available_terms = {
                dimension: len(
                    {
                        record.semester
                        for record in student.quality_records
                        if not record.is_deleted
                        and record.semester in RULE_BY_KEY
                        and record.dimension == dimension
                        and record.level_or_score in LEVELS
                        and record.level_or_score != "N/A"
                    }
                )
                for dimension in dimensions
            }
            snapshots[student.id] = {
                "student": student,
                "summary": self._summary(student.quality_records, dimensions),
                "available_terms": available_terms,
            }
        return snapshots

    def _build_final_export_data(
        self,
        session,
        students: list[Student],
        dimensions: list[str],
    ) -> dict[int, dict[str, Any]]:
        export_data = {student.id: self._empty_final_export() for student in students}
        class_ids = {student.class_id for student in students}
        if not class_ids:
            return export_data
        results = session.scalars(
            select(QualityFinalResult).where(QualityFinalResult.class_id.in_(class_ids))
        ).all()
        results_by_student: dict[int, dict[str, QualityFinalResult]] = defaultdict(dict)
        for result in results:
            results_by_student[result.student_id][result.dimension] = result
        states = {
            state.class_id: state
            for state in session.scalars(
                select(QualityFinalization).where(QualityFinalization.class_id.in_(class_ids))
            ).all()
        }

        for class_group_id in class_ids:
            candidates = self._final_candidates(session, class_group_id, dimensions)
            snapshots = self._candidate_snapshots(candidates, dimensions)
            total_ranks = competition_ranks(
                {
                    student_id: snapshot["summary"]["total_score"]
                    for student_id, snapshot in snapshots.items()
                }
            )
            state = states.get(class_group_id)
            for student_id, snapshot in snapshots.items():
                dimension_results = results_by_student.get(student_id, {})
                generated = all(dimension in dimension_results for dimension in dimensions)
                export_data[student_id] = {
                    "in_final_roster": True,
                    "dimension_ranks": {
                        dimension: dimension_results[dimension].class_rank
                        for dimension in dimensions
                        if dimension in dimension_results
                    },
                    "automatic_levels": {
                        dimension: dimension_results[dimension].automatic_level
                        for dimension in dimensions
                        if dimension in dimension_results
                    },
                    "final_levels": {
                        dimension: dimension_results[dimension].final_level
                        for dimension in dimensions
                        if dimension in dimension_results
                    },
                    "total_rank": total_ranks.get(student_id),
                    "generated": generated,
                    "is_locked": bool(state and state.is_locked and generated),
                    "contains_na": any(
                        count < len(SEMESTER_RULES)
                        for count in snapshot["available_terms"].values()
                    ),
                }
        return export_data

    @staticmethod
    def _empty_final_export() -> dict[str, Any]:
        return {
            "in_final_roster": False,
            "dimension_ranks": {},
            "automatic_levels": {},
            "final_levels": {},
            "total_rank": None,
            "generated": False,
            "is_locked": False,
            "contains_na": False,
        }

    @staticmethod
    def _format_datetime(value: datetime | None) -> str:
        return value.strftime("%Y-%m-%d %H:%M") if value else ""

    def _ensure_dimensions(self, session) -> list[QualityDimension]:
        dimensions = session.scalars(
            select(QualityDimension)
            .where(QualityDimension.is_deleted.is_(False))
            .order_by(QualityDimension.sort_order)
        ).all()
        legacy_defaults = ["维度一", "维度二", "维度三", "维度四", "维度五"]
        if dimensions:
            has_records = session.scalar(
                select(func.count(QualityRecord.id)).where(QualityRecord.is_deleted.is_(False))
            )
            if not has_records and [item.name for item in dimensions] == legacy_defaults:
                for dimension, name in zip(dimensions, DEFAULT_QUALITY_DIMENSIONS, strict=True):
                    dimension.name = name
            return dimensions
        for sort_order, name in enumerate(DEFAULT_QUALITY_DIMENSIONS, start=1):
            session.add(QualityDimension(name=name, sort_order=sort_order))
        session.flush()
        return session.scalars(
            select(QualityDimension)
            .where(QualityDimension.is_deleted.is_(False))
            .order_by(QualityDimension.sort_order)
        ).all()

    @staticmethod
    def _resolve_import_target_class(session, class_id: int | None) -> tuple[ClassGroup, bool]:
        if class_id is not None:
            class_group = session.scalar(
                select(ClassGroup).where(ClassGroup.id == class_id, ClassGroup.is_deleted.is_(False))
            )
            if class_group is None:
                raise QualityDataError("请选择有效的目标班级。")
            return class_group, False

        class_group = session.scalar(
            select(ClassGroup)
            .where(ClassGroup.name == "综合素质导入班", ClassGroup.is_deleted.is_(False))
            .order_by(ClassGroup.id.desc())
        )
        if class_group is not None:
            return class_group, False
        class_group = ClassGroup(
            name="综合素质导入班",
            grade="初中",
            note="由综合素质评价模块独立导入时自动创建。",
        )
        session.add(class_group)
        session.flush()
        return class_group, True

    @staticmethod
    def _rule_for(semester_key: str):
        try:
            return RULE_BY_KEY[semester_key]
        except KeyError as exc:
            raise QualityDataError("无效的评价学期。") from exc

    @staticmethod
    def _import_issue(row, message: str) -> QualityImportIssue:
        return QualityImportIssue(row.sheet_name, row.row_number, row.name, message)

    @staticmethod
    def _normalize_ratings(
        ratings: dict[str, str],
        dimensions: list[str],
        *,
        blanks_as_na: bool = False,
    ) -> dict[str, str]:
        if set(ratings) != set(dimensions):
            raise QualityDataError("请提供全部 5 个维度的评价。")
        normalized: dict[str, str] = {}
        for dimension, raw_level in ratings.items():
            level = str(raw_level or "").upper().strip()
            if level in {"NA", "N.A.", "不适用", "缺失", "无", "-"}:
                level = "N/A"
            if not level and blanks_as_na:
                level = "N/A"
            if level not in LEVELS:
                raise QualityDataError(f"“{dimension}”只能填写 A、B、C、D 或 N/A。")
            normalized[dimension] = level
        return normalized

    @staticmethod
    def _save_evaluation_in_session(
        session,
        student: Student,
        semester_key: str,
        ratings: dict[str, str],
        dimensions: list[str],
    ) -> None:
        existing = {
            record.dimension: record
            for record in student.quality_records
            if not record.is_deleted and record.semester == semester_key and record.dimension in dimensions
        }
        for dimension, level in ratings.items():
            if dimension in existing:
                existing[dimension].level_or_score = level
            else:
                session.add(
                    QualityRecord(
                        student_id=student.id,
                        semester=semester_key,
                        dimension=dimension,
                        level_or_score=level,
                    )
                )

    def _overview(self, student: Student, dimensions: list[str]) -> dict[str, str]:
        summary = self._summary(student.quality_records, dimensions)
        return {
            "_id": str(student.id),
            "姓名": student.name,
            "学号": student.student_no or "",
            "班级": student.class_group.name,
            "已完成学期": f"{summary['completed_terms']}/6",
            "当前累计": f"{formatted_score(summary['total_score'])}/50",
            "最终分数": formatted_score(summary["final_score"]) if summary["final_ready"] else "待完成六学期",
        }

    @staticmethod
    def _summary(records: list[QualityRecord], dimensions: list[str]) -> dict[str, Any]:
        valid_records = [
            record
            for record in records
            if not record.is_deleted
            and record.semester in RULE_BY_KEY
            and record.dimension in dimensions
            and record.level_or_score in LEVELS
        ]
        levels_by_semester: dict[str, set[str]] = defaultdict(set)
        semesters_by_dimension: dict[str, set[str]] = defaultdict(set)
        dimension_scores = {dimension: 0.0 for dimension in dimensions}
        na_semesters: dict[str, set[str]] = defaultdict(set)
        na_dimensions: dict[str, set[str]] = defaultdict(set)
        for record in valid_records:
            levels_by_semester[record.semester].add(record.dimension)
            semesters_by_dimension[record.dimension].add(record.semester)
            dimension_scores[record.dimension] += score_for_level(record.semester, record.level_or_score)
            if record.level_or_score == "N/A":
                na_semesters[record.semester].add(record.dimension)
                na_dimensions[record.dimension].add(record.semester)
        completed_keys = [
            rule.key
            for rule in SEMESTER_RULES
            if len(levels_by_semester.get(rule.key, set())) == len(dimensions)
        ]
        semester_scores = score_by_semester(
            (record.semester, record.level_or_score) for record in valid_records
        )
        dimension_scores = {key: round(value, 2) for key, value in dimension_scores.items()}
        completed_dimensions = [
            dimension
            for dimension in dimensions
            if len(semesters_by_dimension.get(dimension, set())) == len(SEMESTER_RULES)
        ]
        total_score = round(sum(dimension_scores.values()), 2)
        final_ready = (
            len(completed_dimensions) == len(dimensions)
            and len(completed_keys) == len(SEMESTER_RULES)
            and FINAL_SEMESTER_KEY in completed_keys
        )
        return {
            "completed_terms": len(completed_keys),
            "completed_keys": completed_keys,
            "semester_scores": semester_scores,
            "dimension_scores": dimension_scores,
            "completed_dimensions": completed_dimensions,
            "na_semesters": sorted(na_semesters),
            "na_dimensions": sorted(na_dimensions),
            "contains_na": bool(na_semesters),
            "total_score": total_score,
            "final_ready": final_ready,
            "final_score": total_score if final_ready else None,
            "total_maximum": TOTAL_MAXIMUM_SCORE,
        }
