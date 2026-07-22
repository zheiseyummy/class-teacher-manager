from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import date, datetime, time
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy import and_, func, or_, select

from config import APP_NAME, BACKUP_DIR, DATABASE_PATH, ensure_app_dirs
from database.connection import engine, get_session
from database.init_db import initialize_database
from models.backup_record import BackupRecord, BackupSettings
from models.exam import Exam
from models.moral import MoralRecord
from models.reserved import LeaveRecord
from models.schedule import CalendarEvent
from models.teaching_schedule import AcademicSemester, SchedulePeriod, TeachingCourse


class BackupDataError(ValueError):
    """Raised when a backup archive, restore, or schedule setting is invalid."""


class BackupController:
    """Create verified local archives and safely replace the local SQLite database."""

    FORMAT_VERSION = 1
    MANIFEST_ENTRY = "manifest.json"
    DATABASE_ENTRY = "database/class_manager.db"
    MAX_DATABASE_BYTES = 2 * 1024 * 1024 * 1024
    FREQUENCIES = ("daily", "weekly")
    ACTION_LABELS = {
        "manual_backup": "手动完整备份",
        "automatic_backup": "定时完整备份",
        "semester_archive": "学期归档",
        "pre_restore": "恢复前安全备份",
        "restore": "已恢复备份",
    }

    def list_semesters(self) -> list[dict[str, Any]]:
        with get_session() as session:
            semesters = session.scalars(
                select(AcademicSemester)
                .where(AcademicSemester.is_deleted.is_(False))
                .order_by(AcademicSemester.start_date.desc(), AcademicSemester.id.desc())
            ).all()
            return [self._semester_dict(semester) for semester in semesters]

    def get_settings(self) -> dict[str, Any]:
        with get_session() as session:
            settings = self._settings(session)
            return self._settings_dict(settings)

    def save_settings(self, data: dict[str, Any]) -> dict[str, Any]:
        frequency = str(data.get("schedule_frequency") or "daily").strip().lower()
        if frequency not in self.FREQUENCIES:
            raise BackupDataError("请选择每天或每周的自动备份频率。")
        schedule_time = self._time_text(data.get("schedule_time"), "自动备份时间")
        try:
            weekday = int(data.get("schedule_weekday", 1))
        except (TypeError, ValueError) as exc:
            raise BackupDataError("请选择有效的每周备份日期。") from exc
        if weekday not in range(1, 8):
            raise BackupDataError("每周备份日期应为周一至周日。")
        destination_dir = self._backup_directory(data.get("destination_dir"))

        with get_session() as session:
            settings = self._settings(session)
            schedule_changed = (
                settings.schedule_frequency != frequency
                or settings.schedule_time != schedule_time
                or settings.schedule_weekday != weekday
            )
            settings.auto_enabled = bool(data.get("auto_enabled"))
            settings.schedule_frequency = frequency
            settings.schedule_time = schedule_time
            settings.schedule_weekday = weekday
            settings.destination_dir = str(destination_dir)
            if schedule_changed:
                settings.last_auto_backup_at = None
            session.flush()
            return self._settings_dict(settings)

    def list_records(self, limit: int = 120) -> list[dict[str, Any]]:
        with get_session() as session:
            records = session.scalars(
                select(BackupRecord).order_by(BackupRecord.created_at.desc(), BackupRecord.id.desc()).limit(limit)
            ).all()
            result: list[dict[str, Any]] = []
            for record in records:
                path = Path(record.backup_path)
                exists = path.is_file()
                result.append(
                    {
                        "id": record.id,
                        "action": record.action,
                        "action_display": self.ACTION_LABELS.get(record.action, record.action),
                        "backup_path": record.backup_path,
                        "file_name": path.name,
                        "exists": exists,
                        "file_size": path.stat().st_size if exists else 0,
                        "created_at": record.created_at,
                        "created_at_display": record.created_at.strftime("%Y-%m-%d %H:%M"),
                        "note": record.note or "",
                    }
                )
            return result

    def create_full_backup(
        self,
        destination: str | Path | None = None,
        action: str = "manual_backup",
        note: str | None = None,
    ) -> Path:
        return self._create_archive(
            kind="full",
            destination=destination,
            action=action,
            note=note or "完整本地数据库快照。",
        )

    def create_semester_archive(self, semester_id: int, destination: str | Path | None = None) -> Path:
        semester = self._semester_with_summary(semester_id)
        safe_name = self._safe_file_part(semester["name"])
        return self._create_archive(
            kind="semester_archive",
            destination=destination,
            action="semester_archive",
            note=f"{semester['name']} 学期归档。",
            semester=semester,
            filename_prefix=f"学期归档_{safe_name}",
        )

    def inspect_backup(self, archive_path: str | Path) -> dict[str, Any]:
        path = Path(archive_path).expanduser()
        if not path.is_file():
            raise BackupDataError("未找到备份文件，请重新选择 ZIP 文件。")
        if path.suffix.lower() != ".zip":
            raise BackupDataError("请选择本系统生成的 ZIP 备份文件。")
        try:
            with zipfile.ZipFile(path, "r") as archive:
                self._assert_safe_members(archive)
                if self.MANIFEST_ENTRY not in archive.namelist() or self.DATABASE_ENTRY not in archive.namelist():
                    raise BackupDataError("该 ZIP 文件不包含可恢复的班主任管理系统数据。")
                try:
                    manifest = json.loads(archive.read(self.MANIFEST_ENTRY).decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise BackupDataError("备份说明文件已损坏，无法确认数据来源。") from exc
                if manifest.get("format_version") != self.FORMAT_VERSION:
                    raise BackupDataError("该备份文件版本不受当前程序支持。")
                if manifest.get("app_name") != APP_NAME:
                    raise BackupDataError("该 ZIP 文件不是本系统生成的备份。")
                database_info = archive.getinfo(self.DATABASE_ENTRY)
                if database_info.file_size <= 0 or database_info.file_size > self.MAX_DATABASE_BYTES:
                    raise BackupDataError("备份数据库大小异常，已拒绝恢复。")
                expected_hash = str(manifest.get("database", {}).get("sha256") or "").lower()
                if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
                    raise BackupDataError("备份缺少有效的数据校验信息。")
        except zipfile.BadZipFile as exc:
            raise BackupDataError("所选文件不是有效的 ZIP 备份。") from exc
        return {
            "path": str(path.resolve()),
            "file_name": path.name,
            "file_size": path.stat().st_size,
            "manifest": manifest,
            "kind": manifest.get("backup_kind", "full"),
            "created_at": manifest.get("created_at", ""),
            "semester": manifest.get("semester"),
        }

    def restore_backup(self, archive_path: str | Path) -> dict[str, Any]:
        info = self.inspect_backup(archive_path)
        archive_path = Path(info["path"])
        manifest = info["manifest"]
        with tempfile.TemporaryDirectory(prefix="class_manager_restore_") as temp_dir:
            temp_root = Path(temp_dir)
            restored_database = temp_root / "restored.db"
            try:
                with zipfile.ZipFile(archive_path, "r") as archive:
                    with archive.open(self.DATABASE_ENTRY, "r") as source, restored_database.open("wb") as target:
                        shutil.copyfileobj(source, target, length=1024 * 1024)
            except (OSError, zipfile.BadZipFile) as exc:
                raise BackupDataError("读取备份数据库失败，当前数据没有被修改。") from exc

            expected_hash = manifest["database"]["sha256"].lower()
            if self._sha256(restored_database) != expected_hash:
                raise BackupDataError("备份数据校验不通过，当前数据没有被修改。")
            self._assert_sqlite_integrity(restored_database)

            safety_backup = self.create_full_backup(
                action="pre_restore",
                note=f"恢复 {archive_path.name} 前自动创建的安全备份。",
            )
            DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
            replacement = DATABASE_PATH.with_name(f".{DATABASE_PATH.name}.restore")
            shutil.copy2(restored_database, replacement)
            try:
                engine.dispose()
                os.replace(replacement, DATABASE_PATH)
                self._remove_stale_journals()
                initialize_database()
            except OSError as exc:
                if replacement.exists():
                    replacement.unlink(missing_ok=True)
                raise BackupDataError("替换本地数据库失败，当前数据仍保留。") from exc

        with get_session() as session:
            session.add(
                BackupRecord(
                    backup_path=str(archive_path),
                    action="restore",
                    note=f"已恢复 {manifest.get('created_at', '')} 创建的备份；恢复前安全备份：{safety_backup.name}",
                )
            )
        return {
            "restored_from": str(archive_path),
            "safety_backup": str(safety_backup),
            "manifest": manifest,
        }

    def run_scheduled_backup(self, now: datetime | None = None) -> Path | None:
        now = now or datetime.now()
        settings = self.get_settings()
        if not settings["auto_enabled"]:
            return None
        if settings["schedule_frequency"] == "weekly" and now.isoweekday() != settings["schedule_weekday"]:
            return None
        scheduled_time = time.fromisoformat(settings["schedule_time"])
        due_at = datetime.combine(now.date(), scheduled_time)
        if now < due_at:
            return None
        last_run = settings["last_auto_backup_at"]
        if last_run is not None and last_run >= due_at:
            return None

        archive = self.create_full_backup(
            destination=Path(settings["destination_dir"]),
            action="automatic_backup",
            note=f"按{self._frequency_display(settings)}定时执行。",
        )
        with get_session() as session:
            current = self._settings(session)
            current.last_auto_backup_at = now
        return archive

    def _create_archive(
        self,
        *,
        kind: str,
        destination: str | Path | None,
        action: str,
        note: str,
        semester: dict[str, Any] | None = None,
        filename_prefix: str | None = None,
    ) -> Path:
        ensure_app_dirs()
        prefix = filename_prefix or ("完整备份" if kind == "full" else "数据归档")
        target_path = self._archive_path(destination, prefix)
        with tempfile.TemporaryDirectory(prefix="class_manager_backup_") as temp_dir:
            snapshot_path = Path(temp_dir) / "class_manager.db"
            self._snapshot_database(snapshot_path)
            database_metadata = {
                "entry": self.DATABASE_ENTRY,
                "size": snapshot_path.stat().st_size,
                "sha256": self._sha256(snapshot_path),
            }
            manifest: dict[str, Any] = {
                "format_version": self.FORMAT_VERSION,
                "app_name": APP_NAME,
                "backup_kind": kind,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "database": database_metadata,
                "note": note,
            }
            if semester is not None:
                manifest["semester"] = semester
                manifest["archive_note"] = "归档包包含该学期说明与完整数据库快照，可直接用于完整恢复。"
            try:
                with zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr(
                        self.MANIFEST_ENTRY,
                        json.dumps(manifest, ensure_ascii=False, indent=2),
                    )
                    archive.write(snapshot_path, arcname=self.DATABASE_ENTRY)
            except OSError as exc:
                raise BackupDataError("无法写入 ZIP 备份，请确认目标文件未被占用且磁盘空间充足。") from exc
        self._record_backup(target_path, action, note)
        return target_path

    def _semester_with_summary(self, semester_id: int) -> dict[str, Any]:
        with get_session() as session:
            semester = session.scalar(
                select(AcademicSemester).where(
                    AcademicSemester.id == semester_id,
                    AcademicSemester.is_deleted.is_(False),
                )
            )
            if semester is None:
                raise BackupDataError("请选择有效的学期。")
            start_at = datetime.combine(semester.start_date, time.min)
            end_at = datetime.combine(semester.end_date, time.max)
            exams = int(
                session.scalar(
                    select(func.count(Exam.id)).where(
                        Exam.is_deleted.is_(False),
                        or_(
                            Exam.semester == semester.name,
                            and_(Exam.exam_date >= semester.start_date, Exam.exam_date <= semester.end_date),
                        ),
                    )
                )
                or 0
            )
            summary = {
                "teaching_courses": int(
                    session.scalar(
                        select(func.count(TeachingCourse.id)).where(
                            TeachingCourse.semester_id == semester.id,
                            TeachingCourse.is_deleted.is_(False),
                        )
                    )
                    or 0
                ),
                "periods": int(
                    session.scalar(
                        select(func.count(SchedulePeriod.id)).where(
                            SchedulePeriod.semester_id == semester.id,
                            SchedulePeriod.is_deleted.is_(False),
                        )
                    )
                    or 0
                ),
                "calendar_events": int(
                    session.scalar(
                        select(func.count(CalendarEvent.id)).where(
                            CalendarEvent.is_deleted.is_(False),
                            CalendarEvent.event_date >= semester.start_date,
                            CalendarEvent.event_date <= semester.end_date,
                        )
                    )
                    or 0
                ),
                "exams": exams,
                "moral_records": int(
                    session.scalar(
                        select(func.count(MoralRecord.id)).where(
                            MoralRecord.is_deleted.is_(False),
                            MoralRecord.record_date >= semester.start_date,
                            MoralRecord.record_date <= semester.end_date,
                        )
                    )
                    or 0
                ),
                "attendance_records": int(
                    session.scalar(
                        select(func.count(LeaveRecord.id)).where(
                            LeaveRecord.is_deleted.is_(False),
                            LeaveRecord.start_time <= end_at,
                            or_(LeaveRecord.end_time.is_(None), LeaveRecord.end_time >= start_at),
                        )
                    )
                    or 0
                ),
            }
            result = self._semester_dict(semester)
            result["summary"] = summary
            return result

    @staticmethod
    def _semester_dict(semester: AcademicSemester) -> dict[str, Any]:
        return {
            "id": semester.id,
            "name": semester.name,
            "start_date": semester.start_date.isoformat(),
            "end_date": semester.end_date.isoformat(),
            "date_range_display": f"{semester.start_date.isoformat()} 至 {semester.end_date.isoformat()}",
        }

    def _snapshot_database(self, snapshot_path: Path) -> None:
        if not DATABASE_PATH.is_file():
            raise BackupDataError("本地数据库尚未初始化，无法创建备份。")
        source: sqlite3.Connection | None = None
        target: sqlite3.Connection | None = None
        try:
            source = sqlite3.connect(str(DATABASE_PATH))
            target = sqlite3.connect(str(snapshot_path))
            source.backup(target)
        except sqlite3.Error as exc:
            raise BackupDataError("读取本地数据库失败，未生成备份。") from exc
        finally:
            if target is not None:
                target.close()
            if source is not None:
                source.close()
        self._assert_sqlite_integrity(snapshot_path)

    def _archive_path(self, destination: str | Path | None, prefix: str) -> Path:
        file_name = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        if destination is None:
            output_dir = self._backup_directory(BACKUP_DIR)
            return self._unique_archive_path(output_dir / file_name)
        raw_path = Path(destination).expanduser()
        if raw_path.exists() and raw_path.is_dir() or raw_path.suffix.lower() != ".zip":
            output_dir = self._backup_directory(raw_path)
            return self._unique_archive_path(output_dir / file_name)
        target = raw_path.with_suffix(".zip")
        target.parent.mkdir(parents=True, exist_ok=True)
        return self._unique_archive_path(target.resolve())

    @staticmethod
    def _unique_archive_path(path: Path) -> Path:
        if not path.exists():
            return path
        for suffix in range(2, 10_000):
            candidate = path.with_name(f"{path.stem}_{suffix}{path.suffix}")
            if not candidate.exists():
                return candidate
        raise BackupDataError("备份目录中已有过多同名文件，请更换目录后重试。")

    @staticmethod
    def _backup_directory(value: str | Path | None) -> Path:
        path = Path(value or BACKUP_DIR).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise BackupDataError("无法创建备份目录，请检查目录权限。") from exc
        return path.resolve()

    @staticmethod
    def _safe_file_part(value: str) -> str:
        return re.sub(r'[<>:"/\\|?*]+', "_", value).strip(" .") or "学期"

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _assert_sqlite_integrity(path: Path) -> None:
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(str(path))
            result = connection.execute("PRAGMA integrity_check").fetchone()
        except sqlite3.Error as exc:
            raise BackupDataError("备份数据库无法打开或已损坏。") from exc
        finally:
            if connection is not None:
                connection.close()
        if result is None or result[0] != "ok":
            raise BackupDataError("备份数据库完整性校验失败。")

    @staticmethod
    def _assert_safe_members(archive: zipfile.ZipFile) -> None:
        for info in archive.infolist():
            member = PurePosixPath(info.filename)
            if member.is_absolute() or ".." in member.parts:
                raise BackupDataError("备份文件包含不安全路径，已拒绝读取。")

    @staticmethod
    def _time_text(value: Any, label: str) -> str:
        text = str(value or "").strip()
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", text):
            raise BackupDataError(f"{label}应使用 HH:MM 格式。")
        return text

    @staticmethod
    def _remove_stale_journals() -> None:
        for suffix in ("-wal", "-shm"):
            DATABASE_PATH.with_name(f"{DATABASE_PATH.name}{suffix}").unlink(missing_ok=True)

    def _record_backup(self, path: Path, action: str, note: str) -> None:
        with get_session() as session:
            session.add(BackupRecord(backup_path=str(path), action=action, note=note))

    @staticmethod
    def _settings(session) -> BackupSettings:
        settings = session.get(BackupSettings, 1)
        if settings is None:
            settings = BackupSettings(id=1, destination_dir=str(Path(BACKUP_DIR).resolve()))
            session.add(settings)
            session.flush()
        return settings

    @staticmethod
    def _settings_dict(settings: BackupSettings) -> dict[str, Any]:
        return {
            "auto_enabled": settings.auto_enabled,
            "schedule_frequency": settings.schedule_frequency,
            "schedule_time": settings.schedule_time,
            "schedule_weekday": settings.schedule_weekday,
            "destination_dir": settings.destination_dir,
            "last_auto_backup_at": settings.last_auto_backup_at,
        }

    @staticmethod
    def _frequency_display(settings: dict[str, Any]) -> str:
        if settings["schedule_frequency"] == "weekly":
            labels = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
            return f"每周{labels[settings['schedule_weekday'] - 1]} {settings['schedule_time']}"
        return f"每天 {settings['schedule_time']}"
