from __future__ import annotations

from PySide6.QtCore import QTime
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from controllers.teaching_schedule_controller import TeachingScheduleController, TeachingScheduleDataError
from utils.ui_layout import configure_responsive_dialog


class SchedulePeriodDialog(QDialog):
    """Create or edit one user-defined period in a selected semester."""

    def __init__(
        self,
        controller: TeachingScheduleController,
        semester_id: int,
        period_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.semester_id = semester_id
        self.period_id = period_id
        self.saved_period_id: int | None = None
        self.setWindowTitle("编辑课时" if period_id is not None else "新增课时")
        self._build_ui()
        configure_responsive_dialog(self, 440)
        if period_id is not None:
            self._load_period(period_id)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)
        form = QFormLayout()
        form.setSpacing(12)

        self.order_input = QSpinBox()
        self.order_input.setRange(1, 99)
        self.order_input.setValue(len(self.controller.list_periods(self.semester_id)) + 1)
        form.addRow("显示顺序", self.order_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("如：早读、第一节、午休、晚自习")
        form.addRow("课时名称", self.name_input)

        self.start_time = QTimeEdit(QTime(8, 0))
        self.start_time.setDisplayFormat("HH:mm")
        form.addRow("开始时间", self.start_time)

        self.end_time = QTimeEdit(QTime(8, 45))
        self.end_time.setDisplayFormat("HH:mm")
        form.addRow("结束时间", self.end_time)

        self.note_input = QPlainTextEdit()
        self.note_input.setFixedHeight(70)
        self.note_input.setPlaceholderText("可记录铃声、课间时长等。")
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

    def _load_period(self, period_id: int) -> None:
        try:
            period = self.controller.get_period(period_id)
        except TeachingScheduleDataError as exc:
            QMessageBox.warning(self, "无法读取课时", str(exc))
            self.reject()
            return
        self.order_input.setValue(period["sort_order"])
        self.name_input.setText(period["name"])
        start_time = QTime.fromString(period["start_time"], "HH:mm")
        end_time = QTime.fromString(period["end_time"], "HH:mm")
        if start_time.isValid():
            self.start_time.setTime(start_time)
        if end_time.isValid():
            self.end_time.setTime(end_time)
        self.note_input.setPlainText(period["note"])

    def _save(self) -> None:
        try:
            self.saved_period_id = self.controller.save_period(
                {
                    "semester_id": self.semester_id,
                    "sort_order": self.order_input.value(),
                    "name": self.name_input.text(),
                    "start_time": self.start_time.time().toString("HH:mm"),
                    "end_time": self.end_time.time().toString("HH:mm"),
                    "note": self.note_input.toPlainText(),
                },
                self.period_id,
            )
        except TeachingScheduleDataError as exc:
            QMessageBox.warning(self, "无法保存课时", str(exc))
            return
        self.accept()
