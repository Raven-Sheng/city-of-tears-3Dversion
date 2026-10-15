"""Render check views / stills / frame ranges from the SAVED plaza sample (never saves the .blend).

  blender -b --factory-startup scenes/plaza_sample.blend --python scripts/render_plaza.py -- \
      --cams CAM_A,CAM_B --mode clay|dry|final --engine CYCLES|EEVEE [--res 1920x1080] [--samples N]
      [--out DIR] [--frame F] [--anim F0 F1 [--resume]] [--tag NAME] [--view AgX|Standard] [--exposure E] [--look LOOK]

  clay : Workbench solid shading, weather hidden (greybox-style structure check, no rain / fog / lighting)
  dry  : full materials and lights, rain and fog hidden
  final: everything
A manifest with measured render times is written next to the images (render_manifest.json, appended).
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None, count=1):
    if name not in argv:
        return default
    i = argv.index(name)
    return argv[i + 1] if count == 1 else argv[i + 1:i + 1 + count]


cams = arg("--cams", "CAM_REF_Statue").split(",")
mode = arg("--mode", "final")
engine = arg("--engine", "CYCLES")
res = [int(v) for v in arg("--res", "1920x1080").split("x")]
samples = int(arg("--samples", "96"))
out_dir = Path(arg("--out", "renders/previews/stage02"))
out_dir = out_dir if out_dir.is_absolute() else ROOT / out_dir
out_dir.mkdir(parents=True, exist_ok=True)
frame = int(arg("--frame", "1"))
anim = arg("--anim", None, 2)
tag = arg("--tag", mode)
view = arg("--view", None)          # default: what the sample file stores (config/plaza.json look)
exposure = arg("--exposure", None)
look = arg("--look", None)

scene = bpy.context.scene
scene.render.resolution_x, scene.render.resolution_y = res
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.use_motion_blur = False

weather = bpy.data.collections.get("COT_S2_WEATHER")
lights = bpy.data.collections.get("COT_S2_LIGHTS")
layers = {c.name[len("COT_L_"):]: c for c in bpy.data.collections if c.name.startswith("COT_L_")}
info = {"engine": engine, "mode": mode}

if mode == "clay":
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
    info["engine"] = "BLENDER_WORKBENCH"
else:
    if view is not None:
        scene.view_settings.view_transform = view
    if look is not None:
        try:
            scene.view_settings.look = look
        except TypeError:
            info["look_error"] = look
    if exposure is not None:
        scene.view_settings.exposure = float(exposure)
    if engine == "CYCLES":
        scene.render.engine = "CYCLES"
        prefs = bpy.context.preferences.addons["cycles"].preferences
        chosen = None
        for device_type in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = device_type
            except TypeError:
                continue
            prefs.refresh_devices()
            if any(d.type != "CPU" for d in prefs.get_devices_for_type(device_type)):
                for d in prefs.devices:
                    d.use = d.type != "CPU"
                chosen = device_type
                break
        scene.cycles.device = "GPU" if chosen else "CPU"
        scene.cycles.samples = samples
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.02
        scene.cycles.use_denoising = True
        try:
            scene.cycles.denoiser = "OPTIX" if chosen == "OPTIX" else "OPENIMAGEDENOISE"
        except TypeError:
            pass
        scene.cycles.max_bounces = 6
        scene.cycles.diffuse_bounces = 2
        scene.cycles.glossy_bounces = 3
        scene.cycles.transparent_max_bounces = 12
        scene.cycles.volume_bounces = 0
        scene.cycles.caustics_reflective = False
        scene.cycles.caustics_refractive = False
        scene.cycles.sample_clamp_indirect = 6.0
        info.update(device=chosen or "CPU", samples=samples, denoiser=scene.cycles.denoiser, adaptive_threshold=0.02)
    else:
        scene.render.engine = "BLENDER_EEVEE"
        ee = scene.eevee
        for key, value in (("taa_render_samples", samples), ("use_raytracing", True), ("volumetric_tile_size", "4"),
                           ("volumetric_samples", 128), ("volumetric_end", 420.0), ("volumetric_start", 0.5),
                           ("use_volumetric_shadows", True), ("volumetric_shadow_samples", 32), ("use_shadows", True),
                           ("shadow_ray_count", 2), ("shadow_step_count", 8)):
            try:
                setattr(ee, key, value)
            except (AttributeError, TypeError) as exc:
                info.setdefault("eevee_unset", []).append(f"{key}: {exc.__class__.__name__}")
        info.update(samples=samples)

if weather is not None:
    weather.hide_render = mode in ("clay", "dry")
outline = bpy.data.collections.get("COT_S2_OUTLINE")
if outline is not None:                    # the contour hull only works with the lit material; Workbench would draw it solid
    outline.hide_render = mode == "clay" or "--no-outline" in argv

manifest_path = out_dir / "render_manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"renders": []}
manifest["blend"] = bpy.data.filepath
manifest["blender"] = bpy.app.version_string


def gpu_memory():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10)
        return int(out.stdout.strip().splitlines()[0])
    except Exception:
        return None


for name in cams:
    cam = bpy.data.objects[name]
    scene.camera = cam
    hide = []
    if name == "CAM_S2_Top":
        hide = ["CEILING", "HOSTROCK", "CAVESHELL"]
    for key, coll in layers.items():
        coll.hide_render = key in hide
    if anim:
        f0, f1 = int(anim[0]), int(anim[1])
        seq_dir = out_dir / f"{name}_{tag}"
        seq_dir.mkdir(exist_ok=True)
        scene.frame_start, scene.frame_end = f0, f1
        scene.render.filepath = str(seq_dir / "f####")
        existing = len(list(seq_dir.glob("f*.png")))
        if "--resume" in argv:            # keep frames already on disk, render only the missing ones
            scene.render.use_overwrite = False
        started = time.perf_counter()
        bpy.ops.render.render(animation=True)
        seconds = time.perf_counter() - started
        entry = dict(info, camera=name, tag=tag, frames=[f0, f1], dir=seq_dir.name, resolution=res, seconds=round(seconds, 1),
                     seconds_per_frame=round(seconds / max(1, (f1 - f0 + 1) - (existing if "--resume" in argv else 0)), 2),
                     frames_rendered_this_run=(f1 - f0 + 1) - (existing if "--resume" in argv else 0), files=len(list(seq_dir.glob("f*.png"))),
                     view_transform=scene.view_settings.view_transform, exposure=scene.view_settings.exposure, gpu_mem_after_mib=gpu_memory())
    else:
        scene.frame_set(frame)
        target = out_dir / f"{name}__{tag}.png"
        scene.render.filepath = str(target)
        started = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        seconds = time.perf_counter() - started
        entry = dict(info, camera=name, tag=tag, frame=scene.frame_current, file=target.name, resolution=res, seconds=round(seconds, 2),
                     view_transform=scene.view_settings.view_transform, exposure=scene.view_settings.exposure, exists=target.is_file(),
                     gpu_mem_after_mib=gpu_memory())
    manifest["renders"] = [r for r in manifest["renders"] if not (r.get("camera") == name and r.get("tag") == tag)] + [entry]
    print("COT_RENDER", json.dumps(entry))
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
