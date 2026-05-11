"""Main application window with glassmorphism design."""

import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget,
    QPushButton, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient, QPen, QBrush,
    QPainterPath, QFont, QFontMetrics
)

from app.widgets import StepIndicator, GlowButton, shadow, C_TEXT, C_TEXT_MUTED, C_ACCENT1
from app.pages import (
    WelcomePage, USBSelectPage, WindowsSelectPage,
    OptionsPage, ProgressPage, DonePage, DownloadPage
)


class MainWindow(QWidget):
    """Root window — frameless, translucent, glassmorphism background."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowSystemMenuHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(900, 650)
        self.resize(920, 680)

        self._drag_pos = QPoint()
        self._current_step = 0

        # Background animation
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick_bg)
        self._anim_timer.start(50)
        self._bg_offset = 0.0

        self._build_ui()

    # ── Background paint ──────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, 20, 20)

        # Deep space base
        base = QLinearGradient(0, 0, w, h)
        base.setColorAt(0,   QColor(7,  9,  18, 252))
        base.setColorAt(0.4, QColor(12, 16, 32, 252))
        base.setColorAt(0.7, QColor(16, 11, 28, 252))
        base.setColorAt(1,   QColor(7,  9,  18, 252))
        p.fillPath(path, QBrush(base))

        # Animated ambient glow (top-left)
        import math
        ox = math.sin(self._bg_offset * 0.02) * 60
        oy = math.cos(self._bg_offset * 0.015) * 40
        r1 = QRadialGradient(w * 0.2 + ox, h * 0.2 + oy, h * 0.6)
        r1.setColorAt(0, QColor(99, 102, 241, 22))
        r1.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillPath(path, QBrush(r1))

        # Animated ambient glow (bottom-right)
        ox2 = math.cos(self._bg_offset * 0.018) * 50
        oy2 = math.sin(self._bg_offset * 0.022) * 35
        r2 = QRadialGradient(w * 0.8 + ox2, h * 0.75 + oy2, h * 0.5)
        r2.setColorAt(0, QColor(6, 182, 212, 18))
        r2.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillPath(path, QBrush(r2))

        # Window border
        p.setPen(QPen(QColor(255, 255, 255, 28), 1))
        p.drawPath(path)

    def _tick_bg(self):
        self._bg_offset += 1.0
        self.update()

    # ── UI layout ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        root.addWidget(self._make_titlebar())

        # Step indicator
        self._step_bar = StepIndicator(self)
        root.addWidget(self._step_bar)

        # Thin separator
        sep = QWidget(self)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.08);")
        root.addWidget(sep)

        # Page stack
        self._stack = QStackedWidget(self)
        self._stack.setStyleSheet("background: transparent;")

        self._page_welcome  = WelcomePage(self)
        self._page_usb      = USBSelectPage(self)
        self._page_windows  = WindowsSelectPage(self)
        self._page_download = DownloadPage(self)
        self._page_options  = OptionsPage(self)
        self._page_progress = ProgressPage(self)
        self._page_done     = DonePage(self)

        # Page indices
        self._IDX = {
            "welcome":  0,
            "usb":      1,
            "windows":  2,
            "download": 3,
            "options":  4,
            "progress": 5,
            "done":     6,
        }

        for page in [
            self._page_welcome, self._page_usb, self._page_windows,
            self._page_download, self._page_options, self._page_progress,
            self._page_done,
        ]:
            self._stack.addWidget(page)

        root.addWidget(self._stack, 1)

        # Wire navigation
        self._page_welcome.next_clicked.connect(lambda: self._go_to(self._IDX["usb"]))
        self._page_usb.next_clicked.connect(lambda: self._go_to(self._IDX["windows"]))
        self._page_usb.back_clicked.connect(lambda: self._go_to(self._IDX["welcome"]))
        self._page_windows.next_clicked.connect(lambda: self._go_to(self._IDX["options"]))
        self._page_windows.back_clicked.connect(lambda: self._go_to(self._IDX["usb"]))
        self._page_windows.download_clicked.connect(self._open_download_page)
        self._page_download.back_clicked.connect(lambda: self._go_to(self._IDX["windows"]))
        self._page_download.iso_ready.connect(self._on_download_complete)
        self._page_options.next_clicked.connect(self._start_install)
        self._page_options.back_clicked.connect(lambda: self._go_to(self._IDX["windows"]))
        self._page_progress.done_clicked.connect(lambda: self._go_to(self._IDX["done"]))
        self._page_done.restart_clicked.connect(lambda: self._go_to(self._IDX["welcome"]))

    def _make_titlebar(self) -> QWidget:
        bar = QWidget(self)
        bar.setFixedHeight(46)
        bar.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        bar.setCursor(Qt.CursorShape.SizeAllCursor)

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 16, 0)
        lay.setSpacing(0)

        # App icon + name
        icon_lbl = QLabel("⚡")
        icon_lbl.setFont(QFont("Segoe UI Emoji", 14))
        icon_lbl.setStyleSheet("background: transparent; color: #6366f1;")
        lay.addWidget(icon_lbl)
        lay.addSpacing(8)

        title = QLabel("WinFlash Pro")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #e2e8f0; background: transparent;")
        lay.addWidget(title)

        ver = QLabel("v1.0")
        ver.setFont(QFont("Segoe UI", 8))
        ver.setStyleSheet("color: #475569; background: transparent; margin-left: 6px;")
        lay.addWidget(ver)
        lay.addStretch()

        # Window buttons
        for text, slot, color in [
            ("─", self.showMinimized, "#94a3b8"),
            ("✕", self.close,         "#ef4444"),
        ]:
            btn = _TitleBarButton(text, color)
            btn.clicked.connect(slot)
            lay.addWidget(btn)
            lay.addSpacing(4)

        # Make draggable
        bar.mousePressEvent   = self._drag_start
        bar.mouseMoveEvent    = self._drag_move
        bar.mouseReleaseEvent = self._drag_end
        return bar

    # ── Drag to move ──────────────────────────────────────────────────────────
    def _drag_start(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _drag_move(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def _drag_end(self, e):
        self._drag_pos = QPoint()

    # ── Page navigation ───────────────────────────────────────────────────────
    def _go_to(self, index: int):
        self._current_step = index
        self._stack.setCurrentIndex(index)
        self._step_bar.set_step(index)

    def _open_download_page(self, version_data: dict):
        self._page_download.set_version(version_data)
        self._go_to(self._IDX["download"])

    def _on_download_complete(self, iso_path: str):
        """Called when DownloadPage finishes — store ISO and continue to options."""
        self._downloaded_iso = iso_path
        self._go_to(self._IDX["options"])

    def _start_install(self):
        # Use downloaded ISO if available, otherwise use manually selected
        iso = getattr(self, "_downloaded_iso", None) or self._page_usb.iso_path
        usb = self._page_usb.selected_drive
        bypasses = self._page_options.bypass_options

        if not iso or not usb:
            return

        self._go_to(self._IDX["progress"])
        self._page_progress.start_install(
            iso_path=iso,
            usb_path=usb.path,
            bypass_options=bypasses,
        )


class _TitleBarButton(QPushButton):
    def __init__(self, text: str, hover_color: str, parent=None):
        super().__init__(text, parent)
        self._hover_color = QColor(hover_color)
        self._hovered = False
        self.setFixedSize(28, 28)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        font = QFont("Segoe UI", 11)
        self.setFont(font)

    def enterEvent(self, e):
        self._hovered = True
        self.update()

    def leaveEvent(self, e):
        self._hovered = False
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._hovered:
            path = QPainterPath()
            path.addEllipse(2, 2, 24, 24)
            c = QColor(self._hover_color)
            c.setAlpha(40)
            p.fillPath(path, QBrush(c))
        p.setPen(QColor(255, 255, 255, 160) if not self._hovered else self._hover_color)
        p.setFont(self.font())
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())
