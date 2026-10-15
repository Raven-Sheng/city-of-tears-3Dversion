"""Place the Quirrel + bench asset in the LeftWell lancet hall (user request 2026-10-06).

  "D:\\Blender\\blender.exe" -b --factory-startup <city .blend> --python scripts/assets/place_quirrel_bench.py -- \
        [--asset assets/hero/QuirrelBench_v005/QuirrelBench_v005.blend] [--out FILE] [--checkpoint]

* Appends (not links) the asset's QB_Bench and QRL_Quirrel collections; the look-dev stage is never brought in.
* The bench goes under the region collection COT_S3_LeftWell, Quirrel under COT_S3_LeftWell_CHARS (the region's
  creature layer), both parented to one empty QB_Place_LeftWell so they move together.
* Placed objects carry cot_region = LeftWell and cot_qb_placed, but not cot_s3: a structure rebuild of the region
  keeps them, and scripts/build/build_art.py carries them into the art file. Re-running replaces the earlier placement.
* Spot (A, master map): WestBlock floor at map y 2923 (world Z 45.133), bench centre at map x 1723 (world X -133.8),
  about 4 H inside the east wall with its lancet windows. Depth Y -5.5 (front half of the hall, facing the viewer
  side like the game view) is completion (C), chosen clear of the hall's furniture groups and creature.
Writes a placement report next to --out (or the opened file) as quirrel_bench_placement.json in logs/.
"""
import json
import shutil
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


ASSET = Path(arg("--asset", ROOT / "assets" / "hero" / "QuirrelBench_v005" / "QuirrelBench_v005.blend"))
OUT = Path(arg("--out", bpy.data.filepath))
SPOT = Vector((-133.8, -5.5, 45.139))          # 6 mm above the floor top 45.133: the tapered leg ends reach 4 mm below the asset origin
PLACE = "QB_Place_LeftWell"

# ---- remove an earlier placement
old = [o for o in bpy.data.objects if o.get("cot_qb_placed")]
for o in old:
    bpy.data.objects.remove(o, do_unlink=True)
for c in [c for c in bpy.data.collections if c.get("cot_qb_placed")]:
    bpy.data.collections.remove(c)

# ---- append the two asset collections
with bpy.data.libraries.load(str(ASSET), link=False) as (src, dst):
    missing = [n for n in ("QB_Bench", "QRL_Quirrel") if n not in src.collections]
    if missing:
        raise SystemExit(f"asset lacks collections {missing}")
    dst.collections = ["QB_Bench", "QRL_Quirrel"]
bench_c, quirrel_c = dst.collections
region_c = bpy.data.collections["COT_S3_LeftWell"]
chars_c = bpy.data.collections["COT_S3_LeftWell_CHARS"]
region_c.children.link(bench_c)
chars_c.children.link(quirrel_c)
bench_c.name, quirrel_c.name = "LeftWell_QB_Bench", "LeftWell_QRL_Quirrel"
for c in [bench_c, quirrel_c] + list(quirrel_c.children_recursive):
    c["cot_qb_placed"] = True

# the inverted-hull contours join the city's outline collection: render_art.py shows it in final renders and hides it
# for clay checks (in Workbench the hulls would draw the character solid black)
outline_c = bpy.data.collections.get("COT_S2_OUTLINE")
if outline_c is not None:
    for c in list(quirrel_c.children_recursive):
        for o in list(c.objects):
            if o.get("cot_role") == "contour":
                o["cot_region"] = "LeftWell"
                o["cot_qb_placed"] = True
                c.objects.unlink(o)
                outline_c.objects.link(o)
        if not c.objects and not c.children:
            bpy.data.collections.remove(c)

place = bpy.data.objects.new(PLACE, None)
place.empty_display_type = "ARROWS"
place.empty_display_size = 0.5
place.location = SPOT
bench_c.objects.link(place)
asset_name = ASSET.stem
for o in list(bench_c.all_objects) + list(quirrel_c.all_objects):
    o["cot_region"] = "LeftWell"
    o["cot_qb_placed"] = True
    o["cot_qb_asset"] = asset_name
    if o.name in ("QB_Root", "QRL_Root") or (o.parent is None and o is not place):
        o.parent = place
        o.matrix_parent_inverse = Matrix.Identity(4)
place["cot_note"] = "Quirrel and his bench, LeftWell lancet hall east end (map x 1723, floor y 2923); depth Y is completion"

# ---- check cameras (scripts/render/render_art.py reads cot_region / cot_hide / cot_res); the viewer-side facade is cut
for name, loc, target, lens in (("CAM_QB_City_Front", (-133.3, -15.5, 46.35), (-133.3, -5.4, 45.75), 50.0),
                                ("CAM_QB_City_Interior", (-136.9, -9.6, 46.75), (-133.5, -5.3, 45.75), 40.0),
                                ("CAM_QB_City_Hall", (-143.0, -17.0, 48.6), (-133.6, -1.5, 46.6), 26.0)):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_start, data.clip_end = 0.05, 400.0
    cam = bpy.data.objects.new(name, data)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam["cot_region"] = "LeftWell"
    cam["cot_hide"] = "FRONT"
    cam["cot_res"] = [1920, 1080]
    cam["cot_qb_placed"] = True
    bench_c.objects.link(cam)
bpy.context.view_layer.update()

# ---- clearance against the city around the spot
deps = bpy.context.evaluated_depsgraph_get()


def tree(obj):
    ev = obj.evaluated_get(deps)
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(obj.matrix_world)
    ev.to_mesh_clear()
    t = BVHTree.FromBMesh(bm)
    bm.free()
    return t


placed = [o for o in bpy.data.objects if o.get("cot_qb_placed") and o.type in ("MESH", "CURVE") and o.get("cot_role") != "contour"]
lo = SPOT + Vector((-1.6, -1.6, -0.3))
hi = SPOT + Vector((1.6, 1.6, 1.6))


def near(o):
    if o.get("cot_qb_placed") or o.type not in ("MESH", "CURVE") or o.hide_render:
        return False
    corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return all(min(c[i] for c in corners) < hi[i] and max(c[i] for c in corners) > lo[i] for i in range(3))


neighbours = [o for o in bpy.data.objects if near(o)]
hits = []
ptrees = {o.name: tree(o) for o in placed}
for n in neighbours:
    nt = tree(n)
    for name, pt in ptrees.items():
        k = len(pt.overlap(nt))
        if k:
            hits.append({"placed": name, "city": n.name, "triangle_pairs": k})
report = {"target": str(OUT), "asset": str(ASSET), "spot": list(SPOT), "removed_previous": len(old),
          "placed_objects": len([o for o in bpy.data.objects if o.get("cot_qb_placed")]),
          "neighbours_checked": [n.name for n in neighbours], "overlaps": hits}
# contact with the hall floor: the bench feet should sit on it
floor_hits = [h for h in hits if "Floors" in h["city"]]
report["note"] = "overlaps with the hall floor are expected only if the bench feet sink into it"
print("COT_PLACE", json.dumps({"placed": report["placed_objects"], "neighbours": len(neighbours), "overlaps": hits}, ensure_ascii=False))

bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
if "--checkpoint" in argv:
    stem = OUT.stem
    ck = ROOT / "scenes" / "checkpoints"
    n = 1 + max([int(p.stem.rsplit("_v", 1)[1]) for p in ck.glob(f"{stem}_v*.blend") if p.stem.rsplit("_v", 1)[1].isdigit()] or [0])
    target = ck / f"{stem}_v{n:03d}.blend"
    shutil.copy2(OUT, target)
    report["checkpoint"] = str(target)
    print("COT_CHECKPOINT", target)
(ROOT / "logs").mkdir(exist_ok=True)
(ROOT / "logs" / f"quirrel_bench_placement_{OUT.stem}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
