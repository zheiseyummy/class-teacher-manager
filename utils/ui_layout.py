from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QAbstractItemView, QDialog, QHeaderView, QSplitter, QWidget


def restore_splitter(splitter: QSplitter, key: str, default_sizes: Iterable[int]) -> None:
    """Persist user-adjusted splitter sizes between local application launches."""

    settings = QSettings("LocalClassManager", "ClassManager")
    raw_value = settings.value(f"layout/{key}")
    sizes = _read_sizes(raw_value) or list(default_sizes)
    splitter.setSizes(sizes)
    splitter.splitterMoved.connect(lambda _position, _index: settings.setValue(f"layout/{key}", splitter.sizes()))


def configure_resizable_table(table: QAbstractItemView) -> None:
    """Use desktop-friendly, user-resizable table columns and smooth scrolling."""

    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    header.setSectionsMovable(True)
    header.setMinimumSectionSize(58)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.verticalHeader().setDefaultSectionSize(44)


def set_compact_columns(
    table: QAbstractItemView,
    hidden_columns: Iterable[int],
    compact: bool,
) -> None:
    """Hide low-priority columns in narrow layouts while preserving user data."""

    for column in hidden_columns:
        table.setColumnHidden(column, compact)


def refresh_style(widget: QWidget) -> None:
    """Re-evaluate QSS selectors after a dynamic property changes."""

    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def configure_responsive_dialog(
    dialog: QDialog,
    preferred_width: int,
    preferred_height: int | None = None,
    *,
    minimum_width: int = 340,
    minimum_height: int = 240,
) -> None:
    """Keep data-entry dialogs usable when the desktop window is narrow."""

    parent = dialog.parentWidget()
    parent_window = parent.window() if parent is not None else None
    compact = parent_window is not None and parent_window.width() < 840

    target_width = preferred_width
    target_height = preferred_height or max(dialog.sizeHint().height(), minimum_height)
    if compact and parent_window is not None:
        target_width = min(preferred_width, max(320, parent_window.width() - 24))
        target_height = min(target_height, max(420, parent_window.height() - 32))

    dialog.setMinimumWidth(min(minimum_width, target_width))
    dialog.setMinimumHeight(min(minimum_height, target_height))
    dialog.resize(target_width, target_height)
    dialog.setProperty("compact", compact)


def _read_sizes(raw_value) -> list[int] | None:
    if isinstance(raw_value, (list, tuple)):
        try:
            sizes = [int(value) for value in raw_value]
        except (TypeError, ValueError):
            return None
        return sizes if sizes and all(value >= 0 for value in sizes) else None
    if isinstance(raw_value, str):
        try:
            sizes = [int(value) for value in raw_value.split(",")]
        except ValueError:
            return None
        return sizes if sizes and all(value >= 0 for value in sizes) else None
    return None
