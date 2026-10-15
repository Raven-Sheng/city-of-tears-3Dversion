"""Stage 3 prop fitting: settle furniture and standing creatures on the floor surface, drop props that still cut
into the structure (D-350).

Rooms stacked on another building stand on that building's roof slab, tier steps and street floors are not at the
storey height the layout gives, so a prop put at the storey height can sink into the floor. Each floor-standing prop
is lifted onto the highest structure surface under its footprint (at most 0.6 m). A prop that still intersects any
structure mesh or another prop after that (a shaft, a kiosk, a lamp drop, a rock lintel) is removed; region-specific
placements and the general furnishing rules keep this rare. The result is deterministic for the same scene.
"""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

FLOATING = ("winged_sentry", "soul_twister")          # hover: never settled
SEATED = ("resident_seated",)                          # seated on a chair: the chair contact is intended


def _bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


def _is_prop(o):
    return bool(o.get("cot_s3")) and (bool(o.get("cot_character")) or o.get("cot_asset") in ("Furniture", "NoblePortrait", "PillPlatform"))


def _family(o):
    a = o.get("cot_asset") or ""
    return a[len("Creature_"):] if a.startswith("Creature_") else ""


def fit_props(regions=None):
    """Settle and cull the props of the given regions (all regions when None). Returns a report dict."""
    vl = bpy.context.view_layer
    vl.update()
    dg = bpy.context.evaluated_depsgraph_get()
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render and (o.get("cot_s3") or o.get("cot_s2"))
              and len(o.data.polygons) > 0 and not (o.get("cot_s2") and any(k in o.name for k in ("Rain_Layer", "FogDomain", "GlowHaze")))]   # stage 2 effect volumes are not solid
    props = [o for o in meshes if _is_prop(o) and (regions is None or o.get("cot_region") in regions)]
    all_props = {o.name for o in meshes if _is_prop(o)}
    structure = [o for o in meshes if o.name not in all_props]
    boxes = {o.name: _bbox(o) for o in meshes}
    trees = {}

    def tree(o, shrink=0.0, lift=0.0):
        key = (o.name, shrink, lift)
        if key not in trees:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            vs = [o.matrix_world @ v.co for v in me.vertices]
            if shrink or lift:
                c = sum(vs, Vector()) / max(1, len(vs))
                vs = [c + (v - c) * (1.0 - shrink) + Vector((0, 0, lift)) for v in vs]
            trees[key] = BVHTree.FromPolygons(vs, [tuple(p.vertices) for p in me.polygons])
            ev.to_mesh_clear()
        return trees[key]

    CELL = 8.0                                         # uniform grid over x, y so each query only looks at nearby objects

    def cells(lo, hi):
        for ix in range(int(lo[0] // CELL), int(hi[0] // CELL) + 1):
            for iy in range(int(lo[1] // CELL), int(hi[1] // CELL) + 1):
                yield ix, iy

    def index(pool):
        grid = {}
        for o in pool:
            a, b = boxes[o.name]
            if (b[0] - a[0]) * (b[1] - a[1]) > 4.0e4:      # huge objects (cavern shells, host rock) go to a short list
                grid.setdefault("big", []).append(o)
                continue
            for c in cells(a, b):
                grid.setdefault(c, []).append(o)
        return grid

    def near(lo, hi, grid, pad=0.0):
        seen = set()
        for c in list(cells(lo - Vector((pad, pad, pad)), hi + Vector((pad, pad, pad)))) + ["big"]:
            for o in grid.get(c, ()):
                if o.name in seen:
                    continue
                seen.add(o.name)
                a, b = boxes[o.name]
                if all(b[i] >= lo[i] - pad and a[i] <= hi[i] + pad for i in range(3)):
                    yield o

    def group_of(o):
        n = o.name
        return n.rsplit("_", 1)[0] if "_FurnG_" in n else None

    def is_rug(o):
        return o.data is not None and "rug" in o.data.name

    s_grid = index(structure)

    lifted, culled = [], []
    # ---- settle
    for o in props:
        fam = _family(o)
        if o.get("cot_asset") in ("NoblePortrait", "PillPlatform") or fam in FLOATING or fam in SEATED:
            continue
        lo, hi = boxes[o.name]
        base = o.matrix_world.translation.z
        top_hit = None
        cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
        dx, dy = (hi.x - lo.x) * 0.35, (hi.y - lo.y) * 0.35
        probe_lo, probe_hi = Vector((lo.x, lo.y, base - 0.1)), Vector((hi.x, hi.y, base + 0.6))
        cands = list(near(probe_lo, probe_hi, s_grid))
        for px, py in ((cx, cy), (cx - dx, cy - dy), (cx + dx, cy - dy), (cx - dx, cy + dy), (cx + dx, cy + dy)):
            for s in cands:
                hit = tree(s).ray_cast(Vector((px, py, base + 0.6)), Vector((0, 0, -1)), 0.7)
                if hit[0] is not None and (top_hit is None or hit[0].z > top_hit):
                    top_hit = hit[0].z
        if top_hit is not None and top_hit > base + 0.004:
            d = top_hit + 0.01 - base
            o.location.z += d
            lifted.append((o.name, round(d, 3)))
    vl.update()
    for o in props:
        boxes[o.name] = _bbox(o)
    trees = {k: v for k, v in trees.items() if k[0] not in all_props}
    # ---- cull: what still cuts into the structure or another prop
    gone = set()
    p_grid = index([bpy.data.objects[n] for n in sorted(all_props)])
    for o in sorted(props, key=lambda o: o.name):
        if o.name in gone:
            continue
        lo, hi = boxes[o.name]
        t = tree(o, 0.04, 0.03)
        fam = _family(o)
        for s in near(lo, hi, s_grid):
            if fam in SEATED and "Chair" in s.name:
                continue
            if t.overlap(tree(s)):
                culled.append((o.name, s.name))
                gone.add(o.name)
                break
        if o.name in gone:
            continue
        for p in sorted(near(lo, hi, p_grid), key=lambda q: q.name):
            if p.name == o.name or p.name in gone:
                continue
            if (fam in SEATED and "Chair" in p.name) or (_family(p) in SEATED and "Chair" in o.name):
                continue
            if group_of(o) is not None and group_of(o) == group_of(p):
                continue                               # the pieces of one furniture group are laid out together
            if is_rug(o) or is_rug(p):
                continue                               # standing on a rug is fine
            if t.overlap(tree(p, 0.04, 0.03)):
                # keep the furniture, drop the creature; between two of a kind drop the later name
                drop = o if (o.get("cot_character") and not p.get("cot_character")) or \
                    (bool(o.get("cot_character")) == bool(p.get("cot_character")) and o.name > p.name) else p
                if drop.get("cot_region") not in (regions or [drop.get("cot_region")]):
                    drop = o
                culled.append((drop.name, (p if drop is o else o).name))
                gone.add(drop.name)
                if drop is o:
                    break
    # creatures standing right in front of a perspective check camera (within 5 m, inside a 40 degree cone) hide the view
    cams = [c for c in bpy.data.objects if c.type == "CAMERA" and c.get("cot_s3") and c.data.type == "PERSP"]
    for o in sorted(props, key=lambda o: o.name):
        if o.name in gone or not o.get("cot_character") or _family(o) in SEATED:
            continue                                   # the seated audience belongs to its chairs
        lo, hi = boxes[o.name]
        c_o = (lo + hi) / 2
        for c in cams:
            v = c_o - c.matrix_world.translation
            fwd = c.matrix_world.to_3x3() @ Vector((0, 0, -1))
            if v.length < 5.0 and v.length > 1e-3 and fwd.angle(v) < 0.7:
                culled.append((o.name, "camera " + c.name))
                gone.add(o.name)
                break
    for n in sorted(gone):
        ob = bpy.data.objects.get(n)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)
    return {"props": len(props), "lifted": lifted, "culled": culled}
