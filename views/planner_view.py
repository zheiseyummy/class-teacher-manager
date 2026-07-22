from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCalendarWidget,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controllers.planner_controller import PlannerController, PlannerDataError
from utils.ui_layout import configure_resizable_table, restore_splitter
from views.calendar_event_dialog import CalendarEventDialog
from views.teaching_schedule_view import TeachingScheduleView


class CourseCalendarView(QWidget):
    """Host the independent timetable alongside the existing class calendar."""

    data_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = PlannerController()
        self._calendar_classes: list[dict[str, Any]] = []
        self._marked_dates: list[QDate] = []
        self._build_ui()
        self.refresh_all()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("plannerTabs")
        self.schedule_view = TeachingScheduleView()
        self.schedule_view.data_changed.connect(self.data_changed)
        self.tabs.addTab(self.schedule_view, "课程表")
        self.tabs.addTab(self._build_calendar_tab(), "日历")
        layout.addWidget(self.tabs)

    def _build_calendar_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        toolbar = QFrame()
        toolbar.setObjectName("plannerToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 12, 16, 12)
        toolbar_layout.setSpacing(10)

        title = QLabel("班级日历")
        title.setObjectName("sectionTitle")
        toolbar_layout.addWidget(title)

        self.calendar_class_box = QComboBox()
        self.calendar_class_box.setMinimumWidth(180)
        self.calendar_class_box.currentIndexChanged.connect(self._refresh_calendar)
        toolbar_layout.addWidget(self.calendar_class_box)
        toolbar_layout.addStretch(1)

        add_button = QPushButton("新增日程")
        add_button.setObjectName("primaryButton")
        add_button.clicked.connect(self._add_event)
        toolbar_layout.addWidget(add_button)

        edit_button = QPushButton("编辑所选日程")
        edit_button.clicked.connect(self._edit_selected_event)
        toolbar_layout.addWidget(edit_button)

        delete_button = QPushButton("删除所选日程")
        delete_button.clicked.connect(self._delete_selected_event)
        toolbar_layout.addWidget(delete_button)
        layout.addWidget(toolbar)

        self.calendar_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.calendar_splitter.setChildrenCollapsible(False)

        calendar_pane = QFrame()
        calendar_pane.setObjectName("calendarPane")
        calendar_layout = QVBoxLayout(calendar_pane)
        calendar_layout.setContentsMargins(14, 14, 14, 14)
        calendar_layout.setSpacing(10)
        self.calendar_widget = QCalendarWidget()
        self.calendar_widget.setObjectName("classCalendar")
        self.calendar_widget.setGridVisible(False)
        self.calendar_widget.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.calendar_widget.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar_widget.selectionChanged.connect(self._refresh_events_for_selected_date)
        self.calendar_widget.currentPageChanged.connect(self._refresh_calendar_marks)
        calendar_layout.addWidget(self.calendar_widget, 1)
        self.calendar_splitter.addWidget(calendar_pane)

        events_pane = QFrame()
        events_pane.setObjectName("calendarEventsPane")
        events_layout = QVBoxLayout(events_pane)
        events_layout.setContentsMargins(0, 0, 0, 0)
        events_layout.setSpacing(10)
        self.calendar_date_label = QLabel()
        self.calendar_date_label.setObjectName("sectionTitle")
        events_layout.addWidget(self.calendar_date_label)
        hint = QLabel("日历中的浅色日期表示当天有班级或全局日程。")
        hint.setObjectName("summaryText")
        events_layout.addWidget(hint)

        self.event_table = QTableWidget(0, 5)
        self.event_table.setObjectName("eventTable")
        self.event_table.setHorizontalHeaderLabels(["时间", "日程", "班级", "类别", "备注"])
        self.event_table.setAlternatingRowColors(True)
        self.event_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.event_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.event_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.event_table.cellDoubleClicked.connect(lambda _row, _column: self._edit_selected_event())
        configure_resizable_table(self.event_table)
        self.event_table.setColumnWidth(0, 118)
        self.event_table.setColumnWidth(1, 220)
        self.event_table.setColumnWidth(2, 126)
        self.event_table.setColumnWidth(3, 120)
        self.event_table.setColumnWidth(4, 240)
        events_layout.addWidget(self.event_table, 1)
        self.calendar_splitter.addWidget(events_pane)

        self.calendar_splitter.setStretchFactor(0, 0)
        self.calendar_splitter.setStretchFactor(1, 1)
        restore_splitter(self.calendar_splitter, "planner_calendar", [360, 780])
        layout.addWidget(self.calendar_splitter, 1)
        return page

    def refresh_all(self) -> None:
        selected_class_id = self.calendar_class_box.currentData()
        self.schedule_view.refresh_all()
        self._calendar_classes = self.controller.list_classes()
        self._load_calendar_classes(selected_class_id)
        self._refresh_calendar()

    def show_course_tab(self) -> None:
        self.tabs.setCurrentIndex(0)
        self.schedule_view.refresh_all()

    def show_calendar_tab(self) -> None:
        self.tabs.setCurrentIndex(1)
        self._refresh_calendar()

    def open_new_event(self) -> None:
        self.show_calendar_tab()
        self._add_event()

    def _load_calendar_classes(self, selected_class_id: int | None) -> None:
        self.calendar_class_box.blockSignals(True)
        self.calendar_class_box.clear()
        self.calendar_class_box.addItem("全部学生班级和全局日程", None)
        for class_group in self._calendar_classes:
            self.calendar_class_box.addItem(class_group["name"], class_group["id"])
        index = self.calendar_class_box.findData(selected_class_id)
        self.calendar_class_box.setCurrentIndex(index if index >= 0 else 0)
        self.calendar_class_box.blockSignals(False)

    def _refresh_calendar(self, *_args) -> None:
        self._refresh_calendar_marks()
        self._refresh_events_for_selected_date()

    def _refresh_calendar_marks(self, *_args) -> None:
        for marked_date in self._marked_dates:
            self.calendar_widget.setDateTextFormat(marked_date, QTextCharFormat())
        self._marked_dates = []

        selected_class_id = self.calendar_class_box.currentData()
        year = self.calendar_widget.yearShown()
        month = self.calendar_widget.monthShown()
        start = QDate(year, month, 1)
        end = QDate(year, month, start.daysInMonth())
        events = self.controller.list_events(start.toPython(), end.toPython(), selected_class_id)
        grouped: dict[date, list[dict[str, Any]]] = defaultdict(list)
        for event in events:
            grouped[event["event_date"]].append(event)
        for event_date, date_events in grouped.items():
            format_ = QTextCharFormat()
            color = date_events[0]["class_soft_color"] if len(date_events) == 1 else "#E8EDF3"
            format_.setBackground(QColor(color))
            format_.setForeground(QColor("#243042"))
            marked_date = QDate(event_date.year, event_date.month, event_date.day)
            self.calendar_widget.setDateTextFormat(marked_date, format_)
            self._marked_dates.append(marked_date)

    def _refresh_events_for_selected_date(self, *_args) -> None:
        selected_date = self.calendar_widget.selectedDate().toPython()
        selected_class_id = self.calendar_class_box.currentData()
        events = self.controller.list_events(selected_date, selected_date, selected_class_id)
        weekday_labels = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
        self.calendar_date_label.setText(
            f"{selected_date.isoformat()} {weekday_labels[selected_date.weekday()]} 的日程"
        )
        self.event_table.setRowCount(len(events))
        for row, event in enumerate(events):
            time_item = QTableWidgetItem(event["time_display"])
            time_item.setData(Qt.ItemDataRole.UserRole, event["id"])
            title_item = QTableWidgetItem(event["title"])
            class_item = QTableWidgetItem(event["class_name"])
            class_item.setBackground(QColor(event["class_soft_color"]))
            class_item.setForeground(QColor(event["class_color"]))
            category_item = QTableWidgetItem(event["category"])
            note_item = QTableWidgetItem(event["note"])
            for item in (time_item, title_item, class_item, category_item, note_item):
                item.setToolTip(item.text())
            self.event_table.setItem(row, 0, time_item)
            self.event_table.setItem(row, 1, title_item)
            self.event_table.setItem(row, 2, class_item)
            self.event_table.setItem(row, 3, category_item)
            self.event_table.setItem(row, 4, note_item)

    def _add_event(self) -> None:
        dialog = CalendarEventDialog(
            self.controller,
            initial_date=self.calendar_widget.selectedDate().toPython(),
            initial_class_id=self.calendar_class_box.currentData(),
            parent=self,
        )
        if dialog.exec() and dialog.saved_event_id is not None:
            event = self.controller.get_event(dialog.saved_event_id)
            event_date = event["event_date"]
            self.calendar_widget.setSelectedDate(QDate(event_date.year, event_date.month, event_date.day))
            self._refresh_calendar()
            self.data_changed.emit()

    def _edit_selected_event(self) -> None:
        event_id = self._selected_event_id()
        if event_id is None:
            QMessageBox.information(self, "请选择日程", "请先选择要编辑的日程。")
            return
        dialog = CalendarEventDialog(self.controller, event_id=event_id, parent=self)
        if dialog.exec() and dialog.saved_event_id is not None:
            event = self.controller.get_event(dialog.saved_event_id)
            event_date = event["event_date"]
            self.calendar_widget.setSelectedDate(QDate(event_date.year, event_date.month, event_date.day))
            self._refresh_calendar()
            self.data_changed.emit()

    def _delete_selected_event(self) -> None:
        event_id = self._selected_event_id()
        if event_id is None:
            QMessageBox.information(self, "请选择日程", "请先选择要删除的日程。")
            return
        if QMessageBox.question(self, "删除日程", "确定删除所选日程吗？") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.controller.delete_event(event_id)
        except PlannerDataError as exc:
            QMessageBox.warning(self, "无法删除日程", str(exc))
            return
        self._refresh_calendar()
        self.data_changed.emit()

    def _selected_event_id(self) -> int | None:
        row = self.event_table.currentRow()
        if row < 0:
            return None
        item = self.event_table.item(row, 0)
        value = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return int(value) if value is not None else None
