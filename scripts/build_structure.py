"""Build the stage 3 city structure (all regions) on top of the stage 2 plaza sample.

Run from the project root:
  blender -b --factory-startup --python scripts/build_structure.py -- [--from-sample] [--regions A,B] [--checkpoint] [--file FILE] [--no-save]

  * Works on scenes/city_structure.blend. The first run (or --from-sample) derives it from scenes/plaza_sample.blend;
    scenes/city_master.blend and scenes/plaza_sample.blend are never written.
  * Rebuilds only cot_s3 objects of the selected regions (default: every region). Stage 2 sample objects and
    hand-made objects stay. Stage 1 greybox objects of a rebuilt region are hidden and tagged cot_s3_superseded.
  * Same code + config gives the same result (fixed seeds).
  * --checkpoint also writes scenes/checkpoints/city_structure_vNNN.blend.
"""
import importlib
import json
import shutil
import sys
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from cot_s3 import PROJECT, Session  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TARGET = Path(argv[argv.index("--file") + 1]) if "--file" in argv else ROOT / "scenes" / "city_structure.blend"
SAMPLE = ROOT / "scenes" / "plaza_sample.blend"
ONLY = argv[argv.index("--regions") + 1].split(",") if "--regions" in argv else None
source = SAMPLE if ("--from-sample" in argv or not TARGET.exists()) else TARGET
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
scene["cot_stage"] = 3

# region id -> module in scripts/regions; order follows the dependency order of the main specification (section 11)
MODULES = ["central", "leftwell", "west", "bridges", "pleasure", "sanctum", "tower", "east", "world"]
REGISTRY = {}
for mod_name in MODULES:
    try:
        mod = importlib.import_module("regions." + mod_name)
    except ModuleNotFoundError as exc:
        if exc.name != "regions." + mod_name:
            raise
        continue
    REGISTRY.update(mod.REGIONS)

S = Session(scene)
selected = ONLY if ONLY is not None else list(REGISTRY)
report = {"source": str(source), "target": str(TARGET), "regions": {}, "superseded": {}}
started = time.perf_counter()
for rid in selected:
    if rid not in REGISTRY:
        raise SystemExit(f"unknown region {rid}; known: {sorted(REGISTRY)}")
    t0 = time.perf_counter()
    removed = S.clear_region(rid)
    for cam in [o for o in bpy.data.objects if o.type == "CAMERA" and o.get("cot_s3") and o.get("cot_region") == rid]:
        bpy.data.objects.remove(cam, do_unlink=True)
    REGISTRY[rid](S)
    hidden = S.supersede(rid)
    report["regions"][rid] = {"objects": S.counts.get(rid, 0), "removed_before": removed, "greybox_superseded": len(hidden),
                              "seconds": round(time.perf_counter() - t0, 1)}
import cot_fit  # noqa: E402

fit = cot_fit.fit_props(None if ONLY is None else set(selected))
report["props_fit"] = {"props": fit["props"], "lifted": len(fit["lifted"]), "culled": len(fit["culled"])}
(ROOT / "logs").mkdir(exist_ok=True)
(ROOT / "logs" / "props_fit_last.json").write_text(json.dumps(fit, ensure_ascii=False, indent=1), encoding="utf-8")
report["kit_conflicts"] = S.kit_conflicts
if S.kit_conflicts:                                           # one kit key must always mean the same part, or partial rebuilds change other regions
    raise SystemExit("COT_S3_KIT_CONFLICT " + json.dumps(S.kit_conflicts, ensure_ascii=False))
report["seconds"] = round(time.perf_counter() - started, 1)
report["objects_total"] = len(bpy.data.objects)
report["s3_objects"] = sum(1 for o in bpy.data.objects if o.get("cot_s3"))
report["vertices_mesh_data"] = sum(len(m.vertices) for m in bpy.data.meshes)
scene["cot_s3_regions"] = ",".join(sorted({o.get("cot_region") for o in bpy.data.objects if o.get("cot_s3") and o.get("cot_region")}))

# Keep user-directed staging after a region rebuild; Marissa herself is not cot_s3.
if 'MAR_Place_HouseOfPleasure' in bpy.data.objects and (ONLY is None or 'HouseOfPleasure' in selected):
    import runpy
    saved_argv = sys.argv
    try:
        sys.argv = ['clear_marissa_stage.py', '--', '--out', str(TARGET), '--apply-only']
        runpy.run_path(str(ROOT / 'scripts/assets/clear_marissa_stage.py'), run_name='__main__')
        report['marissa_clearance'] = True
    finally:
        sys.argv = saved_argv

if "--no-save" not in argv:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
    if "--checkpoint" in argv:
        cp_dir = ROOT / PROJECT["checkpoint_dir"]
        existing = sorted(cp_dir.glob("city_structure_v*.blend"))
        version = (int(existing[-1].stem.split("_v")[-1]) + 1) if existing else 1
        cp = cp_dir / f"city_structure_v{version:03d}.blend"
        shutil.copy2(TARGET, cp)
        report["checkpoint"] = str(cp)
    (ROOT / "logs").mkdir(exist_ok=True)
    if "--file" not in argv:
        (ROOT / "logs" / "build_structure_last.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("COT_S3_BUILD", json.dumps(report, ensure_ascii=False))
