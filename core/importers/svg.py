from svgpathtools import svg2paths
from core.document import Document, Shape, _normalize_color
import xml.etree.ElementTree as ET
import re

DEFAULT_COLOR = "000000"


NAMED_COLORS = {
    "black"         : "#000000",
    "white"         : "#FFFFFF",
    "red"           : "#FF0000",

    "green"         : "#008000",
    "blue"          : "#0000FF",
    "yellow"        : "#FFFF00",
    "cyan"          : "#00FFFF",
    "magenta"       : "#FF00FF",
    "orange"        : "#FFA500",
    "purple"        : "#800080",
    "gray"          : "#808080",
    "grey"          : "#808080",
    "none"          : None,
    "transparent"   : None,
}

def parse_mm(value: str):
    """
    Parse an SVG dimension string and convert to mm.
    Handles: '37.5mm', '100px', '2.8363' (unitless = user units)
    Returns None if unparseable.
    """

    if value is None:
        return None
    value = value.strip()
    m = re.match(r"^([\d.]+)\s*(mm|px|cm|in|pt)?$", value)
    if not m:
        return None
    num  = float(m.group(1))
    unit = m.group(2) or ""
    conversions = {
        "mm": 1.0,
        "cm": 10.0,
        "in": 25.4,
        "pt": 25.4 / 72,
        "px": 25.4 / 96,
        "":   25.4 / 96,
    }
    return num * conversions.get(unit, 25.4 / 96)


def get_svg_dimensions(filepath: str):
    """
    Read the SVG file and extract real-world width/height in mm and viewBox.
    Returns (width_mm, height_mm, vb_x, vb_y, vb_w, vb_h).
    """

    tree = ET.parse(filepath)
    root = tree.getroot()
    width_mm  = parse_mm(root.get("width"))
    height_mm = parse_mm(root.get("height"))
    vb = root.get("viewBox")

    if vb:
        parts = re.split(r"[\s,]+", vb.strip())
        if len(parts) == 4:
            vb_x, vb_y, vb_w, vb_h = [float(p) for p in parts]
        else:
            vb_x = vb_y = vb_w = vb_h = None
    else:
        vb_x = vb_y = vb_w = vb_h = None

    return width_mm, height_mm, vb_x, vb_y, vb_w, vb_h


# ---------- COLOR PARSING ----------

def _parse_svg_color(value: str) -> str:
    """
    Parse any SVG color string into a normalized #RRGGBB hex string.
    Returns DEFAULT_COLOR if the color is missing, 'none', or unparseable.
    """

    if not value:
        return DEFAULT_COLOR

    value = value.strip().lower()

    if value in ("none", "transparent"):
        return DEFAULT_COLOR

    if value in NAMED_COLORS:
        return NAMED_COLORS[value] or DEFAULT_COLOR

    # RGB shorthand -> expand to #RRGGBB
    m = re.match(r"^#([0-9a-f])([0-9a-f])([0-9a-f])$", value)
    if m:
        return f"#{m.group(1)*2}{m.group(2)*2}{m.group(3)*2}".upper()

    # FOR CASE OF #RRGGBB
    if re.match(r"^#[0-9a-f]{6}$", value):
        return value.upper()

    # rgb(r, g, b)
    m = re.match(r"^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$", value)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"#{r:02X}{g:02X}{b:02X}"

    return DEFAULT_COLOR

def _extract_color(attributes: dict) -> str:
    """
        Extract stroke color from a path's SVG attributes dict.
        We care about stroke for CNC/plotter — not fill.
        Checks 'style' attribute first, then direct 'stroke' attribute.
    """
    # CHECK style ATTRIBUTE
    style = attributes.get("style", "")
    if style:
        m = re.search(r"stroke\s*:\s*([^;]+)", style)
        if m:
            color = _parse_svg_color(m.group(1).strip())
            if color != DEFAULT_COLOR or m.group(1).strip().lower() == "black":
                return color

    # CHECK stroke ATTRIBUTE
    stroke = attributes.get("stroke", "")
    if stroke:
        return _parse_svg_color(stroke)

    # DEFAULT VALUE
    return DEFAULT_COLOR

# ---------- Geometry ----------

def sample_segment(segment, samples: int = 20):
    """Sample a path segment into a list of (x, y) points in raw SVG units."""
    points = []
    for i in range(samples + 1):
        t = i / samples
        pt = segment.point(t)
        points.append((pt.real, pt.imag))
    return points


def import_svg(filepath: str, document: Document, source_name: str = None) -> list:
    """
    Parse an SVG file. Each path becomes a Shape added directly to the
    matching ColorLayer (created if needed).
    Returns list of ColorLayers that received shapes.
    """
    paths, attributes_list = svg2paths(filepath)
    source = source_name or filepath.replace("\\", "/").split("/")[-1]

    # Collect all raw points for transform computation
    all_raw = []
    path_data = []  # [(color, points, closed), ...]

    for path, attributes in zip(paths, attributes_list):
        color = _normalize_color(_extract_color(attributes))
        all_points = []
        for segment in path:
            pts = sample_segment(segment, samples=20)
            if all_points:
                pts = pts[1:]
            all_points.extend(pts)
        if len(all_points) < 2:
            continue
        dx = all_points[0][0] - all_points[-1][0]
        dy = all_points[0][1] - all_points[-1][1]
        closed = (dx*dx + dy*dy) < 0.01
        path_data.append((color, all_points, closed))
        all_raw.extend(all_points)

    if not all_raw:
        return []

    transform = _compute_transform(all_raw, filepath)
    affected_layers = []

    for color, raw_points, closed in path_data:
        transformed = _apply_transform(raw_points, transform)
        shape = Shape(points=transformed, closed=closed, source=source)
        cl = document.get_or_create_color_layer(color)
        cl.shapes.append(shape)
        if cl not in affected_layers:
            affected_layers.append(cl)

    return affected_layers
def _compute_transform(all_points, filepath, work_w_mm=200, work_h_mm=280):
    """
        Compute (scale_x, scale_y, offset_x, offset_y) to convert
        raw SVG units to mm. Returns a dict.
    """

    width_mm, height_mm, vb_x, vb_y, vb_w, vb_h = get_svg_dimensions(filepath)

    scale_x = scale_y = None
    offset_x = offset_y = 0.0

    if width_mm and height_mm and vb_w and vb_h and vb_w > 0 and vb_h > 0:
        scale_x     = width_mm / vb_w
        scale_y     = height_mm / vb_h
        offset_x    = -(vb_x or 0) * scale_x
        offset_y    = -(vb_y or 0) * scale_y
        if width_mm > work_w_mm or height_mm > work_h_mm:
            scale_x = scale_y = None

    if scale_x is None:
        xs = [p[0] for p in all_points]
        ys = [p[1] for p in all_points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        geom_w = max_x - min_x
        geom_h = max_y - min_y
        if geom_w == 0 or geom_h == 0:
            return {"sx": 1, "sy": 1, "ox": 0, "oy": 0}
        margin      = 10
        scale       = min((work_w_mm - 2 * margin) / geom_w,
                          (work_h_mm - 2 * margin) / geom_h)
        scale_x     = scale_y = scale
        offset_x    = -min_x * scale + margin
        offset_y    = -min_y * scale + margin

    return {"sx": scale_x, "sy": scale_y, "ox": offset_x, "oy": offset_y}

def _apply_transform(points, transform):
    sx, sy = transform["sx"], transform["sy"]
    ox, oy = transform["ox"], transform["oy"]
    return [(x * sx + ox, y * sy + oy) for (x, y) in points]