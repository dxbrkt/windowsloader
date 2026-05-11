"""USB drive detection and writing utilities."""

import os
import sys
import subprocess
import platform
import threading
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class USBDrive:
    path: str          # e.g. "E:" on Windows, "/dev/disk2" on Mac
    label: str
    size_bytes: int
    filesystem: str
    removable: bool

    @property
    def size_gb(self) -> float:
        return self.size_bytes / (1024 ** 3)

    @property
    def size_str(self) -> str:
        gb = self.size_gb
        if gb >= 1:
            return f"{gb:.1f} ГБ"
        return f"{self.size_bytes / (1024**2):.0f} МБ"

    @property
    def display_name(self) -> str:
        return self.label if self.label else "USB Накопитель"


def detect_usb_drives() -> List[USBDrive]:
    """Detect all removable USB drives on the system."""
    system = platform.system()
    if system == "Windows":
        return _detect_windows()
    elif system == "Darwin":
        return _detect_macos()
    else:
        return _detect_linux()


def _detect_windows() -> List[USBDrive]:
    drives = []
    try:
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            bit = ord(letter) - ord('A')
            if bitmask & (1 << bit):
                path = f"{letter}:\\"
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(path)
                if drive_type == 2:  # DRIVE_REMOVABLE
                    try:
                        total = ctypes.c_ulonglong(0)
                        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                            path, None, ctypes.byref(total), None
                        )
                        vol_buf = ctypes.create_unicode_buffer(256)
                        fs_buf = ctypes.create_unicode_buffer(256)
                        ctypes.windll.kernel32.GetVolumeInformationW(
                            path, vol_buf, 256, None, None, None, fs_buf, 256
                        )
                        drives.append(USBDrive(
                            path=f"{letter}:",
                            label=vol_buf.value or "USB Drive",
                            size_bytes=total.value,
                            filesystem=fs_buf.value or "FAT32",
                            removable=True,
                        ))
                    except Exception:
                        pass
    except Exception:
        pass
    return drives


def _detect_macos() -> List[USBDrive]:
    drives = []
    try:
        result = subprocess.run(
            ["diskutil", "list", "-plist"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            import plistlib
            data = plistlib.loads(result.stdout.encode())
            for disk in data.get("AllDisksAndPartitions", []):
                disk_id = disk.get("DeviceIdentifier", "")
                if not disk_id.startswith("disk") or disk_id == "disk0":
                    continue
                info_result = subprocess.run(
                    ["diskutil", "info", "-plist", disk_id],
                    capture_output=True, text=True, timeout=5
                )
                if info_result.returncode == 0:
                    info = plistlib.loads(info_result.stdout.encode())
                    if info.get("Removable") or info.get("RemovableMedia"):
                        drives.append(USBDrive(
                            path=f"/dev/{disk_id}",
                            label=info.get("VolumeName") or info.get("MediaName") or "USB Drive",
                            size_bytes=info.get("TotalSize", 0),
                            filesystem=info.get("FilesystemType") or "Unknown",
                            removable=True,
                        ))
    except Exception:
        pass
    return drives


def _detect_linux() -> List[USBDrive]:
    drives = []
    try:
        import psutil
        for partition in psutil.disk_partitions():
            if "removable" in partition.opts or "/media/" in partition.mountpoint:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    drives.append(USBDrive(
                        path=partition.device,
                        label=os.path.basename(partition.mountpoint) or "USB Drive",
                        size_bytes=usage.total,
                        filesystem=partition.fstype,
                        removable=True,
                    ))
                except Exception:
                    pass
    except Exception:
        pass
    return drives


def generate_autounattend_xml(bypass_options: dict) -> str:
    """Generate autounattend.xml for bypassing Windows 11 requirements."""
    tpm_bypass = bypass_options.get("bypass_tpm", True)
    secureboot_bypass = bypass_options.get("bypass_secureboot", True)
    ram_bypass = bypass_options.get("bypass_ram", False)
    storage_bypass = bypass_options.get("bypass_storage", False)

    reg_commands = []
    if tpm_bypass:
        reg_commands.append(
            'reg add "HKLM\\SYSTEM\\Setup\\LabConfig" /v BypassTPMCheck /t REG_DWORD /d 1 /f'
        )
    if secureboot_bypass:
        reg_commands.append(
            'reg add "HKLM\\SYSTEM\\Setup\\LabConfig" /v BypassSecureBootCheck /t REG_DWORD /d 1 /f'
        )
    if ram_bypass:
        reg_commands.append(
            'reg add "HKLM\\SYSTEM\\Setup\\LabConfig" /v BypassRAMCheck /t REG_DWORD /d 1 /f'
        )
    if storage_bypass:
        reg_commands.append(
            'reg add "HKLM\\SYSTEM\\Setup\\LabConfig" /v BypassStorageCheck /t REG_DWORD /d 1 /f'
        )

    commands_xml = "\n".join([
        f"""                    <RunSynchronousCommand wcm:action="add">
                        <Order>{i+1}</Order>
                        <Path>cmd /c {cmd}</Path>
                    </RunSynchronousCommand>"""
        for i, cmd in enumerate(reg_commands)
    ])

    return f"""<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
    <settings pass="windowsPE">
        <component name="Microsoft-Windows-Setup"
                   processorArchitecture="amd64"
                   publicKeyToken="31bf3856ad364e35"
                   language="neutral"
                   versionScope="nonSxS">
            <RunSynchronous>
{commands_xml}
            </RunSynchronous>
        </component>
    </settings>
</unattend>
"""


def generate_bios_guide() -> str:
    """Return step-by-step BIOS boot guide."""
    return """
ИНСТРУКЦИЯ: КАК ЗАГРУЗИТЬСЯ С USB

1. ВСТАВЬТЕ флешку в компьютер ПЕРЕД включением

2. ВКЛЮЧИТЕ компьютер и сразу нажмите клавишу:
   • F12 — Dell, Lenovo, HP (Boot Menu)
   • F9  — HP
   • F8  — Asus
   • Esc → F9 — HP (старые)
   • Del / F2 — вход в BIOS (настройки)

3. В Boot Menu выберите вашу USB флешку

4. Если не видно USB в меню:
   → Войдите в BIOS (Del или F2)
   → Найдите "Boot Order" или "Boot Priority"
   → Переместите USB на первое место
   → Отключите Secure Boot (если Win 10)
   → Сохраните F10

5. Компьютер загрузится с флешки — следуйте инструкциям Windows
"""
