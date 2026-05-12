"""Reusable glassmorphism widgets for WinFlash Pro."""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QRect, QSize
from PyQt6.QtGui import (
    QPainter, QColor, QLinearGradient, QPen, QBrush, QPainterPath,
    QFont, QFontMetrics, QRadialGradient
)


# ── Colour palette ──────────────────────────────────────────────────────────
C_BG         = QColor(10,  14,  26,  255)
C_GLASS      = QColor(255, 255, 255, 12)
C_GLASS_HVR  = QColor(255, 255, 255, 22)
C_BORDER     = QColor(255, 255, 255, 35)
C_BORDER_HVR = QColor(255, 255, 255, 80)
C_ACCENT1    = QColor(99,  102, 241)   # indigo
C_ACCENT2    = QColor(6,   182, 212)   # cyan
C_SUCCESS    = QColor(16,  185, 129)   # emerald
C_WARN       = QColor(245, 158, 11)    # amber
C_DANGER     = QColor(239, 68,  68)    # red
C_TEXT       = QColor(241, 245, 249)
C_TEXT_MUTED = QColor(100, 116, 139)


def shadow(blur=30, color=QColor(0, 0, 0, 120), x=0, y=8):
    eff = QGraphicsDropShadowEffect()
    eff.setBlurRadius(blur)
    eff.setColor(color)
    eff.setOffset(x, y)
    return eff


def glow(color: QColor = None, blur=40):
    color = color or C_ACCENT1
    c = QColor(color)
    c.setAlpha(80)
    return shadow(blur, c, 0, 0)


# ── GlassPanel ───────────────────────────────────────────────────────────────
class GlassPanel(QWidget):
    """Frosted-glass card with optional glow border."""

    def __init__(self, parent=None, radius=16, border_color=None):
        super().__init__(parent)
        self.radius = radius
        self.border_color = border_color or C_BORDER
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        path = QPainterPath()
        path.addRoundedRect(r.x(), r.y(), r.width(), r.height(), self.radius, self.radius)
        p.fillPath(path, QBrush(C_GLASS))
        p.setPen(QPen(self.border_color, 1))
        p.drawPath(path)


# ── GlassCard — selectable card ──────────────────────────────────────────────
class GlassCard(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None, radius=14):
        super().__init__(parent)
        self.radius = radius
        self._selected = False
        self._hovered = False
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setGraphicsEffect(shadow(20))

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, val: bool):
        self._selected = val
        self.update()
        if val:
            self.setGraphicsEffect(glow(C_ACCENT1, 50))
        else:
            self.setGraphicsEffect(shadow(20))

    def enterEvent(self, e):
        self._hovered = True
        self.update()

    def leaveEvent(self, e):
        self._hovered = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        path = QPainterPath()
        path.addRoundedRect(r.x(), r.y(), r.width(), r.height(), self.radius, self.radius)

        if self._selected:
            bg = QLinearGradient(0, 0, r.width(), r.height())
            bg.setColorAt(0, QColor(99, 102, 241, 40))
            bg.setColorAt(1, QColor(6, 182, 212, 25))
            p.fillPath(path, QBrush(bg))
            border = C_ACCENT1
            p.setPen(QPen(border, 1.5))
        elif self._hovered:
            p.fillPath(path, QBrush(C_GLASS_HVR))
            p.setPen(QPen(C_BORDER_HVR, 1))
        else:
            p.fillPath(path, QBrush(C_GLASS))
            p.setPen(QPen(C_BORDER, 1))

        p.drawPath(path)


# ── GlowButton ───────────────────────────────────────────────────────────────
class GlowButton(QPushButton):
    def __init__(self, text="", parent=None, primary=True, small=False):
        super().__init__(text, parent)
        self._primary = primary
        self._small = small
        self._hovered = False
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFlat(True)
        h = 40 if small else 52
        self.setFixedHeight(h)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        font = QFont("Segoe UI", 10 if small else 11, QFont.Weight.Medium)
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
        r = self.rect()
        path = QPainterPath()
        path.addRoundedRect(0, 0, r.width(), r.height(), 12, 12)

        disabled = not self.isEnabled()

        if self._primary:
            alpha = 70 if disabled else (230 if self._hovered else 200)
            g = QLinearGradient(0, 0, r.width(), r.height())
            g.setColorAt(0, QColor(99, 102, 241, alpha))
            g.setColorAt(1, QColor(6, 182, 212, alpha))
            p.fillPath(path, QBrush(g))
            border_c = QColor(255, 255, 255, 20 if disabled else (60 if self._hovered else 40))
        else:
            alpha = 8 if disabled else (35 if self._hovered else 18)
            p.fillPath(path, QBrush(QColor(255, 255, 255, alpha)))
            border_c = QColor(255, 255, 255, 20 if disabled else (70 if self._hovered else 40))

        p.setPen(QPen(border_c, 1))
        p.drawPath(path)

        text_alpha = 60 if disabled else 230
        p.setPen(QColor(255, 255, 255, text_alpha))
        p.setFont(self.font())
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.text())


# ── ToggleSwitch ─────────────────────────────────────────────────────────────
class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(52, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._anim_x = 4 if not checked else 28

    @property
    def checked(self):
        return self._checked

    @checked.setter
    def checked(self, val: bool):
        self._checked = val
        self._anim_x = 28 if val else 4
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self._anim_x = 28 if self._checked else 4
            self.update()
            self.toggled.emit(self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        track = QPainterPath()
        track.addRoundedRect(0, 0, w, h, h / 2, h / 2)
        if self._checked:
            g = QLinearGradient(0, 0, w, 0)
            g.setColorAt(0, QColor(99, 102, 241))
            g.setColorAt(1, QColor(6, 182, 212))
            p.fillPath(track, QBrush(g))
        else:
            p.fillPath(track, QBrush(QColor(60, 70, 90)))

        thumb_x = self._anim_x
        thumb_y = 4
        thumb_size = 20
        thumb = QPainterPath()
        thumb.addEllipse(thumb_x, thumb_y, thumb_size, thumb_size)
        p.fillPath(thumb, QBrush(QColor(255, 255, 255, 240)))


# ── ProgressRing ─────────────────────────────────────────────────────────────
class ProgressRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self.setFixedSize(160, 160)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_value(self, v: int):
        self._value = max(0, min(100, v))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        r = min(w, h) // 2 - 16
        span = int(self._value * 360 / 100)

        # Track ring
        pen = QPen(QColor(255, 255, 255, 18), 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(cx - r, cy - r, r * 2, r * 2, 90 * 16, -360 * 16)

        # Progress arc (gradient color)
        if span > 0:
            # Use indigo→cyan gradient
            gradient_pen_color = QColor(99, 102, 241)
            if self._value > 50:
                t = (self._value - 50) / 50.0
                r1, g1, b1 = 99, 102, 241
                r2, g2, b2 = 6, 182, 212
                gradient_pen_color = QColor(
                    int(r1 + (r2 - r1) * t),
                    int(g1 + (g2 - g1) * t),
                    int(b1 + (b2 - b1) * t),
                )
            pen2 = QPen(gradient_pen_color, 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(pen2)
            p.drawArc(cx - r, cy - r, r * 2, r * 2, 90 * 16, -span * 16)

        # Centre text
        p.setPen(C_TEXT)
        pct_font = QFont("Segoe UI", 22, QFont.Weight.Bold)
        p.setFont(pct_font)
        p.drawText(self.rect().adjusted(0, -10, 0, -10),
                   Qt.AlignmentFlag.AlignCenter, f"{self._value}%")
        p.setPen(C_TEXT_MUTED)
        small_font = QFont("Segoe UI", 9)
        p.setFont(small_font)
        p.drawText(self.rect().adjusted(0, 30, 0, 30),
                   Qt.AlignmentFlag.AlignCenter, "завершено")


# ── StepIndicator ────────────────────────────────────────────────────────────
class StepIndicator(QWidget):
    LABELS = ["Привет", "USB", "Windows", "Загрузка", "Настройки", "Запись", "Готово"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = 0
        self.setFixedHeight(56)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_step(self, step: int):
        self._current = step
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        n = len(self.LABELS)
        w, h = self.width(), self.height()
        dot_r = 10
        spacing = w / (n + 1)

        for i, label in enumerate(self.LABELS):
            cx = int(spacing * (i + 1))
            cy = 18

            # Connector line
            if i < n - 1:
                nx = int(spacing * (i + 2))
                line_color = QColor(99, 102, 241, 140 if i < self._current else 40)
                p.setPen(QPen(line_color, 1.5, Qt.PenStyle.DashLine))
                p.drawLine(cx + dot_r + 2, cy, nx - dot_r - 2, cy)

            # Dot
            dot_path = QPainterPath()
            dot_path.addEllipse(cx - dot_r, cy - dot_r, dot_r * 2, dot_r * 2)

            if i < self._current:
                p.fillPath(dot_path, QBrush(C_SUCCESS))
                p.setPen(QPen(C_SUCCESS, 1))
            elif i == self._current:
                g = QRadialGradient(cx, cy, dot_r)
                g.setColorAt(0, QColor(99, 102, 241))
                g.setColorAt(1, QColor(6, 182, 212))
                p.fillPath(dot_path, QBrush(g))
                p.setPen(QPen(QColor(255, 255, 255, 80), 1))
            else:
                p.fillPath(dot_path, QBrush(QColor(255, 255, 255, 20)))
                p.setPen(QPen(QColor(255, 255, 255, 40), 1))
            p.drawPath(dot_path)

            # Label
            lbl_color = C_TEXT if i == self._current else C_TEXT_MUTED
            if i < self._current:
                lbl_color = C_SUCCESS
            p.setPen(lbl_color)
            font = QFont("Segoe UI", 8, QFont.Weight.Medium if i == self._current else QFont.Weight.Normal)
            p.setFont(font)
            p.drawText(cx - 40, cy + dot_r + 4, 80, 18, Qt.AlignmentFlag.AlignCenter, label)
