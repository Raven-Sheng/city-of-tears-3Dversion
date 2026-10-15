"""Clay check renders of the stage 3 structure from the SAVED file (never saves the .blend).

  blender -b --factory-startup scenes/city_structure.blend --python scripts/render_structure.py -- \
      [--regions A,B] [--cams NAME,NAME] [--out DIR] [--scale 1.0] [--show-greybox]

Every CAM_S3_* camera carries cot_res and cot_hide (layer names: FRONT, CEILING, ROCK, BACKDROP). Weather, lights
helpers, contour hulls and reference labels are hidden; Workbench solid shading shows structure only.
Images go to renders/previews/stage03/<region>/<camera>.png with a manifest per region.
"""
import json
import sys
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


regions = arg("--regions")
regions = set(regions.split(",")) if regions else None
names = arg("--cams")
names = set(names.split(",")) if names else None
out_root = Path(arg("--out", "renders/previews/stage03"))
out_root = out_root if out_root.is_absolute() else ROOT / out_root
scale = float(arg("--scale", "1.0"))

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading
sh.light = "STUDIO"
sh.color_type = "MATERIAL"
sh.show_cavity = True
sh.cavity_type = "BOTH"
sh.show_shadows = True
sh.shadow_intensity = 0.3
sh.show_object_outline = True
sh.object_outline_color = (0.0, 0.0, 0.0)
scene.display.render_aa = "8"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = 0.0
scene.world.color = (0.16, 0.2, 0.27)
scene.render.use_compositing = False
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_percentage = 100
scene.render.film_transparent = False

for cname in ("COT_S2_WEATHER", "COT_S2_OUTLINE", "COT_REFERENCE"):
    coll = bpy.data.collections.get(cname)
    if coll is not None:
        coll.hide_render = True
for obj in bpy.data.objects:                              # fog / haze domains draw as solid boxes in Workbench
    if obj.name.startswith(("COT_S2_Fog", "COT_S2_Glow")):
        obj.hide_render = True

layer_colls = {}
for coll in bpy.data.collections:
    if coll.name.startswith("COT_L_"):
        layer_colls.setdefault(coll.name[len("COT_L_"):], []).append(coll)
    elif coll.name.startswith("COT_S3_"):
        tail = coll.name.rsplit("_", 1)[-1]
        if tail in ("FRONT", "CEILING", "ROCK", "BACKDROP", "CAVESHELL", "CHARS"):
            layer_colls.setdefault(tail, []).append(coll)
# stage 2 sample towers behind and in front of the plaza belong to the far layers (the master draws them blurred);
# they hide with the BACKDROP layer so that section views compare the sharp near layers with the master
S2_FAR = [o for o in bpy.data.objects if o.get("cot_s2") and o.name.startswith(("COT_BackTower_", "COT_FarTower_", "COT_FrontTower_"))]
S2_FAR_RENDER = {o.name: o.hide_render for o in S2_FAR}
ALIAS = {"ROCK": ("ROCK", "HOSTROCK"), "BACKDROP": ("BACKDROP", "FOREGROUND"), "CEILING": ("CEILING",), "FRONT": ("FRONT",), "CAVESHELL": ("CAVESHELL",), "CHARS": ("CHARS",)}

cams = sorted((o for o in bpy.data.objects if o.type == "CAMERA" and o.get("cot_s3")), key=lambda o: o.name)
done = {}
for cam in cams:
    rid = cam.get("cot_region", "")
    if regions is not None and rid not in regions:
        continue
    if names is not None and cam.name not in names:
        continue
    hidden = [h for h in cam.get("cot_hide", "").split(",") if h]
    hide_keys = set()
    for h in hidden:
        hide_keys.update(ALIAS.get(h, (h,)))
    for key, colls in layer_colls.items():
        for coll in colls:
            coll.hide_render = key in hide_keys
    for o in S2_FAR:
        o.hide_render = S2_FAR_RENDER[o.name] or ("BACKDROP" in hide_keys)
    scene.camera = cam
    rx, ry = (int(v) for v in cam["cot_res"])
    scene.render.resolution_x, scene.render.resolution_y = int(rx * scale), int(ry * scale)
    out_dir = out_root / rid
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{cam.name}.png"
    scene.render.filepath = str(target)
    t0 = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    done.setdefault(rid, []).append({"camera": cam.name, "file": target.name, "kind": cam.get("cot_kind", ""), "hidden_layers": hidden,
                                     "purpose": cam.get("cot_purpose", ""), "ref": cam.get("cot_ref", ""),
                                     "map_box": list(cam["cot_map_box"]) if "cot_map_box" in cam else None,
                                     "resolution": [scene.render.resolution_x, scene.render.resolution_y], "type": cam.data.type,
                                     "seconds": round(time.perf_counter() - t0, 2), "exists": target.is_file()})
    print("COT_S3_RENDER", target)

for rid, entries in done.items():
    path = out_root / rid / "render_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"renders": []}
    keep = [r for r in manifest.get("renders", []) if r["camera"] not in {e["camera"] for e in entries}]
    manifest = {"blend": bpy.data.filepath, "blender": bpy.app.version_string, "engine": "BLENDER_WORKBENCH", "renders": sorted(keep + entries, key=lambda r: r["camera"])}
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
print("COT_S3_RENDER_DONE", sum(len(v) for v in done.values()))
