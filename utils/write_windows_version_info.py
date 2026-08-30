from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import APP_NAME, APP_VERSION


def _version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = [int(part) for part in version.split(".")]
    if len(parts) > 4:
        raise ValueError("Windows file versions support at most four numeric parts.")
    return tuple((parts + [0] * (4 - len(parts)))[:4])  # type: ignore[return-value]


def write_version_info(output_path: Path) -> None:
    version_tuple = _version_tuple(APP_VERSION)
    version_csv = ", ".join(str(part) for part in version_tuple)
    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version_csv}),
    prodvers=({version_csv}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '080404B0',
        [
          StringStruct('CompanyName', 'LocalClassManager'),
          StringStruct('FileDescription', {APP_NAME!r}),
          StringStruct('FileVersion', {APP_VERSION!r}),
          StringStruct('InternalName', 'ClassTeacherManager'),
          StringStruct('LegalCopyright', 'Copyright 2026'),
          StringStruct('OriginalFilename', 'ClassTeacherManager.exe'),
          StringStruct('ProductName', {APP_NAME!r}),
          StringStruct('ProductVersion', {APP_VERSION!r})
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [2052, 1200])])
  ]
)
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: write_windows_version_info.py OUTPUT_PATH")
    write_version_info(Path(sys.argv[1]))
