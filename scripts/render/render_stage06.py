"""Render Stage 6 risk clips, resumable take sequences, or 1440p stills.

Blender usage:
  blender -b --factory-startup scenes/city_animation_v010.blend --python scripts/render/render_stage06.py -- --risk rain_fog
  blender -b --factory-startup scenes/city_animation_v010.blend --python scripts/render/render_stage06.py -- --takes S01,S02 --resume
  blender -b --factory-startup scenes/city_animation_v010.blend --python scripts/render/render_stage06.py -- --stills 01_full_city,02_fountain_plaza
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "render"))
from stage06_pipeline import bind_identity, expected_take_frames, light_regions_for_take  # noqa: E402

ARGV = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def arg(name: str, default: str | None = None) -> str | None:
    if name not in ARGV:
        return default
    return ARGV[ARGV.index(name) + 1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


CFG_PATH = ROOT / arg("--config", "config/stage06_render.json")
CFG = json.loads(CFG_PATH.read_text(encoding="utf-8"))
SHOTS_PATH = ROOT / CFG["shot_config"]
SHOTS = json.loads(SHOTS_PATH.read_text(encoding="utf-8"))
SCENE_PATH = Path(bpy.data.filepath)
if sha(SCENE_PATH) != CFG["source_animation_sha256"]:
    raise RuntimeError("Stage 6 source animation hash changed")
if sha(SHOTS_PATH) != CFG["shot_config_sha256"]:
    raise RuntimeError("Stage 6 shot config hash changed")

SCENE = bpy.context.scene
OUT = ROOT / CFG["output_root"]
OUT.mkdir(parents=True, exist_ok=True)


def configure_scene(resolution: tuple[int, int]) -> dict:
    SCENE.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    chosen = "CPU"
    for backend in CFG["device_preference"]:
        if backend == "CPU":
            break
        try:
            prefs.compute_device_type = backend
            prefs.refresh_devices()
        except Exception:
            continue
        available = [d for d in prefs.devices if d.type == backend]
        if available:
            for device in prefs.devices:
                device.use = device.type == backend
            chosen = backend
            break
    SCENE.cycles.device = "GPU" if chosen != "CPU" else "CPU"
    SCENE.cycles.samples = int(CFG["samples"])
    SCENE.cycles.use_adaptive_sampling = bool(CFG["adaptive_sampling"])
    SCENE.cycles.adaptive_threshold = float(CFG["adaptive_threshold"])
    SCENE.cycles.adaptive_min_samples = int(CFG["adaptive_min_samples"])
    SCENE.cycles.use_denoising = bool(CFG["denoise"])
    SCENE.cycles.denoiser = CFG["denoiser"]
    SCENE.cycles.seed = int(CFG["seed"])
    SCENE.cycles.use_animated_seed = bool(CFG["animated_seed"])
    SCENE.render.use_motion_blur = bool(CFG["motion_blur"])
    SCENE.render.use_compositing = bool(CFG["compositing"])
    SCENE.render.use_sequencer = bool(CFG["sequencer"])
    SCENE.render.resolution_x, SCENE.render.resolution_y = resolution
    SCENE.render.resolution_percentage = 100
    SCENE.render.image_settings.file_format = CFG["format"]
    SCENE.render.image_settings.color_mode = CFG["color_mode"]
    SCENE.render.image_settings.color_depth = CFG["color_depth"]
    SCENE.render.image_settings.compression = int(CFG["png_compression"])
    SCENE.render.film_transparent = False
    SCENE.view_settings.view_transform = CFG["view_transform"]
    SCENE.view_settings.look = CFG["look"]
    SCENE.view_settings.exposure = float(CFG["exposure"])
    SCENE.view_settings.gamma = float(CFG["gamma"])
    try:
        SCENE.render.use_persistent_data = True
    except AttributeError:
        pass
    for marker in SCENE.timeline_markers:
        marker.camera = None
    return {
        "engine": SCENE.render.engine,
        "device": chosen,
        "resolution": list(resolution),
        "samples": SCENE.cycles.samples,
        "adaptive_sampling": SCENE.cycles.use_adaptive_sampling,
        "adaptive_threshold": SCENE.cycles.adaptive_threshold,
        "adaptive_min_samples": SCENE.cycles.adaptive_min_samples,
        "denoise": SCENE.cycles.use_denoising,
        "denoiser": SCENE.cycles.denoiser,
        "seed": SCENE.cycles.seed,
        "animated_seed": SCENE.cycles.use_animated_seed,
        "motion_blur": SCENE.render.use_motion_blur,
        "compositing": SCENE.render.use_compositing,
        "sequencer": SCENE.render.use_sequencer,
        "view_transform": SCENE.view_settings.view_transform,
        "look": SCENE.view_settings.look,
        "exposure": SCENE.view_settings.exposure,
        "gamma": SCENE.view_settings.gamma,
        "format": SCENE.render.image_settings.file_format,
        "color_mode": SCENE.render.image_settings.color_mode,
        "color_depth": SCENE.render.image_settings.color_depth,
        "png_compression": SCENE.render.image_settings.compression,
    }


def identity(settings: dict, scope: dict) -> dict:
    return {
        "schema": 1,
        "version": CFG["version"],
        "source_animation": CFG["source_animation"],
        "source_animation_sha256": CFG["source_animation_sha256"],
        "shot_config": CFG["shot_config"],
        "shot_config_sha256": CFG["shot_config_sha256"],
        "stage06_config_sha256": sha(CFG_PATH),
        "renderer_sha256": sha(Path(__file__)),
        "blender": bpy.app.version_string,
        "settings": settings,
        "scope": scope,
    }


def configure_take_lights(take_id: str) -> dict:
    policy = CFG.get("light_culling", {"mode": "none"})
    if policy.get("mode") != "take_regions":
        # Preserve the saved source's visibility, including intentional hides.
        return {"mode": "none", "kept": sum(obj.type == "LIGHT" and not obj.hide_render for obj in bpy.data.objects),
                "hidden": sum(obj.type == "LIGHT" and obj.hide_render for obj in bpy.data.objects)}

    keep_regions = light_regions_for_take(SHOTS, take_id, policy.get("always_regions", []))
    keep_set = set(keep_regions)
    kept = hidden = 0
    hidden_regions: dict[str, int] = {}
    for obj in bpy.data.objects:
        if obj.type != "LIGHT":
            continue
        region = str(obj.get("cot_region", "<none>"))
        obj.hide_render = region not in keep_set
        if obj.hide_render:
            hidden += 1
            hidden_regions[region] = hidden_regions.get(region, 0) + 1
        else:
            kept += 1
    return {
        "mode": "take_regions",
        "keep_regions": keep_regions,
        "kept": kept,
        "hidden": hidden,
        "hidden_regions": dict(sorted(hidden_regions.items())),
    }


def render_range(camera_name: str, frames: tuple[int, int], folder: Path, settings: dict, scope: dict, resume: bool) -> dict:
    bind_identity(folder, identity(settings, scope), resume)
    SCENE.camera = bpy.data.objects[camera_name]
    SCENE.frame_start, SCENE.frame_end = frames
    SCENE.render.filepath = str(folder / "f####")
    SCENE.render.use_overwrite = not resume
    before = len(list(folder.glob("f*.png")))
    started = time.perf_counter()
    previous_write = [started]

    def record_frame(scene, *_args):
        now = time.perf_counter()
        frame_record = {"frame": scene.frame_current, "seconds_since_previous_write": round(now - previous_write[0], 3)}
        previous_write[0] = now
        with (folder / "frame_timings.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(frame_record) + "\n")

    bpy.app.handlers.render_write.append(record_frame)
    try:
        bpy.ops.render.render(animation=True)
    finally:
        bpy.app.handlers.render_write.remove(record_frame)
    elapsed = time.perf_counter() - started
    after = len(list(folder.glob("f*.png")))
    record = {
        "scope": scope,
        "camera": camera_name,
        "frames": list(frames),
        "files_before": before,
        "files_after": after,
        "elapsed_seconds": round(elapsed, 3),
        "new_files": after - before,
        "seconds_per_new_frame": round(elapsed / max(1, after - before), 3),
        "complete": all((folder / f"f{frame:04d}.png").is_file() for frame in range(frames[0], frames[1] + 1)),
    }
    (folder / "timing.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print("STAGE06_RANGE_DONE", json.dumps(record, ensure_ascii=False), flush=True)
    if not record["complete"]:
        raise RuntimeError("render stopped before the requested range was complete")
    return record


settings = configure_scene(tuple(CFG["resolution"]))
resume = "--resume" in ARGV
take_by_id = {take["id"]: take for take in SHOTS["takes"]}

if arg("--risk"):
    risk_id = arg("--risk")
    risk = next(item for item in CFG["risk_tests"] if item["id"] == risk_id)
    take = take_by_id[risk["take"]]
    folder = OUT / "risk_tests" / risk_id
    light_state = configure_take_lights(take["id"])
    render_range(take["camera"], tuple(risk["frames"]), folder, settings, {"kind": "risk", **risk, "light_culling": light_state}, resume)
elif "--stills" in ARGV:
    requested = set((arg("--stills") or ",".join(item["id"] for item in CFG["stills"])).split(","))
    settings = configure_scene(tuple(CFG["still_resolution"]))
    folder = OUT / "stills"
    folder.mkdir(parents=True, exist_ok=True)
    records = []
    for still in CFG["stills"]:
        if still["id"] not in requested:
            continue
        take = take_by_id.get(still.get("take"))
        camera_name = still.get("camera") or take["camera"]
        light_state = configure_take_lights(take["id"] if take else "reference")
        SCENE.camera = bpy.data.objects[camera_name]
        SCENE.frame_set(int(still["frame"]))
        target = folder / f"{still['id']}_f{still['frame']:04d}.png"
        still_identity = identity(settings, {"kind": "still", **still, "camera": camera_name, "light_culling": light_state})
        sidecar = target.with_suffix(".json")
        if target.exists():
            if not resume or not sidecar.exists() or json.loads(sidecar.read_text(encoding="utf-8"))["identity"] != still_identity:
                raise RuntimeError(f"existing still lacks matching resume identity: {target}")
            records.append(json.loads(sidecar.read_text(encoding="utf-8"))["record"])
            continue
        SCENE.render.filepath = str(target)
        started = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        records.append({**still, "file": target.name, "seconds": round(time.perf_counter() - started, 3), "light_culling": light_state})
        sidecar.write_text(json.dumps({"identity": still_identity, "record": records[-1]}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("STAGE06_STILL_DONE", json.dumps(records[-1], ensure_ascii=False), flush=True)
    (folder / "stills_render.json").write_text(
        json.dumps({"identity": identity(settings, {"kind": "stills"}), "records": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
else:
    requested = set((arg("--takes") or ",".join(take_by_id)).split(","))
    plans = expected_take_frames(SHOTS)
    records = []
    for take in SHOTS["takes"]:
        if take["id"] not in requested:
            continue
        frames = (plans[take["id"]][0], plans[take["id"]][-1])
        light_state = configure_take_lights(take["id"])
        records.append(render_range(take["camera"], frames, OUT / "takes" / take["id"], settings, {"kind": "take", "take": take["id"], "light_culling": light_state}, resume))
    print("STAGE06_TAKES_DONE", len(records), flush=True)
