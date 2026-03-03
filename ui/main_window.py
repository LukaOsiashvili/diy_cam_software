from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QToolBar,
    QStatusBar, QFileDialog, QMessageBox,
    QWidget, QVBoxLayout
)
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtCore import Qt

from ui.canvas.canvas_view import CAMCanvasWithRulers
from ui.panels.layer_panel import LayerPanel
from ui.dialogs.color_layer_dialog import ColorLayerDialog
from ui.widgets.color_palette import ColorPaletteWidget

from core.document import Document
from core.importers.svg import import_svg
from core.importers.dxf import import_dxf

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DIY CAM Software")
        self.setMinimumSize(1200, 650)
        self.resize(1400, 850)
        self.showMaximized()

        self.document = Document()
        self._current_selection = []

        self._build_central()
        self._build_panels()
        self._build_menu()
        self._build_toolbar()
        self._build_statusbar()

    # ── Canvas (central widget) ────────────────────────────────────────────────
    def _build_central(self):
        self.canvas = CAMCanvasWithRulers()
        self.palette = ColorPaletteWidget()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.canvas)
        layout.addWidget(self.palette)

        self.setCentralWidget(central)

        self.canvas.selection_changed.connect(self._on_selection_changed)
        self.palette.color_picked.connect(self._on_color_picked)

    # ── Side panels ───────────────────────────────────────────────────────────
    def _build_panels(self):
        # Shape layers' panel
        self.layer_panel = LayerPanel()
        dock = QDockWidget("Layers", self)
        dock.setWidget(self.layer_panel)
        dock.setMinimumWidth(300)
        dock.setMaximumWidth(500)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

        # Connect layer removal signals
        self.layer_panel.shapes_removed.connect(self._on_shapes_removed)
        self.layer_panel.color_layer_removed.connect(self._on_color_layer_removed)
        self.layer_panel.color_layer_settings.connect(self._on_color_layer_settings)
        self.layer_panel.shape_clicked.connect(self._on_tree_shape_clicked)

    # ── Menu bar ──────────────────────────────────────────────────────────────
    def _build_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_svg_action = QAction("Import SVG...", self)
        open_svg_action.setShortcut(QKeySequence("Ctrl+O"))
        open_svg_action.triggered.connect(self.on_import_svg)
        file_menu.addAction(open_svg_action)

        open_dxf_action = QAction("Import DXF...", self)
        open_dxf_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        open_dxf_action.triggered.connect(self.on_import_dxf)
        file_menu.addAction(open_dxf_action)

        file_menu.addSeparator()

        export_gcode_action = QAction("Export GCODE...", self)
        export_gcode_action.setShortcut(QKeySequence("Ctrl+E"))
        export_gcode_action.triggered.connect(self.on_export_gcode)
        file_menu.addAction(export_gcode_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        fit_action = QAction("Fit to Window", self)
        fit_action.setShortcut(QKeySequence("Ctrl+F"))
        fit_action.triggered.connect(self.canvas.fit_view)
        view_menu.addAction(fit_action)

        reset_zoom_action = QAction("Reset Zoom", self)
        reset_zoom_action.setShortcut(QKeySequence("Ctrl+0"))
        reset_zoom_action.triggered.connect(self.canvas.reset_zoom)
        view_menu.addAction(reset_zoom_action)

        # Machine menu
        machine_menu = menubar.addMenu("&Machine")

        connect_action = QAction("Connect to Plotter...", self)
        connect_action.setShortcut(QKeySequence("Ctrl+K"))
        connect_action.triggered.connect(self.on_connect)
        machine_menu.addAction(connect_action)

        machine_menu.addSeparator()

        send_action = QAction("Send to Plotter", self)
        send_action.setShortcut(QKeySequence("Ctrl+P"))
        send_action.triggered.connect(self.on_send)
        machine_menu.addAction(send_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.on_about)
        help_menu.addAction(about_action)

    # ── Toolbar ───────────────────────────────────────────────────────────────
    def _build_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addAction("Import SVG", self.on_import_svg)
        toolbar.addAction("Import DXF", self.on_import_dxf)
        toolbar.addSeparator()
        toolbar.addAction("Export GCODE", self.on_export_gcode)
        toolbar.addSeparator()
        toolbar.addAction("Fit View", self.canvas.fit_view)
        toolbar.addSeparator()
        toolbar.addAction("Connect", self.on_connect)
        toolbar.addAction("▶  Send Job", self.on_send)

    # ── Status bar ────────────────────────────────────────────────────────────
    def _build_statusbar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready  —  No file loaded")

    # ── Import slots ──────────────────────────────────────────────────────────
    def on_import_svg(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import SVG", "", "SVG Files (*.svg)"
        )
        if not path:
            return

        try:
            # Snapshot shape counts before import
            before = {cl.color: len(cl.shapes) for cl in self.document.color_layers}

            affected = import_svg(path, self.document)

            total = 0
            for cl in affected:
                old_count = before.get(cl.color, 0)
                new_shapes = cl.shapes[old_count:]  # only newly added shapes
                for shape in new_shapes:
                    self.canvas.draw_shape(shape, cl.color)
                    self.layer_panel.add_shape(cl, shape)
                # Create color node if it didn't exist before
                total += len(new_shapes)

            self.canvas.fit_view()
            self.status.showMessage(f"Imported {total} shapes from {path}")
        except Exception as e:
            self.status.showMessage(f"SVG import failed: {e}")
            print(f"[SVG import error] {e}")

    def on_import_dxf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import DXF", "", "DXF Files (*.dxf)"
        )
        if not path:
            return
        try:
            # Snapshot shape counts before import
            before = {cl.color: len(cl.shapes) for cl in self.document.color_layers}

            affected = import_dxf(path, self.document)

            total = 0
            for cl in affected:
                old_count = before.get(cl.color, 0)
                new_shapes = cl.shapes[old_count:]  # only newly added shapes
                for shape in new_shapes:
                    self.canvas.draw_shape(shape, cl.color)
                    self.layer_panel.add_shape(cl, shape)
                total += len(new_shapes)

            self.canvas.fit_view()
            self.status.showMessage(f"Imported {total} shapes from {path}")
        except Exception as e:
            self.status.showMessage(f"DXF import failed: {e}")
            print(f"[DXF import error] {e}")

    # ── Layer panel signal handlers ───────────────────────────────────────────

    def _on_selection_changed(self, shape_ids: list):
        self._current_selection = list(shape_ids)
        self.palette.set_has_selection(len(shape_ids) > 0)
        self.layer_panel.sync_selection(shape_ids)
        if not shape_ids:
            self.status.showMessage("Ready")
        elif len(shape_ids) == 1:
            cl, shape = self.document.find_shape(shape_ids[0])
            if cl and shape:
                self.status.showMessage(
                    f"Selected: {shape.source or 'Shape'}  |  "
                    f"Layer: {cl.color.upper()}  |  "
                    f"Operation: {cl.operation}"
                )
        else:
            self.status.showMessage(f"{len(shape_ids)} shapes selected")

    def _on_color_picked(self, new_color: str):
        selected_ids = list(self._current_selection)
        if not selected_ids:
            return

        for shape_id in selected_ids:
            self.document.move_shape(shape_id, new_color)

        self._refresh_views()
        self._current_selection = []
        self.palette.set_has_selection(False)
        self.status.showMessage(
            f"Reassigned {len(selected_ids)} shape(s) to {new_color.upper()}"
        )

    def _on_tree_shape_clicked(self, shape_id: int):
        self.canvas.select_shape(shape_id, additive=False)
        self.canvas.canvas.setFocus()

    def _on_shapes_removed(self, shape_ids: list):
        # Remove from document and canvas
        for shape_id in shape_ids:
            cl, shape = self.document.find_shape(shape_id)
            if cl and shape:
                self.canvas.clear_shape(shape_id)
                cl.shapes.remove(shape)

        # Clean up empty color layers from document
        for cl in list(self.document.color_layers):
            if not cl.shapes:
                self.document.color_layers.remove(cl)

        # Rebuild tree from document — source of truth
        self._rebuild_layer_panel()

    def _on_color_layer_removed(self, color: str):
        """Remove entire color layer from canvas and document."""
        for cl in list(self.document.color_layers):
            if cl.color.upper() == color.upper():
                self.canvas.clear_color_layer(cl)
                self.document.color_layers.remove(cl)
                break

    def _on_color_layer_settings(self, color: str):
        """Open settings dialog for the color layer."""
        for cl in self.document.color_layers:
            if cl.color.upper() == color.upper():
                dialog = ColorLayerDialog(cl, parent=self)
                if dialog.exec():
                    self.layer_panel.update_color_node_label(cl)
                return

    # ── View helpers ──────────────────────────────────────────────────────────

    def _rebuild_layer_panel(self):
        """Rebuild the entire layer panel tree from the document."""
        self.layer_panel.tree.clear()
        for cl in self.document.color_layers:
            for shape in cl.shapes:
                self.layer_panel.add_shape(cl, shape)

    def _refresh_views(self):
        """Rebuild both canvas and tree from document"""
        self.canvas.canvas.scene.clear()
        self.canvas.canvas._draw_work_area()
        for cl in self.document.color_layers:
            for shape in cl.shapes:
                self.canvas.draw_shape(shape, cl.color)

        self._rebuild_layer_panel()

    # ── Upcoming Slots ───────────────────────────────────────────────────────────

    def on_export_gcode(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export GCODE", "output.gcode", "GCODE Files (*.gcode *.nc *.txt)"
        )
        if path:
            self.status.showMessage(f"Exporting GCODE: {path}")
            # TODO: call GCODE generator
            print(f"[GCODE export] {path}")

    def on_connect(self):
        # TODO: open serial connect dialog
        self.status.showMessage("Serial connection — coming soon")

    def on_send(self):
        # TODO: start GCODE streaming
        self.status.showMessage("Send job — coming soon")

    def on_about(self):
        QMessageBox.about(
            self,
            "About DIY CAM Software",
            "DIY CAM Software\n\nBachelor's Project\n\n"
            "Built with Python + PyQt6\n"
            "ezdxf · svgpathtools · Shapely · pyserial"
        )