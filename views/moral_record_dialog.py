from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from controllers.moral_controller import MoralController, MoralDataError
from utils.ui_layout import configure_responsive_dialog


class MoralRecordDialog(QDialog):
    """Create or edit one moral-development activity or award record."""

    def __init__(
        self,
        controller: MoralController,
        record_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.record_id = record_id
        self.saved_record_id: int | None = None
        self.setWindowTitle("编辑德育记录" if record_id is not None else "新增德育记录")
        self._build_ui()
        configure_responsive_dialog(self, 480)
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

        self.category_box = QComboBox()
        for category in self.controller.CATEGORIES:
            self.category_box.addItem(category, category)
        self.category_box.currentIndexChanged.connect(self._sync_category_fields)
        form.addRow("类别", self.category_box)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("日期", self.date_edit)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("如：校园艺术节志愿服务、三好学生")
        form.addRow("活动或奖项", self.title_input)

        self.award_level_box = QComboBox()
        for level in self.controller.AWARD_LEVELS:
            self.award_level_box.addItem(level or "未填写", level)
        form.addRow("奖项级别", self.award_level_box)

        self.organizer_input = QLineEdit()
        self.organizer_input.setPlaceholderText("如：学校团委、区教育局")
        form.addRow("主办方", self.organizer_input)

        self.points_input = QDoubleSpinBox()
        self.points_input.setRange(-1000, 1000)
        self.points_input.setDecimals(2)
        self.points_input.setSingleStep(1)
        self.points_input.setValue(0)
        form.addRow("德育积分", self.points_input)

        self.note_input = QPlainTextEdit()
        self.note_input.setFixedHeight(76)
        self.note_input.setPlaceholderText("可记录获奖证书、参与表现或后续评价")
        form.addRow("备注", self.note_input)

        layout.addLayout(form)
        self._sync_category_fields()

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
        self.student_box.blockSignals(True)
        self.student_box.clear()
        for student in self.controller.list_students(self.class_box.currentData()):
            suffix = f"（{student['student_no']}）" if student["student_no"] else ""
            self.student_box.addItem(f"{student['class_name']} · {student['name']}{suffix}", student["id"])
        index = self.student_box.findData(selected_student_id)
        self.student_box.setCurrentIndex(index if index >= 0 else 0)
        self.student_box.blockSignals(False)

    def _sync_category_fields(self, _index: int | None = None) -> None:
        is_award = self.category_box.currentData() == "获奖荣誉"
        self.award_level_box.setEnabled(is_award)
        if not is_award:
            self.award_level_box.setCurrentIndex(0)

    def _load_record(self, record_id: int) -> None:
        try:
            record = self.controller.get_record(record_id)
        except MoralDataError as exc:
            QMessageBox.warning(self, "无法读取记录", str(exc))
            self.reject()
            return
        class_index = self.class_box.findData(record["class_id"])
        self.class_box.setCurrentIndex(class_index if class_index >= 0 else 0)
        self._refresh_students(selected_student_id=record["student_id"])
        self._select_value(self.category_box, record["category"])
        record_date = record["record_date"]
        self.date_edit.setDate(QDate(record_date.year, record_date.month, record_date.day))
        self.title_input.setText(record["title"])
        self._select_value(self.award_level_box, record["award_level"])
        self.organizer_input.setText(record["organizer"])
        self.points_input.setValue(float(record["points"]))
        self.note_input.setPlainText(record["note"])
        self._sync_category_fields()

    def _save(self) -> None:
        data = {
            "student_id": self.student_box.currentData(),
            "record_date": self.date_edit.date().toPython(),
            "category": self.category_box.currentData(),
            "title": self.title_input.text(),
            "award_level": self.award_level_box.currentData(),
            "organizer": self.organizer_input.text(),
            "points": self.points_input.value(),
            "note": self.note_input.toPlainText(),
        }
        try:
            if self.record_id is None:
                self.saved_record_id = self.controller.create_record(data)
            else:
                self.controller.update_record(self.record_id, data)
                self.saved_record_id = self.record_id
        except MoralDataError as exc:
            QMessageBox.warning(self, "无法保存", str(exc))
            return
        self.accept()

    @staticmethod
    def _select_value(box: QComboBox, value: str) -> None:
        index = box.findData(value)
        box.setCurrentIndex(index if index >= 0 else 0)
