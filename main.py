from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from config import APP_NAME, APP_VERSION, SCORE_IMPORT_TEMPLATE, STUDENT_IMPORT_TEMPLATE
from database.init_db import initialize_database
from utils.excel_service import ensure_student_import_template
from utils.score_excel_import import ensure_score_import_template
from views.main_window import MainWindow


def main() -> int:
    """Application entry point."""
    initialize_database()
    ensure_student_import_template(STUDENT_IMPORT_TEMPLATE)
    ensure_score_import_template(SCORE_IMPORT_TEMPLATE)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("LocalClassManager")

    window = MainWindow()
    window.show()
    QTimer.singleShot(0, window.show_teacher_setup_if_needed)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
