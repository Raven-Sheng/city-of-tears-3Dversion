"""Render one editable delivery frame from the package-relative config.

Usage from the repository root:
  blender -b scenes/city_animation_v010.blend --python scripts/render/render_delivery_frame.py -- --frame 4230 --camera CAM_V8_S07 --output _work/f4230.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy


ARGV = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def arg(name: str, default: str | None = None) -> str | None:
    if name not in ARGV:
        return default
    return ARGV[ARGV.index(name) + 1]


ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "config" / "stage06_delivery.json").read_text(encoding="utf-8"))
RENDER_CONFIG = json.loads((ROOT / CONFIG["render_config"]).read_text(encoding="utf-8"))
SCENE = bpy.context.scene


def configure() -> str:
    SCENE.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    chosen = "CPU"
    for backend in RENDER_CONFIG["device_preference"]:
        if backend == "CPU":
            break
        try:
            prefs.compute_device_type = backend
            prefs.refresh_devices()
        except Exception:
            continue
        available = [device for device in prefs.devices if device.type == backend]
        if available:
            for device in prefs.devices:
                device.use = device.type == backend
            chosen = backend
            break
    SCENE.cycles.device = "GPU" if chosen != "CPU" else "CPU"
    SCENE.cycles.samples = int(RENDER_CONFIG["samples"])
    SCENE.cycles.use_adaptive_sampling = bool(RENDER_CONFIG["adaptive_sampling"])
    SCENE.cycles.adaptive_threshold = float(RENDER_CONFIG["adaptive_threshold"])
    SCENE.cycles.adaptive_min_samples = int(RENDER_CONFIG["adaptive_min_samples"])
    SCENE.cycles.use_denoising = bool(RENDER_CONFIG["denoise"])
    SCENE.cycles.denoiser = RENDER_CONFIG["denoiser"]
    SCENE.render.resolution_x, SCENE.render.resolution_y = CONFIG["resolution"]
    SCENE.render.resolution_percentage = 100
    SCENE.render.image_settings.file_format = "PNG"
    SCENE.render.image_settings.color_mode = "RGB"
    SCENE.render.image_settings.color_depth = "8"
    SCENE.render.use_motion_blur = bool(RENDER_CONFIG["motion_blur"])
    SCENE.render.use_compositing = bool(RENDER_CONFIG["compositing"])
    SCENE.render.use_sequencer = bool(RENDER_CONFIG["sequencer"])
    SCENE.view_settings.view_transform = RENDER_CONFIG["view_transform"]
    SCENE.view_settings.look = RENDER_CONFIG["look"]
    SCENE.view_settings.exposure = float(RENDER_CONFIG["exposure"])
    SCENE.view_settings.gamma = float(RENDER_CONFIG["gamma"])
    return chosen


device = configure()
frame = int(arg("--frame", "4230"))
camera_name = arg("--camera", "CAM_V8_S07")
camera = bpy.data.objects.get(camera_name)
if camera is None or camera.type != "CAMERA":
    raise RuntimeError(f"camera not found: {camera_name}")
if not (SCENE.frame_start <= frame <= SCENE.frame_end):
    raise RuntimeError(f"frame out of range: {frame}")
output = Path(arg("--output", str(ROOT / "_work" / f"f{frame:04d}.png"))).resolve()
output.parent.mkdir(parents=True, exist_ok=True)
SCENE.camera = camera
SCENE.frame_set(frame)
SCENE.render.filepath = str(output)
bpy.ops.render.render(write_still=True)
print(json.dumps({"pass": output.exists(), "frame": frame, "camera": camera_name,
                  "device": device, "output": str(output)}, ensure_ascii=False))
