"""Overlap test for the shell towers, roof spires and ribs of the saved structure file.

  blender -b --factory-startup scenes/city_structure.blend --python scripts/qa/check_overlaps.py

Each tested object (stage 2 sample towers, stage 3 tower bodies, roof spires, corbel ribs) is checked with a BVH
overlap against every other visible stage 3 mesh whose bounding box touches it. Contacts with the ground, the cavern
floor, well beds and water are expected (the towers stand on them) and are listed separately. The remaining
contacts are written to docs/checks/stage_03_overlaps.json for review; a contact with rock or a roof the object
stands on is acceptable, a tower passing through a room is not.
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
dg = bpy.context.evaluated_depsgraph_get()


def bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


_TREES = {}


def tree(o):
    if o.name in _TREES:
        return _TREES[o.name]
    _TREES[o.name] = _tree(o)
    return _TREES[o.name]


def _tree(o):
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    verts = [o.matrix_world @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys)


S2_TOWERS = ("COT_FreeTower_Body", "COT_EastTower_Body", "COT_BackTower_A_Body", "COT_BackTower_B_Body", "COT_FarTower_C_Body",
             "COT_FarTower_E_Body", "COT_FarTower_F_Body", "COT_FrontTower_A_Body", "COT_FrontTower_B_Body", "COT_FrontTower_C_Body")
import sys
PROPS = "--props" in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
if PROPS:      # furniture, portraits, floating platforms and creatures of the rework (D-347, D-348)
    targets = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render and o.get("cot_s3") and
               (o.get("cot_character") or o.get("cot_asset") in ("Furniture", "NoblePortrait", "PillPlatform"))]
else:
    targets = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render and (
        (o.get("cot_s2") and o.name in S2_TOWERS) or
        (o.get("cot_s3") and (o.get("cot_asset") in ("CorbelRibs", "RoofSpire") or (o.name.endswith("_Body") and "Tower" in o.name))))]
others = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render and o.get("cot_s3") and len(o.data.polygons) > 0]
boxes = {o.name: bbox(o) for o in others}
GROUND = ("S3__World_BackFloor", "S3__World_GroundBase", "S3__World_FrontFloor", "S3__World_BackWall", "S3__World_FrontWall")
ground, contacts = [], []
for t in targets:
    lo, hi = bbox(t)
    tt = None
    for o in others:
        if o is t or (not PROPS and o.get("cot_region") == t.get("cot_region") and not t.get("cot_s2")):
            continue
        if PROPS and o in targets and o.name < t.name:                # each prop pair once
            continue
        a, b = boxes[o.name]
        if any(b[i] < lo[i] or a[i] > hi[i] for i in range(3)):
            continue
        tt = tt or tree(t)
        if tt.overlap(tree(o)):
            pair = (t.name, o.name)
            if o.name in GROUND or o.name.endswith(("_Bed", "_Water", "WaterBack", "ChannelWater", "_Ground")):
                ground.append(pair)
            else:
                contacts.append(pair)
out = {"file": bpy.data.filepath, "tested": len(targets), "ground_contacts": ground, "other_contacts": contacts}
(ROOT / "docs" / "checks" / ("stage_03_overlaps_props.json" if PROPS else "stage_03_overlaps.json")).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("COT_OVERLAPS", len(targets), "tested;", len(ground), "ground contacts;", len(contacts), "other contacts")
for c in contacts:
    print("COT_OVERLAP", c[0], c[1])
