"""
Windows ISO downloader via UUP Dump.
UUP Dump downloads files directly from Microsoft's CDN servers
and assembles them into a bootable ISO.
"""

import os
import io
import re
import json
import zipfile
import requests
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional


UUP_API = "https://api.uupdump.net"
UUP_WEB = "https://uupdump.net"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}

# (display_name, search_query, build_number, lang, edition)
_BUILD_MAP = {
    "win11_pro":   ("Windows 11 Pro",    "Windows 11",  "22631", "ru-ru", "Professional"),
    "win11_home":  ("Windows 11 Home",   "Windows 11",  "22631", "ru-ru", "Core"),
    "win10_pro":   ("Windows 10 Pro",    "Windows 10",  "19045", "ru-ru", "Professional"),
    "win10_home":  ("Windows 10 Home",   "Windows 10",  "19045", "ru-ru", "Core"),
    "win11_ltsc":  ("Windows 11 LTSC",   "Windows 11",  "26100", "ru-ru", "IoTEnterpriseS"),
}


# ── Public entry point ────────────────────────────────────────────────────────
class DownloadWorker:
    """
    Background worker: finds the build on UUP Dump → downloads UUP package →
    runs aria2c → runs convert script → returns path to finished .iso.
    """

    def __init__(
        self,
        version_id: str,
        output_dir: str,
        on_progress: Callable[[int, str], None],
        on_done: Callable[[bool, str, str], None],   # success, message, iso_path
    ):
        self.version_id = version_id
        self.output_dir = output_dir
        self.on_progress = on_progress
        self.on_done = on_done
        self._cancelled = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self):
        self._cancelled.set()

    # ── Internal pipeline ─────────────────────────────────────────────────────
    def _run(self):
        try:
            params = _BUILD_MAP.get(self.version_id)
            if not params:
                raise ValueError(f"Неизвестная версия: {self.version_id}")
            name, search, build_num, lang, edition = params

            self._prog(2, f"Поиск сборки {name}...")
            build = _find_latest_build(search, build_num, lang)
            if not build:
                raise RuntimeError(
                    "Сборка не найдена на UUP Dump.\n"
                    "Проверьте интернет-соединение и попробуйте ещё раз."
                )

            build_id    = build["uuid"]
            build_title = build.get("title", name)
            build_ver   = build.get("build", "")
            self._prog(5, f"Найдена: {build_title} (Build {build_ver})")

            if self._cancelled.is_set():
                return

            # Download the UUP package (ZIP with aria2c + scripts)
            self._prog(8, "Получение пакета загрузки с UUP Dump...")
            pkg_bytes = _fetch_download_package(build_id, lang, edition)
            self._prog(10, f"Пакет получен ({len(pkg_bytes)/1024:.0f} КБ)")

            # Extract to a dedicated subfolder
            pkg_dir = os.path.join(self.output_dir, f"uup_{build_id[:8]}")
            os.makedirs(pkg_dir, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(pkg_bytes)) as zf:
                zf.extractall(pkg_dir)
            self._prog(11, "Скрипты распакованы")

            if self._cancelled.is_set():
                return

            # Run the aria2c download script (downloads from Microsoft CDN)
            self._prog(12, "Загрузка файлов с серверов Microsoft...")
            _run_script(
                pkg_dir,
                script_names=["aria2_script.cmd", "aria2_script.sh", "download.cmd"],
                on_line=self._parse_aria2_line,
                cancelled=self._cancelled,
                start_pct=12, end_pct=78,
                prog_cb=self._prog,
            )

            if self._cancelled.is_set():
                return

            # Run the ISO conversion script (DISM + oscdimg, bundled in pkg)
            self._prog(79, "Сборка ISO образа (5–15 минут)...")
            _run_script(
                pkg_dir,
                script_names=["convert-UUP.cmd", "convert.cmd", "convert.sh"],
                on_line=self._parse_convert_line,
                cancelled=self._cancelled,
                start_pct=79, end_pct=98,
                prog_cb=self._prog,
            )

            # Find the resulting ISO
            iso_path = _find_iso(pkg_dir)
            if not iso_path:
                raise RuntimeError(
                    "ISO файл не найден после конвертации.\n"
                    "Попробуйте запустить приложение с правами администратора."
                )

            size_gb = os.path.getsize(iso_path) / 1e9
            self._prog(100, f"Готово! {os.path.basename(iso_path)} ({size_gb:.1f} ГБ)")
            self.on_done(True, "ISO успешно создан!", iso_path)

        except Exception as e:
            if not self._cancelled.is_set():
                self.on_done(False, str(e), "")

    def _prog(self, pct: int, msg: str):
        if not self._cancelled.is_set():
            self.on_progress(pct, msg)

    # ── Line parsers ──────────────────────────────────────────────────────────
    _aria2_pct = 0

    def _parse_aria2_line(self, line: str, start: int, end: int) -> tuple[int, str]:
        """Parse aria2c stdout for overall percentage + speed."""
        m = re.search(r"\((\d+)%\)", line)
        speed_m = re.search(r"DL:([^\s,\]]+)", line)
        if m:
            file_pct = int(m.group(1))
            self.__class__._aria2_pct = file_pct
        else:
            file_pct = self.__class__._aria2_pct
        speed = f"  [{speed_m.group(1)}/s]" if speed_m else ""
        pct = int(start + (end - start) * file_pct / 100)
        return pct, f"Загрузка: {file_pct}%{speed}"

    _convert_line_n = 0

    def _parse_convert_line(self, line: str, start: int, end: int) -> tuple[int, str]:
        self.__class__._convert_line_n += 1
        n = self.__class__._convert_line_n
        est_pct = min(end - 1, int(start + (end - start) * min(n / 150, 1.0)))
        msg = line.strip()[:70]
        if msg:
            return est_pct, f"Сборка ISO: {msg}"
        return est_pct, "Сборка ISO..."


# ── Helpers ───────────────────────────────────────────────────────────────────
def _find_latest_build(search: str, build_num: str, lang: str) -> Optional[dict]:
    """Search UUP Dump for the latest matching build."""
    for query in [f"{search} {build_num}", search]:
        try:
            r = requests.get(
                f"{UUP_API}/listid.php",
                params={"search": query, "language": lang},
                headers=HEADERS,
                timeout=20,
            )
            r.raise_for_status()
            builds = r.json().get("response", {}).get("builds", {})
            if builds:
                return sorted(
                    builds.values(),
                    key=lambda b: b.get("created", ""),
                    reverse=True,
                )[0]
        except Exception:
            pass
    return None


def _fetch_download_package(build_id: str, lang: str, edition: str) -> bytes:
    """
    POST to UUP Dump to get the download package ZIP
    (contains aria2c.exe + download script + conversion script).
    """
    r = requests.post(
        f"{UUP_WEB}/get.php",
        data={
            "id":         build_id,
            "pack":       lang,
            "edition[]":  edition,
            "autodl":     "2",
            "updates":    "1",
        },
        headers=HEADERS,
        timeout=60,
    )
    r.raise_for_status()
    if not r.content[:4] == b"PK\x03\x04":
        raise RuntimeError(
            "Неверный ответ от UUP Dump. "
            "Возможно, сервис временно недоступен — попробуйте позже."
        )
    return r.content


def _run_script(
    cwd: str,
    script_names: list[str],
    on_line: Callable,
    cancelled: threading.Event,
    start_pct: int,
    end_pct: int,
    prog_cb: Callable[[int, str], None],
):
    """Find and run a script, streaming output to on_line."""
    import stat, platform

    script_path = None
    for name in script_names:
        candidate = os.path.join(cwd, name)
        if os.path.exists(candidate):
            script_path = candidate
            break

    if not script_path:
        raise RuntimeError(
            f"Скрипт не найден в пакете UUP Dump. "
            f"Ожидался один из: {', '.join(script_names)}"
        )

    if platform.system() == "Windows":
        cmd = ["cmd.exe", "/c", script_path]
    else:
        os.chmod(script_path, os.stat(script_path).st_mode | stat.S_IEXEC)
        cmd = ["bash", script_path]

    proc = subprocess.Popen(
        cmd, cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )

    for raw_line in proc.stdout:
        if cancelled.is_set():
            proc.terminate()
            return
        if raw_line.strip():
            pct, msg = on_line(raw_line, start_pct, end_pct)
            prog_cb(pct, msg)

    proc.wait()


def _find_iso(directory: str) -> Optional[str]:
    """Recursively find the first .iso file in directory."""
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(".iso"):
                return os.path.join(root, f)
    return None


# ── Estimate download size ────────────────────────────────────────────────────
def estimated_download_gb(version_id: str) -> float:
    sizes = {
        "win11_pro":   5.4,
        "win11_home":  5.2,
        "win10_pro":   4.8,
        "win10_home":  4.6,
        "win11_ltsc":  3.9,
    }
    return sizes.get(version_id, 5.0)
