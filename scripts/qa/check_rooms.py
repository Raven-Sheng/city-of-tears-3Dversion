"""Room intrusion test of the saved structure file.

  blender -b --factory-startup scenes/city_structure.blend --python scripts/qa/check_rooms.py

Every stack records its storey interiors (cot_rooms on its _Walls object). Each visible stage 2 / stage 3 mesh that
is not part of that stack, not a prop (furniture, portraits, creatures) and not an effect volume is tested against
each interior, shrunk by 0.12 m: vertices inside it, or faces crossing its boundary. The result goes to
docs/checks/stage_03_rooms.json. Region pieces meant to stand in a room (stairs, lifts, statues) show up here and
are judged by name; rock, canopies, bands or other buildings inside a room are faults.
"""
import json
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
dg = bpy.context.evaluated_depsgraph_get()
INSET = 0.12


def bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def is_prop(o):
    return bool(o.get("cot_character")) or o.get("cot_asset") in ("Furniture", "NoblePortrait", "PillPlatform")


meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render and (o.get("cot_s3") or o.get("cot_s2"))
          and len(o.data.polygons) > 0 and not is_prop(o) and not (o.get("cot_s2") and any(k in o.name for k in ("Rain_Layer", "FogDomain", "GlowHaze")))]
boxes = {o.name: bbox(o) for o in meshes}
_data = {}


def data(o):
    if o.name not in _data:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        mw = np.array(o.matrix_world)
        wco = co @ mw[:3, :3].T + mw[:3, 3]
        tree = BVHTree.FromPolygons([Vector(v) for v in wco], [tuple(p.vertices) for p in me.polygons])
        ev.to_mesh_clear()
        _data[o.name] = (wco, tree)
    return _data[o.name]


def box_tree(b):
    x0, x1, y0, y1, z0, z1 = b
    vs = [Vector((x, y, z)) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    fs = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return BVHTree.FromPolygons(vs, fs)


FITTINGS = ("LiftCarSpire", "DrapeCanopy", "CanopyCurtain", "ShellBlock", "Column", "TwistedColumn", "CeilingRock")   # names that contain a structural word
STRUCT = ("Canopy", "Louvre", "Roof", "Rock", "Lintel", "Column", "Mass", "Band", "Host", "Spire", "Tower", "Podium")
found = []
walls = [o for o in bpy.data.objects if o.get("cot_rooms")]
for w in walls:
    prefix = w.name[: -len("_Walls")] + "_"
    for r in json.loads(w["cot_rooms"]):
        x0, x1, y0, y1, z0, z1 = r
        b = (x0 + INSET, x1 - INSET, y0 + INSET, y1 - INSET, z0 + INSET, z1 - INSET)
        if b[1] <= b[0] or b[3] <= b[2] or b[5] <= b[4]:
            continue
        bt = None
        for o in meshes:
            if o.name.startswith(prefix) or o is w:
                continue
            lo, hi = boxes[o.name]
            if hi[0] < b[0] or lo[0] > b[1] or hi[1] < b[2] or lo[1] > b[3] or hi[2] < b[4] or lo[2] > b[5]:
                continue
            wco, tree = data(o)
            inside = (wco[:, 0] > b[0]) & (wco[:, 0] < b[1]) & (wco[:, 1] > b[2]) & (wco[:, 1] < b[3]) & (wco[:, 2] > b[4]) & (wco[:, 2] < b[5])
            n_in = int(inside.sum())
            depth = 0.0
            if n_in:
                p = wco[inside]
                d = np.minimum.reduce([p[:, 0] - b[0], b[1] - p[:, 0], p[:, 1] - b[2], b[3] - p[:, 1], p[:, 2] - b[4], b[5] - p[:, 2]])
                depth = float(d.max())
            else:
                bt = bt or box_tree(b)
                if not tree.overlap(bt):
                    continue
            zrel = float(wco[inside][:, 2].max() - z0) if n_in else 0.0
            region, asset = o.get("cot_region") or ("S2" if o.get("cot_s2") else ""), o.get("cot_asset") or ""
            structural = o.name.endswith(("_Body", "_Walls", "_Floors", "_Front")) or (asset not in FITTINGS and any(k in asset for k in STRUCT))
            if structural and o.name.endswith(("_Walls", "_Floors", "_Front")) and n_in and (zrel < 0.8 or (o.name.endswith("_Floors") and depth < 0.3)):
                kind = "stacked_slab"          # where one stack stands on another: the slab edge trim of the upper one, under 0.3 m
            elif structural or region != w.get("cot_region"):
                kind = "fault" if depth > 0.15 or not n_in else "contact"
            else:
                kind = "interior_piece"        # the region's own fittings placed in its rooms (lifts, chandeliers, curtains, platforms)
            found.append({"room": w.name, "storey_z": round(z0, 2), "object": o.name, "region": region,
                          "asset": asset, "verts_inside": n_in, "depth": round(depth, 2), "top_above_floor": round(zrel, 2), "kind": kind})
found.sort(key=lambda f: -f["depth"])
out = {"file": bpy.data.filepath, "rooms": sum(len(json.loads(w["cot_rooms"])) for w in walls), "intrusions": found}
(ROOT / "docs" / "checks" / "stage_03_rooms.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
import collections
kinds = collections.Counter(f["kind"] for f in found)
out["summary"] = dict(kinds)
(ROOT / "docs" / "checks" / "stage_03_rooms.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("COT_ROOMS", out["rooms"], "room volumes;", len(found), "intrusions;", dict(kinds))
for f in found:
    if f["kind"] in ("fault", "contact"):
        print("COT_ROOM", f["kind"], f["room"], f["storey_z"], "|", f["object"], f["asset"], f["verts_inside"], f["depth"])
