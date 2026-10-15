"""Marissa, the singer of the House of Pleasure, as one separate, editable asset (user request 2026-10-07).

Run:  "D:\\Blender\\blender.exe" -b --factory-startup --python scripts/assets/build_marissa.py -- [--out PATH]

Evidence
  * Character/Marissa/Marissa.png (user supplied, 202 x 378 px, front view, transparent background): shapes, proportions
    and colours of every part seen from the front (A). Its depth, back sides and hidden parts are completion (C).
  * 00_Master/master_map.png.png, House of Pleasure stage (crop C1): she floats over the stage, wing tip to lowest tendril
    118 master px = 2.36 H at 50 master px per H (D-102). That sets the size; the drawing sets the shapes.
  * 02_Marissa/Marissa.jpg: the same figure in game (wings in a V, tendrils splayed); used to confirm the reading.
Pose (read from the front drawing, stated to the user before building): facing forward, upright and floating, arms hanging a
little away from the body, butterfly wings raised in a V behind her, the hair swept to her left (+X). The flat drawing is not
read for anything else; wing sweep, lean and camber are completion.

Asset frame and units: 1 = H (project yardstick). She faces -Y, X to the viewer's right (her left), floor (the stage) at Z = 0;
her lowest point floats HOVER above it. Drawing px -> H: S per px, centre line x = CX, lowest point y = Y_FOOT.
This script does not touch the city files; the saved scene holds only the asset plus a look-dev stage in its own collection.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from cot_geo import Geo, TAU, lerp, smoothstep, spow  # noqa: E402

ASSET = "Marissa"
VERSION = "v002"
REF_ART = "Character/Marissa/Marissa.png"
REF_MAP = "00_Master/master_map.png.png, House of Pleasure stage (master px 20416-20468 x 7896-8014; crop C1)"
REF_SHOT = "02_Marissa/Marissa.jpg"
CITY_SPOT = {"region": "HouseOfPleasure", "element": "StagePlatform", "master_px": [20441, 7955],
             "note": "floats over the raised stage in front of the round canopy; not placed in the city by this script"}

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(argv[argv.index("--out") + 1]) if "--out" in argv else ROOT / "assets" / "hero" / f"{ASSET}_{VERSION}" / f"{ASSET}_{VERSION}.blend"

# ------------------------------------------------------------------ measurements
HEIGHT = 2.36              # wing tip to lowest tendril (master map, A)
S = HEIGHT / 371.0         # H per drawing px (figure spans y 2..373 in the drawing)
CX, Y_FOOT = 103.5, 373.0  # body centre line and lowest point in the drawing
HOVER = 0.35               # gap under the tendrils (C: on the master she floats clear of the stage lip)

HEAD_Y = (148.0, 191.0)    # head top (under the hair) and chin in the drawing (A)
HEAD_C = Vector((0.0, 0.0, 0.0))    # set below from HEAD_Y
HEAD_HZ = 0.0
MASK_W = [(148, 0.0), (149, 12.0), (151, 20.0), (154, 25.0), (158, 28.0), (165, 29.5), (172, 29.0), (178, 26.5), (183, 21.0),
          (187, 13.0), (189.5, 6.0), (191, 0.0)]   # half width (px) of the mask at drawing y (A: front outline; top under the hair B)
MASK_D, MASK_P = 0.115, 2.6       # half depth (C) and the superellipse exponent of its sections (rounded-square, C)
EYE_X, EYE_Y = 13.8, 176.0        # eye centres +-13.8 px from the head centre line, at drawing y 176 (A)
EYE_R = (0.040, 0.044)            # 12.5 x 14 px ovals (A); upright (the drawing leans both eyes the same way: a head roll, not adopted)

WING_FORE = dict(sweep=20.0, lean=-14.0, bend=0.10, L=1.3, y0=0.100)   # C: swept and leaned back so the V reads in depth and clears the head
WING_HIND = dict(sweep=24.0, lean=6.0, bend=0.05, L=0.6, y0=0.135)    # C: behind the fore wing where they overlap

MATS = {}


def P(x, y):
    """Drawing px -> (X, Z) in H."""
    return (x - CX) * S, HOVER + (Y_FOOT - y) * S


def srgb(r, g, b):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin(r), lin(g), lin(b))


# colours sampled from the drawing (sRGB px values)
C_MASK = srgb(255, 246, 228)
C_MASK_CHIN = srgb(236, 222, 210)
C_EYE = srgb(21, 35, 65)
C_HAIR = srgb(255, 235, 177)
C_HAIR_INK = srgb(205, 150, 113)
C_BODY = srgb(156, 99, 107)
C_BODY_DARK = srgb(128, 76, 88)
C_PLATE = srgb(164, 155, 148)
C_NAVY = srgb(21, 35, 65)
C_WING_LIGHT = srgb(253, 207, 210)
C_WING_MID = srgb(237, 168, 189)
C_WING_DEEP = srgb(214, 138, 168)
C_VEIN = srgb(130, 87, 134)
C_SPOT = srgb(255, 240, 223)


# ================================================================== materials
class Nodes:
    def __init__(self, name):
        self.mat = bpy.data.materials.new(name)
        self.mat.use_nodes = True
        self.nt = self.mat.node_tree
        self.nt.nodes.clear()
        self.out = self.nt.nodes.new("ShaderNodeOutputMaterial")

    def new(self, kind, **props):
        node = self.nt.nodes.new(kind)
        for k, v in props.items():
            setattr(node, k, v)
        return node

    def link(self, a, b):
        self.nt.links.new(a, b)

    def _feed(self, sock, val):
        if isinstance(val, bpy.types.NodeSocket):
            self.link(val, sock)
        else:
            sock.default_value = val

    def math(self, op, a, b=None):
        node = self.new("ShaderNodeMath", operation=op)
        self._feed(node.inputs[0], a)
        if b is not None:
            self._feed(node.inputs[1], b)
        return node.outputs[0]

    def vmath(self, op, a, b=None):
        node = self.new("ShaderNodeVectorMath", operation=op)
        self._feed(node.inputs[0], a)
        if b is not None:
            self._feed(node.inputs[1], b)
        return node.outputs["Value"] if op in ("LENGTH", "DOT_PRODUCT", "DISTANCE") else node.outputs["Vector"]

    def mix(self, fac, a, b):
        node = self.new("ShaderNodeMix", data_type="RGBA")
        self._feed(node.inputs[0], fac)
        self._feed(node.inputs[6], (*a, 1.0) if isinstance(a, tuple) else a)
        self._feed(node.inputs[7], (*b, 1.0) if isinstance(b, tuple) else b)
        return node.outputs[2]

    def map_range(self, val, a, b, c=0.0, d=1.0):
        node = self.new("ShaderNodeMapRange")
        self._feed(node.inputs["Value"], val)
        node.inputs["From Min"].default_value = a
        node.inputs["From Max"].default_value = b
        node.inputs["To Min"].default_value = c
        node.inputs["To Max"].default_value = d
        return node.outputs["Result"]

    def bsdf(self, color, rough, spec=0.35, sheen=0.0):
        node = self.new("ShaderNodeBsdfPrincipled")
        node.inputs["Roughness"].default_value = rough
        if "Specular IOR Level" in node.inputs:
            node.inputs["Specular IOR Level"].default_value = spec
        if sheen and "Sheen Weight" in node.inputs:
            node.inputs["Sheen Weight"].default_value = sheen
        if isinstance(color, tuple):
            node.inputs["Base Color"].default_value = (*color, 1.0)
        else:
            self.link(color, node.inputs["Base Color"])
        self.link(node.outputs["BSDF"], self.out.inputs["Surface"])
        return node


def plain(key, color, rough=0.5, spec=0.35, sheen=0.0):
    n = Nodes("MAT_MAR_" + key)
    n.bsdf(color, rough, spec, sheen)
    n.mat.diffuse_color = (*color, 1.0)
    MATS[key] = n.mat
    return n.mat


def graded(key, top, bottom, z0, z1, rough=0.45):
    """Colour over object-space Z (mask: warm white, a little deeper toward the chin)."""
    n = Nodes("MAT_MAR_" + key)
    sep = n.new("ShaderNodeSeparateXYZ")
    n.link(n.new("ShaderNodeTexCoord").outputs["Object"], sep.inputs[0])
    n.bsdf(n.mix(n.map_range(sep.outputs["Z"], z0, z1), bottom, top), rough)
    n.mat.diffuse_color = (*top, 1.0)
    MATS[key] = n.mat
    return n.mat


def wing_material(key, spots=None, tip=None, deep_r=(0.04, 0.34)):
    """Wing membrane. Object space of a wing = its drawing-derived 2D frame (|X| outward from the root, Z up), the same
    for the mirrored wing, so one material paints both. Deeper pink near the root, light tip zone above a curved line
    (fore wing), cream spots with a purple ring (fore wing). The light outer rim is a separate face material."""
    n = Nodes("MAT_MAR_" + key)
    sep = n.new("ShaderNodeSeparateXYZ")
    n.link(n.new("ShaderNodeTexCoord").outputs["Object"], sep.inputs[0])
    ax = n.math("ABSOLUTE", sep.outputs["X"])
    z = sep.outputs["Z"]
    flat = n.new("ShaderNodeCombineXYZ")
    n.link(ax, flat.inputs["X"])
    n.link(z, flat.inputs["Z"])
    rr = n.vmath("LENGTH", flat.outputs["Vector"])
    col = n.mix(n.map_range(rr, *deep_r), C_WING_DEEP, C_WING_MID)
    if tip:
        a0, x0, k, zc = tip                     # tip line in drawing px: y = zc - k (x - x0)^2, converted to the wing frame
        q = n.math("SUBTRACT", a0, n.math("DIVIDE", ax, S))
        zb = n.math("MULTIPLY", n.math("ADD", zc, n.math("MULTIPLY", k, n.math("POWER", q, 2.0))), S)
        col = n.mix(n.math("GREATER_THAN", z, zb), col, C_WING_LIGHT)
    if spots:
        inside = ring = None
        for (cx, cz), (rx, rz), tilt, ring_w in spots:
            v = n.vmath("SUBTRACT", flat.outputs["Vector"], (cx, 0.0, cz))
            rot = n.new("ShaderNodeVectorRotate", rotation_type="Y_AXIS")
            n.link(v, rot.inputs["Vector"])
            rot.inputs["Angle"].default_value = -tilt
            d = n.vmath("LENGTH", n.vmath("MULTIPLY", rot.outputs["Vector"], (1.0 / rx, 0.0, 1.0 / rz)))
            i_ = n.math("LESS_THAN", d, 1.0)
            r_ = n.math("LESS_THAN", d, 1.0 + ring_w)
            inside = i_ if inside is None else n.math("MAXIMUM", inside, i_)
            ring = r_ if ring is None else n.math("MAXIMUM", ring, r_)
        col = n.mix(ring, col, C_VEIN)
        col = n.mix(inside, col, C_SPOT)
    n.bsdf(col, 0.42, spec=0.4, sheen=0.25)
    n.mat.diffuse_color = (*C_WING_MID, 1.0)
    MATS[key] = n.mat
    return n.mat


def ink_material(key, color):
    """Contour ink for the inverted hulls: the hull's near side is transparent, its far side shows past the
    silhouette as a line (same method as the city's MAT_S2_outline and Quirrel's MAT_QB_ink)."""
    n = Nodes("MAT_MAR_" + key)
    geo = n.new("ShaderNodeNewGeometry")
    clear = n.new("ShaderNodeBsdfTransparent")
    ink = n.new("ShaderNodeEmission")
    ink.inputs["Color"].default_value = (*color, 1.0)
    ink.inputs["Strength"].default_value = 1.0
    mix = n.new("ShaderNodeMixShader")
    n.link(geo.outputs["Backfacing"], mix.inputs["Fac"])
    n.link(clear.outputs["BSDF"], mix.inputs[1])
    n.link(ink.outputs["Emission"], mix.inputs[2])
    n.link(mix.outputs["Shader"], n.out.inputs["Surface"])
    try:
        n.mat.surface_render_method = "BLENDED"
    except Exception:
        pass
    n.mat.use_backface_culling = True
    n.mat.diffuse_color = (*color, 1.0)
    MATS[key] = n.mat
    return n.mat


# fore wing tip zone and spots, in the fore wing's frame (attach px FORE_A)
FORE_A = (96.0, 205.0)
HIND_A = (96.0, 214.0)


def fw(x, y, a=FORE_A):
    """Drawing px of the left wing -> wing frame (X outward, Z up), H."""
    return (a[0] - x) * S, (a[1] - y) * S


TIP_LINE = (FORE_A[0] - 43.0, 43.0, 0.0049, FORE_A[1] - 109.0)   # drawing: y = 109 - 0.0049 (x - 43)^2, x 19..69 (A)
SPOTS_PX = [((28.8, 53.8), (5.0, 8.8), 8.0), ((30.6, 78.8), (6.9, 7.5), 0.0),
            ((41.9, 71.9), (3.1, 5.8), 0.0), ((47.5, 98.8), (5.0, 8.8), 20.0)]   # (centre, radii, tilt deg) in drawing px (A)


def make_materials():
    graded("mask", C_MASK, C_MASK_CHIN, -0.12, -0.03)
    plain("eye", C_EYE, 0.5)
    plain("hair", C_HAIR, 0.55, sheen=0.3)
    plain("body", C_BODY, 0.55)
    plain("body_dark", C_BODY_DARK, 0.55)
    plain("plate", C_PLATE, 0.45)
    plain("navy", C_NAVY, 0.45)
    plain("wing_rim", C_WING_LIGHT, 0.45, spec=0.4, sheen=0.25)
    plain("vein", C_VEIN, 0.5)
    spots = []
    for (x, y), (rx, ry), tilt in SPOTS_PX:
        cx, cz = fw(x, y)
        spots.append(((cx, cz), (rx * S, ry * S), math.radians(tilt), 1.6 / min(rx, ry)))
    a0, x0, k, zc = TIP_LINE
    wing_material("wing_fore", spots=spots, tip=(a0, x0, k, zc), deep_r=(0.06, 0.40))
    wing_material("wing_hind", deep_r=(0.04, 0.30))
    ink_material("ink", C_NAVY)
    ink_material("ink_wing", srgb(104, 62, 106))
    ink_material("ink_hair", C_HAIR_INK)
    plain("stage_floor", (0.018, 0.024, 0.050), 0.6)


# ================================================================== scene helpers
def collection(name, parent=None):
    coll = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def root_empty(name, coll, props):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = 0.5
    for k, v in props.items():
        e[k] = v
    coll.objects.link(e)
    return e


def ink_hull(obj, coll, thickness, key="ink"):
    """Inverted hull sharing the mesh: same subdivision, pushed out along the normals, ink on every slot."""
    # Thick hulls fold through narrow gown tips and wing veins. Keep their
    # contours thinner; the solid source geometry and wing markings stay intact.
    cfg = json.loads((ROOT / "config/marissa_surface_fix.json").read_text(encoding="utf-8"))
    for prefix, strength in cfg["contour_strength"].items():
        if obj.name.startswith(prefix):
            thickness = strength
    hull = bpy.data.objects.new(obj.name + "_Ink", obj.data)
    coll.objects.link(hull)
    hull.parent = obj.parent
    hull.matrix_parent_inverse = obj.matrix_parent_inverse.copy()
    hull.matrix_basis = obj.matrix_basis.copy()
    for slot in hull.material_slots:
        slot.link = "OBJECT"
        slot.material = MATS[key]
    for mod in obj.modifiers:
        if mod.type == "SUBSURF":
            sub = hull.modifiers.new("Subsurf", "SUBSURF")
            sub.levels, sub.render_levels = mod.levels, mod.render_levels
    disp = hull.modifiers.new("InkInflate", "DISPLACE")
    disp.direction = "NORMAL"
    disp.mid_level = 0.0
    disp.strength = thickness
    for attr in ("visible_shadow", "visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter"):
        setattr(hull, attr, False)
    hull["cot_ink_of"] = obj.name
    hull["cot_role"] = "contour"
    return hull


def mesh_part(name, g, coll, parent, ev, note, m=None, subsurf=0, ink=None, ink_coll=None, ink_key="ink"):
    obj = g.to_object(name, coll, lambda k: MATS[k], props={"cot_id": name, "cot_ev": ev, "cot_ref": REF_ART, "cot_note": note})
    obj.matrix_world = m if m is not None else Matrix.Identity(4)
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()
    if subsurf:
        mod = obj.modifiers.new("Subsurf", "SUBSURF")
        mod.levels = 1
        mod.render_levels = subsurf
    if ink:
        ink_hull(obj, ink_coll, ink, ink_key)
    return obj


def catmull(points, per=6, closed=False):
    """Smooth path through key points (Catmull-Rom). Open paths keep their end points."""
    pts = [Vector(p) for p in points]
    if closed:
        n = len(pts)
        out = []
        for i in range(n):
            p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
            for k in range(per):
                out.append(_cr(p0, p1, p2, p3, k / per))
        return out
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        for k in range(per):
            out.append(_cr(ext[i - 1], ext[i], ext[i + 1], ext[i + 2], k / per))
    out.append(pts[-1])
    return out


def _cr(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


def resample_closed(pts, n):
    """n points equally spaced by arc length along a closed polyline."""
    chain = pts + [pts[0]]
    lens = [(chain[i + 1] - chain[i]).length for i in range(len(pts))]
    cum = [0.0]
    for L in lens:
        cum.append(cum[-1] + L)
    total = cum[-1]
    out, i = [], 0
    for k in range(n):
        d = total * k / n
        while i < len(lens) - 1 and cum[i + 1] < d:
            i += 1
        t = (d - cum[i]) / max(lens[i], 1e-12)
        out.append(chain[i].lerp(chain[i + 1], t))
    return out


def jointed(points, fillet=0.02, per=5):
    """Straight segments between joints, each joint rounded by a short fillet (as Quirrel's limbs)."""
    Pp = [Vector(p) for p in points]
    out = [Pp[0]]
    for i in range(1, len(Pp) - 1):
        a, j, b = Pp[i - 1], Pp[i], Pp[i + 1]
        p1 = j + (a - j).normalized() * min(fillet, (a - j).length * 0.4)
        p2 = j + (b - j).normalized() * min(fillet, (b - j).length * 0.4)
        last = out[-1]
        out += [last.lerp(p1, k / per) for k in range(1, per + 1)]
        out += [(1 - t) ** 2 * p1 + 2 * (1 - t) * t * j + t * t * p2 for t in (0.25, 0.5, 0.75)]
        out.append(p2)
    last = out[-1]
    out += [last.lerp(Pp[-1], k / per) for k in range(1, per + 1)]
    return out


def taper(n, r0, r1, tip=None):
    out = [lerp(r0, r1, i / (n - 1)) for i in range(n)]
    if tip:
        for k in range(tip):
            out[n - 1 - k] *= (k + 0.4) / (tip + 0.4)
    return out


def pxy(x, y, d=0.0):
    """Drawing px + depth (H) -> 3D point."""
    X, Z = P(x, y)
    return Vector((X, d, Z))


# ================================================================== head
def _setup_head():
    global HEAD_C, HEAD_HZ
    zt, zb = P(0, HEAD_Y[0])[1], P(0, HEAD_Y[1])[1]
    HEAD_C = Vector((0.0, -0.015, (zt + zb) / 2))    # a little forward of the body axis (C)
    HEAD_HZ = (zt - zb) / 2


_setup_head()


def mask_w(t):
    """Half width (H) of the mask at normalised height t (+1 top, -1 chin), from the drawing's outline."""
    y = lerp(HEAD_Y[1], HEAD_Y[0], (t + 1.0) / 2.0)
    for (y0, w0), (y1, w1) in zip(MASK_W, MASK_W[1:]):
        if y0 <= y <= y1:
            return lerp(w0, w1, (y - y0) / (y1 - y0)) * S
    return 0.0


def mask_d(t):
    return MASK_D * max(0.0, 1.0 - t * t) ** 0.42 * (0.82 + 0.18 * (t + 1.0) / 2.0)   # a little shallower toward the chin (C)


def se(v, p=MASK_P):
    return math.copysign(abs(v) ** (2.0 / p), v)


def mask_pt(t, b):
    """Point on the mask (head-local): t normalised height, b longitude (b = -90 deg the face, +90 deg the back, 0 her left)."""
    w, d = mask_w(t), mask_d(t)
    y = d * se(math.sin(b))
    if y < 0.0:
        y *= 0.88                                  # flatter face
    return Vector((w * se(math.cos(b)), y, t * HEAD_HZ))


def mask_front(x, z):
    """Front (-Y) surface of the mask at head-local (x, z); None off the mask."""
    t = z / HEAD_HZ
    w, d = mask_w(t), mask_d(t)
    if w <= 0.0 or abs(x) >= w:
        return None
    return -0.88 * d * (1.0 - abs(x / w) ** MASK_P) ** (1.0 / MASK_P)


FRINGE = [(-90, 0.17), (-120, 0.33), (-150, 0.50), (180, 0.56), (150, 0.40), (120, 0.0), (90, -0.5), (60, -0.55), (30, -0.5),
          (0, -0.42), (-30, -0.28), (-60, -0.05)]   # (longitude deg, normalised height) of the hair's lower edge: brow front at drawing
                                                    # y 165 (A), her right brow y 158 (A), her left side down past the eyes where the
                                                    # lock covers the side of the face (A); back C


def fringe_t(b):
    deg = (math.degrees(b) + 180.0) % 360.0 - 180.0
    pts = sorted(FRINGE)
    ext = [(pts[-1][0] - 360.0, pts[-1][1])] + pts + [(pts[0][0] + 360.0, pts[0][1])]
    for (b0, l0), (b1, l1) in zip(ext, ext[1:]):
        if b0 <= deg <= b1:
            t = (deg - b0) / (b1 - b0)
            return lerp(l0, l1, 0.5 - 0.5 * math.cos(math.pi * t))
    return pts[0][1]


def head_normal(t, b):
    e = 1e-3
    p = mask_pt(t, b)
    du = mask_pt(min(0.999, t + e), b) - mask_pt(max(-0.999, t - e), b)
    dv = mask_pt(t, b + e) - mask_pt(t, b - e)
    n = dv.cross(du)
    if n.length < 1e-9:
        return Vector((0, 0, 1 if t > 0 else -1))
    n.normalize()
    return n if n.dot(p) >= 0 else -n


def build_head(coll, ink_coll, root):
    MH = Matrix.Translation(HEAD_C)
    g = Geo()
    g.use("mask")
    rows = []
    for k in range(1, 30):
        t = math.sin(math.pi / 2 * (1.0 - 2.0 * k / 30))       # denser toward top and chin
        rows.append([mask_pt(t, TAU * i / 56) for i in range(56)])
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)
    mesh_part("MAR_Mask", g, coll, root, "A", "warm white mask, front outline traced row by row from the drawing (wide, squarish brow, pointed chin, A); depth C",
              m=MH, subsurf=1, ink=0.010, ink_coll=ink_coll)

    # ---- eyes: dark ovals laid on the face as thin curved shells following the mask (so their full size shows)
    g = Geo()
    g.use("eye")
    cz = P(0, EYE_Y)[1] - HEAD_C.z
    for sx in (-1, 1):
        cx = sx * EYE_X * S
        rows_t, rows_b = [], []
        for k in range(1, 9):
            rho = k / 8
            rt, rb_ = [], []
            for i in range(32):
                ph = TAU * i / 32
                x, z = cx + EYE_R[0] * rho * math.cos(ph), cz + EYE_R[1] * rho * math.sin(ph)
                y = mask_front(x, z)
                lift = 0.003 * (1.0 - rho ** 6) + 0.0012
                rt.append((x, y - lift, z))
                rb_.append((x, y + 0.004, z))
            rows_t.append(rt)
            rows_b.append(rb_)
        g.grid(rows_t + list(reversed(rows_b)), close_u=True, cap_start=True, cap_end=True)
    mesh_part("MAR_Eyes", g, coll, root, "A", "two large dark ovals (12.5 x 14 px) laid on the mask, upright (the drawing's slight lean is a head roll, not adopted)",
              m=MH, subsurf=1)

    # ---- hair: a cap over the top and back of the head, fringe low across the brow (A), and a full lock down her left
    #      side of the face ending in a curl turned back in (A front; depth C)
    g = Geo()
    g.use("hair")
    nb, nu = 72, 12
    outer, inner = [], []
    rim, under = [], []
    for k in range(nu + 1):
        u = k / nu                                     # 0 at the fringe, 1 at the crown
        ro, ri = [], []
        for i in range(nb):
            b = TAU * i / nb
            t = lerp(fringe_t(b), 0.985, u ** 0.85)
            q = mask_pt(t, b)
            n = head_normal(t, b)
            th = 0.016 + 0.016 * (1.0 - u) + 0.014 * max(0.0, -math.cos(b)) * (1.0 - u)   # fuller over her right brow (A)
            th = 0.005 + (th - 0.005) * smoothstep(u / 0.3)                               # thins to a small lip at the fringe (no ledge)
            ro.append(q + n * th)
            ri.append(q - n * 0.012)
            if k == 0:
                rim.append(q + n * 0.0035)
                under.append(q + n * 0.0012)
        outer.append(ro)
        inner.append(ri)
    g.grid(list(reversed(outer)) + [rim, under] + inner, close_u=True, cap_start=True, cap_end=True)
    wave = [(124, 151, -0.006, 9), (135, 158, 0.0, 11), (143, 167, 0.008, 13), (151, 179, 0.016, 16.5), (154, 190, 0.026, 15.5),
            (152, 199, 0.034, 11), (146, 206, 0.040, 7.5), (139, 208, 0.044, 4.2), (136, 203, 0.044, 1.5)]
    per = 6
    path = catmull([pxy(x, y, d) - HEAD_C for x, y, d, _ in wave], per=per)
    widths = interp_keys([w * S for *_, w in wave], per)
    thick = [lerp(0.046, 0.016, (i / (len(path) - 1)) ** 0.8) for i in range(len(path))]   # full lock, not a flat sheet (C)
    g.tube(path, thick, widths, segs=16, ref=(0, 1, 0))
    mesh_part("MAR_Hair", g, coll, root, "A", "blonde cap with the fringe low across the brow and a full lock down her left side ending in a curl (A); back of the head C",
              m=MH, subsurf=1, ink=0.009, ink_coll=ink_coll, ink_key="ink_hair")


def interp_keys(vals, per):
    """Per-point values along a catmull(..., per) path through len(vals) keys."""
    out = []
    for i in range(len(vals) - 1):
        out += [lerp(vals[i], vals[i + 1], k / per) for k in range(per)]
    out.append(vals[-1])
    return out


# ================================================================== body
PLATE_W = 0.058      # breast plate half width at its widest (19 px, A)
THORAX = [(1.405, 0.066, 0.054), (1.374, 0.082, 0.066), (1.33, 0.080, 0.064), (1.291, 0.075, 0.060), (1.24, 0.066, 0.053),
          (1.196, 0.055, 0.045), (1.16, 0.042, 0.036), (1.132, 0.033, 0.029), (1.105, 0.031, 0.027)]   # (z, half width A, half depth C)


def thorax_at(z):
    for (z0, w0, d0), (z1, w1, d1) in zip(THORAX, THORAX[1:]):
        if z1 <= z <= z0:
            t = (z0 - z) / (z0 - z1)
            return lerp(w0, w1, t), lerp(d0, d1, t)
    return (THORAX[0][1], THORAX[0][2]) if z > THORAX[0][0] else (THORAX[-1][1], THORAX[-1][2])


def loft(g, secs, segs=24, flutes=0, fdepth=0.0):
    """secs: [(cx, cy, z, half width, half depth)] top to bottom; closed with caps."""
    rows = []
    for cx, cy, z, hw, hd in secs:
        row = []
        for i in range(segs):
            a = TAU * i / segs
            k = 1.0 - fdepth + fdepth * abs(math.sin(flutes * a / 2)) ** 0.6 if flutes else 1.0
            row.append((cx + hw * k * math.cos(a), cy + hd * k * math.sin(a), z))
        rows.append(row)
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)


def build_body(coll, ink_coll, root):
    ink = 0.009
    # ---- neck, collar and shoulder yoke (A: the bow-like collar under the chin with up-curled points, the narrow neck,
    #      the wider shoulder points; depth C)
    g = Geo()
    g.use("body")
    g.tube([(0, 0.005, 1.585), (0, 0.004, 1.50), (0, 0.0, 1.432), (0, 0.0, 1.39)], [0.032, 0.03, 0.026, 0.04], segs=12)
    half = [(0.130, 0.012, 1.522), (0.108, 0.004, 1.500), (0.068, -0.004, 1.481), (0.030, -0.008, 1.473)]
    col_pts = [Vector((-x, y, z)) for x, y, z in half] + [Vector((0.0, -0.009, 1.471))] + [Vector((x, y, z)) for x, y, z in reversed(half)]
    path = catmull(col_pts, per=5)
    n = len(path)
    prof = [math.sin(math.pi * (0.04 + 0.92 * i / (n - 1))) for i in range(n)]
    g.tube(path, [0.003 + 0.05 * p ** 1.5 for p in prof], [0.002 + 0.03 * p ** 1.1 for p in prof], segs=12, ref=(0, 1, 0))
    half = [(0.160, 0.006, 1.343), (0.130, 0.0, 1.368), (0.080, -0.002, 1.392), (0.030, -0.002, 1.401)]
    yoke = [Vector((-x, y, z)) for x, y, z in half] + [Vector((0.0, -0.002, 1.403))] + [Vector((x, y, z)) for x, y, z in reversed(half)]
    path = catmull(yoke, per=5)
    n = len(path)
    prof = [math.sin(math.pi * (0.03 + 0.94 * i / (n - 1))) for i in range(n)]
    g.tube(path, [0.003 + 0.068 * p ** 1.5 for p in prof], [0.002 + 0.030 * p ** 1.3 for p in prof], segs=12, ref=(0, 1, 0))
    mesh_part("MAR_Collar", g, coll, root, "A", "neck, bow-shaped collar with up-curled points and pointed shoulder yoke (front A, depth C)",
              subsurf=1, ink=ink, ink_coll=ink_coll)

    # ---- thorax tapering to the thin waist, with a raised wing base on the back (C)
    g = Geo()
    g.use("body")
    loft(g, [(0.0, 0.0, z, w, d) for z, w, d in THORAX], segs=28)
    g.ellipsoid((0.0, 0.075, 1.375), (0.07, 0.08, 0.095), segs=20, steps=10)
    mesh_part("MAR_Thorax", g, coll, root, "A", "inverted-cone thorax to a thin waist (A); wing base on the back (C)", subsurf=1, ink=ink, ink_coll=ink_coll)

    # ---- grey breast plate: pointed at both ends, widest a third down, two arched segment lines (A)
    zt, zb = P(0, 210)[1], P(0, 247)[1]
    g = Geo()
    g.use("plate")
    rows = []
    nz, nv = 16, 9
    for k in range(nz + 1):
        u = 0.02 + 0.96 * k / nz
        z = lerp(zt, zb, u)
        hw, hd = thorax_at(z)
        wp = PLATE_W * math.sin(math.pi * u ** 0.85) ** 0.8
        phi = math.asin(min(0.95, wp / hw))
        o, i_ = [], []
        for j in range(nv):
            v = -1.0 + 2.0 * j / (nv - 1)
            a = -math.pi / 2 + phi * v
            p = Vector((hw * math.cos(a), hd * math.sin(a), z))
            nrm = Vector((math.cos(a) / hw, math.sin(a) / hd, 0.0)).normalized()
            o.append(p + nrm * 0.009)
            i_.append(p - nrm * 0.004)
        rows.append(o + list(reversed(i_)))
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)
    g.use("navy")
    for u0 in (0.49, 0.70):
        z0 = lerp(zt, zb, u0)
        hw, hd = thorax_at(z0)
        wp = PLATE_W * math.sin(math.pi * u0 ** 0.85) ** 0.8
        phi = math.asin(min(0.95, wp / hw))
        path = []
        for j in range(13):
            v = -0.85 + 1.7 * j / 12
            a = -math.pi / 2 + phi * v
            z = z0 + 0.012 * (1.0 - v * v)
            hw2, hd2 = thorax_at(z)
            p = Vector((hw2 * math.cos(a), hd2 * math.sin(a), z))
            nrm = Vector((math.cos(a) / hw2, math.sin(a) / hd2, 0.0)).normalized()
            path.append(p + nrm * 0.0095)
        g.tube(path, taper(len(path), 0.0045, 0.0045, tip=2), segs=6)
    mesh_part("MAR_Plate", g, coll, root, "A", "grey kite-shaped breast plate with two arched segment lines (A); its curvature follows the thorax (C)",
              subsurf=1, ink=0.006, ink_coll=ink_coll)

    # ---- gown: broad strands from the thin waist, overlapping, each running out into pointed root-like tips that splay
    #      and curl; a dark lining inside shows through the gaps (A front: strands, tips and dark gaps; back strands C)
    g = Geo()
    g.use("body_dark")
    loft(g, [(0.0, 0.0, 1.12, 0.024, 0.022), (0.004, 0.0, 1.06, 0.04, 0.036), (0.012, 0.01, 0.96, 0.055, 0.05),
             (0.02, 0.015, 0.86, 0.05, 0.05), (0.02, 0.015, 0.80, 0.02, 0.02)], segs=24)
    mesh_part("MAR_GownLining", g, coll, root, "C", "dark lining inside the gown, seen only through the gaps between strands (A: dark gaps)", subsurf=1)

    strands = [  # name, [(drawing x, y, depth H, half width px)], evidence
        ("Left", [(99, 255, -0.006, 6), (95, 280, -0.022, 9), (92, 300, -0.03, 10), (85, 320, -0.03, 9), (74, 336, -0.025, 6), (66, 351, -0.02, 1.4)], "A"),
        ("LeftTip", [(90, 312, -0.034, 6), (84, 335, -0.042, 5), (80, 352, -0.05, 3.5), (82, 364, -0.055, 1.3)], "A"),
        ("Centre", [(104, 258, -0.012, 6), (108, 280, -0.032, 10), (116, 300, -0.038, 12), (130, 312, -0.032, 10), (148, 316, -0.022, 7),
                    (162, 313, -0.016, 4), (168, 303, -0.012, 1.4)], "A"),
        ("CentreTip", [(128, 312, -0.036, 7), (142, 332, -0.042, 5), (153, 345, -0.046, 3.5), (159, 358, -0.05, 1.3)], "A"),
        ("Mid", [(102, 270, -0.018, 6), (101, 300, -0.044, 8), (99, 330, -0.06, 7), (96, 352, -0.07, 5), (94, 366, -0.075, 1.3)], "A"),
        ("MidTip", [(101, 318, -0.052, 5), (106, 340, -0.072, 4), (109, 358, -0.086, 3), (110, 370, -0.092, 1.1)], "A"),
        ("Right", [(108, 262, -0.004, 6), (114, 285, -0.014, 8), (120, 312, -0.024, 8), (123, 340, -0.032, 6), (125, 368, -0.036, 1.3)], "A"),
        ("BackLeft", [(100, 262, 0.03, 6), (94, 295, 0.07, 9), (86, 325, 0.11, 8), (78, 345, 0.15, 5), (74, 356, 0.17, 1.3)], "C"),
        ("BackRight", [(107, 262, 0.03, 6), (116, 295, 0.07, 9), (130, 325, 0.11, 8), (142, 342, 0.15, 5), (147, 352, 0.17, 1.3)], "C"),
        ("BackCentre", [(104, 265, 0.035, 6), (104, 300, 0.09, 9), (103, 330, 0.15, 8), (104, 350, 0.21, 5), (106, 360, 0.25, 1.3)], "C"),
        ("BackFarRight", [(108, 280, 0.03, 5), (128, 305, 0.06, 6), (148, 320, 0.09, 5), (158, 326, 0.11, 3), (163, 318, 0.12, 1.1)], "C"),
        ("BackFarLeft", [(99, 280, 0.03, 5), (82, 305, 0.06, 6), (68, 322, 0.09, 5), (60, 330, 0.11, 3), (57, 322, 0.12, 1.1)], "C"),
    ]
    per = 7
    for tag, key, ev in strands:
        g = Geo()
        g.use("body")
        x0, y0, d0, w0 = key[0]
        top = pxy(x0, y0, d0) + Vector((0.0, 0.0, 0.05 if not tag.endswith("Tip") else 0.03))   # tucked into the waist / the parent strand
        path = catmull([top] + [pxy(x, y, d) for x, y, d, _ in key], per=per)
        rb = interp_keys([w0 * 0.8 * S] + [w * S for *_, w in key], per)
        ra = [0.005 + 0.30 * r for r in rb]
        g.tube(path, ra, rb, segs=12, ref=(0, 1, 0))
        mesh_part(f"MAR_Gown_{tag}", g, coll, root, ev, "gown strand running out into a pointed root-like tip" + ("" if ev == "A" else " (back of the gown, completion)"),
                  subsurf=1, ink=0.008, ink_coll=ink_coll)

    # ---- legs: two thin dark stalks hanging inside the gown, seen between the tendrils at the hem (B)
    g = Geo()
    g.use("navy")
    for x0, x1 in ((100, 99), (108, 109)):
        path = jointed([pxy(x0, 280, 0.004), pxy(x0, 330, 0.004), pxy(x1, 372, -0.004)], fillet=0.02)
        g.tube(path, taper(len(path), 0.010, 0.006, tip=4), segs=8)
    mesh_part("MAR_Legs", g, coll, root, "B", "two thin dark strokes between the tendrils at the hem, read as legs like the arms (B)",
              ink=0.005, ink_coll=ink_coll)

    # ---- arms: thin, straight between the joints, hanging a little away from the body; three spread fingers (A front, depth C)
    g = Geo()
    g.use("navy")
    arms = [(-1, (78, 242), (72, 271), [(67, 283), (71, 286), (77, 283)]),
            (1, (128, 242), (136, 273), [(132, 284), (137, 287), (142, 283)])]
    for sx, elbow, wrist, tips in arms:
        sh = Vector((sx * 0.072, 0.0, 1.352))
        el = pxy(*elbow, -0.006)
        wr = pxy(*wrist, -0.03)
        path = jointed([sh, el, wr], fillet=0.02)
        g.tube(path, taper(len(path), 0.012, 0.0085), segs=10)
        g.ellipsoid(tuple(wr + Vector((0, 0, -0.004))), (0.012, 0.010, 0.014), segs=10, steps=6)
        for k, (tx, ty) in enumerate(tips):
            tip = pxy(tx, ty, -0.03 - 0.012 * k)
            knuckle = wr.lerp(tip, 0.45) + Vector((sx * 0.004 * (k - 1), -0.004, 0.0))
            fp = jointed([wr, knuckle, tip], fillet=0.006, per=4)
            g.tube(fp, taper(len(fp), 0.0055, 0.0035, tip=3), segs=6)
    mesh_part("MAR_Arms", g, coll, root, "A", "thin dark arms bent a little at the elbow, three spread claw fingers (A); depth C", ink=0.006, ink_coll=ink_coll)


# ================================================================== wings
FORE_OUTLINE = [(97, 214), (96, 192), (94, 170), (91, 149), (86, 137), (81, 128), (77, 120), (73, 112), (69, 103), (66, 95), (62, 86),
                (59, 77), (56, 67), (52, 56), (48, 45), (43, 34), (38, 24), (32, 14), (26, 7), (20, 3), (15, 6), (11, 13), (9, 22),
                (8, 33), (8, 46), (9, 58), (9, 69), (7, 81), (6, 94), (5, 106), (4, 118), (4, 130), (4, 142), (6, 152), (9, 162),
                (12, 172), (15, 182), (19, 192), (30, 198), (48, 203), (68, 207), (86, 211)]
HIND_OUTLINE = [(97, 222), (80, 210), (60, 202), (40, 195), (26, 190), (18, 193), (14, 199), (12, 208), (11, 217), (12, 227), (13, 237),
                (12, 247), (13, 256), (16, 265), (20, 273), (26, 281), (33, 289), (41, 296), (51, 301), (63, 303), (75, 300), (84, 293),
                (90, 283), (93, 269), (95, 252), (96, 236)]


def wing_geo(spec, side):
    """Wing membrane as a fan from a centre point to the drawn outline (outline resampled by arc length, so the
    narrow tip keeps its shape), thick in the middle and thin at the edge, bent back toward the tips. Faces of the
    outer band take the light rim material; veins are raised tubes on both faces. side = +1 her left (+X), -1 her right."""
    ax, ay = spec["attach"]

    def T(x, y):
        return Vector(((ax - x) * S, (ay - y) * S))

    poly = resample_closed(catmull([T(x, y) for x, y in spec["outline"]], per=8, closed=True), spec["n"])
    C = T(*spec["centre"])
    n = len(poly)
    px_of = [(ax - p.x / S, ay - p.y / S) for p in poly]
    outer = [spec["outer"](x, y) for x, y in px_of]
    rim = spec["rim"] * S

    def nearest(x, y):
        q = T(x, y)
        return min(range(n), key=lambda j: (poly[j] - q).length)

    cusps = sorted(nearest(x, y) for x, y in spec["cusps"])
    w = []
    for j in range(n):
        if not outer[j]:
            w.append(rim * 0.25)
            continue
        ww = rim
        if spec["scallop"]:
            for a, b in zip(cusps, cusps[1:]):
                if a <= j <= b:
                    ww = rim * (1.0 - 0.5 * math.sin(math.pi * (j - a) / max(1, b - a)))
        w.append(ww)
    r = [(poly[j] - C).length for j in range(n)]
    bfrac = [max(0.3, 1.0 - w[j] / r[j]) for j in range(n)]

    bend, L = spec["bend"], spec["L"]

    def cam(p):
        return bend * (p.x * p.x + p.y * p.y) / (L * L)

    def thick(f):
        return lerp(0.016, 0.0075, min(1.0, f) ** 1.3)

    def pt(j, f, s, h=None):
        p = C + (poly[j] - C) * f
        hh = thick(f) * 0.5 if h is None else h
        return (side * p.x, cam(p) + s * hh, p.y)

    F_IN = [0.03, 0.12, 0.24, 0.37, 0.5, 0.62, 0.74, 0.85, 0.94, 1.0]
    top = [[pt(j, f * bfrac[j], 1) for j in range(n)] for f in F_IN]
    band_t = [[pt(j, (bfrac[j] + 1.0) * 0.5, 1) for j in range(n)], [pt(j, 1.0 - 0.003 / r[j], 1) for j in range(n)]]
    edge = [[pt(j, 1.0, 0, 0.0) for j in range(n)]]
    band_b = [[pt(j, 1.0 - 0.003 / r[j], -1) for j in range(n)], [pt(j, (bfrac[j] + 1.0) * 0.5, -1) for j in range(n)]]
    bot = [[pt(j, f * bfrac[j], -1) for j in range(n)] for f in reversed(F_IN)]
    rows = top + band_t + edge + band_b + bot
    i0, i1 = len(top) - 1, len(top) + len(band_t) + len(edge) + len(band_b)        # rim rows: b ring (top) .. b ring (bottom)

    g = Geo()
    g.use("wing_rim")
    g.use(spec["mat"])
    loops = g.grid(rows, close_u=True, cap_start=True, cap_end=True)
    rim_idx = g.keys.index("wing_rim")
    for i in range(i0, i1):
        a, b = loops[i], loops[i + 1]
        for j in range(n):
            jj = (j + 1) % n
            if outer[j] and outer[jj]:
                face = g.bm.faces.get((a[j], a[jj], b[jj], b[j]))
                if face is not None:
                    face.material_index = rim_idx

    # ---- veins (raised on both faces)
    g.use("vein")
    vr = 0.0085

    def vein(points2d, r0=vr, r1=vr):
        pts = [Vector((side * p.x, cam(p), p.y)) for p in points2d]
        nn = len(pts)
        rb = taper(nn, r0, r1, tip=2)
        ra = [0.0115] * nn
        ra[0] = ra[-1] = 0.009
        g.tube(pts, ra, rb, segs=8, ref=(0, 1, 0))

    def bpt(j):
        return C + (poly[j] - C) * bfrac[j]

    sub = [j for j in range(n) if spec["sub"](*px_of[j])]
    if sub:
        sub.sort()
        runs, cur = [], [sub[0]]
        for j in sub[1:]:
            if j == cur[-1] + 1:
                cur.append(j)
            else:
                runs.append(cur)
                cur = [j]
        runs.append(cur)
        for run in runs:
            if len(run) > 2:
                vein([bpt(j) for j in run])
    radial_ends = []
    for (sx_, sy_), target, kind in spec["radials"]:
        s0 = T(sx_, sy_)
        e = bpt(nearest(*target)) if kind == "rim" else T(*target)
        mid = (s0 + e) * 0.5
        d = (e - s0)
        perp = Vector((-d.y, d.x)).normalized() * d.length * spec.get("bow", 0.06)
        pts = [(1 - t) ** 2 * s0 + 2 * (1 - t) * t * (mid + perp) + t * t * e for t in [k / 14 for k in range(15)]]
        vein(pts, vr * 1.1, vr * 0.8)
        radial_ends.append(pts)
    if spec.get("tipline"):
        x0, x1 = spec["tipline"]
        _, xc, k, zc = TIP_LINE
        vein([T(x, ay - zc - k * (x - xc) ** 2) for x in [x0 + (x1 - x0) * i / 16 for i in range(17)]])   # the shader's tip line
    if spec.get("cross") and len(radial_ends) > 2:
        t = spec["cross"]
        cross = [pts[int(round(t * 14))] for pts in radial_ends]
        vein(catmull(cross, per=6))
    return g


FORE_SPEC = dict(
    outline=FORE_OUTLINE, attach=FORE_A, centre=(50, 125), n=200, rim=7.0, mat="wing_fore", scallop=False,
    outer=lambda x, y: (x < 24 and y > 8) or y < 70,          # light band along the outer edge, the whole tip is light anyway (A)
    sub=lambda x, y: x < 24 and 106 < y < 190,                 # vein along the inner side of the band below the tip line (A)
    cusps=[], tipline=(18.5, 69.5),
    radials=[((90, 194), (30, 107.4), "pt"), ((90, 190), (52, 108.6), "pt"), ((90, 198), (5, 135), "rim"), ((90, 203), (12, 172), "rim")],
    cross=0.55, bow=0.05, **WING_FORE)
HIND_SPEC = dict(
    outline=HIND_OUTLINE, attach=HIND_A, centre=(55, 250), n=180, rim=8.0, mat="wing_hind", scallop=True,
    outer=lambda x, y: y > 196 and x < 86,
    sub=lambda x, y: y > 198 and x < 84,
    cusps=[(15, 202), (12, 228), (14, 255), (24, 279), (42, 296), (64, 302), (83, 294)],
    tipline=None,
    radials=[((92, 232), (15, 202), "rim"), ((92, 234), (12, 228), "rim"), ((92, 238), (14, 255), "rim"), ((92, 242), (24, 279), "rim"),
             ((90, 246), (42, 296), "rim"), ((88, 250), (64, 302), "rim")],
    cross=0.5, bow=-0.05, **WING_HIND)


def build_wings(coll, ink_coll, root):
    for name, spec in (("Fore", FORE_SPEC), ("Hind", HIND_SPEC)):
        ax, ay = spec["attach"]
        z_att = P(0, ay)[1]
        for side, tag in ((-1, "R"), (1, "L")):          # her right wing (-X) and her left wing (+X)
            g = wing_geo(spec, side)
            M = (Matrix.Translation((side * 0.03, spec["y0"], z_att)) @ Matrix.Rotation(side * math.radians(spec["sweep"]), 4, "Z")
                 @ Matrix.Rotation(math.radians(spec["lean"]), 4, "X"))
            mesh_part(f"MAR_Wing{name}_{tag}", g, coll, root, "A",
                      f"{name.lower()} wing: outline, light rim, " + ("tip zone, four cream spots, " if name == "Fore" else "scalloped cells, ")
                      + "veins from the drawing (outline A, vein layout B); thickness, sweep back, lean and camber C",
                      m=M, subsurf=1, ink=0.010, ink_coll=ink_coll, ink_key="ink_wing")


# ================================================================== look-dev stage (own collection, not part of the asset)
def look(scene, coll):
    world = bpy.data.worlds.new("WORLD_MAR")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.040, 0.050, 0.085, 1.0)   # mid-tone so the dark contours read
    bg.inputs["Strength"].default_value = 1.0
    scene.world = world

    g = Geo()
    g.use("stage_floor")
    g.box(-3.0, 3.0, -2.5, 2.5, -0.05, 0.0)
    g.to_object("Stage_Floor", coll, lambda k: MATS[k], props={"cot_role": "lookdev"})

    def light(name, kind, loc, target, power, color, size=1.0):
        data = bpy.data.lights.new(name, kind)
        data.energy = power
        data.color = color
        if kind == "AREA":
            data.size = size
        obj = bpy.data.objects.new(name, data)
        obj.location = loc
        obj.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        obj["cot_role"] = "lookdev"
        coll.objects.link(obj)
        return obj

    light("Light_Back", "AREA", (0.3, 3.6, 3.2), (0.0, 0.0, 1.5), 220.0, (0.86, 0.88, 1.0), size=3.0)
    light("Light_Key", "AREA", (2.8, -3.8, 3.4), (0.0, 0.0, 1.4), 300.0, (0.92, 0.94, 1.0), size=2.2)
    light("Light_Fill", "AREA", (-3.4, -2.6, 1.6), (0.0, 0.0, 1.2), 90.0, (0.60, 0.70, 1.0), size=2.6)

    def cam(name, loc, target, lens=50.0, ortho=None, res=None):
        data = bpy.data.cameras.new(name)
        if ortho:
            data.type = "ORTHO"
            data.ortho_scale = ortho
        else:
            data.lens = lens
        data.clip_start, data.clip_end = 0.05, 60.0
        obj = bpy.data.objects.new(name, data)
        obj.location = loc
        obj.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        obj["cot_role"] = "lookdev"
        if res:
            obj["cot_res"] = list(res)
        coll.objects.link(obj)
        return obj

    # reference-matched view: the whole drawing canvas (202 x 378 px) at S H per px, three times its pixel size
    cx, cz = P(101.0, 189.0)
    cam("CAM_MAR_RefFront", (cx, -10.0, cz), (cx, 0.0, cz), ortho=378.0 * S, res=(606, 1134))
    cam("CAM_MAR_ThreeQuarter", (3.0, -4.6, 2.2), (0.0, 0.05, 1.45), lens=50.0, res=(1200, 1600))
    cam("CAM_MAR_ThreeQuarterL", (-3.0, -4.6, 1.9), (0.0, 0.05, 1.45), lens=50.0, res=(1200, 1600))
    cam("CAM_MAR_SideRight", (5.6, 0.1, 1.5), (0.0, 0.1, 1.5), lens=55.0, res=(1200, 1600))
    cam("CAM_MAR_Back", (-1.8, 5.2, 2.2), (0.0, 0.1, 1.45), lens=50.0, res=(1200, 1600))
    cam("CAM_MAR_Top", (0.0, -0.8, 7.0), (0.0, 0.1, 1.2), lens=40.0, res=(1200, 1200))
    cam("CAM_MAR_Portrait", (0.8, -2.0, 1.72), (0.03, 0.0, 1.47), lens=70.0, res=(1200, 1200))
    cam("CAM_MAR_Audience", (1.5, -5.0, 0.6), (0.0, 0.1, 1.35), lens=40.0, res=(1200, 1600))


# ================================================================== main
def main():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for block in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for item in list(block):
            block.remove(item)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    scene = bpy.context.scene
    scene.name = "Marissa"
    scene.unit_settings.system = "NONE"
    make_materials()

    c_m = collection("MAR_Marissa")
    c_body = collection("MAR_Body", c_m)
    c_wings = collection("MAR_Wings", c_m)
    c_ink = collection("MAR_Ink", c_m)
    c_look = collection("MAR_Lookdev")
    root = root_empty("MAR_Root", c_m, {
        "cot_asset": "Marissa", "cot_version": VERSION, "cot_ref": REF_ART + "; " + REF_MAP + "; " + REF_SHOT,
        "cot_city_spot": json.dumps(CITY_SPOT, ensure_ascii=False),
        "cot_note": "Marissa floating upright, facing forward, arms hanging, wings raised in a V behind her. Static pose (no rig). "
                    "Root at the stage floor; her lowest point floats HOVER above it."})
    build_head(c_body, c_ink, root)
    build_body(c_body, c_ink, root)
    build_wings(c_wings, c_ink, root)
    look(scene, c_look)

    scene.render.engine = "CYCLES"
    scene.cycles.samples = 96
    scene.cycles.use_denoising = True
    scene.cycles.transparent_max_bounces = 32
    scene.view_settings.view_transform = "Standard"      # as the city's art scene (config/art.json color_management)
    scene.view_settings.look = "None"
    scene.camera = bpy.data.objects["CAM_MAR_ThreeQuarter"]
    scene["cot_asset"] = ASSET
    scene["cot_version"] = VERSION
    scene["cot_city_spot"] = json.dumps(CITY_SPOT, ensure_ascii=False)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT), compress=False, relative_remap=True)

    report = {"asset": ASSET, "version": VERSION, "blend": str(OUT.relative_to(ROOT)).replace("\\", "/"), "blender": bpy.app.version_string,
              "units": "H (project yardstick)", "scale": {"height_H": HEIGHT, "H_per_px": round(S, 6), "hover": HOVER},
              "refs": [REF_ART, REF_MAP, REF_SHOT], "city_spot": CITY_SPOT, "objects": []}
    deps = bpy.context.evaluated_depsgraph_get()
    for obj in sorted(bpy.data.objects, key=lambda o: o.name):
        if obj.type != "MESH" or obj.get("cot_role") == "lookdev":
            continue
        ev = obj.evaluated_get(deps)
        me = ev.to_mesh()
        report["objects"].append({"name": obj.name, "collection": obj.users_collection[0].name, "verts": len(me.vertices), "faces": len(me.polygons),
                                  "dims": [round(v, 3) for v in obj.dimensions], "ev": obj.get("cot_ev", ""), "role": obj.get("cot_role", "geometry")})
        ev.to_mesh_clear()
    (OUT.parent / "build_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("COT_SAVED", OUT, len(report["objects"]), "objects")


main()
