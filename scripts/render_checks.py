"""Render the greybox check views from the SAVED master file.

Run from the project root (a separate Blender process from the build):
  blender -b --factory-startup scenes/city_master.blend --python scripts/render_checks.py -- [--only CAM_A,CAM_B] [--out DIR]

Every camera in COT_CAMERAS that carries cot_res is rendered with the layer visibility
stored on it. Nothing is saved back to the .blend. A manifest is written next to the images.
"""
import json
import sys
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
out_dir = Path(argv[argv.index("--out") + 1]) if "--out" in argv else ROOT / "renders" / "previews" / "stage01"
if not out_dir.is_absolute():
    out_dir = ROOT / out_dir
out_dir.mkdir(parents=True, exist_ok=True)

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
shading = scene.display.shading
shading.light = "STUDIO"
shading.color_type = "MATERIAL"
shading.show_cavity = True
shading.cavity_type = "BOTH"
shading.show_shadows = False
shading.show_object_outline = True
shading.object_outline_color = (0.0, 0.0, 0.0)
scene.display.render_aa = "8"
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_percentage = 100
scene.render.film_transparent = False

layers = {c.name[len("COT_L_"):]: c for c in bpy.data.collections if c.name.startswith("COT_L_")}
reference = bpy.data.collections.get("COT_REFERENCE")
manifest = {"blend": bpy.data.filepath, "blender": bpy.app.version_string, "engine": scene.render.engine, "renders": []}

cameras = sorted((o for o in bpy.data.objects if o.type == "CAMERA" and "cot_res" in o), key=lambda o: o.name)
for cam in cameras:
    if only is not None and cam.name not in only:
        continue
    hidden = [h for h in cam.get("cot_hide", "").split(",") if h]
    for name, coll in layers.items():
        coll.hide_render = name in hidden
    if reference is not None:
        reference.hide_render = not bool(cam.get("cot_show_reference", False))
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = (int(v) for v in cam["cot_res"])
    target = out_dir / f"{cam.name}.png"
    scene.render.filepath = str(target)
    started = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    manifest["renders"].append({
        "camera": cam.name, "file": target.name, "type": cam.data.type, "hidden_layers": hidden,
        "reference_shown": bool(cam.get("cot_show_reference", False)),
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "purpose": cam.get("cot_purpose", ""), "seconds": round(time.perf_counter() - started, 2),
        "exists": target.is_file(), "bytes": target.stat().st_size if target.is_file() else 0})

manifest_path = out_dir / "render_manifest.json"
previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() and only is not None else None
if previous is not None:
    done = {r["camera"] for r in manifest["renders"]}
    manifest["renders"] = [r for r in previous.get("renders", []) if r["camera"] not in done] + manifest["renders"]
    manifest["renders"].sort(key=lambda r: r["camera"])
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("COT_RENDER_CHECKS", len(manifest["renders"]), "views ->", out_dir)
