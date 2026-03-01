import math
import ezdxf
import ezdxf.colors
from core.document import Document, Shape, _normalize_color

DEFAULT_COLOR = "000000"

# DXF $INSUNITS values → mm conversion factors
INSUNITS_TO_MM = {
    0:  None,    # unitless — unknown, will auto-scale
    1:  25.4,    # inches
    2:  304.8,   # feet

    3:  1609344, # miles
    4:  1.0,     # millimetres
    5:  10.0,    # centimetres
    6:  1000.0,  # metres
    7:  None,    # microinches — unlikely, treat as unknown
    8:  25.4/1000, # mils (thou)
    9:  None,    # yards
    10: 1e-6,    # angstroms
    11: 1e-3,    # nanometres
    12: 1e-4,    # microns
    13: 100.0,   # decametres
    14: 10000.0, # hectometres
    15: 1000000, # gigametres
    16: None,    # astronomical units
    17: None,    # light years
    18: None,    # parsecs
    19: 25.4/32, # US survey feet
}

def _aci_to_hex(aci: int) -> str:
    """
    Convert an AutoCAD Color Index integer to #RRGGBB hex string.
    Uses ezdxf's built-in ACI table.
    Falls back to black for special values (0=BYBLOCK, 256=BYLAYER).
    """

    if aci in (0, 7, 256) or aci is None:
        return DEFAULT_COLOR
    try:
        r, g, b = ezdxf.colors.aci2rgb(aci)
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return DEFAULT_COLOR

def _get_entity_color(entity, dxf_layer_color: int) -> str:
    """
    Get the color of a DXF entity, resolving BYLAYER inheritance.
    Priority: entity color → layer color → black default.
    """

    try:
        aci = entity.dxf.color
    except Exception:
        aci = 256 # BYLAYER

    # INHERIT LAYER COLOR IF BYLAYER
    if aci == 256:
        aci = dxf_layer_color

    return _normalize_color(_aci_to_hex(aci))

def _get_units_scale(doc) -> float | None:
    """
    Read $INSUNITS from the DXF header and return the mm conversion factor.
    Returns None if units are unknown or not set.
    """
    try:
        insunits = doc.header.get("$INSUNITS", 0)
        return INSUNITS_TO_MM.get(insunits, None)
    except Exception:
        return None


def import_dxf(filepath: str, document: Document) -> list:
    """
    Parse a DXF file. Each unique color becomes a ColorLayer.
    Each DXF layer name becomes an ObjectLayer within the appropriate ColorLayer.
    Returns list of (color_layer, object_layer) tuples created.
    """

    doc         = ezdxf.readfile(filepath)
    msp         = doc.modelspace()
    units_scale = _get_units_scale(doc)

    # MAP of DXF layer -> color
    layer_colors: dict = {}
    for layer in doc.layers:
        try:
            layer_colors[layer.dxf.name] = layer.dxf.color
        except Exception:
            layer_colors[layer.dxf.name] = 7 #default white/black

    # Collect raw shapes with colors
    raw_shapes = []  # [(color, points, closed), ...]
    all_raw    = []

    for entity in msp:
        dxf_layer_name  = entity.dxf.layer if entity.dxf.hasattr("layer") else "0"
        dxf_layer_color = layer_colors.get(dxf_layer_name, 7)
        color           = _get_entity_color(entity, dxf_layer_color)
        result          = _entity_to_points(entity)
        if result:
            points, closed = result
            raw_shapes.append((color, points, closed))
            all_raw.extend(points)

    if not all_raw:
        return []

    # Flip y, since dxf is -y
    flipped = _flip_y_points(all_raw)
    # Compute scale transform
    transform = _compute_transform(flipped, units_scale)

    # Build a mapping from original point index to flipped point
    # by processing shapes in same order
    idx = 0
    affected_layers = []

    for color, raw_points, closed in raw_shapes:
        n           = len(raw_points)
        flipped_pts = flipped[idx:idx+n]
        idx        += n
        transformed = _apply_transform(flipped_pts, transform)
        shape       = Shape(points=transformed, closed=closed, source=filepath.split("\\")[-1].split("/")[-1])
        cl          = document.get_or_create_color_layer(color)
        cl.shapes.append(shape)
        if cl not in affected_layers:
            affected_layers.append(cl)

    return affected_layers

def _flip_y_points(points):

    if not points:
        return points
    min_y = min(p[1] for p in points)
    max_y = max(p[1] for p in points)
    return [(x, max_y + min_y - y) for (x, y) in points]

def _compute_transform(points, units_scale, work_w_mm=200, work_h_mm=280):
    if not points:
        return {"sx": 1, "sy": 1, "ox": 0, "oy": 0}

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    geom_w = max_x - min_x
    geom_h = max_y - min_y

    if geom_w == 0 or geom_h == 0:
        return {"sx": 1, "sy": 1, "ox": 0, "oy": 0}

    margin = 10

    if units_scale is not None:
        real_w = geom_w * units_scale
        real_h = geom_h * units_scale
        if real_w <= work_w_mm and real_h <= work_h_mm:
            print(f"[DXF] Exact size: {real_w:.1f} x {real_h:.1f} mm")
            return {
                "sx": units_scale,
                "sy": units_scale,
                "ox": -min_x * units_scale + margin,
                "oy": -min_y * units_scale + margin
            }
        else:
            scale = min((work_w_mm - 2 * margin) / real_w,
                        (work_h_mm - 2 * margin) / real_h) * units_scale
            print(f"[DXF] Scaled down from {real_w:.1f} x {real_h:.1f} mm")
    else:
        scale = min((work_w_mm - 2 * margin) / geom_w,
                    (work_h_mm - 2 * margin) / geom_h)
        print(f"[DXF] Unknown units — auto-scaled")

    return {"sx": scale, "sy": scale,
            "ox": -min_x * scale + margin,
            "oy": -min_y * scale + margin}

def _apply_transform(points, transform):
    sx, sy = transform["sx"], transform["sy"]
    ox, oy = transform["ox"], transform["oy"]
    return [(x * sx + ox, y * sy + oy) for (x, y) in points]


# ── Entity converters ─────────────────────────────────────────────────────────
def _entity_to_points(entity):
    """Returns (points, closed) or None for unsupported entities."""
    t = entity.dxftype()
    if t == "LINE":
        return _line(entity)
    elif t == "CIRCLE":
        return _circle(entity)
    elif t == "ARC":
        return _arc(entity)
    elif t in ("LWPOLYLINE", "POLYLINE"):
        return _polyline(entity)
    elif t == "SPLINE":
        return _spline(entity)
    return None

def _line(entity):
    start = entity.dxf.start
    end = entity.dxf.end
    return [(start.x, start.y), (end.x, end.y)], False

def _circle(entity):
    cx, cy, r = entity.dxf.center.x, entity.dxf.center.y, entity.dxf.radius
    points = [
        (cx + r * math.cos(math.radians(i * 5)),
         cy + r * math.sin(math.radians(i * 5)))
        for i in range(72)
    ]
    return points, True

def _arc(entity):
    cx, cy, r = entity.dxf.center.x, entity.dxf.center.y, entity.dxf.radius
    start_angle, end_angle = entity.dxf.start_angle, entity.dxf.end_angle

    if end_angle <= start_angle:
        end_angle += 360

    span    = end_angle - start_angle
    samples = max(3, int(span))

    points = [
        (cx + r * math.cos(math.radians(start_angle + span * i / samples)),
         cy + r * math.sin(math.radians(start_angle + span * i / samples)))
        for i in range(samples + 1)
    ]
    return points, False


def _polyline(entity):
    if entity.dxftype() == "LWPOLYLINE":
        points = [(v[0], v[1]) for v in entity.vertices()]
        closed = bool(entity.dxf.flags & 1)
    else:
        points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
        closed = bool(entity.dxf.flags & 1)

    return (points, closed) if len(points) >- 2 else None


def _spline(entity):
    points = [(p.x, p.y) for p in entity.flattening(0.05)]
    closed = bool(entity.dxf.flags & 1)
    return (points, closed) if len(points) >= 2 else None