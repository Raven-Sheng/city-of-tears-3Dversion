"""Encode a rendered PNG sequence to H.264 MP4 with Blender's bundled FFmpeg (no external tools).

  blender -b --factory-startup --python scripts/encode_sequence.py -- <sequence_dir> <out.mp4> [fps] [crf: HIGH|MEDIUM|PERC_LOSSLESS]

The frames are already display-referred, so the sequencer scene uses the Standard view transform
(no second tone mapping). The frame count and size of the result are read back and printed.
"""
import json
import re
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
argv = sys.argv[sys.argv.index("--") + 1:]
seq = Path(argv[0]) if Path(argv[0]).is_absolute() else ROOT / argv[0]
out = Path(argv[1]) if Path(argv[1]).is_absolute() else ROOT / argv[1]
fps = int(argv[2]) if len(argv) > 2 else 24
quality = argv[3] if len(argv) > 3 else "HIGH"

files = sorted(seq.glob("f*.png"))
numbers = [int(re.search(r"(\d+)", p.stem).group(1)) for p in files]
missing = sorted(set(range(numbers[0], numbers[-1] + 1)) - set(numbers))
if missing:
    raise SystemExit(f"missing frames: {missing[:20]}")
img = bpy.data.images.load(str(files[0]))
width, height = img.size
bpy.data.images.remove(img)

scene = bpy.context.scene
scene.render.resolution_x, scene.render.resolution_y = width, height
scene.render.resolution_percentage = 100
scene.render.fps = fps
scene.render.fps_base = 1.0
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.render.use_sequencer = True
editor = scene.sequence_editor_create()
strip = editor.strips.new_image("SEQ", str(files[0]), 1, 1)
for p in files[1:]:
    strip.elements.append(p.name)
scene.frame_start, scene.frame_end = 1, len(files)
try:
    scene.render.image_settings.media_type = "VIDEO"
except (AttributeError, TypeError):
    pass
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = quality
scene.render.ffmpeg.ffmpeg_preset = "GOOD"
scene.render.ffmpeg.gopsize = 12
scene.render.ffmpeg.audio_codec = "NONE"
out.parent.mkdir(parents=True, exist_ok=True)
scene.render.filepath = str(out)
bpy.ops.render.render(animation=True)
produced = out if out.exists() else next(iter(sorted(out.parent.glob(out.stem + "*.mp4"))), None)
report = {"sequence": str(seq), "frames": len(files), "size": [width, height], "fps": fps, "file": str(produced),
          "bytes": produced.stat().st_size if produced else 0}
if produced:
    clip = bpy.data.movieclips.load(str(produced))
    report["readback"] = {"size": list(clip.size), "frames": clip.frame_duration, "fps": round(clip.fps, 3),
                          "seconds": round(clip.frame_duration / clip.fps, 3)}
print("COT_ENCODE", json.dumps(report))
