from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config


def run() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        config.DATA_DIR = root / "data"
        config.BACKUP_DIR = root / "backups"
        config.DATABASE_PATH = config.DATA_DIR / "class_manager.db"
        config.DATABASE_URL = f"sqlite:///{config.DATABASE_PATH.as_posix()}"

        from controllers.score_controller import ScoreController
        from controllers.student_controller import StudentController
        from database.connection import engine
        from database.init_db import initialize_database

        try:
            initialize_database()
            students = StudentController()
            class_a = students.create_class({"name": "初三1班", "grade": "初三"})
            class_b = students.create_class({"name": "初三2班", "grade": "初三"})
            student_ids = {
                "甲": students.create_student({"class_id": class_a, "name": "甲", "student_no": "001"}, []),
                "乙": students.create_student({"class_id": class_a, "name": "乙", "student_no": "002"}, []),
                "丙": students.create_student({"class_id": class_b, "name": "丙", "student_no": "003"}, []),
                "丁": students.create_student({"class_id": class_b, "name": "丁", "student_no": "004"}, []),
            }

            controller = ScoreController()
            first_path = root / "第一次月考.xlsx"
            _write_scores(
                first_path,
                ["姓名", "学号", "班级", "语文(120)", "数学(120)", "英语(120)", "物理(100)"],
                [
                    ["甲", "001", "初三1班", 100, 110, 95, 80],
                    ["乙", "002", "初三1班", 110, 100, 100, 90],
                    ["丙", "003", "初三2班", 120, 110, 105, 95],
                    ["丁", "004", "初三2班", 90, 95, 90, 70],
                ],
            )
            first = controller.import_scores_from_excel(
                first_path,
                {"name": "第一次月考", "exam_date": date(2026, 9, 30), "semester": "初三上", "grade": "初三"},
            )
            assert first.imported_students == 4
            assert first.created_students == 0
            assert first.written_scores == 16
            assert first.subjects == ["语文", "数学", "英语", "物理"]

            dashboard = controller.get_exam_dashboard(first.exam_id, class_a)
            assert dashboard["summary"]["student_count"] == 2
            assert dashboard["summary"]["average_total"] == 392.5
            rows = {row["姓名"]: row for row in dashboard["rows"]}
            assert rows["乙"]["班级排名"] == 1
            assert rows["甲"]["班级排名"] == 2
            assert rows["甲"]["年级排名"] == 3
            grade_rows = {row["姓名"]: row for row in controller.get_exam_dashboard(first.exam_id)["rows"]}
            assert grade_rows["丙"]["年级排名"] == 1

            second_path = root / "期中考试.xlsx"
            _write_scores(
                second_path,
                ["姓名", "班级", "语文", "数学", "英语", "化学(100)"],
                [
                    ["甲", "初三1班", 105, 114, 102, 85],
                    ["乙", "初三1班", 108, 103, 99, 90],
                    ["丙", "初三2班", 118, 112, 108, 92],
                    ["丁", "初三2班", 96, 98, 93, 74],
                ],
            )
            second = controller.import_scores_from_excel(
                second_path,
                {"name": "期中考试", "exam_date": date(2026, 11, 10), "semester": "初三上", "grade": "初三"},
            )
            assert second.written_scores == 16
            student_analysis = controller.get_student_analysis(student_ids["甲"], second.exam_id)
            assert len(student_analysis["trend_rows"]) == 2
            assert student_analysis["trend_rows"][-1]["change"] == 21
            assert {row["subject"] for row in student_analysis["subject_rows"]} == {"语文", "数学", "英语", "化学"}
            assert len(controller.get_class_trends(class_a)) == 2
            subject_trends = controller.get_subject_trends(class_a)
            chinese_second = [row for row in subject_trends if row["subject"] == "语文"][-1]
            assert chinese_second["change"] == 1.5

            standalone_path = root / "独立成绩.xlsx"
            _write_scores(standalone_path, ["姓名", "语文", "数学"], [["独立学生", 100, 100]])
            standalone = controller.import_scores_from_excel(
                standalone_path,
                {"name": "独立考试", "exam_date": date(2026, 12, 1)},
            )
            assert standalone.created_students == 1
            assert standalone.imported_students == 1
            assert standalone.class_names == ["成绩导入班"]
        finally:
            engine.dispose()


def _write_scores(file_path: Path, headers: list[str], rows: list[list[object]]) -> None:
    from openpyxl import Workbook

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    workbook.save(file_path)
    workbook.close()


if __name__ == "__main__":
    run()
    print("Score management smoke test passed.")
