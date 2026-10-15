"""Straight-line passage test for the confirmed connections of docs/connections.csv on the saved structure file.

  blender -b --factory-startup scenes/city_structure.blend --python scripts/qa/check_connections.py

For every row with evidence A or B the two map points are turned into world X / Z and a ray is cast from one to the
other, 1.0 above the given height, at every depth from -22 to 58 in steps of 0.5. Only depths where the end points stand on a built floor
(an upward-facing surface just below them) are tested; a connection counts as open when at least one such depth lets the ray through. Rain, fog, lift cars and chains are ignored. This shows that an opening
exists on the line between the two regions; it does not replace looking at the check images.
"""
import csv
import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OX, OY, PPB = 3730.0, 3600.0, 15.0
IGNORE_NAME = ("COT_S2_Fog", "COT_S2_Glow", "COT_S2_Rain", "COT_Rain", "COT_S2_Streak")
IGNORE_ASSET = ("LiftCar", "LiftChain", "Chain", "LampString", "Banner", "RuneTablet", "CeilingFringe", "Stalactites", "Water")
dg = bpy.context.evaluated_depsgraph_get()
scene = bpy.context.scene


def cast(a, b):
    """First real obstacle between a and b, or None."""
    origin = Vector(a)
    total = (Vector(b) - origin).length
    direction = (Vector(b) - origin).normalized()
    travelled = 0.0
    for _ in range(40):
        hit, loc, nor, idx, obj, mat = scene.ray_cast(dg, origin, direction, distance=total - travelled)
        if not hit:
            return None
        asset = str(obj.get("cot_asset", ""))
        if obj.name.startswith(IGNORE_NAME) or any(k in asset for k in IGNORE_ASSET) or obj.type != "MESH":
            step = (loc - origin).length + 0.02
            travelled += step
            origin = origin + direction * step
            if travelled >= total:
                return None
            continue
        return obj.name
    return "too many ignored hits"


def floor_under(p, reach):
    hit, loc, nor, idx, obj, mat = scene.ray_cast(dg, Vector(p), Vector((0, 0, -1)), distance=reach)
    return bool(hit) and nor.z > 0.5 and not obj.name.startswith(IGNORE_NAME)


rows = list(csv.DictReader((ROOT / "docs" / "connections.csv").open(encoding="utf-8-sig")))
# links inside one region that a connection of the table depends on
rows.append({"从": "WestLowCorridor（长廊）", "到": "WestLowCorridor（下方小室）", "证据等级": "A", "总图位置_7600版": "1622,2190 → 1622,2300", "阶段3检测线_7600版": ""})
out = []
for r in rows:
    ev = r["证据等级"]
    pts = [p.strip() for p in (r.get("阶段3检测线_7600版") or r["总图位置_7600版"]).split("→")]
    (ax, ay), (bx, by) = [[float(v) for v in p.split(",")] for p in pts]
    pa = ((ax - OX) / PPB, (OY - ay) / PPB + 1.0)
    pb = ((bx - OX) / PPB, (OY - by) / PPB + 1.0)
    entry = {"from": r["从"], "to": r["到"], "evidence": ev, "map": r["总图位置_7600版"], "test_line": (r.get("阶段3检测线_7600版") or r["总图位置_7600版"]), "open_depths": [], "blockers": {}}
    if ev in ("A", "B"):
        y = -22.0
        vertical = abs(pa[0] - pb[0]) < abs(pa[1] - pb[1])
        lower = pa if pa[1] < pb[1] else pb
        while y <= 58.0:
            if vertical and abs(y) > 2.0:                  # shafts and floor openings lie on the shaft depth
                y += 0.5
                continue
            # only depths where the ends stand on a built floor count (not open air in front of a building, not the inside of a rock mass)
            ends = [] if vertical else [pa, pb]
            if not all(floor_under((e[0], y, e[1]), 3.0 if vertical else 2.2) for e in ends):
                entry["blockers"]["(no floor under an end point)"] = entry["blockers"].get("(no floor under an end point)", 0) + 1
                y += 0.5
                continue
            blocker = cast((pa[0], y, pa[1]), (pb[0], y, pb[1]))
            if blocker is None:
                entry["open_depths"].append(y)
            else:
                entry["blockers"][blocker] = entry["blockers"].get(blocker, 0) + 1
            y += 0.5
        entry["result"] = "open" if entry["open_depths"] else "blocked"
        entry["blockers"] = dict(sorted(entry["blockers"].items(), key=lambda kv: -kv[1])[:5])
        d = entry["open_depths"]
        entry["open_depths"] = [d[0], d[-1], len(d)] if d else []
    else:
        entry["result"] = "not built (unconfirmed)"
    out.append(entry)
    print("COT_CONN", entry["from"], "->", entry["to"], ev, entry["result"], entry["open_depths"], list(entry["blockers"])[:3] if entry["result"] == "blocked" else "")
target = ROOT / "docs" / "checks" / "stage_03_connections.json"
target.write_text(json.dumps({"file": bpy.data.filepath, "connections": out}, ensure_ascii=False, indent=1), encoding="utf-8")
print("COT_CONN_DONE", sum(1 for e in out if e["result"] == "open"), "open,", sum(1 for e in out if e["result"] == "blocked"), "blocked,",
      sum(1 for e in out if e["result"].startswith("not")), "unconfirmed")
