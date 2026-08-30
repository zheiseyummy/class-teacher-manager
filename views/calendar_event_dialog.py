from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from controllers.planner_controller import PlannerController, PlannerDataError
from utils.ui_layout import configure_responsive_dialog


class CalendarEventDialog(QDialog):
    """Create or edit one dated class or global calendar event."""

    def __init__(
        self,
        controller: PlannerController,
        event_id: int | None = None,
        initial_date: date | None = None,
        initial_class_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.event_id = event_id
        self.saved_event_id: int | None = None
        self.setWindowTitle("编辑日程" if event_id is not None else "新增日程")
        self._build_ui()
        configure_responsive_dialog(self, 480)
        if event_id is not None:
            self._load_event(event_id)
        else:
            if initial_date is not None:
                self.date_edit.setDate(QDate(initial_date.year, initial_date.month, initial_date.day))
            self._select_value(self.class_box, initial_class_id)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)

        self.class_box = QComboBox()
        self.class_box.addItem("全局日程", None)
        for class_group in self.controller.list_classes():
            self.class_box.addItem(class_group["name"], class_group["id"])
        form.addRow("适用班级", self.class_box)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("日期", self.date_edit)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("如：阶段性质量检测、家长会")
        form.addRow("日程名称", self.title_input)

        self.category_box = QComboBox()
        for category in self.controller.EVENT_CATEGORIES:
            self.category_box.addItem(category, category)
        form.addRow("类别", self.category_box)

        self.has_time_box = QCheckBox("设置具体时间")
        self.has_time_box.toggled.connect(self._sync_time_enabled)
        form.addRow("时间", self.has_time_box)

        self.start_time = QTimeEdit(QTime(8, 0))
        self.start_time.setDisplayFormat("HH:mm")
        form.addRow("开始时间", self.start_time)

        self.end_time = QTimeEdit(QTime(9, 0))
        self.end_time.setDisplayFormat("HH:mm")
        form.addRow("结束时间", self.end_time)

        self.note_input = QPlainTextEdit()
        self.note_input.setFixedHeight(76)
        self.note_input.setPlaceholderText("可记录地点、参与人员或跟进事项")
        form.addRow("备注", self.note_input)
        layout.addLayout(form)
        self._sync_time_enabled(False)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_event(self, event_id: int) -> None:
        try:
            event = self.controller.get_event(event_id)
        except PlannerDataError as exc:
            QMessageBox.warning(self, "无法读取日程", str(exc))
            self.reject()
            return
        self._select_value(self.class_box, event["class_id"])
        event_date = event["event_date"]
        self.date_edit.setDate(QDate(event_date.year, event_date.month, event_date.day))
        self.title_input.setText(event["title"])
        self._select_value(self.category_box, event["category"])
        self.note_input.setPlainText(event["note"])
        has_time = bool(event["start_time"] or event["end_time"])
        self.has_time_box.setChecked(has_time)
        if event["start_time"]:
            self.start_time.setTime(QTime.fromString(event["start_time"], "HH:mm"))
        if event["end_time"]:
            self.end_time.setTime(QTime.fromString(event["end_time"], "HH:mm"))

    def _save(self) -> None:
        data = {
            "class_id": self.class_box.currentData(),
            "event_date": self.date_edit.date().toPython(),
            "title": self.title_input.text(),
            "category": self.category_box.currentData(),
            "start_time": self.start_time.time().toString("HH:mm") if self.has_time_box.isChecked() else "",
            "end_time": self.end_time.time().toString("HH:mm") if self.has_time_box.isChecked() else "",
            "note": self.note_input.toPlainText(),
        }
        try:
            self.saved_event_id = self.controller.save_event(data, self.event_id)
        except PlannerDataError as exc:
            QMessageBox.warning(self, "无法保存日程", str(exc))
            return
        self.accept()

    def _sync_time_enabled(self, enabled: bool) -> None:
        self.start_time.setEnabled(enabled)
        self.end_time.setEnabled(enabled)

    @staticmethod
    def _select_value(box: QComboBox, value: int | str | None) -> None:
        index = box.findData(value)
        if index >= 0:
            box.setCurrentIndex(index)
