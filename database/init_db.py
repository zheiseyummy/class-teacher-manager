from __future__ import annotations

from database.connection import engine
from models.base import Base

# Import models so SQLAlchemy registers every table before create_all().
from models import backup_record  # noqa: F401
from models import class_group  # noqa: F401
from models import exam  # noqa: F401
from models import guardian  # noqa: F401
from models import import_record  # noqa: F401
from models import moral  # noqa: F401
from models import quality  # noqa: F401
from models import reserved  # noqa: F401
from models import schedule  # noqa: F401
from models import student  # noqa: F401
from models import teaching_schedule  # noqa: F401


def initialize_database() -> None:
    """Create SQLite tables for the current application version."""
    Base.metadata.create_all(bind=engine)
    _apply_sqlite_compatibility_migrations()
    _migrate_legacy_course_schedules()
    # create_all() does not add indexes to already-created SQLite tables.
    for table in Base.metadata.sorted_tables:
        for index in table.indexes:
            index.create(bind=engine, checkfirst=True)


def _apply_sqlite_compatibility_migrations() -> None:
    """Add small additive columns when a local database predates the current model."""

    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as connection:
        table_names = {
            row[0]
            for row in connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE type = 'table'").all()
        }
        if "classes" not in table_names:
            return
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(classes)").all()}
        if "color" not in columns:
            connection.exec_driver_sql("ALTER TABLE classes ADD COLUMN color VARCHAR(16)")


def _migrate_legacy_course_schedules() -> None:
    """Preserve schedules created before independent teaching groups were introduced."""

    from datetime import date

    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    from database.connection import get_session
    from models.schedule import CourseSchedule
    from models.teaching_schedule import AcademicSemester, SchedulePeriod, TeachingCourse, TeachingGroup

    with get_session() as session:
        legacy_courses = session.scalars(
            select(CourseSchedule)
            .options(joinedload(CourseSchedule.class_group))
            .where(CourseSchedule.is_deleted.is_(False))
            .order_by(CourseSchedule.class_id, CourseSchedule.weekday, CourseSchedule.period)
        ).all()
        if not legacy_courses:
            return
        if session.scalar(select(TeachingCourse.id).where(TeachingCourse.is_deleted.is_(False)).limit(1)) is not None:
            return

        semester = session.scalar(
            select(AcademicSemester).where(
                AcademicSemester.name == "旧版课程表（请设置日期）",
                AcademicSemester.is_deleted.is_(False),
            )
        )
        if semester is None:
            semester = AcademicSemester(
                name="旧版课程表（请设置日期）",
                # Earlier schedules had no term dates.  Keep this placeholder out
                # of normal school years so it never blocks a new term's date range.
                start_date=date(2000, 1, 1),
                end_date=date(2000, 12, 31),
                is_current=False,
                note="由早期班级课程表自动迁移，请按实际学期调整日期。",
            )
            session.add(semester)
            session.flush()

        groups_by_class_id: dict[int, TeachingGroup] = {}
        periods_by_order: dict[int, SchedulePeriod] = {}
        for legacy_course in legacy_courses:
            class_group = legacy_course.class_group
            group = groups_by_class_id.get(legacy_course.class_id)
            if group is None:
                group = session.scalar(
                    select(TeachingGroup).where(
                        TeachingGroup.linked_class_id == legacy_course.class_id,
                        TeachingGroup.is_deleted.is_(False),
                    )
                )
                if group is None:
                    group = TeachingGroup(
                        name=class_group.name,
                        color=class_group.color,
                        linked_class_id=legacy_course.class_id,
                        note="由早期班级课程表自动迁移。",
                    )
                    session.add(group)
                    session.flush()
                groups_by_class_id[legacy_course.class_id] = group

            period = periods_by_order.get(legacy_course.period)
            if period is None:
                period = SchedulePeriod(
                    semester_id=semester.id,
                    sort_order=legacy_course.period,
                    name=f"第 {legacy_course.period} 节",
                    start_time=legacy_course.start_time,
                    end_time=legacy_course.end_time,
                )
                session.add(period)
                session.flush()
                periods_by_order[legacy_course.period] = period

            session.add(
                TeachingCourse(
                    teaching_group_id=group.id,
                    semester_id=semester.id,
                    period_id=period.id,
                    weekday=legacy_course.weekday,
                    subject=legacy_course.subject,
                    teacher=legacy_course.teacher,
                    location=legacy_course.location,
                    note=legacy_course.note,
                )
            )
