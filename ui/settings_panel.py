from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox,
    QDoubleSpinBox, QSpinBox, QLabel, QGroupBox
)


class SettingsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # ── Operation group ──
        op_group = QGroupBox("Operation")
        op_form  = QFormLayout(op_group)

        self.operation_type = QComboBox()
        self.operation_type.addItems(["Outline", "Line Engrave", "Perimeter + Fill"])
        op_form.addRow("Type:", self.operation_type)

        layout.addWidget(op_group)

        # ── Speed group ──
        speed_group = QGroupBox("Speed")
        speed_form  = QFormLayout(speed_group)

        self.feed_rate = QDoubleSpinBox()
        self.feed_rate.setRange(10, 10000)
        self.feed_rate.setValue(1200)
        self.feed_rate.setSuffix(" mm/min")
        speed_form.addRow("Feed Rate:", self.feed_rate)

        self.rapid_rate = QDoubleSpinBox()
        self.rapid_rate.setRange(10, 10000)
        self.rapid_rate.setValue(3000)
        self.rapid_rate.setSuffix(" mm/min")
        speed_form.addRow("Rapid Rate:", self.rapid_rate)

        layout.addWidget(speed_group)

        # ── Engraving group ──
        engrave_group = QGroupBox("Line Engraving")
        engrave_form  = QFormLayout(engrave_group)

        self.line_spacing = QDoubleSpinBox()
        self.line_spacing.setRange(0.1, 20.0)
        self.line_spacing.setValue(1.0)
        self.line_spacing.setSingleStep(0.1)
        self.line_spacing.setSuffix(" mm")
        engrave_form.addRow("Line Spacing:", self.line_spacing)

        self.hatch_angle = QDoubleSpinBox()
        self.hatch_angle.setRange(0, 180)
        self.hatch_angle.setValue(0)
        self.hatch_angle.setSuffix(" °")
        engrave_form.addRow("Hatch Angle:", self.hatch_angle)

        layout.addWidget(engrave_group)

        # ── Passes group ──
        passes_group = QGroupBox("Passes")
        passes_form  = QFormLayout(passes_group)

        self.pass_count = QSpinBox()
        self.pass_count.setRange(1, 10)
        self.pass_count.setValue(1)
        passes_form.addRow("Pass Count:", self.pass_count)

        self.offset = QDoubleSpinBox()
        self.offset.setRange(-5.0, 5.0)
        self.offset.setValue(0.0)
        self.offset.setSingleStep(0.05)
        self.offset.setSuffix(" mm")
        passes_form.addRow("Path Offset:", self.offset)

        layout.addWidget(passes_group)

        layout.addStretch()

    # ── Public API ─────────────────────────────────────────────────────────────
    def get_settings(self) -> dict:
        return {
            "operation":   self.operation_type.currentText(),
            "feed_rate":   self.feed_rate.value(),
            "rapid_rate":  self.rapid_rate.value(),
            "line_spacing":self.line_spacing.value(),
            "hatch_angle": self.hatch_angle.value(),
            "pass_count":  self.pass_count.value(),
            "offset":      self.offset.value(),
        }