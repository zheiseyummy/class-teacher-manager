from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QProcess, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import APP_NAME, RESOURCE_DIR, STUDENT_IMPORT_TEMPLATE
from controllers.student_controller import StudentDataError
from utils.backup_scheduler import BackupScheduler
from utils.excel_service import ensure_student_import_template
from utils.ui_layout import restore_splitter
from views.attendance_view import AttendanceView
from views.backup_view import BackupView
from views.import_result_dialog import ImportResultDialog
from views.moral_view import MoralView
from views.planner_view import CourseCalendarView
from views.quality_view import QualityView
from views.scores_view import ScoresView
from views.students_view import StudentsView
from views.workbench_view import TodayWorkbenchView


class MainWindow(QMainWindow):
    """Main desktop shell: left menu, top actions, right content area."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 760)
        self.setMinimumSize(1100, 680)

        self.menu = QListWidget()
        self.stack = QStackedWidget()
        self.search_input = QLineEdit()
        self.class_filter = QComboBox()

        self._build_ui()
        self._apply_style()
        self._connect_signals()
        self._refresh_class_filter()
        self._change_page(self.menu.currentRow())
        self.backup_scheduler = BackupScheduler(parent=self)
        self.backup_scheduler.backup_created.connect(self.backup_view.show_scheduler_success)
        self.backup_scheduler.backup_failed.connect(self.backup_view.show_scheduler_error)
        self.backup_scheduler.start()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.root_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.root_splitter.setObjectName("mainSplitter")
        self.root_splitter.setChildrenCollapsible(False)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(196)
        sidebar.setMaximumWidth(380)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 22, 18, 18)
        sidebar_layout.setSpacing(14)

        title = QLabel("班主任工作台\n本地数据管理")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignLeft)
        sidebar_layout.addWidget(title)

        self.menu.setObjectName("menu")
        self.menu.setFrameShape(QFrame.NoFrame)
        self.menu.setSpacing(4)
        for text in [
            "今日班级工作台",
            "学生数据中心",
            "综合素质评价",
            "成绩管理",
            "德育评价",
            "请假与考勤",
            "课程表与日历",
            "数据备份与恢复",
        ]:
            self.menu.addItem(QListWidgetItem(text))
        self.menu.setCurrentRow(0)
        sidebar_layout.addWidget(self.menu, 1)

        content = QFrame()
        content.setObjectName("content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 24)
        content_layout.setSpacing(16)

        self.top_bar = QFrame()
        self.top_bar.setObjectName("topBar")
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(16, 12, 16, 12)
        top_layout.setSpacing(12)

        self.search_input.setPlaceholderText("搜索姓名、学号、家长电话...")
        self.search_input.setObjectName("searchInput")
        top_layout.addWidget(self.search_input, 1)

        self.class_filter.setObjectName("classFilter")
        self.class_filter.setMinimumWidth(142)
        top_layout.addWidget(self.class_filter)

        self.manage_class_button = QPushButton("管理班级")
        self.manage_class_button.setObjectName("secondaryButton")
        top_layout.addWidget(self.manage_class_button)

        self.import_button = QPushButton("导入 Excel")
        self.import_button.setObjectName("secondaryButton")
        import_menu = QMenu(self)
        import_menu.addAction("选择 Excel 文件", self._import_excel)
        import_menu.addAction("打开导入模板", self._open_import_template)
        self.import_button.setMenu(import_menu)
        top_layout.addWidget(self.import_button)

        self.export_button = QPushButton("导出 Excel")
        self.export_button.setObjectName("secondaryButton")
        export_menu = QMenu(self)
        export_menu.addAction("导出全部学生信息", self._export_all_students)
        export_menu.addAction("导出当前班级学生信息", self._export_current_class)
        export_menu.addAction("导出家长通讯录", self._export_guardian_directory)
        self.export_button.setMenu(export_menu)
        top_layout.addWidget(self.export_button)

        self.add_student_button = QPushButton("新增学生")
        self.add_student_button.setObjectName("primaryButton")
        top_layout.addWidget(self.add_student_button)

        content_layout.addWidget(self.top_bar)

        self.workbench_view = TodayWorkbenchView()
        self.stack.addWidget(self.workbench_view)
        self.students_view = StudentsView()
        self.stack.addWidget(self.students_view)
        self.stack.addWidget(QualityView())
        self.stack.addWidget(ScoresView())
        self.moral_view = MoralView()
        self.stack.addWidget(self.moral_view)
        self.attendance_view = AttendanceView()
        self.stack.addWidget(self.attendance_view)
        self.planner_view = CourseCalendarView()
        self.stack.addWidget(self.planner_view)
        self.backup_view = BackupView()
        self.stack.addWidget(self.backup_view)
        content_layout.addWidget(self.stack, 1)

        self.root_splitter.addWidget(sidebar)
        self.root_splitter.addWidget(content)
        self.root_splitter.setStretchFactor(0, 0)
        self.root_splitter.setStretchFactor(1, 1)
        restore_splitter(self.root_splitter, "main_window", [220, 1060])
        root_layout.addWidget(self.root_splitter)
        self.setCentralWidget(root)

    def _connect_signals(self) -> None:
        self.menu.currentRowChanged.connect(self._change_page)
        self.search_input.textChanged.connect(self.students_view.set_search_text)
        self.class_filter.currentIndexChanged.connect(self._apply_class_filter)
        self.manage_class_button.clicked.connect(self.students_view.open_class_manager)
        self.add_student_button.clicked.connect(self.students_view.open_add_student)
        self.students_view.classes_changed.connect(self._refresh_class_filter)
        self.students_view.classes_changed.connect(self._refresh_planning_classes)
        self.planner_view.data_changed.connect(self.workbench_view.refresh_classes)
        self.workbench_view.navigate_requested.connect(self.menu.setCurrentRow)
        self.workbench_view.planner_action_requested.connect(self._open_planner_from_workbench)
        self.backup_view.restart_requested.connect(self._restart_application)

    def _change_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.top_bar.setVisible(index == 1)
        if index == 0:
            self.workbench_view.refresh()
        elif index == 4:
            self.moral_view.refresh_filters()
        elif index == 5:
            self.attendance_view.refresh_filters()
        elif index == 6:
            self.planner_view.refresh_all()
        elif index == 7:
            self.backup_view.refresh_all()

    def _refresh_planning_classes(self) -> None:
        self.workbench_view.refresh_classes()
        self.planner_view.refresh_all()

    def _open_planner_from_workbench(self, destination: str) -> None:
        self.menu.setCurrentRow(6)
        if destination == "schedule":
            self.planner_view.show_course_tab()
        elif destination == "calendar_new":
            self.planner_view.open_new_event()
        else:
            self.planner_view.show_calendar_tab()

    def _restart_application(self) -> None:
        arguments = sys.argv[1:] if getattr(sys, "frozen", False) else sys.argv
        if not QProcess.startDetached(sys.executable, arguments):
            QMessageBox.warning(self, "请手动重启", "数据已恢复，请关闭并重新打开软件以加载恢复后的数据。")
            return
        QApplication.instance().quit()

    def _apply_class_filter(self) -> None:
        self.students_view.set_class_filter(self.class_filter.currentData())

    def _refresh_class_filter(self) -> None:
        selected_id = self.class_filter.currentData()
        self.class_filter.blockSignals(True)
        self.class_filter.clear()
        self.class_filter.addItem("全部班级", None)
        for class_group in self.students_view.controller.list_classes():
            self.class_filter.addItem(class_group["name"], class_group["id"])
        selected_index = self.class_filter.findData(selected_id)
        self.class_filter.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        self.class_filter.blockSignals(False)
        self._apply_class_filter()

    def _import_excel(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择学生信息 Excel 文件",
            "",
            "Excel 文件 (*.xlsx *.xlsm)",
        )
        if not file_path:
            return
        try:
            result = self.students_view.controller.import_students_from_excel(file_path)
        except StudentDataError as exc:
            QMessageBox.warning(self, "无法导入", str(exc))
            return
        self._refresh_class_filter()
        ImportResultDialog(result, self).exec()

    def _open_import_template(self) -> None:
        ensure_student_import_template(STUDENT_IMPORT_TEMPLATE)
        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(STUDENT_IMPORT_TEMPLATE)))
        if not opened:
            QMessageBox.information(self, "导入模板", f"模板已生成：\n{STUDENT_IMPORT_TEMPLATE}")

    def _export_all_students(self) -> None:
        self._export_excel("全部学生信息.xlsx", self.students_view.controller.export_students_to_excel)

    def _export_current_class(self) -> None:
        class_id = self.class_filter.currentData()
        if class_id is None:
            QMessageBox.information(self, "请选择班级", "请先在顶部选择要导出的班级。")
            return
        class_name = self.class_filter.currentText()
        self._export_excel(
            f"{class_name}学生信息.xlsx",
            lambda file_path: self.students_view.controller.export_students_to_excel(file_path, int(class_id)),
        )

    def _export_guardian_directory(self) -> None:
        self._export_excel("家长通讯录.xlsx", self.students_view.controller.export_guardian_directory_to_excel)

    def _export_excel(self, default_name: str, export_action) -> None:
        default_path = str(Path.home() / "Desktop" / default_name)
        file_path, _ = QFileDialog.getSaveFileName(self, "导出 Excel", default_path, "Excel 文件 (*.xlsx)")
        if not file_path:
            return
        path = Path(file_path)
        if path.suffix.lower() != ".xlsx":
            path = path.with_suffix(".xlsx")
        try:
            result_path = export_action(path)
        except Exception:
            QMessageBox.warning(self, "导出失败", "无法写入 Excel 文件，请确认文件未被其他程序占用。")
            return
        QMessageBox.information(self, "导出完成", f"Excel 文件已生成：\n{result_path}")

    def _placeholder(self, text: str) -> QWidget:
        page = QFrame()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        label = QLabel(text)
        label.setObjectName("placeholder")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label, 1)
        return page

    def _apply_style(self) -> None:
        style_path = RESOURCE_DIR / "styles.qss"
        if style_path.exists():
            self.setStyleSheet(style_path.read_text(encoding="utf-8"))
