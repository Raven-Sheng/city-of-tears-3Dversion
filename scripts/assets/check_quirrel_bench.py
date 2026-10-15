"""Check the saved Quirrel + bench asset in its own Blender process.

  "D:\\Blender\\blender.exe" -b --factory-startup <blend> --python scripts/assets/check_quirrel_bench.py -- [--out report.json] [--catalog]

Reports, per object: evaluated triangles, open / non-manifold edges, empty material slots; between every Quirrel part
and every bench part: triangle overlaps (BVH) and the smallest vertex distance. --catalog writes the two QuirrelBench rows
in docs/asset_catalog.csv, replacing those of any earlier version (other rows are kept).
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


def members(coll_name):
    coll = bpy.data.collections[coll_name]
    return [o for o in coll.all_objects if o.type in ("MESH", "CURVE") and o.get("cot_role") != "contour"]


def world_bm(obj):
    ev = obj.evaluated_get(deps)
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(obj.matrix_world)
    ev.to_mesh_clear()
    return bm


quirrel, bench = members("QRL_Quirrel"), members("QB_Bench")
report = {"blend": str(blend), "blender": bpy.app.version_string, "objects": {}, "pairs": [], "problems": []}
trees, verts = {}, {}
for obj in quirrel + bench:
    bm = world_bm(obj)
    bm.verts.ensure_lookup_table()
    open_edges = sum(1 for e in bm.edges if len(e.link_faces) < 2)
    nonman = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    empty_slots = sum(1 for s in obj.material_slots if s.material is None)
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    report["objects"][obj.name] = {"asset": "Quirrel" if obj in quirrel else "Bench", "type": obj.type, "triangles": tris,
                                   "open_edges": open_edges, "nonmanifold_edges": nonman, "empty_material_slots": empty_slots,
                                   "evidence": obj.get("cot_ev", ""), "parent": obj.parent.name if obj.parent else None}
    if empty_slots:
        report["problems"].append(f"{obj.name}: {empty_slots} empty material slots")
    if obj.parent is None:
        report["problems"].append(f"{obj.name}: not parented to its asset root")
    trees[obj.name] = BVHTree.FromBMesh(bm)
    verts[obj.name] = [v.co.copy() for v in bm.verts]
    bm.free()

for q in quirrel:
    for b in bench:
        hits = len(trees[q.name].overlap(trees[b.name]))
        dmin = min((trees[b.name].find_nearest(co)[3] for co in verts[q.name][::2]), default=None)
        if hits or (dmin is not None and dmin < 0.03):
            report["pairs"].append({"quirrel": q.name, "bench": b.name, "overlapping_triangle_pairs": hits, "min_distance": round(dmin, 4)})
        if hits:
            report["problems"].append(f"{q.name} intersects {b.name} ({hits} triangle pairs)")

roots = {n: bpy.data.objects.get(n) for n in ("QRL_Root", "QB_Root")}
report["roots"] = {n: (dict(o.items()) if o else None) for n, o in roots.items()}
for n, o in roots.items():
    if o is None:
        report["problems"].append(f"missing root {n}")
report["roots"] = {n: {k: (v if isinstance(v, (str, int, float)) else str(v)) for k, v in (o.items() if o else [])} for n, o in roots.items()}
dims = {}
for name, objs in (("Quirrel", quirrel), ("Bench", bench)):
    lo = [min(c[i] for o in objs for c in verts[o.name]) for i in range(3)]
    hi = [max(c[i] for o in objs for c in verts[o.name]) for i in range(3)]
    dims[name] = {"min": [round(v, 3) for v in lo], "max": [round(v, 3) for v in hi]}
report["bounds_H"] = dims
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("COT_CHECK problems:", report["problems"] or "none")
for pr in report["pairs"]:
    print("COT_PAIR", pr)
print("COT_BOUNDS", dims)

if "--catalog" in argv:
    rel = str(blend.relative_to(ROOT)).replace("\\", "/")
    target = ROOT / "docs" / "asset_catalog.csv"
    with target.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames
        keep = [r for r in reader if r.get("blend_file") != rel and not r.get("asset_id", "").startswith("QuirrelBench_")]   # latest version only
    rows = []
    for asset_id, name_zh, coll, objs, root, note in (
            ("QuirrelBench_Bench", "奎若的铁艺长椅（心形与黑桃卷涡靠背、卷头顶杆、弯腿）", "QB_Bench", bench, "QB_Root",
             "座深与背面为补全；右端按左端对称补全"),
            ("QuirrelBench_Quirrel", "奎若（正面坐、跷腿、右手搭椅背、背负骨钉；静态姿势，无绑定）", "QRL_Quirrel", quirrel, "QRL_Root",
             "姿势按用户 2026-10-06 描述；造型尺寸量自截图；背带与骨钉形状为补全")):
        mats = sorted({s.material.name for o in objs for s in o.material_slots if s.material})
        rows.append({"asset_id": asset_id, "name_zh": name_zh, "category": "角色与陈设（独立资产）", "region_id": "LeftWell",
                     "route": "Blender 参数化／专用建模", "generator": "scripts/assets/build_quirrel_bench.py",
                     "evidence": "/".join(sorted({o.get("cot_ev", "") for o in objs if o.get("cot_ev")})),
                     "references": "Character/Quirrel/Screenshot_HK_Quirrel_05.png; 00_Master crop E_quirrel_bench_hall",
                     "objects": len(objs), "unique_data_blocks": len({o.data.name for o in objs}), "instances": 0,
                     "mesh_vertices": sum(len(o.data.vertices) for o in objs if o.type == "MESH"),
                     "curve_splines": sum(len(o.data.splines) for o in objs if o.type == "CURVE"),
                     "materials": "; ".join(mats), "collection": coll, "blend_file": rel, "example_object": root,
                     "check_views": "CAM_QB_RefFront; CAM_QB_ThreeQuarter; CAM_QB_SideRight; CAM_QB_Back; CAM_QB_Top; CAM_QRL_Portrait; CAM_QB_BenchFront",
                     "completion_notes": note, "lux3d": "未使用", "lux3d_task_id": "—", "lux3d_quote": "—", "lux3d_cost": "0",
                     "status": "独立资产已建成；未放入城市工程"})
    with target.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(keep + rows)
    print("COT_CATALOG", len(keep), "+", len(rows))
