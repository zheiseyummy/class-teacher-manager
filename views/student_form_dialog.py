from __future__ import annotations

from datetime import date
from typing import Any

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controllers.student_controller import StudentController, StudentDataError
from utils.ui_layout import configure_resizable_table, configure_responsive_dialog


class GuardianEditorDialog(QDialog):
    def __init__(self, guardian: dict[str, Any] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.guardian = guardian or {}
        self.result_data: dict[str, Any] | None = None
        self.setWindowTitle("编辑联系人" if guardian else "新增联系人")
        self._build_ui()
        configure_responsive_dialog(self, 460)
        if guardian:
            self._load_data()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)
        form = QFormLayout()
        form.setSpacing(12)

        self.name_input = QLineEdit()
        self.relationship_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.wechat_input = QLineEdit()
        self.workplace_input = QLineEdit()
        self.address_input = QLineEdit()
        self.note_input = QPlainTextEdit()
        self.note_input.setFixedHeight(70)
        self.primary_check = QCheckBox("设为主要联系人")
        form.addRow("家长姓名 *", self.name_input)
        form.addRow("与学生关系", self.relationship_input)
        form.addRow("联系电话", self.phone_input)
        form.addRow("微信号", self.wechat_input)
        form.addRow("工作单位", self.workplace_input)
        form.addRow("家庭地址", self.address_input)
        form.addRow("备注", self.note_input)
        form.addRow("", self.primary_check)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_data(self) -> None:
        self.name_input.setText(self.guardian.get("name", ""))
        self.relationship_input.setText(self.guardian.get("relationship", ""))
        self.phone_input.setText(self.guardian.get("phone", ""))
        self.wechat_input.setText(self.guardian.get("wechat", ""))
        self.workplace_input.setText(self.guardian.get("workplace", ""))
        self.address_input.setText(self.guardian.get("address", ""))
        self.note_input.setPlainText(self.guardian.get("note", ""))
        self.primary_check.setChecked(bool(self.guardian.get("is_primary")))

    def _save(self) -> None:
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "无法保存", "请填写家长姓名。")
            return
        self.result_data = {
            "id": self.guardian.get("id"),
            "name": name,
            "relationship": self.relationship_input.text(),
            "phone": self.phone_input.text(),
            "wechat": self.wechat_input.text(),
            "workplace": self.workplace_input.text(),
            "address": self.address_input.text(),
            "note": self.note_input.toPlainText(),
            "is_primary": self.primary_check.isChecked(),
        }
        self.accept()


class StudentFormDialog(QDialog):
    def __init__(
        self,
        controller: StudentController,
        student_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.student_id = student_id
        self.saved_student_id: int | None = None
        self.guardians: list[dict[str, Any]] = []
        self.empty_date = QDate(1900, 1, 1)
        self.setWindowTitle("编辑学生" if student_id else "新增学生")
        self._build_ui()
        configure_responsive_dialog(self, 840, 760, minimum_height=480)
        self._load_classes()
        if student_id:
            self._load_student(student_id)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 18)
        root.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("dialogScrollContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(26, 24, 26, 16)
        layout.setSpacing(18)

        basic_title = QLabel("基本信息")
        basic_title.setObjectName("sectionTitle")
        layout.addWidget(basic_title)
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.class_box = QComboBox()
        self.name_input = QLineEdit()
        self.gender_box = QComboBox()
        self.gender_box.addItems(["", "男", "女"])
        self.student_no_input = QLineEdit()
        self.grade_input = QLineEdit()
        self.seat_no_input = QLineEdit()
        self.birth_date = QDateEdit()
        self.birth_date.setCalendarPopup(True)
        self.birth_date.setMinimumDate(self.empty_date)
        self.birth_date.setSpecialValueText("未填写")
        self.birth_date.setDate(self.empty_date)
        self.id_card_input = QLineEdit()
        self.ethnicity_input = QLineEdit()
        self.note_input = QPlainTextEdit()
        self.note_input.setFixedHeight(72)
        self.name_input.setPlaceholderText("请输入学生姓名")
        self.student_no_input.setPlaceholderText("可选")
        self.grade_input.setPlaceholderText("未填写时使用班级年级")
        self.seat_no_input.setPlaceholderText("可选")

        form.addRow("所属班级 *", self.class_box)
        form.addRow("姓名 *", self.name_input)
        form.addRow("性别", self.gender_box)
        form.addRow("学号", self.student_no_input)
        form.addRow("年级", self.grade_input)
        form.addRow("座号", self.seat_no_input)
        form.addRow("出生日期", self.birth_date)
        form.addRow("身份证号", self.id_card_input)
        form.addRow("民族", self.ethnicity_input)
        form.addRow("备注", self.note_input)
        layout.addLayout(form)

        guardian_heading = QHBoxLayout()
        guardian_title = QLabel("家长与联系人")
        guardian_title.setObjectName("sectionTitle")
        guardian_heading.addWidget(guardian_title)
        guardian_heading.addStretch(1)
        add_guardian = QPushButton("新增联系人")
        add_guardian.clicked.connect(self._add_guardian)
        guardian_heading.addWidget(add_guardian)
        layout.addLayout(guardian_heading)

        self.guardian_table = QTableWidget(0, 6)
        self.guardian_table.setHorizontalHeaderLabels(["姓名", "关系", "电话", "微信", "工作单位", "主要"])
        self.guardian_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.guardian_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.guardian_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.guardian_table.verticalHeader().setVisible(False)
        configure_resizable_table(self.guardian_table)
        self.guardian_table.setMinimumHeight(180)
        self.guardian_table.itemDoubleClicked.connect(lambda _: self._edit_guardian())
        layout.addWidget(self.guardian_table)

        guardian_actions = QHBoxLayout()
        guardian_actions.addStretch(1)
        edit_guardian = QPushButton("编辑联系人")
        delete_guardian = QPushButton("移除联系人")
        delete_guardian.setObjectName("dangerButton")
        edit_guardian.clicked.connect(self._edit_guardian)
        delete_guardian.clicked.connect(self._delete_guardian)
        guardian_actions.addWidget(edit_guardian)
        guardian_actions.addWidget(delete_guardian)
        layout.addLayout(guardian_actions)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_classes(self) -> None:
        selected_id = self.class_box.currentData()
        self.class_box.clear()
        for class_group in self.controller.list_classes():
            self.class_box.addItem(class_group["name"], class_group["id"])
        if selected_id is not None:
            index = self.class_box.findData(selected_id)
            if index >= 0:
                self.class_box.setCurrentIndex(index)

    def _load_student(self, student_id: int) -> None:
        try:
            student = self.controller.get_student_detail(student_id)
        except StudentDataError as exc:
            QMessageBox.warning(self, "无法打开", str(exc))
            self.reject()
            return
        class_index = self.class_box.findData(student["class_id"])
        if class_index >= 0:
            self.class_box.setCurrentIndex(class_index)
        self.name_input.setText(student["name"])
        self.gender_box.setCurrentText(student["gender"])
        self.student_no_input.setText(student["student_no"])
        self.grade_input.setText(student["grade"])
        self.seat_no_input.setText(student["seat_no"])
        if student["birth_date"]:
            value = student["birth_date"]
            self.birth_date.setDate(QDate(value.year, value.month, value.day))
        self.id_card_input.setText(student["id_card"])
        self.ethnicity_input.setText(student["ethnicity"])
        self.note_input.setPlainText(student["note"])
        self.guardians = list(student["guardians"])
        self._refresh_guardians()

    def _refresh_guardians(self) -> None:
        self.guardian_table.setRowCount(len(self.guardians))
        for row_index, guardian in enumerate(self.guardians):
            values = [
                guardian.get("name", ""),
                guardian.get("relationship", ""),
                guardian.get("phone", ""),
                guardian.get("wechat", ""),
                guardian.get("workplace", ""),
                "是" if guardian.get("is_primary") else "",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, row_index)
                self.guardian_table.setItem(row_index, column, item)

    def _selected_guardian_index(self) -> int | None:
        row_index = self.guardian_table.currentRow()
        if row_index < 0 or row_index >= len(self.guardians):
            QMessageBox.information(self, "请选择联系人", "请先选择一位联系人。")
            return None
        return row_index

    def _add_guardian(self) -> None:
        dialog = GuardianEditorDialog(parent=self)
        if dialog.exec() and dialog.result_data:
            self.guardians.append(dialog.result_data)
            self._refresh_guardians()

    def _edit_guardian(self) -> None:
        row_index = self._selected_guardian_index()
        if row_index is None:
            return
        dialog = GuardianEditorDialog(self.guardians[row_index], self)
        if dialog.exec() and dialog.result_data:
            self.guardians[row_index] = dialog.result_data
            self._refresh_guardians()

    def _delete_guardian(self) -> None:
        row_index = self._selected_guardian_index()
        if row_index is None:
            return
        del self.guardians[row_index]
        self._refresh_guardians()

    def _birth_date_value(self) -> date | None:
        value = self.birth_date.date()
        if value == self.empty_date:
            return None
        return date(value.year(), value.month(), value.day())

    def _save(self) -> None:
        data = {
            "class_id": self.class_box.currentData(),
            "name": self.name_input.text(),
            "gender": self.gender_box.currentText(),
            "student_no": self.student_no_input.text(),
            "grade": self.grade_input.text(),
            "seat_no": self.seat_no_input.text(),
            "birth_date": self._birth_date_value(),
            "id_card": self.id_card_input.text(),
            "ethnicity": self.ethnicity_input.text(),
            "note": self.note_input.toPlainText(),
        }
        try:
            if self.student_id is None:
                self.saved_student_id = self.controller.create_student(data, self.guardians)
            else:
                self.controller.update_student(self.student_id, data, self.guardians)
                self.saved_student_id = self.student_id
        except StudentDataError as exc:
            QMessageBox.warning(self, "无法保存", str(exc))
            return
        except Exception:
            QMessageBox.warning(self, "无法保存", "数据保存失败，请检查班级、学号和身份证号是否重复。")
            return
        self.accept()
