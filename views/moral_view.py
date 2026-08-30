from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QDate, QModelIndex, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from controllers.moral_controller import MoralController, MoralDataError
from utils.ui_icons import lucide_icon
from utils.ui_layout import configure_resizable_table, restore_splitter, set_compact_columns
from views.moral_record_dialog import MoralRecordDialog
from views.ui_components import EmptyState, scrollable_detail


class MoralTableModel(QAbstractTableModel):
    columns = (
        ("record_date_display", "日期"),
        ("student_name", "学生"),
        ("class_name", "班级"),
        ("category", "类别"),
        ("title", "活动或奖项"),
        ("award_level", "级别"),
        ("points_display", "积分"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return None
        key, _header = self.columns[index.column()]
        value = self.rows[index.row()].get(key, "")
        return str(value) if value not in (None, "") else "—"

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.columns[section][1]
        return None

    def set_rows(self, rows: list[dict[str, Any]]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def record_id_at(self, row: int) -> int | None:
        if 0 <= row < len(self.rows):
            return int(self.rows[row]["id"])
        return None


class MoralDetailPane(QFrame):
    data_changed = Signal()

    def __init__(self, controller: MoralController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.record_id: int | None = None
        self.setObjectName("detailPane")
        self._build_ui()
        self.clear()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.name_label = QLabel("德育评价记录")
        self.name_label.setObjectName("detailName")
        self.class_label = QLabel("")
        self.class_label.setObjectName("mutedLabel")
        title_box.addWidget(self.name_label)
        title_box.addWidget(self.class_label)
        header.addLayout(title_box)
        header.addStretch(1)
        self.edit_button = QPushButton("编辑")
        self.delete_button = QPushButton("删除")
        self.delete_button.setObjectName("dangerButton")
        self.edit_button.clicked.connect(self._edit_record)
        self.delete_button.clicked.connect(self._delete_record)
        header.addWidget(self.edit_button)
        header.addWidget(self.delete_button)
        layout.addLayout(header)

        self.student_summary_label = QLabel()
        self.student_summary_label.setObjectName("qualityScore")
        self.student_summary_label.setWordWrap(True)
        layout.addWidget(self.student_summary_label)

        form = QFormLayout()
        form.setSpacing(10)
        self.fields: dict[str, QLabel] = {}
        for key, label in (
            ("record_date_display", "日期"),
            ("category", "类别"),
            ("title", "活动或奖项"),
            ("award_level", "奖项级别"),
            ("organizer", "主办方"),
            ("points_display", "德育积分"),
            ("note", "备注"),
        ):
            value = QLabel()
            value.setObjectName("detailValue")
            value.setWordWrap(True)
            self.fields[key] = value
            form.addRow(label, value)
        layout.addLayout(form)
        layout.addStretch(1)

    def clear(self) -> None:
        self.record_id = None
        self.name_label.setText("德育评价记录")
        self.class_label.setText("从左侧列表选择一条记录")
        self.student_summary_label.setText("学生累计记录、获奖与积分将在这里显示")
        for label in self.fields.values():
            label.setText("—")
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.edit_button.setToolTip("请先从记录列表选择一条记录")
        self.delete_button.setToolTip("请先从记录列表选择一条记录")

    def load_record(self, record_id: int) -> None:
        try:
            record = self.controller.get_record(record_id)
            summary = self.controller.get_student_summary(record["student_id"])
        except MoralDataError:
            self.clear()
            return
        self.record_id = record_id
        suffix = f"（{record['student_no']}）" if record["student_no"] else ""
        self.name_label.setText(f"{record['student_name']}{suffix}")
        self.class_label.setText(record["class_name"])
        self.student_summary_label.setText(
            "累计 {total} 条  |  集体活动 {activities} 次  |  获奖 {awards} 项  |  积分 {points}".format(
                total=summary["total"],
                activities=summary["activities"],
                awards=summary["awards"],
                points=self._number(summary["points"]),
            )
        )
        for key, label in self.fields.items():
            label.setText(str(record.get(key) or "—"))
        self.edit_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.edit_button.setToolTip("编辑所选德育记录")
        self.delete_button.setToolTip("删除所选记录，需要再次确认")

    def _edit_record(self) -> None:
        if self.record_id is None:
            return
        dialog = MoralRecordDialog(self.controller, self.record_id, self)
        if dialog.exec() and dialog.saved_record_id is not None:
            self.load_record(dialog.saved_record_id)
            self.data_changed.emit()

    def _delete_record(self) -> None:
        if self.record_id is None:
            return
        answer = QMessageBox.question(
            self,
            "删除德育记录",
            "确定删除这条德育记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.controller.delete_record(self.record_id)
        except MoralDataError as exc:
            QMessageBox.warning(self, "无法删除", str(exc))
            return
        self.clear()
        self.data_changed.emit()

    @staticmethod
    def _number(value: float | int) -> str:
        return f"{float(value):.2f}".rstrip("0").rstrip(".")


class MoralView(QWidget):
    """Independent workspace for student moral-development evaluation records."""

    def __init__(self) -> None:
        super().__init__()
        self.controller = MoralController()
        self.model = MoralTableModel()
        self._compact_mode = False
        self._empty_action_mode = ""
        self._build_ui()
        self.refresh_filters()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("moduleToolbar")
        self.toolbar_layout = QGridLayout(toolbar_frame)
        self.toolbar_layout.setContentsMargins(12, 8, 12, 8)
        self.toolbar_layout.setHorizontalSpacing(8)
        self.toolbar_context = QLabel("记录管理")
        self.toolbar_context.setObjectName("toolbarContext")
        self.toolbar_layout.addWidget(self.toolbar_context, 0, 0)
        self.toolbar_layout.setColumnStretch(0, 1)
        self.export_button = QPushButton("导出 Excel")
        self.export_button.setIcon(lucide_icon("file-down"))
        self.export_button.clicked.connect(self._export_records)
        self.toolbar_layout.addWidget(self.export_button, 0, 1)
        self.add_button = QPushButton("新增记录")
        self.add_button.setObjectName("primaryButton")
        self.add_button.setIcon(
            lucide_icon("user-plus", color="#FFFFFF", active_color="#FFFFFF")
        )
        self.add_button.clicked.connect(self._add_record)
        self.toolbar_layout.addWidget(self.add_button, 0, 2)
        layout.addWidget(toolbar_frame)

        filter_frame = QFrame()
        filter_frame.setObjectName("filterBar")
        self.filter_layout = QGridLayout(filter_frame)
        self.filter_layout.setContentsMargins(12, 10, 12, 10)
        self.filter_layout.setHorizontalSpacing(10)
        self.filter_layout.setVerticalSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setMinimumWidth(220)
        self.search_input.setPlaceholderText("搜索学生、学号、活动或奖项...")
        self.search_input.textChanged.connect(self.reload)
        self.filter_layout.addWidget(self.search_input, 0, 0)
        self.filter_layout.setColumnStretch(0, 1)

        self.class_filter = QComboBox()
        self.class_filter.setObjectName("classFilter")
        self.class_filter.setMinimumWidth(135)
        self.class_filter.currentIndexChanged.connect(self.reload)
        self.filter_layout.addWidget(self.class_filter, 0, 1)

        self.category_filter = QComboBox()
        self.category_filter.setObjectName("classFilter")
        self.category_filter.setMinimumWidth(120)
        self.category_filter.addItem("全部类别", None)
        for category in self.controller.CATEGORIES:
            self.category_filter.addItem(category, category)
        self.category_filter.currentIndexChanged.connect(self.reload)
        self.filter_layout.addWidget(self.category_filter, 0, 2)

        self.date_filter = QCheckBox("日期范围")
        self.date_filter.toggled.connect(self._toggle_date_filter)
        self.filter_layout.addWidget(self.date_filter, 0, 3)

        self.start_date = QDateEdit(QDate.currentDate().addMonths(-1))
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.dateChanged.connect(self._reload_if_date_filter_enabled)
        self.start_date.setEnabled(False)
        self.filter_layout.addWidget(self.start_date, 0, 4)

        self.end_date = QDateEdit(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.dateChanged.connect(self._reload_if_date_filter_enabled)
        self.end_date.setEnabled(False)
        self.filter_layout.addWidget(self.end_date, 0, 5)
        layout.addWidget(filter_frame)

        self.summary_layout = QGridLayout()
        self.summary_layout.setHorizontalSpacing(14)
        self.summary_layout.setVerticalSpacing(4)
        self.total_label = self._summary_label()
        self.activity_label = self._summary_label()
        self.award_label = self._summary_label()
        self.points_label = self._summary_label()
        for label in (self.total_label, self.activity_label, self.award_label, self.points_label):
            self.summary_layout.addWidget(label, 0, self.summary_layout.count())
        self.summary_layout.setColumnStretch(4, 1)
        layout.addLayout(self.summary_layout)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("moralSplitter")
        self.main_splitter.setChildrenCollapsible(False)

        table_frame = QFrame()
        table_frame.setObjectName("tablePane")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        configure_resizable_table(self.table)
        for column, width in enumerate((104, 84, 106, 92, 190, 80, 66)):
            self.table.setColumnWidth(column, width)
        self.table.clicked.connect(self._show_selected_record)
        self.table_stack = QStackedWidget()
        self.table_stack.setObjectName("dataStateStack")
        self.table_stack.addWidget(self.table)
        self.empty_state = EmptyState(icon_name="award", action=self._handle_empty_action)
        self.table_stack.addWidget(self.empty_state)
        table_layout.addWidget(self.table_stack)
        self.main_splitter.addWidget(table_frame)

        self.detail_pane = MoralDetailPane(self.controller)
        self.detail_pane.data_changed.connect(self.reload)
        self.detail_scroll = scrollable_detail(self.detail_pane, name="moralDetailScroll")
        self.main_splitter.addWidget(self.detail_scroll)
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 2)
        restore_splitter(self.main_splitter, "moral_main", [760, 420])
        layout.addWidget(self.main_splitter, 1)

    def refresh_filters(self) -> None:
        selected_class_id = self.class_filter.currentData()
        self.class_filter.blockSignals(True)
        self.class_filter.clear()
        self.class_filter.addItem("全部班级", None)
        for class_group in self.controller.list_classes():
            self.class_filter.addItem(class_group["name"], class_group["id"])
        index = self.class_filter.findData(selected_class_id)
        self.class_filter.setCurrentIndex(index if index >= 0 else 0)
        self.class_filter.blockSignals(False)
        self.reload()

    def reload(self) -> None:
        filters = self._current_filters()
        rows = self.controller.list_records(**filters)
        self.model.set_rows(rows)
        summary = self.controller.get_summary(**filters)
        self.total_label.setText(f"记录 {summary['total']} 条")
        self.activity_label.setText(f"集体活动 {summary['activities']} 次")
        self.award_label.setText(f"获奖 {summary['awards']} 项")
        self.points_label.setText(f"累计积分 {self._number(summary['points'])}")
        self.detail_pane.clear()
        if rows:
            self.table_stack.setCurrentWidget(self.table)
        else:
            self.table_stack.setCurrentWidget(self.empty_state)
            if self._has_active_filters():
                self._empty_action_mode = "filters"
                self.empty_state.set_content(
                    "没有匹配的德育记录",
                    "请调整学生、班级、类别或日期范围后再次查看。",
                    "清除筛选",
                )
            elif not self.controller.list_students():
                self._empty_action_mode = ""
                self.empty_state.set_content(
                    "还没有学生档案",
                    "请先到学生数据中心建立学生，之后即可记录活动、获奖和社会实践。",
                )
            else:
                self._empty_action_mode = "add"
                self.empty_state.set_content(
                    "暂时没有德育记录",
                    "新增集体活动、荣誉或社会实践记录后，可按类别和日期统一查看。",
                    "新增记录",
                )

    def _current_filters(self) -> dict[str, Any]:
        return {
            "class_id": self.class_filter.currentData(),
            "keyword": self.search_input.text(),
            "category": self.category_filter.currentData(),
            "start_date": self.start_date.date().toPython() if self.date_filter.isChecked() else None,
            "end_date": self.end_date.date().toPython() if self.date_filter.isChecked() else None,
        }

    def _toggle_date_filter(self, enabled: bool) -> None:
        self.start_date.setEnabled(enabled)
        self.end_date.setEnabled(enabled)
        self.reload()

    def _reload_if_date_filter_enabled(self) -> None:
        if self.date_filter.isChecked():
            self.reload()

    def _has_active_filters(self) -> bool:
        return bool(
            self.search_input.text().strip()
            or self.class_filter.currentData() is not None
            or self.category_filter.currentData() is not None
            or self.date_filter.isChecked()
        )

    def _handle_empty_action(self) -> None:
        if self._empty_action_mode == "filters":
            self.search_input.clear()
            self.class_filter.setCurrentIndex(0)
            self.category_filter.setCurrentIndex(0)
            self.date_filter.setChecked(False)
        elif self._empty_action_mode == "add":
            self._add_record()

    def _show_selected_record(self, index: QModelIndex) -> None:
        record_id = self.model.record_id_at(index.row())
        if record_id is not None:
            self.detail_pane.load_record(record_id)

    def _add_record(self) -> None:
        if not self.controller.list_students():
            QMessageBox.information(self, "暂无学生", "请先在学生数据中心建立学生档案。")
            return
        dialog = MoralRecordDialog(self.controller, parent=self)
        if dialog.exec() and dialog.saved_record_id is not None:
            self.reload()
            self._select_record(dialog.saved_record_id)

    def _select_record(self, record_id: int) -> None:
        for row_index in range(self.model.rowCount()):
            if self.model.record_id_at(row_index) == record_id:
                index = self.model.index(row_index, 0)
                self.table.setCurrentIndex(index)
                self._show_selected_record(index)
                return

    def _export_records(self) -> None:
        default_path = Path.home() / "Desktop" / "德育评价.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出德育评价记录",
            str(default_path),
            "Excel 文件 (*.xlsx)",
        )
        if not file_path:
            return
        target_path = Path(file_path)
        if target_path.suffix.lower() != ".xlsx":
            target_path = target_path.with_suffix(".xlsx")
        try:
            result_path = self.controller.export_records_to_excel(target_path, **self._current_filters())
        except Exception:
            QMessageBox.warning(self, "导出失败", "无法写入 Excel 文件，请确认文件未被其他程序占用。")
            return
        QMessageBox.information(self, "导出完成", f"Excel 文件已生成：\n{result_path}")

    @staticmethod
    def _summary_label() -> QLabel:
        label = QLabel()
        label.setObjectName("summaryText")
        return label

    @staticmethod
    def _number(value: float | int) -> str:
        return f"{float(value):.2f}".rstrip("0").rstrip(".")

    def set_compact_mode(self, compact: bool) -> None:
        if compact == self._compact_mode:
            return
        self._compact_mode = compact
        self.toolbar_context.setVisible(not compact)

        filter_widgets = (
            self.search_input,
            self.class_filter,
            self.category_filter,
            self.date_filter,
            self.start_date,
            self.end_date,
        )
        for widget in filter_widgets:
            self.filter_layout.removeWidget(widget)
        if compact:
            self.search_input.setMinimumWidth(0)
            self.class_filter.setMinimumWidth(105)
            self.category_filter.setMinimumWidth(105)
            self.filter_layout.addWidget(self.search_input, 0, 0, 1, 3)
            self.filter_layout.addWidget(self.class_filter, 1, 0)
            self.filter_layout.addWidget(self.category_filter, 1, 1)
            self.filter_layout.addWidget(self.date_filter, 1, 2)
            self.filter_layout.addWidget(self.start_date, 2, 0)
            self.filter_layout.addWidget(self.end_date, 2, 1, 1, 2)
        else:
            self.search_input.setMinimumWidth(220)
            self.class_filter.setMinimumWidth(135)
            self.category_filter.setMinimumWidth(120)
            self.filter_layout.addWidget(self.search_input, 0, 0)
            self.filter_layout.addWidget(self.class_filter, 0, 1)
            self.filter_layout.addWidget(self.category_filter, 0, 2)
            self.filter_layout.addWidget(self.date_filter, 0, 3)
            self.filter_layout.addWidget(self.start_date, 0, 4)
            self.filter_layout.addWidget(self.end_date, 0, 5)

        summary_widgets = (
            self.total_label,
            self.activity_label,
            self.award_label,
            self.points_label,
        )
        for label in summary_widgets:
            self.summary_layout.removeWidget(label)
        columns = 2 if compact else 4
        for index, label in enumerate(summary_widgets):
            row, column = divmod(index, columns)
            self.summary_layout.addWidget(label, row, column)

        self.main_splitter.setOrientation(
            Qt.Orientation.Vertical if compact else Qt.Orientation.Horizontal
        )
        set_compact_columns(self.table, (2, 5), compact)
        self.main_splitter.setSizes([300, 350] if compact else [760, 420])
