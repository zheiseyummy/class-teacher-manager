from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controllers.teaching_schedule_controller import TeachingScheduleController, TeachingScheduleDataError
from utils.ui_layout import configure_resizable_table
from views.teaching_group_dialog import TeachingGroupDialog


class TeachingGroupManagerDialog(QDialog):
    """Maintain timetable teaching groups without entering the student module."""

    def __init__(self, controller: TeachingScheduleController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.changed = False
        self.setWindowTitle("管理教学班")
        self.resize(820, 500)
        self.setMinimumSize(680, 420)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel("教学班")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        hint = QLabel("教学班可独立使用，也可选关联已有学生班级。")
        hint.setObjectName("summaryText")
        header.addWidget(hint)
        header.addStretch(1)
        add_button = QPushButton("新增教学班")
        add_button.setObjectName("primaryButton")
        add_button.clicked.connect(self._add_group)
        header.addWidget(add_button)
        edit_button = QPushButton("编辑")
        edit_button.clicked.connect(self._edit_group)
        header.addWidget(edit_button)
        delete_button = QPushButton("删除")
        delete_button.clicked.connect(self._delete_group)
        header.addWidget(delete_button)
        layout.addLayout(header)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["教学班", "颜色", "关联学生班级", "课程数", "备注"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self._edit_group())
        configure_resizable_table(self.table)
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 190)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 260)
        layout.addWidget(self.table, 1)

        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)

    def refresh(self, selected_group_id: int | None = None) -> None:
        if selected_group_id is None:
            selected_group_id = self._selected_group_id()
        groups = self.controller.list_teaching_groups()
        self.table.setRowCount(len(groups))
        for row, group in enumerate(groups):
            name_item = QTableWidgetItem(group["name"])
            name_item.setData(Qt.ItemDataRole.UserRole, group["id"])
            color_item = QTableWidgetItem(group["color_name"])
            color_item.setBackground(QColor(group["soft_color"]))
            color_item.setForeground(QColor(group["color"]))
            linked_item = QTableWidgetItem(group["linked_class_name"] or "独立教学班")
            count_item = QTableWidgetItem(str(group["course_count"]))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            note_item = QTableWidgetItem(group["note"])
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, color_item)
            self.table.setItem(row, 2, linked_item)
            self.table.setItem(row, 3, count_item)
            self.table.setItem(row, 4, note_item)
            if group["id"] == selected_group_id:
                self.table.setCurrentCell(row, 0)

    def _add_group(self) -> None:
        dialog = TeachingGroupDialog(self.controller, parent=self)
        if dialog.exec() and dialog.saved_group_id is not None:
            self.changed = True
            self.refresh(dialog.saved_group_id)

    def _edit_group(self) -> None:
        group_id = self._selected_group_id()
        if group_id is None:
            QMessageBox.information(self, "请选择教学班", "请先选择要编辑的教学班。")
            return
        dialog = TeachingGroupDialog(self.controller, group_id=group_id, parent=self)
        if dialog.exec() and dialog.saved_group_id is not None:
            self.changed = True
            self.refresh(dialog.saved_group_id)

    def _delete_group(self) -> None:
        group_id = self._selected_group_id()
        if group_id is None:
            QMessageBox.information(self, "请选择教学班", "请先选择要删除的教学班。")
            return
        if QMessageBox.question(self, "删除教学班", "确定删除所选教学班吗？") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.controller.delete_teaching_group(group_id)
        except TeachingScheduleDataError as exc:
            QMessageBox.warning(self, "无法删除教学班", str(exc))
            return
        self.changed = True
        self.refresh()

    def _selected_group_id(self) -> int | None:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        value = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return int(value) if value is not None else None
