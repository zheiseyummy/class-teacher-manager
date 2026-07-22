from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controllers.student_controller import StudentController, StudentDataError
from utils.ui_layout import configure_resizable_table
from views.student_form_dialog import StudentFormDialog


class StudentDetailPane(QFrame):
    data_changed = Signal()

    def __init__(self, controller: StudentController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.student_id: int | None = None
        self.setObjectName("detailPane")
        self._build_ui()
        self.clear()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)

        header = QHBoxLayout()
        name_box = QVBoxLayout()
        name_box.setSpacing(2)
        self.name_label = QLabel("学生档案")
        self.name_label.setObjectName("detailName")
        self.class_label = QLabel("")
        self.class_label.setObjectName("mutedLabel")
        name_box.addWidget(self.name_label)
        name_box.addWidget(self.class_label)
        header.addLayout(name_box)
        header.addStretch(1)
        self.edit_button = QPushButton("编辑")
        self.delete_button = QPushButton("删除")
        self.edit_button.clicked.connect(self._edit_student)
        self.delete_button.clicked.connect(self._delete_student)
        header.addWidget(self.edit_button)
        header.addWidget(self.delete_button)
        layout.addLayout(header)

        form = QFormLayout()
        form.setSpacing(10)
        self.fields: dict[str, QLabel] = {}
        for key, label in [
            ("gender", "性别"),
            ("student_no", "学号"),
            ("grade", "年级"),
            ("seat_no", "座号"),
            ("birth_date", "出生日期"),
            ("id_card", "身份证号"),
            ("ethnicity", "民族"),
            ("note", "备注"),
        ]:
            value = QLabel()
            value.setObjectName("detailValue")
            value.setWordWrap(True)
            self.fields[key] = value
            form.addRow(label, value)
        layout.addLayout(form)

        contacts_title = QLabel("家长与联系人")
        contacts_title.setObjectName("sectionTitle")
        layout.addWidget(contacts_title)
        self.contacts = QTableWidget(0, 4)
        self.contacts.setHorizontalHeaderLabels(["姓名", "关系", "电话", "微信"])
        self.contacts.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.contacts.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.contacts.verticalHeader().setVisible(False)
        configure_resizable_table(self.contacts)
        self.contacts.setMinimumHeight(160)
        layout.addWidget(self.contacts, 1)

    def clear(self) -> None:
        self.student_id = None
        self.name_label.setText("学生档案")
        self.class_label.setText("从左侧列表选择学生")
        for label in self.fields.values():
            label.setText("-")
        self.contacts.setRowCount(0)
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)

    def load_student(self, student_id: int) -> None:
        try:
            student = self.controller.get_student_detail(student_id)
        except StudentDataError:
            self.clear()
            return
        self.student_id = student_id
        self.name_label.setText(student["name"])
        self.class_label.setText(student["class_name"])
        self.fields["gender"].setText(student["gender"] or "-")
        self.fields["student_no"].setText(student["student_no"] or "-")
        self.fields["grade"].setText(student["display_grade"] or "-")
        self.fields["seat_no"].setText(student["seat_no"] or "-")
        self.fields["birth_date"].setText(student["birth_date"].isoformat() if student["birth_date"] else "-")
        self.fields["id_card"].setText(student["id_card"] or "-")
        self.fields["ethnicity"].setText(student["ethnicity"] or "-")
        self.fields["note"].setText(student["note"] or "-")
        self.contacts.setRowCount(len(student["guardians"]))
        for row_index, guardian in enumerate(student["guardians"]):
            values = [
                guardian["name"] + ("（主要）" if guardian["is_primary"] else ""),
                guardian["relationship"],
                guardian["phone"],
                guardian["wechat"],
            ]
            for column, value in enumerate(values):
                self.contacts.setItem(row_index, column, QTableWidgetItem(value))
        self.edit_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def _edit_student(self) -> None:
        if self.student_id is None:
            return
        dialog = StudentFormDialog(self.controller, self.student_id, self)
        if dialog.exec() and dialog.saved_student_id:
            self.load_student(dialog.saved_student_id)
            self.data_changed.emit()

    def _delete_student(self) -> None:
        if self.student_id is None:
            return
        answer = QMessageBox.question(
            self,
            "删除学生档案",
            "确定删除这份学生档案吗？该操作可在后续的数据恢复功能中找回。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.controller.delete_student(self.student_id)
        except StudentDataError as exc:
            QMessageBox.warning(self, "无法删除", str(exc))
            return
        self.clear()
        self.data_changed.emit()
