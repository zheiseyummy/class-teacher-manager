from __future__ import annotations

from datetime import date
from typing import Any

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controllers.planner_controller import PlannerController, PlannerDataError
from utils.ui_layout import configure_resizable_table, restore_splitter


class TodayWorkbenchView(QWidget):
    """The compact daily desk shown when the application opens."""

    navigate_requested = Signal(int)
    planner_action_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = PlannerController()
        self._classes: list[dict[str, Any]] = []
        self._build_ui()
        self.refresh_classes()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        header = QFrame()
        header.setObjectName("workbenchHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(2, 0, 2, 0)
        header_layout.setSpacing(12)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title = QLabel("今日班级工作台")
        title.setObjectName("workbenchTitle")
        title_layout.addWidget(title)
        subtitle = QLabel("课程、日程和班级事务集中查看")
        subtitle.setObjectName("workbenchSubtitle")
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)
        header_layout.addStretch(1)

        self.class_box = QComboBox()
        self.class_box.setMinimumWidth(156)
        self.class_box.currentIndexChanged.connect(self.refresh)
        header_layout.addWidget(self.class_box)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.dateChanged.connect(self.refresh)
        header_layout.addWidget(self.date_edit)

        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh)
        header_layout.addWidget(self.refresh_button)
        layout.addWidget(header)

        quick_actions = QFrame()
        quick_actions.setObjectName("quickActions")
        quick_layout = QHBoxLayout(quick_actions)
        quick_layout.setContentsMargins(14, 10, 14, 10)
        quick_layout.setSpacing(10)
        quick_label = QLabel("快捷操作")
        quick_label.setObjectName("quickActionLabel")
        quick_layout.addWidget(quick_label)

        schedule_button = QPushButton("维护课程表")
        schedule_button.clicked.connect(lambda: self.planner_action_requested.emit("schedule"))
        quick_layout.addWidget(schedule_button)

        event_button = QPushButton("新建日程")
        event_button.setObjectName("primaryButton")
        event_button.clicked.connect(lambda: self.planner_action_requested.emit("calendar_new"))
        quick_layout.addWidget(event_button)

        attendance_button = QPushButton("登记考勤")
        attendance_button.clicked.connect(lambda: self.navigate_requested.emit(5))
        quick_layout.addWidget(attendance_button)

        moral_button = QPushButton("记录德育")
        moral_button.clicked.connect(lambda: self.navigate_requested.emit(4))
        quick_layout.addWidget(moral_button)
        quick_layout.addStretch(1)
        layout.addWidget(quick_actions)

        self.body_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.body_splitter.setChildrenCollapsible(False)
        self.left_splitter = QSplitter(Qt.Orientation.Vertical)
        self.left_splitter.setChildrenCollapsible(False)
        self.left_splitter.addWidget(self._build_course_panel())
        self.left_splitter.addWidget(self._build_event_panel())
        self.left_splitter.setStretchFactor(0, 1)
        self.left_splitter.setStretchFactor(1, 1)
        restore_splitter(self.left_splitter, "workbench_left", [260, 250])
        self.body_splitter.addWidget(self.left_splitter)
        self.body_splitter.addWidget(self._build_overview_panel())
        self.body_splitter.setStretchFactor(0, 1)
        self.body_splitter.setStretchFactor(1, 0)
        restore_splitter(self.body_splitter, "workbench_main", [820, 330])
        layout.addWidget(self.body_splitter, 1)

    def _build_course_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("workbenchPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        header = QHBoxLayout()
        title = QLabel("今日课程")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.course_summary = QLabel()
        self.course_summary.setObjectName("summaryText")
        header.addWidget(self.course_summary)
        layout.addLayout(header)

        self.daily_course_table = QTableWidget(0, 4)
        self.daily_course_table.setObjectName("dailyCourseTable")
        self.daily_course_table.setHorizontalHeaderLabels(["节次", "课程", "任课教师", "地点"])
        self.daily_course_table.setAlternatingRowColors(True)
        self.daily_course_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.daily_course_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.daily_course_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        configure_resizable_table(self.daily_course_table)
        self.daily_course_table.setColumnWidth(0, 90)
        self.daily_course_table.setColumnWidth(1, 176)
        self.daily_course_table.setColumnWidth(2, 160)
        self.daily_course_table.setColumnWidth(3, 178)
        layout.addWidget(self.daily_course_table, 1)
        return panel

    def _build_event_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("workbenchPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        header = QHBoxLayout()
        title = QLabel("今日待办与日程")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.event_summary = QLabel()
        self.event_summary.setObjectName("summaryText")
        header.addWidget(self.event_summary)
        layout.addLayout(header)

        self.daily_event_table = QTableWidget(0, 4)
        self.daily_event_table.setObjectName("dailyEventTable")
        self.daily_event_table.setHorizontalHeaderLabels(["时间", "事项", "类别", "备注"])
        self.daily_event_table.setAlternatingRowColors(True)
        self.daily_event_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.daily_event_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.daily_event_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        configure_resizable_table(self.daily_event_table)
        self.daily_event_table.setColumnWidth(0, 116)
        self.daily_event_table.setColumnWidth(1, 238)
        self.daily_event_table.setColumnWidth(2, 140)
        self.daily_event_table.setColumnWidth(3, 250)
        layout.addWidget(self.daily_event_table, 1)
        return panel

    def _build_overview_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("overviewPane")
        panel.setMinimumWidth(286)
        panel.setMaximumWidth(440)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("班级概览")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.class_badge = QLabel("请选择班级")
        self.class_badge.setObjectName("classBadge")
        self.class_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.class_badge.setMinimumHeight(38)
        layout.addWidget(self.class_badge)

        self.overview_date = QLabel()
        self.overview_date.setObjectName("summaryText")
        self.overview_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.overview_date)

        metric_grid = QGridLayout()
        metric_grid.setContentsMargins(0, 6, 0, 6)
        metric_grid.setHorizontalSpacing(12)
        metric_grid.setVerticalSpacing(18)
        self.metric_values: dict[str, QLabel] = {}
        for index, (key, label) in enumerate(
            (
                ("student_count", "在班学生"),
                ("course_count", "今日课程"),
                ("attendance_count", "考勤记录"),
                ("moral_count", "德育记录"),
            )
        ):
            item = QWidget()
            item_layout = QVBoxLayout(item)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(2)
            value = QLabel("--")
            value.setObjectName("metricValue")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            item_layout.addWidget(value)
            caption = QLabel(label)
            caption.setObjectName("metricLabel")
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            item_layout.addWidget(caption)
            metric_grid.addWidget(item, index // 2, index % 2)
            self.metric_values[key] = value
        layout.addLayout(metric_grid)

        self.overview_note = QLabel("从课程表和日历中维护当天安排。")
        self.overview_note.setObjectName("overviewNote")
        self.overview_note.setWordWrap(True)
        layout.addWidget(self.overview_note)
        layout.addStretch(1)
        return panel

    def refresh_classes(self) -> None:
        selected_class_id = self.class_box.currentData()
        self._classes = self.controller.list_classes()
        self.class_box.blockSignals(True)
        self.class_box.clear()
        for class_group in self._classes:
            self.class_box.addItem(class_group["name"], class_group["id"])
        selected_index = self.class_box.findData(selected_class_id)
        self.class_box.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        self.class_box.blockSignals(False)
        self.refresh()

    def refresh(self, *_args) -> None:
        class_group = self._selected_class()
        selected_date = self.date_edit.date().toPython()
        self.overview_date.setText(self._display_date(selected_date))
        if class_group is None:
            self._set_empty_state()
            return
        try:
            overview = self.controller.get_daily_overview(class_group["id"], selected_date)
        except PlannerDataError:
            self.refresh_classes()
            return
        self._apply_overview(overview, selected_date)

    def _apply_overview(self, overview: dict[str, Any], selected_date: date) -> None:
        class_group = overview["class"]
        self.class_badge.setText(class_group["name"])
        self.class_badge.setStyleSheet(
            f"background: {class_group['soft_color']}; color: {class_group['color']}; "
            "border: 1px solid rgba(0, 0, 0, 0.06); border-radius: 7px; font-weight: 600;"
        )
        self.overview_date.setText(self._display_date(selected_date))
        for key, label in self.metric_values.items():
            label.setText(str(overview["metrics"][key]))
        self.course_summary.setText(f"{overview['metrics']['course_count']} 节安排")
        self.event_summary.setText(f"{len(overview['events'])} 项日程")
        self.overview_note.setText("今日数据会随课程、日程、考勤和德育记录自动更新。")
        self._fill_course_table(overview["courses"], class_group)
        self._fill_event_table(overview["events"], class_group)

    def _fill_course_table(self, courses: list[dict[str, Any]], class_group: dict[str, Any]) -> None:
        self.daily_course_table.setRowCount(len(courses))
        for row, course in enumerate(courses):
            values = (
                f"第 {course['period']} 节",
                course["subject"],
                course["teacher"] or "--",
                course["location"] or "--",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                if column == 1:
                    item.setBackground(QColor(class_group["soft_color"]))
                    item.setForeground(QColor(class_group["color"]))
                    font = QFont(item.font())
                    font.setBold(True)
                    item.setFont(font)
                self.daily_course_table.setItem(row, column, item)

    def _fill_event_table(self, events: list[dict[str, Any]], class_group: dict[str, Any]) -> None:
        self.daily_event_table.setRowCount(len(events))
        for row, event in enumerate(events):
            values = (
                event["time_display"],
                event["title"],
                event["category"],
                event["note"] or "--",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                if column == 1:
                    item.setBackground(QColor(event["class_soft_color"]))
                    item.setForeground(QColor(event["class_color"]))
                    font = QFont(item.font())
                    font.setBold(True)
                    item.setFont(font)
                self.daily_event_table.setItem(row, column, item)

    def _set_empty_state(self) -> None:
        self.class_badge.setText("暂无班级")
        self.class_badge.setStyleSheet(
            "background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0; border-radius: 7px; font-weight: 600;"
        )
        for label in self.metric_values.values():
            label.setText("--")
        self.course_summary.setText("0 节安排")
        self.event_summary.setText("0 项日程")
        self.overview_note.setText("请先在学生数据中心建立班级和学生档案。")
        self.daily_course_table.setRowCount(0)
        self.daily_event_table.setRowCount(0)

    def _selected_class(self) -> dict[str, Any] | None:
        class_id = self.class_box.currentData()
        for class_group in self._classes:
            if class_group["id"] == class_id:
                return class_group
        return None

    @staticmethod
    def _display_date(value: date) -> str:
        weekday_labels = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
        return f"{value.isoformat()} {weekday_labels[value.weekday()]}"
