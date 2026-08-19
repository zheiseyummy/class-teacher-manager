from __future__ import annotations

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config


def run() -> tuple[Path, Path, Path]:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        config.DATA_DIR = root / "data"
        config.BACKUP_DIR = root / "backups"
        config.DATABASE_PATH = config.DATA_DIR / "class_manager.db"
        config.DATABASE_URL = f"sqlite:///{config.DATABASE_PATH.as_posix()}"

        from PySide6.QtWidgets import QApplication

        from controllers.student_controller import StudentController
        from controllers.teacher_profile_controller import TeacherProfileController
        from controllers.teaching_schedule_controller import TeachingScheduleController
        from database.connection import engine
        from database.init_db import initialize_database
        from views.main_window import MainWindow
        from views.teacher_profile_dialog import TeacherProfileDialog

        output_root = Path(__file__).resolve().parents[1] / "docs"
        window_path = output_root / "visual-qa-teacher-footer.png"
        dialog_path = output_root / "visual-qa-teacher-profile.png"
        compact_dialog_path = output_root / "visual-qa-teacher-profile-compact.png"
        window: MainWindow | None = None
        dialog: TeacherProfileDialog | None = None
        app = QApplication.instance() or QApplication([])
        try:
            initialize_database()
            students = StudentController()
            class_ids = [
                students.create_class(
                    {
                        "name": f"初三{index}班",
                        "grade": "初三",
                        "school_year": "2026-2027",
                    }
                )
                for index in range(1, 5)
            ]
            semester_id = TeachingScheduleController().save_semester(
                {
                    "name": "2026-2027 学年上学期",
                    "start_date": date(2026, 9, 1),
                    "end_date": date(2027, 1, 31),
                    "is_current": True,
                }
            )
            profile_controller = TeacherProfileController()
            profile_controller.save_profile(
                {
                    "teacher_name": "李老师",
                    "school_name": "示例中学",
                    "subjects": ["语文", "道德与法治"],
                    "common_class_ids": class_ids,
                    "default_semester_id": semester_id,
                    "personal_mark": "",
                }
            )

            window = MainWindow()
            window.resize(1440, 900)
            window.show()
            app.processEvents()
            assert window.grab().save(str(window_path))

            dialog = TeacherProfileDialog(profile_controller, window)
            dialog.show()
            app.processEvents()
            assert dialog.grab().save(str(dialog_path))
            dialog.resize(dialog.minimumSize())
            app.processEvents()
            assert dialog.grab().save(str(compact_dialog_path))
            return window_path, dialog_path, compact_dialog_path
        finally:
            if dialog is not None:
                dialog.close()
            if window is not None:
                window.close()
            app.processEvents()
            engine.dispose()


if __name__ == "__main__":
    for output in run():
        print(output)
