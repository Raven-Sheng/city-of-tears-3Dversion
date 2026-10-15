"""Stage 4 renders (stills or frame ranges) from a SAVED city file; never saves the .blend.

  blender -b --factory-startup scenes/city_art.blend --python scripts/render/render_art.py -- \
      --cams CAM_A,CAM_B | --regions A,B [--kinds ref,interior]  --mode final|dry|clay
      [--samples 64] [--scale 0.5 | --res 1280x720] [--out renders/previews/stage04] [--tag NAME]
      [--frame F] [--anim F0 F1 [--resume]] [--noise-threshold 0.02] [--no-denoise]

  final: materials, lights, rain, drips, ripples, volumes and depth haze
  dry  : materials and lights; every weather / fog element switched off with the stage 4 switch (scene cot_weather = 0)
  clay : Workbench solid shading, weather off (structure check)
Per camera the stage 3 layer hides (cot_hide: FRONT, CEILING, ROCK, BACKDROP, CAVESHELL, CHARS) are applied, as in the
clay checks. Output: <out>/<region>/<camera>__<tag>.png (stills) or <out>/<region>/<camera>__<tag>/f####.png (ranges);
a manifest per output folder records settings, seconds and the Cycles peak memory reported by the renderer.
"""
import json
import hashlib
import re
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
sys.path.insert(0, str(ROOT / "scripts" / "render"))
from render_identity import bind_sequence
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None, count=1):
    if name not in argv:
        return default
    i = argv.index(name)
    return argv[i + 1] if count == 1 else argv[i + 1:i + 1 + count]


try:
    import art_switch                                         # present once the stage 4 file exists
except ImportError:
    art_switch = None

mode = arg("--mode", "final")
tag = arg("--tag", mode)
samples = int(arg("--samples", "64"))
scale = float(arg("--scale", "1.0"))
res_fixed = [int(v) for v in arg("--res").split("x")] if arg("--res") else None
out_root = Path(arg("--out", "renders/previews/stage04"))
out_root = out_root if out_root.is_absolute() else ROOT / out_root
frame = int(arg("--frame", "1"))
anim = arg("--anim", None, 2)
noise = float(arg("--noise-threshold", "0.02"))
profile_path = Path(arg('--profile')) if arg('--profile') else None
if profile_path is not None and not profile_path.is_absolute():
    profile_path = ROOT / profile_path
profile = json.loads(profile_path.read_text(encoding='utf-8')) if profile_path else {}
if profile:
    samples = int(profile['samples'])
    noise = float(profile['adaptive_threshold'])
    if not (1 <= int(profile['adaptive_min_samples']) <= samples):
        raise ValueError('Adaptive minimum must be within the sample budget')

scene = bpy.context.scene
cams = []
if arg("--set"):                                              # --set reference [--regions A,B]: fixed views from config/art.json
    ref = json.loads((ROOT / "config" / "art.json").read_text(encoding="utf-8"))["reference_cameras"]
    only = set(arg("--regions").split(",")) if arg("--regions") else None
    for rid, names in ref.items():
        if rid == "note" or (only is not None and rid not in only):
            continue
        for n in names:
            if n not in bpy.data.objects:
                raise SystemExit(f"COT_RENDER_ERROR no camera {n}")
            cams.append(bpy.data.objects[n])
elif arg("--cams"):
    for n in arg("--cams").split(","):
        if n not in bpy.data.objects:
            raise SystemExit(f"COT_RENDER_ERROR no camera {n}")
        cams.append(bpy.data.objects[n])
else:
    regions = set(arg("--regions", "").split(",")) if arg("--regions") else None
    kinds = set(arg("--kinds").split(",")) if arg("--kinds") else None
    for o in sorted(bpy.data.objects, key=lambda o: o.name):
        if o.type != "CAMERA" or not (o.get("cot_s3") or o.get("cot_s4")):
            continue
        if regions is not None and o.get("cot_region") not in regions:
            continue
        if kinds is not None and o.get("cot_kind") not in kinds:
            continue
        cams.append(o)

scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_depth = "8"
scene.render.film_transparent = False
scene.render.use_motion_blur = False
info = {"mode": mode, "tag": tag,
        "blend_sha256": hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
        "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
if profile_path:
    info.update(profile=str(profile_path.relative_to(ROOT)),
                profile_sha256=hashlib.sha256(profile_path.read_bytes()).hexdigest())

peak = {"text": ""}


def _stats(text):
    if "Peak" in text or "Mem" in text:
        peak["text"] = text


bpy.app.handlers.render_stats.clear()
bpy.app.handlers.render_stats.append(_stats)

if mode == "clay":
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.light, sh.color_type = "STUDIO", "MATERIAL"
    sh.show_cavity, sh.cavity_type = True, "BOTH"
    sh.show_shadows, sh.shadow_intensity = True, 0.3
    sh.show_object_outline, sh.object_outline_color = True, (0.0, 0.0, 0.0)
    scene.display.render_aa = "8"
    scene.view_settings.view_transform, scene.view_settings.look, scene.view_settings.exposure = "Standard", "None", 0.0
    scene.world.color = (0.16, 0.2, 0.27)
    scene.render.use_compositing = False
    info["engine"] = "BLENDER_WORKBENCH"
else:
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
    cy = scene.cycles
    cy.device = "GPU" if chosen else "CPU"
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = noise
    cy.use_denoising = "--no-denoise" not in argv
    try:
        cy.denoiser = "OPTIX" if chosen == "OPTIX" else "OPENIMAGEDENOISE"
    except TypeError:
        pass
    if profile:
        cy.denoiser = profile['denoiser']
        cy.adaptive_min_samples = int(profile['adaptive_min_samples'])
        cy.seed = int(profile['seed'])
        cy.use_animated_seed = bool(profile['animated_seed'])
    cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces = 6, 2, 3
    cy.transparent_max_bounces, cy.volume_bounces = 16, 0
    cy.caustics_reflective = cy.caustics_refractive = False
    cy.sample_clamp_indirect = 6.0
    cy.use_light_tree = True
    try:
        scene.render.use_persistent_data = bool(anim) or '--persistent' in argv
    except AttributeError:
        pass
    info.update(engine="CYCLES", device=chosen or "CPU", samples=samples, denoise=cy.use_denoising, adaptive_threshold=noise,
                adaptive_min_samples=cy.adaptive_min_samples, denoiser=cy.denoiser,
                denoising_use_gpu=cy.denoising_use_gpu, denoising_quality=cy.denoising_quality,
                denoising_prefilter=cy.denoising_prefilter, denoising_input_passes=cy.denoising_input_passes,
                seed=cy.seed, animated_seed=cy.use_animated_seed,
                volume_step_rate=getattr(cy, "volume_step_rate", None))
    for cname in ("COT_S2_OUTLINE",):
        c = bpy.data.collections.get(cname)
        if c is not None:
            c.hide_render = False

weather_on = mode == "final"
if art_switch is not None and scene.get("cot_stage4"):
    art_switch.set_weather(scene, weather_on)
else:                                                        # structure file: only the stage 2 weather exists
    for cname in ("COT_S2_WEATHER",):
        c = bpy.data.collections.get(cname)
        if c is not None:
            c.hide_render = not weather_on
    for obj in bpy.data.objects:
        if obj.name.startswith(("COT_S2_Fog", "COT_S2_Glow")):
            obj.hide_render = not weather_on
if mode == "clay":
    for cname in ("COT_S2_OUTLINE", "COT_REFERENCE"):
        c = bpy.data.collections.get(cname)
        if c is not None:
            c.hide_render = True
info["weather"] = weather_on
info["view_transform"], info["look"], info["exposure"] = scene.view_settings.view_transform, scene.view_settings.look, scene.view_settings.exposure

layer_colls = {}
for coll in bpy.data.collections:
    if coll.name.startswith("COT_L_"):
        layer_colls.setdefault(coll.name[len("COT_L_"):], []).append(coll)
    elif coll.name.startswith("COT_S3_"):
        tail = coll.name.rsplit("_", 1)[-1]
        if tail in ("FRONT", "CEILING", "ROCK", "BACKDROP", "CAVESHELL", "CHARS"):
            layer_colls.setdefault(tail, []).append(coll)
S2_FAR = [o for o in bpy.data.objects if o.get("cot_s2") and o.name.startswith(("COT_BackTower_", "COT_FarTower_", "COT_FrontTower_"))]
S2_FAR_RENDER = {o.name: o.hide_render for o in S2_FAR}
ALIAS = {"ROCK": ("ROCK", "HOSTROCK"), "BACKDROP": ("BACKDROP", "FOREGROUND")}


def apply_hides(cam):
    hide_keys = set()
    for h in [h for h in cam.get("cot_hide", "").split(",") if h]:
        hide_keys.update(ALIAS.get(h, (h,)))
    for key, colls in layer_colls.items():
        for coll in colls:
            coll.hide_render = key in hide_keys
    for o in S2_FAR:
        o.hide_render = S2_FAR_RENDER[o.name] or ("BACKDROP" in hide_keys)
    for coll in bpy.data.collections:                     # puddles lying on a hidden layer go with it
        if coll.name.startswith("COT_S4_PUDDLES_"):
            coll.hide_render = coll.name[len("COT_S4_PUDDLES_"):] in hide_keys
    return sorted(hide_keys)


def peak_mib():
    m = re.search(r"Peak[: ]+([\d.]+)\s*([MG])", peak["text"]) or re.search(r"Mem[: ]+([\d.]+)\s*([MG])", peak["text"])
    if not m:
        return None
    v = float(m.group(1))
    return round(v * 1024 if m.group(2) == "G" else v, 1)


def rain_cut(cam, hides):
    """Depth of the section plane for cameras that hide the viewer-side facades (0 = no cut)."""
    if "FRONT" not in hides:
        return 0.0
    rid = cam.get("cot_region")
    ys = [max((o.matrix_world @ Vector(c)).y for c in o.bound_box) for o in bpy.data.objects
          if o.get("cot_region") == rid and o.get("cot_layer") == "FRONT" and o.type in ("MESH", "CURVE")]
    if not ys:
        return 0.0
    fwd = cam.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
    if fwd.y < 0.3:
        return 0.0
    return max(0.0, (max(ys) + 0.3 - cam.matrix_world.translation.y) / fwd.y)


results = []
for cam in cams:
    rid = cam.get("cot_region") or ("FountainPlaza" if cam.name.startswith(("CAM_REF_", "CAM_S2_", "CAM_FILM_S2")) else "_misc")
    hides = apply_hides(cam)
    scene["cot_rain_cut"] = cam.get("cot_rain_cut", rain_cut(cam, hides))
    scene.camera = cam
    if res_fixed:
        rx, ry = res_fixed
    else:
        rx, ry = (int(v) for v in cam.get("cot_res", (1920, 1080)))
    scene.render.resolution_x, scene.render.resolution_y = max(16, int(rx * scale)), max(16, int(ry * scale))
    out_dir = out_root / rid
    out_dir.mkdir(parents=True, exist_ok=True)
    peak["text"] = ""
    entry = dict(info, camera=cam.name, region=rid, hidden_layers=hides, resolution=[scene.render.resolution_x, scene.render.resolution_y],
                 rain_cut=round(float(scene["cot_rain_cut"]), 2))
    if anim:
        f0, f1 = int(anim[0]), int(anim[1])
        seq = out_dir / f"{cam.name}__{tag}"
        seq.mkdir(exist_ok=True)
        bind_sequence(seq,{'schema':1,'settings':entry,'frames':[f0,f1]},'--resume' in argv)
        before = len(list(seq.glob("f*.png")))
        scene.frame_start, scene.frame_end = f0, f1
        scene.render.filepath = str(seq / "f####")
        scene.render.use_overwrite = "--resume" not in argv
        t0 = time.perf_counter()
        bpy.ops.render.render(animation=True)
        sec = time.perf_counter() - t0
        n = len(list(seq.glob("f*.png")))
        entry.update(frames=[f0, f1], dir=seq.name, seconds=round(sec, 1), rendered=n - (before if "--resume" in argv else 0), files=n,
                     seconds_per_frame=round(sec / max(1, n - (before if "--resume" in argv else 0)), 2))
    else:
        scene.frame_set(frame)
        target = out_dir / f"{cam.name}__{tag}.png"
        scene.render.filepath = str(target)
        t0 = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        entry.update(frame=scene.frame_current, file=target.name, seconds=round(time.perf_counter() - t0, 2), exists=target.is_file())
    entry["peak_mib"] = peak_mib()
    entry["stats"] = peak["text"][-160:]
    results.append(entry)
    print("COT_RENDER", json.dumps(entry, ensure_ascii=False), flush=True)
    mpath = out_dir / "render_manifest.json"
    man = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {"renders": []}
    man["blend"], man["blender"] = bpy.data.filepath, bpy.app.version_string
    man["renders"] = [r for r in man["renders"] if not (r.get("camera") == cam.name and r.get("tag") == tag)] + [entry]
    mpath.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
print("COT_RENDER_DONE", len(results))
