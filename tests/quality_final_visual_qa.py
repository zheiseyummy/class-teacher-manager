from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config


def run() -> Path:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        config.DATA_DIR = root / "data"
        config.BACKUP_DIR = root / "backups"
        config.DATABASE_PATH = config.DATA_DIR / "class_manager.db"
        config.DATABASE_URL = f"sqlite:///{config.DATABASE_PATH.as_posix()}"

        from PySide6.QtWidgets import QApplication

        from controllers.quality_controller import QualityController
        from controllers.student_controller import StudentController
        from database.connection import engine
        from database.init_db import initialize_database
        from utils.quality_scoring import SEMESTER_RULES
        from views.quality_final_review_dialog import QualityFinalReviewDialog

        output_path = Path(__file__).resolve().parents[1] / "docs" / "visual-qa-quality-final.png"
        try:
            initialize_database()
            students = StudentController()
            class_id = students.create_class({"name": "初三1班", "grade": "初三"})
            quality = QualityController()
            dimensions = [item["name"] for item in quality.list_dimensions()]
            family_names = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何"
            for index, family_name in enumerate(family_names, start=1):
                student_id = students.create_student(
                    {
                        "class_id": class_id,
                        "name": f"{family_name}{'明' if index % 2 else '悦'}",
                        "student_no": f"2026{index:03d}",
                    },
                    [],
                )
                for term_index, rule in enumerate(SEMESTER_RULES):
                    level = "N/A" if index in {3, 11} and term_index < 2 else ("A", "B", "C")[(index + term_index) % 3]
                    quality.save_evaluation(
                        student_id,
                        rule.key,
                        {dimension: level for dimension in dimensions},
                    )
            quality.generate_final_results(class_id)

            app = QApplication.instance() or QApplication([])
            style_path = Path(__file__).resolve().parents[1] / "resources" / "styles.qss"
            app.setStyleSheet(style_path.read_text(encoding="utf-8"))
            dialog = QualityFinalReviewDialog(quality, class_id)
            dialog.resize(1320, 780)
            dialog.show()
            app.processEvents()
            assert dialog.grab().save(str(output_path))
            dialog.close()
            app.processEvents()
            return output_path
        finally:
            engine.dispose()


if __name__ == "__main__":
    print(run())
