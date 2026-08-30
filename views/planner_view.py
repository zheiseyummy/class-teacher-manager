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
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QMenu,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QToolButton,
    QWidget,
)

from controllers.planner_controller import PlannerController, PlannerDataError
from utils.ui_icons import lucide_icon
from utils.ui_layout import configure_resizable_table, restore_splitter, set_compact_columns
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
        self._compact_mode = False
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
        self.calendar_toolbar_layout = QGridLayout(toolbar)
        self.calendar_toolbar_layout.setContentsMargins(12, 10, 12, 10)
        self.calendar_toolbar_layout.setHorizontalSpacing(8)
        self.calendar_toolbar_layout.setVerticalSpacing(8)

        self.calendar_title = QLabel("日程范围")
        self.calendar_title.setObjectName("toolbarContext")
        self.calendar_toolbar_layout.addWidget(self.calendar_title, 0, 0)

        self.calendar_class_box = QComboBox()
        self.calendar_class_box.setMinimumWidth(180)
        self.calendar_class_box.currentIndexChanged.connect(self._refresh_calendar)
        self.calendar_toolbar_layout.addWidget(self.calendar_class_box, 0, 1)
        self.calendar_toolbar_layout.setColumnStretch(2, 1)

        self.add_event_button = QPushButton("新增日程")
        self.add_event_button.setObjectName("primaryButton")
        self.add_event_button.setIcon(
            lucide_icon("calendar-plus", color="#FFFFFF", active_color="#FFFFFF")
        )
        self.add_event_button.clicked.connect(self._add_event)
        self.calendar_toolbar_layout.addWidget(self.add_event_button, 0, 3)

        self.edit_event_button = QPushButton("编辑所选日程")
        self.edit_event_button.clicked.connect(self._edit_selected_event)
        self.calendar_toolbar_layout.addWidget(self.edit_event_button, 0, 4)

        self.delete_event_button = QPushButton("删除所选日程")
        self.delete_event_button.setObjectName("dangerButton")
        self.delete_event_button.clicked.connect(self._delete_selected_event)
        self.calendar_toolbar_layout.addWidget(self.delete_event_button, 0, 5)

        self.calendar_more_button = QToolButton()
        self.calendar_more_button.setObjectName("moreButton")
        self.calendar_more_button.setText("更多")
        self.calendar_more_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.calendar_more_button.setIcon(lucide_icon("clipboard-check"))
        self.calendar_more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        more_menu = QMenu(self.calendar_more_button)
        more_menu.addAction("编辑所选日程", self._edit_selected_event)
        more_menu.addAction("删除所选日程", self._delete_selected_event)
        self.calendar_more_button.setMenu(more_menu)
        self.calendar_more_button.setVisible(False)
        self.calendar_toolbar_layout.addWidget(self.calendar_more_button, 0, 6)
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

    def set_compact_mode(self, compact: bool) -> None:
        if compact == self._compact_mode:
            return
        self._compact_mode = compact
        self.schedule_view.set_compact_mode(compact)
        self.calendar_title.setVisible(not compact)
        self.edit_event_button.setVisible(not compact)
        self.delete_event_button.setVisible(not compact)
        self.calendar_more_button.setVisible(compact)

        toolbar_widgets = (
            self.calendar_class_box,
            self.add_event_button,
            self.edit_event_button,
            self.delete_event_button,
            self.calendar_more_button,
        )
        for widget in toolbar_widgets:
            self.calendar_toolbar_layout.removeWidget(widget)
        if compact:
            self.calendar_class_box.setMinimumWidth(0)
            self.calendar_toolbar_layout.addWidget(self.calendar_class_box, 0, 0, 1, 2)
            self.calendar_toolbar_layout.addWidget(self.add_event_button, 1, 0)
            self.calendar_toolbar_layout.addWidget(self.calendar_more_button, 1, 1)
            self.calendar_toolbar_layout.setColumnStretch(0, 1)
        else:
            self.calendar_class_box.setMinimumWidth(180)
            self.calendar_toolbar_layout.addWidget(self.calendar_class_box, 0, 1)
            self.calendar_toolbar_layout.addWidget(self.add_event_button, 0, 3)
            self.calendar_toolbar_layout.addWidget(self.edit_event_button, 0, 4)
            self.calendar_toolbar_layout.addWidget(self.delete_event_button, 0, 5)
            self.calendar_toolbar_layout.setColumnStretch(2, 1)

        self.calendar_splitter.setOrientation(
            Qt.Orientation.Vertical if compact else Qt.Orientation.Horizontal
        )
        set_compact_columns(self.event_table, (2, 3, 4), compact)
        self.calendar_splitter.setSizes([320, 340] if compact else [360, 780])
