from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QSplitter


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
    table.verticalHeader().setDefaultSectionSize(38)


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
