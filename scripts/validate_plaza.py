"""Independent reload check of the saved plaza sample (run in its own Blender process; never saves).

  blender -b --factory-startup <sample.blend> --python scripts/validate_plaza.py -- [--out logs/validate_plaza.json]

Checks that the file really loads, that stage 2 data is local and editable, that nothing is missing,
and writes a digest of the generated geometry so two builds can be compared.
"""
import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else ROOT / "logs" / "validate_plaza.json"
scene = bpy.context.scene
s2 = [o for o in bpy.data.objects if o.get("cot_s2")]
digest = hashlib.sha256()
for obj in sorted(s2, key=lambda o: o.name):
    digest.update(obj.name.encode())
    digest.update(repr([round(v, 4) for row in obj.matrix_world for v in row]).encode())
    if obj.type == "MESH":
        me = obj.data
        co = [0.0] * (len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        digest.update(repr((len(me.vertices), len(me.polygons), round(sum(co), 3), round(sum(abs(c) for c in co), 3))).encode())
    elif obj.type == "CURVE":
        digest.update(repr([(len(sp.bezier_points), len(sp.points)) for sp in obj.data.splines]).encode())
cams = [o for o in s2 if o.type == "CAMERA"]
film = bpy.data.objects.get("CAM_FILM_S2")
positions = []
if film is not None:
    for f in (1, 60, 120, 180, 240):
        scene.frame_set(f)
        positions.append([round(v, 3) for v in film.matrix_world.translation])
rain = [o for o in s2 if o.name.startswith("COT_Rain_Layer")]
rain_z = []
if rain:
    for f in (1, 2, 3):
        scene.frame_set(f)
        rain_z.append(round(rain[0].matrix_world.translation.z, 3))
report = {
    "file": bpy.data.filepath, "blender": bpy.app.version_string, "scene": scene.name, "stage": scene.get("cot_stage"),
    "objects_total": len(bpy.data.objects), "s2_objects": len(s2),
    "s2_by_type": {t: sum(1 for o in s2 if o.type == t) for t in sorted({o.type for o in s2})},
    "s2_mesh_vertices": sum(len(o.data.vertices) for o in s2 if o.type == "MESH"),
    "greybox_objects": sum(1 for o in bpy.data.objects if o.get("cot_generated") and not o.get("cot_s2")),
    "superseded_hidden": sum(1 for o in bpy.data.objects if o.get("cot_s2_superseded")),
    "manual_objects": [o.name for o in bpy.data.objects if not o.get("cot_s2") and not o.get("cot_generated")],
    "libraries_linked": [lib.filepath for lib in bpy.data.libraries],
    "images": [img.filepath for img in bpy.data.images if img.source == "FILE"],
    "missing_images": [img.filepath for img in bpy.data.images if img.source == "FILE" and not Path(bpy.path.abspath(img.filepath)).exists()],
    "objects_without_material": [o.name for o in s2 if o.type in ("MESH", "CURVE") and not any(s.material for s in o.material_slots)],
    "non_local_data": [o.name for o in s2 if o.data is not None and o.data.library is not None],
    "cameras": sorted(o.name for o in cams), "scene_camera": scene.camera.name if scene.camera else None,
    "film_camera_positions_f1_60_120_180_240": positions,
    "rain_layer0_z_f1_f2_f3": rain_z, "rain_step_per_frame": round(rain_z[0] - rain_z[1], 3) if len(rain_z) > 1 else None,
    "frame_range": [scene.frame_start, scene.frame_end], "fps": scene.render.fps,
    "view_transform": scene.view_settings.view_transform, "look": scene.view_settings.look, "exposure": scene.view_settings.exposure,
    "compositor": scene.compositing_node_group.name if getattr(scene, "compositing_node_group", None) else None,
    "collections_s2": sorted(c.name for c in bpy.data.collections if c.name.startswith("COT_S2")),
    "assets": sorted({o.get("cot_asset") for o in s2 if o.get("cot_asset")}),
    "evidence_counts": {k: sum(1 for o in s2 if o.get("cot_evidence") == k) for k in ("A", "B", "C")},
    "geometry_digest": digest.hexdigest()[:16],
}
problems = []
if report["missing_images"]:
    problems.append("missing images")
if report["libraries_linked"]:
    problems.append("linked libraries present")
if report["objects_without_material"]:
    problems.append("objects without material")
if film is None or len({tuple(p) for p in positions}) < 5:
    problems.append("film camera not animated")
if report["rain_step_per_frame"] in (None, 0.0):
    problems.append("rain not animated")
report["problems"] = problems
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print("COT_VALIDATE", json.dumps(report, ensure_ascii=False)[:1800])
