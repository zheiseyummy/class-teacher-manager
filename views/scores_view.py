from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QMenu,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from config import SCORE_IMPORT_TEMPLATE
from controllers.score_controller import ScoreController, ScoreDataError
from utils.score_excel_import import ensure_score_import_template
from utils.ui_icons import lucide_icon
from utils.ui_layout import configure_resizable_table, restore_splitter, set_compact_columns
from views.score_import_dialog import ScoreImportDialog
from views.score_import_result_dialog import ScoreImportResultDialog
from views.ui_components import EmptyState, scrollable_detail


class ScoresView(QWidget):
    """Exam import, ranking, and longitudinal subject analysis workspace."""

    def __init__(self) -> None:
        super().__init__()
        self.controller = ScoreController()
        self.overview_rows: list[dict[str, Any]] = []
        self.current_exam_id: int | None = None
        self._compact_mode = False
        self._build_ui()
        self._refresh_filters()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("moduleToolbar")
        self.toolbar_layout = QGridLayout(toolbar_frame)
        self.toolbar_layout.setContentsMargins(12, 8, 12, 8)
        self.toolbar_layout.setHorizontalSpacing(8)
        self.toolbar_context = QLabel("分析范围")
        self.toolbar_context.setObjectName("toolbarContext")
        self.toolbar_layout.addWidget(self.toolbar_context, 0, 0)
        self.toolbar_layout.setColumnStretch(0, 1)
        self.class_filter = QComboBox()
        self.class_filter.setObjectName("classFilter")
        self.class_filter.setMinimumWidth(150)
        self.class_filter.currentIndexChanged.connect(self.reload)
        self.toolbar_layout.addWidget(self.class_filter, 0, 1)
        self.template_button = QPushButton("成绩模板")
        self.template_button.setIcon(lucide_icon("file-down"))
        self.template_button.clicked.connect(self._open_template)
        self.toolbar_layout.addWidget(self.template_button, 0, 2)
        self.import_button = QPushButton("导入成绩")
        self.import_button.setObjectName("primaryButton")
        self.import_button.setIcon(
            lucide_icon("file-up", color="#FFFFFF", active_color="#FFFFFF")
        )
        self.import_button.clicked.connect(self._import_scores)
        self.toolbar_layout.addWidget(self.import_button, 0, 3)
        self.more_button = QToolButton()
        self.more_button.setObjectName("moreButton")
        self.more_button.setText("更多")
        self.more_button.setIcon(lucide_icon("clipboard-check"))
        self.more_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        more_menu = QMenu(self.more_button)
        more_menu.addAction(lucide_icon("file-down"), "打开成绩模板", self._open_template)
        self.more_button.setMenu(more_menu)
        self.more_button.setVisible(False)
        self.toolbar_layout.addWidget(self.more_button, 0, 4)
        layout.addWidget(toolbar_frame)

        exam_frame = QFrame()
        exam_frame.setObjectName("filterBar")
        self.exam_layout = QGridLayout(exam_frame)
        self.exam_layout.setContentsMargins(12, 9, 12, 9)
        self.exam_layout.setHorizontalSpacing(10)
        self.exam_layout.setVerticalSpacing(6)
        self.exam_label = QLabel("考试批次")
        self.exam_label.setObjectName("toolbarContext")
        self.exam_layout.addWidget(self.exam_label, 0, 0)
        self.exam_box = QComboBox()
        self.exam_box.setMinimumWidth(360)
        self.exam_box.currentIndexChanged.connect(self._on_exam_changed)
        self.exam_layout.addWidget(self.exam_box, 0, 1)
        self.exam_layout.setColumnStretch(2, 1)
        self.student_count_label = QLabel("学生 0 人")
        self.student_count_label.setObjectName("summaryText")
        self.average_label = QLabel("班均分 -")
        self.average_label.setObjectName("summaryText")
        self.highest_label = QLabel("最高分 -")
        self.highest_label.setObjectName("summaryText")
        self.exam_layout.addWidget(self.student_count_label, 0, 3)
        self.exam_layout.addWidget(self.average_label, 0, 4)
        self.exam_layout.addWidget(self.highest_label, 0, 5)
        layout.addWidget(exam_frame)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_overview_tab(), "成绩总览")
        self.tabs.addTab(self._build_subject_tab(), "学科分析")
        self.tabs.addTab(self._build_subject_trend_tab(), "学科趋势")
        self.tabs.addTab(self._build_class_trend_tab(), "班级趋势")
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("dataStateStack")
        self.content_stack.addWidget(self.tabs)
        self.empty_state = EmptyState(
            icon_name="chart-no-axes-column-increasing",
            action=self._import_scores,
        )
        self.empty_state.set_content(
            "还没有考试成绩",
            "导入一份包含学号和实际考试科目的 Excel，即可开始班级、年级和学生趋势分析。",
            "导入成绩",
        )
        self.content_stack.addWidget(self.empty_state)
        layout.addWidget(self.content_stack, 1)

    def _build_overview_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        self.overview_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.overview_splitter.setObjectName("scoresSplitter")
        self.overview_splitter.setChildrenCollapsible(False)

        table_frame = QFrame()
        table_frame.setObjectName("tablePane")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)
        self.overview_table = QTableWidget(0, 0)
        self.overview_table.setObjectName("studentTable")
        self.overview_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.overview_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.overview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.overview_table.verticalHeader().setVisible(False)
        self.overview_table.setAlternatingRowColors(True)
        configure_resizable_table(self.overview_table)
        self.overview_table.itemSelectionChanged.connect(self._load_selected_student)
        table_layout.addWidget(self.overview_table)
        self.overview_splitter.addWidget(table_frame)

        detail = QFrame()
        detail.setObjectName("scorePane")
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(20, 18, 20, 18)
        detail_layout.setSpacing(12)
        self.student_name_label = QLabel("选择学生")
        self.student_name_label.setObjectName("detailName")
        self.student_class_label = QLabel("")
        self.student_class_label.setObjectName("mutedLabel")
        self.student_rank_label = QLabel("班级排名 -  年级排名 -")
        self.student_rank_label.setObjectName("qualityScore")
        detail_layout.addWidget(self.student_name_label)
        detail_layout.addWidget(self.student_class_label)
        detail_layout.addWidget(self.student_rank_label)

        self.detail_splitter = QSplitter(Qt.Orientation.Vertical)
        self.detail_splitter.setObjectName("scoreDetailSplitter")
        self.detail_splitter.setChildrenCollapsible(False)
        trend_panel = QWidget()
        trend_layout = QVBoxLayout(trend_panel)
        trend_layout.setContentsMargins(0, 0, 0, 0)
        trend_layout.setSpacing(8)
        trend_title = QLabel("历次排名趋势")
        trend_title.setObjectName("sectionTitle")
        trend_layout.addWidget(trend_title)
        self.student_trend_table = self._read_only_table(["考试", "总分", "班级排名", "年级排名", "变化"])
        trend_layout.addWidget(self.student_trend_table, 1)
        self.detail_splitter.addWidget(trend_panel)

        subject_panel = QWidget()
        subject_layout = QVBoxLayout(subject_panel)
        subject_layout.setContentsMargins(0, 0, 0, 0)
        subject_layout.setSpacing(8)
        subject_title = QLabel("本次学科比较")
        subject_title.setObjectName("sectionTitle")
        subject_layout.addWidget(subject_title)
        self.student_subject_table = self._read_only_table(["科目", "本次", "班均", "差值", "判断"])
        subject_layout.addWidget(self.student_subject_table, 1)
        self.detail_splitter.addWidget(subject_panel)
        restore_splitter(self.detail_splitter, "scores_detail", [210, 210])
        detail_layout.addWidget(self.detail_splitter, 1)
        self.detail_scroll = scrollable_detail(detail, name="scoreDetailScroll")
        self.overview_splitter.addWidget(self.detail_scroll)
        self.overview_splitter.setStretchFactor(0, 3)
        self.overview_splitter.setStretchFactor(1, 2)
        restore_splitter(self.overview_splitter, "scores_main", [760, 430])
        layout.addWidget(self.overview_splitter, 1)
        return page

    def _build_subject_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        self.subject_table = self._read_only_table(["学科", "参考人数", "平均分", "最高分", "最低分"])
        layout.addWidget(self.subject_table)
        return page

    def _build_class_trend_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        self.class_trend_table = self._read_only_table(["考试", "班均分", "年级均分", "班级排名", "参与班级"])
        layout.addWidget(self.class_trend_table)
        return page

    def _build_subject_trend_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        self.subject_trend_table = self._read_only_table(["考试", "学科", "平均分", "参考人数", "较上次"])
        layout.addWidget(self.subject_trend_table)
        return page

    @staticmethod
    def _read_only_table(headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        configure_resizable_table(table)
        return table

    def _refresh_filters(self, selected_exam_id: int | None = None) -> None:
        selected_class_id = self.class_filter.currentData()
        self.class_filter.blockSignals(True)
        self.class_filter.clear()
        self.class_filter.addItem("全部班级", None)
        for class_group in self.controller.list_classes():
            self.class_filter.addItem(class_group["name"], class_group["id"])
        class_index = self.class_filter.findData(selected_class_id)
        self.class_filter.setCurrentIndex(class_index if class_index >= 0 else 0)
        self.class_filter.blockSignals(False)

        selected_exam_id = selected_exam_id or self.exam_box.currentData()
        self.exam_box.blockSignals(True)
        self.exam_box.clear()
        for exam in self.controller.list_exams():
            self.exam_box.addItem(exam["label"], exam["id"])
        exam_index = self.exam_box.findData(selected_exam_id)
        self.exam_box.setCurrentIndex(exam_index if exam_index >= 0 else 0)
        self.exam_box.blockSignals(False)

    def _on_exam_changed(self) -> None:
        self.current_exam_id = self.exam_box.currentData()
        self.reload()

    def reload(self) -> None:
        self.current_exam_id = self.exam_box.currentData()
        if self.current_exam_id is None:
            self._clear_tables()
            return
        try:
            dashboard = self.controller.get_exam_dashboard(int(self.current_exam_id), self.class_filter.currentData())
        except ScoreDataError as exc:
            QMessageBox.warning(self, "无法读取成绩", str(exc))
            self._clear_tables()
            return
        self.overview_rows = dashboard["rows"]
        self.content_stack.setCurrentWidget(self.tabs)
        self._populate_overview(dashboard["subjects"], dashboard["rows"])
        self._populate_subjects(dashboard["subject_stats"])
        self._populate_class_trends()
        self._populate_subject_trends()
        summary = dashboard["summary"]
        self.student_count_label.setText(f"学生 {summary['student_count']} 人")
        average_title = "班均分" if self.class_filter.currentData() is not None else "平均分"
        self.average_label.setText(f"{average_title} {self._number(summary['average_total'])}")
        self.highest_label.setText(f"最高分 {self._number(summary['highest_total'])}")
        self._clear_student_detail()

    def _populate_overview(self, subjects: list[str], rows: list[dict[str, Any]]) -> None:
        headers = ["姓名", "学号", "班级", "总分", "班级排名", "年级排名", *subjects]
        self.overview_table.blockSignals(True)
        self.overview_table.setColumnCount(len(headers))
        self.overview_table.setHorizontalHeaderLabels(headers)
        self.overview_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, header in enumerate(headers):
                self.overview_table.setItem(row_index, column_index, QTableWidgetItem(self._number(row.get(header))))
        self.overview_table.setColumnWidth(0, 80)
        self.overview_table.setColumnWidth(1, 92)
        self.overview_table.setColumnWidth(2, 104)
        self.overview_table.setColumnWidth(3, 76)
        self.overview_table.setColumnWidth(4, 84)
        self.overview_table.setColumnWidth(5, 84)
        self.overview_table.blockSignals(False)
        set_compact_columns(
            self.overview_table,
            (1, 2, *range(6, len(headers))),
            self._compact_mode,
        )

    def _populate_subjects(self, rows: list[dict[str, Any]]) -> None:
        self.subject_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [row["subject"], row["count"], row["average"], row["highest"], row["lowest"]]
            for column_index, value in enumerate(values):
                self.subject_table.setItem(row_index, column_index, QTableWidgetItem(self._number(value)))

    def _populate_class_trends(self) -> None:
        rows = self.controller.get_class_trends(self.class_filter.currentData())
        self.class_trend_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [row["exam"], row["class_average"], row["grade_average"], row["class_rank"], row["class_count"]]
            for column_index, value in enumerate(values):
                self.class_trend_table.setItem(row_index, column_index, QTableWidgetItem(self._number(value)))

    def _populate_subject_trends(self) -> None:
        rows = self.controller.get_subject_trends(self.class_filter.currentData())
        self.subject_trend_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [row["exam"], row["subject"], row["average"], row["count"], row["change"]]
            for column_index, value in enumerate(values):
                self.subject_trend_table.setItem(row_index, column_index, QTableWidgetItem(self._number(value)))

    def _load_selected_student(self) -> None:
        selected = self.overview_table.selectionModel().selectedRows()
        if not selected or self.current_exam_id is None:
            return
        row = selected[0].row()
        if not 0 <= row < len(self.overview_rows):
            return
        student_id = self.overview_rows[row]["_id"]
        try:
            data = self.controller.get_student_analysis(student_id, int(self.current_exam_id))
        except ScoreDataError as exc:
            QMessageBox.warning(self, "无法读取学生分析", str(exc))
            return
        self.student_name_label.setText(data["name"])
        self.student_class_label.setText(data["class_name"])
        self.student_rank_label.setText(
            f"总分 {self._number(data['current_total'])}  班级排名 {data['current_class_rank']}  年级排名 {data['current_grade_rank']}"
        )
        self._populate_table(
            self.student_trend_table,
            [[row["exam"], row["total"], row["class_rank"], row["grade_rank"], row["change"]] for row in data["trend_rows"]],
        )
        self._populate_table(
            self.student_subject_table,
            [[row["subject"], row["score"], row["class_average"], row["difference"], row["status"]] for row in data["subject_rows"]],
        )

    def _import_scores(self) -> None:
        dialog = ScoreImportDialog(self.controller.list_classes(), self.class_filter.currentData(), self)
        if not dialog.exec() or dialog.exam_data is None:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择本次考试成绩 Excel",
            str(Path.home() / "Desktop"),
            "Excel 文件 (*.xlsx *.xlsm)",
        )
        if not file_path:
            return
        try:
            result = self.controller.import_scores_from_excel(file_path, dialog.exam_data, self.class_filter.currentData())
        except ScoreDataError as exc:
            QMessageBox.warning(self, "导入失败", str(exc))
            return
        self._refresh_filters(result.exam_id)
        if len(result.class_names) == 1:
            class_index = self.class_filter.findText(result.class_names[0])
            if class_index >= 0:
                self.class_filter.setCurrentIndex(class_index)
        self.reload()
        ScoreImportResultDialog(result, self).exec()

    def _open_template(self) -> None:
        ensure_score_import_template(SCORE_IMPORT_TEMPLATE)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(SCORE_IMPORT_TEMPLATE))):
            QMessageBox.information(self, "成绩模板", f"模板已生成：\n{SCORE_IMPORT_TEMPLATE}")

    def _clear_tables(self) -> None:
        self.overview_rows = []
        self.overview_table.setRowCount(0)
        self.subject_table.setRowCount(0)
        self.subject_trend_table.setRowCount(0)
        self.class_trend_table.setRowCount(0)
        self.student_count_label.setText("学生 0 人")
        self.average_label.setText("班均分 -")
        self.highest_label.setText("最高分 -")
        self._clear_student_detail()
        self.content_stack.setCurrentWidget(self.empty_state)

    def _clear_student_detail(self) -> None:
        self.student_name_label.setText("选择学生")
        self.student_class_label.setText("")
        self.student_rank_label.setText("班级排名 -  年级排名 -")
        self.student_trend_table.setRowCount(0)
        self.student_subject_table.setRowCount(0)

    def _populate_table(self, table: QTableWidget, rows: list[list[Any]]) -> None:
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                table.setItem(row_index, column_index, QTableWidgetItem(self._number(value)))

    @staticmethod
    def _number(value: Any) -> str:
        if value is None:
            return "-"
        if isinstance(value, float):
            return f"{value:.2f}".rstrip("0").rstrip(".")
        return str(value)

    def set_compact_mode(self, compact: bool) -> None:
        if compact == self._compact_mode:
            return
        self._compact_mode = compact
        self.toolbar_context.setVisible(not compact)
        self.template_button.setVisible(not compact)
        self.more_button.setVisible(compact)
        self.class_filter.setMinimumWidth(110 if compact else 150)

        exam_widgets = (
            self.exam_label,
            self.exam_box,
            self.student_count_label,
            self.average_label,
            self.highest_label,
        )
        for widget in exam_widgets:
            self.exam_layout.removeWidget(widget)
        if compact:
            self.exam_label.setVisible(False)
            self.exam_box.setMinimumWidth(0)
            self.exam_layout.addWidget(self.exam_box, 0, 0, 1, 3)
            self.exam_layout.addWidget(self.student_count_label, 1, 0)
            self.exam_layout.addWidget(self.average_label, 1, 1)
            self.exam_layout.addWidget(self.highest_label, 1, 2)
        else:
            self.exam_label.setVisible(True)
            self.exam_box.setMinimumWidth(360)
            self.exam_layout.addWidget(self.exam_label, 0, 0)
            self.exam_layout.addWidget(self.exam_box, 0, 1)
            self.exam_layout.addWidget(self.student_count_label, 0, 3)
            self.exam_layout.addWidget(self.average_label, 0, 4)
            self.exam_layout.addWidget(self.highest_label, 0, 5)

        self.overview_splitter.setOrientation(
            Qt.Orientation.Vertical if compact else Qt.Orientation.Horizontal
        )
        if self.overview_table.columnCount():
            set_compact_columns(
                self.overview_table,
                (1, 2, *range(6, self.overview_table.columnCount())),
                compact,
            )
        self.overview_splitter.setSizes([300, 430] if compact else [760, 430])
