from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QProcess, QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
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
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from config import APP_NAME, APP_VERSION_LABEL, RESOURCE_DIR, STUDENT_IMPORT_TEMPLATE
from controllers.student_controller import StudentDataError
from controllers.teacher_profile_controller import TeacherProfileController
from utils.backup_scheduler import BackupScheduler
from utils.excel_service import ensure_student_import_template
from utils.ui_icons import lucide_icon
from utils.ui_layout import refresh_style, restore_splitter
from views.attendance_view import AttendanceView
from views.backup_view import BackupView
from views.import_result_dialog import ImportResultDialog
from views.moral_view import MoralView
from views.planner_view import CourseCalendarView
from views.quality_view import QualityView
from views.scores_view import ScoresView
from views.students_view import StudentsView
from views.teacher_profile_dialog import TeacherProfileDialog
from views.workbench_view import TodayWorkbenchView


class ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._clickable = True
        self.set_clickable(True)

    def set_clickable(self, enabled: bool) -> None:
        self._clickable = enabled
        self.setProperty("clickable", enabled)
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor
        )
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus if enabled else Qt.FocusPolicy.NoFocus)
        self.style().unpolish(self)
        self.style().polish(self)

    def mouseReleaseEvent(self, event) -> None:
        if (
            self._clickable
            and event.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if self._clickable and event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Space,
        ):
            self.clicked.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class MainWindow(QMainWindow):
    """Main desktop shell: left menu, top actions, right content area."""

    PAGE_META = (
        ("您好，老师！", ""),
        ("学生数据中心", "学生档案、班级与家长联系方式"),
        ("综合素质评价", "六学期五维评价与期末核对"),
        ("成绩管理", "考试成绩、排名趋势与个体分析"),
        ("德育评价", "集体活动、获奖与社会实践记录"),
        ("请假与考勤", "请假、迟到与日常出勤记录"),
        ("课程表与日历", "教学安排与班级日程"),
        ("数据备份与恢复", "本地数据归档与恢复"),
    )

    NAVIGATION_ITEMS = (
        ("今日班级工作台", "layout-dashboard"),
        ("学生数据中心", "users-round"),
        ("综合素质评价", "shield-check"),
        ("成绩管理", "chart-no-axes-column-increasing"),
        ("德育评价", "award"),
        ("请假与考勤", "calendar-clock"),
        ("课程表与日历", "calendar-days"),
        ("数据备份与恢复", "database-backup"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1360, 840)
        self.setMinimumSize(360, 640)
        self._compact_mode: bool | None = None

        self.menu = QListWidget()
        self.stack = QStackedWidget()
        self.search_input = QLineEdit()
        self.class_filter = QComboBox()
        self.teacher_profile_controller = TeacherProfileController()
        self.teacher_profile = self.teacher_profile_controller.get_profile()

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

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(208)
        self.sidebar.setMaximumWidth(280)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(14, 20, 14, 16)
        sidebar_layout.setSpacing(16)

        brand = QWidget()
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(4, 0, 4, 2)
        brand_layout.setSpacing(11)
        brand_mark = QLabel()
        brand_mark.setObjectName("brandMark")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setFixedSize(40, 40)
        brand_icon = lucide_icon(
            "graduation-cap",
            color="#2F64D6",
            active_color="#2F64D6",
            size=22,
        )
        brand_mark.setPixmap(brand_icon.pixmap(QSize(22, 22)))
        brand_layout.addWidget(brand_mark)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        title = QLabel("班主任工作台")
        title.setObjectName("brandTitle")
        brand_text.addWidget(title)
        subtitle = QLabel("本地综合管理")
        subtitle.setObjectName("brandSubtitle")
        brand_text.addWidget(subtitle)
        brand_layout.addLayout(brand_text, 1)
        sidebar_layout.addWidget(brand)

        self.menu.setObjectName("menu")
        self.menu.setFrameShape(QFrame.NoFrame)
        self.menu.setSpacing(2)
        self.menu.setIconSize(QSize(18, 18))
        for text, icon_name in self.NAVIGATION_ITEMS:
            item = QListWidgetItem(
                lucide_icon(
                    icon_name,
                    color="#66768B",
                    active_color="#2F64D6",
                    selected_color="#2F64D6",
                ),
                text,
            )
            item.setToolTip(text)
            self.menu.addItem(item)
        self.menu.setCurrentRow(0)
        sidebar_layout.addWidget(self.menu, 1)

        sidebar_footer = QFrame()
        sidebar_footer.setObjectName("sidebarFooter")
        sidebar_footer_layout = QVBoxLayout(sidebar_footer)
        sidebar_footer_layout.setContentsMargins(8, 8, 8, 8)
        sidebar_footer_layout.setSpacing(2)
        self.sidebar_version = QLabel(f"本地办公版  ·  {APP_VERSION_LABEL}")
        self.sidebar_version.setObjectName("sidebarVersion")
        self.sidebar_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_footer_layout.addWidget(self.sidebar_version)
        self.sidebar_personal_mark = ClickableLabel()
        self.sidebar_personal_mark.setObjectName("sidebarPersonalMark")
        self.sidebar_personal_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_personal_mark.setWordWrap(True)
        self.sidebar_personal_mark.setToolTip("编辑教师信息")
        sidebar_footer_layout.addWidget(self.sidebar_personal_mark)
        sidebar_layout.addWidget(sidebar_footer)

        content = QFrame()
        content.setObjectName("content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.workbench_view = TodayWorkbenchView()

        self.shell_header = QFrame()
        self.shell_header.setObjectName("shellHeader")
        self.shell_header_layout = QHBoxLayout(self.shell_header)
        self.shell_header_layout.setContentsMargins(24, 16, 24, 16)
        self.shell_header_layout.setSpacing(14)

        self.compact_nav_button = QToolButton()
        self.compact_nav_button.setObjectName("compactNavButton")
        self.compact_nav_button.setIcon(lucide_icon("layout-dashboard", size=19))
        self.compact_nav_button.setIconSize(QSize(19, 19))
        self.compact_nav_button.setToolTip("切换功能模块")
        self.compact_nav_button.setAccessibleName("切换功能模块")
        self.compact_nav_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        compact_nav_menu = QMenu(self.compact_nav_button)
        for index, (text, icon_name) in enumerate(self.NAVIGATION_ITEMS):
            action = compact_nav_menu.addAction(lucide_icon(icon_name), text)
            action.triggered.connect(lambda _checked=False, row=index: self.menu.setCurrentRow(row))
        self.compact_nav_button.setMenu(compact_nav_menu)
        self.compact_nav_button.setVisible(False)
        self.shell_header_layout.addWidget(self.compact_nav_button)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        self.page_title = ClickableLabel()
        self.page_title.setObjectName("pageTitle")
        title_layout.addWidget(self.page_title)
        self.page_subtitle = QLabel()
        self.page_subtitle.setObjectName("pageSubtitle")
        title_layout.addWidget(self.page_subtitle)
        self.shell_header_layout.addLayout(title_layout, 1)
        self.shell_header_layout.addWidget(self.workbench_view.header_controls)
        self.header_date = QLabel(self._format_date(date.today()))
        self.header_date.setObjectName("headerDate")
        self.shell_header_layout.addWidget(self.header_date)
        content_layout.addWidget(self.shell_header)

        self.page_area = QFrame()
        self.page_area.setObjectName("pageArea")
        self.page_layout = QVBoxLayout(self.page_area)
        self.page_layout.setContentsMargins(22, 18, 22, 22)
        self.page_layout.setSpacing(14)

        self.top_bar = QFrame()
        self.top_bar.setObjectName("topBar")
        self.top_layout = QGridLayout(self.top_bar)
        self.top_layout.setContentsMargins(14, 10, 14, 10)
        self.top_layout.setHorizontalSpacing(10)
        self.top_layout.setVerticalSpacing(8)

        self.search_input.setPlaceholderText("搜索姓名、学号或家长电话")
        self.search_input.setObjectName("searchInput")
        self.search_input.setMinimumWidth(250)
        self.top_layout.addWidget(self.search_input, 0, 0)
        self.top_layout.setColumnStretch(0, 1)

        self.class_filter.setObjectName("classFilter")
        self.class_filter.setMinimumWidth(142)
        self.top_layout.addWidget(self.class_filter, 0, 1)

        self.manage_class_button = QPushButton("管理班级")
        self.manage_class_button.setObjectName("secondaryButton")
        self.manage_class_button.setIcon(lucide_icon("users-round"))
        self.top_layout.addWidget(self.manage_class_button, 0, 2)

        self.import_button = QPushButton("导入 Excel")
        self.import_button.setObjectName("secondaryButton")
        self.import_button.setIcon(lucide_icon("file-up"))
        import_menu = QMenu(self)
        import_menu.addAction("选择 Excel 文件", self._import_excel)
        import_menu.addAction("打开导入模板", self._open_import_template)
        self.import_button.setMenu(import_menu)
        self.top_layout.addWidget(self.import_button, 0, 3)

        self.export_button = QPushButton("导出 Excel")
        self.export_button.setObjectName("secondaryButton")
        self.export_button.setIcon(lucide_icon("file-down"))
        export_menu = QMenu(self)
        export_menu.addAction("导出全部学生信息", self._export_all_students)
        export_menu.addAction("导出当前班级学生信息", self._export_current_class)
        export_menu.addAction("导出家长通讯录", self._export_guardian_directory)
        self.export_button.setMenu(export_menu)
        self.top_layout.addWidget(self.export_button, 0, 4)

        self.add_student_button = QPushButton("新增学生")
        self.add_student_button.setObjectName("primaryButton")
        self.add_student_button.setIcon(
            lucide_icon(
                "user-plus",
                color="#FFFFFF",
                active_color="#FFFFFF",
            )
        )
        self.top_layout.addWidget(self.add_student_button, 0, 5)

        self.student_more_button = QToolButton()
        self.student_more_button.setObjectName("moreButton")
        self.student_more_button.setText("更多")
        self.student_more_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.student_more_button.setIcon(lucide_icon("clipboard-check"))
        self.student_more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        student_more_menu = QMenu(self.student_more_button)
        student_more_menu.addAction(
            lucide_icon("users-round"),
            "管理班级",
            lambda: self.manage_class_button.click(),
        )
        import_more_menu = student_more_menu.addMenu(lucide_icon("file-up"), "导入")
        import_more_menu.addAction("选择 Excel 文件", self._import_excel)
        import_more_menu.addAction("打开导入模板", self._open_import_template)
        export_more_menu = student_more_menu.addMenu(lucide_icon("file-down"), "导出")
        export_more_menu.addAction("全部学生信息", self._export_all_students)
        export_more_menu.addAction("当前班级学生信息", self._export_current_class)
        export_more_menu.addAction("家长通讯录", self._export_guardian_directory)
        self.student_more_button.setMenu(student_more_menu)
        self.student_more_button.setVisible(False)
        self.top_layout.addWidget(self.student_more_button, 0, 6)

        self.page_layout.addWidget(self.top_bar)

        self.stack.addWidget(self.workbench_view)
        self.students_view = StudentsView()
        self.stack.addWidget(self.students_view)
        self.quality_view = QualityView()
        self.stack.addWidget(self.quality_view)
        self.scores_view = ScoresView()
        self.stack.addWidget(self.scores_view)
        self.moral_view = MoralView()
        self.stack.addWidget(self.moral_view)
        self.attendance_view = AttendanceView()
        self.stack.addWidget(self.attendance_view)
        self.planner_view = CourseCalendarView()
        self.stack.addWidget(self.planner_view)
        self.backup_view = BackupView()
        self.stack.addWidget(self.backup_view)
        self.page_layout.addWidget(self.stack, 1)
        content_layout.addWidget(self.page_area, 1)

        self.root_splitter.addWidget(self.sidebar)
        self.root_splitter.addWidget(content)
        self.root_splitter.setStretchFactor(0, 0)
        self.root_splitter.setStretchFactor(1, 1)
        restore_splitter(self.root_splitter, "main_window", [224, 1136])
        root_layout.addWidget(self.root_splitter)
        self.setCentralWidget(root)
        self._refresh_teacher_profile()
        self._apply_responsive_layout(force=True)

    def _connect_signals(self) -> None:
        self.menu.currentRowChanged.connect(self._change_page)
        self.search_input.textChanged.connect(self.students_view.set_search_text)
        self.class_filter.currentIndexChanged.connect(self._apply_class_filter)
        self.manage_class_button.clicked.connect(self.students_view.open_class_manager)
        self.add_student_button.clicked.connect(self.students_view.open_add_student)
        self.students_view.classes_changed.connect(self._refresh_class_filter)
        self.students_view.classes_changed.connect(self._refresh_planning_classes)
        self.students_view.filters_clear_requested.connect(self._clear_student_filters)
        self.planner_view.data_changed.connect(self.workbench_view.refresh_classes)
        self.workbench_view.navigate_requested.connect(self.menu.setCurrentRow)
        self.workbench_view.planner_action_requested.connect(self._open_planner_from_workbench)
        self.backup_view.restart_requested.connect(self._restart_application)
        self.page_title.clicked.connect(self._open_teacher_profile_from_header)
        self.sidebar_personal_mark.clicked.connect(self._open_teacher_profile)

    def _change_page(self, index: int) -> None:
        if not 0 <= index < len(self.PAGE_META):
            return
        self.stack.setCurrentIndex(index)
        self.top_bar.setVisible(index == 1)
        title, subtitle = self.PAGE_META[index]
        if index == 0:
            title = self.teacher_profile["greeting"]
            subtitle = f"今天是 {self._format_date(date.today())}"
        self.page_title.setText(title)
        self.page_title.set_clickable(index == 0)
        self.page_title.setToolTip("编辑教师信息" if index == 0 else "")
        self.page_subtitle.setText(subtitle)
        self.workbench_view.header_controls.setVisible(index == 0)
        self.header_date.setVisible(index != 0 and not bool(self._compact_mode))
        self.page_subtitle.setVisible(not bool(self._compact_mode))
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

    def show_teacher_setup_if_needed(self) -> None:
        profile = self.teacher_profile_controller.get_profile()
        if profile["onboarding_completed"]:
            return
        dialog = TeacherProfileDialog(self.teacher_profile_controller, self, onboarding=True)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.teacher_profile_controller.dismiss_onboarding()
        self._refresh_teacher_profile()

    def _open_teacher_profile_from_header(self) -> None:
        if self.menu.currentRow() == 0:
            self._open_teacher_profile()

    def _open_teacher_profile(self) -> None:
        dialog = TeacherProfileDialog(self.teacher_profile_controller, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._refresh_teacher_profile()

    def _refresh_teacher_profile(self) -> None:
        self.teacher_profile = self.teacher_profile_controller.get_profile()
        self.sidebar_personal_mark.setText(self.teacher_profile["personal_mark_display"])
        if self.menu.currentRow() == 0:
            self.page_title.setText(self.teacher_profile["greeting"])

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

    def _clear_student_filters(self) -> None:
        self.search_input.clear()
        self.class_filter.setCurrentIndex(0)

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

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not hasattr(self, "sidebar"):
            return
        self._apply_responsive_layout()

    def _apply_responsive_layout(self, *, force: bool = False) -> None:
        compact = self.width() < 840
        if not force and compact == self._compact_mode:
            return
        self._compact_mode = compact
        self.setProperty("compact", compact)
        refresh_style(self)

        self.sidebar.setVisible(not compact)
        self.compact_nav_button.setVisible(compact)
        self.header_date.setVisible(not compact and self.menu.currentRow() != 0)
        self.page_subtitle.setVisible(not compact)
        self.root_splitter.setHandleWidth(1 if compact else 6)
        self.shell_header_layout.setContentsMargins(
            12 if compact else 24,
            10 if compact else 16,
            12 if compact else 24,
            10 if compact else 16,
        )
        self.page_layout.setContentsMargins(
            10 if compact else 22,
            10 if compact else 18,
            10 if compact else 22,
            12 if compact else 22,
        )

        toolbar_widgets = (
            self.search_input,
            self.class_filter,
            self.manage_class_button,
            self.import_button,
            self.export_button,
            self.add_student_button,
            self.student_more_button,
        )
        for widget in toolbar_widgets:
            self.top_layout.removeWidget(widget)

        if compact:
            self.search_input.setMinimumWidth(0)
            self.class_filter.setMinimumWidth(110)
            self.manage_class_button.setVisible(False)
            self.import_button.setVisible(False)
            self.export_button.setVisible(False)
            self.student_more_button.setVisible(True)
            self.top_layout.addWidget(self.search_input, 0, 0, 1, 3)
            self.top_layout.addWidget(self.class_filter, 1, 0)
            self.top_layout.addWidget(self.add_student_button, 1, 1)
            self.top_layout.addWidget(self.student_more_button, 1, 2)
            self.top_layout.setColumnStretch(0, 1)
            self.top_layout.setColumnStretch(1, 0)
            self.top_layout.setColumnStretch(2, 0)
        else:
            self.search_input.setMinimumWidth(250)
            self.class_filter.setMinimumWidth(142)
            self.manage_class_button.setVisible(True)
            self.import_button.setVisible(True)
            self.export_button.setVisible(True)
            self.student_more_button.setVisible(False)
            self.top_layout.addWidget(self.search_input, 0, 0)
            self.top_layout.addWidget(self.class_filter, 0, 1)
            self.top_layout.addWidget(self.manage_class_button, 0, 2)
            self.top_layout.addWidget(self.import_button, 0, 3)
            self.top_layout.addWidget(self.export_button, 0, 4)
            self.top_layout.addWidget(self.add_student_button, 0, 5)
            self.top_layout.setColumnStretch(0, 1)

        self.workbench_view.set_compact_mode(compact)
        for view in (
            self.students_view,
            self.quality_view,
            self.scores_view,
            self.moral_view,
            self.attendance_view,
            self.planner_view,
            self.backup_view,
        ):
            handler = getattr(view, "set_compact_mode", None)
            if callable(handler):
                handler(compact)

    @staticmethod
    def _format_date(value: date) -> str:
        weekdays = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")
        return f"{value.year}年{value.month}月{value.day}日 {weekdays[value.weekday()]}"

    def _apply_style(self) -> None:
        style_path = RESOURCE_DIR / "styles.qss"
        if style_path.exists():
            self.setStyleSheet(style_path.read_text(encoding="utf-8"))
