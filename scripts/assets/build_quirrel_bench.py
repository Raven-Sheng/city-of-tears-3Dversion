"""Quirrel (seated) and his iron bench as two separate, editable assets (user request 2026-10-06).

Run:  "D:\\Blender\\blender.exe" -b --factory-startup --python scripts/assets/build_quirrel_bench.py -- [--out PATH]

Where they are in the city (A, master map): LeftWell / WestBlock, the lit lancet hall on the 2923 floor of the
7600 px reading map (bench at map x 1710-1736). The hall's east end is a cage-roofed glass bay over the left rain
well; the bench stands just inside it. World position about X -133.8, Z 45.1 (H). This script does not touch the
city files; the scene it saves holds only the two assets plus a look-dev stage in its own collection.

Asset frame and units: 1 = H (project yardstick). Bench along X, its front toward -Y, floor at Z = 0.
Evidence: Character/Quirrel/Screenshot_HK_Quirrel_05.png (A, one side view; 120 px per H, found by matching the
bench width to the master crop at 50 px per H); master crop E_quirrel_bench_hall (A). The shapes seen in that
view are A, their depth / back / hidden sides are C. The pose is the user's (2026-10-06): he sits facing forward
against the backrest, one leg crossed over the other, right hand laid over the bench's top rail, nail carried on
his back. The flat game view is not read for the pose. See docs/decisions.md.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from cot_geo import Geo, IronCurves, TAU, bez, lerp, spiral_pts, spow  # noqa: E402

ASSET = "QuirrelBench"
VERSION = "v005"
REF_SHOT = "Character/Quirrel/Screenshot_HK_Quirrel_05.png"
REF_MAP = "00_Master/master_map.png.png, crop E_quirrel_bench_hall (7600 box 1430,2640,1830,3000)"
CITY_SPOT = {"region": "LeftWell", "element": "WestBlock", "floor_map_y_7600": 2923, "bench_map_x_7600": [1710, 1736],
             "world_x": -133.8, "world_z": 45.1, "note": "east end of the lancet hall, just inside the glass bay"}

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(argv[argv.index("--out") + 1]) if "--out" in argv else ROOT / "assets" / "hero" / f"{ASSET}_{VERSION}" / f"{ASSET}_{VERSION}.blend"

# ------------------------------------------------------------------ measurements (screenshot px / 120 = H)
BENCH_X = 0.78          # half length over the end curls and feet (189 px wide)
POST_X = 0.72           # end posts / back panel ends
SEAT_Z = 0.33           # seat top (40 px above the floor)
SEAT_Y = (-0.24, 0.18)  # seat depth: completion (C)
PANEL_O = Vector((-POST_X, 0.185, 0.36))   # back panel: bottom rail line ...
PANEL_TOP = Vector((0.0, 0.245, 0.70))     # ... rising to the top rail (84 px total height), slight recline (C)
LEG_X = (0.60, 0.55)    # front / back leg tops: the legs stand inboard of the back-panel ends (A)
BODY_XY = (0.30, -0.15)  # body centre in plan: right of the bench middle as in the shot (B); clear of the nail behind him
QRL_YAW = 0.0                              # facing forward (-Y), as the user describes
QRL_LEAN = math.radians(6.0)               # settled back toward the backrest
HEAD_C = Vector((0.30, -0.14, 0.985))      # mask between Z 0.83 and 1.14 (A); v005: on the front of the tall upper body (Npc_quirrel.png)
HEAD_YAW = math.radians(10.0)              # face turned slightly to his left (C)
HAT_YAW = math.radians(10.0)
HAT_SCALE = (0.8, 0.82)                    # v002: hat 20 % smaller in plan, 18 % lower (user request 2026-10-06)
EYE_SCALE = 0.78                           # v003: eyes about a fifth smaller (user request 2026-10-06)
BODY_TAPER = (1.0, 0.42)                   # v004: width = a - b * sin(lat): slim under the head, widening evenly to the base (user request)

MATS = {}


# ================================================================== materials
def _tree(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return mat, nt, out


def _principled(nt, out, color, rough, metal=0.0, spec=0.35):
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = spec
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return bsdf


def _mix_rgb(nt, fac, a, b):
    node = nt.nodes.new("ShaderNodeMix")
    node.data_type = "RGBA"
    nt.links.new(fac, node.inputs[0])
    node.inputs[6].default_value = (*a, 1.0)
    node.inputs[7].default_value = (*b, 1.0)
    return node.outputs[2]


def _math(nt, op, a, b=None):
    node = nt.nodes.new("ShaderNodeMath")
    node.operation = op
    for sock, val in zip(node.inputs, (a, b)):
        if val is None:
            continue
        if isinstance(val, bpy.types.NodeSocket):
            nt.links.new(val, sock)
        else:
            sock.default_value = val
    return node.outputs[0]


def plain(key, color, rough=0.5, metal=0.0, spec=0.35):
    mat, nt, out = _tree("MAT_QB_" + key)
    _principled(nt, out, color, rough, metal, spec)
    mat.diffuse_color = (*color, 1.0)
    MATS[key] = mat
    return mat


def spotted(key, base, spot, spots, rough=0.55):
    """Base colour with dark patches on the upward-facing side: spots = [((x, y), (rx, ry), tilt_deg)] in object space,
    measured in plan so a patch follows the curved top instead of floating at one height; tilt turns the ellipse."""
    mat, nt, out = _tree("MAT_QB_" + key)
    bsdf = _principled(nt, out, base, rough)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    acc = None
    for spec in spots:
        (sx, sy), (rx, ry) = spec[0], spec[1]
        tilt = spec[2] if len(spec) > 2 else 0.0
        sub = nt.nodes.new("ShaderNodeVectorMath")
        sub.operation = "SUBTRACT"
        nt.links.new(coord.outputs["Object"], sub.inputs[0])
        sub.inputs[1].default_value = (sx, sy, 0.0)
        rot = nt.nodes.new("ShaderNodeVectorRotate")
        rot.rotation_type = "Z_AXIS"
        rot.inputs["Angle"].default_value = math.radians(-tilt)
        nt.links.new(sub.outputs["Vector"], rot.inputs["Vector"])
        div = nt.nodes.new("ShaderNodeVectorMath")
        div.operation = "MULTIPLY"
        nt.links.new(rot.outputs["Vector"], div.inputs[0])
        div.inputs[1].default_value = (1.0 / rx, 1.0 / ry, 0.0)
        length = nt.nodes.new("ShaderNodeVectorMath")
        length.operation = "LENGTH"
        nt.links.new(div.outputs["Vector"], length.inputs[0])
        inside = _math(nt, "LESS_THAN", length.outputs["Value"], 1.0)
        acc = inside if acc is None else _math(nt, "MAXIMUM", acc, inside)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Normal"], sep.inputs[0])
    acc = _math(nt, "MULTIPLY", acc, _math(nt, "GREATER_THAN", sep.outputs["Z"], 0.25))
    nt.links.new(_mix_rgb(nt, acc, base, spot), bsdf.inputs["Base Color"])
    mat.diffuse_color = (*base, 1.0)
    MATS[key] = mat
    return mat


def graded(key, top, bottom, z0, z1, rough=0.45):
    """Colour blend over object-space Z (mask: white above, a faint warm tint toward the chin)."""
    mat, nt, out = _tree("MAT_QB_" + key)
    bsdf = _principled(nt, out, top, rough)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Object"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = z0
    ramp.inputs["From Max"].default_value = z1
    nt.links.new(sep.outputs["Z"], ramp.inputs["Value"])
    nt.links.new(_mix_rgb(nt, ramp.outputs["Result"], bottom, top), bsdf.inputs["Base Color"])
    mat.diffuse_color = (*top, 1.0)
    MATS[key] = mat
    return mat


def ink_material():
    """Contour ink for the inverted hulls: the hull's near side is transparent, its far side shows past the
    silhouette as a dark line (same method as the city's MAT_S2_outline)."""
    mat, nt, out = _tree("MAT_QB_ink")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    ink = nt.nodes.new("ShaderNodeEmission")
    ink.inputs["Color"].default_value = (0.006, 0.006, 0.014, 1.0)
    ink.inputs["Strength"].default_value = 1.0
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(geo.outputs["Backfacing"], mix.inputs["Fac"])
    nt.links.new(clear.outputs["BSDF"], mix.inputs[1])
    nt.links.new(ink.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    try:
        mat.surface_render_method = "BLENDED"
    except Exception:
        pass
    mat.use_backface_culling = True
    mat.diffuse_color = (0.0, 0.0, 0.01, 1.0)
    MATS["ink"] = mat
    return mat


def make_materials():
    # colours read off the screenshot (sRGB) and converted to linear; painted light is not baked in
    # hat patches: the long dark patch on the crown (A), two small ones toward the back edge (B)
    spotted("qrl_hat", (0.80, 0.79, 0.83), (0.015, 0.015, 0.025),
            [((-0.062, -0.23), (0.034, 0.054), 25.0), ((0.062, -0.23), (0.034, 0.054), -25.0),
             ((0.0, -0.175), (0.014, 0.019))])   # v005: user's hat image (two slanted ovals near the front tip, small dot behind)
    graded("qrl_mask", (0.86, 0.86, 0.89), (0.66, 0.60, 0.64), -0.16, -0.05)
    plain("qrl_eye", (0.006, 0.006, 0.010), 0.32)
    plain("qrl_hood", (0.050, 0.054, 0.090), 0.55)
    plain("qrl_hood_ridge", (0.16, 0.16, 0.22), 0.5)
    plain("qrl_body", (0.36, 0.25, 0.36), 0.5)
    plain("qrl_plate", (0.12, 0.11, 0.17), 0.42)
    plain("qrl_line", (0.025, 0.022, 0.040), 0.5)
    plain("qrl_limb", (0.020, 0.020, 0.036), 0.45)
    plain("qrl_strap", (0.045, 0.034, 0.040), 0.6)
    plain("qrl_blade", (0.42, 0.44, 0.52), 0.32, metal=0.6)
    plain("qb_iron", (0.020, 0.032, 0.080), 0.42, metal=0.5)        # same values as the city's iron
    plain("qb_iron_seat", (0.030, 0.040, 0.085), 0.35, metal=0.5)
    plain("stage_floor", (0.018, 0.024, 0.050), 0.6)
    ink_material()


# ================================================================== scene helpers
def collection(name, parent=None):
    coll = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def root_empty(name, coll, m, props):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = 0.3
    e.matrix_world = m
    for k, v in props.items():
        e[k] = v
    coll.objects.link(e)
    return e


def attach(obj, parent, m):
    obj.matrix_world = m
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def ink_hull(obj, coll, thickness):
    """Inverted hull sharing the mesh: same subdivision, pushed out along the normals, ink on every slot."""
    hull = bpy.data.objects.new(obj.name + "_Ink", obj.data)
    coll.objects.link(hull)
    hull.parent = obj.parent
    hull.matrix_parent_inverse = obj.matrix_parent_inverse.copy()
    hull.matrix_basis = obj.matrix_basis.copy()
    for slot in hull.material_slots:
        slot.link = "OBJECT"
        slot.material = MATS["ink"]
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


def mesh_part(name, g, coll, parent, m, ev, note, subsurf=0, ink=None, ink_coll=None):
    obj = g.to_object(name, coll, lambda k: MATS[k], props={"cot_id": name, "cot_ev": ev, "cot_ref": REF_SHOT, "cot_note": note})
    attach(obj, parent, m)
    if subsurf:
        mod = obj.modifiers.new("Subsurf", "SUBSURF")
        mod.levels = 1
        mod.render_levels = subsurf
    if ink:
        ink_hull(obj, ink_coll, ink)
    return obj


def curve_part(name, ic, coll, parent, m, ev, note, bevel=0.009):
    obj = ic.to_object(name, coll, MATS["qb_iron"], bevel=bevel, props={"cot_id": name, "cot_ev": ev, "cot_ref": REF_SHOT, "cot_note": note},
                       resolution=4, bevel_res=2)
    attach(obj, parent, m)
    return obj


def catmull(points, per=6):
    """Smooth path through key points (Catmull-Rom), endpoints kept."""
    pts = [Vector(p) for p in points]
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


def taper(n, r0, r1, tip=None):
    """Radii along a limb: r0 -> r1, the last few points pinched to a point if tip is given."""
    out = [lerp(r0, r1, i / (n - 1)) for i in range(n)]
    if tip:
        for k in range(tip):
            out[n - 1 - k] *= (k + 0.4) / (tip + 0.4)
    return out


# ================================================================== bench
def build_bench(coll):
    root = root_empty("QB_Root", coll, Matrix.Identity(4), {
        "cot_asset": "QuirrelBench_Bench", "cot_version": VERSION, "cot_ref": REF_SHOT + "; " + REF_MAP,
        "cot_city_spot": json.dumps(CITY_SPOT, ensure_ascii=False),
        "cot_note": "iron bench of Quirrel's hall: heart-and-spade scroll back, curled top rail ends, cabriole legs"})
    I = Matrix.Identity(4)
    y0, y1 = SEAT_Y

    # ---- seat: four slats on a frame of round rails (A: thin dark seat line with a heavier front edge; slats C)
    g = Geo()
    g.use("qb_iron_seat")
    slat_w = (y1 - y0 - 0.03) / 4
    for k in range(4):
        sy0 = y0 + 0.015 + k * slat_w + 0.006
        g.box(-POST_X, POST_X, sy0, sy0 + slat_w - 0.012, SEAT_Z - 0.028, SEAT_Z)
    g.use("qb_iron")
    g.tube([(-POST_X - 0.01, y0, SEAT_Z - 0.03), (POST_X + 0.01, y0, SEAT_Z - 0.03)], 0.026, 0.02, segs=10)
    g.tube([(-POST_X, y1, SEAT_Z - 0.03), (POST_X, y1, SEAT_Z - 0.03)], 0.02, segs=8)
    for sx in (-1, 1):
        for x in (LEG_X[0], POST_X):                     # frame rails over the legs and under the overhanging ends
            g.tube([(sx * x, y0, SEAT_Z - 0.035), (sx * x, y1, SEAT_Z - 0.035)], 0.018, segs=8)
    g.tube([(-LEG_X[0], y0 + 0.005, SEAT_Z - 0.068), (LEG_X[0], y0 + 0.005, SEAT_Z - 0.068)], 0.009, segs=6)   # apron rod (C)
    mesh_part("QB_Seat", g, coll, root, I, "A", "seat line, front edge and overhang past the legs A; slats, rails and depth C")

    # ---- legs: per end a cabriole front leg flaring to a scroll foot and a straighter back leg further in (A side view);
    #      the back posts of the panel rise from the seat ends (C joinery)
    g = Geo()
    g.use("qb_iron")
    fx, bx_ = LEG_X
    for sx in (-1, 1):
        front = catmull([(sx * fx, y0, SEAT_Z - 0.03), (sx * (fx + 0.035), y0 - 0.005, 0.25), (sx * (fx + 0.025), y0 - 0.01, 0.15),
                         (sx * (fx + 0.01), y0 - 0.015, 0.075), (sx * (fx + 0.05), y0 - 0.02, 0.022), (sx * (fx + 0.115), y0 - 0.02, 0.012)], per=5)
        g.tube(front, taper(len(front), 0.024, 0.016), segs=8)
        g.ellipsoid((sx * (fx + 0.11), y0 - 0.02, 0.012), (0.03, 0.022, 0.012), segs=10, steps=5)
        back = catmull([(sx * bx_, y1, SEAT_Z - 0.03), (sx * (bx_ + 0.008), y1 + 0.01, 0.20), (sx * bx_, y1 + 0.03, 0.08),
                        (sx * (bx_ + 0.02), y1 + 0.045, 0.012)], per=5)
        g.tube(back, taper(len(back), 0.022, 0.016), segs=8)
        g.ellipsoid((sx * (bx_ + 0.02), y1 + 0.045, 0.012), (0.026, 0.02, 0.012), segs=10, steps=5)
        p_seat = Vector((sx * POST_X, y1, SEAT_Z - 0.03))
        p_lo = Vector((sx * POST_X, PANEL_O.y, PANEL_O.z))
        p_hi = Vector((sx * POST_X, PANEL_TOP.y, PANEL_TOP.z))
        g.tube([p_seat, p_lo, p_hi], 0.019, segs=8)
        # small scroll bracket between the front leg and the overhanging seat end (A: curl under the left end)
        a0 = 0.0 if sx > 0 else math.pi * 0.5
        g.ring_arc((sx * (fx + 0.055), y0, SEAT_Z - 0.07), 0.032, a0, a0 + math.pi * 1.5, 0.008, n=12, plane="XZ", segs=5)
    mesh_part("QB_Legs", g, coll, root, I, "A", "two legs per end as drawn (cabriole outer, straighter inner); depth C; right end mirrors the left (C)")

    # ---- back panel frame + scroll infill in the reclined panel plane
    ez = (PANEL_TOP - Vector((0.0, PANEL_O.y, PANEL_O.z))).normalized()
    ex = Vector((1.0, 0.0, 0.0))
    ey = ez.cross(ex)
    M = Matrix(((ex.x, ey.x, ez.x, PANEL_O.x), (ex.y, ey.y, ez.y, PANEL_O.y), (ex.z, ey.z, ez.z, PANEL_O.z), (0, 0, 0, 1)))
    H = (PANEL_TOP - Vector((0.0, PANEL_O.y, PANEL_O.z))).length      # panel height along the incline
    L = 2 * POST_X

    rails = IronCurves()
    rails.add([(0.0, 0.0), (L, 0.0)], r=1.4, smooth=False)                     # bottom rail of the panel
    rails.add([(-0.005, H), (L + 0.005, H)], r=2.0, smooth=False)               # top rail
    for sx, x in ((-1, 0.0), (1, L)):                                          # curled ends of the top rail (A left, C right)
        start = (x, H)
        sp = spiral_pts(x + sx * 0.035, H - 0.04, 0.042, 1.15, math.pi / 2, ccw=(sx < 0), r1=0.01, n=22)
        rails.add([start] + sp[1:], r=[2.0] + [lerp(2.0, 1.1, i / (len(sp) - 1)) for i in range(1, len(sp))])
    curve_part("QB_BackFrame", rails.transformed(M), coll, root, I, "A", "top rail with curled ends, panel bottom rail")

    scroll = IronCurves()
    n_units = 6
    w = L / n_units

    def heart(cx):
        """V-shaped heart, widest at its two curled lobes under the top rail (A: the row of paired curls)."""
        for s in (-1, 1):
            body = bez((cx, 0.03), (cx + s * 0.062, 0.085), (cx + s * 0.098, 0.20), (cx + s * 0.092, 0.287), n=10)
            sp = spiral_pts(cx + s * 0.046, 0.287, 0.046, 1.2, 0.0 if s > 0 else math.pi, ccw=(s > 0), r1=0.008, n=22)
            scroll.add(body + sp[1:], r=1.0)
        scroll.add([(cx, 0.0), (cx, 0.031)], r=1.0, smooth=False)

    def spade(bx, sides=(-1, 1)):
        """Spade pointing up between two hearts, its lobes curled at the bottom (A)."""
        for s in sides:
            body = bez((bx, 0.235), (bx + s * 0.01, 0.20), (bx + s * 0.042, 0.165), (bx + s * 0.04, 0.10), n=8)
            sp = spiral_pts(bx + s * 0.021, 0.10, 0.019, 1.1, 0.0 if s > 0 else math.pi, ccw=(s < 0), r1=0.005, n=16)
            scroll.add(body + sp[1:], r=1.0)
        if len(sides) == 2:
            scroll.add([(bx, 0.0), (bx, 0.081)], r=1.0, smooth=False)

    for k in range(n_units):
        heart((k + 0.5) * w)
    for k in range(1, n_units):
        spade(k * w)
    spade(0.0, sides=(1,))                                                     # half spades against the posts (C)
    spade(L, sides=(-1,))
    curve_part("QB_BackScroll", scroll.transformed(M), coll, root, I, "A",
               "hearts with curled tops alternating with upward spades, read from the visible two thirds; spacing B; hidden third continues the pattern (C)",
               bevel=0.011)
    return root


# ================================================================== Quirrel
RX, RY, RZ, CZ = 0.21, 0.22, 0.40, 0.39      # v005: tall bean body after Npc_quirrel.png (height about 1.9 x width); depth C


def body_pt(a, b, f=1.0):
    """Point on the seated body: a latitude, b longitude (b = -90 deg is the belly, +90 deg the back, 0 his left)."""
    ca, sa = math.cos(a), math.sin(a)
    widen = BODY_TAPER[0] - BODY_TAPER[1] * sa                             # one even taper from the slim top to the full base
    x = RX * widen * ca * math.cos(b)
    y = RY * widen * ca * math.sin(b)
    if y < 0.0:
        y *= 1.06 + 0.10 * max(0.0, -sa)                                   # lower belly bulges forward (standing drawing)
    p = Vector((x, y, RZ * sa)) * f
    p.z += CZ
    zf = 0.012
    if p.z < zf:
        p.z = zf - (zf - p.z) * 0.12
    return p


def body_frame():
    """Root -> yaw -> lift -> lean. The lift keeps the lowest point of the leaned body just on the seat; the root is
    placed so the body centre lands on BODY_XY."""
    lean = Matrix.Rotation(-QRL_LEAN, 4, "X")
    low = min((lean @ body_pt(-math.pi / 2 + math.pi * k / 24, TAU * i / 32)).z for k in range(25) for i in range(32))
    lift = Matrix.Translation((0.0, 0.0, 0.004 - low))
    rot = Matrix.Rotation(QRL_YAW, 4, "Z")
    off = (rot @ lift @ lean) @ Vector((0.0, 0.0, CZ))
    yaw = Matrix.Translation((BODY_XY[0] - off.x, BODY_XY[1] - off.y, SEAT_Z)) @ rot
    return yaw, yaw @ lift @ lean


def line_radii(n, r):
    return [r * max(0.3, math.sin(math.pi * i / (n - 1)) ** 0.5) for i in range(n)]


def jointed(points, fillet=0.03, per=5):
    """Straight segments between joints, each joint rounded by a short fillet (limbs bend only at elbow / knee / ankle)."""
    P = [Vector(p) for p in points]
    out = [P[0]]
    for i in range(1, len(P) - 1):
        a, j, b = P[i - 1], P[i], P[i + 1]
        p1 = j + (a - j).normalized() * min(fillet, (a - j).length * 0.4)
        p2 = j + (b - j).normalized() * min(fillet, (b - j).length * 0.4)
        last = out[-1]
        out += [last.lerp(p1, k / per) for k in range(1, per + 1)]
        out += [(1 - t) ** 2 * p1 + 2 * (1 - t) * t * j + t * t * p2 for t in (0.25, 0.5, 0.75)]
        out.append(p2)
    last = out[-1]
    out += [last.lerp(P[-1], k / per) for k in range(1, per + 1)]
    return out


def limb(g, pts, r0, r1, per=6, tip=3, segs=10):
    path = jointed(pts, per=per)
    g.tube(path, taper(len(path), r0, r1, tip=tip), segs=segs)
    return path


def claws(g, base, tips, r0=0.011, r1=0.006):
    for tip in tips:
        limb(g, [base, Vector(tip)], r0, r1, per=5, tip=3, segs=6)


def ribbon(g, pts, normals, width, thick):
    """Flat strap: a closed band of rectangular section following pts, lying on the surface with the given normals."""
    rows = []
    n = len(pts)
    for i in range(n):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        nn = (normals[i] - t * normals[i].dot(t)).normalized()
        side = t.cross(nn)
        c = pts[i]
        rows.append([c + side * width * 0.5, c + side * width * 0.5 + nn * thick, c - side * width * 0.5 + nn * thick, c - side * width * 0.5])
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)


def build_quirrel(coll, ink_coll):
    yaw, MB = body_frame()
    BX, BY = BODY_XY
    root = root_empty("QRL_Root", coll, yaw, {
        "cot_asset": "QuirrelBench_Quirrel", "cot_version": VERSION, "cot_ref": REF_SHOT + "; " + REF_MAP,
        "cot_city_spot": json.dumps(CITY_SPOT, ensure_ascii=False),
        "cot_note": "Quirrel seated facing forward, legs crossed, right hand over the top rail, nail on his back. Static pose (no rig)."})
    ink = 0.012

    def bp(a_deg, b_deg, f=1.0):
        return MB @ body_pt(math.radians(a_deg), math.radians(b_deg), f)

    # ---- body: plump egg, mauve belly with two segment lines (A colour / outline; depth C)
    g = Geo()
    g.use("qrl_body")
    steps, segs = 30, 48
    rows = [[body_pt(-math.pi / 2 + math.pi * k / steps, TAU * i / segs) for i in range(segs)] for k in range(1, steps)]
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)
    g.use("qrl_line")
    for lat, b0, b1 in ((27.0, 212, 328), (-20.0, 206, 334)):   # under the chest and across the lower belly (A)
        a = math.radians(lat)
        path = [body_pt(a, math.radians(b), 1.006) for b in range(b0, b1 + 1, 4)]
        g.tube(path, line_radii(len(path), 0.0055), segs=5)
    mesh_part("QRL_Body", g, coll, root, MB, "A", "outline, colour and segment lines A; volume and back C", subsurf=1, ink=ink, ink_coll=ink_coll)

    # ---- back plates: five overlapping shell bands over the back, each lip proud of the one below (pill bug, B/C)
    g = Geo()
    g.use("qrl_plate")
    for k in range(5):
        a_top = math.radians(76.0 - k * 25.0)
        a_bot = a_top - math.radians(30.0)
        b0, b1 = math.radians(90.0 - 80.0), math.radians(90.0 + 80.0)
        nu, nv = 9, 30
        rows = []
        for i in range(nu + 1):
            u = i / nu
            a = lerp(a_top, a_bot, u)
            outer, inner = [], []
            for j in range(nv + 1):
                v = j / nv
                b = lerp(b0, b1, v)
                edge = math.sin(math.pi * v) ** 0.35                    # thinner toward the side edges
                outer.append(body_pt(a, b, 1.0 + (0.016 + 0.028 * u ** 1.5) * edge + 0.004))
                inner.append(body_pt(a, b, 0.995))
            rows.append(outer + inner[::-1])
        g.grid(rows, close_u=True, cap_start=True, cap_end=True)
    mesh_part("QRL_BackPlates", g, coll, root, MB, "B", "grey back of the body (A colour) built as pill-bug plates (B/C)",
              subsurf=1, ink=ink, ink_coll=ink_coll)

    # ---- head: on the front-top of the body, facing forward and turned a little to his left
    MH = Matrix.Translation(HEAD_C) @ Matrix.Rotation(HEAD_YAW, 4, "Z")

    g = Geo()
    g.use("qrl_hood")
    hc, hr = (0.0, 0.07, 0.0), (0.165, 0.15, 0.18)        # v005: smaller, flowing into the tall back instead of bulging past it
    g.ellipsoid(hc, hr, segs=32, steps=18)
    g.use("qrl_hood_ridge")
    for k in range(5):                                   # ridges running down the back of the head (A: striped grey behind the mask)
        b = math.radians(40.0 + 25.0 * k)
        path = []
        for i in range(13):
            a = math.radians(lerp(66.0, -62.0, i / 12))
            path.append((hc[0] + hr[0] * 1.004 * math.cos(a) * math.cos(b), hc[1] + hr[1] * 1.004 * math.cos(a) * math.sin(b),
                         hc[2] + hr[2] * 1.004 * math.sin(a)))
        g.tube(path, line_radii(len(path), 0.009), segs=5)
    mesh_part("QRL_Hood", g, coll, root, MH, "A", "dark striped head shell behind the mask A; ridge count B", subsurf=1, ink=ink, ink_coll=ink_coll)

    E = 0.78
    MRX, MRY, MRZ, MOY = 0.19, 0.14, 0.155, -0.02

    def mask_pt(a, b):
        ca, sa = spow(math.cos(a), E), spow(math.sin(a), E)
        x = MRX * ca * spow(math.cos(b), E)
        y = MRY * ca * spow(math.sin(b), E)
        z = MRZ * sa
        if z < 0.0:
            x *= 1.0 - 0.20 * (-sa) ** 1.5                 # narrower chin
        if y < 0.0:
            y *= 0.86                                      # flatter face
        return (x, y + MOY, z)

    g = Geo()
    g.use("qrl_mask")
    rows = [[mask_pt(-math.pi / 2 + math.pi * k / 24, TAU * i / 40) for i in range(40)] for k in range(1, 24)]
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)
    mesh_part("QRL_Mask", g, coll, root, MH, "A", "white mask, wide brow and narrower chin A; depth C", subsurf=1, ink=ink, ink_coll=ink_coll)

    g = Geo()
    g.use("qrl_eye")
    for sx in (-1, 1):
        ex_, ez_ = sx * 0.08, 0.02
        t = 1.0 - abs(ex_ / MRX) ** (2 / E) - abs(ez_ / MRZ) ** (2 / E)
        fy = MOY - MRY * 0.86 * max(t, 0.0) ** (E / 2)       # front surface of the mask at the eye
        turn = sx * math.radians(20.0)                         # follow the curve of the face
        m = Matrix.Translation((ex_, fy + 0.011, ez_)) @ Matrix.Rotation(turn, 4, "Z")
        g.ellipsoid((0, 0, 0), (0.068 * EYE_SCALE, 0.022, 0.093 * EYE_SCALE), segs=20, steps=12, m=m)
    mesh_part("QRL_Eyes", g, coll, root, MH, "A", "two large black oval eyes, widely spaced (A)", subsurf=1)

    # ---- hat: thick lens-shaped shell, crown toward the back, long thin pointed front brim, brim curving down all
    #      round and most at the back (A: top Z 1.31, over the face 1.14, front tip 1.09, back edge 1.03)
    sp_, sz_ = HAT_SCALE

    def hat_edge(u):
        """Teardrop outline seen from above (user's hat image): u = 0 at the front tip, wide rounded back."""
        L, W, k, yoff = 0.90, 0.64, 0.45, -0.05
        y = -0.5 * L * math.cos(u) + yoff
        x = 0.5 * W * math.sin(u) * (1.0 - k * math.cos(u)) / (1.0 + k * 0.35)
        return Vector((x, y)) * sp_

    def droop(phi, rho):
        c, s = math.cos(phi), math.sin(phi)
        return sp_ * (-0.05 * max(0.0, c) ** 2 - 0.11 * max(0.0, -c) ** 2 - 0.04 * s * s) * rho * rho

    crown = Vector((0.0, 0.06 * sp_))
    rings = [(rho, 0.006 + sz_ * 0.17 * (1.0 - rho * rho) ** 0.7) for rho in (0.002, 0.15, 0.3, 0.45, 0.6, 0.72, 0.82, 0.9, 0.95, 0.985, 1.0)]
    rings += [(rho, -0.004 + sz_ * 0.035 * (1.0 - rho * rho) ** 1.2) for rho in (1.0, 0.97, 0.9, 0.75, 0.55, 0.3, 0.002)]
    g = Geo()
    g.use("qrl_hat")
    rows = []
    nseg = 64
    for rho, z in rings:
        row = []
        for i in range(nseg):
            e = hat_edge(TAU * i / nseg)
            phi = math.atan2(e.x, -e.y)
            p = crown * (1.0 - rho) + e * rho
            row.append((p.x, p.y, z + droop(phi, rho)))
        rows.append(row)
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)
    MHAT = Matrix.Translation(HEAD_C + Vector((0.0, 0.0, MRZ))) @ Matrix.Rotation(HAT_YAW, 4, "Z")
    mesh_part("QRL_Hat", g, coll, root, MHAT, "A", "pale shell hat; v005 teardrop planform and spot pattern (two ovals near the front, a small dot behind them) from the user's top-view image (A); "
              "v002 made smaller at the user's request",
              subsurf=1, ink=ink, ink_coll=ink_coll)

    # ---- arms (dark, thin, straight between the joints, tapering to claws as drawn)
    g = Geo()
    g.use("qrl_limb")
    rail_y, rail_z = PANEL_TOP.y, PANEL_TOP.z + 0.018           # top of the backrest's top rail
    # right arm laid over the top rail: upper arm back to the elbow on the rail, forearm along it, claws over its back (user pose)
    arm_r = limb(g, [bp(28, 178, 0.9), Vector((BX - 0.36, rail_y - 0.01, rail_z + 0.03)), Vector((BX - 0.62, rail_y, rail_z + 0.028))],
                 0.017, 0.015, tip=None)
    hand = arm_r[-1]
    g.ellipsoid(tuple(hand + Vector((-0.008, 0.004, 0.0))), (0.024, 0.02, 0.02), segs=12, steps=7)
    claws(g, hand, [(BX - 0.66, rail_y + 0.075, rail_z - 0.04), (BX - 0.63, rail_y + 0.08, rail_z - 0.045), (BX - 0.69, rail_y + 0.07, rail_z - 0.035)])
    # left arm: upper arm down his side, forearm to a hand resting on the crossed knee (C)
    arm_l = limb(g, [bp(28, 2, 0.9), Vector((BX + 0.30, BY - 0.12, 0.62)), Vector((BX + 0.13, BY - 0.36, 0.575))], 0.017, 0.014, tip=None)
    claws(g, arm_l[-1], [(BX + 0.07, BY - 0.40, 0.565), (BX + 0.10, BY - 0.41, 0.56), (BX + 0.13, BY - 0.40, 0.565)])
    mesh_part("QRL_Arms", g, coll, root, Matrix.Identity(4), "C", "right hand over the top rail (user pose); left hand on the crossed knee (C)",
              ink=ink, ink_coll=ink_coll)

    # ---- legs: left foot on the floor, right leg crossed over the left knee (user pose)
    g = Geo()
    g.use("qrl_limb")
    # straight thigh, shin and foot; the right thigh rests over the left knee
    limb(g, [bp(-48, -55, 0.8), Vector((BX + 0.11, BY - 0.29, 0.43)), Vector((BX + 0.125, BY - 0.32, 0.05)), Vector((BX + 0.135, BY - 0.45, 0.012))],
         0.019, 0.011, per=6, tip=4)
    limb(g, [bp(-48, -125, 0.8), Vector((BX + 0.10, BY - 0.36, 0.52)), Vector((BX + 0.24, BY - 0.43, 0.29)), Vector((BX + 0.28, BY - 0.51, 0.24))],
         0.019, 0.011, per=6, tip=4)
    mesh_part("QRL_Legs", g, coll, root, Matrix.Identity(4), "C", "legs crossed, right over left (user pose); thin long stick legs after Npc_quirrel.png (A)",
              ink=ink, ink_coll=ink_coll)

    # ---- strap: a baldric from the left shoulder across the chest to the right hip and back up over the plates (C)
    g = Geo()
    g.use("qrl_strap")
    for f, b_from, b_to in ((1.012, -12.0, -168.0), (1.07, -12.0, 192.0)):
        pts, nrm = [], []
        for i in range(25):
            t = i / 24
            a, b = math.radians(lerp(36.0, -42.0, t)), math.radians(lerp(b_from, b_to, t))   # v005: kept below the mask
            p = body_pt(a, b, f)
            pts.append(p)
            nrm.append((p - Vector((0.0, 0.0, CZ))).normalized())
        ribbon(g, pts, nrm, 0.038, 0.009)
    mesh_part("QRL_Strap", g, coll, root, MB, "C", "carrying strap for the nail (completion; not seen in the shot)", subsurf=0, ink=ink, ink_coll=ink_coll)

    # ---- nail on his back: diagonal behind the plates, grip out past the left shoulder, tip by the right hip (user pose).
    #      Shape after Npc_quirrel.png: long needle blade longer than his body, short pale grip, a curved hook as guard (A)
    g = Geo()
    pommel = MB @ Vector((0.38, 0.29, 0.72))
    tip = MB @ Vector((-0.27, 0.29, 0.10))
    d = (tip - pommel).normalized()
    out = (MB.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()          # away from his back
    side = d.cross(out).normalized()
    g.use("qrl_blade")
    g.ellipsoid(tuple(pommel), (0.017, 0.017, 0.017), segs=10, steps=6)
    g.tube([pommel, pommel + d * 0.12], [0.014, 0.015], segs=8)
    base = pommel + d * 0.12
    hook = [base, base + side * 0.03 + d * 0.012, base + side * 0.052 - d * 0.012, base + side * 0.056 - d * 0.05]
    g.tube(catmull(hook, per=4), taper(13, 0.009, 0.004, tip=3), segs=6)
    length = (tip - pommel).length
    blade = [pommel + d * lerp(0.12, length, t) for t in (0.0, 0.25, 0.5, 0.75, 0.9, 1.0)]
    g.tube(blade, [0.0045] * 6, [0.017, 0.014, 0.011, 0.007, 0.004, 0.0015], segs=6, ref=tuple(out))   # flat side to his back
    mesh_part("QRL_Nail", g, coll, root, Matrix.Identity(4), "A", "needle nail with a hook guard as in Npc_quirrel.png (A); carried on the back (user pose)",
              ink=ink, ink_coll=ink_coll)
    return root


# ================================================================== look-dev stage (own collection, not part of the assets)
def look(scene, coll):
    world = bpy.data.worlds.new("WORLD_QB")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.010, 0.016, 0.040, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scene.world = world

    g = Geo()
    g.use("stage_floor")
    g.box(-2.5, 2.5, -2.0, 2.0, -0.05, 0.0)
    floor = g.to_object("Stage_Floor", coll, lambda k: MATS[k], props={"cot_role": "lookdev"})

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

    light("Light_Window", "AREA", (0.2, 2.6, 1.6), (0.2, 0.0, 0.6), 260.0, (0.86, 0.88, 1.0), size=2.5)   # pale window light behind
    light("Light_Key", "AREA", (1.8, -2.4, 2.2), (0.3, 0.0, 0.6), 220.0, (0.88, 0.92, 1.0), size=1.6)
    light("Light_Fill", "AREA", (-2.2, -1.8, 1.0), (0.0, 0.0, 0.5), 60.0, (0.55, 0.68, 1.0), size=2.0)

    def cam(name, loc, target, lens=50.0, ortho=None, res=None):
        data = bpy.data.cameras.new(name)
        if ortho:
            data.type = "ORTHO"
            data.ortho_scale = ortho
        else:
            data.lens = lens
        data.clip_start, data.clip_end = 0.05, 50.0
        obj = bpy.data.objects.new(name, data)
        obj.location = loc
        obj.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        obj["cot_role"] = "lookdev"
        if res:
            obj["cot_res"] = list(res)
        coll.objects.link(obj)
        return obj

    # reference-matched view: the screenshot crop (495..745, 735..915 px) at 120 px per H, bench left end at px 512.5
    cx = -BENCH_X + (620.0 - 512.5) / 120.0
    cz = (907.5 - 825.0) / 120.0
    cam("CAM_QB_RefFront", (cx, -8.0, cz), (cx, 0.0, cz), ortho=250.0 / 120.0, res=(1000, 720))
    cam("CAM_QB_ThreeQuarter", (2.3, -3.1, 1.45), (0.15, 0.0, 0.52), lens=55.0, res=(1600, 1200))
    cam("CAM_QB_SideRight", (4.2, 0.0, 0.62), (0.0, 0.0, 0.56), lens=70.0, res=(1600, 1200))
    cam("CAM_QB_Back", (-1.3, 3.4, 1.25), (0.15, 0.0, 0.55), lens=50.0, res=(1600, 1200))
    cam("CAM_QB_Top", (0.0, -0.4, 4.6), (0.0, 0.0, 0.4), lens=45.0, res=(1600, 1200))
    cam("CAM_QRL_Portrait", (1.55, -1.75, 1.15), (0.42, 0.0, 0.88), lens=70.0, res=(1600, 1200))
    cam("CAM_QB_BenchFront", (0.0, -4.5, 0.5), (0.0, 0.0, 0.42), lens=55.0, res=(1600, 1000))
    return floor


# ================================================================== main
def main():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for block in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for item in list(block):
            block.remove(item)
    scene = bpy.context.scene
    scene.name = "QuirrelBench"
    scene.unit_settings.system = "NONE"
    make_materials()

    c_q = collection("QRL_Quirrel")
    c_ink = collection("QRL_Ink", c_q)
    c_b = collection("QB_Bench")
    c_look = collection("QB_Lookdev")
    build_bench(c_b)
    build_quirrel(c_q, c_ink)
    look(scene, c_look)

    scene.render.engine = "CYCLES"
    scene.cycles.samples = 96
    scene.cycles.use_denoising = True
    scene.cycles.transparent_max_bounces = 16
    scene.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in scene.view_settings.bl_rna.properties["view_transform"].enum_items] else scene.view_settings.view_transform
    scene.camera = bpy.data.objects["CAM_QB_ThreeQuarter"]
    scene["cot_asset"] = ASSET
    scene["cot_version"] = VERSION
    scene["cot_city_spot"] = json.dumps(CITY_SPOT, ensure_ascii=False)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT), compress=False, relative_remap=True)

    report = {"asset": ASSET, "version": VERSION, "blend": str(OUT.relative_to(ROOT)).replace("\\", "/"), "blender": bpy.app.version_string,
              "units": "H (project yardstick)", "refs": [REF_SHOT, REF_MAP], "city_spot": CITY_SPOT, "objects": []}
    deps = bpy.context.evaluated_depsgraph_get()
    for obj in sorted(bpy.data.objects, key=lambda o: o.name):
        if obj.type not in ("MESH", "CURVE") or obj.get("cot_role") == "lookdev":
            continue
        ev = obj.evaluated_get(deps)
        me = ev.to_mesh()
        dims = [round(v, 3) for v in obj.dimensions]
        report["objects"].append({"name": obj.name, "collection": obj.users_collection[0].name, "type": obj.type,
                                  "verts": len(me.vertices), "faces": len(me.polygons), "dims": dims, "ev": obj.get("cot_ev", ""),
                                  "role": obj.get("cot_role", "geometry")})
        ev.to_mesh_clear()
    (OUT.parent / "build_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("COT_SAVED", OUT, len(report["objects"]), "objects")


main()
