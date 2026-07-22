from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from controllers.attendance_controller import AttendanceController, AttendanceDataError


class AttendanceRecordDialog(QDialog):
    """Create or edit one leave or attendance record."""

    def __init__(
        self,
        controller: AttendanceController,
        record_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.record_id = record_id
        self.saved_record_id: int | None = None
        self.setWindowTitle("编辑记录" if record_id is not None else "新增请假与考勤记录")
        self.setMinimumWidth(480)
        self._build_ui()
        if record_id is not None:
            self._load_record(record_id)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)

        self.class_box = QComboBox()
        self._load_classes()
        self.class_box.currentIndexChanged.connect(self._refresh_students)
        form.addRow("班级", self.class_box)

        self.student_box = QComboBox()
        form.addRow("学生", self.student_box)
        self._refresh_students()

        self.type_box = QComboBox()
        for record_type in self.controller.RECORD_TYPES:
            self.type_box.addItem(record_type, record_type)
        form.addRow("类型", self.type_box)

        self.status_box = QComboBox()
        for status in self.controller.APPROVAL_STATUSES:
            self.status_box.addItem(status, status)
        form.addRow("状态", self.status_box)

        now = QDateTime.currentDateTime()
        self.start_edit = QDateTimeEdit(now)
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        form.addRow("开始时间", self.start_edit)

        self.end_edit = QDateTimeEdit(now.addSecs(60 * 60))
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        form.addRow("结束时间", self.end_edit)

        self.reason_input = QPlainTextEdit()
        self.reason_input.setPlaceholderText("如：发热就医、交通原因、家庭事务")
        self.reason_input.setFixedHeight(74)
        form.addRow("事由", self.reason_input)

        self.note_input = QPlainTextEdit()
        self.note_input.setPlaceholderText("可补充家长沟通、证明材料或跟进安排")
        self.note_input.setFixedHeight(74)
        form.addRow("备注", self.note_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_classes(self) -> None:
        self.class_box.blockSignals(True)
        self.class_box.clear()
        self.class_box.addItem("全部班级", None)
        for class_group in self.controller.list_classes():
            self.class_box.addItem(class_group["name"], class_group["id"])
        self.class_box.blockSignals(False)

    def _refresh_students(self, _index: int | None = None, selected_student_id: int | None = None) -> None:
        class_id = self.class_box.currentData()
        self.student_box.blockSignals(True)
        self.student_box.clear()
        for student in self.controller.list_students(class_id):
            suffix = f"（{student['student_no']}）" if student["student_no"] else ""
            label = f"{student['class_name']} · {student['name']}{suffix}"
            self.student_box.addItem(label, student["id"])
        index = self.student_box.findData(selected_student_id)
        self.student_box.setCurrentIndex(index if index >= 0 else 0)
        self.student_box.blockSignals(False)

    def _load_record(self, record_id: int) -> None:
        try:
            record = self.controller.get_record(record_id)
        except AttendanceDataError as exc:
            QMessageBox.warning(self, "无法读取记录", str(exc))
            self.reject()
            return

        class_index = self.class_box.findData(record["class_id"])
        self.class_box.setCurrentIndex(class_index if class_index >= 0 else 0)
        self._refresh_students(selected_student_id=record["student_id"])
        self._select_value(self.type_box, record["record_type"])
        self._select_value(self.status_box, record["approval_status"])
        self.start_edit.setDateTime(QDateTime(record["start_time"]))
        self.end_edit.setDateTime(QDateTime(record["end_time"]))
        self.reason_input.setPlainText(record["reason"])
        self.note_input.setPlainText(record["note"])

    def _save(self) -> None:
        data = {
            "student_id": self.student_box.currentData(),
            "record_type": self.type_box.currentData(),
            "approval_status": self.status_box.currentData(),
            "start_time": self.start_edit.dateTime().toPython(),
            "end_time": self.end_edit.dateTime().toPython(),
            "reason": self.reason_input.toPlainText(),
            "note": self.note_input.toPlainText(),
        }
        try:
            if self.record_id is None:
                self.saved_record_id = self.controller.create_record(data)
            else:
                self.controller.update_record(self.record_id, data)
                self.saved_record_id = self.record_id
        except AttendanceDataError as exc:
            QMessageBox.warning(self, "无法保存", str(exc))
            return
        self.accept()

    @staticmethod
    def _select_value(box: QComboBox, value: str) -> None:
        index = box.findData(value)
        box.setCurrentIndex(index if index >= 0 else 0)
