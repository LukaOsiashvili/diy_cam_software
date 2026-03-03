from dataclasses import dataclass, field
from typing import List, Tuple
import itertools

# Shape ID counter, every shape gets unique ID
_id_counter = itertools.count(1)

def _next_id() -> int:
    return next(_id_counter)

def _normalize_color(color: str) -> str:
        """Ensure color is always uppercase #RRGGBB format."""

        color = color.strip().upper()
        if not color.startswith("#"):
            color = "#" + color
        return color

@dataclass
class Shape:
    points: List[Tuple[float, float]]
    closed: bool = False # means if the last point should connect back to first or not
    id: int = field(default_factory=_next_id)
    source: str = ""  # filename the shape was imported from

@dataclass
class ColorLayer:
    color:          str                = "#000000"     # default color
    operation:      str                = "Line Draw"   # type of operation: [Line Draw, Engrave, etc.]
    speed:          float              = 1200.0        #mm/min
    rapid_speed:    float              = 3000.0        #mm/min
    line_spacing:   float              = 1.0           #mm, for engraving
    line_angle:     str                = "Horizontal"  #either Horizontal or Vertical
    pass_count:     int                = 1
    shapes:         List[Shape]        = field(default_factory=list)

    @property
    def label(self) -> str:
        """Human-readable label for the tree widget"""
        return self.color.upper()


@dataclass
class Document:
    color_layers: List[ColorLayer] = field(default_factory=list)

    def get_or_create_color_layer(self, color: str) -> ColorLayer:
        """Find existing ColorLayer by color or create a new one."""

        color = _normalize_color(color)
        for cl in self.color_layers:
            if cl.color.upper() == color.upper():
                return cl
        cl = ColorLayer(color=color)
        self.color_layers.append(cl)
        return cl

    def find_shape(self, shape_id: int):
        """Find a shape and its parent ColorLayer by shape id"""
        for cl in self.color_layers:
            for shape in cl.shapes:
                if shape.id == shape_id:
                    return cl, shape

        return None, None

    def move_shape(self, shape_id: int, target_color: str):
        """
        Move a shape from its current ColorLayer to the target color's layer.
        Creates the target ColorLayer if it doesn't exist.
        Removes the source ColorLayer if it becomes empty.
        Returns (old_color_layer, new_color_layer, shape).
        """

        source_cl, shape = self.find_shape(shape_id)
        if source_cl is None:
            return None, None, None

        target_cl = self.get_or_create_color_layer(target_color)

        if source_cl.color.upper() == target_cl.color.upper():
            return source_cl, target_cl, shape

        source_cl.shapes.remove(shape)
        target_cl.shapes.append(shape)

        if not source_cl.shapes:
            self.color_layers.remove(source_cl)

        return source_cl, target_cl, shape

    def clear(self):
        self.color_layers.clear()