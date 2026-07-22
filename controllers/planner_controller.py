from __future__ import annotations

import re
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from database.connection import get_session
from models.class_group import ClassGroup
from models.moral import MoralRecord
from models.reserved import LeaveRecord
from models.schedule import CalendarEvent, CourseSchedule
from models.student import Student
from models.teaching_schedule import AcademicSemester, SchedulePeriod, TeachingCourse, TeachingGroup
from utils.class_colors import CLASS_COLOR_CHOICES, class_color_info, is_supported_class_color


class PlannerDataError(ValueError):
    """Raised when a course or calendar item is invalid."""


class PlannerController:
    """Own the recurring course schedules and dated calendar events."""

    WEEKDAYS = (
        (1, "周一"),
        (2, "周二"),
        (3, "周三"),
        (4, "周四"),
        (5, "周五"),
    )
    PERIODS = tuple(range(1, 11))
    EVENT_CATEGORIES = ("班级活动", "考试安排", "家校沟通", "值日提醒", "会议", "其他")
    GLOBAL_EVENT_COLOR = {"name": "全局日程", "color": "#64748B", "soft": "#F1F5F9"}

    def list_classes(self) -> list[dict[str, Any]]:
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
            return [self._class_dict(class_group, counts.get(class_group.id, 0)) for class_group in classes]

    def set_class_color(self, class_id: int, color: str) -> None:
        if not is_supported_class_color(color):
            raise PlannerDataError("请选择预设的班级颜色。")
        with get_session() as session:
            class_group = self._active_class(session, class_id)
            class_group.color = color.upper()

    def list_courses(self, class_id: int) -> list[dict[str, Any]]:
        with get_session() as session:
            self._active_class(session, class_id)
            courses = session.scalars(
                select(CourseSchedule)
                .where(CourseSchedule.class_id == class_id, CourseSchedule.is_deleted.is_(False))
                .order_by(CourseSchedule.weekday, CourseSchedule.period)
            ).all()
            return [self._course_dict(course) for course in courses]

    def get_course(self, course_id: int) -> dict[str, Any]:
        with get_session() as session:
            course = session.scalar(
                select(CourseSchedule)
                .options(joinedload(CourseSchedule.class_group))
                .where(CourseSchedule.id == course_id, CourseSchedule.is_deleted.is_(False))
            )
            if course is None:
                raise PlannerDataError("未找到这节课程。")
            return self._course_dict(course)

    def save_course(self, data: dict[str, Any], course_id: int | None = None) -> int:
        values = self._course_values(data)
        with get_session() as session:
            self._active_class(session, values["class_id"])
            if course_id is not None:
                course = session.scalar(
                    select(CourseSchedule).where(
                        CourseSchedule.id == course_id,
                        CourseSchedule.is_deleted.is_(False),
                    )
                )
                if course is None:
                    raise PlannerDataError("未找到这节课程。")
                conflicting_course = session.scalar(
                    select(CourseSchedule).where(
                        CourseSchedule.class_id == values["class_id"],
                        CourseSchedule.weekday == values["weekday"],
                        CourseSchedule.period == values["period"],
                        CourseSchedule.id != course_id,
                        CourseSchedule.is_deleted.is_(False),
                    )
                )
                if conflicting_course is not None:
                    raise PlannerDataError("目标节次已有课程，请先编辑或删除该课程。")
            else:
                course = session.scalar(
                    select(CourseSchedule).where(
                        CourseSchedule.class_id == values["class_id"],
                        CourseSchedule.weekday == values["weekday"],
                        CourseSchedule.period == values["period"],
                        CourseSchedule.is_deleted.is_(False),
                    )
                )
            if course is None:
                course = CourseSchedule(**values)
                session.add(course)
                session.flush()
                return course.id
            for key, value in values.items():
                setattr(course, key, value)
            session.flush()
            return course.id

    def delete_course(self, course_id: int) -> None:
        with get_session() as session:
            course = session.scalar(
                select(CourseSchedule).where(CourseSchedule.id == course_id, CourseSchedule.is_deleted.is_(False))
            )
            if course is None:
                raise PlannerDataError("未找到这节课程。")
            course.is_deleted = True

    def list_events(
        self,
        start_date: date,
        end_date: date,
        class_id: int | None = None,
    ) -> list[dict[str, Any]]:
        with get_session() as session:
            stmt = (
                select(CalendarEvent)
                .options(joinedload(CalendarEvent.class_group))
                .where(
                    CalendarEvent.is_deleted.is_(False),
                    CalendarEvent.event_date >= start_date,
                    CalendarEvent.event_date <= end_date,
                )
                .order_by(CalendarEvent.event_date, CalendarEvent.start_time, CalendarEvent.id)
            )
            if class_id is not None:
                self._active_class(session, class_id)
                stmt = stmt.where(or_(CalendarEvent.class_id == class_id, CalendarEvent.class_id.is_(None)))
            return [self._event_dict(event) for event in session.scalars(stmt).all()]

    def get_event(self, event_id: int) -> dict[str, Any]:
        with get_session() as session:
            event = session.scalar(
                select(CalendarEvent)
                .options(joinedload(CalendarEvent.class_group))
                .where(CalendarEvent.id == event_id, CalendarEvent.is_deleted.is_(False))
            )
            if event is None:
                raise PlannerDataError("未找到这条日程。")
            return self._event_dict(event)

    def save_event(self, data: dict[str, Any], event_id: int | None = None) -> int:
        values = self._event_values(data)
        with get_session() as session:
            if values["class_id"] is not None:
                self._active_class(session, values["class_id"])
            if event_id is None:
                event = CalendarEvent(**values)
                session.add(event)
                session.flush()
                return event.id
            event = session.scalar(
                select(CalendarEvent).where(CalendarEvent.id == event_id, CalendarEvent.is_deleted.is_(False))
            )
            if event is None:
                raise PlannerDataError("未找到这条日程。")
            for key, value in values.items():
                setattr(event, key, value)
            session.flush()
            return event.id

    def delete_event(self, event_id: int) -> None:
        with get_session() as session:
            event = session.scalar(
                select(CalendarEvent).where(CalendarEvent.id == event_id, CalendarEvent.is_deleted.is_(False))
            )
            if event is None:
                raise PlannerDataError("未找到这条日程。")
            event.is_deleted = True

    def get_daily_overview(self, class_id: int, target_date: date) -> dict[str, Any]:
        with get_session() as session:
            class_group = self._active_class(session, class_id)
            student_count = int(
                session.scalar(
                    select(func.count(Student.id)).where(
                        Student.class_id == class_id,
                        Student.is_deleted.is_(False),
                    )
                )
                or 0
            )
            teaching_courses = session.scalars(
                select(TeachingCourse)
                .options(
                    joinedload(TeachingCourse.teaching_group),
                    joinedload(TeachingCourse.semester),
                    joinedload(TeachingCourse.period),
                )
                .join(TeachingCourse.teaching_group)
                .join(TeachingCourse.semester)
                .join(TeachingCourse.period)
                .where(
                    TeachingCourse.is_deleted.is_(False),
                    TeachingGroup.is_deleted.is_(False),
                    TeachingGroup.linked_class_id == class_id,
                    AcademicSemester.is_deleted.is_(False),
                    AcademicSemester.start_date <= target_date,
                    AcademicSemester.end_date >= target_date,
                    SchedulePeriod.is_deleted.is_(False),
                    TeachingCourse.weekday == target_date.isoweekday(),
                )
                .order_by(SchedulePeriod.sort_order, TeachingCourse.id)
            ).all()
            legacy_courses = session.scalars(
                select(CourseSchedule)
                .where(
                    CourseSchedule.class_id == class_id,
                    CourseSchedule.weekday == target_date.isoweekday(),
                    CourseSchedule.is_deleted.is_(False),
                )
                .order_by(CourseSchedule.period)
            ).all()
            # A linked teaching group is opt-in.  When it has an active term for the
            # chosen day, it replaces the pre-term class schedule; otherwise old data
            # remains visible until the teacher has set its migration term dates.
            courses = (
                [self._teaching_course_dict(course) for course in teaching_courses]
                if teaching_courses
                else [self._course_dict(course) for course in legacy_courses]
            )
            events = session.scalars(
                select(CalendarEvent)
                .options(joinedload(CalendarEvent.class_group))
                .where(
                    CalendarEvent.is_deleted.is_(False),
                    CalendarEvent.event_date == target_date,
                    or_(CalendarEvent.class_id == class_id, CalendarEvent.class_id.is_(None)),
                )
                .order_by(CalendarEvent.start_time, CalendarEvent.id)
            ).all()
            day_start = datetime.combine(target_date, time.min)
            day_end = datetime.combine(target_date, time.max)
            attendance_count = int(
                session.scalar(
                    select(func.count(LeaveRecord.id))
                    .join(Student, LeaveRecord.student_id == Student.id)
                    .where(
                        LeaveRecord.is_deleted.is_(False),
                        Student.is_deleted.is_(False),
                        Student.class_id == class_id,
                        LeaveRecord.start_time <= day_end,
                        LeaveRecord.end_time >= day_start,
                    )
                )
                or 0
            )
            moral_count = int(
                session.scalar(
                    select(func.count(MoralRecord.id))
                    .join(Student, MoralRecord.student_id == Student.id)
                    .where(
                        MoralRecord.is_deleted.is_(False),
                        Student.is_deleted.is_(False),
                        Student.class_id == class_id,
                        MoralRecord.record_date == target_date,
                    )
                )
                or 0
            )
            return {
                "class": self._class_dict(class_group, student_count),
                "courses": courses,
                "events": [self._event_dict(event) for event in events],
                "metrics": {
                    "student_count": student_count,
                    "course_count": len(courses),
                    "attendance_count": attendance_count,
                    "moral_count": moral_count,
                },
            }

    def _course_values(self, data: dict[str, Any]) -> dict[str, Any]:
        class_id = self._int_value(data.get("class_id"), "班级")
        weekday = self._int_value(data.get("weekday"), "星期")
        period = self._int_value(data.get("period"), "节次")
        if weekday not in {item[0] for item in self.WEEKDAYS}:
            raise PlannerDataError("请选择周一至周五。")
        if period not in self.PERIODS:
            raise PlannerDataError("请选择有效节次。")
        start_time = self._time_value(data.get("start_time"), "开始时间")
        end_time = self._time_value(data.get("end_time"), "结束时间")
        if start_time and end_time and end_time <= start_time:
            raise PlannerDataError("结束时间应晚于开始时间。")
        return {
            "class_id": class_id,
            "weekday": weekday,
            "period": period,
            "subject": self._required_text(data.get("subject"), "课程名称"),
            "teacher": self._optional_text(data.get("teacher")),
            "location": self._optional_text(data.get("location")),
            "start_time": start_time,
            "end_time": end_time,
            "note": self._optional_text(data.get("note")),
        }

    def _event_values(self, data: dict[str, Any]) -> dict[str, Any]:
        raw_class_id = data.get("class_id")
        class_id = None if raw_class_id in (None, "") else self._int_value(raw_class_id, "班级")
        event_date = data.get("event_date")
        if not isinstance(event_date, date):
            raise PlannerDataError("请选择有效日期。")
        category = str(data.get("category") or "").strip()
        if category not in self.EVENT_CATEGORIES:
            raise PlannerDataError("请选择有效的日程类别。")
        start_time = self._time_value(data.get("start_time"), "开始时间")
        end_time = self._time_value(data.get("end_time"), "结束时间")
        if start_time and end_time and end_time <= start_time:
            raise PlannerDataError("结束时间应晚于开始时间。")
        return {
            "class_id": class_id,
            "event_date": event_date,
            "title": self._required_text(data.get("title"), "日程名称"),
            "category": category,
            "start_time": start_time,
            "end_time": end_time,
            "note": self._optional_text(data.get("note")),
        }

    @staticmethod
    def _active_class(session, class_id: int) -> ClassGroup:
        class_group = session.scalar(
            select(ClassGroup).where(ClassGroup.id == class_id, ClassGroup.is_deleted.is_(False))
        )
        if class_group is None:
            raise PlannerDataError("请选择有效班级。")
        return class_group

    @staticmethod
    def _int_value(value: Any, label: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise PlannerDataError(f"请选择有效的{label}。") from exc

    @staticmethod
    def _required_text(value: Any, label: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise PlannerDataError(f"请填写{label}。")
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
            raise PlannerDataError(f"{label}应使用 HH:MM 格式。")
        return text

    @staticmethod
    def _class_dict(class_group: ClassGroup, student_count: int) -> dict[str, Any]:
        color = class_color_info(class_group.color, class_group.id)
        return {
            "id": class_group.id,
            "name": class_group.name,
            "grade": class_group.grade or "",
            "color": color["color"],
            "soft_color": color["soft"],
            "color_name": color["name"],
            "student_count": student_count,
        }

    @staticmethod
    def _course_dict(course: CourseSchedule) -> dict[str, Any]:
        return {
            "id": course.id,
            "class_id": course.class_id,
            "weekday": course.weekday,
            "period": course.period,
            "subject": course.subject,
            "teacher": course.teacher or "",
            "location": course.location or "",
            "start_time": course.start_time or "",
            "end_time": course.end_time or "",
            "note": course.note or "",
        }

    @staticmethod
    def _teaching_course_dict(course: TeachingCourse) -> dict[str, Any]:
        """Adapt a configurable independent timetable course for the daily desk."""

        return {
            "id": course.id,
            "class_id": course.teaching_group.linked_class_id,
            "weekday": course.weekday,
            "period": course.period.sort_order,
            "period_name": course.period.name,
            "subject": course.subject,
            "teacher": course.teacher or "",
            "location": course.location or "",
            "start_time": course.period.start_time or "",
            "end_time": course.period.end_time or "",
            "note": course.note or "",
            "teaching_group_name": course.teaching_group.name,
        }

    @classmethod
    def _event_dict(cls, event: CalendarEvent) -> dict[str, Any]:
        if event.class_group is None:
            color = cls.GLOBAL_EVENT_COLOR
            class_name = "全局日程"
        else:
            color = class_color_info(event.class_group.color, event.class_group.id)
            class_name = event.class_group.name
        time_text = "全天"
        if event.start_time and event.end_time:
            time_text = f"{event.start_time} - {event.end_time}"
        elif event.start_time:
            time_text = event.start_time
        return {
            "id": event.id,
            "class_id": event.class_id,
            "class_name": class_name,
            "class_color": color["color"],
            "class_soft_color": color["soft"],
            "event_date": event.event_date,
            "event_date_display": event.event_date.isoformat(),
            "title": event.title,
            "category": event.category,
            "start_time": event.start_time or "",
            "end_time": event.end_time or "",
            "time_display": time_text,
            "note": event.note or "",
        }
