"""Check the saved Marissa asset in its own Blender process.

  "D:\\Blender\\blender.exe" -b --factory-startup <blend> --python scripts/assets/check_marissa.py -- [--out report.json] [--catalog]

Reports, per object: evaluated triangles, open / non-manifold edges, empty material slots, parenting; triangle overlaps (BVH)
for the part pairs that must stay apart (arms / hair / gown against the wings, fore wing against hind wing on each side,
left against right wing, arms against the gown); overall bounds and height. --catalog writes the Marissa row in
docs/asset_catalog.csv, replacing an earlier version's row (other rows are kept).
"""
import csv
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
blend = Path(bpy.data.filepath)
OUT = Path(argv[argv.index("--out") + 1]) if "--out" in argv else blend.parent / "check_report.json"
deps = bpy.context.evaluated_depsgraph_get()

parts = [o for o in bpy.data.collections["MAR_Marissa"].all_objects if o.type == "MESH" and o.get("cot_role") != "contour"]
hulls = [o for o in bpy.data.collections["MAR_Ink"].all_objects if o.get("cot_role") == "contour"]


def world_bm(obj):
    ev = obj.evaluated_get(deps)
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(obj.matrix_world)
    ev.to_mesh_clear()
    return bm


report = {"blend": str(blend), "blender": bpy.app.version_string, "objects": {}, "pairs": [], "problems": []}
trees, verts = {}, {}
for obj in parts:
    bm = world_bm(obj)
    open_edges = sum(1 for e in bm.edges if len(e.link_faces) < 2)
    nonman = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    empty_slots = sum(1 for s in obj.material_slots if s.material is None)
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    report["objects"][obj.name] = {"triangles": tris, "open_edges": open_edges, "nonmanifold_edges": nonman, "empty_material_slots": empty_slots,
                                   "evidence": obj.get("cot_ev", ""), "parent": obj.parent.name if obj.parent else None,
                                   "materials": [s.material.name for s in obj.material_slots if s.material]}
    if empty_slots:
        report["problems"].append(f"{obj.name}: {empty_slots} empty material slots")
    if open_edges or nonman:
        report["problems"].append(f"{obj.name}: {open_edges} open / {nonman} non-manifold edges")
    if obj.parent is None or obj.parent.name != "MAR_Root":
        report["problems"].append(f"{obj.name}: not parented to MAR_Root")
    trees[obj.name] = BVHTree.FromBMesh(bm)
    verts[obj.name] = [v.co.copy() for v in bm.verts]
    bm.free()
for h in hulls:
    if h.get("cot_ink_of") not in report["objects"]:
        report["problems"].append(f"{h.name}: contour of a missing part")


def group(prefix):
    return [o.name for o in parts if o.name.startswith(prefix)]


wings = group("MAR_Wing")
pairs = []
for a in group("MAR_Arms") + group("MAR_Hair") + group("MAR_Gown_") + group("MAR_Legs"):
    pairs += [(a, w) for w in wings]
for side in ("L", "R"):
    pairs.append((f"MAR_WingFore_{side}", f"MAR_WingHind_{side}"))
pairs += [("MAR_WingFore_L", "MAR_WingFore_R"), ("MAR_WingHind_L", "MAR_WingHind_R"), ("MAR_WingFore_L", "MAR_WingHind_R"), ("MAR_WingFore_R", "MAR_WingHind_L")]
pairs += [("MAR_Arms", g) for g in group("MAR_Gown_")] + [("MAR_Arms", "MAR_Hair")]
for a, b in pairs:
    if a not in trees or b not in trees:
        continue
    hits = len(trees[a].overlap(trees[b]))
    dmin = min((trees[b].find_nearest(co)[3] for co in verts[a][::3]), default=None)
    entry = {"a": a, "b": b, "overlapping_triangle_pairs": hits, "min_distance": round(dmin, 4) if dmin is not None else None}
    report["pairs"].append(entry)
    if hits:
        report["problems"].append(f"{a} intersects {b} ({hits} triangle pairs)")

allv = [c for n in verts for c in verts[n]]
lo = [min(c[i] for c in allv) for i in range(3)]
hi = [max(c[i] for c in allv) for i in range(3)]
report["bounds_H"] = {"min": [round(v, 3) for v in lo], "max": [round(v, 3) for v in hi], "figure_height": round(hi[2] - lo[2], 3), "hover": round(lo[2], 3)}
root = bpy.data.objects.get("MAR_Root")
report["root"] = {k: (v if isinstance(v, (str, int, float)) else str(v)) for k, v in (root.items() if root else [])}
if root is None:
    report["problems"].append("missing root MAR_Root")
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("COT_CHECK problems:", report["problems"] or "none")
print("COT_BOUNDS", report["bounds_H"])
print("COT_PAIRS", len(report["pairs"]), "checked;", sum(1 for p in report["pairs"] if p["overlapping_triangle_pairs"]), "intersecting")

if "--catalog" in argv:
    rel = str(blend.relative_to(ROOT)).replace("\\", "/")
    target = ROOT / "docs" / "asset_catalog.csv"
    with target.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames
        keep = [r for r in reader if r.get("asset_id") != "Marissa"]          # latest version only
    mats = sorted({s.material.name for o in parts for s in o.material_slots if s.material})
    row = {"asset_id": "Marissa", "name_zh": "玛丽莎（欢乐之屋歌手：悬浮直立、双臂下垂、身后 V 形蝶翼、金发偏左、根须状长裙；静态姿势，无绑定）",
           "category": "角色（独立资产）", "region_id": "HouseOfPleasure", "route": "Blender 参数化／专用建模",
           "generator": "scripts/assets/build_marissa.py",
           "evidence": "/".join(sorted({o.get("cot_ev", "") for o in parts if o.get("cot_ev")})),
           "references": "Character/Marissa/Marissa.png; 00_Master crop C1 (stage); 02_Marissa/Marissa.jpg",
           "objects": len(parts), "unique_data_blocks": len({o.data.name for o in parts}), "instances": 0,
           "mesh_vertices": sum(len(o.data.vertices) for o in parts), "curve_splines": 0,
           "materials": "; ".join(mats), "collection": "MAR_Marissa", "blend_file": rel, "example_object": "MAR_Root",
           "check_views": "CAM_MAR_RefFront; CAM_MAR_ThreeQuarter; CAM_MAR_ThreeQuarterL; CAM_MAR_SideRight; CAM_MAR_Back; CAM_MAR_Top; CAM_MAR_Portrait; CAM_MAR_Audience",
           "completion_notes": "正面造型与颜色取自用户原图（A），尺寸按总图舞台（A）；翅膀后掠、前后倾与弯度、身体进深、背面裙片为补全（C）；腿为 B",
           "lux3d": "未使用", "lux3d_task_id": "—", "lux3d_quote": "—", "lux3d_cost": "0",
           "status": "独立资产已建成；未放入城市工程"}
    with target.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(keep + [row])
    print("COT_CATALOG", len(keep), "+ 1")
