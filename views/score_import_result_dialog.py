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

from controllers.score_controller import ScoreImportResult
from utils.ui_layout import configure_resizable_table, configure_responsive_dialog


class ScoreImportResultDialog(QDialog):
    def __init__(self, result: ScoreImportResult, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("成绩 Excel 导入结果")
        self._build_ui(result)
        configure_responsive_dialog(self, 700, 410, minimum_height=340)

    def _build_ui(self, result: ScoreImportResult) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        summary = QLabel(
            f"文件：{result.file_name}\n"
            f"考试：{result.exam_label}\n"
            f"识别学科：{'、'.join(result.subjects)}\n"
            f"读取 {result.total_rows} 行，导入学生 {result.imported_students} 人，"
            f"自动建档 {result.created_students} 人，新增成绩 {result.written_scores} 条，"
            f"更新成绩 {result.updated_scores} 条。"
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        issue_title = QLabel(f"提示与跳过项（{len(result.issues)}）")
        issue_title.setObjectName("sectionTitle")
        layout.addWidget(issue_title)
        table = QTableWidget(len(result.issues), 3)
        table.setHorizontalHeaderLabels(["行号", "学生", "说明"])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.verticalHeader().setVisible(False)
        configure_resizable_table(table)
        table.setColumnWidth(0, 76)
        table.setColumnWidth(1, 120)
        for row_index, issue in enumerate(result.issues):
            for column, value in enumerate((str(issue.row_number), issue.student_name, issue.message)):
                table.setItem(row_index, column, QTableWidgetItem(value))
        layout.addWidget(table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
