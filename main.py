from __future__ import annotations

import ctypes
import platform
import sys
import traceback
from datetime import datetime
from pathlib import Path

from config import (
    APP_NAME,
    APP_VERSION,
    RESOURCE_DIR,
    SCORE_IMPORT_TEMPLATE,
    STUDENT_IMPORT_TEMPLATE,
)


def _write_startup_diagnostic(error: BaseException) -> Path | None:
    """Write a Qt-independent diagnostic when the desktop runtime cannot load."""
    app_dir = (
        Path(sys.executable).resolve().parent
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parent
    )
    fallback_dir = Path.home() / "ClassTeacherManager"
    details = "\n".join(
        (
            f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}",
            f"Application: {APP_NAME} {APP_VERSION}",
            f"Windows: {platform.platform()}",
            f"Architecture: {platform.machine()} / {platform.architecture()[0]}",
            f"Python: {sys.version}",
            f"Executable: {sys.executable}",
            "",
            "Exception:",
            "".join(traceback.format_exception(type(error), error, error.__traceback__)),
        )
    )

    for directory in (app_dir, fallback_dir):
        try:
            directory.mkdir(parents=True, exist_ok=True)
            diagnostic_path = directory / "启动诊断.txt"
            diagnostic_path.write_text(details, encoding="utf-8")
            return diagnostic_path
        except OSError:
            continue
    return None


def _show_startup_error(error: BaseException) -> None:
    diagnostic_path = _write_startup_diagnostic(error)
    diagnostic_hint = str(diagnostic_path) if diagnostic_path else "未能写入诊断文件"
    message = (
        f"{APP_NAME} 无法加载桌面界面运行库。\n\n"
        "请确认：\n"
        "1. 使用 Windows 10 1809 或更高版本的 64 位系统；\n"
        "2. 已完整解压 ZIP，并从解压后的文件夹运行程序；\n"
        "3. 没有单独复制或移动 ClassTeacherManager.exe。\n\n"
        f"诊断文件：{diagnostic_hint}\n\n"
        f"错误信息：{error}"
    )
    try:
        ctypes.windll.user32.MessageBoxW(0, message, f"{APP_NAME} - 启动失败", 0x10)
    except (AttributeError, OSError):
        print(message, file=sys.stderr)


def main() -> int:
    """Application entry point."""
    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication

        from views.main_window import MainWindow
    except (ImportError, OSError) as error:
        _show_startup_error(error)
        return 1

    from database.init_db import initialize_database
    from utils.excel_service import ensure_student_import_template
    from utils.score_excel_import import ensure_score_import_template

    initialize_database()
    ensure_student_import_template(STUDENT_IMPORT_TEMPLATE)
    ensure_score_import_template(SCORE_IMPORT_TEMPLATE)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("LocalClassManager")
    app.setWindowIcon(QIcon(str(RESOURCE_DIR / "app.ico")))

    window = MainWindow()
    window.show()
    QTimer.singleShot(0, window.show_teacher_setup_if_needed)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
