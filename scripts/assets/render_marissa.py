"""Check renders of the Marissa asset, from the saved .blend in its own Blender process.

  "D:\\Blender\\blender.exe" -b --factory-startup <blend> --python scripts/assets/render_marissa.py -- --out DIR
        [--modes lit,clay,body,wings] [--cams CAM_A,CAM_B] [--samples 96]

lit   : Cycles, look-dev lights, ink contours on
clay  : Workbench solid grey, contours hidden (form check without colour or ink)
body  : lit, wings and their contours hidden (what the wings cover: back of the head, hair, thorax, wing base)
wings : lit, body hidden (the four wings and their veins alone)
Writes <out>/<mode>_<camera>.png, <out>/render_manifest.json and, when the reference view was rendered,
<out>/compare_RefFront.png (the drawing | lit | clay, same scale).
"""
import json
import sys
import time
from pathlib import Path

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default


ROOT = Path(bpy.data.filepath).resolve().parents[3]
OUT = Path(arg("--out", "renders/previews/marissa")).resolve()
MODES = arg("--modes", "lit,clay,body,wings").split(",")
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


def wing_inks(flag):
    for o in bpy.data.collections["MAR_Ink"].objects:
        if o.get("cot_ink_of", "").startswith("MAR_Wing"):
            o.hide_render = not flag


def body_inks(flag):
    for o in bpy.data.collections["MAR_Ink"].objects:
        if not o.get("cot_ink_of", "").startswith("MAR_Wing"):
            o.hide_render = not flag


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

if any(m in MODES for m in ("lit", "body", "wings")):
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

if "body" in MODES:
    coll_visible("MAR_Wings", False)
    wing_inks(False)
    for cam in cams:
        if cam.name in ("CAM_MAR_RefFront", "CAM_MAR_ThreeQuarter", "CAM_MAR_SideRight", "CAM_MAR_Back", "CAM_MAR_Portrait"):
            manifest["renders"].append(render("body", cam))
    coll_visible("MAR_Wings", True)
    wing_inks(True)

if "wings" in MODES:
    coll_visible("MAR_Body", False)
    body_inks(False)
    for cam in cams:
        if cam.name in ("CAM_MAR_RefFront", "CAM_MAR_ThreeQuarter", "CAM_MAR_SideRight", "CAM_MAR_Back", "CAM_MAR_Top"):
            manifest["renders"].append(render("wings", cam))
    coll_visible("MAR_Body", True)
    body_inks(True)

if "clay" in MODES:
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "SINGLE"
    shading.single_color = (0.62, 0.62, 0.64)
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    shading.show_object_outline = False
    coll_visible("MAR_Ink", False)
    for cam in cams:
        manifest["renders"].append(render("clay", cam))
    coll_visible("MAR_Ink", True)

# side-by-side with the drawing at the same scale (the reference camera frames the whole drawing canvas)
lit, clay = OUT / "lit_CAM_MAR_RefFront.png", OUT / "clay_CAM_MAR_RefFront.png"
ref = ROOT / "Character" / "Marissa" / "Marissa.png"
if lit.exists() and ref.exists():
    import numpy as np
    import OpenImageIO as oiio

    def load(path, w, h):
        buf = oiio.ImageBuf(str(path))
        spec = buf.spec()
        px = np.asarray(buf.get_pixels(oiio.FLOAT))
        if px.shape[2] == 4:
            a = px[..., 3:4]
            px = px[..., :3] * a + np.array([0.012, 0.018, 0.045]) ** (1 / 2.2) * (1 - a)
        px = px[..., :3]
        if (spec.width, spec.height) != (w, h):
            tmp = oiio.ImageBuf(oiio.ImageSpec(spec.width, spec.height, 3, oiio.FLOAT))
            tmp.set_pixels(oiio.ROI(0, spec.width, 0, spec.height), np.ascontiguousarray(px.astype(np.float32)))
            tmp = oiio.ImageBufAlgo.resize(tmp, roi=oiio.ROI(0, w, 0, h, 0, 1, 0, 3))
            px = np.asarray(tmp.get_pixels(oiio.FLOAT))[..., :3]
        return px

    W, H = 606, 1134
    panels = [load(ref, W, H), load(lit, W, H)] + ([load(clay, W, H)] if clay.exists() else [])
    gap = np.ones((H, 12, 3), np.float32) * 0.5
    sheet = panels[0]
    for p in panels[1:]:
        sheet = np.concatenate([sheet, gap, p], axis=1)
    out = oiio.ImageBuf(oiio.ImageSpec(sheet.shape[1], H, 3, oiio.FLOAT))
    out.set_pixels(oiio.ROI(0, sheet.shape[1], 0, H), np.ascontiguousarray(sheet.astype(np.float32)))
    out.write(str(OUT / "compare_RefFront.png"), oiio.UINT8)
    manifest["compare"] = "compare_RefFront.png"

(OUT / "render_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("COT_DONE", len(manifest["renders"]))
