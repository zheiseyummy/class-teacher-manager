from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from config import SCORE_IMPORT_TEMPLATE, STUDENT_IMPORT_TEMPLATE
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
    app.setApplicationName("班主任综合管理系统")
    app.setOrganizationName("LocalClassManager")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
