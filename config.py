from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "班主任综合管理系统"
PROJECT_ROOT = Path(__file__).resolve().parent
RESOURCE_DIR = PROJECT_ROOT / "resources"
TEMPLATE_DIR = RESOURCE_DIR / "templates"
STUDENT_IMPORT_TEMPLATE = TEMPLATE_DIR / "学生信息导入模板.xlsx"
SCORE_IMPORT_TEMPLATE = TEMPLATE_DIR / "成绩导入模板.xlsx"


def _runtime_root() -> Path:
    """Keep packaged application data in the current Windows user's local folder."""
    if getattr(sys, "frozen", False):
        local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        return local_app_data / "LocalClassManager"
    return PROJECT_ROOT


RUNTIME_ROOT = _runtime_root()
DATA_DIR = RUNTIME_ROOT / "data"
BACKUP_DIR = RUNTIME_ROOT / "backups"
DATABASE_PATH = DATA_DIR / "class_manager.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"


def ensure_app_dirs() -> None:
    """Create local runtime directories if they do not exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
