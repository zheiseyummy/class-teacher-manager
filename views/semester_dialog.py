from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from controllers.teaching_schedule_controller import TeachingScheduleController, TeachingScheduleDataError
from utils.ui_layout import configure_responsive_dialog


class SemesterDialog(QDialog):
    """Create or edit an academic semester used by the timetable."""

    def __init__(
        self,
        controller: TeachingScheduleController,
        semester_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.semester_id = semester_id
        self.saved_semester_id: int | None = None
        self.setWindowTitle("编辑学期" if semester_id is not None else "新增学期")
        self._build_ui()
        configure_responsive_dialog(self, 470)
        if semester_id is not None:
            self._load_semester(semester_id)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)
        form = QFormLayout()
        form.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("如：2026-2027 学年第一学期")
        form.addRow("学期名称", self.name_input)

        self.start_date = QDateEdit(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        form.addRow("开始日期", self.start_date)

        self.end_date = QDateEdit(QDate.currentDate().addMonths(5))
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        form.addRow("结束日期", self.end_date)

        self.current_box = QCheckBox("设为当前学期")
        self.current_box.setChecked(True)
        form.addRow("状态", self.current_box)

        self.note_input = QPlainTextEdit()
        self.note_input.setFixedHeight(76)
        self.note_input.setPlaceholderText("学期日期不允许与其他有效学期重叠。")
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

    def _load_semester(self, semester_id: int) -> None:
        try:
            semester = self.controller.get_semester(semester_id)
        except TeachingScheduleDataError as exc:
            QMessageBox.warning(self, "无法读取学期", str(exc))
            self.reject()
            return
        self.name_input.setText(semester["name"])
        self.start_date.setDate(QDate(semester["start_date"]))
        self.end_date.setDate(QDate(semester["end_date"]))
        self.current_box.setChecked(semester["is_current"])
        self.note_input.setPlainText(semester["note"])

    def _save(self) -> None:
        try:
            self.saved_semester_id = self.controller.save_semester(
                {
                    "name": self.name_input.text(),
                    "start_date": self.start_date.date().toPython(),
                    "end_date": self.end_date.date().toPython(),
                    "is_current": self.current_box.isChecked(),
                    "note": self.note_input.toPlainText(),
                },
                self.semester_id,
            )
        except TeachingScheduleDataError as exc:
            QMessageBox.warning(self, "无法保存学期", str(exc))
            return
        self.accept()
