from __future__ import annotations

from datetime import date, datetime
from typing import Any

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from controllers.planner_controller import PlannerController, PlannerDataError
from controllers.score_controller import ScoreController, ScoreDataError
from utils.ui_icons import lucide_icon
from utils.ui_layout import restore_splitter


class MetricCard(QFrame):
    """Compact, fixed-height dashboard metric fed by real controller data."""

    def __init__(
        self,
        label: str,
        icon_name: str,
        tone: str,
        icon_color: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setProperty("tone", tone)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(92)
        self.setMaximumHeight(98)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(11)

        icon_label = QLabel()
        icon_label.setObjectName("metricIcon")
        icon_label.setProperty("tone", tone)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(42, 42)
        icon = lucide_icon(
            icon_name,
            color=icon_color,
            active_color=icon_color,
            size=20,
        )
        icon_label.setPixmap(icon.pixmap(QSize(20, 20)))
        layout.addWidget(icon_label)

        body = QVBoxLayout()
        body.setSpacing(1)
        metric_label = QLabel(label)
        metric_label.setObjectName("dashboardMetricLabel")
        body.addWidget(metric_label)
        self.value_label = QLabel("--")
        self.value_label.setObjectName("dashboardMetricValue")
        body.addWidget(self.value_label)
        self.note_label = QLabel("等待数据")
        self.note_label.setObjectName("dashboardMetricNote")
        body.addWidget(self.note_label)
        layout.addLayout(body, 1)

    def set_value(self, value: str, note: str) -> None:
        self.value_label.setText(value)
        self.note_label.setText(note)
        self.setToolTip(f"{self.value_label.text()} · {note}")


class TodayWorkbenchView(QWidget):
    """Daily class desk with real metrics, activities, and recent score changes."""

    navigate_requested = Signal(int)
    planner_action_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = PlannerController()
        self.score_controller = ScoreController()
        self._reference_date: date | None = None
        self._classes: list[dict[str, Any]] = []
        self._build_header_controls()
        self._build_ui()
        self.refresh_classes()

    def _build_header_controls(self) -> None:
        self.header_controls = QFrame()
        self.header_controls.setObjectName("workbenchHeaderControls")
        header_layout = QHBoxLayout(self.header_controls)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        self.class_box = QComboBox()
        self.class_box.setMinimumWidth(168)
        self.class_box.currentIndexChanged.connect(self.refresh)
        header_layout.addWidget(self.class_box)

        self.date_display = QFrame()
        self.date_display.setObjectName("workbenchDateDisplay")
        self.date_display.setMinimumWidth(142)
        date_layout = QHBoxLayout(self.date_display)
        date_layout.setContentsMargins(11, 0, 11, 0)
        date_layout.setSpacing(7)
        date_icon = QLabel()
        date_icon.setPixmap(
            lucide_icon(
                "calendar-days",
                color="#718096",
                active_color="#718096",
                size=16,
            ).pixmap(QSize(16, 16))
        )
        date_icon.setFixedSize(16, 16)
        date_layout.addWidget(date_icon)
        self.date_label = QLabel()
        self.date_label.setObjectName("workbenchDateLabel")
        date_layout.addWidget(self.date_label, 1)
        header_layout.addWidget(self.date_display)

        self.refresh_button = QPushButton()
        self.refresh_button.setObjectName("iconButton")
        self.refresh_button.setToolTip("刷新工作台")
        self.refresh_button.setAccessibleName("刷新工作台")
        self.refresh_button.setFixedWidth(38)
        self.refresh_button.setIcon(lucide_icon("refresh-cw"))
        self.refresh_button.clicked.connect(self.refresh)
        header_layout.addWidget(self.refresh_button)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        metric_grid = QGridLayout()
        metric_grid.setContentsMargins(0, 0, 0, 0)
        metric_grid.setHorizontalSpacing(10)
        metric_grid.setVerticalSpacing(10)
        self.metric_cards: dict[str, MetricCard] = {}
        metric_definitions = (
            (
                "student_count",
                "在班学生",
                "users-round",
                "blue",
                "#2563EB",
            ),
            (
                "course_count",
                "今日课程",
                "book-open-check",
                "green",
                "#16966A",
            ),
            (
                "attendance_count",
                "考勤记录",
                "user-check",
                "purple",
                "#7C4DCC",
            ),
            (
                "event_count",
                "今日日程",
                "clipboard-check",
                "orange",
                "#D88913",
            ),
            (
                "moral_count",
                "德育记录",
                "award",
                "red",
                "#DB515D",
            ),
        )
        for column, (key, label, icon, tone, color) in enumerate(metric_definitions):
            card = MetricCard(label, icon, tone, color)
            metric_grid.addWidget(card, 0, column)
            metric_grid.setColumnStretch(column, 1)
            self.metric_cards[key] = card
        layout.addLayout(metric_grid)

        self.body_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.body_splitter.setObjectName("workbenchBodySplitter")
        self.body_splitter.setChildrenCollapsible(False)

        self.left_splitter = QSplitter(Qt.Orientation.Vertical)
        self.left_splitter.setChildrenCollapsible(False)
        self.left_splitter.addWidget(self._build_course_panel())
        self.left_splitter.addWidget(self._build_activity_panel())
        self.left_splitter.setStretchFactor(0, 1)
        self.left_splitter.setStretchFactor(1, 1)
        restore_splitter(self.left_splitter, "workbench_left_v2", [340, 300])

        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.setChildrenCollapsible(False)
        self.right_splitter.addWidget(self._build_event_panel())
        self.right_splitter.addWidget(self._build_score_fluctuation_panel())
        self.right_splitter.setStretchFactor(0, 1)
        self.right_splitter.setStretchFactor(1, 1)
        restore_splitter(self.right_splitter, "workbench_right_v3", [340, 300])

        self.body_splitter.addWidget(self.left_splitter)
        self.body_splitter.addWidget(self.right_splitter)
        self.body_splitter.setStretchFactor(0, 1)
        self.body_splitter.setStretchFactor(1, 1)
        restore_splitter(self.body_splitter, "workbench_columns_v2", [560, 560])
        layout.addWidget(self.body_splitter, 1)

    def _build_course_panel(self) -> QWidget:
        panel, layout, header = self._panel("今日课程")
        self.course_summary = QLabel()
        self.course_summary.setObjectName("summaryText")
        header.addWidget(self.course_summary)
        schedule_button = self._action_button(
            "查看课表",
            "arrow-right",
            lambda: self.planner_action_requested.emit("schedule"),
        )
        header.addWidget(schedule_button)
        self.course_list = self._dashboard_list()
        layout.addWidget(self.course_list, 1)
        return panel

    def _build_event_panel(self) -> QWidget:
        panel, layout, header = self._panel("今日待办与日程")
        self.event_summary = QLabel()
        self.event_summary.setObjectName("summaryText")
        header.addWidget(self.event_summary)
        event_button = self._action_button(
            "新建日程",
            "calendar-plus",
            lambda: self.planner_action_requested.emit("calendar_new"),
        )
        header.addWidget(event_button)
        self.event_list = self._dashboard_list()
        layout.addWidget(self.event_list, 1)
        return panel

    def _build_activity_panel(self) -> QWidget:
        panel, layout, header = self._panel("近期班级动态")
        attendance_button = self._action_button(
            "考勤",
            "calendar-clock",
            lambda: self.navigate_requested.emit(5),
        )
        header.addWidget(attendance_button)
        moral_button = self._action_button(
            "德育",
            "award",
            lambda: self.navigate_requested.emit(4),
        )
        header.addWidget(moral_button)
        self.activity_list = self._dashboard_list()
        layout.addWidget(self.activity_list, 1)
        return panel

    def _build_score_fluctuation_panel(self) -> QWidget:
        panel, layout, header = self._panel("近期考试波动学生")
        self.score_fluctuation_summary = QLabel("暂无可比考试")
        self.score_fluctuation_summary.setObjectName("scoreFluctuationSummary")
        header.addWidget(self.score_fluctuation_summary)
        score_button = self._action_button(
            "成绩分析",
            "chart-no-axes-column-increasing",
            lambda: self.navigate_requested.emit(3),
        )
        header.addWidget(score_button)
        self.score_fluctuation_list = self._dashboard_list()
        layout.addWidget(self.score_fluctuation_list, 1)
        return panel

    @staticmethod
    def _panel(title: str) -> tuple[QFrame, QVBoxLayout, QHBoxLayout]:
        panel = QFrame()
        panel.setObjectName("dashboardPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(8)
        header = QHBoxLayout()
        header.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("dashboardPanelTitle")
        header.addWidget(title_label)
        header.addStretch(1)
        layout.addLayout(header)
        return panel, layout, header

    def _action_button(
        self,
        text: str,
        icon_name: str,
        action,
    ) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("dashboardActionButton")
        button.setIcon(lucide_icon(icon_name, size=15))
        button.clicked.connect(action)
        return button

    @staticmethod
    def _dashboard_list() -> QListWidget:
        widget = QListWidget()
        widget.setObjectName("dashboardList")
        widget.setFrameShape(QFrame.Shape.NoFrame)
        widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        widget.setResizeMode(QListView.ResizeMode.Adjust)
        widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        widget.setSpacing(0)
        return widget

    def refresh_classes(self) -> None:
        selected_class_id = self.class_box.currentData()
        self._classes = self.controller.list_classes()
        self.class_box.blockSignals(True)
        self.class_box.clear()
        for class_group in self._classes:
            self.class_box.addItem(class_group["name"], class_group["id"])
        selected_index = self.class_box.findData(selected_class_id)
        self.class_box.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        self.class_box.blockSignals(False)
        self.refresh()

    def refresh(self, *_args) -> None:
        class_group = self._selected_class()
        selected_date = self._reference_date or date.today()
        self.date_label.setText(selected_date.strftime("%Y-%m-%d"))
        if class_group is None:
            self._set_empty_state()
            return
        try:
            overview = self.controller.get_daily_overview(class_group["id"], selected_date)
        except PlannerDataError:
            self.refresh_classes()
            return
        self._apply_overview(overview, selected_date)

    def set_reference_date(self, value: date | None) -> None:
        """Set a deterministic display date for testing; production always uses today."""

        self._reference_date = value
        self.refresh()

    def _apply_overview(self, overview: dict[str, Any], selected_date: date) -> None:
        class_group = overview["class"]
        metrics = overview["metrics"]
        event_count = len(overview["events"])
        attendance_note = "暂无异常记录" if metrics["attendance_count"] == 0 else "请及时核对记录"
        moral_note = "暂无新增记录" if metrics["moral_count"] == 0 else "今日新增记录"

        self.metric_cards["student_count"].set_value(
            f"{metrics['student_count']} 人",
            class_group["name"],
        )
        self.metric_cards["course_count"].set_value(
            f"{metrics['course_count']} 节",
            self._course_note(overview["courses"], selected_date),
        )
        self.metric_cards["attendance_count"].set_value(
            f"{metrics['attendance_count']} 条",
            attendance_note,
        )
        self.metric_cards["event_count"].set_value(
            f"{event_count} 项",
            self._display_date(selected_date),
        )
        self.metric_cards["moral_count"].set_value(
            f"{metrics['moral_count']} 条",
            moral_note,
        )

        self.course_summary.setText(f"{metrics['course_count']} 节")
        self.event_summary.setText(f"{event_count} 项")
        self._fill_course_list(overview["courses"], class_group, selected_date)
        self._fill_event_list(overview["events"])
        self._fill_activity_list(overview["recent_activity"])
        try:
            fluctuation = self.score_controller.get_recent_fluctuations(class_group["id"], limit=5)
        except ScoreDataError as exc:
            fluctuation = {
                "current_exam": None,
                "previous_exam": None,
                "rows": [],
                "reason": str(exc),
            }
        self._fill_score_fluctuation_list(fluctuation)

    def _fill_course_list(
        self,
        courses: list[dict[str, Any]],
        class_group: dict[str, Any],
        selected_date: date,
    ) -> None:
        self.course_list.clear()
        if not courses:
            self._add_empty_item(self.course_list, "当天没有课程安排")
            return
        for course in courses:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 62))
            self.course_list.addItem(item)

            row = QFrame()
            row.setObjectName("dashboardRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 3, 4, 3)
            row_layout.setSpacing(10)

            period_widget = QWidget()
            period_widget.setFixedWidth(96)
            period_block = QVBoxLayout(period_widget)
            period_block.setContentsMargins(0, 0, 0, 0)
            period_block.setSpacing(1)
            period = QLabel(course.get("period_name") or f"第 {course['period']} 节")
            period.setObjectName("rowMetaStrong")
            period_block.addWidget(period)
            course_time = QLabel(self._course_time(course))
            course_time.setObjectName("rowMeta")
            period_block.addWidget(course_time)
            row_layout.addWidget(period_widget)

            subject_mark = QLabel((course["subject"] or "课")[:1])
            subject_mark.setObjectName("subjectMark")
            subject_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
            subject_mark.setFixedSize(32, 32)
            subject_mark.setStyleSheet(
                f"background: {class_group['soft_color']}; color: {class_group['color']}; "
                "border: 1px solid rgba(0, 0, 0, 0.04); border-radius: 6px; font-weight: 700;"
            )
            row_layout.addWidget(subject_mark)

            course_copy_widget = QWidget()
            course_copy_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            course_copy = QVBoxLayout(course_copy_widget)
            course_copy.setContentsMargins(0, 0, 0, 0)
            course_copy.setSpacing(1)
            subject = QLabel(course["subject"])
            subject.setObjectName("rowPrimary")
            subject.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            course_copy.addWidget(subject)
            details = [value for value in (course.get("teacher"), course.get("location")) if value]
            detail = QLabel(" · ".join(details) or "暂未填写教师和地点")
            detail.setObjectName("rowSecondary")
            detail.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            course_copy.addWidget(detail)
            row_layout.addWidget(course_copy_widget, 1)

            state, tone = self._course_state(course, selected_date)
            status = QLabel(state)
            status.setObjectName("statusBadge")
            status.setProperty("tone", tone)
            status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status.setMinimumWidth(48)
            status.setFixedHeight(24)
            row_layout.addWidget(status)
            row.setToolTip(f"{period.text()} · {course['subject']} · {detail.text()}")
            self.course_list.setItemWidget(item, row)

    def _fill_event_list(self, events: list[dict[str, Any]]) -> None:
        self.event_list.clear()
        if not events:
            self._add_empty_item(self.event_list, "当天没有待办或日程")
            return
        for event in events:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 62))
            self.event_list.addItem(item)

            row = QFrame()
            row.setObjectName("dashboardRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 3, 4, 3)
            row_layout.setSpacing(10)

            time_label = QLabel(event["time_display"])
            time_label.setObjectName("eventTime")
            time_label.setFixedWidth(82)
            time_label.setStyleSheet(f"color: {event['class_color']}; font-weight: 600;")
            row_layout.addWidget(time_label)

            event_copy_widget = QWidget()
            event_copy_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            event_copy = QVBoxLayout(event_copy_widget)
            event_copy.setContentsMargins(0, 0, 0, 0)
            event_copy.setSpacing(1)
            title = QLabel(event["title"])
            title.setObjectName("rowPrimary")
            title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            event_copy.addWidget(title)
            details = [event["class_name"], event["note"]] if event["note"] else [event["class_name"]]
            detail = QLabel(" · ".join(details))
            detail.setObjectName("rowSecondary")
            detail.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            event_copy.addWidget(detail)
            row_layout.addWidget(event_copy_widget, 1)

            category = QLabel(event["category"])
            category.setObjectName("statusBadge")
            category.setProperty("tone", "info")
            category.setAlignment(Qt.AlignmentFlag.AlignCenter)
            category.setMinimumWidth(48)
            category.setFixedHeight(24)
            row_layout.addWidget(category)
            row.setToolTip(f"{event['time_display']} · {event['title']} · {detail.text()}")
            self.event_list.setItemWidget(item, row)

    def _fill_activity_list(self, activities: list[dict[str, Any]]) -> None:
        self.activity_list.clear()
        if not activities:
            self._add_empty_item(self.activity_list, "暂无考勤或德育动态")
            return
        for activity in activities:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 58))
            self.activity_list.addItem(item)

            row = QFrame()
            row.setObjectName("dashboardRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 3, 4, 3)
            row_layout.setSpacing(10)

            kind = QLabel(activity["kind"][:1])
            kind.setObjectName("activityKind")
            kind.setProperty("tone", activity["tone"])
            kind.setAlignment(Qt.AlignmentFlag.AlignCenter)
            kind.setFixedSize(30, 30)
            row_layout.addWidget(kind)

            activity_copy_widget = QWidget()
            activity_copy_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            activity_copy = QVBoxLayout(activity_copy_widget)
            activity_copy.setContentsMargins(0, 0, 0, 0)
            activity_copy.setSpacing(1)
            title = QLabel(activity["title"])
            title.setObjectName("rowPrimary")
            title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            activity_copy.addWidget(title)
            detail = QLabel(activity["detail"])
            detail.setObjectName("rowSecondary")
            detail.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            activity_copy.addWidget(detail)
            row_layout.addWidget(activity_copy_widget, 1)

            time_label = QLabel(activity["time_display"])
            time_label.setObjectName("rowMeta")
            row_layout.addWidget(time_label)
            row.setToolTip(f"{activity['title']} · {activity['detail']}")
            self.activity_list.setItemWidget(item, row)

    def _fill_score_fluctuation_list(self, result: dict[str, Any]) -> None:
        self.score_fluctuation_list.clear()
        rows = result.get("rows", [])
        current_exam = result.get("current_exam")
        previous_exam = result.get("previous_exam")
        if not rows:
            self.score_fluctuation_summary.setText("暂无可比考试")
            self.score_fluctuation_summary.setToolTip("")
            self._add_empty_item(
                self.score_fluctuation_list,
                result.get("reason") or "至少导入两次同学期考试后显示",
            )
            return

        self.score_fluctuation_summary.setText(
            f"{self._compact_exam_name(previous_exam)} → "
            f"{self._compact_exam_name(current_exam)}"
        )
        self.score_fluctuation_summary.setToolTip(
            f"{previous_exam['label']} → {current_exam['label']}"
        )
        for score_row in rows:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 70))
            self.score_fluctuation_list.addItem(item)

            row = QFrame()
            row.setObjectName("dashboardRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 4, 4, 4)
            row_layout.setSpacing(10)

            student_widget = QWidget()
            student_widget.setFixedWidth(78)
            student_layout = QVBoxLayout(student_widget)
            student_layout.setContentsMargins(0, 0, 0, 0)
            student_layout.setSpacing(2)
            name = QLabel(score_row["name"])
            name.setObjectName("scoreStudentName")
            student_layout.addWidget(name)
            student_number = QLabel(score_row["student_no"] or "未填学号")
            student_number.setObjectName("rowMeta")
            student_layout.addWidget(student_number)
            row_layout.addWidget(student_widget)

            score_widget = QWidget()
            score_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            score_layout = QVBoxLayout(score_widget)
            score_layout.setContentsMargins(0, 0, 0, 0)
            score_layout.setSpacing(2)
            rank_change = int(score_row["rank_change"])
            if rank_change > 0:
                badge_text, tone = f"进步 {rank_change} 名", "up"
            elif rank_change < 0:
                badge_text, tone = f"退步 {abs(rank_change)} 名", "down"
            else:
                badge_text, tone = "名次持平", "steady"

            top_line = QHBoxLayout()
            top_line.setContentsMargins(0, 0, 0, 0)
            top_line.setSpacing(8)
            total_change = (
                self._signed_score(score_row["total_change"])
                if score_row["total_comparable"]
                else "科目不同"
            )
            total_label = QLabel(
                "总分 "
                f"{self._format_score(score_row['previous_total'])} → "
                f"{self._format_score(score_row['current_total'])}"
                f"（{total_change}）"
            )
            total_label.setObjectName("scoreCompare")
            total_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            top_line.addWidget(total_label, 1)
            badge = QLabel(badge_text)
            badge.setObjectName("rankChangeBadge")
            badge.setProperty("tone", tone)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedSize(80, 23)
            top_line.addWidget(badge)
            score_layout.addLayout(top_line)

            bottom_line = QHBoxLayout()
            bottom_line.setContentsMargins(0, 0, 0, 0)
            bottom_line.setSpacing(8)
            subject_label = QLabel(self._subject_change_text(score_row["subject_changes"]))
            subject_label.setObjectName("subjectChange")
            subject_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            bottom_line.addWidget(subject_label, 1)
            rank_label = QLabel(
                f"班级 {score_row['previous_class_rank']} → {score_row['current_class_rank']}"
            )
            rank_label.setObjectName("rowMeta")
            rank_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rank_label.setFixedWidth(80)
            bottom_line.addWidget(rank_label)
            score_layout.addLayout(bottom_line)
            row_layout.addWidget(score_widget, 1)

            row.setToolTip(
                f"{score_row['name']} · {previous_exam['label']} → {current_exam['label']} · "
                f"总分 {self._format_score(score_row['previous_total'])} → "
                f"{self._format_score(score_row['current_total'])} · "
                f"{self._subject_change_text(score_row['subject_changes'])}"
            )
            self.score_fluctuation_list.setItemWidget(item, row)

    @staticmethod
    def _compact_exam_name(exam: dict[str, Any]) -> str:
        name = str(exam.get("name") or exam.get("label") or "考试")
        return name if len(name) <= 6 else f"{name[:5]}…"

    @classmethod
    def _subject_change_text(cls, rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "暂无相同科目可比较"
        return "；".join(
            f"{item['subject']} {cls._format_score(item['previous'])}→"
            f"{cls._format_score(item['current'])}（{cls._signed_score(item['change'])}）"
            for item in rows
        )

    @staticmethod
    def _format_score(value: float) -> str:
        number = float(value)
        return str(int(number)) if number.is_integer() else f"{number:.1f}"

    @classmethod
    def _signed_score(cls, value: float) -> str:
        number = float(value)
        prefix = "+" if number > 0 else ""
        return f"{prefix}{cls._format_score(number)}"

    @staticmethod
    def _add_empty_item(widget: QListWidget, text: str) -> None:
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 72))
        widget.addItem(item)
        label = QLabel(text)
        label.setObjectName("dashboardEmptyState")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget.setItemWidget(item, label)

    def _set_empty_state(self) -> None:
        notes = {
            "student_count": "请先建立班级",
            "course_count": "暂无课程数据",
            "attendance_count": "暂无考勤数据",
            "event_count": "暂无日程数据",
            "moral_count": "暂无德育数据",
        }
        for key, card in self.metric_cards.items():
            card.set_value("--", notes[key])
        self.course_summary.setText("0 节")
        self.event_summary.setText("0 项")
        self.score_fluctuation_summary.setText("暂无可比考试")
        self.score_fluctuation_summary.setToolTip("")
        self._add_empty_after_clear(self.course_list, "请先在学生数据中心建立班级")
        self._add_empty_after_clear(self.event_list, "建立班级后可维护日程")
        self._add_empty_after_clear(self.activity_list, "暂无班级动态")
        self._add_empty_after_clear(
            self.score_fluctuation_list,
            "建立班级并导入至少两次同学期考试后显示",
        )

    @classmethod
    def _add_empty_after_clear(cls, widget: QListWidget, text: str) -> None:
        widget.clear()
        cls._add_empty_item(widget, text)

    def _selected_class(self) -> dict[str, Any] | None:
        class_id = self.class_box.currentData()
        for class_group in self._classes:
            if class_group["id"] == class_id:
                return class_group
        return None

    @staticmethod
    def _course_time(course: dict[str, Any]) -> str:
        start_time = course.get("start_time") or ""
        end_time = course.get("end_time") or ""
        if start_time and end_time:
            return f"{start_time}—{end_time}"
        return start_time or "时间待定"

    @staticmethod
    def _course_note(courses: list[dict[str, Any]], selected_date: date) -> str:
        if not courses:
            return "暂无课程安排"
        if selected_date != date.today():
            return "已按课表载入"
        current_time = datetime.now().strftime("%H:%M")
        for course in courses:
            start_time = course.get("start_time") or ""
            if start_time and start_time > current_time:
                return f"下一节 {start_time}"
        return "今日课程已结束"

    @staticmethod
    def _course_state(course: dict[str, Any], selected_date: date) -> tuple[str, str]:
        if selected_date != date.today():
            return "已排课", "neutral"
        start_time = course.get("start_time") or ""
        end_time = course.get("end_time") or ""
        if not start_time:
            return "已排课", "neutral"
        current_time = datetime.now().strftime("%H:%M")
        if end_time and current_time > end_time:
            return "已结束", "info"
        if start_time <= current_time <= (end_time or start_time):
            return "进行中", "success"
        return "未开始", "neutral"

    @staticmethod
    def _display_date(value: date) -> str:
        weekday_labels = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
        return f"{value.month}月{value.day}日 {weekday_labels[value.weekday()]}"
