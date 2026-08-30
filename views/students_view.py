from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from controllers.student_controller import StudentController
from utils.ui_layout import configure_resizable_table, restore_splitter, set_compact_columns
from views.class_dialog import ClassManagementDialog
from views.student_detail_pane import StudentDetailPane
from views.student_form_dialog import StudentFormDialog
from views.ui_components import EmptyState, scrollable_detail


class StudentTableModel(QAbstractTableModel):
    headers = ["ID", "姓名", "性别", "学号", "班级", "年级", "座号", "家长电话", "备注"]

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict[str, str]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.FontRole and index.column() == 1:
            font = QFont()
            font.setWeight(QFont.Weight.DemiBold)
            return font
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
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
        if row < 0 or row >= len(self.rows):
            return None
        return int(self.rows[row]["_id"])


class StudentsView(QWidget):
    """The student data center: list, filter result, and student archive pane."""

    classes_changed = Signal()
    filters_clear_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.controller = StudentController()
        self.model = StudentTableModel()
        self.search_text = ""
        self.class_id: int | None = None
        self._empty_action_mode = ""
        self._compact_mode = False
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        summary = QHBoxLayout()
        self.count_label = QLabel("学生 0 人")
        self.count_label.setObjectName("summaryText")
        self.class_label = QLabel("班级 0 个")
        self.class_label.setObjectName("summaryText")
        summary.addWidget(self.count_label)
        summary.addWidget(self.class_label)
        summary.addStretch(1)
        layout.addLayout(summary)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("studentsSplitter")
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
        self.table.setColumnWidth(0, 58)
        self.table.setColumnWidth(1, 82)
        self.table.setColumnWidth(2, 56)
        self.table.setColumnWidth(3, 96)
        self.table.setColumnWidth(4, 112)
        self.table.setColumnWidth(5, 78)
        self.table.setColumnWidth(6, 58)
        self.table.setColumnWidth(7, 142)
        self.table.clicked.connect(self._show_selected_student)
        self.table_stack = QStackedWidget()
        self.table_stack.setObjectName("dataStateStack")
        self.table_stack.addWidget(self.table)
        self.empty_state = EmptyState(
            icon_name="users-round",
            action=self._handle_empty_action,
        )
        self.table_stack.addWidget(self.empty_state)
        table_layout.addWidget(self.table_stack)
        self.main_splitter.addWidget(table_frame)

        self.detail_pane = StudentDetailPane(self.controller)
        self.detail_pane.data_changed.connect(self._reload_after_detail_change)
        self.detail_scroll = scrollable_detail(self.detail_pane, name="studentDetailScroll")
        self.main_splitter.addWidget(self.detail_scroll)
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 2)
        restore_splitter(self.main_splitter, "students_main", [720, 420])
        layout.addWidget(self.main_splitter, 1)

    def set_search_text(self, text: str) -> None:
        self.search_text = text
        self.reload()

    def set_class_filter(self, class_id: int | None) -> None:
        self.class_id = class_id
        self.reload()

    def reload(self) -> None:
        rows = self.controller.search_students(self.search_text, self.class_id)
        self.model.set_rows(rows)
        self.count_label.setText(f"学生 {len(rows)} 人")
        class_count = self.controller.count_classes()
        self.class_label.setText(f"班级 {class_count} 个")
        self.detail_pane.clear()
        if rows:
            self.table_stack.setCurrentWidget(self.table)
            return
        self.table_stack.setCurrentWidget(self.empty_state)
        if class_count == 0:
            self._empty_action_mode = "classes"
            self.empty_state.set_content(
                "先建立第一个班级",
                "班级是学生档案、成绩和评价的共同范围，建立后即可新增或导入学生。",
                "管理班级",
            )
        elif self.search_text.strip() or self.class_id is not None:
            self._empty_action_mode = "filters"
            self.empty_state.set_content(
                "没有匹配的学生",
                "请检查姓名、学号、家长电话或当前班级筛选条件。",
                "清除筛选",
            )
        else:
            self._empty_action_mode = "student"
            self.empty_state.set_content(
                "班级中还没有学生",
                "可以逐个新增学生，也可以使用统一 Excel 模板批量导入。",
                "新增学生",
            )

    def _reload_after_detail_change(self) -> None:
        selected_id = self.detail_pane.student_id
        self.reload()
        if selected_id is not None:
            self._select_student(selected_id)

    def open_add_student(self) -> None:
        if not self.controller.list_classes():
            QMessageBox.information(self, "请先创建班级", "请先在“管理班级”中创建学生所属班级。")
            return
        dialog = StudentFormDialog(self.controller, parent=self)
        if dialog.exec() and dialog.saved_student_id:
            self.reload()
            self._select_student(dialog.saved_student_id)

    def open_class_manager(self) -> None:
        dialog = ClassManagementDialog(self.controller, self)
        dialog.exec()
        self.reload()
        self.classes_changed.emit()

    def _show_selected_student(self, index: QModelIndex) -> None:
        student_id = self.model.student_id_at(index.row())
        if student_id is not None:
            self.detail_pane.load_student(student_id)

    def _select_student(self, student_id: int) -> None:
        for row_index in range(self.model.rowCount()):
            if self.model.student_id_at(row_index) == student_id:
                index = self.model.index(row_index, 0)
                self.table.setCurrentIndex(index)
                self._show_selected_student(index)
                return

    def _handle_empty_action(self) -> None:
        if self._empty_action_mode == "classes":
            self.open_class_manager()
        elif self._empty_action_mode == "filters":
            self.filters_clear_requested.emit()
        elif self._empty_action_mode == "student":
            self.open_add_student()

    def set_compact_mode(self, compact: bool) -> None:
        if compact == self._compact_mode:
            return
        self._compact_mode = compact
        self.main_splitter.setOrientation(
            Qt.Orientation.Vertical if compact else Qt.Orientation.Horizontal
        )
        set_compact_columns(self.table, (0, 2, 5, 6, 7, 8), compact)
        if compact:
            self.table.setColumnWidth(1, 92)
            self.table.setColumnWidth(3, 104)
            self.table.setColumnWidth(4, 112)
            self.main_splitter.setSizes([300, 360])
        else:
            self.main_splitter.setSizes([720, 420])
