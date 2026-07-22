from __future__ import annotations

from datetime import date
from typing import Any

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ScoreImportDialog(QDialog):
    def __init__(
        self,
        classes: list[dict[str, Any]],
        selected_class_id: int | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("导入单次考试成绩")
        self.setMinimumWidth(460)
        self.exam_data: dict[str, Any] | None = None
        self._build_ui(classes, selected_class_id)

    def _build_ui(self, classes: list[dict[str, Any]], selected_class_id: int | None) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)
        form = QFormLayout()
        form.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如：第一次月考")
        form.addRow("考试名称", self.name_input)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")
        self.date_input.setDate(QDate.currentDate())
        form.addRow("考试日期", self.date_input)

        self.semester_input = QLineEdit()
        self.semester_input.setPlaceholderText("例如：2026-2027 学年上学期")
        form.addRow("学期", self.semester_input)

        self.grade_input = QComboBox()
        self.grade_input.setEditable(True)
        grades = []
        selected_grade = ""
        for class_group in classes:
            grade = class_group["grade"]
            if grade and grade not in grades:
                grades.append(grade)
            if class_group["id"] == selected_class_id:
                selected_grade = grade
        self.grade_input.addItems(grades)
        if selected_grade:
            self.grade_input.setCurrentText(selected_grade)
        self.grade_input.setPlaceholderText("可选")
        form.addRow("年级", self.grade_input)

        self.note_input = QTextEdit()
        self.note_input.setMaximumHeight(72)
        self.note_input.setPlaceholderText("可选")
        form.addRow("备注", self.note_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("选择 Excel")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        name = self.name_input.text().strip()
        if not name:
            self.name_input.setFocus()
            return
        selected_date = self.date_input.date()
        self.exam_data = {
            "name": name,
            "exam_date": date(selected_date.year(), selected_date.month(), selected_date.day()),
            "semester": self.semester_input.text().strip(),
            "grade": self.grade_input.currentText().strip(),
            "note": self.note_input.toPlainText().strip(),
        }
        self.accept()
