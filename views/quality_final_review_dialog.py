from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from controllers.quality_controller import QualityController, QualityDataError
from utils.quality_scoring import FINAL_LEVELS, formatted_score
from utils.ui_layout import configure_resizable_table, configure_responsive_dialog


class QualityFinalReviewDialog(QDialog):
    """Class-by-class review workspace for the five final dimension levels."""

    headers = [
        "姓名",
        "学号",
        "累计得分",
        "班级排名",
        "系统等级",
        "最终等级",
        "学期数据",
        "五维总分",
        "总排名",
        "调整状态",
    ]

    def __init__(
        self,
        controller: QualityController,
        initial_class_id: int | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.initial_class_id = initial_class_id
        self.review_data: dict | None = None
        self.setWindowTitle("综合素质最终评定")
        self._build_ui()
        configure_responsive_dialog(self, 1260, 760, minimum_height=480)
        self._load_filters()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)

        title = QLabel("最终五维评定")
        title.setObjectName("detailName")
        layout.addWidget(title)

        filters = QGridLayout()
        filters.setHorizontalSpacing(10)
        filters.setVerticalSpacing(8)
        self.class_box = QComboBox()
        self.class_box.setMinimumWidth(0)
        self.class_box.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.class_box, 0, 0)
        self.dimension_box = QComboBox()
        self.dimension_box.setMinimumWidth(0)
        self.dimension_box.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.dimension_box, 0, 1)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索姓名或学号...")
        self.search_input.setMinimumWidth(0)
        self.search_input.textChanged.connect(self.refresh)
        filters.addWidget(self.search_input, 1, 0, 1, 2)
        filters.setColumnStretch(0, 1)
        filters.setColumnStretch(1, 1)
        layout.addLayout(filters)

        self.state_label = QLabel("尚未生成")
        self.state_label.setObjectName("finalReviewState")
        self.state_label.setWordWrap(True)
        layout.addWidget(self.state_label)
        status_row = QHBoxLayout()
        status_row.addStretch(1)
        self.generate_button = QPushButton("重新计算")
        self.generate_button.setObjectName("secondaryButton")
        self.generate_button.clicked.connect(self._generate)
        status_row.addWidget(self.generate_button)
        self.lock_button = QPushButton("锁定结果")
        self.lock_button.setObjectName("primaryButton")
        self.lock_button.clicked.connect(self._toggle_lock)
        status_row.addWidget(self.lock_button)
        layout.addLayout(status_row)

        self.summary_label = QLabel("A 0 人 · B 0 人 · C 0 人")
        self.summary_label.setObjectName("finalReviewSummary")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.table = QTableWidget(0, len(self.headers))
        self.table.setObjectName("finalReviewTable")
        self.table.setHorizontalHeaderLabels(self.headers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        configure_resizable_table(self.table)
        self.table.horizontalHeader().setStretchLastSection(True)
        for column, width in enumerate((100, 110, 92, 82, 82, 104, 96, 96, 82, 96)):
            self.table.setColumnWidth(column, width)
        layout.addWidget(self.table, 1)

        self.hint_label = QLabel("黄色行表示六学期数据不完整；N/A 不折算，累计分按已有学期计算。")
        self.hint_label.setObjectName("mutedLabel")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

    def _load_filters(self) -> None:
        self.class_box.blockSignals(True)
        self.class_box.clear()
        for class_group in self.controller.list_classes():
            self.class_box.addItem(class_group["name"], class_group["id"])
        selected_index = self.class_box.findData(self.initial_class_id)
        self.class_box.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        self.class_box.blockSignals(False)

        self.dimension_box.blockSignals(True)
        self.dimension_box.clear()
        for dimension in self.controller.list_dimensions():
            self.dimension_box.addItem(dimension["name"], dimension["name"])
        self.dimension_box.blockSignals(False)

    def refresh(self) -> None:
        class_id = self.class_box.currentData()
        dimension = self.dimension_box.currentData()
        if class_id is None or not dimension:
            self._show_empty_state("请先创建班级并设置评价维度。")
            return
        scroll_value = self.table.verticalScrollBar().value()
        try:
            data = self.controller.get_final_review(
                int(class_id),
                str(dimension),
                self.search_input.text(),
            )
        except QualityDataError as exc:
            self._show_empty_state(str(exc))
            return
        self.review_data = data
        self._update_state(data)
        self._populate_table(data)
        self.table.verticalScrollBar().setValue(scroll_value)

    def _update_state(self, data: dict) -> None:
        if data["is_locked"]:
            state_text = f"已锁定 · {data['locked_at']}"
        elif data["generated"]:
            state_text = f"待教师复核 · 计算于 {data['generated_at']}"
        else:
            state_text = f"九下名单 {data['candidate_count']} 人 · 尚未生成最终等级"
        self.state_label.setText(state_text)
        self.generate_button.setEnabled(not data["is_locked"] and data["candidate_count"] > 0)
        self.lock_button.setEnabled(data["generated"])
        self.lock_button.setText("解锁结果" if data["is_locked"] else "锁定结果")
        self.lock_button.setObjectName("secondaryButton" if data["is_locked"] else "primaryButton")
        self.lock_button.style().unpolish(self.lock_button)
        self.lock_button.style().polish(self.lock_button)

        count = data["candidate_count"]
        parts = []
        for level in FINAL_LEVELS:
            level_count = data["level_counts"].get(level, 0)
            percentage = level_count / count * 100 if count else 0
            parts.append(f"{level} {level_count} 人（{percentage:.1f}%）")
        parts.append(f"人工调整 {data['manual_count']} 项")
        parts.append(f"数据不完整 {data['incomplete_count']} 人")
        self.summary_label.setText("   ".join(parts))

    def _populate_table(self, data: dict) -> None:
        rows = data["rows"]
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row["name"],
                row["student_no"],
                formatted_score(row["score"]),
                row["rank"],
                row["automatic_level"],
                "",
                f"{row['available_terms']}/6" if not row["contains_na"] else f"{row['available_terms']}/6 · N/A",
                formatted_score(row["total_score"]),
                row["total_rank"] or "",
                "已调整" if row["is_manually_adjusted"] else "系统结果",
            ]
            for column, value in enumerate(values):
                if column == 5:
                    continue
                item = QTableWidgetItem(str(value))
                if column in {2, 3, 4, 6, 7, 8, 9}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if row["contains_na"]:
                    item.setBackground(QColor("#fff6df"))
                    item.setForeground(QColor("#7a5200"))
                self.table.setItem(row_index, column, item)

            level_box = QComboBox()
            for level in FINAL_LEVELS:
                level_box.addItem(level, level)
            level_box.setCurrentIndex(level_box.findData(row["final_level"]))
            level_box.setEnabled(not data["is_locked"])
            if row["contains_na"]:
                level_box.setStyleSheet("QComboBox { background: #fff6df; color: #7a5200; }")
            level_box.currentIndexChanged.connect(
                lambda _index, result_id=row["result_id"], box=level_box: self._change_level(
                    result_id,
                    str(box.currentData()),
                )
            )
            self.table.setCellWidget(row_index, 5, level_box)

    def _generate(self) -> None:
        class_id = self.class_box.currentData()
        if class_id is None:
            return
        answer = QMessageBox.question(
            self,
            "重新计算最终等级",
            "将按九下名单重新计算五个维度的累计分、班级排名和 ABC 等级。已有人工调整会保留。",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.controller.generate_final_results(int(class_id))
        except QualityDataError as exc:
            QMessageBox.warning(self, "无法计算", str(exc))
            return
        self.refresh()

    def _change_level(self, result_id: int, level: str) -> None:
        try:
            self.controller.update_final_level(result_id, level)
        except QualityDataError as exc:
            QMessageBox.warning(self, "无法调整", str(exc))
        self.refresh()

    def _toggle_lock(self) -> None:
        if not self.review_data:
            return
        locked = bool(self.review_data["is_locked"])
        action = "解锁" if locked else "锁定"
        message = (
            "解锁后可以重新计算或调整最终等级。"
            if locked
            else "锁定后，本班六学期原始评价和最终等级都不能修改，导出档案会标记为已锁定。"
        )
        answer = QMessageBox.question(self, f"{action}最终结果", message)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.controller.set_finalization_locked(int(self.review_data["class_id"]), not locked)
        except QualityDataError as exc:
            QMessageBox.warning(self, f"无法{action}", str(exc))
            return
        self.refresh()

    def _show_empty_state(self, message: str) -> None:
        self.review_data = None
        self.table.setRowCount(0)
        self.state_label.setText(message)
        self.summary_label.setText("A 0 人   B 0 人   C 0 人")
        self.generate_button.setEnabled(False)
        self.lock_button.setEnabled(False)
