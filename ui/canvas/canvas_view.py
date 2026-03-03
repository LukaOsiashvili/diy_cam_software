from PyQt6.QtWidgets import QWidget, QGridLayout

from ui.canvas.canvas import CAMCanvas
from ui.canvas.rulers import RulerWidget


class CAMCanvasWithRulers(QWidget):
    """
    Wraps CAMCanvas with horizontal and vertical rulers.
    """

    selection_changed = None  # assigned in __init__ from canvas signal

    def __init__(self):
        super().__init__()

        self.canvas  = CAMCanvas()
        self.h_ruler = RulerWidget("horizontal")
        self.v_ruler = RulerWidget("vertical")

        # Corner square to fill the gap between the two rulers
        corner = QWidget()
        corner.setFixedSize(RulerWidget.RULER_SIZE, RulerWidget.RULER_SIZE)
        corner.setStyleSheet("background-color: #D0D0D0;")

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        #        col 0          col 1
        # row 0  corner         h_ruler
        # row 1  v_ruler        canvas
        layout.addWidget(corner,         0, 0)
        layout.addWidget(self.h_ruler,   0, 1)
        layout.addWidget(self.v_ruler,   1, 0)
        layout.addWidget(self.canvas,    1, 1)

        # Connect canvas transform signal to rulers
        self.canvas.transform_changed.connect(self._on_transform_changed)

        # Expose canvas public methods at this level for convenience
        self.selection_changed = self.canvas.selection_changed
        self.draw_color_layer  = self.canvas.draw_color_layer
        self.draw_shape        = self.canvas.draw_shape
        self.clear_shape       = self.canvas.clear_shape
        self.clear_color_layer = self.canvas.clear_color_layer
        self.redraw_shape      = self.canvas.redraw_shape
        self.deselect_all      = self.canvas.deselect_all
        self.select_shape      = self.canvas.select_shape
        self.get_selected_ids  = self.canvas.get_selected_ids
        self.fit_view          = self.canvas.fit_view
        self.reset_zoom        = self.canvas.reset_zoom

    def _on_transform_changed(self, ox: float, oy: float, sx: float, sy: float):
        self.h_ruler.update_from_transform(ox, sx)
        self.v_ruler.update_from_transform(oy, sy)

    def showEvent(self, event):
        super().showEvent(event)
        # Push initial transform to rulers once the widget is visible
        self.canvas._emit_transform()
