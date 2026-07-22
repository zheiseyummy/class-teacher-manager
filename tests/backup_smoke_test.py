from __future__ import annotations

import sys
import tempfile
import zipfile
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

        from controllers.backup_controller import BackupController
        from controllers.student_controller import StudentController
        from controllers.teaching_schedule_controller import TeachingScheduleController
        from database.connection import engine
        from database.init_db import initialize_database

        try:
            initialize_database()
            students = StudentController()
            class_id = students.create_class({"name": "初三1班", "grade": "初三"})
            students.create_student({"class_id": class_id, "name": "李明", "student_no": "001"}, [])

            schedules = TeachingScheduleController()
            semester_id = schedules.save_semester(
                {
                    "name": "2026-2027 学年第一学期",
                    "start_date": date(2026, 9, 1),
                    "end_date": date(2027, 1, 31),
                    "is_current": True,
                }
            )
            group_id = schedules.save_teaching_group(
                {"name": "初三1班日常课程", "color": "#12966D", "linked_class_id": class_id}
            )
            period_id = schedules.save_period(
                {
                    "semester_id": semester_id,
                    "sort_order": 1,
                    "name": "第一节",
                    "start_time": "08:00",
                    "end_time": "08:45",
                }
            )
            schedules.save_course(
                {
                    "semester_id": semester_id,
                    "teaching_group_id": group_id,
                    "period_id": period_id,
                    "weekday": 1,
                    "subject": "语文",
                }
            )

            controller = BackupController()
            full_archive = controller.create_full_backup()
            assert full_archive.is_file()
            full_info = controller.inspect_backup(full_archive)
            assert full_info["kind"] == "full"
            with zipfile.ZipFile(full_archive) as archive:
                assert {"manifest.json", "database/class_manager.db"}.issubset(archive.namelist())

            students.create_student({"class_id": class_id, "name": "王婷", "student_no": "002"}, [])
            assert students.count_students() == 2
            restore_result = controller.restore_backup(full_archive)
            assert Path(restore_result["safety_backup"]).is_file()
            assert students.count_students() == 1
            assert any(item["action"] == "restore" for item in controller.list_records())

            semester_archive = controller.create_semester_archive(semester_id)
            semester_info = controller.inspect_backup(semester_archive)
            assert semester_info["kind"] == "semester_archive"
            assert semester_info["semester"]["name"] == "2026-2027 学年第一学期"
            assert semester_info["semester"]["summary"]["teaching_courses"] == 1

            settings = controller.save_settings(
                {
                    "auto_enabled": True,
                    "schedule_frequency": "daily",
                    "schedule_time": "18:00",
                    "schedule_weekday": 1,
                    "destination_dir": str(root / "scheduled"),
                }
            )
            assert settings["auto_enabled"] is True
            scheduled_archive = controller.run_scheduled_backup(datetime(2026, 10, 8, 18, 1))
            assert scheduled_archive is not None and scheduled_archive.is_file()
            assert controller.run_scheduled_backup(datetime(2026, 10, 8, 18, 2)) is None
        finally:
            engine.dispose()


if __name__ == "__main__":
    run()
    print("Backup and restore smoke test passed.")
