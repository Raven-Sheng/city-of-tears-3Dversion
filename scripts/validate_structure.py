"""Stage 3 structure checks that a script can do (they do not replace looking at the check images).

  blender -b --factory-startup <file.blend> --python scripts/validate_structure.py -- [--out report.json]

Reports per region: stage 3 objects, evidence levels, check cameras, visible stage 1 greybox, objects without
materials, degenerate meshes, duplicate names, a content digest (for repeat-build and partial-rebuild tests),
objects that carry no generator tag (hand-made), and district objects that lie inside the world rock masses.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out_path = Path(argv[argv.index("--out") + 1]) if "--out" in argv else ROOT / "docs" / "checks" / "stage_03_validate.json"
layout = json.loads((ROOT / "config" / "layout.json").read_text(encoding="utf-8"))
region_ids = [r["id"] for r in layout["regions"]]

objs = list(bpy.data.objects)
s3 = [o for o in objs if o.get("cot_s3")]
report = {"file": bpy.data.filepath, "blender": bpy.app.version_string, "regions": {}, "problems": []}


def world_bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


# ---- per region
for rid in region_ids:
    mine = [o for o in s3 if o.get("cot_region") == rid]
    geo = [o for o in mine if o.type != "CAMERA"]
    cams = [o for o in mine if o.type == "CAMERA"]
    s2 = [o for o in objs if o.get("cot_s2") and (o.get("cot_region") == rid or rid == "FountainPlaza")]     # the stage 2 sample is the plaza
    grey = [o for o in objs if o.get("cot_generated") and not o.get("cot_s2") and not o.get("cot_s3") and o.get("cot_region") == rid]
    grey_visible = [o.name for o in grey if not o.hide_render]
    ev = {}
    for o in geo:
        ev[o.get("cot_evidence", "?")] = ev.get(o.get("cot_evidence", "?"), 0) + 1
    h = hashlib.sha1()
    hg = hashlib.sha1()                                   # geometry only: no datablock names
    for o in sorted(geo, key=lambda o: o.name):
        d = o.data
        nv = len(d.vertices) if o.type == "MESH" else (sum(len(s.bezier_points) + len(s.points) for s in d.splines) if o.type == "CURVE" else 0)
        cs = 0.0
        if o.type == "MESH" and nv:
            co = [0.0] * (nv * 3)
            d.vertices.foreach_get("co", co)
            cs = round(sum(co), 2)
        loc = o.matrix_world.translation
        h.update(f"{o.name}|{d.name if d else ''}|{loc.x:.3f},{loc.y:.3f},{loc.z:.3f}|{nv}|{cs}\n".encode())
        hg.update(f"{o.name}|{loc.x:.3f},{loc.y:.3f},{loc.z:.3f}|{nv}|{cs}\n".encode())
    verts = sum(len(o.data.vertices) for o in geo if o.type == "MESH")
    report["regions"][rid] = {"s3_objects": len(geo), "s3_cameras": len(cams), "s2_objects": len(s2), "evidence": ev, "greybox_total": len(grey),
                              "greybox_visible": grey_visible, "vertices_instanced": verts, "digest": h.hexdigest()[:16],
                              "geometry_digest": hg.hexdigest()[:16]}
    if not geo and not s2:
        report["problems"].append(f"{rid}: no stage 3 or stage 2 geometry")
    if grey_visible:
        report["problems"].append(f"{rid}: {len(grey_visible)} stage 1 greybox objects still render")
    if "?" in ev:
        report["problems"].append(f"{rid}: {ev['?']} objects without evidence level")

# ---- materials, meshes, names
no_mat, bad_mesh = [], []
seen = set()
for o in s3:
    if o.type not in ("MESH", "CURVE"):
        continue
    if not o.data.materials or any(m is None for m in o.data.materials):
        no_mat.append(o.name)
    if o.type == "MESH" and o.data.name not in seen:
        seen.add(o.data.name)
        me = o.data
        if len(me.vertices) == 0 or len(me.polygons) == 0:
            bad_mesh.append((o.name, "empty"))
            continue
        co = [0.0] * (len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        if any(math.isnan(v) or math.isinf(v) for v in co):
            bad_mesh.append((o.name, "non-finite"))
        idx = [0] * len(me.polygons)
        me.polygons.foreach_get("material_index", idx)
        if max(idx) >= len(me.materials):
            bad_mesh.append((o.name, "material index out of range"))
report["no_material"] = no_mat
report["bad_meshes"] = bad_mesh
report["duplicate_names"] = sorted(o.name for o in s3 if len(o.name) > 4 and o.name[-4] == "." and o.name[-3:].isdigit())
report["untagged_objects"] = sorted(o.name for o in objs if not (o.get("cot_generated") or o.get("cot_s2") or o.get("cot_s3")))
report["kit_datablocks"] = sum(1 for m in list(bpy.data.meshes) + list(bpy.data.curves) if m.get("cot_s3_kit"))
report["kit_instances"] = sum(1 for o in s3 if o.get("cot_kit"))
for key, label in (("no_material", "objects without material"), ("bad_meshes", "bad meshes"), ("duplicate_names", "duplicate names")):
    if report[key]:
        report["problems"].append(f"{len(report[key])} {label}")

# ---- district objects inside world rock (rooms swallowed by a host mass)
rock_layers = {"ROCK", "CEILING", "BACKDROP", "CAVESHELL"}
world = [o for o in s3 if o.get("cot_region") == "_World" and o.type == "MESH" and o.get("cot_asset") != "Stalactites"]
others = [(o, o.matrix_world.translation.copy() if o.get("cot_kit") else None) for o in s3
          if o.get("cot_region") != "_World" and o.type in ("MESH", "CURVE") and o.get("cot_layer") not in rock_layers]
centres = []
for o, loc in others:
    lo, hi = world_bbox(o)
    centres.append((o, Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)), [hi[i] - lo[i] for i in range(3)]))
# built on purpose inside a rock mass (the core of the mass is cut out around it)
ACCEPTED = {"S3_WestStation_TunnelArch": "station tunnel stub: the rock core has a hole cut for it",
            "S3_WestLowCorridor_SunkenRoom": "sunken middle room of the low corridor: the rock core and skin have a hole cut for it"}
ACCEPTED.update({f"S3_WestStation_PortalLobes_{k:03d}": "rock lobes in the mouth of the station tunnel, inside the hole cut for it (D-363)" for k in range(4)})
swallowed = {}
for w in world:
    lo, hi = world_bbox(w)
    lo, hi = [v + 1.2 for v in lo], [v - 1.2 for v in hi]
    inside = [o.name for o, c, size in centres if max(size) < 30.0 and all(lo[i] < c[i] < hi[i] for i in range(3)) and o.name not in ACCEPTED]
    if inside:
        swallowed[w.name] = {"count": len(inside), "sample": inside[:8]}
report["inside_world_rock"] = swallowed
report["inside_world_rock_accepted"] = ACCEPTED
if swallowed:
    report["problems"].append(f"{sum(v['count'] for v in swallowed.values())} district objects lie inside world rock masses")

report["totals"] = {"objects": len(objs), "s3_objects": len(s3), "s2_objects": sum(1 for o in objs if o.get("cot_s2")),
                    "greybox_hidden": sum(1 for o in objs if o.get("cot_s3_superseded")), "mesh_datablocks": len(bpy.data.meshes),
                    "vertices_mesh_data": sum(len(m.vertices) for m in bpy.data.meshes),
                    "vertices_instanced": sum(len(o.data.vertices) for o in objs if o.type == "MESH"),
                    "cameras_s3": sum(1 for o in s3 if o.type == "CAMERA"), "materials": len(bpy.data.materials)}
h = hashlib.sha1("".join(f"{k}{v['digest']}" for k, v in sorted(report["regions"].items())).encode())
report["digest"] = h.hexdigest()[:16]
report["geometry_digest"] = hashlib.sha1("".join(f"{k}{v['geometry_digest']}" for k, v in sorted(report["regions"].items())).encode()).hexdigest()[:16]
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print("COT_S3_VALIDATE", json.dumps({"problems": report["problems"], "totals": report["totals"], "digest": report["digest"],
                                     "geometry_digest": report["geometry_digest"], "out": str(out_path)}, ensure_ascii=False))
