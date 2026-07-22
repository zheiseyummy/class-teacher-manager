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
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from controllers.moral_controller import MoralController, MoralDataError
from utils.ui_layout import configure_resizable_table, restore_splitter
from views.moral_record_dialog import MoralRecordDialog


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
        self._build_ui()
        self.refresh_filters()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        title = QLabel("德育评价")
        title.setObjectName("sectionTitle")
        toolbar.addWidget(title)
        toolbar.addStretch(1)
        export_button = QPushButton("导出 Excel")
        export_button.clicked.connect(self._export_records)
        toolbar.addWidget(export_button)
        add_button = QPushButton("新增记录")
        add_button.setObjectName("primaryButton")
        add_button.clicked.connect(self._add_record)
        toolbar.addWidget(add_button)
        layout.addLayout(toolbar)

        filters = QHBoxLayout()
        filters.setSpacing(10)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setMinimumWidth(220)
        self.search_input.setPlaceholderText("搜索学生、学号、活动或奖项...")
        self.search_input.textChanged.connect(self.reload)
        filters.addWidget(self.search_input, 1)

        self.class_filter = QComboBox()
        self.class_filter.setObjectName("classFilter")
        self.class_filter.setMinimumWidth(135)
        self.class_filter.currentIndexChanged.connect(self.reload)
        filters.addWidget(self.class_filter)

        self.category_filter = QComboBox()
        self.category_filter.setObjectName("classFilter")
        self.category_filter.setMinimumWidth(120)
        self.category_filter.addItem("全部类别", None)
        for category in self.controller.CATEGORIES:
            self.category_filter.addItem(category, category)
        self.category_filter.currentIndexChanged.connect(self.reload)
        filters.addWidget(self.category_filter)

        self.date_filter = QCheckBox("日期范围")
        self.date_filter.toggled.connect(self._toggle_date_filter)
        filters.addWidget(self.date_filter)

        self.start_date = QDateEdit(QDate.currentDate().addMonths(-1))
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.dateChanged.connect(self._reload_if_date_filter_enabled)
        self.start_date.setEnabled(False)
        filters.addWidget(self.start_date)

        self.end_date = QDateEdit(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.dateChanged.connect(self._reload_if_date_filter_enabled)
        self.end_date.setEnabled(False)
        filters.addWidget(self.end_date)
        layout.addLayout(filters)

        summary = QHBoxLayout()
        self.total_label = self._summary_label()
        self.activity_label = self._summary_label()
        self.award_label = self._summary_label()
        self.points_label = self._summary_label()
        for label in (self.total_label, self.activity_label, self.award_label, self.points_label):
            summary.addWidget(label)
        summary.addStretch(1)
        layout.addLayout(summary)

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
        table_layout.addWidget(self.table)
        self.main_splitter.addWidget(table_frame)

        self.detail_pane = MoralDetailPane(self.controller)
        self.detail_pane.data_changed.connect(self.reload)
        self.main_splitter.addWidget(self.detail_pane)
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
        self.model.set_rows(self.controller.list_records(**filters))
        summary = self.controller.get_summary(**filters)
        self.total_label.setText(f"记录 {summary['total']} 条")
        self.activity_label.setText(f"集体活动 {summary['activities']} 次")
        self.award_label.setText(f"获奖 {summary['awards']} 项")
        self.points_label.setText(f"累计积分 {self._number(summary['points'])}")
        self.detail_pane.clear()

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
