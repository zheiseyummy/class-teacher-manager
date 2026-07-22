from __future__ import annotations

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config


def run() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        config.DATA_DIR = root / "data"
        config.BACKUP_DIR = root / "backups"
        config.DATABASE_PATH = config.DATA_DIR / "class_manager.db"
        config.DATABASE_URL = f"sqlite:///{config.DATABASE_PATH.as_posix()}"

        from PySide6.QtWidgets import QApplication

        from controllers.teaching_schedule_controller import TeachingScheduleController
        from database.connection import engine
        from database.init_db import initialize_database
        from views.main_window import MainWindow
        from views.schedule_period_dialog import SchedulePeriodDialog
        from views.semester_dialog import SemesterDialog
        from views.semester_period_manager_dialog import SemesterPeriodManagerDialog
        from views.teaching_course_dialog import TeachingCourseDialog
        from views.teaching_group_manager_dialog import TeachingGroupManagerDialog

        try:
            initialize_database()
            controller = TeachingScheduleController()
            semester_id = controller.save_semester(
                {
                    "name": "2026 秋季学期",
                    "start_date": date(2026, 9, 1),
                    "end_date": date(2027, 1, 31),
                    "is_current": True,
                }
            )
            group_id = controller.save_teaching_group(
                {"name": "九年级数学提高班", "color": "#12966D"}
            )
            period_1 = controller.save_period(
                {
                    "semester_id": semester_id,
                    "sort_order": 1,
                    "name": "早读",
                    "start_time": "07:30",
                    "end_time": "07:55",
                }
            )
            controller.save_period(
                {
                    "semester_id": semester_id,
                    "sort_order": 2,
                    "name": "第一节",
                    "start_time": "08:05",
                    "end_time": "08:45",
                }
            )
            controller.save_course(
                {
                    "semester_id": semester_id,
                    "teaching_group_id": group_id,
                    "weekday": 1,
                    "period_id": period_1,
                    "subject": "数学竞赛",
                    "teacher": "李老师",
                }
            )

            app = QApplication.instance() or QApplication([])
            window = MainWindow()
            window.resize(1360, 860)
            window.menu.setCurrentRow(6)
            window.show()
            app.processEvents()

            schedule_view = window.planner_view.schedule_view
            assert schedule_view.semester_box.currentData() == semester_id
            assert schedule_view.course_table.rowCount() == 2
            assert schedule_view.course_table.columnCount() == 7
            assert schedule_view.course_table.item(0, 0) is not None

            group_manager = TeachingGroupManagerDialog(controller, parent=window)
            period_manager = SemesterPeriodManagerDialog(controller, parent=window)
            semester_dialog = SemesterDialog(controller, semester_id=semester_id, parent=window)
            period_dialog = SchedulePeriodDialog(
                controller,
                semester_id=semester_id,
                period_id=period_1,
                parent=window,
            )
            course_dialog = TeachingCourseDialog(
                controller,
                initial_semester_id=semester_id,
                initial_group_id=group_id,
                initial_period_id=period_1,
                parent=window,
            )
            assert group_manager.table.rowCount() == 1
            assert period_manager.semester_table.rowCount() == 1
            assert semester_dialog.name_input.text() == "2026 秋季学期"
            assert period_dialog.name_input.text() == "早读"
            assert course_dialog.period_box.count() == 2
            group_manager.close()
            period_manager.close()
            semester_dialog.close()
            period_dialog.close()
            course_dialog.close()
            window.close()
            app.quit()
        finally:
            engine.dispose()


if __name__ == "__main__":
    run()
    print("Independent teaching schedule UI smoke test passed.")
