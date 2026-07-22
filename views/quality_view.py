from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
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
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from controllers.quality_controller import QualityController, QualityDataError
from utils.quality_scoring import ENTRY_LEVELS, RULE_BY_KEY, SEMESTER_RULES, formatted_score
from utils.ui_layout import configure_resizable_table, restore_splitter
from views.quality_final_review_dialog import QualityFinalReviewDialog
from views.quality_import_result_dialog import QualityImportResultDialog


class QualityDimensionDialog(QDialog):
    def __init__(self, controller: QualityController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("评价维度")
        self.setMinimumWidth(440)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)
        form = QFormLayout()
        form.setSpacing(12)
        self.inputs: list[QLineEdit] = []
        for index, dimension in enumerate(self.controller.list_dimensions(), start=1):
            input_widget = QLineEdit(dimension["name"])
            self.inputs.append(input_widget)
            form.addRow(f"维度 {index}", input_widget)
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

    def _save(self) -> None:
        try:
            self.controller.update_dimensions([item.text() for item in self.inputs])
        except QualityDataError as exc:
            QMessageBox.warning(self, "无法保存", str(exc))
            return
        self.accept()


class QualityTableModel(QAbstractTableModel):
    headers = ["姓名", "学号", "班级", "已完成学期", "当前累计", "最终分数"]

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict[str, str]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return None
        return self.rows[index.row()].get(self.headers[index.column()], "")

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None

    def set_rows(self, rows: list[dict[str, str]]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def student_id_at(self, row: int) -> int | None:
        if 0 <= row < len(self.rows):
            return int(self.rows[row]["_id"])
        return None


class QualityView(QWidget):
    """Six-semester quality evaluation entry and score conversion workspace."""

    def __init__(self) -> None:
        super().__init__()
        self.controller = QualityController()
        self.model = QualityTableModel()
        self.current_student_id: int | None = None
        self.current_dimensions: list[str] = []
        self._build_ui()
        self._refresh_class_filter()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        title = QLabel("综合素质评价")
        title.setObjectName("sectionTitle")
        toolbar.addWidget(title)
        toolbar.addStretch(1)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("搜索姓名或学号...")
        self.search_input.setMinimumWidth(220)
        self.search_input.textChanged.connect(self.reload)
        toolbar.addWidget(self.search_input)
        self.class_filter = QComboBox()
        self.class_filter.setObjectName("classFilter")
        self.class_filter.setMinimumWidth(140)
        self.class_filter.currentIndexChanged.connect(self.reload)
        toolbar.addWidget(self.class_filter)
        dimension_button = QPushButton("评价维度")
        dimension_button.clicked.connect(self._open_dimension_settings)
        toolbar.addWidget(dimension_button)
        final_button = QPushButton("最终评定")
        final_button.setObjectName("primaryButton")
        final_button.clicked.connect(self._open_final_review)
        toolbar.addWidget(final_button)
        import_button = QPushButton("导入 Excel")
        import_button.setObjectName("secondaryButton")
        import_button.clicked.connect(self._import_quality)
        toolbar.addWidget(import_button)
        export_button = QPushButton("导出 Excel")
        export_button.setObjectName("secondaryButton")
        export_button.clicked.connect(self._export_quality)
        toolbar.addWidget(export_button)
        layout.addLayout(toolbar)

        self.count_label = QLabel("学生 0 人")
        self.count_label.setObjectName("summaryText")
        layout.addWidget(self.count_label)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("qualitySplitter")
        self.main_splitter.setChildrenCollapsible(False)

        table_frame = QFrame()
        table_frame.setObjectName("tablePane")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableView()
        self.table.setObjectName("studentTable")
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        configure_resizable_table(self.table)
        self.table.setColumnWidth(0, 88)
        self.table.setColumnWidth(1, 94)
        self.table.setColumnWidth(2, 108)
        self.table.setColumnWidth(3, 94)
        self.table.setColumnWidth(4, 96)
        self.table.clicked.connect(self._select_student)
        table_layout.addWidget(self.table)
        self.main_splitter.addWidget(table_frame)

        self.editor = QFrame()
        self.editor.setObjectName("qualityPane")
        self._build_editor()
        self.main_splitter.addWidget(self.editor)
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 2)
        restore_splitter(self.main_splitter, "quality_main", [720, 440])
        layout.addWidget(self.main_splitter, 1)

    def _build_editor(self) -> None:
        layout = QVBoxLayout(self.editor)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        header = QVBoxLayout()
        header.setSpacing(2)
        self.student_name_label = QLabel("选择学生")
        self.student_name_label.setObjectName("detailName")
        self.student_class_label = QLabel("")
        self.student_class_label.setObjectName("mutedLabel")
        header.addWidget(self.student_name_label)
        header.addWidget(self.student_class_label)
        layout.addLayout(header)

        self.semester_box = QComboBox()
        for rule in SEMESTER_RULES:
            self.semester_box.addItem(rule.label, rule.key)
        self.semester_box.currentIndexChanged.connect(self._load_current_evaluation)
        layout.addWidget(self.semester_box)

        self.term_score_label = QLabel("本学期得分：-")
        self.term_score_label.setObjectName("qualityScore")
        layout.addWidget(self.term_score_label)

        self.dimension_form = QFormLayout()
        self.dimension_form.setSpacing(10)
        self.level_boxes: dict[str, QComboBox] = {}
        layout.addLayout(self.dimension_form)

        self.save_button = QPushButton("保存本学期评价")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self._save_evaluation)
        layout.addWidget(self.save_button)

        score_title = QLabel("换算进度")
        score_title.setObjectName("sectionTitle")
        layout.addWidget(score_title)
        self.total_score_label = QLabel("当前累计：-")
        self.total_score_label.setObjectName("qualityScore")
        self.final_score_label = QLabel("五维总分：-")
        self.final_score_label.setObjectName("qualityScore")
        layout.addWidget(self.total_score_label)
        layout.addWidget(self.final_score_label)

        self.score_tabs = QTabWidget()
        self.semester_table = QTableWidget(0, 3)
        self.semester_table.setHorizontalHeaderLabels(["学期", "得分", "状态"])
        self.semester_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.semester_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.semester_table.verticalHeader().setVisible(False)
        configure_resizable_table(self.semester_table)
        semester_page = QWidget()
        semester_layout = QVBoxLayout(semester_page)
        semester_layout.setContentsMargins(0, 8, 0, 0)
        semester_layout.addWidget(self.semester_table)
        self.score_tabs.addTab(semester_page, "学期进度")

        self.dimension_table = QTableWidget(0, 3)
        self.dimension_table.setHorizontalHeaderLabels(["维度", "得分", "状态"])
        self.dimension_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.dimension_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.dimension_table.verticalHeader().setVisible(False)
        configure_resizable_table(self.dimension_table)
        dimension_page = QWidget()
        dimension_layout = QVBoxLayout(dimension_page)
        dimension_layout.setContentsMargins(0, 8, 0, 0)
        dimension_layout.addWidget(self.dimension_table)
        self.score_tabs.addTab(dimension_page, "维度得分")
        layout.addWidget(self.score_tabs, 1)
        self._clear_editor()

    def _refresh_class_filter(self) -> None:
        selected_id = self.class_filter.currentData()
        self.class_filter.blockSignals(True)
        self.class_filter.clear()
        self.class_filter.addItem("全部班级", None)
        for class_group in self.controller.list_classes():
            self.class_filter.addItem(class_group["name"], class_group["id"])
        index = self.class_filter.findData(selected_id)
        self.class_filter.setCurrentIndex(index if index >= 0 else 0)
        self.class_filter.blockSignals(False)

    def reload(self) -> None:
        class_id = self.class_filter.currentData()
        rows = self.controller.list_student_overviews(class_id, self.search_input.text())
        self.model.set_rows(rows)
        self.count_label.setText(f"学生 {len(rows)} 人")
        self._clear_editor()

    def _select_student(self, index: QModelIndex) -> None:
        student_id = self.model.student_id_at(index.row())
        if student_id is None:
            return
        self.current_student_id = student_id
        self._load_current_evaluation()

    def _load_current_evaluation(self) -> None:
        if self.current_student_id is None:
            return
        semester_key = str(self.semester_box.currentData())
        try:
            data = self.controller.get_student_evaluation(self.current_student_id, semester_key)
        except QualityDataError as exc:
            QMessageBox.warning(self, "无法读取", str(exc))
            return
        self.student_name_label.setText(data["name"])
        self.student_class_label.setText(data["class_name"])
        self._set_dimension_inputs(data["dimensions"], data["ratings"])
        self._update_term_score()
        self._update_summary(data)
        self.save_button.setEnabled(True)

    def _set_dimension_inputs(self, dimensions: list[str], ratings: dict[str, str]) -> None:
        while self.dimension_form.count():
            item = self.dimension_form.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.level_boxes = {}
        self.current_dimensions = dimensions
        for dimension in dimensions:
            box = QComboBox()
            box.addItem("请选择", "")
            for level in ENTRY_LEVELS:
                box.addItem(level, level)
            selected = box.findData(ratings.get(dimension, ""))
            box.setCurrentIndex(selected if selected >= 0 else 0)
            box.currentIndexChanged.connect(self._update_term_score)
            self.level_boxes[dimension] = box
            self.dimension_form.addRow(dimension, box)

    def _update_term_score(self) -> None:
        semester_key = str(self.semester_box.currentData())
        rule = RULE_BY_KEY[semester_key]
        score = sum(rule.level_scores.get(str(box.currentData()), 0) for box in self.level_boxes.values())
        self.term_score_label.setText(f"本学期得分：{formatted_score(score)}/{formatted_score(rule.maximum_score)}")

    def _update_summary(self, data: dict[str, Any]) -> None:
        self.total_score_label.setText(
            f"当前累计：{formatted_score(data['total_score'])}/{formatted_score(data['total_maximum'])}"
        )
        if data["final_ready"]:
            title = "五维总分（含 N/A）" if data["contains_na"] else "五维总分"
            self.final_score_label.setText(f"{title}：{formatted_score(data['final_score'])}/50")
        else:
            self.final_score_label.setText("五维总分：待完成六学期")
        self.semester_table.setRowCount(len(SEMESTER_RULES))
        for row_index, rule in enumerate(SEMESTER_RULES):
            completed = rule.key in data["completed_keys"]
            values = [
                rule.label,
                f"{formatted_score(data['semester_scores'][rule.key])}/{formatted_score(rule.maximum_score)}",
                "含 N/A" if rule.key in data["na_semesters"] else "已完成" if completed else "未完成",
            ]
            for column, value in enumerate(values):
                self.semester_table.setItem(row_index, column, QTableWidgetItem(value))
        self.dimension_table.setRowCount(len(data["dimensions"]))
        for row_index, dimension in enumerate(data["dimensions"]):
            completed = dimension in data["completed_dimensions"]
            values = [
                dimension,
                f"{formatted_score(data['dimension_scores'][dimension])}/10",
                "含 N/A" if dimension in data["na_dimensions"] else "已完成" if completed else "未完成",
            ]
            for column, value in enumerate(values):
                self.dimension_table.setItem(row_index, column, QTableWidgetItem(value))

    def _save_evaluation(self) -> None:
        if self.current_student_id is None:
            QMessageBox.information(self, "请选择学生", "请先从左侧选择一名学生。")
            return
        ratings = {dimension: str(box.currentData()) for dimension, box in self.level_boxes.items()}
        try:
            self.controller.save_evaluation(self.current_student_id, str(self.semester_box.currentData()), ratings)
        except QualityDataError as exc:
            QMessageBox.warning(self, "无法保存", str(exc))
            return
        selected_id = self.current_student_id
        self.reload()
        self._select_student_by_id(selected_id)

    def _open_dimension_settings(self) -> None:
        if QualityDimensionDialog(self.controller, self).exec():
            self.reload()

    def _open_final_review(self) -> None:
        QualityFinalReviewDialog(
            self.controller,
            self.class_filter.currentData(),
            self,
        ).exec()
        self.reload()

    def _import_quality(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入综合素质评价",
            str(Path.home() / "Desktop"),
            "Excel 文件 (*.xlsx *.xlsm)",
        )
        if not file_path:
            return
        try:
            result = self.controller.import_quality_from_excel(file_path, self.class_filter.currentData())
        except QualityDataError as exc:
            QMessageBox.warning(self, "导入失败", str(exc))
            return
        self._refresh_class_filter()
        class_index = self.class_filter.findData(result.target_class_id)
        if class_index >= 0:
            self.class_filter.setCurrentIndex(class_index)
        self.reload()
        QualityImportResultDialog(result, self).exec()

    def _export_quality(self) -> None:
        class_id = self.class_filter.currentData()
        class_name = self.class_filter.currentText()
        default_name = f"{class_name}综合素质评价.xlsx" if class_id is not None else "综合素质评价.xlsx"
        default_path = str(Path.home() / "Desktop" / default_name)
        file_path, _ = QFileDialog.getSaveFileName(self, "导出综合素质评价", default_path, "Excel 文件 (*.xlsx)")
        if not file_path:
            return
        path = Path(file_path)
        if path.suffix.lower() != ".xlsx":
            path = path.with_suffix(".xlsx")
        try:
            result_path = self.controller.export_quality_to_excel(path, class_id, self.search_input.text())
        except Exception:
            QMessageBox.warning(self, "导出失败", "无法写入 Excel 文件，请确认文件未被其他程序占用。")
            return
        QMessageBox.information(self, "导出完成", f"Excel 文件已生成：\n{result_path}")

    def _select_student_by_id(self, student_id: int) -> None:
        for row in range(self.model.rowCount()):
            if self.model.student_id_at(row) == student_id:
                index = self.model.index(row, 0)
                self.table.setCurrentIndex(index)
                self._select_student(index)
                return

    def _clear_editor(self) -> None:
        self.current_student_id = None
        self.current_dimensions = []
        self.student_name_label.setText("选择学生")
        self.student_class_label.setText("")
        self.term_score_label.setText("本学期得分：-")
        self.total_score_label.setText("当前累计：-")
        self.final_score_label.setText("五维总分：-")
        self.semester_table.setRowCount(0)
        self.dimension_table.setRowCount(0)
        self.save_button.setEnabled(False)
        while self.dimension_form.count():
            item = self.dimension_form.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.level_boxes = {}
