from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controllers.teaching_schedule_controller import TeachingScheduleController, TeachingScheduleDataError
from utils.ui_layout import (
    configure_resizable_table,
    configure_responsive_dialog,
    restore_splitter,
)
from views.schedule_period_dialog import SchedulePeriodDialog
from views.semester_dialog import SemesterDialog


class SemesterPeriodManagerDialog(QDialog):
    """Manage non-overlapping semesters and their custom daily periods."""

    def __init__(self, controller: TeachingScheduleController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.changed = False
        self.setWindowTitle("学期与课时设置")
        self._build_ui()
        configure_responsive_dialog(self, 860, 680, minimum_height=480)
        self.refresh()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(22, 20, 22, 20)
        root_layout.setSpacing(12)
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self._build_semester_pane())
        self.splitter.addWidget(self._build_period_pane())
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        restore_splitter(self.splitter, "semester_period_manager", [300, 340])
        root_layout.addWidget(self.splitter, 1)
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        root_layout.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)

    def _build_semester_pane(self) -> QWidget:
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        header = QHBoxLayout()
        title = QLabel("学期")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        hint = QLabel("日期范围不能与其他有效学期重叠。")
        hint.setObjectName("summaryText")
        header.addWidget(hint)
        header.addStretch(1)
        add_button = QPushButton("新增学期")
        add_button.setObjectName("primaryButton")
        add_button.clicked.connect(self._add_semester)
        header.addWidget(add_button)
        edit_button = QPushButton("编辑")
        edit_button.clicked.connect(self._edit_semester)
        header.addWidget(edit_button)
        delete_button = QPushButton("删除")
        delete_button.setObjectName("dangerButton")
        delete_button.clicked.connect(self._delete_semester)
        header.addWidget(delete_button)
        layout.addLayout(header)

        self.semester_table = QTableWidget(0, 4)
        self.semester_table.setHorizontalHeaderLabels(["学期", "日期范围", "当前", "课时数"])
        self.semester_table.setAlternatingRowColors(True)
        self.semester_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.semester_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.semester_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.semester_table.itemSelectionChanged.connect(self._refresh_periods)
        self.semester_table.cellDoubleClicked.connect(lambda _row, _column: self._edit_semester())
        configure_resizable_table(self.semester_table)
        self.semester_table.setColumnWidth(0, 220)
        self.semester_table.setColumnWidth(1, 250)
        self.semester_table.setColumnWidth(2, 74)
        self.semester_table.setColumnWidth(3, 86)
        layout.addWidget(self.semester_table, 1)
        return pane

    def _build_period_pane(self) -> QWidget:
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        header = QHBoxLayout()
        self.period_title = QLabel("课时")
        self.period_title.setObjectName("sectionTitle")
        header.addWidget(self.period_title)
        self.period_hint = QLabel("一个学期可以按实际需要设置任意数量的课时。")
        self.period_hint.setObjectName("summaryText")
        header.addWidget(self.period_hint)
        header.addStretch(1)
        self.add_period_button = QPushButton("新增课时")
        self.add_period_button.setObjectName("primaryButton")
        self.add_period_button.clicked.connect(self._add_period)
        header.addWidget(self.add_period_button)
        self.edit_period_button = QPushButton("编辑")
        self.edit_period_button.clicked.connect(self._edit_period)
        header.addWidget(self.edit_period_button)
        self.delete_period_button = QPushButton("删除")
        self.delete_period_button.setObjectName("dangerButton")
        self.delete_period_button.clicked.connect(self._delete_period)
        header.addWidget(self.delete_period_button)
        layout.addLayout(header)

        self.period_table = QTableWidget(0, 4)
        self.period_table.setHorizontalHeaderLabels(["顺序", "课时名称", "时间", "备注"])
        self.period_table.setAlternatingRowColors(True)
        self.period_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.period_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.period_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.period_table.cellDoubleClicked.connect(lambda _row, _column: self._edit_period())
        configure_resizable_table(self.period_table)
        self.period_table.setColumnWidth(0, 76)
        self.period_table.setColumnWidth(1, 180)
        self.period_table.setColumnWidth(2, 160)
        self.period_table.setColumnWidth(3, 320)
        layout.addWidget(self.period_table, 1)
        return pane

    def refresh(self, selected_semester_id: int | None = None) -> None:
        if selected_semester_id is None:
            selected_semester_id = self._selected_semester_id()
        semesters = self.controller.list_semesters()
        self.semester_table.blockSignals(True)
        self.semester_table.setRowCount(len(semesters))
        for row, semester in enumerate(semesters):
            name_item = QTableWidgetItem(semester["name"])
            name_item.setData(Qt.ItemDataRole.UserRole, semester["id"])
            range_item = QTableWidgetItem(semester["date_range_display"])
            current_item = QTableWidgetItem("当前" if semester["is_current"] else "")
            current_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            count_item = QTableWidgetItem(str(semester["period_count"]))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.semester_table.setItem(row, 0, name_item)
            self.semester_table.setItem(row, 1, range_item)
            self.semester_table.setItem(row, 2, current_item)
            self.semester_table.setItem(row, 3, count_item)
            if semester["id"] == selected_semester_id:
                self.semester_table.setCurrentCell(row, 0)
        self.semester_table.blockSignals(False)
        if self.semester_table.currentRow() < 0 and semesters:
            self.semester_table.setCurrentCell(0, 0)
        self._refresh_periods()

    def _refresh_periods(self) -> None:
        semester_id = self._selected_semester_id()
        enabled = semester_id is not None
        self.add_period_button.setEnabled(enabled)
        self.edit_period_button.setEnabled(enabled)
        self.delete_period_button.setEnabled(enabled)
        self.period_table.setRowCount(0)
        if semester_id is None:
            self.period_title.setText("课时")
            self.period_hint.setText("请先建立并选择一个学期。")
            return
        semester = self.controller.get_semester(semester_id)
        self.period_title.setText(f"课时 - {semester['name']}")
        self.period_hint.setText("新增、删除课时即可调整每天可排课程数量和时间。")
        periods = self.controller.list_periods(semester_id)
        self.period_table.setRowCount(len(periods))
        for row, period in enumerate(periods):
            order_item = QTableWidgetItem(str(period["sort_order"]))
            order_item.setData(Qt.ItemDataRole.UserRole, period["id"])
            name_item = QTableWidgetItem(period["name"])
            time_item = QTableWidgetItem(period["time_display"])
            note_item = QTableWidgetItem(period["note"])
            self.period_table.setItem(row, 0, order_item)
            self.period_table.setItem(row, 1, name_item)
            self.period_table.setItem(row, 2, time_item)
            self.period_table.setItem(row, 3, note_item)

    def _add_semester(self) -> None:
        dialog = SemesterDialog(self.controller, parent=self)
        if dialog.exec() and dialog.saved_semester_id is not None:
            self.changed = True
            self.refresh(dialog.saved_semester_id)

    def _edit_semester(self) -> None:
        semester_id = self._selected_semester_id()
        if semester_id is None:
            QMessageBox.information(self, "请选择学期", "请先选择要编辑的学期。")
            return
        dialog = SemesterDialog(self.controller, semester_id=semester_id, parent=self)
        if dialog.exec() and dialog.saved_semester_id is not None:
            self.changed = True
            self.refresh(dialog.saved_semester_id)

    def _delete_semester(self) -> None:
        semester_id = self._selected_semester_id()
        if semester_id is None:
            QMessageBox.information(self, "请选择学期", "请先选择要删除的学期。")
            return
        if QMessageBox.question(self, "删除学期", "确定删除所选学期及无课程的课时设置吗？") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.controller.delete_semester(semester_id)
        except TeachingScheduleDataError as exc:
            QMessageBox.warning(self, "无法删除学期", str(exc))
            return
        self.changed = True
        self.refresh()

    def _add_period(self) -> None:
        semester_id = self._selected_semester_id()
        if semester_id is None:
            return
        dialog = SchedulePeriodDialog(self.controller, semester_id=semester_id, parent=self)
        if dialog.exec() and dialog.saved_period_id is not None:
            self.changed = True
            self._refresh_periods()
            self._select_period(dialog.saved_period_id)

    def _edit_period(self) -> None:
        period_id = self._selected_period_id()
        semester_id = self._selected_semester_id()
        if period_id is None or semester_id is None:
            QMessageBox.information(self, "请选择课时", "请先选择要编辑的课时。")
            return
        dialog = SchedulePeriodDialog(self.controller, semester_id=semester_id, period_id=period_id, parent=self)
        if dialog.exec() and dialog.saved_period_id is not None:
            self.changed = True
            self._refresh_periods()
            self._select_period(dialog.saved_period_id)

    def _delete_period(self) -> None:
        period_id = self._selected_period_id()
        if period_id is None:
            QMessageBox.information(self, "请选择课时", "请先选择要删除的课时。")
            return
        if QMessageBox.question(self, "删除课时", "确定删除所选课时吗？") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.controller.delete_period(period_id)
        except TeachingScheduleDataError as exc:
            QMessageBox.warning(self, "无法删除课时", str(exc))
            return
        self.changed = True
        self._refresh_periods()

    def _selected_semester_id(self) -> int | None:
        row = self.semester_table.currentRow()
        item = self.semester_table.item(row, 0) if row >= 0 else None
        value = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return int(value) if value is not None else None

    def _selected_period_id(self) -> int | None:
        row = self.period_table.currentRow()
        item = self.period_table.item(row, 0) if row >= 0 else None
        value = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return int(value) if value is not None else None

    def _select_period(self, period_id: int) -> None:
        for row in range(self.period_table.rowCount()):
            item = self.period_table.item(row, 0)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == period_id:
                self.period_table.setCurrentCell(row, 0)
                return
