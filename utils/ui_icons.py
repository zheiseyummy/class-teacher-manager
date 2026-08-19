from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

ICON_DIR = Path(__file__).resolve().parents[1] / "resources" / "icons"


def lucide_icon(
    name: str,
    *,
    color: str = "#53657A",
    active_color: str = "#2563EB",
    selected_color: str | None = None,
    size: int = 18,
) -> QIcon:
    """Return a consistently rendered, palette-friendly Lucide icon."""

    icon_path = ICON_DIR / f"{name}.svg"
    if not icon_path.exists():
        return QIcon()

    source_icon = QIcon(str(icon_path))
    icon = QIcon()
    target_size = QSize(size, size)
    icon.addPixmap(
        _tint_pixmap(source_icon.pixmap(target_size), color),
        QIcon.Mode.Normal,
        QIcon.State.Off,
    )
    icon.addPixmap(
        _tint_pixmap(source_icon.pixmap(target_size), active_color),
        QIcon.Mode.Active,
        QIcon.State.Off,
    )
    if selected_color:
        icon.addPixmap(
            _tint_pixmap(source_icon.pixmap(target_size), selected_color),
            QIcon.Mode.Selected,
            QIcon.State.Off,
        )
    return icon


def _tint_pixmap(source: QPixmap, color: str) -> QPixmap:
    tinted = QPixmap(source.size())
    tinted.fill(Qt.GlobalColor.transparent)
    painter = QPainter(tinted)
    painter.drawPixmap(0, 0, source)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), QColor(color))
    painter.end()
    return tinted
