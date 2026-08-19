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

        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication, QDialog

        from controllers.backup_controller import BackupController
        from controllers.student_controller import StudentController
        from controllers.teacher_profile_controller import TeacherProfileController
        from controllers.teaching_schedule_controller import TeachingScheduleController
        from database.connection import engine
        from database.init_db import initialize_database
        from views.main_window import MainWindow
        from views.teacher_profile_dialog import TeacherProfileDialog

        window: MainWindow | None = None
        app = QApplication.instance() or QApplication([])
        try:
            initialize_database()
            students = StudentController()
            class_id = students.create_class(
                {"name": "初三1班", "grade": "初三", "school_year": "2026-2027"}
            )
            semesters = TeachingScheduleController()
            semester_id = semesters.save_semester(
                {
                    "name": "2026-2027 学年上学期",
                    "start_date": date(2026, 9, 1),
                    "end_date": date(2027, 1, 31),
                    "is_current": True,
                }
            )

            controller = TeacherProfileController()
            empty = controller.get_profile()
            assert empty["onboarding_completed"] is False
            assert empty["greeting"] == "您好，老师！"

            window = MainWindow()
            window.show()
            onboarding_closed: list[bool] = []

            def close_onboarding() -> None:
                active_dialog = app.activeModalWidget()
                if isinstance(active_dialog, TeacherProfileDialog):
                    onboarding_closed.append(True)
                    active_dialog.reject()

            QTimer.singleShot(0, close_onboarding)
            window.show_teacher_setup_if_needed()
            assert onboarding_closed == [True]
            assert controller.get_profile()["onboarding_completed"] is True

            saved = controller.save_profile(
                {
                    "teacher_name": "李",
                    "school_name": "示例中学",
                    "subjects": ["语文", "体育", "语文"],
                    "common_class_ids": [class_id],
                    "default_semester_id": semester_id,
                    "personal_mark": "",
                }
            )
            assert saved["greeting"] == "您好，李老师！"
            assert saved["personal_mark_display"] == "李老师 · 个人教学工作台"
            assert saved["subjects"] == ["语文", "体育"]
            assert saved["common_class_ids"] == [class_id]

            persisted = TeacherProfileController().get_profile()
            assert persisted["school_name"] == "示例中学"
            assert persisted["default_semester_id"] == semester_id

            archive = BackupController().create_full_backup()
            manifest = BackupController().inspect_backup(archive)["manifest"]
            assert manifest["app_version"] == config.APP_VERSION

            window._refresh_teacher_profile()
            app.processEvents()
            assert window.page_title.text() == "您好，李老师！"
            assert window.sidebar_version.text() == f"本地办公版  ·  {config.APP_VERSION_LABEL}"
            assert window.sidebar_personal_mark.text() == "李老师 · 个人教学工作台"

            dialog = TeacherProfileDialog(controller, window)
            assert dialog.name_input.text() == "李"
            dialog.name_input.setText("王老师")
            dialog.mark_input.setText("王老师 · 九年级教学")
            dialog._save()
            assert dialog.result() == QDialog.DialogCode.Accepted
            window._refresh_teacher_profile()
            assert window.page_title.text() == "您好，王老师！"
            assert window.sidebar_personal_mark.text() == "王老师 · 九年级教学"
        finally:
            if window is not None:
                window.close()
            app.processEvents()
            engine.dispose()


if __name__ == "__main__":
    run()
    print("Teacher profile and version smoke test passed.")
