"""Put each front-elevation check render next to the same area of the master map.

Run from the project root, after render_checks.py:
  blender -b --factory-startup scenes/city_master.blend --python scripts/compare_master.py -- [--dir renders/previews/stage01]

For every camera that stores cot_map_box (an orthographic front view framed on a master-map
rectangle) this writes to renders/comparisons/stage01/:
  <camera>__pair.jpg     master crop above, greybox render below, same framing
  <camera>__overlay.jpg  the render blended over a brightened master crop
The reading version of the master map is used; the original PNG is not touched.
"""
import sys
from pathlib import Path

import bpy
import numpy as np
import OpenImageIO as oiio

ROOT = Path(__file__).resolve().parents[1]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
src_dir = ROOT / (argv[argv.index("--dir") + 1] if "--dir" in argv else "renders/previews/stage01")
out_dir = ROOT / "renders" / "comparisons" / src_dir.name
out_dir.mkdir(parents=True, exist_ok=True)
MASTER = ROOT / "docs" / "reference_review" / "master_map_7600.jpg"


def read(path):
    buf = oiio.ImageBuf(str(path))
    return np.asarray(buf.get_pixels(oiio.FLOAT))[..., :3].copy()


def resize(array, width, height):
    src = oiio.ImageBuf(oiio.ImageSpec(array.shape[1], array.shape[0], 3, oiio.FLOAT))
    src.set_pixels(oiio.ROI(0, array.shape[1], 0, array.shape[0]), np.ascontiguousarray(array, dtype=np.float32))
    dst = oiio.ImageBufAlgo.resize(src, roi=oiio.ROI(0, width, 0, height, 0, 1, 0, 3))
    return np.asarray(dst.get_pixels(oiio.FLOAT))[..., :3].copy()


def write(array, path):
    array = np.clip(array, 0.0, 1.0).astype(np.float32)
    spec = oiio.ImageSpec(array.shape[1], array.shape[0], 3, oiio.UINT8)
    spec.attribute("CompressionQuality", 88)
    out = oiio.ImageOutput.create(str(path))
    out.open(str(path), spec)
    out.write_image(np.ascontiguousarray(array))
    out.close()


master = read(MASTER)
mh, mw = master.shape[:2]
done = []
for cam in sorted((o for o in bpy.data.objects if o.type == "CAMERA" and "cot_map_box" in o), key=lambda o: o.name):
    render_path = src_dir / f"{cam.name}.png"
    if not render_path.is_file():
        continue
    x0, y0, x1, y1 = (float(v) for v in cam["cot_map_box"])
    render = read(render_path)
    rh, rw = render.shape[:2]
    cx0, cy0 = max(0, int(round(x0))), max(0, int(round(y0)))
    cx1, cy1 = min(mw, int(round(x1))), min(mh, int(round(y1)))
    crop = np.zeros((int(round(y1 - y0)), int(round(x1 - x0)), 3), np.float32)
    crop[cy0 - int(round(y0)):cy1 - int(round(y0)), cx0 - int(round(x0)):cx1 - int(round(x0))] = master[cy0:cy1, cx0:cx1]
    crop = resize(crop, rw, rh)
    scale = min(1.0, 2000.0 / rw)
    if scale < 1.0:
        w, h = int(rw * scale), int(rh * scale)
        crop, render = resize(crop, w, h), resize(render, w, h)
    bright = np.clip(crop * 2.4, 0.0, 1.0) ** 0.8
    gap = np.full((6, crop.shape[1], 3), 0.5, np.float32)
    write(np.vstack([bright, gap, render]), out_dir / f"{cam.name}__pair.jpg")
    write(bright * 0.75 + render * 0.45, out_dir / f"{cam.name}__overlay.jpg")
    done.append(cam.name)
print("COT_COMPARE", len(done), "cameras ->", out_dir, done)
