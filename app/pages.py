"""All wizard pages for WinFlash Pro."""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFileDialog, QFrame, QSizePolicy, QSpacerItem, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot, QSize, QMetaObject, Q_ARG
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QBrush, QPen, QLinearGradient

from app.widgets import (
    GlassPanel, GlassCard, GlowButton, ToggleSwitch, ProgressRing,
    C_TEXT, C_TEXT_MUTED, C_ACCENT1, C_ACCENT2, C_SUCCESS, C_BORDER
)
from core.windows_db import WINDOWS_VERSIONS, BYPASS_OPTIONS
from core.usb import USBDrive, detect_usb_drives, generate_bios_guide


def label(text, size=13, bold=False, muted=False, parent=None):
    lbl = QLabel(text, parent)
    weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
    lbl.setFont(QFont("Segoe UI", size, weight))
    color = "#64748b" if muted else "#f1f5f9"
    lbl.setStyleSheet(f"color: {color}; background: transparent;")
    lbl.setWordWrap(True)
    return lbl


# ── PAGE 1: Welcome ───────────────────────────────────────────────────────────
class WelcomePage(QWidget):
    next_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(60, 50, 60, 50)
        lay.setSpacing(0)

        title_widget = _GradientTitle("⚡  WinFlash Pro", self)
        lay.addWidget(title_widget, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addSpacing(10)

        sub = label("Автоматическое создание загрузочной флешки с Windows", 14, muted=True)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)
        lay.addSpacing(40)

        # Feature cards row
        features = [
            ("🔍", "Авто-поиск\nUSB флешки"),
            ("🪟", "Выбор версии\nWindows"),
            ("🛡️", "Обход\nTPM / Secure Boot"),
            ("🚀", "Полная\nавтоматизация"),
        ]
        feat_row = QHBoxLayout()
        feat_row.setSpacing(12)
        for icon, text in features:
            card = GlassCard(self, radius=12)
            card_lay = QVBoxLayout(card)
            card_lay.setContentsMargins(16, 16, 16, 16)
            card_lay.setSpacing(6)
            icon_lbl = QLabel(icon)
            icon_lbl.setFont(QFont("Segoe UI Emoji", 22))
            icon_lbl.setStyleSheet("background: transparent;")
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_lay.addWidget(icon_lbl)
            txt = label(text, 10, muted=True)
            txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_lay.addWidget(txt)
            card.setFixedSize(140, 100)
            feat_row.addWidget(card)
        lay.addLayout(feat_row)
        lay.addSpacing(50)

        btn = GlowButton("  Начать работу  →", self, primary=True)
        btn.setFixedWidth(260)
        btn.clicked.connect(self.next_clicked)
        lay.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addSpacing(20)
        hint = label("Windows 10 / 11 · GPT/MBR · UEFI/Legacy · Обход TPM", 9, muted=True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)
        lay.addStretch()

class _GradientTitle(QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self._text = text
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedHeight(60)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        font = QFont("Segoe UI", 30, QFont.Weight.Bold)
        from PyQt6.QtGui import QFontMetrics
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self._text)
        text_h = fm.height()
        x = (self.width() - text_w) / 2
        y = (self.height() + text_h) / 2 - fm.descent()

        text_path = QPainterPath()
        text_path.addText(x, y, font, self._text)

        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0, QColor(99, 102, 241))
        g.setColorAt(0.5, QColor(168, 85, 247))
        g.setColorAt(1, QColor(6, 182, 212))

        p.setClipPath(text_path)
        p.fillRect(self.rect(), QBrush(g))


# ── PAGE 2: USB Selection ─────────────────────────────────────────────────────
class USBSelectPage(QWidget):
    next_clicked = pyqtSignal()
    back_clicked = pyqtSignal()
    usb_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drives = []
        self._selected_drive = None
        self._setup_ui()
        self.refresh_drives()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(48, 36, 48, 36)
        lay.setSpacing(0)

        hdr = QHBoxLayout()
        hdr.addWidget(label("💾  Выберите USB флешку", 18, bold=True))
        hdr.addStretch()
        refresh_btn = GlowButton("⟳  Обновить", self, primary=False, small=True)
        refresh_btn.setFixedWidth(120)
        refresh_btn.clicked.connect(self.refresh_drives)
        hdr.addWidget(refresh_btn)
        lay.addLayout(hdr)
        lay.addSpacing(6)
        lay.addWidget(label("Вставьте флешку (минимум 8 ГБ) и нажмите Обновить", 11, muted=True))
        lay.addSpacing(20)

        # Drive list area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_container = QWidget()
        self._list_container.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setSpacing(10)
        self._list_layout.setContentsMargins(0, 0, 8, 0)
        scroll.setWidget(self._list_container)
        lay.addWidget(scroll, 1)
        lay.addSpacing(20)

        nav = QHBoxLayout()
        self._back_btn = GlowButton("← Назад", self, primary=False)
        self._back_btn.setFixedWidth(140)
        self._back_btn.clicked.connect(self.back_clicked)
        nav.addWidget(self._back_btn)
        nav.addStretch()
        self._next_btn = GlowButton("Далее →", self, primary=True)
        self._next_btn.setFixedWidth(160)
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(self._on_next)
        nav.addWidget(self._next_btn)
        lay.addLayout(nav)

    def refresh_drives(self):
        # Clear existing
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._drives = detect_usb_drives()
        if not self._drives:
            empty = GlassPanel(self._list_container, radius=12)
            empty_lay = QVBoxLayout(empty)
            empty_lay.setContentsMargins(20, 30, 20, 30)
            empty_lay.addWidget(label("🔌  USB флешки не найдены", 13, bold=True), 0, Qt.AlignmentFlag.AlignCenter)
            empty_lay.addWidget(label("Вставьте флешку и нажмите «Обновить»", 10, muted=True), 0, Qt.AlignmentFlag.AlignCenter)
            self._list_layout.addWidget(empty)
        else:
            for drive in self._drives:
                card = _DriveCard(drive, self._list_container)
                card.clicked.connect(lambda d=drive, c=card: self._select_drive(d, c))
                self._list_layout.addWidget(card)
        self._list_layout.addStretch()
        self._selected_drive = None
        self._check_next()

    def _select_drive(self, drive: USBDrive, card: "GlassCard"):
        self._selected_drive = drive
        for i in range(self._list_layout.count()):
            w = self._list_layout.itemAt(i).widget()
            if isinstance(w, _DriveCard):
                w.selected = (w.drive == drive)
        self.usb_selected.emit(drive)
        self._check_next()

    def _check_next(self):
        self._next_btn.setEnabled(self._selected_drive is not None)

    def _on_next(self):
        self.next_clicked.emit()

    @property
    def selected_drive(self):
        return self._selected_drive


class _DriveCard(GlassCard):
    def __init__(self, drive: USBDrive, parent=None):
        super().__init__(parent)
        self.drive = drive
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(14)

        icon = QLabel("🔌")
        icon.setFont(QFont("Segoe UI Emoji", 24))
        icon.setStyleSheet("background: transparent;")
        icon.setFixedWidth(36)
        lay.addWidget(icon)

        info_lay = QVBoxLayout()
        info_lay.setSpacing(2)
        name_lbl = label(f"{drive.display_name}  [{drive.path}]", 12, bold=True)
        info_lay.addWidget(name_lbl)
        detail = label(f"{drive.size_str}  ·  {drive.filesystem}", 10, muted=True)
        info_lay.addWidget(detail)
        lay.addLayout(info_lay, 1)

        # Size indicator bar
        pct = min(1.0, drive.size_gb / 64.0)
        size_bar = _MiniBar(pct, parent=self)
        size_bar.setFixedWidth(80)
        lay.addWidget(size_bar)

        self.setFixedHeight(72)


class _MiniBar(QWidget):
    def __init__(self, fill=0.5, parent=None):
        super().__init__(parent)
        self.fill = fill
        self.setFixedHeight(6)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 20)))
        p.drawRoundedRect(0, 0, self.width(), self.height(), 3, 3)
        g = QLinearGradient(0, 0, self.width() * self.fill, 0)
        g.setColorAt(0, QColor(99, 102, 241))
        g.setColorAt(1, QColor(6, 182, 212))
        p.setBrush(QBrush(g))
        p.drawRoundedRect(0, 0, int(self.width() * self.fill), self.height(), 3, 3)


# ── PAGE 3: Windows Selection ─────────────────────────────────────────────────
class WindowsSelectPage(QWidget):
    next_clicked = pyqtSignal()
    back_clicked = pyqtSignal()
    version_selected = pyqtSignal(dict)
    download_clicked = pyqtSignal(dict)   # emitted when auto-download is requested

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._selected = None
        self._cards = {}
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(48, 36, 48, 36)
        lay.setSpacing(0)

        lay.addWidget(label("🪟  Выберите версию Windows", 18, bold=True))
        lay.addSpacing(4)
        lay.addWidget(label("Нажмите на карточку для выбора версии", 11, muted=True))
        lay.addSpacing(20)

        # Grid of version cards (2 per row)
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: transparent;")
        grid_lay = QVBoxLayout(grid_widget)
        grid_lay.setSpacing(10)
        grid_lay.setContentsMargins(0, 0, 0, 0)

        for i in range(0, len(WINDOWS_VERSIONS), 2):
            row = QHBoxLayout()
            row.setSpacing(10)
            for win in WINDOWS_VERSIONS[i:i+2]:
                card = _WinCard(win, self)
                card.clicked.connect(lambda w=win, c=card: self._select(w, c))
                self._cards[win["id"]] = card
                row.addWidget(card)
            if len(WINDOWS_VERSIONS[i:i+2]) == 1:
                row.addStretch()
            grid_lay.addLayout(row)

        lay.addWidget(grid_widget, 1)
        lay.addSpacing(20)

        # Info hint panel
        dl_panel = GlassPanel(self, radius=10)
        dl_lay = QHBoxLayout(dl_panel)
        dl_lay.setContentsMargins(16, 10, 16, 10)
        dl_lay.addWidget(label(
            "💡  Выберите версию Windows и нажмите «Скачать и записать» — "
            "файл загрузится напрямую с серверов Microsoft (~5 ГБ).",
            10, muted=True
        ), 1)
        lay.addWidget(dl_panel)
        lay.addSpacing(16)

        self._iso_path = None

        nav = QHBoxLayout()
        back = GlowButton("← Назад", self, primary=False)
        back.setFixedWidth(130)
        back.clicked.connect(self.back_clicked)
        nav.addWidget(back)
        nav.addStretch()
        # Secondary: user already has a file
        self._next_btn = GlowButton("📁  У меня есть файл...", self, primary=False)
        self._next_btn.setFixedWidth(210)
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(self._pick_and_proceed)
        nav.addWidget(self._next_btn)
        nav.addSpacing(8)
        # Primary: auto-download
        self._dl_btn = GlowButton("⬇  Скачать и записать", self, primary=True)
        self._dl_btn.setFixedWidth(220)
        self._dl_btn.setEnabled(False)
        self._dl_btn.clicked.connect(self._on_download)
        nav.addWidget(self._dl_btn)
        lay.addLayout(nav)

    def _select(self, win_version: dict, card: "_WinCard"):
        self._selected = win_version
        for cid, c in self._cards.items():
            c.selected = (cid == win_version["id"])
        self.version_selected.emit(win_version)
        self._dl_btn.setEnabled(True)
        self._next_btn.setEnabled(True)

    def _on_download(self):
        if self._selected:
            self.download_clicked.emit(self._selected)

    def _pick_and_proceed(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл установки Windows", "",
            "Файлы установки Windows (*.iso);;Все файлы (*)"
        )
        if path:
            self._iso_path = path
            self.next_clicked.emit()

    @property
    def selected_version(self):
        return self._selected

    @property
    def iso_path(self):
        return self._iso_path


class _WinCard(GlassCard):
    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.data = data
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.addWidget(label(data["name"], 13, bold=True))
        top_row.addStretch()
        if data.get("recommended"):
            rec = QLabel("★ Рекомендуем")
            rec.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            rec.setStyleSheet(
                "color: #0a0f1e; background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 #6366f1,stop:1 #06b6d4); padding: 2px 8px; border-radius: 8px;"
            )
            top_row.addWidget(rec)
        lay.addLayout(top_row)

        ver = label(f"Версия {data['version']}  ·  Build {data['build']}  ·  {data['size_gb']} ГБ", 9, muted=True)
        lay.addWidget(ver)
        lay.addSpacing(8)

        feat_lay = QHBoxLayout()
        feat_lay.setSpacing(6)
        for feat in data["features"][:3]:
            badge = QLabel(feat)
            badge.setFont(QFont("Segoe UI", 8))
            badge.setStyleSheet(
                "color: #94a3b8; background: rgba(255,255,255,15);"
                "padding: 2px 8px; border-radius: 6px; border: 1px solid rgba(255,255,255,30);"
            )
            feat_lay.addWidget(badge)
        feat_lay.addStretch()
        lay.addLayout(feat_lay)
        self.setMinimumHeight(110)


# ── PAGE 4: Options ───────────────────────────────────────────────────────────
class OptionsPage(QWidget):
    next_clicked = pyqtSignal()
    back_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._toggles = {}
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(48, 36, 48, 36)
        lay.setSpacing(0)

        lay.addWidget(label("🛡️  Настройки и обходы", 18, bold=True))
        lay.addSpacing(4)
        lay.addWidget(label("Настройте параметры перед записью флешки", 11, muted=True))
        lay.addSpacing(22)

        # Bypass options section
        bypass_panel = GlassPanel(self, radius=14)
        bypass_lay = QVBoxLayout(bypass_panel)
        bypass_lay.setContentsMargins(20, 16, 20, 16)
        bypass_lay.setSpacing(0)
        bypass_lay.addWidget(label("Обход требований Windows 11", 12, bold=True))
        bypass_lay.addSpacing(4)
        bypass_lay.addWidget(label(
            "Позволяет установить Windows 11 на ПК без TPM 2.0 и Secure Boot",
            10, muted=True
        ))
        bypass_lay.addSpacing(14)

        for opt in BYPASS_OPTIONS:
            row = QHBoxLayout()
            row.setSpacing(14)
            info_lay = QVBoxLayout()
            info_lay.setSpacing(2)
            info_lay.addWidget(label(opt["name"], 11, bold=True))
            info_lay.addWidget(label(opt["description"], 9, muted=True))
            row.addLayout(info_lay, 1)
            toggle = ToggleSwitch(opt["default"])
            self._toggles[opt["id"]] = toggle
            row.addWidget(toggle, 0, Qt.AlignmentFlag.AlignVCenter)
            bypass_lay.addLayout(row)
            bypass_lay.addSpacing(12)

        lay.addWidget(bypass_panel)
        lay.addSpacing(14)

        # Partition scheme
        scheme_panel = GlassPanel(self, radius=14)
        scheme_lay = QVBoxLayout(scheme_panel)
        scheme_lay.setContentsMargins(20, 16, 20, 16)
        scheme_lay.setSpacing(8)
        scheme_lay.addWidget(label("Схема разделов", 12, bold=True))
        scheme_lay.addWidget(label("GPT — для UEFI (современные ПК)  ·  MBR — для legacy BIOS (старые ПК)", 9, muted=True))
        scheme_row = QHBoxLayout()
        scheme_row.setSpacing(10)
        self._gpt_btn = GlowButton("GPT  (рекомендуется)", self, primary=True, small=True)
        self._mbr_btn = GlowButton("MBR  (legacy)", self, primary=False, small=True)
        self._gpt_btn.clicked.connect(lambda: self._set_scheme("GPT"))
        self._mbr_btn.clicked.connect(lambda: self._set_scheme("MBR"))
        scheme_row.addWidget(self._gpt_btn)
        scheme_row.addWidget(self._mbr_btn)
        scheme_row.addStretch()
        scheme_lay.addLayout(scheme_row)
        lay.addWidget(scheme_panel)
        self._scheme = "GPT"
        lay.addSpacing(14)

        # BIOS guide hint
        bios_panel = GlassPanel(self, radius=14)
        bios_lay = QHBoxLayout(bios_panel)
        bios_lay.setContentsMargins(16, 12, 16, 12)
        bios_lay.addWidget(label("📖  Посмотреть инструкцию по входу в BIOS и загрузке с USB", 10), 1)
        guide_btn = GlowButton("Показать гайд", self, primary=False, small=True)
        guide_btn.setFixedWidth(140)
        guide_btn.clicked.connect(self._show_bios_guide)
        bios_lay.addWidget(guide_btn)
        lay.addWidget(bios_panel)
        lay.addStretch()

        nav = QHBoxLayout()
        back = GlowButton("← Назад", self, primary=False)
        back.setFixedWidth(140)
        back.clicked.connect(self.back_clicked)
        nav.addWidget(back)
        nav.addStretch()
        nxt = GlowButton("Записать USB  →", self, primary=True)
        nxt.setFixedWidth(200)
        nxt.clicked.connect(self.next_clicked)
        nav.addWidget(nxt)
        lay.addLayout(nav)

    def _set_scheme(self, scheme):
        self._scheme = scheme
        self._gpt_btn._primary = (scheme == "GPT")
        self._mbr_btn._primary = (scheme == "MBR")
        self._gpt_btn.update()
        self._mbr_btn.update()

    def _show_bios_guide(self):
        dlg = _GuideDialog(generate_bios_guide(), parent=self.window())
        dlg.exec()

    @property
    def bypass_options(self):
        return {k: t.checked for k, t in self._toggles.items()}

    @property
    def partition_scheme(self):
        return self._scheme


# ── PAGE 5: Progress ──────────────────────────────────────────────────────────
class ProgressPage(QWidget):
    done_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(48, 36, 48, 36)
        lay.setSpacing(0)

        lay.addWidget(label("🚀  Запись загрузочной флешки", 18, bold=True))
        lay.addSpacing(4)
        self._status_top = label("Подготовка...", 11, muted=True)
        lay.addWidget(self._status_top)
        lay.addSpacing(30)

        center = QHBoxLayout()
        center.setSpacing(40)

        # Progress ring
        self._ring = ProgressRing(self)
        center.addWidget(self._ring, 0, Qt.AlignmentFlag.AlignVCenter)

        # Log
        log_col = QVBoxLayout()
        log_col.setSpacing(8)
        log_col.addWidget(label("Лог операций:", 10, bold=True))
        self._log = QTextEdit(self)
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(180)
        self._log.setStyleSheet(
            "QTextEdit { background: rgba(0,0,0,89); color: #94a3b8; "
            "border: 1px solid rgba(255,255,255,25); border-radius: 10px; "
            "padding: 10px; font-family: 'Consolas', monospace; font-size: 10px; }"
        )
        log_col.addWidget(self._log)
        center.addLayout(log_col, 1)
        lay.addLayout(center, 1)
        lay.addSpacing(24)

        # Steps list
        self._steps_panel = GlassPanel(self, radius=12)
        steps_lay = QHBoxLayout(self._steps_panel)
        steps_lay.setContentsMargins(16, 10, 16, 10)
        steps_lay.setSpacing(0)
        self._step_labels = []
        steps_text = [
            "Форматирование", "Монтирование ISO",
            "Копирование файлов", "Применение обходов", "Финализация"
        ]
        for i, s in enumerate(steps_text):
            lbl = label(f"{'✓' if False else '○'}  {s}", 9, muted=True)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._step_labels.append((lbl, s))
            steps_lay.addWidget(lbl, 1)
        lay.addWidget(self._steps_panel)
        lay.addSpacing(20)

        self._cancel_btn = GlowButton("Отменить", self, primary=False)
        self._cancel_btn.setFixedWidth(140)
        self._done_btn = GlowButton("🎉  Готово!", self, primary=True)
        self._done_btn.setFixedWidth(200)
        self._done_btn.setVisible(False)
        self._done_btn.clicked.connect(self.done_clicked)

        nav = QHBoxLayout()
        nav.addWidget(self._cancel_btn)
        nav.addStretch()
        nav.addWidget(self._done_btn)
        lay.addLayout(nav)

    def start_install(self, iso_path: str, usb_path: str, bypass_options: dict):
        from core.installer import InstallWorker

        self._ring.set_value(0)
        self._log.clear()
        self._done_btn.setVisible(False)
        self._cancel_btn.setVisible(True)

        self._worker = InstallWorker(
            iso_path=iso_path,
            usb_path=usb_path,
            bypass_options=bypass_options,
            on_progress=self._on_progress,
            on_done=self._on_done,
        )
        self._cancel_btn.clicked.connect(self._worker.cancel)
        self._worker.start()

    def _on_progress(self, pct: int, msg: str):
        from PyQt6.QtCore import QMetaObject, Q_ARG
        QMetaObject.invokeMethod(
            self, "_update_progress",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, pct),
            Q_ARG(str, msg),
        )

    @pyqtSlot(int, str)
    def _update_progress(self, pct: int, msg: str):
        self._ring.set_value(pct)
        self._status_top.setText(msg)
        self._log.append(f"[{pct:3d}%]  {msg}")
        # Update step indicators
        thresholds = [20, 35, 75, 90, 100]
        for i, (lbl, s) in enumerate(self._step_labels):
            if pct >= thresholds[i]:
                lbl.setText(f"✅  {s}")
                lbl.setStyleSheet("color: #10b981; background: transparent;")
            elif pct >= (thresholds[i - 1] if i > 0 else 0):
                lbl.setText(f"⚙️  {s}")
                lbl.setStyleSheet("color: #6366f1; background: transparent;")

    def _on_done(self, success: bool, message: str):
        from PyQt6.QtCore import QMetaObject, Q_ARG
        QMetaObject.invokeMethod(
            self, "_finish",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(bool, success),
            Q_ARG(str, message),
        )

    @pyqtSlot(bool, str)
    def _finish(self, success: bool, message: str):
        if success:
            self._ring.set_value(100)
            self._status_top.setText(message)
            self._log.append(f"\n✅  {message}")
            self._cancel_btn.setVisible(False)
            self._done_btn.setVisible(True)
        else:
            self._status_top.setText(f"Ошибка: {message}")
            self._log.append(f"\n❌  Ошибка: {message}")
            self._cancel_btn.setText("Закрыть")


# ── PAGE 6: Done ──────────────────────────────────────────────────────────────
class DonePage(QWidget):
    restart_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(60, 50, 60, 50)
        lay.setSpacing(0)

        # Big checkmark
        check = QLabel("✅")
        check.setFont(QFont("Segoe UI Emoji", 56))
        check.setStyleSheet("background: transparent;")
        check.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(check)
        lay.addSpacing(16)

        lay.addWidget(label("Флешка успешно создана!", 22, bold=True), 0, Qt.AlignmentFlag.AlignCenter)
        lay.addSpacing(8)
        lay.addWidget(label("Следуйте инструкции ниже для установки Windows", 12, muted=True), 0, Qt.AlignmentFlag.AlignCenter)
        lay.addSpacing(28)

        # Steps
        steps = [
            ("1", "Не вытаскивайте флешку — она готова к использованию"),
            ("2", "Перезагрузите компьютер, на который хотите поставить Windows"),
            ("3", "При загрузке нажмите F12 (или Del) для Boot Menu"),
            ("4", "Выберите USB флешку в списке загрузки"),
            ("5", "Следуйте инструкциям установщика Windows"),
        ]
        for num, text in steps:
            row = QHBoxLayout()
            row.setSpacing(14)
            num_lbl = QLabel(num)
            num_lbl.setFixedSize(28, 28)
            num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            num_lbl.setStyleSheet(
                "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                "stop:0 #6366f1,stop:1 #06b6d4);"
                "color: white; border-radius: 14px;"
            )
            row.addWidget(num_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(label(text, 11), 1)
            lay.addLayout(row)
            lay.addSpacing(8)

        lay.addStretch()

        nav = QHBoxLayout()
        nav.addStretch()
        restart = GlowButton("Создать ещё одну флешку", self, primary=False)
        restart.setFixedWidth(240)
        restart.clicked.connect(self.restart_clicked)
        nav.addWidget(restart)
        nav.addStretch()
        lay.addLayout(nav)


# ── PAGE: Auto-Download via UUP Dump ─────────────────────────────────────────
class DownloadPage(QWidget):
    """
    Downloads Windows ISO automatically via UUP Dump
    (files come directly from Microsoft CDN — 100% legitimate).
    Emits iso_ready with the path when done, or skip_to_iso to go back.
    """
    iso_ready    = pyqtSignal(str)   # path to downloaded .iso
    back_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._worker = None
        self._iso_path = ""
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(48, 36, 48, 36)
        lay.setSpacing(0)

        # Header
        lay.addWidget(label("⬇  Скачать Windows автоматически", 18, bold=True))
        lay.addSpacing(4)
        self._subtitle = label(
            "Файлы скачиваются напрямую с серверов Microsoft через сервис UUP Dump",
            11, muted=True
        )
        lay.addWidget(self._subtitle)
        lay.addSpacing(24)

        # Info panel about UUP Dump
        info_panel = GlassPanel(self, radius=12)
        info_lay = QHBoxLayout(info_panel)
        info_lay.setContentsMargins(16, 12, 16, 12)
        info_lay.setSpacing(14)
        info_icon = QLabel("🔒")
        info_icon.setFont(QFont("Segoe UI Emoji", 20))
        info_icon.setStyleSheet("background: transparent;")
        info_lay.addWidget(info_icon)
        txt_lay = QVBoxLayout()
        txt_lay.setSpacing(2)
        txt_lay.addWidget(label("Безопасная загрузка через UUP Dump", 11, bold=True))
        txt_lay.addWidget(label(
            "UUP Dump — официальный инструмент, качает файлы обновлений Windows "
            "напрямую с CDN Microsoft и собирает ISO локально на вашем ПК.",
            9, muted=True
        ))
        info_lay.addLayout(txt_lay, 1)
        lay.addWidget(info_panel)
        lay.addSpacing(20)

        # Selected version display
        self._ver_panel = GlassPanel(self, radius=12)
        ver_lay = QHBoxLayout(self._ver_panel)
        ver_lay.setContentsMargins(18, 14, 18, 14)
        self._ver_icon = QLabel("🪟")
        self._ver_icon.setFont(QFont("Segoe UI Emoji", 24))
        self._ver_icon.setStyleSheet("background: transparent;")
        ver_lay.addWidget(self._ver_icon)
        vinfo = QVBoxLayout()
        vinfo.setSpacing(2)
        self._ver_name = label("Windows 11 Pro", 14, bold=True)
        self._ver_detail = label("Версия 24H2  ·  ~5.4 ГБ  ·  Русский язык", 10, muted=True)
        vinfo.addWidget(self._ver_name)
        vinfo.addWidget(self._ver_detail)
        ver_lay.addLayout(vinfo, 1)
        lay.addWidget(self._ver_panel)
        lay.addSpacing(24)

        # Progress area
        prog_panel = GlassPanel(self, radius=14)
        prog_lay = QVBoxLayout(prog_panel)
        prog_lay.setContentsMargins(20, 18, 20, 18)
        prog_lay.setSpacing(10)

        # Status row
        status_row = QHBoxLayout()
        self._status_lbl = label("Нажмите «Начать загрузку»", 11)
        status_row.addWidget(self._status_lbl, 1)
        self._speed_lbl = label("", 10, muted=True)
        status_row.addWidget(self._speed_lbl)
        prog_lay.addLayout(status_row)

        # Progress bar
        self._prog_bar = _ProgressBar(self)
        prog_lay.addWidget(self._prog_bar)

        # Percentage + ETA row
        pct_row = QHBoxLayout()
        self._pct_lbl = label("0%", 11, bold=True)
        pct_row.addWidget(self._pct_lbl)
        pct_row.addStretch()
        self._phase_lbl = label("", 9, muted=True)
        pct_row.addWidget(self._phase_lbl)
        prog_lay.addLayout(pct_row)

        # Log
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(130)
        self._log.setStyleSheet(
            "QTextEdit { background: rgba(0,0,0,76); color: #64748b; "
            "border: 1px solid rgba(255,255,255,15); border-radius: 8px; "
            "padding: 8px; font-family: 'Consolas', monospace; font-size: 9px; }"
        )
        prog_lay.addWidget(self._log)
        lay.addWidget(prog_panel, 1)
        lay.addSpacing(20)

        # Navigation
        nav = QHBoxLayout()
        self._back_btn = GlowButton("← Назад", self, primary=False)
        self._back_btn.setFixedWidth(130)
        self._back_btn.clicked.connect(self.back_clicked)
        nav.addWidget(self._back_btn)
        nav.addStretch()
        self._start_btn = GlowButton("⬇  Начать загрузку", self, primary=True)
        self._start_btn.setFixedWidth(200)
        self._start_btn.clicked.connect(self._start_download)
        nav.addWidget(self._start_btn)
        nav.addSpacing(8)
        self._continue_btn = GlowButton("Записать на USB →", self, primary=True)
        self._continue_btn.setFixedWidth(200)
        self._continue_btn.setVisible(False)
        self._continue_btn.clicked.connect(self._on_continue)
        nav.addWidget(self._continue_btn)
        lay.addLayout(nav)

    def set_version(self, version_data: dict):
        """Update the displayed Windows version before showing this page."""
        from core.downloader import estimated_download_gb
        self._version_data = version_data
        self._ver_name.setText(version_data["name"])
        size = estimated_download_gb(version_data["id"])
        self._ver_detail.setText(
            f"Версия {version_data['version']}  ·  ~{size:.1f} ГБ  ·  Русский язык"
        )
        self._prog_bar.set_value(0)
        self._pct_lbl.setText("0%")
        self._status_lbl.setText("Нажмите «Начать загрузку»")
        self._log.clear()
        self._start_btn.setVisible(True)
        self._continue_btn.setVisible(False)
        self._iso_path = ""

    def _start_download(self):
        import tempfile, os
        from core.downloader import DownloadWorker

        self._start_btn.setEnabled(False)
        self._back_btn.setEnabled(False)

        out_dir = os.path.join(tempfile.gettempdir(), "winflash_downloads")
        os.makedirs(out_dir, exist_ok=True)

        self._worker = DownloadWorker(
            version_id=self._version_data["id"],
            output_dir=out_dir,
            on_progress=self._on_progress,
            on_done=self._on_done,
        )
        self._log.append("▶  Запуск загрузки через UUP Dump...")
        self._log.append(f"   Папка: {out_dir}")
        self._worker.start()

    def _on_progress(self, pct: int, msg: str):
        QMetaObject.invokeMethod(
            self, "_update_ui",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, pct),
            Q_ARG(str, msg),
        )

    @pyqtSlot(int, str)
    def _update_ui(self, pct: int, msg: str):
        self._prog_bar.set_value(pct)
        self._pct_lbl.setText(f"{pct}%")
        self._status_lbl.setText(msg)
        self._log.append(f"[{pct:3d}%]  {msg}")
        # Auto-scroll log
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())
        # Phase hint
        if pct < 12:
            self._phase_lbl.setText("🔍 Поиск сборки")
        elif pct < 78:
            self._phase_lbl.setText("📥 Загрузка с Microsoft CDN")
        else:
            self._phase_lbl.setText("🔧 Сборка ISO образа")

    def _on_done(self, success: bool, message: str, iso_path: str):
        QMetaObject.invokeMethod(
            self, "_finish",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(bool, success),
            Q_ARG(str, message),
            Q_ARG(str, iso_path),
        )

    @pyqtSlot(bool, str, str)
    def _finish(self, success: bool, message: str, iso_path: str):
        self._back_btn.setEnabled(True)
        if success:
            self._iso_path = iso_path
            self._prog_bar.set_value(100)
            self._pct_lbl.setText("100%")
            self._status_lbl.setText(f"✅  {message}")
            self._phase_lbl.setText("✅ Готово!")
            self._log.append(f"\n✅  ISO сохранён: {iso_path}")
            self._start_btn.setVisible(False)
            self._continue_btn.setVisible(True)
        else:
            self._status_lbl.setText(f"❌  Ошибка")
            self._log.append(f"\n❌  {message}")
            self._start_btn.setEnabled(True)
            self._start_btn.setText("↺  Повторить")

    def _on_continue(self):
        if self._iso_path:
            self.iso_ready.emit(self._iso_path)


class _ProgressBar(QWidget):
    """Thin gradient progress bar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self.setFixedHeight(8)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_value(self, v: int):
        self._value = max(0, min(100, v))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        # Track
        p.setBrush(QBrush(QColor(255, 255, 255, 18)))
        p.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)
        # Fill
        if self._value > 0:
            fill_w = int(self.width() * self._value / 100)
            g = QLinearGradient(0, 0, fill_w, 0)
            g.setColorAt(0, QColor(99, 102, 241))
            if self._value > 50:
                t = (self._value - 50) / 50.0
                g.setColorAt(1, QColor(
                    int(99  + (6  - 99)  * t),
                    int(102 + (182 - 102) * t),
                    int(241 + (212 - 241) * t),
                ))
            else:
                g.setColorAt(1, QColor(168, 85, 247))
            p.setBrush(QBrush(g))
            p.drawRoundedRect(0, 0, fill_w, self.height(), 4, 4)


# ── BIOS Guide dialog ─────────────────────────────────────────────────────────
class _GuideDialog:
    def __init__(self, text: str, parent=None):
        self._text = text
        self._parent = parent

    def exec(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
        dlg = QDialog(self._parent)
        dlg.setWindowTitle("Инструкция по загрузке с USB")
        dlg.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        dlg.setFixedSize(520, 420)

        outer = QWidget(dlg)
        outer.setGeometry(0, 0, 520, 420)
        outer.setStyleSheet(
            "background: rgba(13,17,35,247); border-radius: 16px; "
            "border: 1px solid rgba(255,255,255,30);"
        )
        lay = QVBoxLayout(outer)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)
        lay.addWidget(label("📖  Как загрузиться с USB флешки", 14, bold=True))

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(self._text)
        txt.setStyleSheet(
            "background: rgba(0,0,0,76); color: #cbd5e1; border: 1px solid rgba(255,255,255,20);"
            "border-radius: 10px; padding: 12px; font-family: 'Consolas', monospace; font-size: 11px;"
        )
        lay.addWidget(txt, 1)

        close_btn = GlowButton("Закрыть", outer, primary=False, small=True)
        close_btn.setFixedWidth(120)
        close_btn.clicked.connect(dlg.accept)
        lay.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignCenter)

        dlg.exec()
