from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from database.connection import get_session
from models.class_group import ClassGroup
from models.exam import Exam, ExamScore
from models.student import Student
from utils.score_excel_import import (
    DEFAULT_SUBJECTS,
    ParsedScoreRow,
    ScoreExcelImportError,
    read_score_import_file,
)


class ScoreDataError(ValueError):
    """Raised when exam score data cannot be saved or analysed."""


@dataclass(frozen=True)
class ScoreImportIssue:
    row_number: int
    student_name: str
    message: str


@dataclass(frozen=True)
class ScoreImportResult:
    file_name: str
    exam_id: int
    exam_label: str
    subjects: list[str]
    total_rows: int
    imported_students: int
    created_students: int
    written_scores: int
    updated_scores: int
    class_names: list[str]
    issues: list[ScoreImportIssue]


class ScoreController:
    def list_classes(self) -> list[dict[str, Any]]:
        with get_session() as session:
            classes = session.scalars(
                select(ClassGroup)
                .where(ClassGroup.is_deleted.is_(False))
                .order_by(ClassGroup.grade, ClassGroup.name)
            ).all()
            return [{"id": item.id, "name": item.name, "grade": item.grade or ""} for item in classes]

    def list_exams(self) -> list[dict[str, Any]]:
        with get_session() as session:
            exams = session.scalars(
                select(Exam)
                .where(Exam.is_deleted.is_(False))
                .order_by(Exam.exam_date.desc(), Exam.id.desc())
            ).all()
            return [
                {
                    "id": exam.id,
                    "name": exam.name,
                    "exam_date": exam.exam_date,
                    "semester": exam.semester or "",
                    "grade": exam.grade or "",
                    "label": self._exam_label(exam),
                }
                for exam in exams
            ]

    def import_scores_from_excel(
        self,
        file_path: str | Path,
        exam_data: dict[str, Any],
        target_class_id: int | None = None,
    ) -> ScoreImportResult:
        try:
            workbook = read_score_import_file(file_path)
        except ScoreExcelImportError as exc:
            raise ScoreDataError(str(exc)) from exc
        values = self._exam_values(exam_data)
        source_path = Path(file_path)
        issues: list[ScoreImportIssue] = []

        with get_session() as session:
            exam = self._find_or_create_exam(session, values)
            selected_class = self._active_class(session, target_class_id) if target_class_id else None
            default_class: ClassGroup | None = None
            class_names: set[str] = set()
            existing_scores = {
                (item.student_id, item.subject): item
                for item in session.scalars(
                    select(ExamScore).where(ExamScore.exam_id == exam.id, ExamScore.is_deleted.is_(False))
                ).all()
            }
            imported_students: set[int] = set()
            created_students = 0
            written_scores = 0
            updated_scores = 0

            for row in workbook.rows:
                if not row.name and not row.student_no:
                    issues.append(self._issue(row, "学生姓名和学号均为空，已跳过。"))
                    continue
                if not row.scores:
                    issues.append(self._issue(row, "未读取到有效成绩，已跳过。"))
                    continue
                for subject, raw_value in row.invalid_scores.items():
                    issues.append(self._issue(row, f"{subject}成绩“{raw_value}”不是有效数字，未导入该科。"))

                class_group, default_class = self._resolve_row_class(
                    session,
                    row,
                    selected_class,
                    default_class,
                    values["grade"],
                )
                student, was_created = self._resolve_student(session, class_group, row)
                if student is None:
                    issues.append(self._issue(row, "目标班级中存在同名或同学号学生，已跳过。"))
                    continue
                if was_created:
                    created_students += 1
                class_names.add(class_group.name)
                imported_students.add(student.id)

                for subject, score in row.scores.items():
                    key = (student.id, subject)
                    existing = existing_scores.get(key)
                    if existing is None:
                        existing = ExamScore(
                            exam_id=exam.id,
                            student_id=student.id,
                            subject=subject,
                            score=score,
                            full_score=workbook.full_scores.get(subject),
                        )
                        session.add(existing)
                        existing_scores[key] = existing
                        written_scores += 1
                    else:
                        existing.score = score
                        existing.full_score = workbook.full_scores.get(subject) or existing.full_score
                        updated_scores += 1

            exam_id = exam.id
            exam_label = self._exam_label(exam)

        return ScoreImportResult(
            file_name=source_path.name,
            exam_id=exam_id,
            exam_label=exam_label,
            subjects=workbook.subjects,
            total_rows=len(workbook.rows),
            imported_students=len(imported_students),
            created_students=created_students,
            written_scores=written_scores,
            updated_scores=updated_scores,
            class_names=sorted(class_names),
            issues=issues,
        )

    def get_exam_dashboard(self, exam_id: int, class_id: int | None = None) -> dict[str, Any]:
        snapshot = self._exam_snapshot(exam_id)
        selected_states = sorted(
            (state for state in snapshot["states"].values() if class_id is None or state["class_id"] == class_id),
            key=lambda state: (-state["total"], state["name"]),
        )
        subject_stats = self._subject_stats(selected_states, snapshot["subjects"])
        totals = [state["total"] for state in selected_states]
        return {
            "exam": snapshot["exam"],
            "subjects": snapshot["subjects"],
            "rows": [self._display_row(state, snapshot["subjects"]) for state in selected_states],
            "subject_stats": subject_stats,
            "summary": {
                "student_count": len(selected_states),
                "average_total": self._round(mean(totals)) if totals else 0.0,
                "highest_total": self._round(max(totals)) if totals else 0.0,
                "lowest_total": self._round(min(totals)) if totals else 0.0,
            },
        }

    def get_student_analysis(self, student_id: int, current_exam_id: int) -> dict[str, Any]:
        current_snapshot = self._exam_snapshot(current_exam_id)
        current_state = current_snapshot["states"].get(student_id)
        if current_state is None:
            raise ScoreDataError("该学生没有本次考试成绩。")

        trend_rows: list[dict[str, Any]] = []
        previous_total: float | None = None
        for exam in self.list_exams()[::-1]:
            snapshot = self._exam_snapshot(exam["id"])
            state = snapshot["states"].get(student_id)
            if state is None:
                continue
            change = None if previous_total is None else self._round(state["total"] - previous_total)
            trend_rows.append(
                {
                    "exam": exam["label"],
                    "total": state["total"],
                    "class_rank": state["class_rank"],
                    "grade_rank": state["grade_rank"],
                    "change": change,
                }
            )
            previous_total = state["total"]

        class_states = [
            state for state in current_snapshot["states"].values() if state["class_id"] == current_state["class_id"]
        ]
        subject_rows: list[dict[str, Any]] = []
        for subject in current_snapshot["subjects"]:
            score = current_state["scores"].get(subject)
            values = [state["scores"][subject] for state in class_states if subject in state["scores"]]
            class_average = self._round(mean(values)) if values else None
            difference = self._round(score - class_average) if score is not None and class_average is not None else None
            if score is None or class_average in (None, 0):
                status = "暂无比较"
            elif score < class_average * 0.9:
                status = "偏弱"
            elif score > class_average * 1.1:
                status = "优势"
            else:
                status = "均衡"
            subject_rows.append(
                {
                    "subject": subject,
                    "score": score,
                    "class_average": class_average,
                    "difference": difference,
                    "status": status,
                }
            )

        return {
            "name": current_state["name"],
            "class_name": current_state["class_name"],
            "current_total": current_state["total"],
            "current_class_rank": current_state["class_rank"],
            "current_grade_rank": current_state["grade_rank"],
            "trend_rows": trend_rows,
            "subject_rows": subject_rows,
        }

    def get_class_trends(self, class_id: int | None) -> list[dict[str, Any]]:
        if class_id is None:
            return []
        trends: list[dict[str, Any]] = []
        for exam in self.list_exams()[::-1]:
            snapshot = self._exam_snapshot(exam["id"])
            class_states = [state for state in snapshot["states"].values() if state["class_id"] == class_id]
            if not class_states:
                continue
            grade = class_states[0]["grade"]
            grade_states = [state for state in snapshot["states"].values() if state["grade"] == grade]
            class_average = self._round(mean(state["total"] for state in class_states))
            grade_average = self._round(mean(state["total"] for state in grade_states)) if grade_states else 0.0
            averages_by_class: dict[int, list[float]] = defaultdict(list)
            for state in grade_states:
                averages_by_class[state["class_id"]].append(state["total"])
            class_averages = {
                item_class_id: self._round(mean(values)) for item_class_id, values in averages_by_class.items()
            }
            rank = self._rank_values(class_averages)
            trends.append(
                {
                    "exam": exam["label"],
                    "class_average": class_average,
                    "grade_average": grade_average,
                    "class_rank": rank.get(class_id),
                    "class_count": len(class_averages),
                }
            )
        return trends

    def get_subject_trends(self, class_id: int | None) -> list[dict[str, Any]]:
        trends: list[dict[str, Any]] = []
        previous_averages: dict[str, float] = {}
        for exam in self.list_exams()[::-1]:
            snapshot = self._exam_snapshot(exam["id"])
            states = [
                state
                for state in snapshot["states"].values()
                if class_id is None or state["class_id"] == class_id
            ]
            for stat in self._subject_stats(states, snapshot["subjects"]):
                previous = previous_averages.get(stat["subject"])
                trends.append(
                    {
                        "exam": exam["label"],
                        "subject": stat["subject"],
                        "average": stat["average"],
                        "count": stat["count"],
                        "change": None if previous is None else self._round(stat["average"] - previous),
                    }
                )
                previous_averages[stat["subject"]] = stat["average"]
        return trends

    def get_recent_fluctuations(self, class_id: int, limit: int = 5) -> dict[str, Any]:
        """Compare the latest two same-semester exams available for one class."""

        current: dict[str, Any] | None = None
        previous: dict[str, Any] | None = None
        for exam in self.list_exams():
            snapshot = self._exam_snapshot(exam["id"])
            states = {
                student_id: state
                for student_id, state in snapshot["states"].items()
                if state["class_id"] == class_id
            }
            if not states:
                continue
            candidate = {"exam": snapshot["exam"], "states": states}
            if current is None:
                current = candidate
            elif self._same_comparison_period(current["exam"], candidate["exam"]):
                previous = candidate
                break

        if current is None:
            return {
                "current_exam": None,
                "previous_exam": None,
                "rows": [],
                "reason": "该班暂无考试成绩",
            }

        current_exam = current["exam"]
        if previous is None:
            return {
                "current_exam": current_exam,
                "previous_exam": None,
                "rows": [],
                "reason": "本学期至少需要两次该班考试成绩",
            }

        rows: list[dict[str, Any]] = []
        common_student_ids = set(current["states"]) & set(previous["states"])
        for student_id in common_student_ids:
            current_state = current["states"][student_id]
            previous_state = previous["states"][student_id]
            current_subjects = set(current_state["scores"])
            previous_subjects = set(previous_state["scores"])
            subject_changes = [
                {
                    "subject": subject,
                    "previous": previous_state["scores"][subject],
                    "current": current_state["scores"][subject],
                    "change": self._round(
                        current_state["scores"][subject] - previous_state["scores"][subject]
                    ),
                }
                for subject in current_subjects & previous_subjects
            ]
            subject_changes.sort(key=lambda row: (-abs(row["change"]), row["subject"]))
            total_change = self._round(current_state["total"] - previous_state["total"])
            rank_change = previous_state["class_rank"] - current_state["class_rank"]
            if (
                rank_change == 0
                and total_change == 0
                and not any(item["change"] for item in subject_changes)
            ):
                continue
            rows.append(
                {
                    "student_id": student_id,
                    "name": current_state["name"],
                    "student_no": current_state["student_no"],
                    "previous_total": previous_state["total"],
                    "current_total": current_state["total"],
                    "total_change": total_change,
                    "total_comparable": current_subjects == previous_subjects,
                    "previous_class_rank": previous_state["class_rank"],
                    "current_class_rank": current_state["class_rank"],
                    "previous_grade_rank": previous_state["grade_rank"],
                    "current_grade_rank": current_state["grade_rank"],
                    "rank_change": rank_change,
                    "subject_changes": subject_changes[:2],
                }
            )

        rows.sort(
            key=lambda row: (
                -abs(row["rank_change"]),
                -(
                    abs(row["total_change"])
                    if row["total_comparable"]
                    else max(
                        (abs(item["change"]) for item in row["subject_changes"]),
                        default=0,
                    )
                ),
                row["name"],
            )
        )
        return {
            "current_exam": current_exam,
            "previous_exam": previous["exam"],
            "rows": rows[: max(1, limit)],
            "reason": "" if rows else "最近两次考试暂无成绩波动",
        }

    def _exam_snapshot(self, exam_id: int) -> dict[str, Any]:
        with get_session() as session:
            exam = session.scalar(
                select(Exam)
                .options(selectinload(Exam.scores))
                .where(Exam.id == exam_id, Exam.is_deleted.is_(False))
            )
            if exam is None:
                raise ScoreDataError("未找到该次考试。")
            records = session.scalars(
                select(ExamScore)
                .options(joinedload(ExamScore.student).joinedload(Student.class_group))
                .join(Student, ExamScore.student_id == Student.id)
                .where(ExamScore.exam_id == exam_id, ExamScore.is_deleted.is_(False), Student.is_deleted.is_(False))
            ).all()
            subjects = self._ordered_subjects({record.subject for record in records})
            states: dict[int, dict[str, Any]] = {}
            for record in records:
                student = record.student
                if student.class_group is None or student.class_group.is_deleted:
                    continue
                state = states.setdefault(
                    student.id,
                    {
                        "student_id": student.id,
                        "name": student.name,
                        "student_no": student.student_no or "",
                        "class_id": student.class_id,
                        "class_name": student.class_group.name,
                        "grade": student.class_group.grade or student.grade or "未设置年级",
                        "scores": {},
                    },
                )
                state["scores"][record.subject] = record.score
            for state in states.values():
                state["total"] = self._round(sum(state["scores"].values()))

            by_class: dict[int, list[dict[str, Any]]] = defaultdict(list)
            by_grade: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for state in states.values():
                by_class[state["class_id"]].append(state)
                by_grade[state["grade"]].append(state)
            for group in by_class.values():
                ranks = self._rank_values({state["student_id"]: state["total"] for state in group})
                for state in group:
                    state["class_rank"] = ranks[state["student_id"]]
            for group in by_grade.values():
                ranks = self._rank_values({state["student_id"]: state["total"] for state in group})
                for state in group:
                    state["grade_rank"] = ranks[state["student_id"]]

            return {
                "exam": {
                    "id": exam.id,
                    "label": self._exam_label(exam),
                    "name": exam.name,
                    "exam_date": exam.exam_date,
                    "semester": exam.semester or "",
                    "grade": exam.grade or "",
                },
                "subjects": subjects,
                "states": states,
            }

    @staticmethod
    def _same_comparison_period(current: dict[str, Any], previous: dict[str, Any]) -> bool:
        if current["semester"] and current["semester"] != previous["semester"]:
            return False
        if current["grade"] and previous["grade"] and current["grade"] != previous["grade"]:
            return False
        return True

    def _find_or_create_exam(self, session, values: dict[str, Any]) -> Exam:
        stmt = select(Exam).where(Exam.name == values["name"], Exam.is_deleted.is_(False))
        for field in ("exam_date", "semester", "grade"):
            value = values[field]
            stmt = stmt.where(getattr(Exam, field).is_(None) if value is None else getattr(Exam, field) == value)
        exam = session.scalar(stmt.order_by(Exam.id.desc()))
        if exam is None:
            exam = Exam(**values)
            session.add(exam)
            session.flush()
        else:
            exam.note = values["note"] or exam.note
        return exam

    @staticmethod
    def _active_class(session, class_id: int) -> ClassGroup:
        class_group = session.scalar(
            select(ClassGroup).where(ClassGroup.id == class_id, ClassGroup.is_deleted.is_(False))
        )
        if class_group is None:
            raise ScoreDataError("请选择有效的目标班级。")
        return class_group

    def _resolve_row_class(
        self,
        session,
        row: ParsedScoreRow,
        selected_class: ClassGroup | None,
        default_class: ClassGroup | None,
        grade: str | None,
    ) -> tuple[ClassGroup, ClassGroup | None]:
        if selected_class is not None:
            return selected_class, default_class
        if row.class_name:
            class_group = session.scalar(
                select(ClassGroup)
                .where(ClassGroup.name == row.class_name, ClassGroup.is_deleted.is_(False))
                .order_by(ClassGroup.id.desc())
            )
            if class_group is None:
                class_group = ClassGroup(name=row.class_name, grade=grade)
                session.add(class_group)
                session.flush()
            elif not class_group.grade and grade:
                class_group.grade = grade
            return class_group, default_class
        if default_class is None:
            default_class = session.scalar(
                select(ClassGroup)
                .where(ClassGroup.name == "成绩导入班", ClassGroup.is_deleted.is_(False))
                .order_by(ClassGroup.id.desc())
            )
            if default_class is None:
                default_class = ClassGroup(
                    name="成绩导入班",
                    grade=grade,
                    note="由成绩管理模块导入时自动创建。",
                )
                session.add(default_class)
                session.flush()
        return default_class, default_class

    @staticmethod
    def _resolve_student(session, class_group: ClassGroup, row: ParsedScoreRow) -> tuple[Student | None, bool]:
        if row.student_no:
            matches = session.scalars(
                select(Student).where(
                    Student.class_id == class_group.id,
                    Student.student_no == row.student_no,
                    Student.is_deleted.is_(False),
                )
            ).all()
        else:
            matches = session.scalars(
                select(Student).where(
                    Student.class_id == class_group.id,
                    Student.name == row.name,
                    Student.is_deleted.is_(False),
                )
            ).all()
        if len(matches) == 1:
            return matches[0], False
        if len(matches) > 1 or not row.name:
            return None, False
        student = Student(
            class_id=class_group.id,
            name=row.name,
            student_no=row.student_no or None,
            grade=class_group.grade,
        )
        session.add(student)
        session.flush()
        return student, True

    @staticmethod
    def _issue(row: ParsedScoreRow, message: str) -> ScoreImportIssue:
        return ScoreImportIssue(row.row_number, row.name or row.student_no or "-", message)

    @staticmethod
    def _exam_values(data: dict[str, Any]) -> dict[str, Any]:
        name = str(data.get("name") or "").strip()
        if not name:
            raise ScoreDataError("请填写考试名称。")
        exam_date = data.get("exam_date")
        if exam_date is not None and not isinstance(exam_date, date):
            raise ScoreDataError("考试日期格式不正确。")
        return {
            "name": name,
            "exam_date": exam_date,
            "semester": str(data.get("semester") or "").strip() or None,
            "grade": str(data.get("grade") or "").strip() or None,
            "note": str(data.get("note") or "").strip() or None,
        }

    @staticmethod
    def _ordered_subjects(subjects: set[str]) -> list[str]:
        return [subject for subject in DEFAULT_SUBJECTS if subject in subjects] + sorted(subjects - set(DEFAULT_SUBJECTS))

    @staticmethod
    def _rank_values(values: dict[int, float]) -> dict[int, int]:
        ranks: dict[int, int] = {}
        previous_value: float | None = None
        current_rank = 0
        for position, (item_id, value) in enumerate(
            sorted(values.items(), key=lambda item: (-item[1], item[0])),
            start=1,
        ):
            if previous_value is None or value != previous_value:
                current_rank = position
                previous_value = value
            ranks[item_id] = current_rank
        return ranks

    @staticmethod
    def _subject_stats(states: list[dict[str, Any]], subjects: list[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for subject in subjects:
            values = [state["scores"][subject] for state in states if subject in state["scores"]]
            rows.append(
                {
                    "subject": subject,
                    "count": len(values),
                    "average": ScoreController._round(mean(values)) if values else 0.0,
                    "highest": ScoreController._round(max(values)) if values else 0.0,
                    "lowest": ScoreController._round(min(values)) if values else 0.0,
                }
            )
        return rows

    @staticmethod
    def _display_row(state: dict[str, Any], subjects: list[str]) -> dict[str, Any]:
        return {
            "_id": state["student_id"],
            "姓名": state["name"],
            "学号": state["student_no"],
            "班级": state["class_name"],
            "总分": state["total"],
            "班级排名": state["class_rank"],
            "年级排名": state["grade_rank"],
            **{subject: state["scores"].get(subject) for subject in subjects},
        }

    @staticmethod
    def _exam_label(exam: Exam) -> str:
        date_text = exam.exam_date.isoformat() if exam.exam_date else "未设日期"
        return f"{exam.name} · {date_text}"

    @staticmethod
    def _round(value: float | None) -> float:
        return round(value or 0.0, 2)
