from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
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


class TeachingCourseDialog(QDialog):
    """Create or edit a course in the independent teaching timetable."""

    def __init__(
        self,
        controller: TeachingScheduleController,
        course_id: int | None = None,
        initial_semester_id: int | None = None,
        initial_group_id: int | None = None,
        initial_weekday: int | None = None,
        initial_period_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.course_id = course_id
        self.saved_course_id: int | None = None
        self.setWindowTitle("编辑课程" if course_id is not None else "新增课程")
        self._build_ui()
        configure_responsive_dialog(self, 470)
        if course_id is not None:
            self._load_course(course_id)
        else:
            self._select_value(self.semester_box, initial_semester_id)
            self._refresh_periods(selected_period_id=initial_period_id)
            self._select_value(self.group_box, initial_group_id)
            self._select_value(self.weekday_box, initial_weekday)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)
        form = QFormLayout()
        form.setSpacing(12)

        self.semester_box = QComboBox()
        for semester in self.controller.list_semesters():
            self.semester_box.addItem(
                f"{semester['name']}（{semester['date_range_display']}）",
                semester["id"],
            )
        self.semester_box.currentIndexChanged.connect(self._refresh_periods)
        form.addRow("学期", self.semester_box)

        self.group_box = QComboBox()
        for group in self.controller.list_teaching_groups():
            self.group_box.addItem(group["name"], group["id"])
        form.addRow("教学班", self.group_box)

        self.weekday_box = QComboBox()
        for weekday, label in self.controller.WEEKDAYS:
            self.weekday_box.addItem(label, weekday)
        form.addRow("星期", self.weekday_box)

        self.period_box = QComboBox()
        form.addRow("课时", self.period_box)

        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("如：语文、数学、班会、英语口语")
        form.addRow("课程名称", self.subject_input)

        self.teacher_input = QLineEdit()
        self.teacher_input.setPlaceholderText("可选")
        form.addRow("任课教师", self.teacher_input)

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("如：本班教室、实验楼 201")
        form.addRow("上课地点", self.location_input)

        self.note_input = QPlainTextEdit()
        self.note_input.setFixedHeight(72)
        self.note_input.setPlaceholderText("可记录携带材料、调课说明等。")
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

    def _refresh_periods(self, _index: int | None = None, selected_period_id: int | None = None) -> None:
        semester_id = self.semester_box.currentData()
        self.period_box.blockSignals(True)
        self.period_box.clear()
        if semester_id is not None:
            for period in self.controller.list_periods(int(semester_id)):
                self.period_box.addItem(
                    f"{period['name']}（{period['time_display']}）",
                    period["id"],
                )
        self._select_value(self.period_box, selected_period_id)
        self.period_box.blockSignals(False)

    def _load_course(self, course_id: int) -> None:
        try:
            course = self.controller.get_course(course_id)
        except TeachingScheduleDataError as exc:
            QMessageBox.warning(self, "无法读取课程", str(exc))
            self.reject()
            return
        self._select_value(self.semester_box, course["semester_id"])
        self._refresh_periods(selected_period_id=course["period_id"])
        self._select_value(self.group_box, course["teaching_group_id"])
        self._select_value(self.weekday_box, course["weekday"])
        self.subject_input.setText(course["subject"])
        self.teacher_input.setText(course["teacher"])
        self.location_input.setText(course["location"])
        self.note_input.setPlainText(course["note"])

    def _save(self) -> None:
        try:
            self.saved_course_id = self.controller.save_course(
                {
                    "semester_id": self.semester_box.currentData(),
                    "teaching_group_id": self.group_box.currentData(),
                    "weekday": self.weekday_box.currentData(),
                    "period_id": self.period_box.currentData(),
                    "subject": self.subject_input.text(),
                    "teacher": self.teacher_input.text(),
                    "location": self.location_input.text(),
                    "note": self.note_input.toPlainText(),
                },
                self.course_id,
            )
        except TeachingScheduleDataError as exc:
            QMessageBox.warning(self, "无法保存课程", str(exc))
            return
        self.accept()

    @staticmethod
    def _select_value(box: QComboBox, value: int | None) -> None:
        index = box.findData(value)
        if index >= 0:
            box.setCurrentIndex(index)
