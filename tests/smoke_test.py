from __future__ import annotations

import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config


def run() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        config.DATA_DIR = root / "data"
        config.BACKUP_DIR = root / "backups"
        config.DATABASE_PATH = config.DATA_DIR / "class_manager.db"
        config.DATABASE_URL = f"sqlite:///{config.DATABASE_PATH.as_posix()}"

        from database.connection import engine
        from database.init_db import initialize_database
        from controllers.student_controller import StudentController
        from openpyxl import Workbook
        from utils.excel_service import ensure_student_import_template

        try:
            initialize_database()
            controller = StudentController()
            class_id = controller.create_class(
                {"name": "初三1班", "grade": "初三", "school_year": "2026-2027"}
            )
            student_id = controller.create_student(
                {"class_id": class_id, "name": "已有学生", "student_no": "001", "seat_no": "1"},
                [{"name": "家长甲", "relationship": "母亲", "phone": "13800000001", "is_primary": True}],
            )
            detail = controller.get_student_detail(student_id)
            assert detail["name"] == "已有学生"
            assert detail["guardians"][0]["phone"] == "13800000001"

            template_path = ensure_student_import_template(root / "学生信息导入模板.xlsx")
            assert template_path.exists()
            assert controller.export_students_to_excel(root / "学生导出.xlsx").exists()
            assert controller.export_guardian_directory_to_excel(root / "家长通讯录.xlsx").exists()

            workbook = Workbook()
            sheet = workbook.active
            sheet.append(["姓名", "班级", "学号", "座号", "出生日期", "家长姓名", "联系电话"])
            sheet.append(["已有学生", "初三1班", "001", "1", "", "家长甲", "13800000001"])
            sheet.append(["新增学生", "初三2班", "002", "2", "2010-01-01", "家长乙", "13900000002"])
            sheet.append(["日期错误", "初三2班", "003", "3", "2010/99/99", "", ""])
            import_path = root / "导入测试.xlsx"
            workbook.save(import_path)
            workbook.close()

            result = controller.import_students_from_excel(import_path)
            assert (result.success_rows, result.skipped_rows, result.failed_rows) == (1, 1, 1), result
            assert controller.count_classes() == 2
            assert len(controller.search_students("新增学生")) == 1
        finally:
            engine.dispose()


if __name__ == "__main__":
    run()
    print("Student center / Excel smoke test passed.")
