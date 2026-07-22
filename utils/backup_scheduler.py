from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from controllers.backup_controller import BackupController, BackupDataError


class BackupScheduler(QObject):
    """Check configured local backup schedules while the desktop app is running."""

    backup_created = Signal(str)
    backup_failed = Signal(str)

    def __init__(self, controller: BackupController | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.controller = controller or BackupController()
        self.timer = QTimer(self)
        self.timer.setInterval(30_000)
        self.timer.timeout.connect(self.check_now)

    def start(self) -> None:
        self.timer.start()
        QTimer.singleShot(1_000, self.check_now)

    @Slot()
    def check_now(self) -> None:
        try:
            archive = self.controller.run_scheduled_backup()
        except BackupDataError as exc:
            self.backup_failed.emit(str(exc))
            return
        if archive is not None:
            self.backup_created.emit(str(archive))
