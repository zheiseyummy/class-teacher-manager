from __future__ import annotations

import re
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from database.connection import get_session
from models.class_group import ClassGroup
from models.student import Student
from models.teaching_schedule import AcademicSemester, SchedulePeriod, TeachingCourse, TeachingGroup
from utils.class_colors import class_color_info, is_supported_class_color


class TeachingScheduleDataError(ValueError):
    """Raised when an independent timetable record is invalid."""


class TeachingScheduleController:
    """Manage independent teaching groups, bounded semesters and configurable periods."""

    WEEKDAYS = (
        (1, "周一"),
        (2, "周二"),
        (3, "周三"),
        (4, "周四"),
        (5, "周五"),
        (6, "周六"),
        (7, "周日"),
    )

    def list_teaching_groups(self) -> list[dict[str, Any]]:
        with get_session() as session:
            groups = session.scalars(
                select(TeachingGroup)
                .options(joinedload(TeachingGroup.linked_class_group))
                .where(TeachingGroup.is_deleted.is_(False))
                .order_by(TeachingGroup.name)
            ).all()
            course_counts = dict(
                session.execute(
                    select(TeachingCourse.teaching_group_id, func.count(TeachingCourse.id))
                    .where(TeachingCourse.is_deleted.is_(False))
                    .group_by(TeachingCourse.teaching_group_id)
                ).all()
            )
            return [self._group_dict(group, int(course_counts.get(group.id, 0))) for group in groups]

    def list_student_class_options(self) -> list[dict[str, Any]]:
        with get_session() as session:
            classes = session.scalars(
                select(ClassGroup)
                .where(ClassGroup.is_deleted.is_(False))
                .order_by(ClassGroup.grade, ClassGroup.name)
            ).all()
            counts = dict(
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
                    "student_count": int(counts.get(class_group.id, 0)),
                }
                for class_group in classes
            ]

    def get_teaching_group(self, group_id: int) -> dict[str, Any]:
        with get_session() as session:
            group = session.scalar(
                select(TeachingGroup)
                .options(joinedload(TeachingGroup.linked_class_group))
                .where(TeachingGroup.id == group_id, TeachingGroup.is_deleted.is_(False))
            )
            if group is None:
                raise TeachingScheduleDataError("未找到该教学班。")
            return self._group_dict(group, 0)

    def save_teaching_group(self, data: dict[str, Any], group_id: int | None = None) -> int:
        values = self._group_values(data)
        with get_session() as session:
            if values["linked_class_id"] is not None:
                self._active_student_class(session, values["linked_class_id"])
            duplicate = session.scalar(
                select(TeachingGroup).where(
                    TeachingGroup.name == values["name"],
                    TeachingGroup.is_deleted.is_(False),
                    TeachingGroup.id != (group_id or 0),
                )
            )
            if duplicate is not None:
                raise TeachingScheduleDataError("已有同名教学班，请换一个名称。")
            if group_id is None:
                group = TeachingGroup(**values)
                session.add(group)
                session.flush()
                return group.id
            group = self._active_teaching_group(session, group_id)
            for key, value in values.items():
                setattr(group, key, value)
            session.flush()
            return group.id

    def delete_teaching_group(self, group_id: int) -> None:
        with get_session() as session:
            group = self._active_teaching_group(session, group_id)
            has_courses = session.scalar(
                select(TeachingCourse.id)
                .where(
                    TeachingCourse.teaching_group_id == group_id,
                    TeachingCourse.is_deleted.is_(False),
                )
                .limit(1)
            )
            if has_courses is not None:
                raise TeachingScheduleDataError("该教学班仍有课程，请先删除或调整课程。")
            group.is_deleted = True

    def list_semesters(self) -> list[dict[str, Any]]:
        with get_session() as session:
            semesters = session.scalars(
                select(AcademicSemester)
                .where(AcademicSemester.is_deleted.is_(False))
                .order_by(AcademicSemester.is_current.desc(), AcademicSemester.start_date.desc(), AcademicSemester.id.desc())
            ).all()
            period_counts = dict(
                session.execute(
                    select(SchedulePeriod.semester_id, func.count(SchedulePeriod.id))
                    .where(SchedulePeriod.is_deleted.is_(False))
                    .group_by(SchedulePeriod.semester_id)
                ).all()
            )
            return [self._semester_dict(item, int(period_counts.get(item.id, 0))) for item in semesters]

    def get_semester(self, semester_id: int) -> dict[str, Any]:
        with get_session() as session:
            semester = self._active_semester(session, semester_id)
            return self._semester_dict(semester, 0)

    def save_semester(self, data: dict[str, Any], semester_id: int | None = None) -> int:
        values = self._semester_values(data)
        with get_session() as session:
            duplicate = session.scalar(
                select(AcademicSemester).where(
                    AcademicSemester.name == values["name"],
                    AcademicSemester.is_deleted.is_(False),
                    AcademicSemester.id != (semester_id or 0),
                )
            )
            if duplicate is not None:
                raise TeachingScheduleDataError("已有同名学期，请换一个名称。")
            overlap = session.scalar(
                select(AcademicSemester).where(
                    AcademicSemester.is_deleted.is_(False),
                    AcademicSemester.id != (semester_id or 0),
                    AcademicSemester.start_date <= values["end_date"],
                    AcademicSemester.end_date >= values["start_date"],
                )
            )
            if overlap is not None:
                raise TeachingScheduleDataError(f"学期日期与“{overlap.name}”重叠，请调整起止日期。")
            if values["is_current"]:
                for other in session.scalars(
                    select(AcademicSemester).where(AcademicSemester.is_deleted.is_(False))
                ).all():
                    other.is_current = False
            if semester_id is None:
                semester = AcademicSemester(**values)
                session.add(semester)
                session.flush()
                return semester.id
            semester = self._active_semester(session, semester_id)
            for key, value in values.items():
                setattr(semester, key, value)
            session.flush()
            return semester.id

    def delete_semester(self, semester_id: int) -> None:
        with get_session() as session:
            semester = self._active_semester(session, semester_id)
            has_courses = session.scalar(
                select(TeachingCourse.id)
                .where(TeachingCourse.semester_id == semester_id, TeachingCourse.is_deleted.is_(False))
                .limit(1)
            )
            if has_courses is not None:
                raise TeachingScheduleDataError("该学期仍有课程，请先删除或调整课程。")
            semester.is_deleted = True
            for period in session.scalars(
                select(SchedulePeriod).where(
                    SchedulePeriod.semester_id == semester_id,
                    SchedulePeriod.is_deleted.is_(False),
                )
            ).all():
                period.is_deleted = True

    def list_periods(self, semester_id: int) -> list[dict[str, Any]]:
        with get_session() as session:
            self._active_semester(session, semester_id)
            periods = session.scalars(
                select(SchedulePeriod)
                .where(SchedulePeriod.semester_id == semester_id, SchedulePeriod.is_deleted.is_(False))
                .order_by(SchedulePeriod.sort_order, SchedulePeriod.id)
            ).all()
            return [self._period_dict(period) for period in periods]

    def get_period(self, period_id: int) -> dict[str, Any]:
        with get_session() as session:
            period = session.scalar(
                select(SchedulePeriod)
                .options(joinedload(SchedulePeriod.semester))
                .where(SchedulePeriod.id == period_id, SchedulePeriod.is_deleted.is_(False))
            )
            if period is None:
                raise TeachingScheduleDataError("未找到该课时。")
            return self._period_dict(period)

    def save_period(self, data: dict[str, Any], period_id: int | None = None) -> int:
        values = self._period_values(data)
        with get_session() as session:
            self._active_semester(session, values["semester_id"])
            duplicate = session.scalar(
                select(SchedulePeriod).where(
                    SchedulePeriod.semester_id == values["semester_id"],
                    SchedulePeriod.sort_order == values["sort_order"],
                    SchedulePeriod.is_deleted.is_(False),
                    SchedulePeriod.id != (period_id or 0),
                )
            )
            if duplicate is not None:
                raise TeachingScheduleDataError("该学期已有相同排序的课时。")
            if period_id is None:
                period = SchedulePeriod(**values)
                session.add(period)
                session.flush()
                return period.id
            period = self._active_period(session, period_id)
            for key, value in values.items():
                setattr(period, key, value)
            session.flush()
            return period.id

    def delete_period(self, period_id: int) -> None:
        with get_session() as session:
            period = self._active_period(session, period_id)
            has_courses = session.scalar(
                select(TeachingCourse.id)
                .where(TeachingCourse.period_id == period_id, TeachingCourse.is_deleted.is_(False))
                .limit(1)
            )
            if has_courses is not None:
                raise TeachingScheduleDataError("该课时仍有课程，请先删除或调整课程。")
            period.is_deleted = True

    def list_courses(self, semester_id: int, teaching_group_id: int | None = None) -> list[dict[str, Any]]:
        with get_session() as session:
            self._active_semester(session, semester_id)
            if teaching_group_id is not None:
                self._active_teaching_group(session, teaching_group_id)
            stmt = (
                select(TeachingCourse)
                .options(
                    joinedload(TeachingCourse.teaching_group),
                    joinedload(TeachingCourse.semester),
                    joinedload(TeachingCourse.period),
                )
                .join(TeachingCourse.period)
                .where(
                    TeachingCourse.semester_id == semester_id,
                    TeachingCourse.is_deleted.is_(False),
                )
                .order_by(TeachingCourse.weekday, SchedulePeriod.sort_order, TeachingCourse.id)
            )
            if teaching_group_id is not None:
                stmt = stmt.where(TeachingCourse.teaching_group_id == teaching_group_id)
            return [self._course_dict(course) for course in session.scalars(stmt).all()]

    def get_course(self, course_id: int) -> dict[str, Any]:
        with get_session() as session:
            course = session.scalar(
                select(TeachingCourse)
                .options(
                    joinedload(TeachingCourse.teaching_group),
                    joinedload(TeachingCourse.semester),
                    joinedload(TeachingCourse.period),
                )
                .where(TeachingCourse.id == course_id, TeachingCourse.is_deleted.is_(False))
            )
            if course is None:
                raise TeachingScheduleDataError("未找到该课程。")
            return self._course_dict(course)

    def save_course(self, data: dict[str, Any], course_id: int | None = None) -> int:
        values = self._course_values(data)
        with get_session() as session:
            self._active_teaching_group(session, values["teaching_group_id"])
            self._active_semester(session, values["semester_id"])
            period = self._active_period(session, values["period_id"])
            if period.semester_id != values["semester_id"]:
                raise TeachingScheduleDataError("请选择当前学期配置的课时。")
            duplicate = session.scalar(
                select(TeachingCourse).where(
                    TeachingCourse.teaching_group_id == values["teaching_group_id"],
                    TeachingCourse.semester_id == values["semester_id"],
                    TeachingCourse.weekday == values["weekday"],
                    TeachingCourse.period_id == values["period_id"],
                    TeachingCourse.is_deleted.is_(False),
                    TeachingCourse.id != (course_id or 0),
                )
            )
            if course_id is None and duplicate is not None:
                for key, value in values.items():
                    setattr(duplicate, key, value)
                session.flush()
                return duplicate.id
            if course_id is not None and duplicate is not None:
                raise TeachingScheduleDataError("目标教学班、日期和课时已有课程。")
            if course_id is None:
                course = TeachingCourse(**values)
                session.add(course)
                session.flush()
                return course.id
            course = self._active_course(session, course_id)
            for key, value in values.items():
                setattr(course, key, value)
            session.flush()
            return course.id

    def delete_course(self, course_id: int) -> None:
        with get_session() as session:
            course = self._active_course(session, course_id)
            course.is_deleted = True

    def _group_values(self, data: dict[str, Any]) -> dict[str, Any]:
        raw_linked_class_id = data.get("linked_class_id")
        linked_class_id = None if raw_linked_class_id in (None, "") else self._int_value(raw_linked_class_id, "关联学生班级")
        raw_color = str(data.get("color") or "").strip().upper()
        if raw_color and not is_supported_class_color(raw_color):
            raise TeachingScheduleDataError("请选择预设的教学班颜色。")
        return {
            "name": self._required_text(data.get("name"), "教学班名称"),
            "color": raw_color or None,
            "linked_class_id": linked_class_id,
            "note": self._optional_text(data.get("note")),
        }

    def _semester_values(self, data: dict[str, Any]) -> dict[str, Any]:
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        if not isinstance(start_date, date) or not isinstance(end_date, date):
            raise TeachingScheduleDataError("请设置有效的学期起止日期。")
        if end_date < start_date:
            raise TeachingScheduleDataError("学期结束日期不能早于开始日期。")
        return {
            "name": self._required_text(data.get("name"), "学期名称"),
            "start_date": start_date,
            "end_date": end_date,
            "is_current": bool(data.get("is_current")),
            "note": self._optional_text(data.get("note")),
        }

    def _period_values(self, data: dict[str, Any]) -> dict[str, Any]:
        semester_id = self._int_value(data.get("semester_id"), "学期")
        sort_order = self._int_value(data.get("sort_order"), "课时排序")
        if sort_order < 1 or sort_order > 99:
            raise TeachingScheduleDataError("课时排序应在 1 到 99 之间。")
        start_time = self._time_value(data.get("start_time"), "开始时间")
        end_time = self._time_value(data.get("end_time"), "结束时间")
        if start_time is None or end_time is None:
            raise TeachingScheduleDataError("请为课时设置开始和结束时间。")
        if end_time <= start_time:
            raise TeachingScheduleDataError("结束时间应晚于开始时间。")
        return {
            "semester_id": semester_id,
            "sort_order": sort_order,
            "name": self._required_text(data.get("name"), "课时名称"),
            "start_time": start_time,
            "end_time": end_time,
            "note": self._optional_text(data.get("note")),
        }

    def _course_values(self, data: dict[str, Any]) -> dict[str, Any]:
        weekday = self._int_value(data.get("weekday"), "星期")
        if weekday not in {item[0] for item in self.WEEKDAYS}:
            raise TeachingScheduleDataError("请选择周一至周日。")
        return {
            "teaching_group_id": self._int_value(data.get("teaching_group_id"), "教学班"),
            "semester_id": self._int_value(data.get("semester_id"), "学期"),
            "period_id": self._int_value(data.get("period_id"), "课时"),
            "weekday": weekday,
            "subject": self._required_text(data.get("subject"), "课程名称"),
            "teacher": self._optional_text(data.get("teacher")),
            "location": self._optional_text(data.get("location")),
            "note": self._optional_text(data.get("note")),
        }

    @staticmethod
    def _active_teaching_group(session, group_id: int) -> TeachingGroup:
        group = session.scalar(
            select(TeachingGroup).where(TeachingGroup.id == group_id, TeachingGroup.is_deleted.is_(False))
        )
        if group is None:
            raise TeachingScheduleDataError("请选择有效的教学班。")
        return group

    @staticmethod
    def _active_student_class(session, class_id: int) -> ClassGroup:
        class_group = session.scalar(
            select(ClassGroup).where(ClassGroup.id == class_id, ClassGroup.is_deleted.is_(False))
        )
        if class_group is None:
            raise TeachingScheduleDataError("请选择有效的学生班级。")
        return class_group

    @staticmethod
    def _active_semester(session, semester_id: int) -> AcademicSemester:
        semester = session.scalar(
            select(AcademicSemester).where(
                AcademicSemester.id == semester_id,
                AcademicSemester.is_deleted.is_(False),
            )
        )
        if semester is None:
            raise TeachingScheduleDataError("请选择有效的学期。")
        return semester

    @staticmethod
    def _active_period(session, period_id: int) -> SchedulePeriod:
        period = session.scalar(
            select(SchedulePeriod).where(SchedulePeriod.id == period_id, SchedulePeriod.is_deleted.is_(False))
        )
        if period is None:
            raise TeachingScheduleDataError("请选择有效的课时。")
        return period

    @staticmethod
    def _active_course(session, course_id: int) -> TeachingCourse:
        course = session.scalar(
            select(TeachingCourse).where(TeachingCourse.id == course_id, TeachingCourse.is_deleted.is_(False))
        )
        if course is None:
            raise TeachingScheduleDataError("未找到该课程。")
        return course

    @staticmethod
    def _int_value(value: Any, label: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise TeachingScheduleDataError(f"请选择有效的{label}。") from exc

    @staticmethod
    def _required_text(value: Any, label: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise TeachingScheduleDataError(f"请填写{label}。")
        return text

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _time_value(value: Any, label: str) -> str | None:
        text = str(value or "").strip()
        if not text:
            return None
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", text):
            raise TeachingScheduleDataError(f"{label}应使用 HH:MM 格式。")
        return text

    @staticmethod
    def _group_dict(group: TeachingGroup, course_count: int) -> dict[str, Any]:
        color = class_color_info(group.color, group.id)
        linked_class = group.linked_class_group
        return {
            "id": group.id,
            "name": group.name,
            "color": color["color"],
            "soft_color": color["soft"],
            "color_name": color["name"],
            "linked_class_id": group.linked_class_id,
            "linked_class_name": linked_class.name if linked_class and not linked_class.is_deleted else "",
            "note": group.note or "",
            "course_count": course_count,
        }

    @staticmethod
    def _semester_dict(semester: AcademicSemester, period_count: int) -> dict[str, Any]:
        return {
            "id": semester.id,
            "name": semester.name,
            "start_date": semester.start_date,
            "end_date": semester.end_date,
            "date_range_display": f"{semester.start_date.isoformat()} 至 {semester.end_date.isoformat()}",
            "is_current": semester.is_current,
            "note": semester.note or "",
            "period_count": period_count,
        }

    @staticmethod
    def _period_dict(period: SchedulePeriod) -> dict[str, Any]:
        return {
            "id": period.id,
            "semester_id": period.semester_id,
            "sort_order": period.sort_order,
            "name": period.name,
            "start_time": period.start_time or "",
            "end_time": period.end_time or "",
            "time_display": f"{period.start_time or '--:--'} - {period.end_time or '--:--'}",
            "note": period.note or "",
        }

    @staticmethod
    def _course_dict(course: TeachingCourse) -> dict[str, Any]:
        color = class_color_info(course.teaching_group.color, course.teaching_group.id)
        period = course.period
        return {
            "id": course.id,
            "teaching_group_id": course.teaching_group_id,
            "teaching_group_name": course.teaching_group.name,
            "group_color": color["color"],
            "group_soft_color": color["soft"],
            "semester_id": course.semester_id,
            "semester_name": course.semester.name,
            "period_id": course.period_id,
            "period_order": period.sort_order,
            "period_name": period.name,
            "period_start_time": period.start_time or "",
            "period_end_time": period.end_time or "",
            "weekday": course.weekday,
            "subject": course.subject,
            "teacher": course.teacher or "",
            "location": course.location or "",
            "note": course.note or "",
        }
