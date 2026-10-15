"""Place the Marissa asset on the House of Pleasure stage (user request 2026-10-07: put her in the house, not too small,
so she reads as the centre of the stage).

  "D:\\Blender\\blender.exe" -b --factory-startup <city .blend> --python scripts/assets/place_marissa.py -- \
        [--asset assets/hero/Marissa_v002/Marissa_v002.blend] [--scale 1.5] [--xy 158.5,4.12] [--lift 0.1] [--out FILE] [--checkpoint] [--apply-only]

* Appends (not links) the asset's MAR_Marissa collection; its look-dev stage is never brought in. She goes under the
  region's creature layer COT_S3_HouseOfPleasure_CHARS (renamed HouseOfPleasure_MAR_Marissa), parented to one empty
  MAR_Place_HouseOfPleasure that carries the placement scale. Her inverted-hull contours join the city's outline
  collection COT_S2_OUTLINE (shown in final renders, hidden for clay checks), as for Quirrel (D-431).
* Placed objects carry cot_region = HouseOfPleasure and cot_mar_placed, but not cot_s3: a structure rebuild of the region
  keeps them, and scripts/build/build_art.py carries them into the art file. Re-running replaces the earlier placement.
* Spot: the stage top is found by a ray cast at --xy; the root sits --lift above it. She floats just in front of the
  round canopy (valance front y 5.1-5.5), which frames her from behind as in Marissa.jpg (B). X 158.5 instead of the
  master's 160.3 (A): at the master x the long stalactite (x 160.8, tip below the stage top) hangs right in front of her
  and the rock ceiling is low enough to cut her wings; at 158.5 she is under the highest part of the cave ceiling,
  between the left stalactite (x 157.8) and the right pelmet lamp (x 159.5), and her face and body stay clear of the
  stalactite over the audience (x 158.6, y -2.7) in the fixed reference view; only wing tips pass behind stalactites (C).
  Scale 1.5 (3.4 H): the master size (2.36 H) leaves her small on the 8.8 H wide stage; the user asked for her to be
  larger so she reads as the centre of the stage; 1.5 is about the largest that clears ceiling and canopy (C, user).
Writes logs/marissa_placement_<file stem>.json.
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


ASSET = Path(arg("--asset", ROOT / "assets" / "hero" / "Marissa_v002" / "Marissa_v002.blend"))
OUT = Path(arg("--out", bpy.data.filepath))
SCALE = float(arg("--scale", 1.5))
XY = [float(v) for v in arg("--xy", "158.5,4.12").split(",")]
LIFT = float(arg("--lift", 0.1))
REGION = "HouseOfPleasure"
PLACE = "MAR_Place_HouseOfPleasure"

# ---- remove an earlier placement
old = [o for o in bpy.data.objects if o.get("cot_mar_placed")]
for o in old:
    bpy.data.objects.remove(o, do_unlink=True)
for c in [c for c in bpy.data.collections if c.get("cot_mar_placed")]:
    bpy.data.collections.remove(c)
for m in [m for m in bpy.data.meshes if m.users == 0 and m.name.startswith("MAR_")]:
    bpy.data.meshes.remove(m)
bpy.context.view_layer.update()

# ---- stage top under the spot (ray cast down from just above the stage, before anything is appended)
deps = bpy.context.evaluated_depsgraph_get()
hit, loc, _n, _i, hit_obj, _m = bpy.context.scene.ray_cast(deps, Vector((XY[0], XY[1], 79.6)), Vector((0, 0, -1)), distance=3.0)
if not hit or "StagePlatform" not in hit_obj.name:
    raise SystemExit(f"no stage top under {XY}: hit {hit_obj.name if hit else None}")
STAGE_TOP = loc.z
SPOT = Vector((XY[0], XY[1], STAGE_TOP + LIFT))

# ---- append the asset collection
with bpy.data.libraries.load(str(ASSET), link=False) as (src, dst):
    if "MAR_Marissa" not in src.collections:
        raise SystemExit("asset lacks collection MAR_Marissa")
    dst.collections = ["MAR_Marissa"]
mar_c = dst.collections[0]
asset_objs = list(mar_c.all_objects)
chars_c = bpy.data.collections[f"COT_S3_{REGION}_CHARS"]
chars_c.children.link(mar_c)
mar_c.name = f"{REGION}_MAR_Marissa"
for c in [mar_c] + list(mar_c.children_recursive):
    c["cot_mar_placed"] = True
    c.name = c.name if c.name.startswith(REGION) else f"{REGION}_{c.name}"

outline_c = bpy.data.collections.get("COT_S2_OUTLINE")
if outline_c is not None:
    for c in list(mar_c.children_recursive):
        for o in list(c.objects):
            if o.get("cot_role") == "contour":
                c.objects.unlink(o)
                outline_c.objects.link(o)
        if not c.objects and not c.children:
            bpy.data.collections.remove(c)

place = bpy.data.objects.new(PLACE, None)
place.empty_display_type = "ARROWS"
place.empty_display_size = 0.6
place.location = SPOT
place.scale = (SCALE, SCALE, SCALE)
mar_c.objects.link(place)
for o in asset_objs + [place]:
    o["cot_region"] = REGION
    o["cot_mar_placed"] = True
    o["cot_mar_asset"] = ASSET.stem
root = bpy.data.objects["MAR_Root"]
root.parent = place
root.matrix_parent_inverse = Matrix.Identity(4)
place["cot_note"] = (f"Marissa on the House of Pleasure stage, x {XY[0]} y {XY[1]}, stage top z {STAGE_TOP:.3f} + {LIFT}, scale {SCALE} "
                     "(master size x1.0 = 2.36 H; enlarged at the user's request)")
place["cot_scale"] = SCALE

# ---- check cameras (scripts/render/render_art.py reads cot_region / cot_hide / cot_res)
tgt = SPOT + Vector((0.0, 0.0, 1.4 * SCALE))                       # her upper chest
# positions chosen by sight-line ray casts: no stalactite, lamp or curtain between camera and her head, chest and gown
for name, loc, target, lens in (("CAM_MAR_City_Front", (158.0, -1.0, 80.4), tgt + Vector((0, 0, 0.25)), 22.0),  # front row, low: her whole and both beams
                                ("CAM_MAR_City_Audience", (156.8, -6.9, 81.2), tgt, 28.0),                 # back of the audience: stage in context
                                ("CAM_MAR_City_Close", (156.0, 1.0, 80.6), tgt + Vector((0, 0, 0.2)), 28.0),   # stage-left front, three-quarter
                                ("CAM_MAR_City_Side", (163.2, 0.8, 80.5), tgt, 26.0)):                     # stage-right front
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_start, data.clip_end = 0.05, 400.0
    cam = bpy.data.objects.new(name, data)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam["cot_region"] = REGION
    cam["cot_hide"] = ""
    cam["cot_res"] = [1920, 1080]
    cam["cot_mar_placed"] = True
    mar_c.objects.link(cam)
bpy.context.view_layer.update()

# ---- clearance against the city around her
deps = bpy.context.evaluated_depsgraph_get()


def tree(obj):
    ev = obj.evaluated_get(deps)
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(obj.matrix_world)
    ev.to_mesh_clear()
    t = BVHTree.FromBMesh(bm)
    vs = [v.co.copy() for v in bm.verts]
    bm.free()
    return t, vs


parts = [o for o in bpy.data.objects if o.get("cot_mar_placed") and o.type == "MESH" and o.get("cot_role") != "contour"]
ptrees = {o.name: tree(o) for o in parts}
allv = [v for _t, vs in ptrees.values() for v in vs]
lo = Vector([min(v[i] for v in allv) for i in range(3)])
hi = Vector([max(v[i] for v in allv) for i in range(3)])
pad = Vector((0.3, 0.3, 0.3))


def near(o):
    if o.get("cot_mar_placed") or o.type not in ("MESH", "CURVE") or o.hide_render:
        return False
    corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return all(min(c[i] for c in corners) < hi[i] + pad[i] and max(c[i] for c in corners) > lo[i] - pad[i] for i in range(3))


neighbours = [o for o in bpy.data.objects if near(o)]
hits, gaps = [], {}
for n in neighbours:
    nt, nv = tree(n)
    for name, (pt, pv) in ptrees.items():
        k = len(pt.overlap(nt))
        if k:
            hits.append({"placed": name, "city": n.name, "triangle_pairs": k})
        d = min((nt.find_nearest(co)[3] for co in pv[::2]), default=None)
        if d is not None and (n.name not in gaps or d < gaps[n.name][1]):
            gaps[n.name] = (name, round(d, 3))
report = {"target": str(OUT), "asset": str(ASSET), "spot": [round(v, 3) for v in SPOT], "scale": SCALE, "removed_previous": len(old),
          "placed_objects": len([o for o in bpy.data.objects if o.get("cot_mar_placed")]),
          "bounds": {"min": [round(v, 3) for v in lo], "max": [round(v, 3) for v in hi], "height": round(hi.z - lo.z, 3),
                     "hover_above_stage": round(lo.z - STAGE_TOP, 3)},
          "neighbours_checked": len(neighbours), "overlaps": hits,
          "nearest_city_parts": dict(sorted(((k, v) for k, v in gaps.items()), key=lambda kv: kv[1][1])[:12])}
print("COT_PLACE", json.dumps({k: report[k] for k in ("spot", "scale", "placed_objects", "bounds", "neighbours_checked", "overlaps")}, ensure_ascii=False))
print("COT_NEAREST", json.dumps(report["nearest_city_parts"], ensure_ascii=False))

if "--apply-only" not in argv:
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
if "--checkpoint" in argv and "--apply-only" not in argv:
    stem = OUT.stem
    ck = ROOT / "scenes" / "checkpoints"
    n = 1 + max([int(p.stem.rsplit("_v", 1)[1]) for p in ck.glob(f"{stem}_v*.blend") if p.stem.rsplit("_v", 1)[1].isdigit()] or [0])
    target = ck / f"{stem}_v{n:03d}.blend"
    shutil.copy2(OUT, target)
    report["checkpoint"] = str(target)
    print("COT_CHECKPOINT", target)
(ROOT / "logs").mkdir(exist_ok=True)
(ROOT / "logs" / f"marissa_placement_{OUT.stem}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
