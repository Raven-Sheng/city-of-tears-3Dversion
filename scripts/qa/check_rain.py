"""Rain checks on the SAVED stage 4 file (never saves).

  blender -b --factory-startup scenes/city_art.blend --python scripts/qa/check_rain.py [-- --out JSON]

1. Rooms: no rain or drip column span overlaps a recorded room interior (cot_rooms boxes of the stage 3 stacks).
2. Shelter: at six heights inside every column span, a ray cast straight up must meet only cave rock / ceiling (or
   nothing) before the column top; a building, roof, deck or bridge above a rain point means rain under cover.
3. Motion: every rain / drip layer moves down by the same step each frame (linear, cyclic), so the streak pattern
   repeats seamlessly; the scrolled pattern never leaves the span it must cover.
Columns are read back from the saved meshes (vertex attributes cot_zlo / cot_zhi), not from the build's memory.
Result: docs/checks/stage_04_rain.json.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "build"))
import art_weather as AW  # noqa: E402

scene = bpy.context.scene
for cname in ("COT_REFERENCE", "COT_S2_OUTLINE", "COT_S4_RETIRED", "COT_S4_WEATHER", "COT_S4_FOG", "COT_S2_WEATHER"):
    c = bpy.data.collections.get(cname)
    if c is not None:
        c.hide_viewport = True
for o in bpy.data.objects:
    if o.hide_render and o.type in ("MESH", "CURVE", "FONT"):
        o.hide_viewport = True
bpy.context.view_layer.update()

layers = [o for o in bpy.data.objects if o.get("cot_weather") in ("rain", "drip")]
columns = []
for o in layers:
    me = o.data
    lo = me.attributes["cot_zlo"].data
    hi = me.attributes["cot_zhi"].data
    groups = defaultdict(list)
    for v, a, b in zip(me.vertices, lo, hi):
        groups[(round(a.value, 4), round(b.value, 4))].append(v.co)
    for (zlo, zhi), pts in groups.items():
        # one key may hold several columns with equal spans only by coincidence; split by xy clusters
        clusters = []                                    # [first point, sum, count]: a column is a thin prism, use its centre
        for p in pts:
            for c in clusters:
                if (c[0] - p.xy).length < 0.2:
                    c[1] += p.xy
                    c[2] += 1
                    break
            else:
                clusters.append([p.xy.copy(), p.xy.copy(), 1])
        for _first, s, n in clusters:
            xy = s / n
            columns.append({"layer": o.name, "kind": o["cot_weather"], "x": xy.x + o.location.x, "y": xy.y + o.location.y, "zlo": zlo, "zhi": zhi})

rooms = []
for w in bpy.data.objects:
    if w.get("cot_rooms"):
        for r in json.loads(w["cot_rooms"]):
            rooms.append((w.name, r))
room_hits = []
for c in columns:
    for name, (x0, x1, y0, y1, z0, z1) in rooms:
        # the lowest 0.3 m of a column is its landing on the surface below (same allowance as the builder): a drip that
        # lands on a room's roof slab, inside the nominal room box that includes the slab, is not rain in the room
        if x0 + 0.1 < c["x"] < x1 - 0.1 and y0 + 0.1 < c["y"] < y1 - 0.1 and c["zlo"] + 0.3 < z1 - 0.1 and c["zhi"] > z0 + 0.1:
            room_hits.append({"room": name, **{k: round(v, 2) if isinstance(v, float) else v for k, v in c.items()}})

C = AW.Caster(scene)
shelter = []
for c in columns:
    span = c["zhi"] - c["zlo"]
    for k in range(6):
        z = c["zlo"] + 0.5 + (span - 1.0) * k / 5.0
        hit = C.cast((c["x"], c["y"], z), (0, 0, 1))
        if hit is not None and hit[0].z < c["zhi"] - 0.5 and not AW._is_sky(hit[2]):
            shelter.append({"layer": c["layer"], "x": round(c["x"], 2), "y": round(c["y"], 2), "z": round(z, 2), "covered_by": hit[2].name if hit[2] else "",
                            "cover_z": round(hit[0].z, 2)})
            break

motion = {}
for o in layers:
    # the weather layers are hidden for the ray casts, so read the animation curve itself (modifiers included)
    action = o.animation_data.action
    curves = []
    try:
        curves = list(action.fcurves)
    except AttributeError:
        for lay in action.layers:
            for strip in lay.strips:
                for bag in strip.channelbags:
                    curves += list(bag.fcurves)
    fc = next(c for c in curves if c.data_path == "location" and c.array_index == 2)
    zs = [fc.evaluate(f) for f in range(1, 74)]
    steps = [b - a for a, b in zip(zs, zs[1:])]
    period = o.modifiers["PeriodRepeat"].constant_offset_displace[2]
    wraps = [s for s in steps if s > 0]
    plain = [s for s in steps if s <= 0]
    motion[o.name] = {"step_min": round(min(plain), 4), "step_max": round(max(plain), 4), "wraps": len(wraps),
                      "wrap_step_minus_period": [round(s - period, 4) for s in wraps][:4], "copies": o.modifiers["PeriodRepeat"].count}
scene.frame_set(1)
ok = not room_hits and not shelter
out = {"file": bpy.data.filepath, "layers": [o.name for o in layers], "columns": len(columns), "rooms_checked": len(rooms),
       "room_overlaps": room_hits[:50], "room_overlap_count": len(room_hits), "covered_points": shelter[:50], "covered_count": len(shelter),
       "rays": C.n, "motion": motion, "pass": ok}
(ROOT / sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else ROOT / "docs" / "checks" / "stage_04_rain.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("COT_RAIN_CHECK", json.dumps({k: out[k] for k in ("columns", "rooms_checked", "room_overlap_count", "covered_count", "rays", "pass")}))
print("COT_RAIN_MOTION", json.dumps(motion))
