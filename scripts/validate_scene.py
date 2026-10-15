"""Validate the saved greybox against config/layout.json. Run in its own Blender process:

  blender -b --factory-startup scenes/city_master.blend --python scripts/validate_scene.py -- [--out logs/validate_scene.json]

Checks that what was saved matches what the layout says should exist: every region and element
has objects, meshes are local editable data with materials, cameras and reference objects are
present, and built bounds agree with the layout boxes. It also reports solid-versus-room overlaps
computed from the layout. Machine checks only; they do not replace looking at the renders.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = ROOT / (argv[argv.index("--out") + 1] if "--out" in argv else "logs/validate_scene.json")
PROJECT = json.loads((ROOT / "config" / "project.json").read_text(encoding="utf-8"))
LAYOUT = json.loads((ROOT / "config" / "layout.json").read_text(encoding="utf-8"))
OX, OY = PROJECT["coordinates"]["origin_map"]
PPB = PROJECT["coordinates"]["px_per_bu"]
D = PROJECT["depth_defaults"]

report = {"blend": bpy.data.filepath, "blender": bpy.app.version_string, "problems": [], "warnings": []}
problems, warnings = report["problems"], report["warnings"]

generated = [o for o in bpy.data.objects if o.get("cot_generated")]
by_region = defaultdict(list)
for obj in generated:
    by_region[obj["cot_region"]].append(obj)

regions = {}
for region in LAYOUT["regions"]:
    rid = region["id"]
    objs = by_region.get(rid, [])
    built = {o["cot_element"] for o in objs}
    missing = [e["id"] for e in region["elements"] if e["id"] not in built]
    if not objs:
        problems.append(f"region {rid}: no objects in the saved file")
    if missing:
        problems.append(f"region {rid}: elements without objects: {missing}")
    evidence = Counter(e.get("ev", "C") for e in region["elements"])
    regions[rid] = {"objects": len(objs), "elements": len(region["elements"]), "evidence": dict(evidence),
                    "collection": bpy.data.collections.get("COT_R_" + rid) is not None}
    if not regions[rid]["collection"]:
        problems.append(f"region {rid}: collection COT_R_{rid} missing")
report["regions"] = regions
report["region_count"] = len([r for r in regions if not r.startswith("_")])

mesh_objects = [o for o in generated if o.type == "MESH"]
for obj in mesh_objects:
    if len(obj.data.vertices) == 0:
        problems.append(f"{obj.name}: empty mesh")
    if obj.data.library is not None:
        problems.append(f"{obj.name}: mesh is library-linked, not editable local data")
    if not obj.data.materials or any(m is None for m in obj.data.materials):
        problems.append(f"{obj.name}: missing material")
report["mesh_objects"] = len(mesh_objects)
report["vertices_total"] = sum(len(o.data.vertices) for o in mesh_objects)
report["polygons_total"] = sum(len(o.data.polygons) for o in mesh_objects)
report["manual_objects"] = sorted(o.name for o in bpy.data.objects if not o.get("cot_generated"))
report["libraries"] = [lib.filepath for lib in bpy.data.libraries]
report["images"] = len(bpy.data.images)

# built bounds versus layout boxes, for elements whose silhouette should fill their map box
checked = 0
for region in LAYOUT["regions"]:
    for e in region["elements"]:
        if e["type"] not in ("stack", "box", "slab") or "map" not in e:
            continue
        objs = [o for o in by_region[region["id"]] if o["cot_element"] == e["id"] and o.type == "MESH"]
        if not objs:
            continue
        xs, zs = [], []
        for obj in objs:
            for corner in obj.bound_box:
                world = obj.matrix_world @ Vector(corner)
                xs.append(world.x)
                zs.append(world.z)
        want_x = sorted(((e["map"][0] - OX) / PPB, (e["map"][2] - OX) / PPB))
        if abs(min(xs) - want_x[0]) > 0.05 or abs(max(xs) - want_x[1]) > 0.05:
            problems.append(f"{region['id']}.{e['id']}: built X range {min(xs):.2f}..{max(xs):.2f} differs from layout {want_x}")
        checked += 1
report["bounds_checked"] = checked

# cameras and reference objects
cams = [o for o in bpy.data.objects if o.type == "CAMERA"]
want_cams = {c["id"] for c in LAYOUT.get("cameras", [])}
have_cams = {o.name for o in cams}
if want_cams - have_cams:
    problems.append(f"cameras missing: {sorted(want_cams - have_cams)}")
report["cameras"] = len(cams)
report["scene_camera"] = bpy.context.scene.camera.name if bpy.context.scene.camera else None
links = [o for o in bpy.data.objects if o.name.startswith("REF_Link_")]
labels = [o for o in bpy.data.objects if o.name.startswith("REF_Label_")]
if len(links) != len(LAYOUT.get("connections", [])):
    problems.append(f"connection lines: {len(links)} in file, {len(LAYOUT.get('connections', []))} in layout")
report["connection_lines"] = dict(Counter(o["cot_link_ev"] for o in links))
report["labels"] = len(labels)
report["layer_collections"] = sorted(c.name for c in bpy.data.collections if c.name.startswith("COT_L_"))

# layout-level overlap report: rooms against solid masses, in X/Z and in depth
def depth(e):
    if "y" in e:
        return sorted(e["y"])
    return {"stack": D["stack_y"], "box": D["walkway_y"], "slab": D["walkway_y"]}.get(e["type"])


def box(e):
    x0, y0, x1, y1 = e["map"]
    return min(x0, x1) / PPB, max(x0, x1) / PPB, min(y0, y1) / PPB, max(y0, y1) / PPB


rooms, solids = [], []
for region in LAYOUT["regions"]:
    for e in region["elements"]:
        if "map" not in e or depth(e) is None:
            continue
        item = (region["id"] + "." + e["id"], box(e), depth(e))
        if e["type"] == "stack":
            rooms.append(item)
        elif e["type"] in ("rock", "box") and e.get("mat", "rock") in ("rock", "hostrock", "stone"):
            solids.append(item)
overlaps = []
for i, (name_a, a, da) in enumerate(rooms):
    for name_b, b, db in solids + rooms[i + 1:]:
        ox = min(a[1], b[1]) - max(a[0], b[0])
        oz = min(a[3], b[3]) - max(a[2], b[2])
        oy = min(da[1], db[1]) - max(da[0], db[0])
        if ox > 0.7 and oz > 0.7 and oy > 0.7:
            overlaps.append({"a": name_a, "b": name_b, "overlap_x": round(ox, 2), "overlap_z": round(oz, 2), "overlap_depth": round(oy, 2)})
report["room_solid_overlaps"] = overlaps
if overlaps:
    warnings.append(f"{len(overlaps)} room/solid overlaps larger than 0.7 units in all three axes")

report["all_passed"] = not problems
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("COT_VALIDATE", json.dumps({k: report[k] for k in ("all_passed", "region_count", "mesh_objects", "vertices_total",
                                                           "cameras", "connection_lines", "manual_objects")}, ensure_ascii=False))
print("COT_VALIDATE_PROBLEMS", json.dumps(problems, ensure_ascii=False))
print("COT_VALIDATE_OVERLAPS", json.dumps(overlaps, ensure_ascii=False))
