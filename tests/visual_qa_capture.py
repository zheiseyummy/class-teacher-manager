from __future__ import annotations

import sys
import tempfile
from datetime import date, datetime
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

        from PySide6.QtCore import QDate
        from PySide6.QtWidgets import QApplication, QLabel

        from controllers.attendance_controller import AttendanceController
        from controllers.backup_controller import BackupController
        from controllers.moral_controller import MoralController
        from controllers.planner_controller import PlannerController
        from controllers.score_controller import ScoreController
        from controllers.student_controller import StudentController
        from controllers.teaching_schedule_controller import TeachingScheduleController
        from database.connection import engine
        from database.init_db import initialize_database
        from views.main_window import MainWindow

        target_date = date(2026, 7, 16)
        output_dir = Path(__file__).resolve().parents[1] / "docs"
        output_dir.mkdir(exist_ok=True)
        try:
            initialize_database()
            students = StudentController()
            class_a = students.create_class({"name": "初三1班", "grade": "初三"})
            class_b = students.create_class({"name": "初三2班", "grade": "初三"})
            class_c = students.create_class({"name": "初三6班", "grade": "初三"})
            student_a = students.create_student(
                {"class_id": class_a, "name": "李明", "student_no": "202601"}, []
            )
            students.create_student(
                {"class_id": class_a, "name": "王婷", "student_no": "202602"}, []
            )
            students.create_student({"class_id": class_b, "name": "张宇", "student_no": "202603"}, [])
            students.create_student({"class_id": class_c, "name": "陈雨", "student_no": "202604"}, [])

            planner = PlannerController()
            planner.set_class_color(class_a, "#12966D")
            planner.set_class_color(class_b, "#2D7DD2")
            planner.set_class_color(class_c, "#D97706")
            schedule = TeachingScheduleController()
            semester_id = schedule.save_semester(
                {
                    "name": "2026 暑期课程",
                    "start_date": date(2026, 7, 1),
                    "end_date": date(2026, 7, 31),
                    "is_current": True,
                }
            )
            group_a = schedule.save_teaching_group(
                {"name": "初三1班", "color": "#12966D", "linked_class_id": class_a}
            )
            group_b = schedule.save_teaching_group(
                {"name": "初三2班", "color": "#2D7DD2", "linked_class_id": class_b}
            )
            group_c = schedule.save_teaching_group(
                {"name": "九年级晚自习", "color": "#D97706"}
            )
            periods = [
                ("早读", "07:30", "07:55"),
                ("第一节", "08:05", "08:45"),
                ("第二节", "08:55", "09:35"),
                ("午间辅导", "12:30", "13:05"),
                ("晚自习", "18:30", "20:00"),
            ]
            period_ids = [
                schedule.save_period(
                    {
                        "semester_id": semester_id,
                        "sort_order": index,
                        "name": name,
                        "start_time": start_time,
                        "end_time": end_time,
                    }
                )
                for index, (name, start_time, end_time) in enumerate(periods, start=1)
            ]
            for teaching_group_id, weekday, period_index, subject, teacher, location in (
                (group_a, 1, 0, "语文", "王老师", "初三1班教室"),
                (group_a, 2, 1, "数学", "赵老师", "初三1班教室"),
                (group_a, 3, 2, "英语", "陈老师", "初三1班教室"),
                (group_a, 4, 0, "语文", "王老师", "初三1班教室"),
                (group_a, 4, 1, "数学", "赵老师", "初三1班教室"),
                (group_a, 4, 2, "物理", "孙老师", "实验楼201"),
                (group_a, 5, 3, "生涯辅导", "李老师", "团体辅导室"),
                (group_b, 1, 0, "英语", "陈老师", "初三2班教室"),
                (group_b, 2, 1, "化学", "周老师", "实验楼302"),
                (group_b, 4, 0, "英语", "陈老师", "初三2班教室"),
                (group_b, 4, 1, "化学", "周老师", "实验楼302"),
                (group_b, 5, 2, "体育", "刘老师", "操场"),
                (group_c, 4, 4, "晚自习答疑", "教师团队", "阅览室"),
                (group_c, 5, 4, "晚自习答疑", "教师团队", "阅览室"),
            ):
                schedule.save_course(
                    {
                        "semester_id": semester_id,
                        "teaching_group_id": teaching_group_id,
                        "weekday": weekday,
                        "period_id": period_ids[period_index],
                        "subject": subject,
                        "teacher": teacher,
                        "location": location,
                    }
                )
            planner.save_event(
                {
                    "class_id": class_a,
                    "event_date": target_date,
                    "title": "阶段性质量分析会",
                    "category": "班级活动",
                    "start_time": "16:10",
                    "end_time": "16:45",
                    "note": "整理本周学习情况",
                }
            )
            planner.save_event(
                {
                    "class_id": None,
                    "event_date": target_date,
                    "title": "年级组教研会议",
                    "category": "会议",
                    "start_time": "18:30",
                    "end_time": "19:20",
                }
            )
            AttendanceController().create_record(
                {
                    "student_id": student_a,
                    "record_type": "迟到",
                    "approval_status": "已登记",
                    "start_time": datetime(2026, 7, 16, 7, 52),
                    "end_time": datetime(2026, 7, 16, 8, 8),
                    "reason": "交通原因",
                }
            )
            MoralController().create_record(
                {
                    "student_id": student_a,
                    "record_date": target_date,
                    "category": "班级服务",
                    "title": "整理图书角",
                    "points": 2,
                }
            )
            first_score_path = root / "六月月考.xlsx"
            _write_score_book(
                first_score_path,
                [
                    ["李明", "202601", "初三1班", 90, 88, 85],
                    ["王婷", "202602", "初三1班", 95, 93, 92],
                ],
            )
            second_score_path = root / "七月阶段检测.xlsx"
            _write_score_book(
                second_score_path,
                [
                    ["李明", "202601", "初三1班", 98, 96, 91],
                    ["王婷", "202602", "初三1班", 94, 92, 90],
                ],
            )
            score_controller = ScoreController()
            score_controller.import_scores_from_excel(
                first_score_path,
                {
                    "name": "六月月考",
                    "exam_date": date(2026, 6, 20),
                    "semester": "初三下",
                    "grade": "初三",
                },
            )
            score_controller.import_scores_from_excel(
                second_score_path,
                {
                    "name": "七月阶段检测",
                    "exam_date": date(2026, 7, 15),
                    "semester": "初三下",
                    "grade": "初三",
                },
            )
            BackupController().create_full_backup()

            app = QApplication([])
            window = MainWindow()
            window.resize(1487, 1058)
            workbench_date = QDate(target_date.year, target_date.month, target_date.day)
            window.workbench_view.set_reference_date(target_date)
            window.menu.setCurrentRow(0)
            window.page_subtitle.setText(f"今天是 {window._format_date(target_date)}")
            window.show()
            app.processEvents()
            assert window.workbench_view.date_label.text() == "2026-07-16"
            assert not hasattr(window.workbench_view, "date_edit")
            assert window.workbench_view.score_fluctuation_list.count() == 2
            assert all(not window.menu.item(index).icon().isNull() for index in range(window.menu.count()))
            assert window.grab().save(str(output_dir / "visual-qa-workbench.png"))

            window.resize(1120, 700)
            app.processEvents()
            for index in range(window.workbench_view.score_fluctuation_list.count()):
                row = window.workbench_view.score_fluctuation_list.itemWidget(
                    window.workbench_view.score_fluctuation_list.item(index)
                )
                assert row.findChild(QLabel, "rankChangeBadge").isVisible()
            assert window.grab().save(str(output_dir / "visual-qa-workbench-compact.png"))

            window.resize(1487, 1058)
            window.menu.setCurrentRow(1)
            app.processEvents()
            assert window.grab().save(str(output_dir / "visual-qa-students.png"))

            window.resize(1120, 700)
            app.processEvents()
            assert window.grab().save(str(output_dir / "visual-qa-students-compact.png"))

            window.resize(1487, 1058)
            window.menu.setCurrentRow(6)
            window.planner_view.show_course_tab()
            app.processEvents()
            assert window.grab().save(str(output_dir / "visual-qa-teaching-schedule.png"))

            window.planner_view.show_calendar_tab()
            window.planner_view.calendar_widget.setSelectedDate(workbench_date)
            app.processEvents()
            assert window.grab().save(str(output_dir / "visual-qa-planner.png"))

            window.menu.setCurrentRow(7)
            app.processEvents()
            assert window.grab().save(str(output_dir / "visual-qa-backup.png"))
            window.close()
            app.quit()
        finally:
            engine.dispose()


def _write_score_book(file_path: Path, rows: list[list[object]]) -> None:
    from openpyxl import Workbook

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["姓名", "学号", "班级", "语文", "数学", "英语"])
    for row in rows:
        worksheet.append(row)
    workbook.save(file_path)
    workbook.close()


if __name__ == "__main__":
    run()
    print("Visual QA screenshots captured.")
