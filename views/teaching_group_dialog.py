from __future__ import annotations

from PySide6.QtGui import QColor, QIcon, QPixmap
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
from utils.class_colors import CLASS_COLOR_CHOICES


class TeachingGroupDialog(QDialog):
    """Create or edit a timetable-only teaching group."""

    def __init__(
        self,
        controller: TeachingScheduleController,
        group_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.group_id = group_id
        self.saved_group_id: int | None = None
        self.setWindowTitle("编辑教学班" if group_id is not None else "新增教学班")
        self.setMinimumWidth(470)
        self._build_ui()
        if group_id is not None:
            self._load_group(group_id)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)
        form = QFormLayout()
        form.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("如：初三1班、九年级竞赛辅导班")
        form.addRow("教学班名称", self.name_input)

        self.color_box = QComboBox()
        for choice in CLASS_COLOR_CHOICES:
            self.color_box.addItem(self._color_icon(choice["color"]), choice["name"], choice["color"])
        form.addRow("识别颜色", self.color_box)

        self.linked_class_box = QComboBox()
        self.linked_class_box.addItem("不关联学生班级（独立使用）", None)
        for class_group in self.controller.list_student_class_options():
            suffix = f"（{class_group['student_count']} 人）"
            self.linked_class_box.addItem(f"{class_group['name']}{suffix}", class_group["id"])
        form.addRow("关联学生班级", self.linked_class_box)

        self.note_input = QPlainTextEdit()
        self.note_input.setFixedHeight(76)
        self.note_input.setPlaceholderText("可记录授课对象、校区或用途；不影响学生数据中心。")
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

    def _load_group(self, group_id: int) -> None:
        try:
            group = self.controller.get_teaching_group(group_id)
        except TeachingScheduleDataError as exc:
            QMessageBox.warning(self, "无法读取教学班", str(exc))
            self.reject()
            return
        self.name_input.setText(group["name"])
        self.note_input.setPlainText(group["note"])
        self._select_value(self.color_box, group["color"])
        self._select_value(self.linked_class_box, group["linked_class_id"])

    def _save(self) -> None:
        try:
            self.saved_group_id = self.controller.save_teaching_group(
                {
                    "name": self.name_input.text(),
                    "color": self.color_box.currentData(),
                    "linked_class_id": self.linked_class_box.currentData(),
                    "note": self.note_input.toPlainText(),
                },
                self.group_id,
            )
        except TeachingScheduleDataError as exc:
            QMessageBox.warning(self, "无法保存教学班", str(exc))
            return
        self.accept()

    @staticmethod
    def _color_icon(color: str) -> QIcon:
        pixmap = QPixmap(14, 14)
        pixmap.fill(QColor(color))
        return QIcon(pixmap)

    @staticmethod
    def _select_value(box: QComboBox, value: int | str | None) -> None:
        index = box.findData(value)
        if index >= 0:
            box.setCurrentIndex(index)
