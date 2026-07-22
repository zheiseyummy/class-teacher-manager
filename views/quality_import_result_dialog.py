from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controllers.quality_controller import QualityImportResult
from utils.quality_scoring import RULE_BY_KEY
from utils.ui_layout import configure_resizable_table


class QualityImportResultDialog(QDialog):
    def __init__(self, result: QualityImportResult, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("综合素质 Excel 导入结果")
        self.setMinimumSize(720, 420)
        self._build_ui(result)

    def _build_ui(self, result: QualityImportResult) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)

        summary = QLabel(
            f"文件：{result.file_name}\n"
            f"导入班级：{result.target_class_name}{'（已自动创建）' if result.created_class else ''}\n"
            f"读取评价行 {result.total_rows} 条，导入学生 {result.matched_students} 人，"
            f"自动建立学生档案 {result.created_students} 人，"
            f"写入学期评价 {result.updated_evaluations} 份，含 N/A 的学期评价 {result.na_evaluations} 份。"
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        mapped_sheets = "；".join(
            f"{RULE_BY_KEY[key].label}：{sheet_name}"
            for key, sheet_name in result.semester_sheets.items()
        )
        sheet_label = QLabel(f"已识别工作表：{mapped_sheets}")
        sheet_label.setObjectName("mutedLabel")
        sheet_label.setWordWrap(True)
        layout.addWidget(sheet_label)

        issue_title = QLabel(f"提示与跳过项（{len(result.issues)}）")
        issue_title.setObjectName("sectionTitle")
        layout.addWidget(issue_title)
        self.table = QTableWidget(len(result.issues), 4)
        self.table.setHorizontalHeaderLabels(["工作表", "行号", "学生", "说明"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.verticalHeader().setVisible(False)
        configure_resizable_table(self.table)
        self.table.setColumnWidth(0, 96)
        self.table.setColumnWidth(1, 68)
        self.table.setColumnWidth(2, 100)
        for row_index, issue in enumerate(result.issues):
            values = [issue.sheet_name, str(issue.row_number), issue.student_name or "-", issue.message]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))
        layout.addWidget(self.table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
