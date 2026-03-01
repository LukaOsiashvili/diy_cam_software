from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QDoubleSpinBox, QSpinBox,
    QPushButton, QWidget, QFrame
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

from core.document import ColorLayer

class ColorLayerDialog(QDialog):
    """

    Modal dialog for editing a ColorLayer's operation settings.
    Opened by double-clicking a color node in the layer tree.
    Engraving-specific fields show/hide based on selected operation.
    """

    def __init__(self, color_layer: ColorLayer, parent=None):
        super().__init__(parent)
        self.color_layer = color_layer
        self.setWindowTitle("Layer Settings")
        self.setMinimumWidth(340)
        self.setModal(True)
        self._build_ui()
        self._load_values()
        self._on_operation_changed()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Colored header
        header = QWidget()
        header.setFixedHeight(52)
        color = self.color_layer.color
        # Text color based on brightness of background
        qc = QColor(color)
        lum = 0.299 * qc.red() + 0.587 * qc.green() + 0.114 * qc.blue()
        text_color = "#000000" if lum > 140 else "FFFFFF"
        header.setStyleSheet(f"background-color: {color};")

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)

        # color swatch circle
        swatch = QLabel("●")
        swatch.setStyleSheet(f""""
            color: {text_color};
            font-size: 22px;
        """)
        header_layout.addWidget(swatch)

        # layer color label
        title = QLabel(color.upper())
        title.setStyleSheet(f"""
            color: {text_color};
            font-size: 15px;
            font-weight: bold;
            font-family: 'Courier New', monospace
            padding-left: 8px; 
        """)

        layout.addWidget(header)

        # Thin accent line
        accent = QFrame()
        accent.setFixedHeight(3)
        accent.setStyleSheet(f"background-color: {self._darken(color)};")
        layout.addWidget(accent)

        # form body

        body = QWidget()
        body.setStyleSheet("background-color: #F5F5F5;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(16, 16, 16, 8)
        body_layout.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)

        # operation type
        self.combo_operation = QComboBox()
        self.combo_operation.addItems(["Line Draw", "Engrave"])
        self.combo_operation.setStyleSheet(self._input_style())
        self.combo_operation.currentTextChanged.connect(self._on_operation_changed)
        form.addRow("Operation: ", self.combo_operation)

        sep1 = self._separator()
        form.addRow(sep1)

        # Feed rate
        self.spin_feed = QDoubleSpinBox()
        self.spin_feed.setRange(1, 1000)
        self.spin_feed.setSuffix(" mm/min")
        self.spin_feed.setDecimals(0)
        self.spin_feed.setStyleSheet(self._input_style())
        form.addRow("Feed Rate:", self.spin_feed)

        # Rapid rate
        self.spin_rapid = QDoubleSpinBox()
        self.spin_rapid.setRange(1, 1000)
        self.spin_rapid.setSuffix("  mm/min")
        self.spin_rapid.setDecimals(0)
        self.spin_rapid.setStyleSheet(self._input_style())
        form.addRow("Rapid Rate:", self.spin_rapid)

        # pass count
        self.spin_passes = QSpinBox()
        self.spin_passes.setRange(1, 20)
        self.spin_passes.setStyleSheet(self._input_style())
        form.addRow("Passes:", self.spin_passes)

        # -----Engraving Section-----
        self.sep_engrave = self._separator()
        form.addRow(self.sep_engrave)

        self.label_spacing = QLabel("Line Spacing:")
        self.spin_spacing = QDoubleSpinBox()
        self.spin_spacing.setRange(0.1, 20)
        self.spin_spacing.setSuffix(" mm")
        self.spin_spacing.setDecimals(2)
        self.spin_spacing.setSingleStep(0.1)
        self.spin_spacing.setStyleSheet(self._input_style())
        form.addRow(self.label_spacing, self.spin_spacing)

        self.label_angle = QLabel("Line Angle:")
        self.combo_angle = QComboBox()
        self.combo_angle.addItems(["Horizontal", "Vertical"])
        self.combo_angle.setStyleSheet(self._input_style())
        form.addRow(self.label_angle, self.combo_angle)

        body_layout.addLayout(form)
        layout.addWidget(body)

        # ----- Buttons -----
        btn_bar = QWidget()
        btn_bar.setStyleSheet("background-color: #EBEBEB;")
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(16, 10, 16, 10)
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedWidth(90)
        btn_cancel.setStyleSheet(self._btn_style(accent=False))
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("OK")
        btn_ok.setStyleSheet(self._btn_style(accent=True, color=color))
        btn_ok.clicked.connect(self._on_accept)
        btn_ok.setDefault(True)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addSpacing(8)
        btn_layout.addWidget(btn_ok)
        layout.addWidget(btn_bar)

    def _load_values(self):
        """Pre-fill all inputs from the ColorLayer's current values."""
        cl = self.color_layer
        idx = self.combo_operation.findText(cl.operation)
        if idx >= 0:
            self.combo_operation.setCurrentIndex(idx)
        self.spin_feed.setValue(cl.speed)
        self.spin_rapid.setValue(cl.rapid_speed)
        self.spin_passes.setValue(cl.pass_count)
        self.spin_spacing.setValue(cl.line_spacing)
        idx2 = self.combo_angle.findText(cl.line_angle)
        if idx2 >= 0:
            self.combo_angle.setCurrentIndex(idx2)

    def _on_operation_changed(self):
        """Show engraving fields only when operation is Engrave."""
        is_engrave = self.combo_operation.currentText() == "Engrave"
        self.sep_engrave.setVisible(is_engrave)
        self.label_spacing.setVisible(is_engrave)
        self.spin_spacing.setVisible(is_engrave)
        self.label_angle.setVisible(is_engrave)
        self.combo_angle.setVisible(is_engrave)
        self.adjustSize()

    def _on_accept(self):
        """Save values back to the ColorLayer and close."""
        cl = self.color_layer
        cl.operation = self.combo_operation.currentText()
        cl.speed = self.spin_feed.value()
        cl.rapid_speed = self.spin_rapid.value()
        cl.pass_count = self.spin_passes.value()
        cl.line_spacing = self.spin_spacing.value()
        cl.line_angle = self.combo_angle.currentText()
        self.accept()

    # ── Style helpers ─────────────────────────────────────────────────────────
    def _darken(self, hex_color: str, factor: float = 0.75) -> str:
        c = QColor(hex_color)
        return QColor(
            int(c.red() * factor),
            int(c.green() * factor),
            int(c.blue() * factor)
        ).name()

    def _separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #CCCCCC; margin: 2px 0;")
        return line

    def _input_style(self) -> str:
        return """
            QComboBox, QDoubleSpinBox, QSpinBox {
                background: white;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 140px;
            }
            QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {
                border: 1px solid #0F3460;
            }
        """

    def _btn_style(self, accent: bool, color: str = "#0F3460") -> str:
        if accent:
            return f"""
                QPushButton {{
                    background-color: {color};
                    color: {'#000' if QColor(color).lightness() > 140 else '#fff'};
                    border: none;
                    border-radius: 4px;
                    padding: 6px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background-color: {self._darken(color, 0.85)}; }}
            """
        return """
            QPushButton {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover { background-color: #E8E8E8; }
        """
