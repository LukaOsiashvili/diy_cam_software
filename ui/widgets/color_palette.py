from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush
from PyQt6.QtCore import Qt, pyqtSignal, QRect

# 20 fixed colors
PALETTE_COLORS = [
    "#000000",  # Black
    "#FF0000",  # Red
    "#FF6600",  # Orange
    "#FFFF00",  # Yellow
    "#00FF00",  # Lime
    "#008000",  # Green

    "#00FFFF",  # Cyan
    "#0000FF",  # Blue
    "#8000FF",  # Violet
    "#FF00FF",  # Magenta
    "#FF0080",  # Pink
    "#804000",  # Brown
    "#808000",  # Olive
    "#008080",  # Teal
    "#000080",  # Navy
    "#800080",  # Purple
    "#808080",  # Grey
    "#C0C0C0",  # Silver
    "#FFFFFF",  # White
    "#FF8080",  # Light Red
]

#Pixels
SWATCH_SIZE = 24
SWATCH_MARGIN = 3
PALETTE_HEIGHT = SWATCH_SIZE + SWATCH_MARGIN * 2

class ColorPaletteWidget(QWidget):
    """
        Horizontal strip of color swatches at the bottom of the canvas.
        Emits color_picked(color_hex) when a swatch is clicked.
        Does nothing if no shapes are selected.
    """

    color_picked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._has_selection = False
        self._hovered_color = None
        self.setFixedHeight(PALETTE_HEIGHT)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("background-color: #2B2B2B;")
        self.setToolTip("Select shapes first, then click a color to reassign")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_has_selection(self, has_selection: bool):
        """Called by main window when selection changes."""
        self._has_selection = has_selection
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor("#2B2B2B"))

        # Label
        painter.setPen(QPen(QColor("#888888")))
        painter.setFont(self.font())
        painter.drawText(8, SWATCH_MARGIN + SWATCH_SIZE // 2 + 4, "Color:")

        # Draw swatches
        for i, color in enumerate(PALETTE_COLORS):
            rect = self._swatch_rect(i)
            qc = QColor(color)

            if not self._has_selection:
                qc.setAlpha(80)

            is_hovered = (color == self._hovered_color and self._has_selection)

            painter.setBrush(QBrush(qc))
            if is_hovered:
                painter.setPen(QPen(QColor("#FFFFFF"), 2))
                expanded = rect.adjusted(-2, -2, 2, 2)
                painter.drawRoundedRect(expanded, 3, 3)
            else:
                painter.setPen(QPen(QColor("#555555"), 1))
                painter.drawRoundedRect(rect, 2, 2)

        painter.end()

    def mouseMoveEvent(self, event):
        color = self._color_at(event.pos().x(), event.pos().y())
        if color != self._hovered_color:
            self._hovered_color = color
            self.update()

    def leaveEvent(self, event):
        self._hovered_color = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._has_selection:
            color = self._color_at(event.pos().x(), event.pos().y())
            if color:
                self.color_picked.emit(color)

    def _swatch_rect(self, index: int) -> QRect:
        """Calculate the rect for the swatch at the given index."""
        label_offset = 52
        x = label_offset + index * (SWATCH_SIZE + SWATCH_MARGIN)
        y = SWATCH_MARGIN
        return QRect(x, y, SWATCH_SIZE, SWATCH_SIZE)

    def _color_at(self, x: int, y: int) -> str | None:
        """Return the color hex at screen position, or None"""
        for i, color in enumerate(PALETTE_COLORS):
            if self._swatch_rect(i).contains(x, y):
                return color
        return None