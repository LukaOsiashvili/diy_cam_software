from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPen, QColor, QPainter, QFont
from PyQt6.QtCore import Qt

PIXELS_PER_MM = 3  # scale factor: 1mm = 3px on screen


class RulerWidget(QWidget):
    """
        A ruler that draws mm tick marks along one axis.
        Stays in sync with the canvas viewport via update_from_transform().
    """

    RULER_SIZE = 20 # thickness in px

    def __init__(self, orientation: str, parent=None):
        """Orientation is 'horizontal' or 'vertical' """

        super().__init__(parent)
        self.orientation = orientation
        self._offset = 0.0 # scene origin in viewport pixels
        self._scale = 1.0 # pixels per scene pixel (zoom factor)

        if orientation == "horizontal":
            self.setFixedHeight(self.RULER_SIZE)
        else:
            self.setFixedWidth(self.RULER_SIZE)

        self.setStyleSheet("background-color: #D0D0D0;")

    def update_from_transform(self, offset: float, scale: float):
        """Called by the canvas whenever zoom or pan changes"""

        self._offset = offset
        self._scale = scale
        self.update() # rerender

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        size = self.width() if self.orientation == "horizontal" else self.height()

        # background
        painter.fillRect(self.rect(), QColor("#D0D0D0"))

        # pixel per mm | Chooses tick spacing based on zoom level
        ppm = PIXELS_PER_MM * self._scale

        major_mm = 10
        minor_mm = 5

        pen_major = QPen(QColor("#222222"), 1)
        pen_minor = QPen(QColor("#777777"), 1)
        pen_text = QPen(QColor("#111111"), 1)

        font = QFont("Helvetica", 7)
        painter.setFont(font)

        # first tick position
        start_mm = -self._offset / (PIXELS_PER_MM * self._scale)
        end_mm = start_mm + size / (PIXELS_PER_MM * self._scale)

        first_tick = int(start_mm / minor_mm) * minor_mm

        tick = first_tick
        while tick <= end_mm + minor_mm:
            pos = self._offset + tick * PIXELS_PER_MM * self._scale

            is_major = (round(tick) % major_mm == 0)  # CHANGED: simple modulo check for 10mm

            if self.orientation == "horizontal":
                tick_h = 12 if is_major else 6
                painter.setPen(pen_major if is_major else pen_minor)
                painter.drawLine(int(pos), self.RULER_SIZE - tick_h, int(pos), self.RULER_SIZE)
                if is_major and 0 <= pos <= size:
                    painter.setPen(pen_text)
                    painter.drawText(int(pos) + 2, self.RULER_SIZE - 10, f"{round(tick)}")
            else:
                tick_h = 12 if is_major else 6
                painter.setPen(pen_major if is_major else pen_minor)
                painter.drawLine(self.RULER_SIZE - tick_h, int(pos), self.RULER_SIZE, int(pos))
                if is_major and 0 <= pos <= size:
                    painter.setPen(pen_text)
                    painter.save()
                    painter.translate(self.RULER_SIZE - 10, int(pos) - 2)
                    painter.rotate(-90)
                    painter.drawText(0, 0, f"{round(tick)}")
                    painter.restore()

            tick = round(tick + minor_mm, 6)

        painter.setPen(QPen(QColor("#999999"), 1))
        if self.orientation == "horizontal":
            painter.drawLine(0, self.RULER_SIZE - 1, self.width(), self.RULER_SIZE - 1)
        else:
            painter.drawLine(self.RULER_SIZE - 1, 0, self.RULER_SIZE - 1, self.height())

        painter.end()
