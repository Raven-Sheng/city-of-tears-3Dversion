"""Build the City of Tears greybox from config/layout.json (stage 1).

Run from the project root:
  blender -b --factory-startup --python scripts/build_city.py -- [--regions A,B] [--checkpoint] [--fresh] [--master FILE]

  * Opens scenes/city_master.blend if it exists (unless --fresh), otherwise starts empty.
  * Rebuilds only objects it generated itself (custom property cot_generated) for the
    selected regions; anything else in the file, including hand-made assets, is left alone.
  * Same layout + same seed gives the same result.
  * --checkpoint also writes scenes/checkpoints/city_greybox_vNNN.blend.

Map coordinates are pixels of the 7600 px reading version of the master map.
World: X = map x, Z = height, Y = added depth (level-C design).
"""
import json
import math
import shutil
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector, noise

ROOT = Path(__file__).resolve().parents[1]
PROJECT = json.loads((ROOT / "config" / "project.json").read_text(encoding="utf-8"))
LAYOUT = json.loads((ROOT / "config" / "layout.json").read_text(encoding="utf-8"))
CHECKPOINTS = ROOT / PROJECT["checkpoint_dir"]

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
# --master lets tests run against a copy instead of the real master file.
MASTER = Path(argv[argv.index("--master") + 1]) if "--master" in argv else ROOT / PROJECT["master_file"]
ONLY = None
if "--regions" in argv:
    ONLY = set(argv[argv.index("--regions") + 1].split(","))
FRESH = "--fresh" in argv
CHECKPOINT = "--checkpoint" in argv

OX, OY = PROJECT["coordinates"]["origin_map"]
PPB = PROJECT["coordinates"]["px_per_bu"]
D = PROJECT["depth_defaults"]
WALL, FLOOR = D["wall"], D["floor"]
SEED = PROJECT["random_seed"]


def X(mx):
    return (mx - OX) / PPB


def Z(my):
    return (OY - my) / PPB


# --------------------------------------------------------------------------- scene
if MASTER.exists() and not FRESH:
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "COT_CITY"
scene.unit_settings.system = "NONE"
scene["cot_stage"] = 1
scene["cot_px_per_bu"] = PPB
scene["cot_origin_map"] = [OX, OY]


def collection(name, parent=None):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    holder = parent if parent is not None else scene.collection
    if coll.name not in holder.children:
        holder.children.link(coll)
    return coll


C_WORLD = collection("COT_WORLD")
C_REGIONS = collection("COT_REGIONS", C_WORLD)
C_LAYERS = {name: collection("COT_L_" + name, C_WORLD)
            for name in ("FRONT", "CEILING", "HOSTROCK", "BACKDROP", "FOREGROUND", "CAVESHELL")}
C_CAMERAS = collection("COT_CAMERAS")
C_REFERENCE = collection("COT_REFERENCE")

PALETTE = {
    "stone": (0.46, 0.52, 0.62), "floor": (0.30, 0.36, 0.47), "front": (0.58, 0.62, 0.70),
    "rock": (0.17, 0.19, 0.25), "hostrock": (0.10, 0.11, 0.15), "iron": (0.20, 0.24, 0.33),
    "glass": (0.62, 0.86, 0.95), "louvre": (0.28, 0.36, 0.60), "shell": (0.22, 0.26, 0.50),
    "water": (0.10, 0.32, 0.50), "landmark": (0.92, 0.66, 0.30), "placeholder": (0.95, 0.42, 0.22),
    "backdrop": (0.20, 0.30, 0.46), "shaft": (0.36, 0.33, 0.56), "car": (0.80, 0.74, 0.92),
    "ref_A": (0.25, 0.85, 0.40), "ref_B": (0.95, 0.85, 0.25), "ref_C": (0.95, 0.55, 0.20),
    "ref_U": (0.95, 0.20, 0.25), "ref_text": (1.0, 1.0, 1.0),
}


def material(key):
    name = "MAT_GB_" + key
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    color = (*PALETTE[key], 1.0)
    mat.diffuse_color = color
    mat.roughness = 0.8
    if mat.node_tree is not None:
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = color
            bsdf.inputs["Roughness"].default_value = 0.8
    return mat


def remove_generated(region_id):
    for obj in [o for o in bpy.data.objects if o.get("cot_generated") and o.get("cot_region") == region_id]:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data is not None and data.users == 0:
            kind = type(data).__name__
            store = {"Mesh": bpy.data.meshes, "Camera": bpy.data.cameras, "TextCurve": bpy.data.curves,
                     "Curve": bpy.data.curves}.get(kind)
            if store is not None:
                store.remove(data)


# --------------------------------------------------------------------------- mesh helpers
class MB:
    """Accumulates simple closed solids into one mesh."""

    def __init__(self):
        self.bm = bmesh.new()

    def box(self, x0, x1, y0, y1, z0, z1):
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        z0, z1 = sorted((z0, z1))
        if x1 - x0 < 1e-4 or y1 - y0 < 1e-4 or z1 - z0 < 1e-4:
            return
        v = [self.bm.verts.new(p) for p in (
            (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
        for a, b, c, d in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.bm.faces.new((v[a], v[b], v[c], v[d]))

    def prism(self, pts_xz, y0, y1):
        """Extrude a polygon given in the XZ plane along Y."""
        front = [self.bm.verts.new((x, y0, z)) for x, z in pts_xz]
        back = [self.bm.verts.new((x, y1, z)) for x, z in pts_xz]
        n = len(front)
        for i in range(n):
            j = (i + 1) % n
            self.bm.faces.new((front[i], front[j], back[j], back[i]))
        caps = [self.bm.faces.new(front), self.bm.faces.new(list(reversed(back)))]
        bmesh.ops.triangulate(self.bm, faces=caps)

    def extruded_polygon(self, pts3d, offset):
        front = [self.bm.verts.new(p) for p in pts3d]
        back = [self.bm.verts.new(Vector(p) + offset) for p in pts3d]
        n = len(front)
        for i in range(n):
            j = (i + 1) % n
            self.bm.faces.new((front[i], front[j], back[j], back[i]))
        caps = [self.bm.faces.new(front), self.bm.faces.new(list(reversed(back)))]
        bmesh.ops.triangulate(self.bm, faces=caps)

    def rings(self, rings, cap_bottom=True, cap_top=True):
        """Loft a list of rings (each a list of 3D points, same count)."""
        loops = [[self.bm.verts.new(p) for p in ring] for ring in rings]
        n = len(loops[0])
        for a, b in zip(loops, loops[1:]):
            for i in range(n):
                j = (i + 1) % n
                self.bm.faces.new((a[i], a[j], b[j], b[i]))
        if cap_bottom:
            self.bm.faces.new(list(reversed(loops[0])))
        if cap_top:
            self.bm.faces.new(loops[-1])

    def cylinder(self, cx, cy, z0, z1, rx, ry=None, segs=20):
        ry = rx if ry is None else ry
        ring = lambda z: [(cx + rx * math.cos(2 * math.pi * i / segs), cy + ry * math.sin(2 * math.pi * i / segs), z)
                          for i in range(segs)]
        self.rings([ring(z0), ring(z1)])

    def cone(self, cx, cy, z0, z1, rx, ry=None, segs=20, top_scale=0.02):
        ry = rx if ry is None else ry
        ring = lambda z, s: [(cx + rx * s * math.cos(2 * math.pi * i / segs),
                              cy + ry * s * math.sin(2 * math.pi * i / segs), z) for i in range(segs)]
        self.rings([ring(z0, 1.0), ring(z1, top_scale)])

    def half_ellipsoid(self, cx, cy, z0, rx, ry, rz, segs=24, steps=7):
        rings = []
        for k in range(steps):
            a = (math.pi / 2) * k / steps
            rings.append([(cx + rx * math.cos(a) * math.cos(2 * math.pi * i / segs),
                           cy + ry * math.cos(a) * math.sin(2 * math.pi * i / segs),
                           z0 + rz * math.sin(a)) for i in range(segs)])
        rings.append([(cx + rx * 0.03 * math.cos(2 * math.pi * i / segs),
                       cy + ry * 0.03 * math.sin(2 * math.pi * i / segs), z0 + rz) for i in range(segs)])
        self.rings(rings)

    def ellipsoid(self, cx, cy, cz, rx, ry, rz, segs=20, steps=10):
        rings = []
        for k in range(1, steps):
            a = -math.pi / 2 + math.pi * k / steps
            rings.append([(cx + rx * math.cos(a) * math.cos(2 * math.pi * i / segs),
                           cy + ry * math.cos(a) * math.sin(2 * math.pi * i / segs),
                           cz + rz * math.sin(a)) for i in range(segs)])
        self.rings(rings)

    def rock(self, x0, x1, y0, y1, z0, z1, amp, salt):
        """Subdivided box with deterministic noise so rock reads differently from masonry."""
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        z0, z1 = sorted((z0, z1))
        start = len(self.bm.verts)
        self.box(x0, x1, y0, y1, z0, z1)
        self.bm.verts.ensure_lookup_table()
        edges = {e for v in self.bm.verts[start:] for e in v.link_edges}
        size = max(x1 - x0, y1 - y0, z1 - z0)
        cuts = max(1, min(5, int(size / 9)))
        bmesh.ops.subdivide_edges(self.bm, edges=list(edges), cuts=cuts, use_grid_fill=True)
        self.bm.verts.ensure_lookup_table()
        amp = min(amp, 0.2 * min(x1 - x0, y1 - y0, z1 - z0))
        for v in self.bm.verts[start:]:
            p = v.co
            n = noise.noise(Vector((p.x * 0.11 + salt, p.y * 0.11 - salt, p.z * 0.11 + SEED * 1e-6)))
            direction = Vector((p.x - (x0 + x1) / 2, p.y - (y0 + y1) / 2, p.z - (z0 + z1) / 2))
            if direction.length > 1e-6:
                v.co = p + direction.normalized() * n * amp

    def to_object(self, name, coll, mat_key, props):
        if not self.bm.verts:
            self.bm.free()
            return None
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces[:])
        mesh = bpy.data.meshes.new(name + "_mesh")
        self.bm.to_mesh(mesh)
        self.bm.free()
        mesh.materials.append(material(mat_key))
        obj = bpy.data.objects.new(name, mesh)
        for key, value in props.items():
            obj[key] = value
        coll.objects.link(obj)
        return obj


def split_interval(a, b, holes):
    """Return the parts of [a, b] not covered by the hole intervals."""
    parts, cursor = [], a
    for h0, h1 in sorted(holes):
        h0, h1 = max(a, h0), min(b, h1)
        if h1 <= h0:
            continue
        if h0 > cursor:
            parts.append((cursor, h0))
        cursor = max(cursor, h1)
    if cursor < b:
        parts.append((cursor, b))
    return parts


# --------------------------------------------------------------------------- element builders
class Ctx:
    def __init__(self, region_id, coll):
        self.region_id = region_id
        self.coll = coll
        self.count = 0

    def emit(self, mb, element, part, mat_key, layer=None):
        name = f"COT_{self.region_id}_{element['id']}" + (f"_{part}" if part else "")
        layer = layer or element.get("layer")
        coll = C_LAYERS[layer] if layer else self.coll
        props = {"cot_generated": True, "cot_region": self.region_id, "cot_element": element["id"],
                 "cot_type": element["type"], "cot_evidence": element.get("ev", "C"),
                 "cot_ref": element.get("ref", ""), "cot_layer": layer or ""}
        if "map" in element:
            props["cot_map_box"] = [float(v) for v in element["map"]]
        obj = mb.to_object(name, coll, mat_key, props)
        if obj is not None:
            self.count += 1
        return obj


def void_list(element):
    out = []
    for v in element.get("voids", []):
        x0, x1 = X(v[0]), X(v[1])
        z_hi = Z(v[2]) if len(v) > 2 else 1e9
        z_lo = Z(v[3]) if len(v) > 3 else -1e9
        out.append((x0, x1, z_lo, z_hi))
    return out


def build_stack(ctx, e):
    x0, x1 = X(e["map"][0]), X(e["map"][2])
    zt, zb = Z(e["map"][1]), Z(e["map"][3])
    yf, yb = e.get("y", D["stack_y"])
    floors = sorted(Z(v) for v in e["floors"])
    bottom = (min(floors) if floors else zb) - FLOOR
    voids = void_list(e)
    sy0, sy1 = D["shaft_y"]

    mb = MB()
    for zf in floors:
        holes = [(a, b) for a, b, lo, hi in voids if lo <= zf <= hi]
        for a, b in split_interval(x0 + WALL, x1 - WALL, holes):
            mb.box(a, b, yf + WALL, yb - WALL, zf - FLOOR, zf)
        for a, b in holes:
            a, b = max(a, x0 + WALL), min(b, x1 - WALL)
            mb.box(a, b, yf + WALL, sy0, zf - FLOOR, zf)
            mb.box(a, b, sy1, yb - WALL, zf - FLOOR, zf)
    holes = [(a, b) for a, b, lo, hi in voids if lo <= zt <= hi]
    for a, b in split_interval(x0, x1, holes):
        mb.box(a, b, yf, yb, zt, zt + FLOOR)
    for a, b in holes:
        mb.box(a, b, yf, sy0, zt, zt + FLOOR)
        mb.box(a, b, sy1, yb, zt, zt + FLOOR)
    ctx.emit(mb, e, "Floors", "floor")

    mb = MB()
    dy0, dy1 = D["door_y"]
    for side, xa, xb in (("L", x0, x0 + WALL), ("R", x1 - WALL, x1)):
        doors = sorted((Z(d[1]), Z(d[1]) + (d[2] if len(d) > 2 else 3.5)) for d in e.get("doors", []) if d[0] == side)
        for a, b in split_interval(bottom, zt, doors):
            mb.box(xa, xb, yf, yb, a, b)
        for a, b in doors:
            mb.box(xa, xb, yf, dy0, a, min(b, zt))
            mb.box(xa, xb, dy1, yb, a, min(b, zt))
    mb.box(x0 + WALL, x1 - WALL, yb - WALL, yb, bottom, zt)
    ctx.emit(mb, e, "Walls", "stone")

    mb = MB()
    mb.box(x0 + WALL, x1 - WALL, yf, yf + WALL, bottom, zt)
    ctx.emit(mb, e, "Front", "front", layer="FRONT")


def build_shaft(ctx, e):
    x0, x1 = X(e["map"][0]), X(e["map"][2])
    zt, zb = Z(e["map"][1]), Z(e["map"][3])
    yf, yb = e.get("y", D["shaft_y"])
    t = 0.3
    mb = MB()
    if e.get("open"):
        # Lift frame standing inside rooms: corner posts and a back panel, so floors stay walkable past it.
        for px in (x0, x1 - t):
            for py in (yf, yb - t):
                mb.box(px, px + t, py, py + t, zb, zt)
        mb.box(x0 + t, x1 - t, yb - 0.12, yb, zb, zt)
        ctx.emit(mb, e, "Frame", "shaft")
    else:
        mb.box(x0, x0 + t, yf, yb, zb, zt)
        mb.box(x1 - t, x1, yf, yb, zb, zt)
        mb.box(x0 + t, x1 - t, yb - t, yb, zb, zt)
        ctx.emit(mb, e, "Walls", "shaft")
        mb = MB()
        mb.box(x0 + t, x1 - t, yf, yf + t, zb, zt)
        ctx.emit(mb, e, "Front", "front", layer="FRONT")
    if "car" in e:
        zc = Z(e["car"])
        half = (e.get("car_w", (e["map"][2] - e["map"][0]) * 0.75) / PPB) / 2
        cx = (x0 + x1) / 2
        depth = min(1.6, (yb - yf) / 2 - 0.5)
        mb = MB()
        mb.box(cx - half, cx + half, -depth, depth, zc, zc + 3.0)
        mb.cone(cx, 0.0, zc + 3.0, zc + 4.4, half, depth, segs=4, top_scale=0.05)
        ctx.emit(mb, e, "Car", "car")


def arcade_band(mb, x0, x1, z_top, z_bot, bays, y0, y1):
    width = (x1 - x0) / bays
    radius = min(width / 2 - 0.25, (z_top - z_bot) - 0.25)
    for i in range(bays):
        xa, xb = x0 + i * width, x0 + (i + 1) * width
        cx = (xa + xb) / 2
        pts = [(xa, z_top), (xb, z_top), (xb, z_bot), (cx + radius, z_bot)]
        pts += [(cx + radius * math.cos(math.pi * k / 10), z_bot + radius * math.sin(math.pi * k / 10))
                for k in range(1, 10)]
        pts += [(cx - radius, z_bot), (xa, z_bot)]
        mb.prism(pts, y0, y1)


def build_bridge(ctx, e):
    x0, x1 = X(e["x"][0]), X(e["x"][1])
    y0, y1 = e.get("y", D["bridge_y"])
    z_deck = Z(e["deck"])
    deck_t = e.get("deck_t", 12) / PPB
    mb = MB()
    mb.box(x0, x1, y0, y1, z_deck - deck_t, z_deck)
    ctx.emit(mb, e, "Deck", "stone")
    mb = MB()
    z_band = Z(e["band_to"])
    arcade_band(mb, x0, x1, z_deck - deck_t, z_band, e["bays"], y0, y0 + 0.4)
    arcade_band(mb, x0, x1, z_deck - deck_t, z_band, e["bays"], y1 - 0.4, y1)
    ctx.emit(mb, e, "Arcade", "stone")
    if "roof" in e:
        z_rt, z_rb = Z(e["roof"][0]), Z(e["roof"][1])
        mb = MB()
        mb.box(x0, x1, y0 - 0.3, y1 + 0.3, z_rb, z_rt)
        for cx in e.get("pavilions", []):
            half = e.get("pav_w", 100) / PPB / 2
            mb.box(X(cx) - half, X(cx) + half, y0 - 0.5, y1 + 0.5, z_rt, z_rt + 0.4)
            mb.half_ellipsoid(X(cx), (y0 + y1) / 2, z_rt + 0.4, half, (y1 - y0) / 2 + 0.3, Z(e["pav_top"]) - z_rt - 0.4)
        ctx.emit(mb, e, "Roof", "louvre")
        mb = MB()
        posts = e.get("posts", e["bays"])
        for i in range(posts + 1):
            px = x0 + (x1 - x0) * i / posts
            for py in (y0 + 0.15, y1 - 0.4):
                mb.box(px - 0.12, px + 0.12, py, py + 0.25, z_deck, z_rb)
        ctx.emit(mb, e, "Posts", "iron")


def canopy_profile(x0, x1, zt, zb, curve, thick=0.35):
    rise = zt - zb
    reach = min((x1 - x0) * (0.5 if curve == "both" else 0.8), rise * 1.6)
    steps = 10
    outer = []
    if curve in ("L", "both"):
        outer += [(x0 + reach - reach * math.cos(math.pi / 2 * k / steps), zb + rise * math.sin(math.pi / 2 * k / steps))
                  for k in range(steps + 1)]
    else:
        outer.append((x0, zt))
    if curve in ("R", "both"):
        outer += [(x1 - reach + reach * math.sin(math.pi / 2 * k / steps), zb + rise * math.cos(math.pi / 2 * k / steps))
                  for k in range(steps + 1)]
    else:
        outer.append((x1, zt))
    inner = [(x, z - thick) for x, z in reversed(outer)]
    return outer + inner


def build_canopy(ctx, e):
    x0, x1 = X(e["map"][0]), X(e["map"][2])
    zt, zb = Z(e["map"][1]), Z(e["map"][3])
    y0, y1 = e.get("y", D["canopy_y"])
    mb = MB()
    if e.get("curve", "flat") == "flat":
        mb.box(x0, x1, y0, y1, zt - 0.35, zt)
    else:
        mb.prism(canopy_profile(x0, x1, zt, zb, e["curve"]), y0, y1)
    ctx.emit(mb, e, "", "louvre")


def build_pavilion(ctx, e):
    x0, x1 = X(e["map"][0]), X(e["map"][2])
    z_top, z_floor = Z(e["map"][1]), Z(e["map"][3])
    z_eave = Z(e["roof_to"])
    y0, y1 = e.get("y", [-3.5, 3.5])
    mb = MB()
    mb.box(x0, x1, y0, y1, z_eave, z_eave + 0.3)
    mb.half_ellipsoid((x0 + x1) / 2, (y0 + y1) / 2, z_eave + 0.3, (x1 - x0) / 2, (y1 - y0) / 2, z_top - z_eave - 0.3)
    ctx.emit(mb, e, "Roof", "louvre")
    mb = MB()
    for px in (x0 + 0.2, x1 - 0.5):
        for py in (y0 + 0.2, y1 - 0.5):
            mb.box(px, px + 0.3, py, py + 0.3, z_floor, z_eave)
    ctx.emit(mb, e, "Posts", "iron")


def build_dome(ctx, e):
    x0, x1 = X(e["map"][0]), X(e["map"][2])
    zt, zb = Z(e["map"][1]), Z(e["map"][3])
    mb = MB()
    mb.half_ellipsoid((x0 + x1) / 2, e.get("yc", 1.0), zb, (x1 - x0) / 2, e["ry"], zt - zb)
    ctx.emit(mb, e, "", "louvre")


def leaf_outline(w, h, n=6):
    right = [(w / 2 * math.sin(math.pi * k / n), h / 2 - h * k / n) for k in range(n + 1)]
    left = [(-x, z) for x, z in reversed(right[1:-1])]
    return right + left


def build_tower(ctx, e):
    x0, x1 = X(e["map"][0]), X(e["map"][2])
    zt, zb = Z(e["map"][1]), Z(e["map"][3])
    cx, cy = (x0 + x1) / 2, e.get("yc", 6.0)
    rx, ry = (x1 - x0) / 2, e.get("ry", (x1 - x0) / 2 * 0.85)
    taper = e.get("taper", 1.0)
    segs = 28
    tier = 6.0
    tiers = max(1, round((zt - zb) / tier))

    def scale_at(z):
        f = (z - zb) / (zt - zb)
        return taper + (1.0 - taper) * min(1.0, f / 0.45) if taper < 1.0 else 1.0

    def ring(z, s):
        return [(cx + rx * s * math.cos(2 * math.pi * i / segs), cy + ry * s * math.sin(2 * math.pi * i / segs), z)
                for i in range(segs)]

    rings = []
    for k in range(tiers):
        z_low = zb + (zt - zb) * k / tiers
        z_high = zb + (zt - zb) * (k + 1) / tiers
        rings.append(ring(z_low, scale_at(z_low) * 1.0))       # flared skirt of each shell tier
        rings.append(ring(z_high - 0.05, scale_at(z_high) * 0.9))
    mb = MB()
    mb.rings(rings)
    roof = e.get("roof", "flat")
    if roof == "umbrella":
        mb.cone(cx, cy, zt - 0.2, zt + rx * 0.32, rx * 1.16, ry * 1.16, segs=segs, top_scale=0.04)
    elif roof == "dome":
        mb.half_ellipsoid(cx, cy, zt - 0.1, rx * 0.92, ry * 0.92, rx * 0.55, segs=segs)
    backdrop = e.get("layer") in ("BACKDROP", "FOREGROUND")
    ctx.emit(mb, e, "Body", "backdrop" if backdrop else "shell")

    count = e.get("windows", 0)
    if count:
        mb = MB()
        w, h = e.get("leaf", [1.9, 5.6])
        outline = leaf_outline(w, h)
        for i in range(count):
            angle = -math.pi / 2 + (i * 0.61803398875 % 1.0) * 2 * math.pi
            frac = ((i * 0.38196601125 + 0.17) % 1.0)
            z = zb + h / 2 + 1.0 + frac * max(0.0, (zt - zb) - h - 2.0)
            s = scale_at(z) * 0.98
            centre = Vector((cx + rx * s * math.cos(angle), cy + ry * s * math.sin(angle), z))
            normal = Vector((math.cos(angle) / rx, math.sin(angle) / ry, 0.0)).normalized()
            tangent = Vector((-normal.y, normal.x, 0.0))
            pts = [centre + tangent * px + Vector((0, 0, pz)) + normal * 0.05 for px, pz in outline]
            mb.extruded_polygon(pts, normal * 0.22)
        ctx.emit(mb, e, "Windows", "backdrop" if backdrop else "glass")


def build_scaffold(ctx, e):
    x0, x1 = X(e["map"][0]), X(e["map"][2])
    zt, zb = Z(e["map"][1]), Z(e["map"][3])
    y0, y1 = e.get("y", [-1.5, 1.5])
    mb = MB()
    posts = max(2, e.get("posts", 2))
    for i in range(posts):
        px = x0 + (x1 - x0) * i / (posts - 1)
        for py in (y0, y1 - 0.14):
            mb.box(px - 0.07, px + 0.07, py, py + 0.14, zb, zt)
    for level in e["tiers"]:
        mb.box(x0 - 0.2, x1 + 0.2, y0, y1, Z(level) - 0.18, Z(level))
    ctx.emit(mb, e, "", "iron")


def build_slabs(ctx, e):
    y0, y1 = e.get("y", [-1.3, 1.3])
    mb = MB()
    for item in e["items"]:
        if len(item) == 2:
            half = e.get("w", 30) / 2
            xa, xb, level = item[0] - half, item[0] + half, item[1]
        else:
            xa, xb, level = item
        mb.box(X(xa), X(xb), y0, y1, Z(level) - 0.35, Z(level))
    ctx.emit(mb, e, "", e.get("mat", "stone"))


def build_cables(ctx, e):
    zt, zb = Z(e["map_y"][0]), Z(e["map_y"][1])
    mb = MB()
    for mx in e["xs"]:
        for dx in (-1.0, 1.0):
            mb.box(X(mx) + dx - 0.04, X(mx) + dx + 0.04, -0.04, 0.04, zb, zt)
    ctx.emit(mb, e, "", "iron")


def build_piers(ctx, e):
    y0, y1 = e.get("y", [-2.5, 2.5])
    mb = MB()
    for xa, xb, top in e["items"]:
        mb.box(X(xa), X(xb), y0, y1, Z(e.get("base", 3625)), Z(top))
    ctx.emit(mb, e, "", "stone")


def build_pillar(ctx, e):
    r = e.get("r", 12) / PPB
    mb = MB()
    mb.cylinder(X(e["x"]), e.get("yc", 0.0), Z(e["map_y"][1]), Z(e["map_y"][0]), r, r, segs=16)
    ctx.emit(mb, e, "", "glass")


def build_statue(ctx, e):
    cx, cy, z0 = X(e["x"]), e.get("yc", 2.0), Z(e["base"])
    height = e["height_px"] / PPB
    mb = MB()
    mb.box(cx - 3.4, cx + 3.4, cy - 2.6, cy + 2.6, z0, z0 + height * 0.10)           # stepped plinth
    mb.cylinder(cx, cy, z0 + height * 0.10, z0 + height * 0.20, 3.6, 2.8)                # lower basin
    mb.cone(cx, cy, z0 + height * 0.20, z0 + height * 0.36, 1.2, 1.2, top_scale=2.0)     # flaring upper basin
    mb.cone(cx, cy, z0 + height * 0.36, z0 + height * 0.92, 0.95, 0.8, top_scale=0.22)   # central cloaked figure
    for dx in (-0.25, 0.25):
        mb.cone(cx + dx, cy, z0 + height * 0.88, z0 + height, 0.10, 0.10, segs=6)        # horns
    for dx, dy in ((-1.5, -0.4), (1.5, -0.4), (0.0, 1.4)):
        mb.cone(cx + dx, cy + dy, z0 + height * 0.36, z0 + height * 0.66, 0.6, 0.5, top_scale=0.25)
    ctx.emit(mb, e, "", "placeholder")


def build_lamp(ctx, e):
    cx, cy, z0 = X(e["x"]), e.get("yc", 0.0), Z(e["base"])
    mb = MB()
    mb.box(cx - 0.06, cx + 0.06, cy - 0.06, cy + 0.06, z0, z0 + 2.7)
    mb.box(cx - 0.75, cx + 0.75, cy - 0.04, cy + 0.04, z0 + 2.62, z0 + 2.70)
    ctx.emit(mb, e, "Post", "iron")
    mb = MB()
    for dx in (-0.75, 0.75):
        mb.ellipsoid(cx + dx, cy, z0 + 2.38, 0.2, 0.2, 0.2, segs=10, steps=6)
    ctx.emit(mb, e, "Globes", "glass")


def build_marker(ctx, e):
    shape = e["shape"]
    x0, x1 = X(e["map"][0]), X(e["map"][2])
    zt, zb = Z(e["map"][1]), Z(e["map"][3])
    mb = MB()
    if shape == "box":
        y0, y1 = e["y"]
        mb.box(x0, x1, y0, y1, zb, zt)
    elif shape == "sphere":
        y0, y1 = e["y"]
        mb.ellipsoid((x0 + x1) / 2, (y0 + y1) / 2, (zt + zb) / 2, (x1 - x0) / 2, (y1 - y0) / 2, (zt - zb) / 2)
    elif shape == "cyl":
        mb.cylinder((x0 + x1) / 2, e.get("yc", 0.0), zb, zt, (x1 - x0) / 2, e.get("ry", (x1 - x0) / 2))
    elif shape == "cylx":
        y0, y1 = e["y"]
        cz, r = (zt + zb) / 2, (zt - zb) / 2
        ring = lambda x: [(x, (y0 + y1) / 2 + r * math.cos(2 * math.pi * i / 12), cz + r * math.sin(2 * math.pi * i / 12))
                          for i in range(12)]
        mb.rings([ring(x0), ring(x1)])
    elif shape == "spire":
        cy, r = e.get("yc", 40.0), (x1 - x0) / 2
        mb.cone((x0 + x1) / 2, cy, zb, zt, r, r, segs=10)
    elif shape == "hut":
        cy, r = e.get("yc", 1.0), (x1 - x0) / 2
        h = zt - zb
        mb.half_ellipsoid((x0 + x1) / 2, cy, zb, r, r, h * 0.55)
        mb.cone((x0 + x1) / 2, cy, zb + h * 0.5, zt, r * 0.35, r * 0.35, segs=10, top_scale=0.25)
    ctx.emit(mb, e, "", e.get("mat", "landmark"))


def build_simple(ctx, e):
    kind = e["type"]
    mb = MB()
    if kind in ("box", "slab", "water"):
        x0, x1 = X(e["map"][0]), X(e["map"][2])
        zt, zb = Z(e["map"][1]), Z(e["map"][3])
        y0, y1 = e.get("y", D["walkway_y"])
        if kind == "water":
            zt, zb = zt, zt - 0.06
        mb.box(x0, x1, y0, y1, zb, zt)
        ctx.emit(mb, e, "", "water" if kind == "water" else e.get("mat", "stone"))
    elif kind == "rock":
        x0, x1 = X(e["map"][0]), X(e["map"][2])
        zt, zb = Z(e["map"][1]), Z(e["map"][3])
        y0, y1 = e["y"]
        salt = (sum(ord(c) for c in ctx.region_id + e["id"]) % 97) * 0.37
        amp = e.get("amp", min(1.6, 0.06 * max(x1 - x0, zt - zb, y1 - y0) + 0.3))
        mb.rock(x0, x1, y0, y1, zb, zt, amp, salt)
        ctx.emit(mb, e, "", "hostrock" if e.get("layer") == "HOSTROCK" else "rock")
    elif kind == "poly":
        y0, y1 = e["y"]
        mb.prism([(X(px), Z(py)) for px, py in e["pts"]], y0, y1)
        ctx.emit(mb, e, "", e.get("mat", "rock"))


BUILDERS = {
    "stack": build_stack, "shaft": build_shaft, "bridge": build_bridge, "canopy": build_canopy,
    "pavilion": build_pavilion, "dome": build_dome, "tower": build_tower, "scaffold": build_scaffold,
    "slabs": build_slabs, "cables": build_cables, "piers": build_piers, "pillar": build_pillar,
    "statue": build_statue, "lamp": build_lamp, "marker": build_marker,
    "box": build_simple, "slab": build_simple, "water": build_simple, "rock": build_simple, "poly": build_simple,
}

# --------------------------------------------------------------------------- regions
summary = {}
for region in LAYOUT["regions"]:
    rid = region["id"]
    if ONLY is not None and rid not in ONLY:
        continue
    remove_generated(rid)
    coll = collection("COT_R_" + rid, C_REGIONS)
    coll["cot_region"] = rid
    ctx = Ctx(rid, coll)
    for element in region["elements"]:
        BUILDERS[element["type"]](ctx, element)
    summary[rid] = ctx.count

# --------------------------------------------------------------------------- reference: labels, links, scale figure
if ONLY is None:
    remove_generated("_Reference")
    remove_generated("_Cameras")
    ref_props = {"cot_generated": True, "cot_region": "_Reference"}
    anchors = {}
    for region in LAYOUT["regions"]:
        if region["id"].startswith("_"):
            continue
        lx, ly = region["label"]
        anchors[region["id"]] = (lx, ly)
        curve = bpy.data.curves.new("REF_Label_" + region["id"], "FONT")
        curve.body = region["id"]
        curve.size = 4.2
        curve.align_x = "CENTER"
        curve.materials.append(material("ref_text"))
        text = bpy.data.objects.new("REF_Label_" + region["id"], curve)
        text.location = (X(lx), -18.0, Z(ly))
        text.rotation_euler = (math.radians(90.0), 0.0, 0.0)
        for key, value in ref_props.items():
            text[key] = value
        C_REFERENCE.objects.link(text)
    for index, link in enumerate(LAYOUT.get("connections", [])):
        curve = bpy.data.curves.new(f"REF_Link_{index:02d}", "CURVE")
        curve.dimensions = "3D"
        curve.bevel_depth = 0.45
        spline = curve.splines.new("POLY")
        pts = link["path"]
        spline.points.add(len(pts) - 1)
        for point, (mx, my) in zip(spline.points, pts):
            point.co = (X(mx), -17.0, Z(my), 1.0)
        curve.materials.append(material("ref_" + link["ev"]))
        obj = bpy.data.objects.new(f"REF_Link_{index:02d}_{link['a']}__{link['b']}", curve)
        obj["cot_link_a"], obj["cot_link_b"], obj["cot_link_ev"] = link["a"], link["b"], link["ev"]
        for key, value in ref_props.items():
            obj[key] = value
        C_REFERENCE.objects.link(obj)
    mb = MB()
    mb.cylinder(X(3660), -1.0, Z(3587), Z(3587) + 1.0, 0.22, 0.22, segs=12)
    figure = mb.to_object("REF_ScaleFigure_1H", C_REFERENCE, "landmark", dict(ref_props))
    C_REFERENCE.hide_render = True

    # ----------------------------------------------------------------------- cameras
    for spec in LAYOUT.get("cameras", []):
        data = bpy.data.cameras.new(spec["id"] + "_data")
        cam = bpy.data.objects.new(spec["id"], data)
        data.clip_start, data.clip_end = 0.1, 3000.0
        ax, ay, depth = spec["at"]
        location = Vector((X(ax), depth, Z(ay)))
        if spec["type"] == "ORTHO":
            data.type = "ORTHO"
            data.ortho_scale = spec["ortho_scale"]
        else:
            data.lens = spec.get("lens", 35.0)
        if "look" in spec:
            lx, ly, ldepth = spec["look"]
            direction = Vector((X(lx), ldepth, Z(ly))) - location
            cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        else:
            cam.rotation_euler = [math.radians(v) for v in spec["rot"]]
        cam.location = location
        cam["cot_generated"], cam["cot_region"] = True, "_Cameras"
        cam["cot_hide"] = ",".join(spec.get("hide", []))
        cam["cot_show_reference"] = bool(spec.get("reference", False))
        cam["cot_res"] = spec.get("res", [1920, 1080])
        cam["cot_purpose"] = spec.get("purpose", "")
        if "map_box" in spec:
            cam["cot_map_box"] = [float(v) for v in spec["map_box"]]
        C_CAMERAS.objects.link(cam)
    first = next((o for o in C_CAMERAS.objects if o.type == "CAMERA"), None)
    if first is not None:
        scene.camera = first

# --------------------------------------------------------------------------- display + save
world = scene.world or bpy.data.worlds.new("COT_World")
scene.world = world
world.color = (0.015, 0.025, 0.045)
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.view_settings.view_transform = "Standard"

MASTER.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER))
report = {"master": str(MASTER), "regions_built": summary, "objects_total": len(bpy.data.objects),
          "generated": sum(1 for o in bpy.data.objects if o.get("cot_generated")),
          "manual_preserved": sum(1 for o in bpy.data.objects if not o.get("cot_generated")),
          "cameras": len([o for o in bpy.data.objects if o.type == "CAMERA"])}
if CHECKPOINT:
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    existing = sorted(CHECKPOINTS.glob("city_greybox_v*.blend"))
    version = (int(existing[-1].stem.split("_v")[-1]) + 1) if existing else 1
    target = CHECKPOINTS / f"city_greybox_v{version:03d}.blend"
    shutil.copy2(MASTER, target)
    report["checkpoint"] = str(target)
(ROOT / "logs").mkdir(exist_ok=True)
if "--master" not in argv:
    (ROOT / "logs" / "build_city_last.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("COT_BUILD", json.dumps(report, ensure_ascii=False))
