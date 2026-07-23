from __future__ import annotations

import sys
import tempfile
from datetime import date, datetime
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

        from controllers.attendance_controller import AttendanceController
        from controllers.moral_controller import MoralController
        from controllers.planner_controller import PlannerController, PlannerDataError
        from controllers.student_controller import StudentController
        from database.connection import engine
        from database.init_db import initialize_database

        try:
            initialize_database()
            students = StudentController()
            class_a = students.create_class({"name": "初三1班", "grade": "初三"})
            class_b = students.create_class({"name": "初三2班", "grade": "初三"})
            student_a = students.create_student(
                {"class_id": class_a, "name": "李明", "student_no": "001"}, []
            )
            students.create_student({"class_id": class_b, "name": "张婷", "student_no": "002"}, [])

            controller = PlannerController()
            classes = controller.list_classes()
            assert len(classes) == 2
            assert classes[0]["color"].startswith("#")
            assert classes[0]["soft_color"].startswith("#")
            controller.set_class_color(class_a, "#2D7DD2")
            class_a_data = next(item for item in controller.list_classes() if item["id"] == class_a)
            assert class_a_data["color"] == "#2D7DD2"

            course_id = controller.save_course(
                {
                    "class_id": class_a,
                    "weekday": 1,
                    "period": 1,
                    "subject": "语文",
                    "teacher": "王老师",
                    "location": "初三1班教室",
                    "start_time": "08:00",
                    "end_time": "08:45",
                }
            )
            updated_course_id = controller.save_course(
                {
                    "class_id": class_a,
                    "weekday": 1,
                    "period": 1,
                    "subject": "数学",
                    "teacher": "赵老师",
                    "location": "初三1班教室",
                    "start_time": "08:00",
                    "end_time": "08:45",
                }
            )
            assert updated_course_id == course_id
            courses = controller.list_courses(class_a)
            assert len(courses) == 1
            assert courses[0]["subject"] == "数学"
            other_course_id = controller.save_course(
                {
                    "class_id": class_a,
                    "weekday": 1,
                    "period": 2,
                    "subject": "英语",
                }
            )
            try:
                controller.save_course(
                    {
                        "class_id": class_a,
                        "weekday": 1,
                        "period": 2,
                        "subject": "数学",
                    },
                    course_id=course_id,
                )
            except PlannerDataError:
                pass
            else:
                raise AssertionError("Editing into an occupied course slot should be rejected.")

            target_date = date(2026, 9, 7)
            assert target_date.isoweekday() == 1
            class_event_id = controller.save_event(
                {
                    "class_id": class_a,
                    "event_date": target_date,
                    "title": "班会课",
                    "category": "班级活动",
                    "start_time": "16:00",
                    "end_time": "16:40",
                    "note": "总结本周纪律情况",
                }
            )
            controller.save_event(
                {
                    "class_id": None,
                    "event_date": target_date,
                    "title": "教研组会议",
                    "category": "会议",
                }
            )
            controller.save_event(
                {
                    "class_id": class_b,
                    "event_date": target_date,
                    "title": "初三2班班会",
                    "category": "班级活动",
                }
            )
            filtered_events = controller.list_events(target_date, target_date, class_a)
            assert {event["title"] for event in filtered_events} == {"班会课", "教研组会议"}
            assert len(controller.list_events(target_date, target_date)) == 3

            AttendanceController().create_record(
                {
                    "student_id": student_a,
                    "record_type": "病假",
                    "approval_status": "已批准",
                    "start_time": datetime(2026, 9, 6, 20, 0),
                    "end_time": datetime(2026, 9, 7, 8, 10),
                    "reason": "发热就医",
                }
            )
            MoralController().create_record(
                {
                    "student_id": student_a,
                    "record_date": target_date,
                    "category": "班级服务",
                    "title": "图书角整理",
                    "points": 2,
                }
            )
            overview = controller.get_daily_overview(class_a, target_date)
            assert overview["metrics"] == {
                "student_count": 1,
                "course_count": 2,
                "attendance_count": 1,
                "moral_count": 1,
            }
            assert len(overview["events"]) == 2
            assert len(overview["activity_trend"]) == 7
            assert overview["activity_trend"][-1]["attendance"] == 1
            assert overview["activity_trend"][-1]["moral"] == 1
            assert {item["kind"] for item in overview["recent_activity"]} == {"考勤", "德育"}

            try:
                controller.save_course(
                    {
                        "class_id": class_a,
                        "weekday": 1,
                        "period": 2,
                        "subject": "英语",
                        "start_time": "10:00",
                        "end_time": "09:00",
                    }
                )
            except PlannerDataError:
                pass
            else:
                raise AssertionError("An invalid course time range should be rejected.")

            controller.delete_course(course_id)
            controller.delete_course(other_course_id)
            assert controller.list_courses(class_a) == []
            controller.delete_event(class_event_id)
            assert {event["title"] for event in controller.list_events(target_date, target_date, class_a)} == {
                "教研组会议"
            }
        finally:
            engine.dispose()


if __name__ == "__main__":
    run()
    print("Planner smoke test passed.")
