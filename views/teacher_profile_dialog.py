from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from controllers.teacher_profile_controller import (
    TeacherProfileController,
    TeacherProfileDataError,
)
from utils.ui_icons import lucide_icon
from utils.ui_layout import configure_responsive_dialog


class TeacherProfileDialog(QDialog):
    """Edit the local teacher identity and frequently used options."""

    def __init__(
        self,
        controller: TeacherProfileController,
        parent: QWidget | None = None,
        *,
        onboarding: bool = False,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.onboarding = onboarding
        self.profile = controller.get_profile()
        self.options = controller.get_form_options()
        self.subject_checks: dict[str, QCheckBox] = {}
        self.saved_profile: dict[str, Any] | None = None
        self.setWindowTitle("首次使用设置" if onboarding else "教师信息")
        self._build_ui()
        configure_responsive_dialog(self, 640, 680, minimum_height=480)
        self._load_profile()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 18)
        root.setSpacing(10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("dialogScrollContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(26, 24, 26, 14)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)
        icon_label = QLabel()
        icon_label.setObjectName("profileDialogIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(42, 42)
        icon_label.setPixmap(lucide_icon("user-check", color="#2563EB", size=22).pixmap(22, 22))
        header.addWidget(icon_label)
        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        title = QLabel("完善教师信息" if self.onboarding else "教师信息")
        title.setObjectName("dialogTitle")
        header_text.addWidget(title)
        hint = QLabel("用于首页问候、常用筛选和报告署名，所有信息只保存在本机。")
        hint.setObjectName("dialogHint")
        hint.setWordWrap(True)
        header_text.addWidget(hint)
        header.addLayout(header_text, 1)
        layout.addLayout(header)

        identity_title = QLabel("基本信息")
        identity_title.setObjectName("sectionTitle")
        layout.addWidget(identity_title)
        identity_form = QFormLayout()
        identity_form.setHorizontalSpacing(18)
        identity_form.setVerticalSpacing(11)
        self.name_input = QLineEdit()
        self.name_input.setMaxLength(80)
        self.name_input.setPlaceholderText("例如：李老师或李")
        self.school_input = QLineEdit()
        self.school_input.setMaxLength(160)
        self.school_input.setPlaceholderText("选填，可用于报告标题")
        identity_form.addRow("教师姓名 *", self.name_input)
        identity_form.addRow("学校名称", self.school_input)
        layout.addLayout(identity_form)

        teaching_title = QLabel("任教偏好")
        teaching_title.setObjectName("sectionTitle")
        layout.addWidget(teaching_title)
        self.subject_grid = QGridLayout()
        self.subject_grid.setHorizontalSpacing(18)
        self.subject_grid.setVerticalSpacing(8)
        for subject in self.controller.COMMON_SUBJECTS:
            self._ensure_subject_checkbox(subject)
        layout.addLayout(self.subject_grid)

        custom_subject_row = QHBoxLayout()
        custom_subject_row.setSpacing(8)
        self.custom_subject_input = QLineEdit()
        self.custom_subject_input.setMaxLength(30)
        self.custom_subject_input.setPlaceholderText("其他学科，如体育、音乐")
        self.custom_subject_input.returnPressed.connect(self._add_custom_subject)
        custom_subject_row.addWidget(self.custom_subject_input, 1)
        add_subject_button = QPushButton("添加")
        add_subject_button.setObjectName("secondaryButton")
        add_subject_button.setIcon(lucide_icon("plus"))
        add_subject_button.clicked.connect(self._add_custom_subject)
        custom_subject_row.addWidget(add_subject_button)
        layout.addLayout(custom_subject_row)

        preference_form = QFormLayout()
        preference_form.setHorizontalSpacing(18)
        preference_form.setVerticalSpacing(11)
        self.class_list = QListWidget()
        self.class_list.setObjectName("profileClassList")
        self.class_list.setFixedHeight(104)
        self.class_list.setAlternatingRowColors(False)
        classes = self.options["classes"]
        if classes:
            for class_row in classes:
                detail = class_row["school_year"] or class_row["grade"]
                label = class_row["name"] if not detail else f"{class_row['name']}  ·  {detail}"
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, class_row["id"])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.class_list.addItem(item)
        else:
            item = QListWidgetItem("尚未创建学生班级，可稍后设置")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.class_list.addItem(item)
        self.semester_combo = QComboBox()
        self.semester_combo.addItem("暂不设置", None)
        for semester in self.options["semesters"]:
            suffix = "  ·  当前" if semester["is_current"] else ""
            self.semester_combo.addItem(f"{semester['name']}{suffix}", semester["id"])
        preference_form.addRow("常用班级", self.class_list)
        preference_form.addRow("默认学期", self.semester_combo)
        layout.addLayout(preference_form)

        mark_title = QLabel("个人标记")
        mark_title.setObjectName("sectionTitle")
        layout.addWidget(mark_title)
        self.mark_input = QLineEdit()
        self.mark_input.setMaxLength(120)
        self.mark_input.setPlaceholderText("留空则自动生成“姓名老师 · 个人教学工作台”")
        layout.addWidget(self.mark_input)
        self.preview_label = QLabel()
        self.preview_label.setObjectName("profilePreview")
        self.preview_label.setWordWrap(True)
        layout.addWidget(self.preview_label)

        privacy_hint = QLabel("不保存账号、密码、身份证号或联系电话。")
        privacy_hint.setObjectName("privacyHint")
        layout.addWidget(privacy_hint)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存教师信息")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            "稍后设置" if self.onboarding else "取消"
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(26, 0, 26, 0)
        footer_layout.addWidget(buttons)
        root.addWidget(footer)

        self.name_input.textChanged.connect(self._refresh_preview)
        self.mark_input.textChanged.connect(self._refresh_preview)

    def _load_profile(self) -> None:
        self.name_input.setText(self.profile["teacher_name"])
        self.school_input.setText(self.profile["school_name"])
        for subject in self.profile["subjects"]:
            self._ensure_subject_checkbox(subject).setChecked(True)
        selected_class_ids = set(self.profile["common_class_ids"])
        for row in range(self.class_list.count()):
            item = self.class_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) in selected_class_ids:
                item.setCheckState(Qt.CheckState.Checked)
        semester_index = self.semester_combo.findData(self.profile["default_semester_id"])
        self.semester_combo.setCurrentIndex(semester_index if semester_index >= 0 else 0)
        self.mark_input.setText(self.profile["personal_mark"])
        self._refresh_preview()
        self.name_input.setFocus()

    def _ensure_subject_checkbox(self, subject: str) -> QCheckBox:
        normalized = subject.strip()
        existing = self.subject_checks.get(normalized)
        if existing is not None:
            return existing
        checkbox = QCheckBox(normalized)
        index = len(self.subject_checks)
        self.subject_grid.addWidget(checkbox, index // 3, index % 3)
        self.subject_checks[normalized] = checkbox
        return checkbox

    def _add_custom_subject(self) -> None:
        subject = self.custom_subject_input.text().strip()
        if not subject:
            return
        self._ensure_subject_checkbox(subject).setChecked(True)
        self.custom_subject_input.clear()

    def _selected_class_ids(self) -> list[int]:
        result: list[int] = []
        for row in range(self.class_list.count()):
            item = self.class_list.item(row)
            class_id = item.data(Qt.ItemDataRole.UserRole)
            if class_id is not None and item.checkState() == Qt.CheckState.Checked:
                result.append(int(class_id))
        return result

    def _refresh_preview(self) -> None:
        teacher_name = self.name_input.text().strip()
        display_name = self.controller.teacher_display_name(teacher_name)
        custom_mark = self.mark_input.text().strip()
        mark = custom_mark or (
            f"{display_name} · 个人教学工作台" if teacher_name else "个人教学工作台"
        )
        self.preview_label.setText(f"首页：您好，{display_name}！\n底部：{mark}")

    def _save(self) -> None:
        data = {
            "teacher_name": self.name_input.text(),
            "school_name": self.school_input.text(),
            "subjects": [
                subject for subject, checkbox in self.subject_checks.items() if checkbox.isChecked()
            ],
            "common_class_ids": self._selected_class_ids(),
            "default_semester_id": self.semester_combo.currentData(),
            "personal_mark": self.mark_input.text(),
        }
        try:
            self.saved_profile = self.controller.save_profile(data)
        except TeacherProfileDataError as exc:
            QMessageBox.warning(self, "无法保存", str(exc))
            return
        self.accept()
