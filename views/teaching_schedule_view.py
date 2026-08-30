from __future__ import annotations

from collections import defaultdict
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QToolButton,
    QWidget,
)

from controllers.teaching_schedule_controller import TeachingScheduleController, TeachingScheduleDataError
from utils.ui_icons import lucide_icon
from utils.ui_layout import configure_resizable_table
from views.semester_period_manager_dialog import SemesterPeriodManagerDialog
from views.teaching_course_dialog import TeachingCourseDialog
from views.teaching_group_manager_dialog import TeachingGroupManagerDialog


class TeachingScheduleView(QWidget):
    """Independent multi-group timetable with semester-specific periods."""

    data_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = TeachingScheduleController()
        self._semesters: list[dict[str, Any]] = []
        self._groups: list[dict[str, Any]] = []
        self._periods: list[dict[str, Any]] = []
        self._compact_mode = False
        self._build_ui()
        self.refresh_all()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        toolbar = QFrame()
        toolbar.setObjectName("plannerToolbar")
        self.toolbar_layout = QGridLayout(toolbar)
        self.toolbar_layout.setContentsMargins(12, 10, 12, 10)
        self.toolbar_layout.setHorizontalSpacing(8)
        self.toolbar_layout.setVerticalSpacing(8)

        self.toolbar_title = QLabel("课程范围")
        self.toolbar_title.setObjectName("toolbarContext")
        self.toolbar_layout.addWidget(self.toolbar_title, 0, 0)

        self.semester_box = QComboBox()
        self.semester_box.setMinimumWidth(238)
        self.semester_box.currentIndexChanged.connect(self._on_semester_changed)
        self.toolbar_layout.addWidget(self.semester_box, 0, 1)

        self.group_box = QComboBox()
        self.group_box.setMinimumWidth(176)
        self.group_box.currentIndexChanged.connect(self._on_group_changed)
        self.toolbar_layout.addWidget(self.group_box, 0, 2)

        self.group_color_swatch = QFrame()
        self.group_color_swatch.setObjectName("classColorSwatch")
        self.group_color_swatch.setFixedSize(18, 18)
        self.toolbar_layout.addWidget(self.group_color_swatch, 0, 3)
        self.toolbar_layout.setColumnStretch(4, 1)

        self.group_button = QPushButton("管理教学班")
        self.group_button.clicked.connect(self._manage_groups)
        self.toolbar_layout.addWidget(self.group_button, 0, 5)

        self.settings_button = QPushButton("学期与课时")
        self.settings_button.clicked.connect(self._manage_semesters_and_periods)
        self.toolbar_layout.addWidget(self.settings_button, 0, 6)

        self.add_course_button = QPushButton("新增课程")
        self.add_course_button.setObjectName("primaryButton")
        self.add_course_button.clicked.connect(self._add_or_edit_course)
        self.add_course_button.setIcon(
            lucide_icon("calendar-plus", color="#FFFFFF", active_color="#FFFFFF")
        )
        self.toolbar_layout.addWidget(self.add_course_button, 0, 7)

        self.delete_course_button = QPushButton("删除所选课程")
        self.delete_course_button.setObjectName("dangerButton")
        self.delete_course_button.clicked.connect(self._delete_selected_course)
        self.toolbar_layout.addWidget(self.delete_course_button, 0, 8)

        self.more_button = QToolButton()
        self.more_button.setObjectName("moreButton")
        self.more_button.setText("更多")
        self.more_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.more_button.setIcon(lucide_icon("clipboard-check"))
        self.more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        more_menu = QMenu(self.more_button)
        more_menu.addAction("管理教学班", self._manage_groups)
        more_menu.addAction("学期与课时", self._manage_semesters_and_periods)
        more_menu.addSeparator()
        more_menu.addAction("删除所选课程", self._delete_selected_course)
        self.more_button.setMenu(more_menu)
        self.more_button.setVisible(False)
        self.toolbar_layout.addWidget(self.more_button, 0, 9)
        layout.addWidget(toolbar)

        self.status_line = QLabel()
        self.status_line.setObjectName("summaryText")
        layout.addWidget(self.status_line)

        self.course_table = QTableWidget(0, len(self.controller.WEEKDAYS))
        self.course_table.setObjectName("courseTable")
        self.course_table.setHorizontalHeaderLabels([label for _weekday, label in self.controller.WEEKDAYS])
        self.course_table.setAlternatingRowColors(False)
        self.course_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.course_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.course_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.course_table.cellDoubleClicked.connect(self._double_click_course_cell)
        configure_resizable_table(self.course_table)
        self.course_table.verticalHeader().setDefaultSectionSize(68)
        self.course_table.setMinimumHeight(470)
        for column in range(self.course_table.columnCount()):
            self.course_table.setColumnWidth(column, 150)
        layout.addWidget(self.course_table, 1)

    def refresh_all(self) -> None:
        selected_semester_id = self.semester_box.currentData()
        selected_group_id = self.group_box.currentData()
        self._semesters = self.controller.list_semesters()
        self._groups = self.controller.list_teaching_groups()
        self._load_semesters(selected_semester_id)
        self._load_groups(selected_group_id)
        self._refresh_timetable()

    def _load_semesters(self, selected_semester_id: int | None) -> None:
        self.semester_box.blockSignals(True)
        self.semester_box.clear()
        if not self._semesters:
            self.semester_box.addItem("请先建立学期", None)
        else:
            for semester in self._semesters:
                current_suffix = "（当前）" if semester["is_current"] else ""
                self.semester_box.addItem(
                    f"{semester['name']}{current_suffix}",
                    semester["id"],
                )
        index = self.semester_box.findData(selected_semester_id)
        self.semester_box.setCurrentIndex(index if index >= 0 else 0)
        self.semester_box.blockSignals(False)

    def _load_groups(self, selected_group_id: int | None) -> None:
        self.group_box.blockSignals(True)
        self.group_box.clear()
        self.group_box.addItem("全部教学班（汇总）", None)
        for group in self._groups:
            self.group_box.addItem(self._color_icon(group["color"]), group["name"], group["id"])
        index = self.group_box.findData(selected_group_id)
        self.group_box.setCurrentIndex(index if index >= 0 else 0)
        self.group_box.blockSignals(False)
        self._refresh_group_swatch()

    def _on_semester_changed(self, _index: int) -> None:
        self._refresh_timetable()

    def _on_group_changed(self, _index: int) -> None:
        self._refresh_group_swatch()
        self._refresh_timetable()

    def _refresh_group_swatch(self) -> None:
        group = self._selected_group()
        if group is None:
            self.group_color_swatch.setStyleSheet("background: #d7dee8; border-radius: 4px;")
            return
        self.group_color_swatch.setStyleSheet(
            f"background: {group['color']}; border: 1px solid rgba(0, 0, 0, 0.08); border-radius: 4px;"
        )

    def _refresh_timetable(self) -> None:
        self.course_table.clearContents()
        semester = self._selected_semester()
        group = self._selected_group()
        self._periods = []
        if semester is None:
            self.course_table.setRowCount(0)
            self.status_line.setText("请点击“学期与课时”建立学期、日期范围和当天课时设置。")
            self.add_course_button.setEnabled(False)
            self.delete_course_button.setEnabled(False)
            return
        self._periods = self.controller.list_periods(semester["id"])
        self.course_table.setRowCount(len(self._periods))
        self.course_table.setVerticalHeaderLabels(
            [
                f"{period['sort_order']}  {period['name']}\n{period['time_display']}"
                for period in self._periods
            ]
        )
        if not self._periods:
            self.status_line.setText(
                f"{semester['name']}：请在“学期与课时”中增加课时，课程表会按课时数量自动扩展。"
            )
            self.add_course_button.setEnabled(False)
            self.delete_course_button.setEnabled(False)
            return
        if not self._groups:
            self.status_line.setText("请先点击“管理教学班”新增教学班；它不需要在学生数据中心预先建班。")
            self.add_course_button.setEnabled(False)
            self.delete_course_button.setEnabled(False)
            return

        courses = self.controller.list_courses(semester["id"], group["id"] if group else None)
        grouped_courses: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
        for course in courses:
            grouped_courses[(course["weekday"], course["period_id"])].append(course)
        period_rows = {period["id"]: index for index, period in enumerate(self._periods)}
        for (weekday, period_id), cell_courses in grouped_courses.items():
            row = period_rows.get(period_id)
            if row is None:
                continue
            column = weekday - 1
            self.course_table.setItem(row, column, self._course_item(cell_courses, aggregate=group is None))

        if group is None:
            self.status_line.setText(
                f"{semester['name']}（{semester['date_range_display']}）：汇总显示 {len(self._groups)} 个教学班；选择单个教学班后可直接编辑。"
            )
            self.add_course_button.setEnabled(False)
            self.delete_course_button.setEnabled(False)
        else:
            self.status_line.setText(
                f"{semester['name']}（{semester['date_range_display']}） · {group['name']} · {len(self._periods)} 个自定义课时"
            )
            self.add_course_button.setEnabled(True)
            self.delete_course_button.setEnabled(True)

    def _course_item(self, courses: list[dict[str, Any]], aggregate: bool) -> QTableWidgetItem:
        if aggregate and len(courses) > 1:
            text = "\n".join(f"{course['teaching_group_name']} · {course['subject']}" for course in courses)
            item = QTableWidgetItem(text)
            item.setBackground(QColor("#F1F5F9"))
            item.setForeground(QColor("#475569"))
            item.setToolTip("\n\n".join(self._course_tooltip(course) for course in courses))
            return item
        course = courses[0]
        if aggregate:
            lines = [f"{course['teaching_group_name']} · {course['subject']}"]
        else:
            lines = [course["subject"]]
        if course["teacher"]:
            lines.append(course["teacher"])
        if course["location"]:
            lines.append(course["location"])
        item = QTableWidgetItem("\n".join(lines))
        item.setData(Qt.ItemDataRole.UserRole, course["id"])
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setToolTip(self._course_tooltip(course))
        item.setBackground(QColor(course["group_soft_color"]))
        item.setForeground(QColor(course["group_color"]))
        font = QFont(item.font())
        font.setBold(True)
        item.setFont(font)
        return item

    def _double_click_course_cell(self, row: int, column: int) -> None:
        semester = self._selected_semester()
        group = self._selected_group()
        if semester is None:
            self._manage_semesters_and_periods()
            return
        if group is None:
            QMessageBox.information(self, "请选择教学班", "汇总视图用于查看，请先选择单个教学班后再新增或编辑课程。")
            return
        item = self.course_table.item(row, column)
        course_id = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        period_id = self._periods[row]["id"] if 0 <= row < len(self._periods) else None
        self._add_or_edit_course(course_id, column + 1, period_id)

    def _add_or_edit_course(
        self,
        course_id: int | None = None,
        weekday: int | None = None,
        period_id: int | None = None,
    ) -> None:
        semester = self._selected_semester()
        group = self._selected_group()
        if semester is None or group is None:
            QMessageBox.information(self, "请先完成设置", "请先选择一个学期和教学班。")
            return
        if course_id is None:
            current_item = self.course_table.currentItem()
            current_index = self.course_table.currentIndex()
            if current_item is not None:
                course_id = current_item.data(Qt.ItemDataRole.UserRole)
            if current_index.isValid():
                if weekday is None:
                    weekday = current_index.column() + 1
                if period_id is None and 0 <= current_index.row() < len(self._periods):
                    period_id = self._periods[current_index.row()]["id"]
        dialog = TeachingCourseDialog(
            self.controller,
            course_id=course_id,
            initial_semester_id=semester["id"],
            initial_group_id=group["id"],
            initial_weekday=weekday,
            initial_period_id=period_id,
            parent=self,
        )
        if dialog.exec() and dialog.saved_course_id is not None:
            self._refresh_timetable()
            self.data_changed.emit()

    def _delete_selected_course(self) -> None:
        item = self.course_table.currentItem()
        course_id = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if course_id is None:
            QMessageBox.information(self, "请选择课程", "请先选择要删除的课程。")
            return
        if QMessageBox.question(self, "删除课程", "确定删除所选课程吗？") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.controller.delete_course(int(course_id))
        except TeachingScheduleDataError as exc:
            QMessageBox.warning(self, "无法删除课程", str(exc))
            return
        self._refresh_timetable()
        self.data_changed.emit()

    def _manage_groups(self) -> None:
        dialog = TeachingGroupManagerDialog(self.controller, parent=self)
        dialog.exec()
        if dialog.changed:
            self.refresh_all()
            self.data_changed.emit()

    def _manage_semesters_and_periods(self) -> None:
        dialog = SemesterPeriodManagerDialog(self.controller, parent=self)
        dialog.exec()
        if dialog.changed:
            self.refresh_all()
            self.data_changed.emit()

    def _selected_semester(self) -> dict[str, Any] | None:
        semester_id = self.semester_box.currentData()
        for semester in self._semesters:
            if semester["id"] == semester_id:
                return semester
        return None

    def _selected_group(self) -> dict[str, Any] | None:
        group_id = self.group_box.currentData()
        for group in self._groups:
            if group["id"] == group_id:
                return group
        return None

    @staticmethod
    def _color_icon(color: str) -> QIcon:
        pixmap = QPixmap(14, 14)
        pixmap.fill(QColor(color))
        return QIcon(pixmap)

    @staticmethod
    def _course_tooltip(course: dict[str, Any]) -> str:
        lines = [f"{course['teaching_group_name']} · {course['subject']}"]
        lines.append(f"课时：{course['period_name']} {course['period_start_time']} - {course['period_end_time']}")
        if course["teacher"]:
            lines.append(f"教师：{course['teacher']}")
        if course["location"]:
            lines.append(f"地点：{course['location']}")
        if course["note"]:
            lines.append(f"备注：{course['note']}")
        return "\n".join(lines)

    def set_compact_mode(self, compact: bool) -> None:
        if compact == self._compact_mode:
            return
        self._compact_mode = compact
        self.toolbar_title.setVisible(not compact)
        self.group_button.setVisible(not compact)
        self.settings_button.setVisible(not compact)
        self.delete_course_button.setVisible(not compact)
        self.more_button.setVisible(compact)

        toolbar_widgets = (
            self.semester_box,
            self.group_box,
            self.group_color_swatch,
            self.group_button,
            self.settings_button,
            self.add_course_button,
            self.delete_course_button,
            self.more_button,
        )
        for widget in toolbar_widgets:
            self.toolbar_layout.removeWidget(widget)
        if compact:
            self.semester_box.setMinimumWidth(0)
            self.group_box.setMinimumWidth(0)
            self.toolbar_layout.addWidget(self.semester_box, 0, 0, 1, 3)
            self.toolbar_layout.addWidget(self.group_box, 1, 0, 1, 2)
            self.toolbar_layout.addWidget(self.group_color_swatch, 1, 2)
            self.toolbar_layout.addWidget(self.add_course_button, 2, 0, 1, 2)
            self.toolbar_layout.addWidget(self.more_button, 2, 2)
            self.toolbar_layout.setColumnStretch(0, 1)
        else:
            self.semester_box.setMinimumWidth(238)
            self.group_box.setMinimumWidth(176)
            self.toolbar_layout.addWidget(self.semester_box, 0, 1)
            self.toolbar_layout.addWidget(self.group_box, 0, 2)
            self.toolbar_layout.addWidget(self.group_color_swatch, 0, 3)
            self.toolbar_layout.addWidget(self.group_button, 0, 5)
            self.toolbar_layout.addWidget(self.settings_button, 0, 6)
            self.toolbar_layout.addWidget(self.add_course_button, 0, 7)
            self.toolbar_layout.addWidget(self.delete_course_button, 0, 8)
            self.toolbar_layout.setColumnStretch(4, 1)
        self.course_table.setMinimumHeight(340 if compact else 470)
