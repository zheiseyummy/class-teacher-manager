from __future__ import annotations

from typing import Any


CLASS_COLOR_CHOICES = (
    {"name": "翡翠绿", "color": "#12966D", "soft": "#E6F5EE"},
    {"name": "晴空蓝", "color": "#2D7DD2", "soft": "#EAF3FC"},
    {"name": "琥珀橙", "color": "#D97706", "soft": "#FFF4E5"},
    {"name": "玫瑰红", "color": "#C84B6F", "soft": "#FCEEF2"},
    {"name": "青松绿", "color": "#5F8F3A", "soft": "#F1F7EA"},
    {"name": "湖水青", "color": "#27808C", "soft": "#E9F7F8"},
)


def class_color_info(color: str | None, seed: Any = "") -> dict[str, str]:
    """Return a supported persistent class color, falling back deterministically."""

    normalized = str(color or "").strip().upper()
    for choice in CLASS_COLOR_CHOICES:
        if choice["color"] == normalized:
            return dict(choice)
    index = sum(ord(character) for character in str(seed)) % len(CLASS_COLOR_CHOICES)
    return dict(CLASS_COLOR_CHOICES[index])


def is_supported_class_color(color: str | None) -> bool:
    normalized = str(color or "").strip().upper()
    return any(choice["color"] == normalized for choice in CLASS_COLOR_CHOICES)
