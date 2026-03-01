from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QWidget, QGridLayout
from PyQt6.QtGui import QPen, QBrush, QColor, QWheelEvent, QPainter, QPainterPath, QFont, QPainterPathStroker
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from core.document import ColorLayer, Shape

# Work area dimensions in mm (default A4)
WORK_W_MM = 210
WORK_H_MM = 297
PIXELS_PER_MM = 3  # scale factor: 1mm = 3px on screen
# Zoom limits
ZOOM_MIN = 0.2   # can zoom out to see 5x the work area
ZOOM_MAX = 5.0   # can zoom in to 5x the work area size

SELECTION_COLOR = "#FF6B00"

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

class CAMCanvas(QGraphicsView):

    # Signal emitted when the viewport transform changes (zoom / pan)
    transform_changed = pyqtSignal(float, float, float, float)  # x_offset, y_offset, scale_x, scale_y

    # Emits shape_id of clicked shape (0 = nothing)
    selection_changed = pyqtSignal(list)

    def __init__(self):
        super().__init__()

        self.scene     = QGraphicsScene()
        self._zoom     = 1.0   # current cumulative zoom level

        self._select_mode = False
        self._selected_ids: set = set()

        self._rubber_band_origin = None
        self._drag_start = None

        self.setScene(self.scene)
        self._setup_view()
        self._draw_work_area()

    def _setup_view(self):
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setBackgroundBrush(QBrush(QColor("#2B2B2B")))
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setRubberBandSelectionMode(Qt.ItemSelectionMode.IntersectsItemShape)

    def _draw_work_area(self):
        w = WORK_W_MM * PIXELS_PER_MM
        h = WORK_H_MM * PIXELS_PER_MM

        work_rect = QGraphicsRectItem(0, 0, w, h)
        work_rect.setBrush(QBrush(QColor("#FFFFFF")))
        work_rect.setPen(QPen(QColor("#AAAAAA"), 1))
        work_rect.setZValue(-10)
        self.scene.addItem(work_rect)

        pen = QPen(QColor("#E94560"), 1)
        self.scene.addLine(-8, 0, 8, 0, pen)
        self.scene.addLine(0, -8, 0, 8, pen)

        self.scene.setSceneRect(-20, -20, w + 40, h + 40)

    # ── Keyboard ──────────────────────────────────────────────────────────────
    # Toggle between Select and Drag modes
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._select_mode = not self._select_mode
            if self._select_mode:
                self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
                self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
            else:
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                self.deselect_all()
        else:
            super().keyPressEvent(event)

    # MOUSE EVENT FOR SELECTION
    # def mousePressEvent(self, event):
    #     if self._select_mode and event.button() == Qt.MouseButton.LeftButton:
    #         scene_pos = self.mapToScene(event.pos())
    #         # Use items() at point with a small tolerance instead of itemAt
    #         items = self.scene.items(scene_pos)
    #         # Filter to only items tagged with a shape id (skip work area rect etc.)
    #         shape_items = [i for i in items if i.data(0) is not None]
    #         if shape_items:
    #             shape_id = shape_items[0].data(0)
    #             shift_held = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
    #
    #             if shift_held:
    #                 if shape_id in self._selected_ids:
    #                     self._deselect_one(shape_id)
    #                 else:
    #                     self._add_to_selection(shape_id)
    #             else:
    #                 self.deselect_all()
    #                 self._add_to_selection(shape_id)
    #         else:
    #             if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
    #                 self.deselect_all()
    #
    #         # Lef parent handle rubber band drag start
    #         super().mousePressEvent(event)
    #     else:
    #         super().mousePressEvent(event)

    def mousePressEvent(self, event):
        if self._select_mode and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.pos()
            scene_pos = self.mapToScene(event.pos())
            shift_held = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

            hit_id = None
            # CHANGED: manual stroke hit test — check all items, find closest stroke
            for item in self.scene.items(scene_pos):
                if item.data(0) is None:
                    continue
                stroker = QPainterPathStroker()
                stroker.setWidth(16.0 / self._zoom)  # hit tolerance in scene units
                stroke_path = stroker.createStroke(item.path())
                if stroke_path.contains(scene_pos):
                    hit_id = item.data(0)
                    break

            if hit_id is not None:
                if shift_held:
                    if hit_id in self._selected_ids:
                        self._deselect_one(hit_id)
                    else:
                        self._add_to_selection(hit_id)
                else:
                    self.deselect_all()
                    self._add_to_selection(hit_id)
            else:
                if not shift_held:
                    self.deselect_all()

            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._select_mode and self._drag_start is not None:
            # Let Qt draw the rubber band visually — we still use RubberBandDrag mode
            super().mouseMoveEvent(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._select_mode and event.button() == Qt.MouseButton.LeftButton:
            shift_held = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

            if self._drag_start is not None:
                drag_dist = (event.pos() - self._drag_start).manhattanLength()

                if drag_dist > 5:  # it was a drag, not a click
                    self._rubber_band_select(self._drag_start, event.pos(), shift_held)

                self._drag_start = None

            super().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

    def _rubber_band_select(self, p1, p2, additive: bool):
        """Select all shapes whose stroke intersects the rubber band rectangle."""
        scene_rect = QRectF(
            self.mapToScene(p1),
            self.mapToScene(p2)
        ).normalized()

        if not additive:
            self.deselect_all()

        for item in self.scene.items(scene_rect, Qt.ItemSelectionMode.IntersectsItemShape):
            if item.data(0) is None:
                continue
            # Check if stroke actually intersects the rect
            stroker = QPainterPathStroker()
            stroker.setWidth(16.0 / self._zoom)
            stroke_path = stroker.createStroke(item.path())
            rect_path = QPainterPath()
            rect_path.addRect(scene_rect)
            if stroke_path.intersects(rect_path):
                self._add_to_selection(item.data(0))

    def _collect_rubber_band_selection(self, additive: bool):
        qt_selected = [i for i in self.scene.selectedItems() if i.data(0) is not None]
        if not qt_selected:
            return

        if not additive:
            self.deselect_all()

        for item in qt_selected:
            self._add_to_selection(item.data(0))

        # We manage selection state ourselves, so we clear QT's selection state
        self.scene.clearSelection()

    # SELECTION HELPERS:

    def _add_to_selection(self, shape_id: int):
        """Add a shape to the selection and highlight it"""
        self._selected_ids.add(shape_id)
        for item in self.scene.items():
            if item.data(0) == shape_id:
                item.setPen(QPen(QColor(SELECTION_COLOR), 1.5))
        self.selection_changed.emit(list(self._selected_ids))

    def _deselect_one(self, shape_id: int):
        """Remove one shape from selection and restore its color"""
        self._selected_ids.discard(shape_id)
        for item in self.scene.items():
            if item.data(0) == shape_id:
                original = item.data(2)
                if original:
                    item.setPen(QPen(QColor(original), 0.5))
        self.selection_changed.emit(list(self._selected_ids))

    def deselect_all(self):
        """Deselect and restore all shapes to their original color."""
        for shape_id in list(self._selected_ids):
            for item in self.scene.items():
                if item.data(0) == shape_id:
                    original = item.data(2)
                    if original:
                        item.setPen(QPen(QColor(original), 0.5))
        self._selected_ids.clear()
        self.selection_changed.emit([])

    def select_shape(self, shape_id: int, additive: bool = False):
        """Programmatically select a shape (called from tree click)."""
        if not additive:
            self.deselect_all()
        self._add_to_selection(shape_id)

    def get_selected_ids(self) -> list:
        return  list(self._selected_ids)

    # ── Draw / clear layers ───────────────────────────────────────────────────

    def draw_color_layer(self, color_layer: ColorLayer):
        """Draw all shapes in a color layer."""
        for shape in color_layer.shapes:
            self._draw_shape(shape, color_layer.color)

    def draw_shape(self, shape: Shape, color: str):
        """Draw a single shape."""
        self._draw_shape(shape, color)

    def _draw_shape(self, shape: Shape, color: str):
        if not shape.points:
            return
        pen = QPen(QColor(color), 0.5)
        path = QPainterPath()
        x0, y0 = shape.points[0]
        path.moveTo(self.mm_to_px(x0), self.mm_to_px(y0))
        for (x, y) in shape.points[1:]:
            path.lineTo(self.mm_to_px(x), self.mm_to_px(y))
        if shape.closed:
            path.closeSubpath()
        item = self.scene.addPath(path, pen)
        item.setData(0, shape.id)  # shape id for selection/removal
        item.setData(2, color)  # original color for deselect restore

    def clear_shape(self, shape_id: int):
        self._selected_ids.discard(shape_id)
        to_remove = [i for i in self.scene.items() if i.data(0) == shape_id]
        for item in to_remove:
            self.scene.removeItem(item)

    def clear_color_layer(self, color_layer: ColorLayer):
        for shape in color_layer.shapes:
            self.clear_shape(shape.id)

    def redraw_shape(self, shape: Shape, new_color: str):
        """Remove and redraw a shape in a new color."""
        was_selected = shape.id in self._selected_ids
        self.clear_shape(shape.id)
        self._draw_shape(shape, new_color)
        if was_selected:
            self._add_to_selection(shape.id)

    # ── Zoom & pan ────────────────────────────────────────────────────────────
    def wheelEvent(self, event: QWheelEvent):
        factor   = 1.15 if event.angleDelta().y() > 0 else 1/1.15
        new_zoom = self._zoom * factor
        if new_zoom < ZOOM_MIN or new_zoom > ZOOM_MAX:
            return
        self._zoom = new_zoom
        self.scale(factor, factor)
        self._emit_transform()

    def _emit_transform(self):
        t      = self.transform()
        origin = self.mapFromScene(0, 0)
        self.transform_changed.emit(origin.x(), origin.y(), t.m11(), t.m22())

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self._emit_transform()

    def fit_view(self):
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = self.transform().m11()
        self._emit_transform()

    def reset_zoom(self):
        self.resetTransform()
        self._zoom = 1.0
        self._emit_transform()

    def mm_to_px(self, mm: float) -> float:
        return mm * PIXELS_PER_MM

    def px_to_mm(self, px: float) -> float:
        return px / PIXELS_PER_MM


class CAMCanvasWithRulers(QWidget):
    """
    Wraps CAMCanvas with horizontal and vertical rulers.
    Use this as the central widget instead of CAMCanvas directly.
    """
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
        self.selection_changed = self.canvas.selection_changed

    def _on_transform_changed(self, ox: float, oy: float, sx: float, sy: float):
        self.h_ruler.update_from_transform(ox, sx)
        self.v_ruler.update_from_transform(oy, sy)

    def showEvent(self, event):
        super().showEvent(event)
        # Push initial transform to rulers once the widget is visible
        self.canvas._emit_transform()