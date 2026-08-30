from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controllers.student_controller import StudentImportResult
from utils.ui_layout import configure_resizable_table, configure_responsive_dialog


class ImportResultDialog(QDialog):
    def __init__(self, result: StudentImportResult, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Excel 导入结果")
        self._build_ui(result)
        configure_responsive_dialog(self, 760, 500, minimum_height=360)

    def _build_ui(self, result: StudentImportResult) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        title = QLabel(result.file_name)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        summary = QHBoxLayout()
        for text in [
            f"读取 {result.total_rows} 行",
            f"成功 {result.success_rows} 行",
            f"跳过 {result.skipped_rows} 行",
            f"失败 {result.failed_rows} 行",
        ]:
            label = QLabel(text)
            label.setObjectName("summaryText")
            summary.addWidget(label)
        summary.addStretch(1)
        layout.addLayout(summary)

        self.table = QTableWidget(len(result.issues), 4)
        self.table.setHorizontalHeaderLabels(["状态", "Excel 行", "数据", "说明"])
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        configure_resizable_table(self.table)
        for row_index, issue in enumerate(result.issues):
            values = [
                "已跳过" if issue.skipped else "失败",
                str(issue.row_number),
                issue.raw_value,
                issue.message,
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))
        layout.addWidget(self.table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("关闭")
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
