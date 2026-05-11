#!/usr/bin/env python3
"""
WinFlash Pro — Automated Windows USB Installer
Run: python main.py
"""

import sys
import platform

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QDir
from PyQt6.QtGui import QFont, QFontDatabase


def main():
    # Enable high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("WinFlash Pro")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("WinFlash")
    app.setStyle("Fusion")

    # Use system font with Segoe UI fallback
    default_font = QFont("Segoe UI", 10)
    default_font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(default_font)

    # Import here so QApplication exists before any QWidget is created
    from app.window import MainWindow
    window = MainWindow()
    window.show()

    # Center on screen
    screen = app.primaryScreen().availableGeometry()
    window.move(
        screen.x() + (screen.width()  - window.width())  // 2,
        screen.y() + (screen.height() - window.height()) // 2,
    )

    sys.exit(app.exec())


if __name__ == "__main__":
    # On Windows, check admin rights early (needed for diskpart / dd)
    if platform.system() == "Windows":
        import ctypes
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            is_admin = False
        if not is_admin:
            # Re-launch with admin rights
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            sys.exit(0)

    main()
