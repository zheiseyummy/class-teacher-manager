from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from utils.ui_icons import lucide_icon


class EmptyState(QFrame):
    """Reusable business-aware empty state for table and list workspaces."""

    def __init__(
        self,
        *,
        icon_name: str = "clipboard-check",
        action: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("emptyState")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)
        layout.addStretch(1)

        self.icon_label = QLabel()
        self.icon_label.setObjectName("emptyStateIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedSize(48, 48)
        self.icon_label.setPixmap(
            lucide_icon(
                icon_name,
                color="#6F7F93",
                active_color="#6F7F93",
                size=22,
            ).pixmap(QSize(22, 22))
        )
        layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.title_label = QLabel()
        self.title_label.setObjectName("emptyStateTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.message_label = QLabel()
        self.message_label.setObjectName("emptyStateMessage")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setMaximumWidth(430)
        layout.addWidget(self.message_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.action_button = QPushButton()
        self.action_button.setObjectName("emptyActionButton")
        self.action_button.setVisible(False)
        if action is not None:
            self.action_button.clicked.connect(action)
        layout.addWidget(self.action_button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)

    def set_content(self, title: str, message: str, action_text: str = "") -> None:
        self.title_label.setText(title)
        self.message_label.setText(message)
        self.action_button.setText(action_text)
        self.action_button.setVisible(bool(action_text))


def scrollable_detail(widget: QWidget, *, name: str = "detailScroll") -> QScrollArea:
    """Place a dense detail/form pane in a borderless vertical scroll area."""

    widget.setMinimumWidth(0)
    scroll = QScrollArea()
    scroll.setObjectName(name)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(widget)
    return scroll
