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

        from controllers.backup_controller import BackupController
        from controllers.teaching_schedule_controller import TeachingScheduleController
        from database.connection import engine
        from database.init_db import initialize_database
        from views.main_window import MainWindow

        try:
            initialize_database()
            semester_id = TeachingScheduleController().save_semester(
                {
                    "name": "2026 秋季学期",
                    "start_date": date(2026, 9, 1),
                    "end_date": date(2027, 1, 31),
                    "is_current": True,
                }
            )
            app = QApplication.instance() or QApplication([])
            window = MainWindow()
            window.resize(1360, 860)
            window.menu.setCurrentRow(7)
            window.show()
            app.processEvents()

            backup_view = window.backup_view
            assert window.menu.item(7).text() == "数据备份与恢复"
            assert backup_view.semester_box.currentData() == semester_id
            assert backup_view.auto_enabled.isChecked() is False
            assert backup_view.history_table.columnCount() == 5

            archive = BackupController().create_full_backup()
            backup_view.refresh_all()
            assert archive.is_file()
            assert backup_view.history_table.rowCount() >= 1
            assert backup_view.history_table.item(0, 0) is not None

            window.close()
            app.quit()
        finally:
            engine.dispose()


if __name__ == "__main__":
    run()
    print("Backup center UI smoke test passed.")
