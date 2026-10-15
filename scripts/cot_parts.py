"""Stage 3 composite builders: rooms, lifts, towers, roofs, railings, rock and prop placement.

These use a cot_s3.Session (S) so that every object is tagged and repeated parts share kit datablocks.
Sizes are in Blender units (1 unit = 1 H, the project yardstick). Depths and backs are level-C completion.
"""
import json
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

import cot_assets as A
import cot_creatures as CR
import cot_furnish as FU
import cot_kit as K
import cot_shell as SH
from cot_geo import Geo, IronCurves, TAU, lerp, place, rng
from cot_s3 import MX, MY, PROJECT, X, Z

D = PROJECT["depth_defaults"]
WALL, FLOOR = D["wall"], D["floor"]


def wel(eid, x0, x1, zb, zt, floors=None, **kw):
    """Layout-style element from world coordinates (for rooms that are not in config/layout.json)."""
    e = {"id": eid, "type": "stack", "map": [MX(x0), MY(zt), MX(x1), MY(zb)], "floors": [MY(z) for z in (floors if floors is not None else [zb])]}
    if "doors" in kw:
        kw["doors"] = [[d[0], MY(d[1])] + list(d[2:]) for d in kw["doors"]]
    if "voids" in kw:
        kw["voids"] = [[MX(v[0]), MX(v[1])] + ([MY(v[3]), MY(v[2])] if len(v) > 3 else []) for v in kw["voids"]]
    e.update(kw)
    return e


def carve_s2_box(obj_name, box, tol=0.03):
    """Remove a placeholder solid (an axis-aligned box given as x0, y0, z0, x1, y1, z1) from a stage 2 sample mesh.

    Stage 2 stood in solid boxes for buildings whose interiors belong to stage 3. Only faces whose four corners
    are corners of that exact box are deleted; everything else in the mesh stays. Idempotent.
    """
    obj = bpy.data.objects.get(obj_name)
    if obj is None or obj.type != "MESH":
        return -1
    x0, y0, z0, x1, y1, z1 = box
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    def corner(v):
        c = v.co
        return (min(abs(c.x - x0), abs(c.x - x1)) < tol and min(abs(c.y - y0), abs(c.y - y1)) < tol and min(abs(c.z - z0), abs(c.z - z1)) < tol)

    faces = [f for f in bm.faces if len(f.verts) == 4 and all(corner(v) for v in f.verts)]
    if faces:
        bmesh.ops.delete(bm, geom=faces, context="FACES")
        bm.to_mesh(obj.data)
        obj.data.update()
        done = list(obj.get("cot_s3_carved", []))
        obj["cot_s3_carved"] = done + [float(v) for v in box]
    bm.free()
    return len(faces)

# Region styles: what distinguishes the districts structurally (arch form, wall bays, lamps). Lighting is stage 4.
STYLES = {
    # blue lancet interiors of the central block and the left-well block (11_Lower_City middle / upper, 03_Left_City left_upper)
    "blue": dict(furniture="blue", ceiling="ribs", ext="stone_far", fringe=True, wall="wall_blue", floor="floor", trim="trim", front="pointed", bay=4.2, back=("lancet", "noble", "lancet", "niche"), side_portraits=True,
                 glass="glass_blue", lamp="string", partition=3, rail=True),
    # low stone arcades of the western streets and corridors (05_Streets)
    "street": dict(furniture="street", ceiling="beams", ext="stone_far", wall="stone_far", floor="stone", trim="stone_far_trim", front="round", bay=4.4, back=("blind", "lancet"),
                   glass="glass_blue", lamp="string", partition=0, rail=False),
    # Soul Sanctum: pale stone, round arches, oval mirrors and cold white windows (01_Soul_Sanctuary)
    "sanctum": dict(furniture="sanctum", ceiling="ribs", ext="wall_sanctum", fringe=True, wall="wall_sanctum", floor="floor", trim="trim_pale", front="round", bay=5.0, back=("oval", "tall", "noble", "shelf_pale"), side_portraits=True,
                    glass="glass_white", lamp="orb", partition=3, rail=False),
    # purple interiors of the east city (06_Right_City step1-3, peak; 13_Lighting/Lighting_04)
    "purple": dict(furniture="purple", ceiling="ribs", ext="house_wall", fringe=True, wall="wall_purple", floor="floor", trim="trim_purple", front="cusp", bay=4.4, back=("shelf", "noble", "web", "drape"), side_portraits=True,
                   glass="glass_purple", lamp="round", partition=3, rail=True),
    # tower block: blue stone with pink glass, portraits and web tracery (08_Tower)
    "tower": dict(furniture="tower", ceiling="ribs", ext="stone_far", fringe=True, wall="wall_blue", floor="floor", trim="trim", front="pointed", bay=4.4, back=("web", "noble", "lancet", "portrait"), side_portraits=True,
                  glass="glass_pink", lamp="string", partition=4, rail=True),
    # plain service corridors known only from the master map
    "corridor": dict(furniture="corridor", ceiling="beams", ext="stone_far", wall="wall_deep", floor="floor", trim="trim", front="round", bay=5.0, back=("blind", "niche"),
                     glass="glass_blue", lamp="string", partition=0, rail=False),
    # jar house at the east end (master C4): purple, plain bays that carry shelves of jars
    "jar": dict(furniture="jar", ceiling="beams", ext="house_wall", fringe=True, wall="wall_purple", floor="floor", trim="trim_purple", front="round", bay=4.0, back=("jars",),
                glass="glass_purple", lamp="round", partition=0, rail=True),
    # green atrium side rooms (07_Interior)
    "green": dict(furniture="green", ceiling="beams", ext="stone_far", wall="wall_green", floor="floor", trim="trim", front="round", bay=4.0, back=("blind", "lancet"),
                  glass="glass_blue", lamp="string", partition=0, rail=True),
}


def q(v, step=0.05):
    return round(v / step) * step


def split_interval(a, b, holes):
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


def fit_arch(kind, w, height, clear_top=0.45, min_spring=1.9):
    """Arch kind, rise and springing height that fit an opening of width w into a storey of the given height."""
    rise = K.arch_rise(w, kind)
    if height - clear_top - rise < min_spring:
        avail = height - clear_top - min_spring
        if avail < 0.3:
            rise = max(0.18, height * 0.1)
            return "flat", rise, max(0.6, height - clear_top - rise)
        if kind == "pointed":
            rise = avail
        elif kind == "cusp":
            rise = avail
        else:
            kind, rise = "flat", avail
    return kind, rise, height - clear_top - rise


# ---------------------------------------------------------------------------- kit accessors
def kit_column(S, h, r=0.15, key="trim"):
    h = max(1.4, q(h, 0.1))
    return S.kit(f"column_{key}_{h:.1f}_{r:.2f}", lambda: K.k_column(h, r, key))


def kit_window(S, kind, w, h, glass):
    w, h = q(w, 0.1), q(h, 0.1)
    key = f"win_{kind}_{w:.1f}_{h:.1f}_{glass}"
    if kind == "lancet":
        return S.kit(key, lambda: K.k_window_lancet(w, h, glass))
    if kind == "web":
        return S.kit(key, lambda: K.k_window_lancet(w, h, glass, web=True))
    if kind == "tall":
        return S.kit(key, lambda: K.k_window_tall(w, h, glass))
    if kind == "oval":
        return S.kit(key, lambda: K.k_oval(w, h, "mirror"))
    if kind == "oval_glass":
        return S.kit(key, lambda: K.k_oval(w, h, glass, frame="trim_purple"))
    raise KeyError(kind)


def kit_objs(S, key, build):
    """Kit datablocks produced by a stage 2 builder that returns objects (e.g. the validated street lamp)."""
    if key in S.kit_done:
        return S.kit_done[key]
    tmp = bpy.data.collections.new("TMP_S3_KIT")
    objs = [o for o in build(tmp) if o is not None]
    datas = []
    for i, o in enumerate(objs):
        d = o.data
        name = f"KIT3_{key}_{i}"
        store = bpy.data.meshes if o.type == "MESH" else bpy.data.curves
        old = store.get(name)
        if old is not None and old != d:
            old.user_remap(d)
            store.remove(old)
        d.name = name
        d["cot_s3_kit"] = key
        datas.append(d)
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(tmp)
    S.kit_done[key] = datas
    return datas


# ---------------------------------------------------------------------------- single placements
def lamp(S, rid, name, x, y, z, rz=0.0, ev="A", ref="12_Materials/Materials_01.jpg", layer=None):
    """Double-headed street lamp validated in stage 2."""
    datas = kit_objs(S, "lamp_double", lambda coll: A.build_lamp(coll, S.mat, name="lamp"))
    return [S.put(d, f"{name}_{'Iron' if i == 0 else 'Globes'}", rid, "LampDouble", place(x, y, z, rz=rz), ev, ref, layer=layer) for i, d in enumerate(datas)]


def railing(S, rid, name, p0, p1, z, ev="A", ref="12_Materials/Materials_01.jpg", layer=None):
    """Ornate railing of the stage 2 bay along a line (instances; scaled along the run to fit)."""
    (ax, ay), (bx, by) = p0, p1
    length = math.hypot(bx - ax, by - ay)
    n = max(1, int(round(length / 1.05)))
    sx = length / (n * 1.05)
    rz = math.atan2(by - ay, bx - ax)
    bay = S.kit("rail_bay", lambda: (A.railing_bay_curves(1.05), "iron", 0.02))
    end = S.kit("rail_bay_end", lambda: (A.railing_bay_curves(1.05, final_post=True), "iron", 0.02))
    out = []
    for i in range(n):
        m = place(lerp(ax, bx, i / n), lerp(ay, by, i / n), z, rz=rz) @ Matrix.Diagonal((sx, 1.0, 1.0, 1.0))
        out.append(S.put(end if i == n - 1 else bay, f"{name}_{i:02d}", rid, "RailingBay", m, ev, ref, layer=layer))
    return out


def spike_rail(S, rid, name, runs, z=None, ev="A", ref="", layer=None, h=0.95, note=""):
    """Plain spear railing as one mesh. runs: ((x0, y0), (x1, y1), z) or with a shared z."""
    g = Geo()
    for run in runs:
        p0, p1 = run[0], run[1]
        zz = run[2] if len(run) > 2 else z
        K.spike_rail(g, p0, p1, zz, h=h)
    return S.add(g, name, rid, "SpikeRail", ev, ref, note=note, layer=layer)


def tower(S, rid, name, cx, cy, z0, z1, r, windows=10, roof="dome", seed=1, leaf=(2.6, 6.8), tier=7.5, ry_scale=1.0, far=False,
          ev="A", ref="", note="", layer=None, arc=(-math.pi, math.pi), taper=None, z_win=None):
    """Shell tower with fringe tiers and leaf windows (stage 2 builder). Windows are spread without overlaps."""
    w, h = leaf
    rand = rng(seed * 977 + 31)
    wins = []
    zlo, zhi = z_win if z_win else (z0 + h / 2 + 1.5, z1 - h / 2 - 1.0)
    tries = 0
    while len(wins) < windows and tries < windows * 30 and zhi > zlo:
        tries += 1
        th = lerp(arc[0], arc[1], rand())
        z = lerp(zlo, zhi, rand())
        s = rand(0.8, 1.15)
        ok = True
        for t2, z2, w2, h2 in wins:
            d_ang = abs((th - t2 + math.pi) % TAU - math.pi) * r
            if d_ang < (w * s + w2) * 0.75 and abs(z - z2) < (h * s + h2) * 0.56:
                ok = False
                break
        if ok:
            wins.append((th, z, w * s, h * s))
    objs = A.build_tower(S.coll(rid, layer), S.mat, name, cx, cy, z0, z1, r, tier, wins, roof=roof, seed=seed, props=None, ry_scale=ry_scale,
                         glass_key="glass_far_blue" if far else "glass", fringe_key="tower_far" if far else "fringe", taper=taper)
    return S.adopt(objs, rid, name, ev, ref, note, layer)


def louvre_roof(S, rid, name, x0, x1, zb, zt, y0, y1, bays=3, curve_end="W", ev="A", ref="", note="", layer=None, spikes=True, scallop=True):
    objs = A.build_louvre_roof(S.coll(rid, layer), S.mat, name, x0, x1, zb, zt, y0, y1, bays=bays, curve_end=curve_end, props=None, spikes=spikes, scallop=scallop)
    return S.adopt(objs, rid, name, ev, ref, note, layer)


def glass_pillar(S, rid, name, x, y, r, z0, z1, ev="A", ref="", note="", layer=None):
    objs = A.build_glass_pillar(S.coll(rid, layer), S.mat, name, r, z0, z1, props=None)
    for o in objs:
        o.location = (x, y, 0.0)
    return S.adopt(objs, rid, name, ev, ref, note, layer)


def scaffold(S, rid, name, posts, bays, ev="A", ref="", note="", layer=None):
    objs = A.build_scaffold(S.coll(rid, layer), S.mat, name, posts, bays, props=None)
    return S.adopt(objs, rid, name, ev, ref, note, layer)


def shell_block(S, rid, name, x0, x1, y0, y1, z0, z1, tier=7.0, seed=1, windows=(), ev="C", ref="", note="", layer=None, far=False, e=0.3,
                glass=None, hang=True):
    """Black fringed building mass (rounded rectangle in plan) with optional leaf windows.

    windows: (face, position along the face, z, width, height); face is S / N / E / W.
    hang: the lowest fringe tier hangs below z0 (over open space); False when the mass sits on a building, so its
    ragged hem (up to about half the tier height) ends at z0 instead of reaching into the rooms below.
    """
    g = Geo()
    cx, cy, hx, hy = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    SH.shell_core(g, cx, cy, hx, hy, z0, z1, e)
    tiers = max(1, round((z1 - z0) / tier))
    th = (z1 - z0) / tiers
    for k in range(tiers):
        if k == 0 and not hang and tiers > 1:
            continue                                     # the next tier's hem (about 0.52 x tier height) then ends near z0, over the bare core
        zb = z0 + th * k - th * 0.3 if (k or hang) else z0 + th * 0.344
        SH.fringe_tier_rect(g, cx, cy, hx, hy, z0 + th * (k + 1), zb, seed=seed * 31 + k, e=e, key="tower_far" if far else "fringe")
    out = [S.add(g, name + "_Body", rid, name, ev, ref, note, layer, smooth=60)]
    if windows:
        gf, gg = Geo(), Geo()
        for i, (face, u, z, w, h) in enumerate(windows):
            px, py, rz = {"S": (u, y0 - 0.55, 0.0), "N": (u, y1 + 0.55, math.pi), "E": (x1 + 0.55, u, math.pi / 2), "W": (x0 - 0.55, u, -math.pi / 2)}[face]
            A.add_leaf_window(gf, gg, place(px, py, z, rz=rz), w, h, index=i + seed * 7, glass_key=glass or ("glass_far_blue" if far else "glass"))
        out.append(S.add(gf, name + "_WindowFrames", rid, name, ev, ref, note, layer))
        out.append(S.add(gg, name + "_WindowGlass", rid, name, ev, ref, note, layer))
    return out


def louvre_band(S, rid, name, x0, x1, y0, y1, zb, zt, posts=None, spikes=True, ev="A", ref="", note="", layer=None, scallop=True):
    g = Geo()
    SH.louvre_band(g, x0, x1, y0, y1, zb, zt, posts=posts, spikes=spikes)
    if scallop:
        for yy in (y0 - 0.34, y1 + 0.34):
            SH.scallop_trim(g, x0, x1, yy, zb - 0.26)
    return S.add(g, name, rid, name, ev, ref, note, layer, smooth=35)


def rock(S, rid, name, x0, x1, y0, y1, z0, z1, ev="C", ref="", note="", layer="ROCK", amp=None, seed=None, cell=2.4, key="rock"):
    g = Geo()
    seed = seed if seed is not None else (sum(ord(c) for c in rid + name) % 97)
    K.rock(g, x0, x1, y0, y1, z0, z1, amp=amp, seed=seed, cell=cell, key=key)
    return S.add(g, name, rid, name, ev, ref, note=note, layer=layer, smooth=48)


def _chunks(a, b, size):
    n = max(1, int(round((b - a) / size)))
    return [(a + (b - a) * i / n, a + (b - a) * (i + 1) / n) for i in range(n)]


def _rect_minus(r, h):
    """Parts of rectangle r = (a0, a1, b0, b1) outside rectangle h."""
    a0, a1, b0, b1 = r
    h0, h1, k0, k1 = max(h[0], a0), min(h[1], a1), max(h[2], b0), min(h[3], b1)
    if h1 <= h0 or k1 <= k0:
        return [r]
    out = [(a0, h0, b0, b1), (h1, a1, b0, b1), (h0, h1, b0, k0), (h0, h1, k1, b1)]
    return [q for q in out if q[1] - q[0] > 0.8 and q[3] - q[2] > 0.8]


def rock_skin(g, box, face, a=0.9, size=44.0, seed=0, hole=None):
    """Rough rock slab just inside one face of a box (front / back / bottom / top / west / east); it never reaches beyond the box.
    hole: a box kept clear (the skin is left out over it, with a margin for the roughness)."""
    x0, x1, y0, y1, z0, z1 = box
    depth = {"front": y1 - y0, "back": y1 - y0, "bottom": z1 - z0, "top": z1 - z0, "west": x1 - x0, "east": x1 - x0}[face]
    t = max(0.2, min(3.0, depth - 2 * a))               # a thin mass gets a thin skin, so the skin stays inside the box
    spans = {"front": ("xz", (y0 + a, y0 + a + t)), "back": ("xz", (y1 - a - t, y1 - a)), "bottom": ("xy", (z0 + a, z0 + a + t)), "top": ("xy", (z1 - a - t, z1 - a)),
             "west": ("yz", (x0 + a, x0 + a + t)), "east": ("yz", (x1 - a - t, x1 - a))}
    plane, (n0, n1) = spans[face]
    cell = size / 22.0
    axes = {"xz": ((x0, x1), (z0, z1), 1), "xy": ((x0, x1), (y0, y1), 2), "yz": ((y0, y1), (z0, z1), 0)}[plane]
    (u0, u1), (v0, v1), normal = axes
    cut = None
    if hole is not None:
        hx = {"xz": (hole[0], hole[1], hole[4], hole[5], hole[2], hole[3]), "xy": (hole[0], hole[1], hole[2], hole[3], hole[4], hole[5]),
              "yz": (hole[2], hole[3], hole[4], hole[5], hole[0], hole[1])}[plane]
        m = a + 0.6
        if hx[4] - m < n1 and hx[5] + m > n0:
            cut = (hx[0] - m, hx[1] + m, hx[2] - m, hx[3] + m)
    for ca, cb in _chunks(u0 + a, u1 - a, size):
        for da, db in _chunks(v0 + a, v1 - a, size):
            for qa, qb, qc, qd in (_rect_minus((ca, cb, da, db), cut) if cut else [(ca, cb, da, db)]):
                if plane == "xz":
                    K.rock(g, qa - 0.4, qb + 0.4, n0, n1, qc - 0.4, qd + 0.4, amp=a, seed=seed, cell=cell, rounding=0.0)
                elif plane == "xy":
                    K.rock(g, qa - 0.4, qb + 0.4, qc - 0.4, qd + 0.4, n0, n1, amp=a, seed=seed, cell=cell, rounding=0.0)
                else:
                    K.rock(g, n0, n1, qa - 0.4, qb + 0.4, qc - 0.4, qd + 0.4, amp=a, seed=seed, cell=cell, rounding=0.0)


def host(S, rid, name, box, faces=("front",), ev="C", ref="", note="", layer="ROCK", a=None, size=44.0, seed=None, asset=None, hole=None):
    """Rock mass that buildings stand against: an exact core (keeps rooms closed) behind rough rock on the visible faces."""
    x0, x1, y0, y1, z0, z1 = box
    if a is None:
        a = 0.9 if min(x1 - x0, y1 - y0, z1 - z0) > 6.0 else 0.4
    seed = seed if seed is not None else (sum(ord(c) for c in rid + name) % 97)
    g = Geo().use("rock")
    core = [x0, x1, y0, y1, z0, z1]
    for f in faces:
        i, sgn = {"front": (2, 1), "back": (3, -1), "bottom": (4, 1), "top": (5, -1), "west": (0, 1), "east": (1, -1)}[f]
        core[i] += sgn * (2 * a + 0.2)
    if core[1] > core[0] and core[3] > core[2] and core[5] > core[4]:
        if hole is None:
            g.box(*core)
        else:                                                  # keep a built volume (a tunnel stub) clear of the core
            cx0, cx1, cy0, cy1, cz0, cz1 = core
            hx0, hx1, hy0, hy1, hz0, hz1 = (max(hole[0], cx0), min(hole[1], cx1), max(hole[2], cy0), min(hole[3], cy1), max(hole[4], cz0), min(hole[5], cz1))
            for bx in ((cx0, hx0, cy0, cy1, cz0, cz1), (hx1, cx1, cy0, cy1, cz0, cz1), (hx0, hx1, hy1, cy1, cz0, cz1), (hx0, hx1, cy0, hy0, cz0, cz1),
                       (hx0, hx1, hy0, hy1, hz1, cz1), (hx0, hx1, hy0, hy1, cz0, hz0)):
                if bx[1] - bx[0] > 1e-3 and bx[3] - bx[2] > 1e-3 and bx[5] - bx[4] > 1e-3:
                    g.box(*bx)
    for k, f in enumerate(faces):
        rock_skin(g, box, f, a, size, seed + k, hole=hole)
    return S.add(g, name, rid, asset or name, ev, ref, note=note, layer=layer, smooth=48)


def water(S, rid, name, x0, x1, y0, y1, z, ev="A", ref=""):
    g = Geo().use("water")
    g.box(x0, x1, y0, y1, z - 0.06, z)
    return S.add(g, name, rid, "Water", ev, ref)


def scatter(S, rid, data, name, asset, items, ev="A", ref="", layer=None, note=""):
    """items: (x, y, z) or (x, y, z, rz) or (x, y, z, rz, scale)."""
    out = []
    for i, it in enumerate(items):
        x, y, z = it[:3]
        rz = it[3] if len(it) > 3 else 0.0
        s = it[4] if len(it) > 4 else 1.0
        out.append(S.put(data, f"{name}_{i:03d}", rid, asset, place(x, y, z, rz=rz, s=s), ev, ref, layer=layer, note=note))
    return out


def clusters(S, rid, name, items, ev="A", ref="", layer=None, note=""):
    """Spotted clusters: items (x, y, z, scale, tilt_x, tilt_y, variant)."""
    kits = [S.kit(f"cluster_{v}", lambda v=v: K.k_cluster(seed=v, n=8 + v % 3)) for v in range(4)]
    out = []
    for i, (x, y, z, s, rx, ry, v) in enumerate(items):
        m = place(x, y, z, rz=i * 1.7, s=s, rx=rx, ry=ry)
        out.append(S.put(kits[v % 4], f"{name}_{i:03d}", rid, "SpottedCluster", m, ev, ref, layer=layer, note=note))
    return out


def cluster_field(S, rid, name, x0, x1, z0, z1, y, count, seed=0, facing="front", size=(0.7, 1.5), ev="A", ref="", layer=None, y_jitter=0.6, keep=None):
    """Clusters studding a wall (facing 'front' = growing toward -Y), a floor ('up') or a ceiling ('down')."""
    rand = rng(seed * 131 + 17)
    items = []
    tries = 0
    while len(items) < count and tries < count * 6:
        tries += 1
        a, b = rand(x0, x1), rand(z0, z1)
        if keep is not None and not keep(a, b):
            continue
        s = rand(*size)
        if facing == "front":
            items.append((a, y + rand(-y_jitter, 0.1), b, s, math.pi / 2 + rand(-0.4, 0.4), rand(-0.4, 0.4), int(rand(0, 4))))
        elif facing == "up":
            items.append((a, b, y, s, rand(-0.25, 0.25), rand(-0.25, 0.25), int(rand(0, 4))))
        else:
            items.append((a, b, y, s, math.pi + rand(-0.3, 0.3), rand(-0.3, 0.3), int(rand(0, 4))))
    return clusters(S, rid, name, items, ev, ref, layer)


# ---------------------------------------------------------------------------- room stacks
def sits_on(S, e, x0, x1, yf, yb, zf):
    """Roof top of another layout stack this one stands on: its top lies within 0.8 m below / 0.3 m above this stack's
    lowest floor and the two overlap in plan by 2 m or more. Read from the layout, so the answer does not depend on
    which regions are rebuilt."""
    best = None
    for reg in S.layout.values():
        for o in reg.get("elements", []):
            if o.get("type") != "stack" or "map" not in o or (o.get("id") == e.get("id") and o.get("map") == e.get("map")):
                continue
            zt_o = Z(o["map"][1])
            if not (zf - 0.8 <= zt_o <= zf + 0.3):
                continue
            if min(x1, X(o["map"][2])) - max(x0, X(o["map"][0])) < 2.0:
                continue
            oy = o.get("y", D["stack_y"])
            if min(yb, oy[1]) - max(yf, oy[0]) < 2.0:
                continue
            best = zt_o + FLOOR if best is None else max(best, zt_o + FLOOR)
    return best


def stack(S, rid, e, style="blue", name=None, y=None, front=True, roof=True, rear=True, lamps=True, decor=True, ev=None, ref=None,
          front_rail=None, levels=None, note="", skip_bays=None, side_open=(), door_y=None, ext_faces=("L", "R", "N"), shaft_y=None, rail_skip=(), cells=(), furnish=None, furn_skip=(), keep_clear=()):
    """Multi-storey building from a layout 'stack' element: slabs, walls with door arches, decorated back wall,
    arcaded viewer-side facade (FRONT layer), partitions, lamps. Returns a dict of useful coordinates.

    levels: optional per-storey overrides {index: dict(back=(...), lamp=..., front=...)}; index 0 is the lowest storey.
    side_open: sides ("L", "R") left without a wall (the stack continues into a neighbour).
    cells: (storey index, map x0, map x1) parts of a storey that are solid black building mass, as the master map draws
    them inside many outlines; they are snapped to whole bays and get no rooms, decor, lamps or front openings.
    furnish: put the style's furniture in the rooms (default: when decor is on and the style names a furniture set);
    furn_skip: (storey, bay) pairs kept free of furniture (region-specific pieces stand there).
    keep_clear: (storey, x0, x1, y0, y1) rectangles kept free of furniture and creatures (region-specific pieces).
    The returned dict has "room": the furnished storeys and a free(storey, x, y, radius) test, for placing creatures.
    """
    st = dict(STYLES[style]) if isinstance(style, str) else dict(style)
    name = name or e["id"]
    ev = ev or e.get("ev", "A")
    ref = ref if ref is not None else e.get("ref", "")
    x0, x1 = X(e["map"][0]), X(e["map"][2])
    zt, zb = Z(e["map"][1]), Z(e["map"][3])
    yf, yb = y if y is not None else e.get("y", D["stack_y"])
    floors = sorted(Z(v) for v in e.get("floors", [e["map"][3]]))
    # a stack standing on another one starts on that one's roof slab: its lowest floor is lifted to the roof top, so
    # neither slab nor the rear dressing reaches into the room below (D-351)
    base = sits_on(S, e, x0, x1, yf, yb, floors[0])
    if base is not None and floors[0] < base + 0.02 and (len(floors) == 1 or floors[1] - base > 2.0):
        floors[0] = base + 0.02
    bottom = floors[0] - FLOOR
    voids = [(X(v[0]), X(v[1]), Z(v[3]) if len(v) > 3 else -1e9, Z(v[2]) if len(v) > 2 else 1e9) for v in e.get("voids", [])]
    sy0, sy1 = shaft_y if shaft_y is not None else D["shaft_y"]
    wall, floor, trim = st["wall"], st["floor"], st["trim"]
    C = "C" if ev == "A" else ev

    # ---- slabs
    g = Geo()
    full = {(X(v[0]), X(v[1])) for v in e.get("voids", []) if len(v) > 4 and v[4]}      # voids that take the whole depth (double-height rooms)

    def full_at(zf, top):
        out = []
        for v in e.get("voids", []):
            if len(v) > 4 and v[4]:
                lo, hi = Z(v[3]) - 0.6, Z(v[2]) + 0.6
                if lo <= zf <= hi or lo <= top + FLOOR <= hi:
                    out.append((X(v[0]), X(v[1])))
        return out
    for zf in floors:
        holes = [(a, b) for a, b, lo, hi in voids if lo <= zf <= hi]
        for a, b in split_interval(x0 + WALL, x1 - WALL, holes):
            K.slab(g, a, b, yf - 0.3, yb - WALL, zf, FLOOR, floor, lip=("front",), trim=trim)
        for a, b in holes:
            if (a, b) in full:
                continue
            a, b = max(a, x0 + WALL), min(b, x1 - WALL)
            K.slab(g, a, b, yf - 0.3, sy0, zf, FLOOR, floor, lip=("front",), trim=trim)
            K.slab(g, a, b, sy1, yb - WALL, zf, FLOOR, floor, lip=(), trim=trim)
    if roof:
        holes = [(a, b) for a, b, lo, hi in voids if lo <= zt <= hi]
        for a, b in split_interval(x0 - 0.3, x1 + 0.3, holes):
            K.slab(g, a, b, yf - 0.45, yb + 0.3, zt + FLOOR, FLOOR, floor, lip=("front", "back"), trim=trim)
        for a, b in holes:
            K.slab(g, a, b, yf - 0.45, sy0, zt + FLOOR, FLOOR, floor, lip=("front",), trim=trim)
            K.slab(g, a, b, sy1, yb + 0.3, zt + FLOOR, FLOOR, floor, lip=("back",), trim=trim)
    S.add(g, name + "_Floors", rid, name, ev, ref, note=note)

    # ---- storeys
    storeys = []
    for i, zf in enumerate(floors):
        top = (floors[i + 1] - FLOOR) if i + 1 < len(floors) else zt
        if top - zf > 1.2:
            storeys.append((i, zf, top))

    # storeys marked solid are black building mass between rooms (A: black bands inside the outlines on the master)
    solid = {i for i, ov in (levels or {}).items() if ov.get("solid")}
    solid_storeys = [t for t in storeys if t[0] in solid]
    storeys = [t for t in storeys if t[0] not in solid]

    # ---- walls: an inner lining in the room material and an outer skin in the exterior material
    ext = st.get("ext", wall)
    g = Geo()
    for i, zf, top in solid_storeys:
        g.use("mass_black")                                    # 1 cm off the floor and ceiling faces: no coplanar faces (D-383)
        g.box(x0 + WALL, x1 - WALL, yf + 0.02, yb - WALL, zf + 0.01, top - 0.01)
        SH.hanging_fringe(g, x0 + WALL + 0.2, x1 - WALL - 0.2, yf + 0.35, zf - FLOOR, 1.7, seed=i * 11 + 2)
    door_cy = min(max(0.0, yf + 2.4), yb - 2.4)
    door_at = {}
    for side, xa, xb in (("L", x0, x0 + WALL), ("R", x1 - WALL, x1)):
        if side in side_open:
            continue
        doors = {}
        for d in e.get("doors", []):
            if d[0] == side:
                zn = min(floors, key=lambda f: abs(f - Z(d[1])))      # the door stands on the nearest floor
                if abs(zn - Z(d[1])) < 0.8:
                    doors[round(zn, 2)] = d[2] if len(d) > 2 else 3.4
        m = place(xb, 0, 0, rz=math.pi / 2)
        dcy = (door_y or {}).get(side, door_cy)
        layers = ((0.0, 0.14, ext), (0.14, WALL, wall)) if side == "R" else ((0.0, WALL - 0.14, wall), (WALL - 0.14, WALL, ext))
        bands = [(bottom, floors[0])] + [(zf, (floors[i + 1] if i + 1 < len(floors) else zt)) for i, zf in enumerate(floors)]
        for z_lo, z_hi in bands:
            if z_hi - z_lo < 1e-3:
                continue
            dh = doors.get(round(z_lo, 2))
            if dh and z_hi - z_lo > 2.0:
                door_at[(side, round(z_lo, 2))] = dcy
                kind, rise, spring = fit_arch(st["front"] if st["front"] != "cusp" else "round", 2.8, min(z_hi - z_lo - FLOOR, dh + 0.8), 0.3, 1.5)
                for la, lb, key in layers:
                    g.use(key)
                    K.arcade(g, yf, yb, z_lo, z_hi, la, lb, [(dcy, 2.8, z_lo + spring, kind, rise, None)], m=m)
                g.use(trim)
                for off in (-0.03, WALL + 0.03):
                    K.arch_trim(g, dcy, 2.8, z_lo + spring, z_lo, kind, rise, y=off, r=0.09, m=m)
            else:
                for la, lb, key in layers:
                    g.use(key)
                    g.box(yf, yb, la, lb, z_lo, z_hi, m=m)
    g.use(wall)
    g.box(x0 + WALL, x1 - WALL, yb - WALL, yb - 0.14, bottom, zt)
    g.use(ext)
    g.box(x0 + WALL, x1 - WALL, yb - 0.14, yb, bottom, zt)
    width = x1 - x0 - 2 * WALL
    nb = max(1, int(round(width / st["bay"])))
    bw = width / nb
    bay_x = [x0 + WALL + bw * (k + 0.5) for k in range(nb)]
    edge_x = [x0 + WALL + bw * k for k in range(nb + 1)]
    cell_at = {}
    for ci, ma, mb in cells:
        ka = int(round((X(ma) - (x0 + WALL)) / bw))
        kb = int(round((X(mb) - (x0 + WALL)) / bw))
        ka, kb = max(0, min(nb, ka)), max(0, min(nb, kb))
        if kb > ka:
            cell_at.setdefault(ci, []).append((edge_x[ka], edge_x[kb]))

    def in_cell(i, x, pad=0.0):
        return any(a - pad < x < b + pad for a, b in cell_at.get(i, ()))

    if rear:                                             # exterior dressing of the back and side faces (C)
        g.use(trim)
        for zf in floors + [zt + FLOOR]:
            g.tube([(x0 - 0.05, yb + 0.06, zf - 0.2), (x1 + 0.05, yb + 0.06, zf - 0.2)], 0.12, segs=6)
            for xs in (x0 - 0.06, x1 + 0.06):
                if ("L" if xs < x0 else "R") not in side_open:
                    g.tube([(xs, yf, zf - 0.2), (xs, yb, zf - 0.2)], 0.12, segs=6)
        g.use(ext)
        ns = max(1, int(round((yb - yf) / st["bay"])))
        side_y = [yf + (yb - yf) * (k + 0.5) / ns for k in range(ns)]
        if "N" in ext_faces:
            for xe in edge_x:
                g.box(xe - 0.28, xe + 0.28, yb, yb + 0.32, bottom, zt)
            for k, xe in enumerate(edge_x):                  # buttresses on every other pilaster, with spear finials (C)
                if k % 2:
                    continue
                g.use(ext)
                g.prism([(0.0, bottom), (1.0, bottom), (1.0, zt - 3.0), (0.35, zt - 0.8), (0.0, zt - 0.8)], -0.36, 0.36, m=place(xe, yb, 0, rz=math.pi / 2))
                g.use("iron")
                g.spike((xe, yb + 0.55, zt - 2.0), (xe, yb + 0.55, zt + 0.9), 0.1, segs=6, bulb=1.0)
                g.use(ext)
            for zf in floors + [zt + FLOOR]:
                if base is not None and zf == floors[0]:
                    continue                             # it would hang into the building below
                SH.hanging_fringe(g, x0 + 0.2, x1 - 0.2, yb + 0.42, zf - 0.32, 0.75, seed=int(zf * 7) % 97, key="fringe")
            g.use(ext)
        for side, xs0, xs1 in (("L", x0 - 0.32, x0), ("R", x1, x1 + 0.32)):
            if side in side_open or side not in ext_faces:
                continue
            for k in range(ns + 1):
                ye = yf + (yb - yf) * k / ns
                g.box(xs0, xs1, ye - 0.28, ye + 0.28, bottom, zt)
        # windows on the outer faces (C): the same lancets as inside, so the building glows on every side
        for i, zf, top in storeys:
            hgt = top - zf
            w, h = min(1.6, st["bay"] * 0.4), min(hgt * 0.6, 4.2)
            if h < 1.6:
                continue
            win = kit_window(S, "lancet", w, h, st["glass"])
            sill = min(1.0, hgt * 0.16)
            for side, px, rz in (("L", x0 - 0.12, -math.pi / 2), ("R", x1 + 0.12, math.pi / 2)):
                if side in side_open or side not in ext_faces:
                    continue
                dy = door_at.get((side, round(zf, 2)))
                for k, yy in enumerate(side_y):
                    if dy is not None and abs(yy - dy) < 2.4:
                        continue
                    S.put(win, f"{name}_XWin{side}_{i}_{k:02d}", rid, "WindowLancet", place(px, yy, zf + sill, rz=rz), "C", ref, note="exterior window: completion")
            if "N" in ext_faces:
                for k, cx in enumerate(bay_x):
                    if (k + i) % 2 == 0:
                        S.put(win, f"{name}_XWinN_{i}_{k:02d}", rid, "WindowLancet", place(cx, yb + 0.12, zf + sill, rz=math.pi), "C", ref, note="exterior window: completion")
    # transverse partition arches (one opening per ~11 units of depth) and, in deep buildings, a longitudinal arcade
    part = st.get("partition", 0)
    depth = (yb - WALL) - (yf + 0.4)
    pkind = "pointed" if st["front"] == "pointed" else "round"
    if part:
        n_open = max(1, int(math.ceil(depth / 11.0)))
        ow = depth / n_open
        for i, zf, top in storeys:
            for k in range(part, nb, part):
                xp = edge_x[k]
                if any(a - 0.4 < xp < b + 0.4 for a, b, lo, hi in voids if lo <= zf + 1 <= hi):
                    continue
                if any(a + 0.1 < xp < b - 0.1 for a, b in cell_at.get(i, ())):
                    continue
                kind, rise, spring = fit_arch(pkind, ow - 1.0, top - zf, 0.35, 1.6)
                g.use(wall)
                K.arcade(g, yf + 0.4, yb - WALL, zf, top, 0.0, 0.34,
                         [(yf + 0.4 + ow * (j + 0.5), ow - 1.0, zf + spring, kind, rise, None) for j in range(n_open)],
                         m=place(xp + 0.17, 0, 0, rz=math.pi / 2))
    inner_rows = []
    if st.get("inner", depth > 16.0):
        n_rows = 1 if depth < 26 else 2
        inner_rows = [yf + 0.4 + depth * (r + 1) / (n_rows + 1) for r in range(n_rows)]
        for i, zf, top in storeys:
            if top - zf < 2.6:
                continue
            aw = bw - 0.4
            kind, rise, spring = fit_arch(pkind, aw, top - zf, 0.3, 1.8)
            for yy in inner_rows:
                g.use(wall)
                ops = [(cx, aw, zf + spring, kind, rise, None) for cx in bay_x]
                gaps = [(edge_x[max(0, min(nb, int((fa - x0 - WALL) / bw + 0.5)))], edge_x[max(0, min(nb, int((fb - x0 - WALL) / bw + 0.5)))])
                        for fa, fb in full_at(zf, top)] + list(cell_at.get(i, ()))     # double-height rooms and solid cells stay clear
                for sa, sb in split_interval(x0 + WALL, x1 - WALL, gaps):
                    if sb - sa < 1.0:
                        continue
                    K.arcade(g, sa, sb, zf + spring - 0.02, top, yy - 0.17, yy + 0.17, [(cx, aw, zf + spring, kind, rise, zf + spring - 0.02) for cx in bay_x if sa < cx < sb])
                col = kit_column(S, spring, 0.13, trim)
                for k, xe in enumerate(edge_x[1:-1]):
                    if any(a - 0.5 < xe < b + 0.5 and sy0 - 0.5 < yy < sy1 + 0.5 for a, b, lo, hi in voids if lo <= zf + 1 <= hi):
                        continue
                    if any(ga + 0.1 < xe < gb - 0.1 for ga, gb in gaps):
                        continue
                    S.put(col, f"{name}_ICol_{i}_{int(yy * 10)}_{k:02d}", rid, "Column", place(xe, yy, zf), C, ref)
    wo = S.add(g, name + "_Walls", rid, name, ev, ref, note=note)
    rooms = []                                           # interior volumes per storey, for the room intrusion check (qa/check_rooms.py)
    for i, zf, top in storeys:
        for a, b in split_interval(x0 + WALL, x1 - WALL, list(cell_at.get(i, ()))):
            rooms.append([round(v, 3) for v in (a, b, yf + 0.4, yb - WALL, zf, top)])
    if wo is not None:
        wo["cot_rooms"] = json.dumps(rooms)
    ceil = st.get("ceiling")
    if ceil:                                             # ribs or beams under each ceiling, so the rooms are not roofed by a flat plane (C)
        g = Geo().use(trim)
        for i, zf, top in storeys:
            hgt = top - zf
            if hgt < 2.8:
                continue
            rho = min(1.1, 0.16 * hgt) if ceil == "ribs" else 0.25
            ym = (yf + 0.4 + yb - WALL) / 2
            open_x = []
            for xe in edge_x[1:-1]:
                if in_cell(i, xe, 0.3) or any(a - 0.4 < xe < b + 0.4 for a, b, lo, hi in voids if lo <= zf + 1 <= hi):
                    continue
                open_x.append(xe)
                if ceil == "ribs":
                    path = [(xe, lerp(yf + 0.4, yb - WALL, t), top - 0.06 - rho * (1 - math.sin(math.pi * t)) ** 1.4) for t in [j / 10 for j in range(11)]]
                    g.tube(path, 0.11, segs=6, ref=(1, 0, 0))
                else:
                    g.box(xe - 0.14, xe + 0.14, yf + 0.4, yb - WALL, top - 0.32, top)
            gaps = list(cell_at.get(i, ())) + [(a - 0.3, b + 0.3) for a, b, lo, hi in voids if lo <= zf + 1 <= hi]
            for sa, sb in split_interval(x0 + WALL, x1 - WALL, gaps):
                if sb - sa < 1.0:
                    continue
                if ceil == "ribs":
                    g.tube([(sa, ym, top - 0.08), (sb, ym, top - 0.08)], 0.09, segs=6)
                    for xe in open_x:
                        if sa < xe < sb:
                            g.ellipsoid((xe, ym, top - 0.14), (0.2, 0.2, 0.16), segs=8, steps=5)
                else:
                    g.box(sa, sb, ym - 0.12, ym + 0.12, top - 0.26, top)
        S.add(g, name + "_Ceiling", rid, "CeilingRibs", C, ref, note="ribs or beams under the ceilings: completion")
    if cell_at:
        g = Geo()
        for i, zf, top in storeys:
            for a, b in cell_at.get(i, ()):
                g.use("mass_black")
                shafts = [(max(a, va), min(b, vb)) for va, vb, lo, hi in voids if lo <= zf + 1 <= hi and va < b and vb > a]
                for sa, sb in split_interval(a, b, shafts):          # full depth outside the lift shafts (1 cm off floor and ceiling)
                    g.box(sa, sb, yf + 0.42, yb - WALL, zf + 0.01, top - 0.01)
                for sa, sb in shafts:                                  # around a shaft the mass stops at the shaft walls
                    g.box(sa, sb, yf + 0.42, sy0 - 0.35, zf + 0.01, top - 0.01)
                    g.box(sa, sb, sy1 + 0.35, yb - WALL, zf, top)
                if not (i == 0 and base is not None):              # the lowest storey of a stack standing on another: the room below is not ours
                    SH.hanging_fringe(g, a + 0.1, b - 0.1, yf + 0.6, zf - FLOOR, 1.6, seed=i * 13 + int(a), key="fringe")
        S.add(g, name + "_SolidCells", rid, "SolidMass", "B", ref,
              note="black parts of the storey on the master: solid building mass (what is inside is unknown); fringe hangs under it into the room below")

    # ---- hanging fringe under the ceilings (A: nearly every interior reference)
    if st.get("fringe"):
        g = Geo()
        for i, zf, top in storeys:
            drop = min(1.5, (top - zf) * 0.2)
            open_top = [(fa, fb) for fa, fb in full_at(zf, top) if any(lo <= top + FLOOR <= hi for a_, b_, lo, hi in voids if (a_, b_) == (fa, fb))]
            for k, (sa, sb) in enumerate(split_interval(x0 + WALL + 0.2, x1 - WALL - 0.2, open_top)):
                if sb - sa < 1.0:
                    continue
                SH.hanging_fringe(g, sa, sb, yb - WALL - 0.45, top, drop, seed=i * 7 + 1 + k * 13, key=st.get("fringe_key", "curtain"))
                SH.hanging_fringe(g, sa, sb, yf + 0.9, top, drop * 0.7, seed=i * 7 + 3 + k * 13, key=st.get("fringe_key", "curtain"))
        S.add(g, name + "_Fringe", rid, "CeilingFringe", ev, ref)

    # ---- viewer-side facade (FRONT layer): pier arcade per storey with engaged columns, or a solid wall
    if front == "solid":
        g = Geo().use(ext)
        g.box(x0 + WALL, x1 - WALL, yf, yf + WALL, bottom, zt)
        if "S" in ext_faces:                              # pilasters and lancets on the viewer-side wall as on the other faces
            for xe in edge_x:
                g.box(xe - 0.28, xe + 0.28, yf - 0.32, yf, bottom, zt)
            for i, zf, top in storeys:
                hgt = top - zf
                w, h = min(1.6, st["bay"] * 0.4), min(hgt * 0.6, 4.2)
                if h < 1.6:
                    continue
                win = kit_window(S, "lancet", w, h, st["glass"])
                for k, cx in enumerate(bay_x):
                    S.put(win, f"{name}_XWinS_{i}_{k:02d}", rid, "WindowLancet", place(cx, yf - 0.12, zf + min(1.0, hgt * 0.16)), "C", ref, note="exterior window: completion", layer="FRONT")
        S.add(g, name + "_Front", rid, name, C, ref, note="viewer-side wall", layer="FRONT")
    elif front:
        g = Geo()
        gr = Geo()
        for i, zf, top in storeys:
            ov = (levels or {}).get(i, {})
            fkind = ov.get("front", st["front"])
            if fkind is None:
                continue
            aw = bw - 0.5
            kind, rise, spring = fit_arch(fkind, aw, top - zf, 0.4, 1.7)
            g.use(wall)
            open_x = [cx for cx in bay_x if not in_cell(i, cx)]
            K.arcade(g, x0 + WALL, x1 - WALL, zf, top, yf, yf + 0.4, [(cx, aw, zf + spring, kind, rise, None) for cx in open_x])
            g.use(trim)
            for cx in open_x:
                K.arch_trim(g, cx, aw, zf + spring, zf + spring, kind, rise, y=yf - 0.03, r=0.075)
            col = kit_column(S, spring, 0.13, trim)
            for k, xe in enumerate(edge_x):
                S.put(col, f"{name}_FCol_{i}_{k:02d}", rid, "Column", place(xe, yf - 0.1, zf), C, ref, layer="FRONT")
            if (front_rail if front_rail is not None else st.get("rail")) and i > 0:
                for k, cx in enumerate(bay_x):
                    if (i, k) in rail_skip or in_cell(i, cx):   # an entrance from a balcony outside / a solid cell
                        continue
                    K.spike_rail(gr, (cx - aw / 2 + 0.08, yf + 0.2), (cx + aw / 2 - 0.08, yf + 0.2), zf, h=0.9)
        S.add(g, name + "_Front", rid, name, C, ref, note="viewer-side facade: arcade form is completion", layer="FRONT")
        S.add(gr, name + "_FrontRail", rid, "SpikeRail", C, ref, layer="FRONT")

    # ---- back-wall bays, pilasters, lamps
    if decor:
        yw = yb - WALL - 0.12
        for i, zf, top in storeys:
            hgt = top - zf
            ov = (levels or {}).get(i, {})
            kinds = ov.get("back", st["back"])
            glass = ov.get("glass", st["glass"])
            pil = kit_column(S, hgt, 0.12, trim)
            for k, xe in enumerate(edge_x):
                if in_cell(i, xe, -0.1):
                    continue
                S.put(pil, f"{name}_Pil_{i}_{k:02d}", rid, "Column", place(xe, yb - WALL - 0.1, zf), C, ref)
            for k, cx in enumerate(bay_x):
                if any(a - 0.3 < cx < b + 0.3 for a, b, lo, hi in voids if lo <= zf + 1 <= hi):
                    continue
                if skip_bays and (i, k) in skip_bays:
                    continue
                if in_cell(i, cx):
                    continue
                kind = kinds[(k + i) % len(kinds)]
                bay_decor(S, rid, f"{name}_B{i}_{k:02d}", kind, cx, yw, zf, bw, hgt, glass, trim, ev, ref, seed=i * 31 + k)
            if st.get("side_portraits") and hgt > 3.2 and (yb - yf) > 8.0:
                for side, px, rz in (("L", x0 + WALL + 0.06, math.pi / 2), ("R", x1 - WALL - 0.06, -math.pi / 2)):
                    if side in side_open or in_cell(i, px + (1.0 if side == "L" else -1.0)):
                        continue
                    if any(a - 1.2 < px < b + 1.2 for a, b, lo, hi in voids if lo <= zf + 1 <= hi):
                        continue
                    dy = door_at.get((side, round(zf, 2)))
                    for j, f in enumerate((0.45, 0.75)):
                        py = lerp(yf + 0.6, yb - WALL, f)
                        if dy is not None and abs(py - dy) < 2.6:
                            continue
                        v = (i * 3 + j + (side == "R")) % 4
                        if hgt > 7.0:                    # high room: a larger portrait, hung higher (D-361)
                            S.put(S.kit(f"noble_{v}_M", lambda v=v: FU.k_noble_portrait(v, 1.4, 2.0)), f"{name}_SideNoble_{side}_{i}_{j}", rid, "NoblePortrait",
                                  place(px, py, zf + min(hgt * 0.36, 2.8), rz=rz), C, ref, note="portrait on the side wall: completion")
                        else:
                            S.put(S.kit(f"noble_{v}", lambda v=v: FU.k_noble_portrait(v)), f"{name}_SideNoble_{side}_{i}_{j}", rid, "NoblePortrait",
                                  place(px, py, zf + min(hgt * 0.42, 1.9), rz=rz), C, ref, note="portrait on the side wall: completion")
            lk = ov.get("lamp", st.get("lamp")) if lamps else None
            if lk and hgt > 2.6:
                ym = (yf + yb - WALL) / 2
                for k, cx in enumerate(bay_x):
                    if any(a - 0.6 < cx < b + 0.6 for a, b, lo, hi in voids if lo <= zf + 1 <= hi):
                        continue
                    if in_cell(i, cx):
                        continue
                    if lk == "string" and k % 2 == (i % 2):
                        ln = q(min(1.9, hgt * 0.3), 0.1)
                        S.put(S.kit(f"lampstring_{ln:.1f}", lambda ln=ln: K.k_lamp_string(2, ln)), f"{name}_Lamp_{i}_{k:02d}", rid, "LampString",
                              place(cx, ym, top), ev, ref)
                    elif lk == "round" and k % 2 == (i % 2):
                        S.put(S.kit("walllamp_pink", lambda: K.k_wall_lamp("lamp_pink")), f"{name}_Lamp_{i}_{k:02d}", rid, "WallLamp",
                              place(cx - bw / 2 + 0.3, yw, zf + min(hgt * 0.7, 2.8)), ev, ref)
                    elif lk == "orb" and k % 3 == (i % 3):
                        S.put(S.kit("orbpost_3", lambda: K.k_orb_post(min(3.4, 3.4), 3)), f"{name}_Lamp_{i}_{k:02d}", rid, "OrbPost",
                              place(cx - bw / 2 + 0.6, ym + 1.5, zf), ev, ref)
    occ = []
    fset = st.get("furniture")

    def storey_z(i):
        return next(zf for j, zf, top in storeys if j == i)

    def shaft_at(i, x, pad):
        return any(a - pad < x < b + pad for a, b, lo, hi in voids if lo <= storey_z(i) + 1 <= hi)

    if (furnish if furnish is not None else (decor and fset)) and fset:
        def blocked(i, cx):
            if in_cell(i, cx, 0.2) or shaft_at(i, cx, bw / 2):
                return True
            k = min(range(len(bay_x)), key=lambda j: abs(bay_x[j] - cx))
            return (i, k) in furn_skip or bool(skip_bays and (i, k) in skip_bays)

        door_bays = {}
        for (side, zr), dcy in door_at.items():
            for i, zf, top in storeys:
                if abs(zf - zr) < 0.05:
                    door_bays.setdefault(i, set()).add(0 if side == "L" else len(bay_x) - 1)
        window_bays = {}
        if decor:
            for i, zf, top in storeys:
                kinds = (levels or {}).get(i, {}).get("back", st["back"])
                for k in range(len(bay_x)):
                    window_bays[(i, k)] = decor_clear(kinds[(k + i) % len(kinds)], top - zf)
        lamp_clear = []                                  # standing orb lamps stay clear
        for i, zf, top in storeys:
            if ((levels or {}).get(i, {}).get("lamp", st.get("lamp")) if lamps else None) == "orb" and top - zf > 2.6:
                ym = (yf + yb - WALL) / 2
                for k, cx in enumerate(bay_x):
                    if k % 3 == (i % 3):
                        lamp_clear.append((i, cx - bw / 2 + 0.15, cx - bw / 2 + 1.05, ym + 1.05, ym + 1.95))
        keep_clear = list(keep_clear) + lamp_clear
        occ = FU.furnish_storeys(S, rid, name, fset, storeys, bay_x, bw, x0, x1, yf, yb, WALL, blocked, door_bays, inner_rows,
                                 seed=sum(ord(c) for c in name), ev=ev, ref=ref, window_bays=window_bays, clear=keep_clear)

        def side_ok(i, side, y, half):
            zf_i = storey_z(i)
            if side in side_open:
                return False
            px = x0 + WALL + 1.0 if side == "L" else x1 - WALL - 1.0
            if in_cell(i, px) or any(a - 1.5 < px < b + 1.5 for a, b, lo, hi in voids if lo <= zf_i + 1 <= hi):
                return False
            dy = door_at.get((side, round(zf_i, 2)))
            if dy is not None and abs(y - dy) < 1.4 + half + 0.4:
                return False
            if any(abs(y - r) < half + 0.5 for r in inner_rows):
                return False
            return not any(j == i and a < px + 0.6 and b > px - 0.6 and c < y + half and d > y - half for j, a, b, c, d in occ)
        occ += FU.side_cases(S, rid, name, fset, storeys, x0, x1, yf, yb, WALL, side_ok, ref)
    else:
        occ = list(keep_clear)

    def free(i, x, y, r):
        """True when a creature of footprint radius r can stand at (x, y) on storey i."""
        if not (x0 + WALL + r < x < x1 - WALL - r and yf + 0.5 + r < y < yb - WALL - r):
            return False
        if in_cell(i, x, r) or shaft_at(i, x, r + 0.3):
            return False
        for yy in inner_rows:                            # inner arcades: keep off the whole row
            if abs(y - yy) < r + 0.3:
                return False
        if part:                                         # transverse partition arches
            for k in range(part, nb, part):
                if abs(x - edge_x[k]) < r + 0.3:
                    return False
        for j, a, b, c, d in occ:
            if j == i and a - r < x < b + r and c - r < y < d + r:
                return False
        return True

    room = dict(storeys=[t for t in storeys if t[2] - t[1] > 2.2], free=free, occ=occ, x0=x0 + WALL, x1=x1 - WALL, yf=yf + 0.5, yb=yb - WALL)
    return dict(x0=x0, x1=x1, zt=zt, zb=zb, yf=yf, yb=yb, floors=floors, storeys=storeys, bay_x=bay_x, edge_x=edge_x, bw=bw, bottom=bottom, cells=cell_at,
                room=room, base=base)


def decor_clear(kind, hgt):
    """(height limit, stand-off from the wall) for furniture in front of a back-wall bay of this kind (mirrors bay_decor)."""
    if kind in ("lancet", "web"):
        return (min(1.0, hgt * 0.16) - 0.12, 0.32) if min(hgt * 0.62, 4.6) >= 1.6 else (99.0, 0.0)
    if kind == "tall":
        return (hgt * 0.06 - 0.12, 0.32) if hgt * 0.8 >= 2.0 else (99.0, 0.0)
    if kind == "oval":
        h = min(hgt * 0.6, 3.6)
        return ((hgt - h) * 0.45 - 0.12, 0.32) if h >= 1.6 else (99.0, 0.0)
    if kind in ("shelf", "shelf_pale", "drape", "jars"):
        return (0.0, 0.0)
    if kind in ("portrait", "noble"):
        if hgt < 2.5:
            return (99.0, 0.0)
        base = min(hgt * 0.24, 2.4) if (kind == "noble" and hgt > 8.0) else (min(hgt * 0.3, 2.0) if (kind == "noble" and hgt > 5.0) else min(hgt * 0.45, 1.9, hgt - 1.8))
        return (base - 0.12, 0.3)
    if kind in ("quilt", "chevron", "lotus", "blind"):
        return (99.0, 0.5)
    return (99.0, 0.0)


def bay_decor(S, rid, name, kind, cx, yw, zf, bw, hgt, glass, trim, ev, ref, seed=0):
    """One back-wall bay. yw is the plane just in front of the wall face."""
    if kind in ("lancet", "web"):
        w, h = min(bw * 0.44, 1.8), min(hgt * 0.62, 4.6)
        if h < 1.6:
            return
        S.put(kit_window(S, kind, w, h, glass), name, rid, "Window" + kind.title(), place(cx, yw, zf + min(1.0, hgt * 0.16)), ev, ref)
    elif kind == "tall":
        w, h = min(bw * 0.5, 2.2), hgt * 0.8
        if h < 2.0:
            return
        S.put(kit_window(S, "tall", w, h, glass), name, rid, "WindowTall", place(cx, yw, zf + hgt * 0.06), ev, ref)
    elif kind == "oval":
        w, h = min(bw * 0.42, 1.8), min(hgt * 0.6, 3.6)
        if h < 1.6:
            return
        S.put(kit_window(S, "oval", w, h, glass), name, rid, "OvalMirror", place(cx, yw, zf + (hgt - h) * 0.45), ev, ref)
    elif kind in ("shelf", "shelf_pale"):
        w, h = q(min(bw * 0.62, 2.6), 0.1), q(min(hgt * 0.62, 3.3), 0.1)
        if h < 1.5:
            return
        fr = "trim_purple" if kind == "shelf" else "trim_pale"
        v = seed % 3
        S.put(S.kit(f"shelf_{w:.1f}_{h:.1f}_{fr}_{v}", lambda: K.k_shelf_arch(w, h, seed=v, frame=fr)), name, rid, "ShelfArch", place(cx, yw - 0.06, zf), ev, ref)
    elif kind == "quilt":                                  # padded wall panel (A: purple pads on master C4)
        g = Geo()
        K.pattern_relief(g, cx - bw * 0.42, cx + bw * 0.42, zf + 0.35, zf + hgt - 0.45, yw, cell=0.85, key="pattern", depth=0.07, kind="diamond")
        S.add(g, name, rid, "QuiltedWall", ev, ref)
    elif kind in ("portrait", "noble"):
        if hgt < 2.5:
            return
        v = seed % 4
        if kind == "noble" and hgt > 8.0:                # very high wall: a large portrait over two mid-sized ones (D-361)
            big = S.kit(f"noble_{v}_XL", lambda: FU.k_noble_portrait(v, 2.3, 3.3))
            S.put(big, name, rid, "NoblePortrait", place(cx, yw, zf + min(hgt * 0.32, 3.4)), ev, ref)
            small = S.kit(f"noble_{(v + 1) % 4}_M", lambda: FU.k_noble_portrait((v + 1) % 4, 1.4, 2.0))
            dx = max(bw * 0.33, 2.05)
            if dx + 0.85 < bw / 2:
                for j, sgn in enumerate((-1, 1)):
                    S.put(small, f"{name}_s{j}", rid, "NoblePortrait", place(cx + sgn * dx, yw, zf + min(hgt * 0.24, 2.4)), ev, ref)
        elif kind == "noble" and hgt > 5.0:              # a large portrait between two small ones
            big = S.kit(f"noble_{v}_L", lambda: FU.k_noble_portrait(v, 1.6, 2.3))
            S.put(big, name, rid, "NoblePortrait", place(cx, yw, zf + min(hgt * 0.3, 2.0)), ev, ref)
            small = S.kit(f"noble_{(v + 1) % 4}", lambda: FU.k_noble_portrait((v + 1) % 4))
            dx = max(bw * 0.32, 1.5)                     # clear of the large frame (half width 0.85) and of the pilasters
            if dx + 0.68 < bw / 2:
                for j, sgn in enumerate((-1, 1)):
                    S.put(small, f"{name}_s{j}", rid, "NoblePortrait", place(cx + sgn * dx, yw, zf + min(hgt * 0.38, 2.3)), ev, ref)
        else:
            S.put(S.kit(f"noble_{v}", lambda: FU.k_noble_portrait(v)), name, rid, "NoblePortrait", place(cx, yw, zf + min(hgt * 0.45, 1.9, hgt - 1.8)), ev, ref)
    elif kind == "drape":
        g = Geo()
        K.drape(g, cx - bw * 0.36, cx + bw * 0.36, yw - 0.1, zf + hgt - 0.25, zf + 0.25, folds=5, amp=0.12, key="cloth_purple",
                gather=(zf + hgt * 0.45, 0.5), seed=seed)
        S.add(g, name, rid, "Drape", ev, ref)
    elif kind == "chevron":                               # herringbone wall bay (A: 01_Soul_Sanctuary core / middle1)
        g = Geo()
        K.chevron_panel(g, cx - bw * 0.4, cx + bw * 0.4, yw + 0.02, zf + 0.3, zf + hgt - 0.5, pitch=0.8, key=trim)
        S.add(g, name, rid, "ChevronBay", ev, ref)
    elif kind == "lotus":                                 # repeating lotus motif wall (A: 01_Soul_Sanctuary core, bottom)
        g = Geo()
        K.pattern_relief(g, cx - bw * 0.42, cx + bw * 0.42, zf + 0.4, zf + hgt - 0.5, yw + 0.1, cell=1.0, key="pattern_blue", kind="damask")
        S.add(g, name, rid, "LotusPattern", ev, ref, note="pattern panel is separate from the wall")
    elif kind == "blind":
        w = min(bw * 0.6, 2.6)
        kind2, rise, spring = fit_arch("round", w, hgt, 0.5, 1.2)
        g = Geo().use(trim)
        K.arch_trim(g, cx, w, zf + spring, zf, kind2, rise, y=yw + 0.06, r=0.1)
        S.add(g, name, rid, "BlindArch", "C" if ev == "A" else ev, ref)
    elif kind == "jars":
        g = Geo().use(trim)
        n = max(1, int((hgt - 0.6) / 1.5))
        jar = S.kit("jar_glass", lambda: jar_glass())
        for r in range(n):
            z = zf + 0.9 + 1.5 * r
            if r > 0:
                g.box(cx - bw * 0.4, cx + bw * 0.4, yw - 0.5, yw + 0.1, z - 0.08, z)
            for j in range(3):
                S.put(jar, f"{name}_{r}_{j}", rid, "GlassJar", place(cx + (j - 1) * bw * 0.26, yw - 0.26, z if r > 0 else zf), ev, ref)
        S.add(g, name, rid, "JarShelf", ev, ref)
    # "niche": left plain


def jar_glass():
    """Glass specimen jar (A: master C4 shows rows of jar-like vessels; form is completion)."""
    g = Geo()
    g.use("jar_glass")
    g.revolve([(0.22, 0.05), (0.3, 0.14), (0.3, 0.86), (0.2, 1.0)], segs=12)
    g.use("trim_purple")
    g.revolve([(0.26, 0.0), (0.27, 0.06), (0.22, 0.08)], segs=12)
    g.revolve([(0.2, 1.0), (0.24, 1.04), (0.2, 1.1), (0.06, 1.16), (0.02, 1.26)], segs=12)
    return g


# ---------------------------------------------------------------------------- lifts
def lift(S, rid, e, name=None, y=None, car="spire", closed=None, ev=None, ref=None, trim="trim", stops=(), chain_to=None, front=True,
         back="chevron", panels=()):
    """Lift shaft from a layout 'shaft' element: herringbone (or plain) back, slot panels, guide posts, optional
    enclosing walls, car and chain. panels: z of slot panels (A: 11_Lower_City middle / bottom)."""
    name = name or e["id"]
    ev = ev or e.get("ev", "A")
    ref = ref if ref is not None else e.get("ref", "")
    x0, x1 = X(e["map"][0]), X(e["map"][2])
    zt, zb = Z(e["map"][1]), Z(e["map"][3])
    yf, yb = y if y is not None else e.get("y", D["shaft_y"])
    closed = (not e.get("open", False)) if closed is None else closed
    g = Geo()
    if back == "chevron":
        K.chevron_panel(g, x0 + 0.2, x1 - 0.2, yb - 0.16, zb, zt, key=trim)
    else:
        g.use("wall_deep")
        g.box(x0 + 0.2, x1 - 0.2, yb - 0.16, yb - 0.02, zb, zt)
    for zp in panels:
        SH.slot_panel(g, (x0 + x1) / 2, yb - 0.3, zp, w=(x1 - x0) - 0.5, h=2.3, key=trim)
    g.use(trim)
    t = 0.26
    for px in (x0, x1 - t):
        for py in ((yf, yb - t) if not closed else (yf,)):
            g.box(px, px + t, py, py + t, zb, zt)
            z = zb + 1.5
            while z < zt - 0.5:
                g.box(px - 0.06, px + t + 0.06, py - 0.06, py + t + 0.06, z, z + 0.22)
                z += 3.2
    if closed:
        g.use("wall_deep")
        g.box(x0, x0 + t, yf + t, yb, zb, zt)
        g.box(x1 - t, x1, yf + t, yb, zb, zt)
    S.add(g, name + "_Shaft", rid, name, ev, ref)
    if closed and front:
        g = Geo().use("wall_deep")
        ops = sorted(set([zb] + [s for s in stops]))
        cur = zb
        cx, w = (x0 + x1) / 2, (x1 - x0) - 2 * t - 0.3
        for zs in ops:                                    # an arched doorway at each stop
            if zs - cur > 0.05:
                g.box(x0 + t, x1 - t, yf, yf + t, cur, zs)
            top = min(zt, zs + 4.6)
            if top - zs > 3.4:
                K.arcade(g, x0 + t, x1 - t, zs, top, yf, yf + t, [(cx, w, zs + 2.4, "pointed", min(1.6, top - zs - 2.7), None)])
            elif top - zs > 0.05:
                g.box(x0 + t, x1 - t, yf, yf + t, zs, top)
            cur = top
        if zt - cur > 0.05:
            g.box(x0 + t, x1 - t, yf, yf + t, cur, zt)
        S.add(g, name + "_ShaftFront", rid, name, "C", ref, note="enclosing front wall is completion", layer="FRONT")
    if "car" in e and car:
        zc = Z(e["car"])
        cxm, cym = (x0 + x1) / 2, (yf + yb) / 2
        width = min(2.3, (x1 - x0) - 0.7)
        if car == "dome":
            S.put(S.kit("car_dome", lambda: K.k_car_dome()), name + "_Car", rid, "LiftCarDome", place(cxm, cym, zc), ev, ref)
            top = zc + K.CAR_DOME_TOP
        else:
            s = width / 2.1
            S.put(S.kit("car_spire", lambda: K.k_car_spire()), name + "_Car", rid, "LiftCarSpire", place(cxm, cym, zc, s=s), ev, ref)
            top = zc + K.CAR_SPIRE_TOP * s
        zc_top = chain_to if chain_to is not None else zt
        if zc_top - top > 0.5:
            g = Geo()
            K.chain(g, cxm, cym, top - 0.1, zc_top)
            S.add(g, name + "_Chain", rid, "LiftChain", ev, ref)
    return dict(x0=x0, x1=x1, zt=zt, zb=zb, yf=yf, yb=yb)


# ---------------------------------------------------------------------------- bridges and arcades
def under_arcade(g, x0, x1, y0, y1, z_top, z_bot, bays, key="stone", trim="trim", pendants=True, faces=0.45):
    """Row of round arches hanging under a deck, with a pendant spike at each pier (A: 04_Bridges, 11_Lower_City upperbridge)."""
    width = (x1 - x0) / bays
    aw = width - 0.5
    hw = aw / 2
    kind, rise, spring = ("round", hw, 0.0)
    drop = z_top - z_bot
    if hw > drop - 0.3:
        kind, rise = "flat", drop - 0.3
    for yy0, yy1 in ((y0, y0 + faces), (y1 - faces, y1)):
        g.use(key)
        K.arcade(g, x0, x1, z_bot, z_top, yy0, yy1, [(x0 + width * (k + 0.5), aw, z_bot + 0.02, kind, rise, None) for k in range(bays)])
    g.use(trim)
    for yy in (y0 - 0.03, y1 + 0.03):
        for k in range(bays):
            cx = x0 + width * (k + 0.5)
            g.tube([(cx + px, yy, z_bot + 0.02 + pz) for px, pz in K.arch_profile(aw, kind, rise)], 0.08, segs=5, ref=(0, 1, 0))
    if pendants:
        g.use("iron")
        for k in range(bays + 1):
            xe = x0 + width * k
            for yy in (y0 + faces / 2, y1 - faces / 2):
                g.spike((xe, yy, z_bot + 0.05), (xe, yy, z_bot - 0.9), 0.1, segs=6, bulb=1.2)
    g.use(key)
    for k in range(bays + 1):                             # cross ribs so the underside is not a flat soffit
        xe = x0 + width * k
        g.box(xe - 0.25, xe + 0.25, y0 + faces, y1 - faces, z_bot, z_top)


def stairs(g, x0, x1, y0, y1, z0, z1, step=0.5, key="stone", solid=True):
    """Flight of steps rising from (x0, z0) to (x1, z1) along X."""
    g.use(key)
    n = max(1, int(round(abs(z1 - z0) / step)))
    for i in range(n):
        xa = lerp(x0, x1, i / n)
        xb = lerp(x0, x1, (i + 1) / n)
        zt = lerp(z0, z1, (i + 1) / n)
        g.box(xa, xb, y0, y1, (min(z0, z1) if solid else zt - step * 1.2), zt)


# ---------------------------------------------------------------------------- organic fields, iron frames, piers
def pad_field(S, rid, name, a0, a1, b0, b1, c, count, seed=0, facing="front", size=(1.0, 2.2), ev="A", ref="", layer=None, keep=None, jitter=0.5, note=""):
    """Spotted pads covering a surface. facing: front (wall at y=c, grows toward -Y; a = x, b = z), back (toward +Y),
    down (ceiling at z=c; a = x, b = y), up (floor at z=c), east (wall at x=c facing +X; a = y, b = z), west (facing -X)."""
    kits = [S.kit(f"pad_{v}", lambda v=v: SH.k_pad(v)) for v in range(4)]
    rand = rng(seed * 211 + 9)
    out, tries = [], 0
    while len(out) < count and tries < count * 8:
        tries += 1
        a, b = rand(a0, a1), rand(b0, b1)
        if keep is not None and not keep(a, b):
            continue
        s = rand(*size)
        roll, t1, t2, j = rand(0, TAU), rand(-0.45, 0.45), rand(-0.45, 0.45), rand(0, jitter)
        if facing == "front":
            m = place(a, c - j, b, rz=t2, ry=roll, rx=t1, s=s)
        elif facing == "back":
            m = place(a, c + j, b, rz=math.pi + t2, ry=roll, rx=t1, s=s)
        elif facing == "down":
            m = place(a, b, c - j, rz=roll, rx=math.pi / 2 + t1, ry=t2, s=s)
        elif facing == "up":
            m = place(a, b, c + j, rz=roll, rx=-math.pi / 2 + t1, ry=t2, s=s)
        elif facing == "east":
            m = place(c + j, a, b, rz=math.pi / 2 + t2, ry=roll, rx=t1, s=s)
        else:
            m = place(c - j, a, b, rz=-math.pi / 2 + t2, ry=roll, rx=t1, s=s)
        out.append(S.put(kits[len(out) % 4], f"{name}_{len(out):03d}", rid, "SpottedPad", m, ev, ref, layer=layer, note=note))
    return out


def iron_frame(S, rid, name, xs, y0, y1, z_base, decks, extra_tiers=(), ev="A", ref="", note="", walk=True, top_extra=1.2):
    """Iron scaffold frame on slender posts with arched trusses under each deck level and iron walkways on them
    (A: 03_Left_City middle, 15_Background/Background_01 and 02). xs: post positions along X."""
    top = max(decks)
    posts = [(x, y, z_base, top + top_extra) for x in xs for y in (y0, y1)]
    bays = []
    levels = sorted(set(list(decks) + list(extra_tiers)))
    for xa, xb in zip(xs, xs[1:]):
        span = xb - xa
        spr = [z - 0.2 * span - 0.06 for z in levels if z - 0.2 * span - 0.06 > z_base + 0.6]
        for yy in (y0, y1):
            bays.append((xa, yy, xb, yy, spr, None, None, None))
    span = y1 - y0
    for x in (xs[0], xs[-1]):
        spr = [z - 0.2 * span - 0.06 for z in decks if z - 0.2 * span - 0.06 > z_base + 0.6]
        bays.append((x, y0, x, y1, spr, None, None, None))
    out = scaffold(S, rid, name, posts, bays, ev, ref, note)
    if walk:
        g = Geo()
        for z in decks:
            SH.iron_walk(g, xs[0] - 0.45, xs[-1] + 0.45, y0 - 0.2, y1 + 0.2, z)
        out.append(S.add(g, name + "_Walks", rid, "IronWalkway", ev, ref, note))
    return out


def stone_pier(g, x0, x1, y0, y1, z0, z1, seed=0, block=0.85, cap=True):
    """Pier of rounded rubble blocks with a cobbled top (A: 03_Left_City left_bottom, 09_Bench middle, 12_Materials)."""
    SH.rubble_pier(g, x0, x1, y0, y1, z0, z1 - (0.24 if cap else 0.0), seed=seed, block=block)
    if cap:
        A.add_cobbles(g, x0 - 0.15, x1 + 0.15, y0 - 0.15, y1 + 0.15, z1, size=(0.7, 0.56), seed=seed + 1, key="cobble", height=0.26)


def ring_posts(S, rid, name, items, ev="A", ref="11_Lower_City/Lower_City_statue.jpg; 03_Left_City/Left_City_left_bottom.jpg"):
    """Mooring posts with a ring head standing in the water (stage 2 part). items: (x, y, z_base[, scale])."""
    datas = kit_objs(S, "ringpost_tall", lambda coll: A.build_ring_post(coll, S.mat, "rp", 2.9))
    out = []
    for i, it in enumerate(items):
        s = it[3] if len(it) > 3 else 0.86
        out.append(S.put(datas[0], f"{name}_{i:03d}", rid, "RingPostTall", place(it[0], it[1], it[2], s=s), ev, ref))
    return out


# ---------------------------------------------------------------------------- creatures (D-347: static set dressing)
def creature(S, rid, kind, name, x, y, z, rz=0.0, s=1.0, note=""):
    """Place one static creature in the region's CHARS collection."""
    fam = CR.family(kind)
    s = s * CR.SCALE.get(fam, 1.0)
    ev, ref = CR.EVIDENCE.get(fam, CR.EVIDENCE.get(fam.replace("_seated", ""), ("C", "")))
    obj = S.put(S.kit("CR_" + kind, CR.BUILDERS[kind]), f"Char_{name}", rid, "Creature_" + fam, place(x, y, z, rz=rz, s=s), ev, ref, layer="CHARS",
                note=("static figure (user decision D-347); " + note).strip("; "))
    obj["cot_character"] = True
    return obj


def populate(S, rid, name, info, kinds, count, seed=0, facing=0.0, storeys=None, avoid=()):
    """Put up to `count` creatures in a stack's rooms where their footprint is free of walls, columns, shafts, solid
    cells, furniture and each other. kinds: creature kit keys (picked at random). storeys: limit to these storey indices.
    avoid: extra (storey, x0, x1, y0, y1) rectangles kept clear (region-specific pieces)."""
    room = info["room"]
    rand = rng(seed * 4099 + 11)
    taken = []
    out = []
    pool = [t for t in room["storeys"] if storeys is None or t[0] in storeys]
    if not pool:
        return out
    for n in range(count):
        kind = kinds[int(rand(0, len(kinds)))]
        fam = CR.family(kind)
        r = CR.RADIUS.get(fam, 0.8)
        for _ in range(60):
            i, zf, top = pool[int(rand(0, len(pool)))]
            if top - zf < CR.HEIGHT.get(fam, 1.8) + 0.4:
                continue
            x, y = rand(room["x0"], room["x1"]), rand(room["yf"], room["yb"])
            if not room["free"](i, x, y, r):
                continue
            if any(j == i and abs(x - tx) < r + tr and abs(y - ty) < r + tr for j, tx, ty, tr in taken):
                continue
            if any(j == i and a - r < x < b + r and c - r < y < d + r for j, a, b, c, d in avoid):
                continue
            out.append(creature(S, rid, kind, f"{name}_{n:02d}", x, y, zf + 0.01, rz=facing + rand(-0.6, 0.6)))
            taken.append((i, x, y, r))
            break
    return out

