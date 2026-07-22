from __future__ import annotations

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config


def run() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        config.DATA_DIR = root / "data"
        config.BACKUP_DIR = root / "backups"
        config.DATABASE_PATH = config.DATA_DIR / "class_manager.db"
        config.DATABASE_URL = f"sqlite:///{config.DATABASE_PATH.as_posix()}"

        from controllers.planner_controller import PlannerController
        from controllers.student_controller import StudentController
        from controllers.teaching_schedule_controller import (
            TeachingScheduleController,
            TeachingScheduleDataError,
        )
        from database.connection import engine
        from database.init_db import initialize_database

        try:
            initialize_database()
            students = StudentController()
            student_class_id = students.create_class({"name": "初三1班", "grade": "初三"})
            PlannerController().save_course(
                {
                    "class_id": student_class_id,
                    "weekday": 1,
                    "period": 1,
                    "subject": "语文",
                    "teacher": "王老师",
                    "start_time": "08:00",
                    "end_time": "08:45",
                }
            )

            initialize_database()
            controller = TeachingScheduleController()
            migrated_semester = next(
                item for item in controller.list_semesters() if item["name"] == "旧版课程表（请设置日期）"
            )
            migrated_courses = controller.list_courses(migrated_semester["id"])
            assert len(migrated_courses) == 1
            assert migrated_courses[0]["subject"] == "语文"
            assert migrated_courses[0]["teaching_group_name"] == "初三1班"

            target_date = date.today()
            while target_date.isoweekday() != 1:
                target_date += timedelta(days=1)
            legacy_overview = PlannerController().get_daily_overview(student_class_id, target_date)
            assert [course["subject"] for course in legacy_overview["courses"]] == ["语文"]

            linked_semester_id = controller.save_semester(
                {
                    "name": f"{target_date.year} 关联班级测试学期",
                    "start_date": target_date - timedelta(days=7),
                    "end_date": target_date + timedelta(days=7),
                }
            )
            linked_group_id = controller.save_teaching_group(
                {
                    "name": "初三1班日常课表",
                    "color": "#12966D",
                    "linked_class_id": student_class_id,
                }
            )
            linked_period_id = controller.save_period(
                {
                    "semester_id": linked_semester_id,
                    "sort_order": 1,
                    "name": "第一节",
                    "start_time": "08:00",
                    "end_time": "08:45",
                }
            )
            controller.save_course(
                {
                    "teaching_group_id": linked_group_id,
                    "semester_id": linked_semester_id,
                    "period_id": linked_period_id,
                    "weekday": 1,
                    "subject": "现代语文",
                    "teacher": "王老师",
                }
            )
            linked_overview = PlannerController().get_daily_overview(student_class_id, target_date)
            assert [course["subject"] for course in linked_overview["courses"]] == ["现代语文"]

            next_year = date.today().year + 1
            semester_id = controller.save_semester(
                {
                    "name": f"{next_year} 秋季学期",
                    "start_date": date(next_year, 9, 1),
                    "end_date": date(next_year + 1, 1, 31),
                    "is_current": True,
                }
            )
            try:
                controller.save_semester(
                    {
                        "name": "重复日期学期",
                        "start_date": date(next_year, 12, 1),
                        "end_date": date(next_year + 1, 2, 1),
                    }
                )
            except TeachingScheduleDataError:
                pass
            else:
                raise AssertionError("Overlapping semester dates should be rejected.")

            group_a = controller.save_teaching_group(
                {"name": "九年级竞赛辅导班", "color": "#2D7DD2"}
            )
            group_b = controller.save_teaching_group(
                {"name": "七年级英语社团", "color": "#D97706"}
            )
            groups = controller.list_teaching_groups()
            independent_group = next(item for item in groups if item["id"] == group_a)
            assert independent_group["linked_class_id"] is None
            assert independent_group["color"] == "#2D7DD2"

            morning_period = controller.save_period(
                {
                    "semester_id": semester_id,
                    "sort_order": 1,
                    "name": "早读",
                    "start_time": "07:30",
                    "end_time": "07:55",
                }
            )
            first_period = controller.save_period(
                {
                    "semester_id": semester_id,
                    "sort_order": 2,
                    "name": "第一节",
                    "start_time": "08:05",
                    "end_time": "08:45",
                }
            )
            assert [item["name"] for item in controller.list_periods(semester_id)] == ["早读", "第一节"]

            course_id = controller.save_course(
                {
                    "teaching_group_id": group_a,
                    "semester_id": semester_id,
                    "period_id": morning_period,
                    "weekday": 1,
                    "subject": "数学竞赛",
                    "teacher": "李老师",
                    "location": "创新教室",
                }
            )
            assert controller.save_course(
                {
                    "teaching_group_id": group_a,
                    "semester_id": semester_id,
                    "period_id": morning_period,
                    "weekday": 1,
                    "subject": "数学竞赛强化",
                    "teacher": "李老师",
                }
            ) == course_id
            controller.save_course(
                {
                    "teaching_group_id": group_b,
                    "semester_id": semester_id,
                    "period_id": morning_period,
                    "weekday": 1,
                    "subject": "英语口语",
                    "teacher": "周老师",
                }
            )
            controller.save_course(
                {
                    "teaching_group_id": group_a,
                    "semester_id": semester_id,
                    "period_id": first_period,
                    "weekday": 3,
                    "subject": "几何专题",
                }
            )
            all_courses = controller.list_courses(semester_id)
            assert len(all_courses) == 3
            assert {course["teaching_group_name"] for course in all_courses} == {
                "九年级竞赛辅导班",
                "七年级英语社团",
            }
            assert controller.list_courses(semester_id, group_a)[0]["subject"] == "数学竞赛强化"

            try:
                controller.delete_period(morning_period)
            except TeachingScheduleDataError:
                pass
            else:
                raise AssertionError("A period with active courses should not be deleted.")
            try:
                controller.delete_teaching_group(group_a)
            except TeachingScheduleDataError:
                pass
            else:
                raise AssertionError("A group with active courses should not be deleted.")
        finally:
            engine.dispose()


if __name__ == "__main__":
    run()
    print("Independent teaching schedule smoke test passed.")
