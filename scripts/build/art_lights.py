"""Stage 4 lighting: real lights at every lamp globe, per-region painted fill, and region-specific accents.

* Lamp lights: one point light per lamp globe (connected faces of a lamp material), placed at the globe centre with
  the globe radius, coloured by material (config art.json lights.lamp_materials). The globe material keeps its own
  emission (what the eye sees); the point light is what lights the room. Stage 2 plaza lamps already have lights.
* Region fill: two shadowless rectangle lights per region (one in front facing the viewer-side openings, one above
  facing down), light-linked to that region's collection only, coloured by the region family. This is the painted
  ambient of the references (rooms readable everywhere) without lighting the neighbours or casting rectangles in
  reflections. Power = family irradiance (W/m2) x light area.
"""
import math
from collections import defaultdict

import bmesh
import bpy
from mathutils import Vector

LIGHT_ROOT = "COT_S4_LIGHTS"


def coll(name, parent):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in parent.children:
        parent.children.link(c)
    return c


def new_light(c, name, kind, loc, color, power, radius=0.1, size=None, rot=None, shadow=True, props=None, spread=None):
    data = bpy.data.lights.new(name + "_data", kind)
    data.color = color
    data.energy = power
    data.use_shadow = shadow
    if kind in ("POINT", "SPOT"):
        data.shadow_soft_size = radius
    if kind == "AREA":
        data.shape = "RECTANGLE"
        data.size, data.size_y = size
        if spread is not None:
            data.spread = math.radians(spread)
    obj = bpy.data.objects.new(name, data)
    obj.location = loc
    if rot is not None:
        obj.rotation_euler = rot
    obj.visible_camera = False
    if kind == "AREA" or radius > 1.5:
        obj.visible_glossy = False
    obj["cot_s4"] = True
    for k, v in (props or {}).items():
        obj[k] = v
    c.objects.link(obj)
    return obj


def _islands(mesh, slot_indices):
    """Centroid (local) and radius of each connected group of faces using one of the material slots."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    faces = [f for f in bm.faces if f.material_index in slot_indices]
    parent = {}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for f in faces:
        parent[f.index] = f.index
    vert_face = defaultdict(list)
    for f in faces:
        for v in f.verts:
            vert_face[v.index].append(f.index)
    for fl in vert_face.values():
        r0 = find(fl[0])
        for fi in fl[1:]:
            r = find(fi)
            if r != r0:
                parent[r] = r0
    groups = defaultdict(list)
    fmap = {f.index: f for f in faces}
    for fi in parent:
        groups[find(fi)].append(fmap[fi])
    out = []
    for fl in groups.values():
        vs = {v.index: v.co.copy() for f in fl for v in f.verts}
        c = sum(vs.values(), Vector()) / len(vs)
        r = max((p - c).length for p in vs.values())
        mi = fl[0].material_index
        out.append((c, r, mi))
    bm.free()
    return out


def lamp_sites(materials, merge):
    cache = {}
    sites = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.hide_render or obj.get("cot_s2") or not obj.get("cot_s3"):
            continue
        slots = [(i, s.material.name) for i, s in enumerate(obj.material_slots) if s.material and s.material.name in materials]
        if not slots:
            continue
        key = obj.data.name
        if key not in cache:
            cache[key] = _islands(obj.data, {i for i, _ in slots})
        names = dict(slots)
        sc = max(obj.matrix_world.to_scale())
        for c, r, mi in cache[key]:
            sites.append({"loc": obj.matrix_world @ c, "r": r * sc, "mat": names.get(mi, slots[0][1]), "region": obj.get("cot_region", "_misc"),
                          "gain": float(obj.get("cot_lamp_gain", 1.0))})
    # merge globes closer than `merge` with the same material (e.g. a cluster of tiny candles)
    merged = []
    for s in sorted(sites, key=lambda s: (s["mat"], s["loc"].x, s["loc"].y, s["loc"].z)):
        for m in merged:
            if m["mat"] == s["mat"] and (m["loc"] - s["loc"]).length < merge:
                m["n"] += 1
                m["loc"] = m["loc"].lerp(s["loc"], 1.0 / m["n"])
                m["r"] = max(m["r"], s["r"])
                break
        else:
            merged.append(dict(s, n=1))
    return merged, len(sites)


def build_lamp_lights(root, cfg):
    mats = cfg["lamp_materials"]
    sites, raw = lamp_sites(set(mats), cfg.get("lamp_merge", 0.35))
    counts = defaultdict(int)
    for i, s in enumerate(sites):
        spec = mats[s["mat"]]
        c = coll(f"COT_S4_LIGHTS_{s['region']}", root)
        # lamp_scale: per-region power factor for halls packed with lamps (e.g. the TowerBlock chandeliers)
        power = spec["power"] * min(3.0, s["n"]) * cfg.get("lamp_scale", {}).get(s["region"], 1.0) * s.get("gain", 1.0)
        # lamp_color: per-region colour of a lamp material (e.g. the warm lamps of the House of Pleasure turned pink)
        color = cfg.get("lamp_color", {}).get(s["region"], {}).get(s["mat"], spec["color"])
        new_light(c, f"COT_S4_Lamp_{s['region']}_{i:04d}", "POINT", s["loc"], color, power, radius=max(0.03, min(0.25, s["r"])),
                  props={"cot_region": s["region"], "cot_light_kind": "lamp", "cot_lamp_material": s["mat"]})
        counts[s["region"]] += 1
    return {"globes": raw, "lights": len(sites), "per_region": dict(counts)}


def region_bounds(rid):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    n = 0
    for o in bpy.data.objects:
        if o.get("cot_region") != rid or not o.get("cot_s3") or o.type not in ("MESH", "CURVE") or o.hide_render:
            continue
        if o.get("cot_layer") in ("ROCK", "CAVESHELL", "BACKDROP"):
            continue
        for corner in o.bound_box:
            w = o.matrix_world @ Vector(corner)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
        n += 1
    return (lo, hi) if n else None


def build_region_fill(root, cfg):
    report = {}
    scales = cfg.get("fill_scale", {})
    for rid, fam in cfg["regions"].items():
        spec = dict(cfg["families"][fam])
        s = scales.get(rid, 1.0)
        spec["front"], spec["top"] = spec["front"] * s, spec["top"] * s
        amb = [c * cfg.get("ambient_scale", {}).get(rid, 1.0) for c in spec.get("ambient", (0.0, 0.0, 0.0))]
        n_amb = 0
        for o in bpy.data.objects:                               # painted ambient read by NG_COT_Paint (cot_amb)
            if o.get("cot_region") == rid and o.get("cot_s3") and o.type in ("MESH", "CURVE", "FONT"):
                # viewer-side facades are seen from outside: they keep less of the interior's painted ambient
                f = cfg.get("front_layer_ambient", 1.0) if o.get("cot_layer") == "FRONT" else 1.0
                o["cot_amb"] = [c * f for c in amb]
                n_amb += 1
        target = bpy.data.collections.get("COT_S3_" + rid)
        b = region_bounds(rid)
        if target is None or b is None:
            report[rid] = "skipped (no collection or geometry)"
            continue
        lo, hi = b
        c = coll(f"COT_S4_LIGHTS_{rid}", root)
        w, d, h = hi.x - lo.x, hi.y - lo.y, hi.z - lo.z
        cx, cy, cz = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2, (lo.z + hi.z) / 2
        props = {"cot_region": rid, "cot_light_kind": "fill", "cot_family": fam}
        front = new_light(c, f"COT_S4_Fill_{rid}_Front", "AREA", (cx, lo.y - 2.0, cz), spec["fill"], spec["front"] * w * h,
                          size=(w, h), rot=(math.radians(90), 0, 0), shadow=False, props=props)
        top = new_light(c, f"COT_S4_Fill_{rid}_Top", "AREA", (cx, cy, hi.z + 2.0), spec["fill"], spec["top"] * w * d,
                        size=(w, d), shadow=False, props=props)
        for L in (front, top):
            L.light_linking.receiver_collection = target
        report[rid] = {"family": fam, "ambient": [round(c, 3) for c in amb], "ambient_objects": n_amb, "box": [round(v, 1) for v in (*lo, *hi)], "front_W": round(front.data.energy), "top_W": round(top.data.energy)}
    return report
