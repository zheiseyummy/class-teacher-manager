from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class BackupRecord(Base):
    __tablename__ = "backup_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    backup_path: Mapped[str] = mapped_column(String(500), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class BackupSettings(TimestampMixin, Base):
    """Singleton settings for local scheduled backups."""

    __tablename__ = "backup_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    auto_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    schedule_frequency: Mapped[str] = mapped_column(String(20), default="daily", nullable=False)
    schedule_time: Mapped[str] = mapped_column(String(5), default="18:00", nullable=False)
    schedule_weekday: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    destination_dir: Mapped[str] = mapped_column(String(500), nullable=False)
    last_auto_backup_at: Mapped[datetime | None] = mapped_column(DateTime)
