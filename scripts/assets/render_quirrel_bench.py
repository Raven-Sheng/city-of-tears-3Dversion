"""Check renders of the Quirrel + bench asset, from the saved .blend in its own Blender process.

  "D:\\Blender\\blender.exe" -b --factory-startup <blend> --python scripts/assets/render_quirrel_bench.py -- --out DIR
        [--modes lit,clay,solo] [--cams CAM_A,CAM_B] [--samples 96]

lit  : Cycles, look-dev lights, ink contours on
clay : Workbench solid grey, contours hidden (form check without colour or ink)
solo : lit, Quirrel alone and the bench alone (each asset hidden in turn) from the three-quarter and back views
bench / benchclay : the bench alone (Quirrel hidden) from every camera, lit / clay
Writes <out>/<mode>_<camera>.png and <out>/render_manifest.json.
"""
import json
import sys
import time
from pathlib import Path

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default


OUT = Path(arg("--out", "renders/previews/quirrel_bench")).resolve()
MODES = arg("--modes", "lit,clay,solo").split(",")
SAMPLES = int(arg("--samples", "96"))
scene = bpy.context.scene
cams = sorted((o for o in bpy.data.objects if o.type == "CAMERA" and o.get("cot_res")), key=lambda o: o.name)
want = arg("--cams", "")
if want:
    cams = [c for c in cams if c.name in want.split(",")]
OUT.mkdir(parents=True, exist_ok=True)


def use_gpu():
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for device_type in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = device_type
        except TypeError:
            continue
        prefs.refresh_devices()
        if any(d.type != "CPU" for d in prefs.get_devices_for_type(device_type)):
            for d in prefs.devices:
                d.use = d.type != "CPU"
            return device_type
    return None


def coll_visible(name, flag):
    coll = bpy.data.collections[name]
    coll.hide_render = not flag
    coll.hide_viewport = not flag


def render(tag, cam):
    scene.camera = cam
    w, h = cam["cot_res"]
    scene.render.resolution_x, scene.render.resolution_y = int(w), int(h)
    scene.render.resolution_percentage = 100
    path = OUT / f"{tag}_{cam.name}.png"
    scene.render.filepath = str(path)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print("COT_RENDER", path, round(time.time() - t0, 1), "s")
    return {"file": path.name, "camera": cam.name, "mode": tag, "seconds": round(time.time() - t0, 1)}


manifest = {"blend": bpy.data.filepath, "blender": bpy.app.version_string, "renders": []}
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
device = None

if "lit" in MODES or "solo" in MODES or "bench" in MODES:
    scene.render.engine = "CYCLES"
    device = use_gpu()
    cy = scene.cycles
    cy.device = "GPU" if device else "CPU"
    cy.samples = SAMPLES
    cy.use_denoising = True
    cy.transparent_max_bounces = 16
    manifest["cycles"] = {"device": device or "CPU", "samples": SAMPLES}

if "lit" in MODES:
    for cam in cams:
        manifest["renders"].append(render("lit", cam))

if "bench" in MODES:
    coll_visible("QRL_Quirrel", False)
    for cam in cams:
        manifest["renders"].append(render("bench", cam))
    coll_visible("QRL_Quirrel", True)

if "solo" in MODES:
    for cam in [c for c in cams if c.name in ("CAM_QB_ThreeQuarter", "CAM_QB_Back", "CAM_QB_SideRight")]:
        coll_visible("QB_Bench", False)
        manifest["renders"].append(render("soloQuirrel", cam))
        coll_visible("QB_Bench", True)
        coll_visible("QRL_Quirrel", False)
        manifest["renders"].append(render("soloBench", cam))
        coll_visible("QRL_Quirrel", True)

if "clay" in MODES or "benchclay" in MODES:
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "SINGLE"
    shading.single_color = (0.62, 0.62, 0.64)
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    shading.show_object_outline = False
    coll_visible("QRL_Ink", False)
    if "clay" in MODES:
        for cam in cams:
            manifest["renders"].append(render("clay", cam))
    if "benchclay" in MODES:
        coll_visible("QRL_Quirrel", False)
        for cam in cams:
            manifest["renders"].append(render("benchclay", cam))
        coll_visible("QRL_Quirrel", True)
    coll_visible("QRL_Ink", True)

(OUT / "render_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("COT_DONE", len(manifest["renders"]))
