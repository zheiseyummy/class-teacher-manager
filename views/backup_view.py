from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTime, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QMenu,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from controllers.backup_controller import BackupController, BackupDataError
from utils.ui_icons import lucide_icon
from utils.ui_layout import configure_resizable_table, restore_splitter, set_compact_columns
from views.ui_components import EmptyState, scrollable_detail


class BackupView(QWidget):
    """Local backup center for full snapshots, semester archives, and restores."""

    restart_requested = Signal()

    WEEKDAYS = (
        (1, "周一"),
        (2, "周二"),
        (3, "周三"),
        (4, "周四"),
        (5, "周五"),
        (6, "周六"),
        (7, "周日"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = BackupController()
        self._semesters: list[dict[str, Any]] = []
        self._records: list[dict[str, Any]] = []
        self._compact_mode = False
        self._build_ui()
        self.refresh_all()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("moduleToolbar")
        self.toolbar_layout = QGridLayout(toolbar_frame)
        self.toolbar_layout.setContentsMargins(12, 8, 12, 8)
        self.toolbar_layout.setHorizontalSpacing(8)
        self.toolbar_copy = QWidget()
        title_box = QVBoxLayout()
        self.toolbar_copy.setLayout(title_box)
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(2)
        title = QLabel("备份与归档")
        title.setObjectName("toolbarContext")
        title_box.addWidget(title)
        subtitle = QLabel("本地 ZIP 归档、定时备份与可验证恢复")
        subtitle.setObjectName("mutedLabel")
        title_box.addWidget(subtitle)
        self.toolbar_layout.addWidget(self.toolbar_copy, 0, 0)
        self.toolbar_layout.setColumnStretch(0, 1)

        self.refresh_button = QPushButton("刷新记录")
        self.refresh_button.setIcon(lucide_icon("refresh-cw"))
        self.refresh_button.clicked.connect(self.refresh_all)
        self.toolbar_layout.addWidget(self.refresh_button, 0, 1)

        self.restore_file_button = QPushButton("导入 ZIP 恢复")
        self.restore_file_button.setObjectName("dangerButton")
        self.restore_file_button.clicked.connect(self._choose_restore_file)
        self.toolbar_layout.addWidget(self.restore_file_button, 0, 2)

        self.full_backup_button = QPushButton("立即完整备份")
        self.full_backup_button.setObjectName("primaryButton")
        self.full_backup_button.setIcon(
            lucide_icon("database-backup", color="#FFFFFF", active_color="#FFFFFF")
        )
        self.full_backup_button.clicked.connect(self._create_full_backup)
        self.toolbar_layout.addWidget(self.full_backup_button, 0, 3)

        self.more_button = QToolButton()
        self.more_button.setObjectName("moreButton")
        self.more_button.setText("更多")
        self.more_button.setIcon(lucide_icon("clipboard-check"))
        self.more_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        more_menu = QMenu(self.more_button)
        more_menu.addAction(lucide_icon("refresh-cw"), "刷新备份记录", self.refresh_all)
        more_menu.addAction("导入 ZIP 并恢复", self._choose_restore_file)
        self.more_button.setMenu(more_menu)
        self.more_button.setVisible(False)
        self.toolbar_layout.addWidget(self.more_button, 0, 4)
        layout.addWidget(toolbar_frame)

        self.status_line = QLabel()
        self.status_line.setObjectName("summaryText")
        self.status_line.setWordWrap(True)
        layout.addWidget(self.status_line)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("backupSplitter")
        self.main_splitter.setChildrenCollapsible(False)
        self.settings_panel = self._build_settings_panel()
        self.settings_scroll = scrollable_detail(self.settings_panel, name="backupSettingsScroll")
        self.main_splitter.addWidget(self.settings_scroll)
        self.history_panel = self._build_history_panel()
        self.main_splitter.addWidget(self.history_panel)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        restore_splitter(self.main_splitter, "backup_main", [420, 780])
        layout.addWidget(self.main_splitter, 1)

    def _build_settings_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("backupPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        archive_title = QLabel("手动备份与学期归档")
        archive_title.setObjectName("backupPanelTitle")
        layout.addWidget(archive_title)
        archive_note = QLabel(
            "完整备份可恢复全部数据。学期归档会写入所选学期的说明和统计，同时保留完整数据库快照。"
        )
        archive_note.setObjectName("backupHint")
        archive_note.setWordWrap(True)
        layout.addWidget(archive_note)

        full_button = QPushButton("创建完整数据备份")
        full_button.clicked.connect(self._create_full_backup)
        layout.addWidget(full_button)

        self.semester_layout = QGridLayout()
        self.semester_layout.setContentsMargins(0, 0, 0, 0)
        self.semester_layout.setHorizontalSpacing(8)
        self.semester_layout.setVerticalSpacing(8)
        self.semester_box = QComboBox()
        self.semester_box.setMinimumWidth(240)
        self.semester_box.currentIndexChanged.connect(self._update_semester_hint)
        self.semester_layout.addWidget(self.semester_box, 0, 0)
        self.semester_layout.setColumnStretch(0, 1)
        self.semester_backup_button = QPushButton("归档所选学期")
        self.semester_backup_button.clicked.connect(self._create_semester_archive)
        self.semester_layout.addWidget(self.semester_backup_button, 0, 1)
        layout.addLayout(self.semester_layout)

        self.semester_hint = QLabel()
        self.semester_hint.setObjectName("backupHint")
        self.semester_hint.setWordWrap(True)
        layout.addWidget(self.semester_hint)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("backupDivider")
        layout.addWidget(divider)

        schedule_title = QLabel("定时备份")
        schedule_title.setObjectName("backupPanelTitle")
        layout.addWidget(schedule_title)
        schedule_hint = QLabel("自动备份仅在本软件正在运行时执行，可设置每天或每周的指定时间。")
        schedule_hint.setObjectName("backupHint")
        schedule_hint.setWordWrap(True)
        layout.addWidget(schedule_hint)

        self.auto_enabled = QCheckBox("启用自动备份")
        self.auto_enabled.toggled.connect(self._sync_schedule_controls)
        layout.addWidget(self.auto_enabled)

        form = QFormLayout()
        form.setSpacing(11)
        self.frequency_box = QComboBox()
        self.frequency_box.addItem("每天", "daily")
        self.frequency_box.addItem("每周", "weekly")
        self.frequency_box.currentIndexChanged.connect(self._sync_schedule_controls)
        form.addRow("备份频率", self.frequency_box)

        self.weekday_label = QLabel("每周日期")
        self.weekday_box = QComboBox()
        for weekday, label in self.WEEKDAYS:
            self.weekday_box.addItem(label, weekday)
        form.addRow(self.weekday_label, self.weekday_box)

        self.time_edit = QTimeEdit(QTime(18, 0))
        self.time_edit.setDisplayFormat("HH:mm")
        form.addRow("执行时间", self.time_edit)

        self.directory_input = QLineEdit()
        self.directory_input.setPlaceholderText("自动备份保存目录")
        directory_row = QWidget()
        self.directory_layout = QGridLayout(directory_row)
        self.directory_layout.setContentsMargins(0, 0, 0, 0)
        self.directory_layout.setHorizontalSpacing(8)
        self.directory_layout.setVerticalSpacing(8)
        self.directory_layout.addWidget(self.directory_input, 0, 0)
        self.directory_layout.setColumnStretch(0, 1)
        self.browse_button = QPushButton("选择文件夹")
        self.browse_button.clicked.connect(self._choose_backup_directory)
        self.directory_layout.addWidget(self.browse_button, 0, 1)
        form.addRow("保存位置", directory_row)
        layout.addLayout(form)

        self.save_schedule_button = QPushButton("保存定时备份设置")
        self.save_schedule_button.setObjectName("primaryButton")
        self.save_schedule_button.clicked.connect(self._save_schedule)
        layout.addWidget(self.save_schedule_button)
        layout.addStretch(1)
        return panel

    def _build_history_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("backupPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("备份历史")
        title.setObjectName("backupPanelTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.history_summary = QLabel()
        self.history_summary.setObjectName("summaryText")
        header.addWidget(self.history_summary)
        layout.addLayout(header)

        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["类型", "创建时间", "文件", "说明", "状态"])
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        configure_resizable_table(self.history_table)
        self.history_table.setColumnWidth(0, 116)
        self.history_table.setColumnWidth(1, 138)
        self.history_table.setColumnWidth(2, 230)
        self.history_table.setColumnWidth(3, 260)
        self.history_table.setColumnWidth(4, 88)
        self.history_stack = QStackedWidget()
        self.history_stack.setObjectName("dataStateStack")
        self.history_stack.addWidget(self.history_table)
        self.history_empty_state = EmptyState(
            icon_name="database-backup",
            action=self._create_full_backup,
        )
        self.history_empty_state.set_content(
            "还没有备份记录",
            "创建第一份完整备份后，系统会在这里显示文件状态和恢复入口。",
            "创建完整备份",
        )
        self.history_stack.addWidget(self.history_empty_state)
        layout.addWidget(self.history_stack, 1)

        actions = QHBoxLayout()
        self.open_folder_button = QPushButton("打开所在文件夹")
        self.open_folder_button.clicked.connect(self._open_selected_folder)
        actions.addWidget(self.open_folder_button)
        self.restore_selected_button = QPushButton("恢复所选备份")
        self.restore_selected_button.setObjectName("dangerButton")
        self.restore_selected_button.clicked.connect(self._restore_selected_backup)
        actions.addWidget(self.restore_selected_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        return panel

    def refresh_all(self) -> None:
        selected_semester_id = self.semester_box.currentData()
        self._semesters = self.controller.list_semesters()
        self.semester_box.blockSignals(True)
        self.semester_box.clear()
        if not self._semesters:
            self.semester_box.addItem("暂无可归档学期", None)
        else:
            for semester in self._semesters:
                self.semester_box.addItem(
                    f"{semester['name']}（{semester['date_range_display']}）",
                    semester["id"],
                )
        selected_index = self.semester_box.findData(selected_semester_id)
        self.semester_box.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        self.semester_box.blockSignals(False)
        self._update_semester_hint()
        self.semester_backup_button.setEnabled(bool(self._semesters))

        self._load_settings()
        self._refresh_history()
        self.status_line.setText("完整备份和学期归档均可用于一键恢复；恢复前会自动保存当前数据。")

    def _load_settings(self) -> None:
        settings = self.controller.get_settings()
        self.auto_enabled.blockSignals(True)
        self.frequency_box.blockSignals(True)
        self.weekday_box.blockSignals(True)
        self.auto_enabled.setChecked(settings["auto_enabled"])
        index = self.frequency_box.findData(settings["schedule_frequency"])
        self.frequency_box.setCurrentIndex(index if index >= 0 else 0)
        weekday_index = self.weekday_box.findData(settings["schedule_weekday"])
        self.weekday_box.setCurrentIndex(weekday_index if weekday_index >= 0 else 0)
        parsed_time = QTime.fromString(settings["schedule_time"], "HH:mm")
        if parsed_time.isValid():
            self.time_edit.setTime(parsed_time)
        self.directory_input.setText(settings["destination_dir"])
        self.auto_enabled.blockSignals(False)
        self.frequency_box.blockSignals(False)
        self.weekday_box.blockSignals(False)
        self._sync_schedule_controls()

    def _refresh_history(self) -> None:
        self._records = self.controller.list_records()
        self.history_table.setRowCount(len(self._records))
        available_count = 0
        for row, record in enumerate(self._records):
            if record["exists"]:
                available_count += 1
            values = (
                record["action_display"],
                record["created_at_display"],
                record["file_name"],
                record["note"] or "—",
                "可恢复" if record["exists"] else "文件缺失",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(record["backup_path"] if column in (2, 4) else value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, record["backup_path"])
                self.history_table.setItem(row, column, item)
        self.history_summary.setText(f"{available_count} 个可用备份")
        self.history_stack.setCurrentWidget(
            self.history_table if self._records else self.history_empty_state
        )

    def set_compact_mode(self, compact: bool) -> None:
        if compact == self._compact_mode:
            return
        self._compact_mode = compact
        self.toolbar_copy.setVisible(not compact)
        self.refresh_button.setVisible(not compact)
        self.restore_file_button.setVisible(not compact)
        self.more_button.setVisible(compact)

        toolbar_widgets = (
            self.full_backup_button,
            self.refresh_button,
            self.restore_file_button,
            self.more_button,
        )
        for widget in toolbar_widgets:
            self.toolbar_layout.removeWidget(widget)
        if compact:
            self.toolbar_layout.addWidget(self.full_backup_button, 0, 0)
            self.toolbar_layout.addWidget(self.more_button, 0, 1)
            self.toolbar_layout.setColumnStretch(0, 1)
        else:
            self.toolbar_layout.addWidget(self.refresh_button, 0, 1)
            self.toolbar_layout.addWidget(self.restore_file_button, 0, 2)
            self.toolbar_layout.addWidget(self.full_backup_button, 0, 3)

        self.semester_layout.removeWidget(self.semester_box)
        self.semester_layout.removeWidget(self.semester_backup_button)
        self.directory_layout.removeWidget(self.directory_input)
        self.directory_layout.removeWidget(self.browse_button)
        if compact:
            self.semester_box.setMinimumWidth(0)
            self.semester_layout.addWidget(self.semester_box, 0, 0)
            self.semester_layout.addWidget(self.semester_backup_button, 1, 0)
            self.directory_layout.addWidget(self.directory_input, 0, 0)
            self.directory_layout.addWidget(self.browse_button, 1, 0)
        else:
            self.semester_box.setMinimumWidth(240)
            self.semester_layout.addWidget(self.semester_box, 0, 0)
            self.semester_layout.addWidget(self.semester_backup_button, 0, 1)
            self.directory_layout.addWidget(self.directory_input, 0, 0)
            self.directory_layout.addWidget(self.browse_button, 0, 1)

        self.main_splitter.setOrientation(
            Qt.Orientation.Vertical if compact else Qt.Orientation.Horizontal
        )
        set_compact_columns(self.history_table, (2, 3), compact)
        self.main_splitter.setSizes([430, 330] if compact else [420, 780])

    def _update_semester_hint(self, *_args) -> None:
        semester_id = self.semester_box.currentData()
        semester = next((item for item in self._semesters if item["id"] == semester_id), None)
        if semester is None:
            self.semester_hint.setText("请先在课程表的“学期与课时”中建立可归档的学期。")
            return
        self.semester_hint.setText(
            f"归档范围：{semester['date_range_display']}。归档包会保留完整恢复快照，方便日后查档。"
        )

    def _sync_schedule_controls(self, *_args) -> None:
        enabled = self.auto_enabled.isChecked()
        self.frequency_box.setEnabled(enabled)
        self.time_edit.setEnabled(enabled)
        is_weekly = self.frequency_box.currentData() == "weekly"
        self.weekday_label.setVisible(is_weekly)
        self.weekday_box.setVisible(is_weekly)
        self.weekday_box.setEnabled(enabled and is_weekly)

    def _choose_backup_directory(self) -> None:
        start_directory = self.directory_input.text().strip() or str(Path.home() / "Documents")
        directory = QFileDialog.getExistingDirectory(self, "选择自动备份保存位置", start_directory)
        if directory:
            self.directory_input.setText(directory)

    def _create_full_backup(self) -> None:
        settings = self.controller.get_settings()
        default_path = Path(settings["destination_dir"]) / self._default_file_name("完整备份")
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存完整数据备份",
            str(default_path),
            "ZIP 备份文件 (*.zip)",
        )
        if not selected_path:
            return
        try:
            archive = self.controller.create_full_backup(self._zip_path(selected_path))
        except BackupDataError as exc:
            QMessageBox.warning(self, "备份失败", str(exc))
            return
        self._refresh_history()
        self.status_line.setText(f"完整备份已创建：{archive.name}")
        QMessageBox.information(self, "备份完成", f"完整数据备份已创建：\n{archive}")

    def _create_semester_archive(self) -> None:
        semester_id = self.semester_box.currentData()
        semester = next((item for item in self._semesters if item["id"] == semester_id), None)
        if semester is None:
            QMessageBox.information(self, "请选择学期", "请先建立并选择需要归档的学期。")
            return
        settings = self.controller.get_settings()
        default_path = Path(settings["destination_dir"]) / self._default_file_name(f"学期归档_{semester['name']}")
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存学期归档",
            str(default_path),
            "ZIP 归档文件 (*.zip)",
        )
        if not selected_path:
            return
        try:
            archive = self.controller.create_semester_archive(int(semester_id), self._zip_path(selected_path))
        except BackupDataError as exc:
            QMessageBox.warning(self, "归档失败", str(exc))
            return
        self._refresh_history()
        self.status_line.setText(f"{semester['name']} 已归档：{archive.name}")
        QMessageBox.information(self, "归档完成", f"学期归档已创建：\n{archive}")

    def _save_schedule(self) -> None:
        try:
            settings = self.controller.save_settings(
                {
                    "auto_enabled": self.auto_enabled.isChecked(),
                    "schedule_frequency": self.frequency_box.currentData(),
                    "schedule_time": self.time_edit.time().toString("HH:mm"),
                    "schedule_weekday": self.weekday_box.currentData(),
                    "destination_dir": self.directory_input.text(),
                }
            )
        except BackupDataError as exc:
            QMessageBox.warning(self, "无法保存设置", str(exc))
            return
        self._load_settings()
        if settings["auto_enabled"]:
            frequency_text = "每天" if settings["schedule_frequency"] == "daily" else "每周指定日期"
            self.status_line.setText(f"已启用{frequency_text} {settings['schedule_time']} 的自动备份。")
        else:
            self.status_line.setText("自动备份已关闭，仍可随时创建手动备份或学期归档。")

    def _choose_restore_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择要恢复的 ZIP 备份", "", "ZIP 备份文件 (*.zip)")
        if path:
            self._restore_from_path(Path(path))

    def _restore_selected_backup(self) -> None:
        item = self.history_table.currentItem()
        if item is None:
            QMessageBox.information(self, "请选择备份", "请先在备份历史中选择一个可恢复的文件。")
            return
        path = self.history_table.item(item.row(), 0).data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        self._restore_from_path(Path(str(path)))

    def _restore_from_path(self, path: Path) -> None:
        try:
            info = self.controller.inspect_backup(path)
        except BackupDataError as exc:
            QMessageBox.warning(self, "无法读取备份", str(exc))
            return
        kind_label = "学期归档" if info["kind"] == "semester_archive" else "完整备份"
        semester = info.get("semester") or {}
        semester_text = f"\n归档学期：{semester.get('name', '')}" if semester else ""
        answer = QMessageBox.question(
            self,
            "确认恢复全部数据",
            f"将恢复“{info['file_name']}”（{kind_label}，创建于 {info['created_at']}）。{semester_text}\n\n"
            "当前所有本地数据会被该备份替换，但系统会先自动创建一份恢复前安全备份。\n\n确定继续吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            result = self.controller.restore_backup(path)
        except BackupDataError as exc:
            QMessageBox.warning(self, "恢复失败", str(exc))
            return
        QMessageBox.information(
            self,
            "恢复完成",
            f"数据已恢复。恢复前安全备份已保存：\n{result['safety_backup']}\n\n程序将重新启动以加载恢复后的全部数据。",
        )
        self.restart_requested.emit()

    def _open_selected_folder(self) -> None:
        item = self.history_table.currentItem()
        if item is None:
            QMessageBox.information(self, "请选择备份", "请先在备份历史中选择一个文件。")
            return
        path = Path(str(self.history_table.item(item.row(), 0).data(Qt.ItemDataRole.UserRole) or ""))
        if not path.is_file():
            QMessageBox.warning(self, "文件缺失", "该备份文件已被移动或删除。")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent))):
            QMessageBox.information(self, "备份位置", str(path.parent))

    def show_scheduler_success(self, archive_path: str) -> None:
        archive = Path(archive_path)
        self._refresh_history()
        self.status_line.setText(f"定时备份已完成：{archive.name}")

    def show_scheduler_error(self, message: str) -> None:
        self.status_line.setText(f"定时备份失败：{message}")

    @staticmethod
    def _default_file_name(prefix: str) -> str:
        safe_prefix = "".join("_" if character in '<>:"/\\|?*' else character for character in prefix)
        return f"{safe_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    @staticmethod
    def _zip_path(value: str) -> Path:
        path = Path(value)
        return path if path.suffix.lower() == ".zip" else path.with_suffix(".zip")
