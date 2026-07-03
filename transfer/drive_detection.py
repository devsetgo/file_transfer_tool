from __future__ import annotations

from dataclasses import dataclass
import ctypes
from pathlib import Path
import string
import os


DRIVE_UNKNOWN = 0
DRIVE_NO_ROOT_DIR = 1
DRIVE_REMOVABLE = 2
DRIVE_FIXED = 3


@dataclass(frozen=True)
class DriveInfo:
    root: str
    label: str
    drive_type: int


def _get_drive_type(root: str) -> int:
    return int(ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root)))


def _get_volume_label(root: str) -> str:
    volume_name_buffer = ctypes.create_unicode_buffer(261)
    file_system_name_buffer = ctypes.create_unicode_buffer(261)
    serial_number = ctypes.c_uint(0)
    max_component_len = ctypes.c_uint(0)
    file_system_flags = ctypes.c_uint(0)

    success = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(root),
        volume_name_buffer,
        ctypes.sizeof(volume_name_buffer),
        ctypes.byref(serial_number),
        ctypes.byref(max_component_len),
        ctypes.byref(file_system_flags),
        file_system_name_buffer,
        ctypes.sizeof(file_system_name_buffer),
    )

    if not success:
        return ""
    return volume_name_buffer.value


def _existing_drive_roots() -> list[str]:
    roots: list[str] = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if Path(root).exists():
            roots.append(root)
    return roots


def list_drives() -> list[DriveInfo]:
    drives: list[DriveInfo] = []
    for root in _existing_drive_roots():
        drives.append(
            DriveInfo(
                root=root,
                label=_get_volume_label(root),
                drive_type=_get_drive_type(root),
            )
        )
    return drives


def list_removable_drives() -> list[DriveInfo]:
    return [d for d in list_drives() if d.drive_type == DRIVE_REMOVABLE]


def find_archive_candidates(drives: list[DriveInfo], valid_labels: list[str]) -> list[DriveInfo]:
    label_set = {label.strip().lower() for label in valid_labels if label.strip()}
    if not label_set:
        return []
    return [d for d in drives if d.label.strip().lower() in label_set]


def is_system_drive(root: str) -> bool:
    system_drive = os.environ.get("SystemDrive", "C:").upper().rstrip("\\") + "\\"
    return root.upper() == system_drive
