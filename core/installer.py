"""Installation worker thread for creating bootable USB."""

import os
import sys
import time
import shutil
import platform
import subprocess
import threading
from pathlib import Path
from typing import Optional, Callable


class InstallWorker:
    """Runs in a background thread to create bootable USB."""

    def __init__(
        self,
        iso_path: str,
        usb_path: str,
        bypass_options: dict,
        on_progress: Callable[[int, str], None],
        on_done: Callable[[bool, str], None],
    ):
        self.iso_path = iso_path
        self.usb_path = usb_path
        self.bypass_options = bypass_options
        self.on_progress = on_progress
        self.on_done = on_done
        self._cancelled = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self):
        self._cancelled = True

    def _run(self):
        try:
            system = platform.system()
            if system == "Windows":
                self._run_windows()
            elif system == "Darwin":
                self._run_macos()
            else:
                self._run_linux()
        except Exception as e:
            if not self._cancelled:
                self.on_done(False, str(e))

    def _progress(self, pct: int, msg: str):
        if not self._cancelled:
            self.on_progress(pct, msg)

    def _run_windows(self):
        drive = self.usb_path  # e.g. "E:"
        if not drive.endswith("\\"):
            drive_path = drive + "\\"
        else:
            drive_path = drive
            drive = drive.rstrip("\\")

        self._progress(5, "Форматирование USB накопителя...")
        diskpart_script = f"""select volume {drive[0]}
clean
create partition primary
select partition 1
active
format fs=fat32 quick label="WINFLASH"
assign letter={drive[0]}
exit
"""
        script_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "winflash_diskpart.txt")
        with open(script_path, "w") as f:
            f.write(diskpart_script)

        result = subprocess.run(
            ["diskpart", "/s", script_path],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise RuntimeError(f"Ошибка форматирования: {result.stderr}")

        self._progress(20, "Монтирование ISO образа...")
        mount_result = subprocess.run(
            ["powershell", "-Command",
             f"(Mount-DiskImage -ImagePath '{self.iso_path}' -PassThru | Get-Volume).DriveLetter"],
            capture_output=True, text=True, timeout=60
        )
        if mount_result.returncode != 0:
            raise RuntimeError("Не удалось смонтировать ISO")

        iso_drive = mount_result.stdout.strip() + ":"
        self._progress(30, f"ISO смонтирован как {iso_drive}")

        self._progress(35, "Копирование файлов Windows на USB...")
        copy_result = subprocess.run(
            ["robocopy", iso_drive + "\\", drive_path, "/E", "/NDL", "/NFL", "/NJH"],
            capture_output=True, text=True, timeout=1800
        )
        # robocopy exit codes 0-7 are success
        if copy_result.returncode > 7:
            raise RuntimeError(f"Ошибка копирования: {copy_result.stderr}")

        self._progress(75, "Отмонтирование ISO образа...")
        subprocess.run(
            ["powershell", "-Command", f"Dismount-DiskImage -ImagePath '{self.iso_path}'"],
            capture_output=True, timeout=30
        )

        self._progress(80, "Применение обходов требований Windows 11...")
        self._apply_bypasses_windows(drive_path)

        self._progress(90, "Делаем USB загрузочным...")
        bootsect = os.path.join(drive_path, "boot", "bootsect.exe")
        if os.path.exists(bootsect):
            subprocess.run([bootsect, "/nt60", drive, "/mbr"],
                           capture_output=True, timeout=30)

        self._progress(100, "Готово! Загрузочная флешка создана.")
        self.on_done(True, "USB флешка успешно создана и готова к использованию!")

    def _apply_bypasses_windows(self, usb_root: str):
        """Write autounattend.xml with bypass registry keys to the USB."""
        from core.usb import generate_autounattend_xml
        xml = generate_autounattend_xml(self.bypass_options)
        xml_path = os.path.join(usb_root, "autounattend.xml")
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(xml)

        # Also write a helper script in $OEM$ folder
        oem_path = os.path.join(usb_root, "$OEM$", "$$", "Setup", "Scripts")
        os.makedirs(oem_path, exist_ok=True)
        script_lines = ["@echo off"]
        if self.bypass_options.get("bypass_tpm"):
            script_lines.append(
                'reg add "HKLM\\SYSTEM\\Setup\\LabConfig" /v BypassTPMCheck /t REG_DWORD /d 1 /f'
            )
        if self.bypass_options.get("bypass_secureboot"):
            script_lines.append(
                'reg add "HKLM\\SYSTEM\\Setup\\LabConfig" /v BypassSecureBootCheck /t REG_DWORD /d 1 /f'
            )
        with open(os.path.join(oem_path, "SetupComplete.cmd"), "w") as f:
            f.write("\n".join(script_lines))

    def _run_macos(self):
        """macOS version using dd — for testing/development only."""
        self._progress(5, "Определение диска...")
        disk = self.usb_path  # e.g. /dev/disk2

        self._progress(10, "Размонтирование диска...")
        subprocess.run(["diskutil", "unmountDisk", disk],
                       capture_output=True, timeout=30)

        self._progress(15, "Запись ISO на USB (это займёт несколько минут)...")
        # Use dd with progress via pv if available, else plain dd
        dd_cmd = ["dd", f"if={self.iso_path}", f"of={disk}", "bs=4m", "status=progress"]
        proc = subprocess.Popen(dd_cmd, stderr=subprocess.PIPE, text=True)

        import re
        while True:
            if self._cancelled:
                proc.terminate()
                return
            line = proc.stderr.readline()
            if not line and proc.poll() is not None:
                break
            match = re.search(r"(\d+)\s+bytes", line)
            if match:
                bytes_written = int(match.group(1))
                iso_size = os.path.getsize(self.iso_path)
                if iso_size > 0:
                    pct = min(90, int(15 + 75 * bytes_written / iso_size))
                    self._progress(pct, f"Записано: {bytes_written / 1e9:.1f} ГБ")

        if proc.returncode != 0:
            raise RuntimeError("Ошибка записи dd")

        self._progress(95, "Применение обходов...")
        # Mount and patch the USB
        mount_result = subprocess.run(
            ["diskutil", "mount", disk + "s2"],
            capture_output=True, text=True, timeout=30
        )
        if mount_result.returncode == 0:
            import re
            m = re.search(r"on (/Volumes/\S+)", mount_result.stdout)
            if m:
                usb_root = m.group(1)
                from core.usb import generate_autounattend_xml
                xml = generate_autounattend_xml(self.bypass_options)
                with open(os.path.join(usb_root, "autounattend.xml"), "w") as f:
                    f.write(xml)

        self._progress(100, "Готово!")
        self.on_done(True, "USB флешка успешно создана!")

    def _run_linux(self):
        self._run_macos()  # Same dd approach works on Linux
