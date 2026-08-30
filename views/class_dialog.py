from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controllers.student_controller import StudentController, StudentDataError
from utils.ui_layout import configure_resizable_table, configure_responsive_dialog


class ClassEditDialog(QDialog):
    def __init__(self, controller: StudentController, class_data: dict[str, Any] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.class_data = class_data
        self.setWindowTitle("编辑班级" if class_data else "新增班级")
        self._build_ui()
        configure_responsive_dialog(self, 460)
        if class_data:
            self._load_data(class_data)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如：初三1班")
        self.grade_input = QLineEdit()
        self.grade_input.setPlaceholderText("例如：初三")
        self.school_year_input = QLineEdit()
        self.school_year_input.setPlaceholderText("例如：2026-2027")
        self.teacher_input = QLineEdit()
        self.note_input = QPlainTextEdit()
        self.note_input.setFixedHeight(76)
        form.addRow("班级名称 *", self.name_input)
        form.addRow("年级", self.grade_input)
        form.addRow("学年", self.school_year_input)
        form.addRow("班主任", self.teacher_input)
        form.addRow("备注", self.note_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_data(self, class_data: dict[str, Any]) -> None:
        self.name_input.setText(class_data["name"])
        self.grade_input.setText(class_data["grade"])
        self.school_year_input.setText(class_data["school_year"])
        self.teacher_input.setText(class_data["head_teacher"])
        self.note_input.setPlainText(class_data["note"])

    def _save(self) -> None:
        data = {
            "name": self.name_input.text(),
            "grade": self.grade_input.text(),
            "school_year": self.school_year_input.text(),
            "head_teacher": self.teacher_input.text(),
            "note": self.note_input.toPlainText(),
        }
        try:
            if self.class_data:
                self.controller.update_class(int(self.class_data["id"]), data)
            else:
                self.controller.create_class(data)
        except StudentDataError as exc:
            QMessageBox.warning(self, "无法保存", str(exc))
            return
        except Exception:
            QMessageBox.warning(self, "无法保存", "班级名称和学年不能重复。")
            return
        self.accept()


class ClassManagementDialog(QDialog):
    classes_changed = Signal()

    def __init__(self, controller: StudentController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.class_rows: list[dict[str, Any]] = []
        self.setWindowTitle("班级管理")
        self._build_ui()
        configure_responsive_dialog(self, 760, 500, minimum_height=360)
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        heading = QHBoxLayout()
        heading.addWidget(QLabel("班级"))
        heading.addStretch(1)
        add_button = QPushButton("新增班级")
        add_button.setObjectName("primaryButton")
        add_button.clicked.connect(self._add_class)
        heading.addWidget(add_button)
        layout.addLayout(heading)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["班级", "年级", "学年", "班主任", "学生数"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        configure_resizable_table(self.table)
        self.table.itemDoubleClicked.connect(lambda _: self._edit_class())
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        edit_button = QPushButton("编辑")
        delete_button = QPushButton("删除")
        delete_button.setObjectName("dangerButton")
        edit_button.clicked.connect(self._edit_class)
        delete_button.clicked.connect(self._delete_class)
        actions.addWidget(edit_button)
        actions.addWidget(delete_button)
        layout.addLayout(actions)

    def reload(self) -> None:
        self.class_rows = self.controller.list_classes()
        self.table.setRowCount(len(self.class_rows))
        for row_index, row in enumerate(self.class_rows):
            values = [row["name"], row["grade"], row["school_year"], row["head_teacher"], str(row["student_count"])]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, row["id"])
                self.table.setItem(row_index, column, item)

    def _selected_class(self) -> dict[str, Any] | None:
        row_index = self.table.currentRow()
        if row_index < 0 or row_index >= len(self.class_rows):
            QMessageBox.information(self, "请选择班级", "请先选择一个班级。")
            return None
        return self.class_rows[row_index]

    def _add_class(self) -> None:
        if ClassEditDialog(self.controller, parent=self).exec():
            self.reload()
            self.classes_changed.emit()

    def _edit_class(self) -> None:
        selected = self._selected_class()
        if selected and ClassEditDialog(self.controller, selected, self).exec():
            self.reload()
            self.classes_changed.emit()

    def _delete_class(self) -> None:
        selected = self._selected_class()
        if not selected:
            return
        answer = QMessageBox.question(
            self,
            "删除班级",
            f"确定删除“{selected['name']}”吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.controller.delete_class(int(selected["id"]))
        except StudentDataError as exc:
            QMessageBox.warning(self, "无法删除", str(exc))
            return
        self.reload()
        self.classes_changed.emit()
