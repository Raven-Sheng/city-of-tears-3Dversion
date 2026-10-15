"""Build the stage 4 city look (materials, lights, rain, fog, far masses, art cameras) into scenes/city_art.blend.

Run from the project root:
  blender -b --factory-startup --python scripts/build/build_art.py -- [--checkpoint] [--no-weather] [--file OUT]

  * Always derived from scenes/city_structure.blend (the stage 3 structure file is never written). Everything stage 4
    adds carries cot_s4 and lives in COT_S4_* collections or NG_COT_* / MAT_S4_* datablocks; materials of stage 2/3
    are rebuilt in place on the stage 4 node groups (same names, so every object keeps its assignment).
  * Same code + config/art.json + seed gives the same file content (ray casts and random choices are seeded).
  * --checkpoint also copies the result to scenes/checkpoints/city_art_vNNN.blend.
"""
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
sys.path.insert(0, str(ROOT / "scripts" / "cam"))

import art_lights as AL  # noqa: E402
import art_materials as AM  # noqa: E402
import art_switch  # noqa: E402
import art_weather as AW  # noqa: E402
import cot_look  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
CFG = json.loads((ROOT / "config" / "art.json").read_text(encoding="utf-8"))
SOURCE = ROOT / "scenes" / "city_structure.blend"
TARGET = Path(argv[argv.index("--file") + 1]) if "--file" in argv else ROOT / "scenes" / "city_art.blend"
report = {"source": str(SOURCE), "target": str(TARGET), "config_sha": hashlib.sha256((ROOT / "config" / "art.json").read_bytes()).hexdigest()[:16]}
t_all = time.perf_counter()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
scene["cot_stage"] = 4
scene["cot_stage4"] = 1


def coll(name, parent):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in parent.children:
        parent.children.link(c)
    return c


ROOT_C = coll("COT_S4", scene.collection)
LIGHTS = coll(AL.LIGHT_ROOT, ROOT_C)
WEATHER = coll("COT_S4_WEATHER", ROOT_C)
FOG = coll("COT_S4_FOG", ROOT_C)
RETIRED = coll("COT_S4_RETIRED", ROOT_C)
RETIRED.hide_render = True
RETIRED.hide_viewport = True

# ------------------------------------------------------------------ colour management (fixed for the whole city)
cm = CFG["color_management"]
scene.view_settings.view_transform = cm["view_transform"]
scene.view_settings.look = cm["look"]
scene.view_settings.exposure = cm["exposure"]
scene.view_settings.gamma = cm["gamma"]
scene.display_settings.display_device = "sRGB"
scene.render.fps = 24

# ------------------------------------------------------------------ materials
t0 = time.perf_counter()
AM.build_groups(CFG["global"])
converted = []
for key, (color, rough, metal) in cot_look.SURFACES.items():
    if key in AM.STAGE2_KEEP:
        continue
    m = AM.stage2_surface(key, color, rough, metal, key in cot_look.COURSED)
    if m is not None:
        converted.append(m.name)
m = AM.stage2_surface("iron_scaffold", cot_look.SURFACES["iron"][0], cot_look.SURFACES["iron"][1], cot_look.SURFACES["iron"][2], False,
                      emission=((0.10, 0.21, 0.52), 0.075))
if m is not None:
    converted.append(m.name)
for key in cot_look.GLASS:
    AM.add_glass_gain(bpy.data.materials.get("MAT_S2_" + key))
AM.add_lamp_gain(bpy.data.materials.get("MAT_S2_lamp"))
for key in cot_look.FRINGE:                                   # shell-tower tiers in the wells get the region ambient too
    AM.add_ambient(bpy.data.materials.get("MAT_S2_" + key))
made, missing = [], []
for key, spec in CFG["materials"].items():
    name = "MAT_S3_" + key
    if bpy.data.materials.get(name) is None:
        missing.append(name)
    AM.make_material(name, spec)
    made.append(name)
import art_specials as AS  # noqa: E402

SP = CFG.get("specials", {})
for src_name, spec in SP.get("coat_copies", {}).items():
    # stage 3 copy of a stage 2 material with a clear coat / sheen layer (e.g. shell-tower tiers catch an edge
    # highlight per tier); the stage 2 original stays as it is for the plaza; used through material_overrides
    src = bpy.data.materials.get(src_name)
    if src is not None:
        old = bpy.data.materials.get(spec["name"])
        if old is not None:
            bpy.data.materials.remove(old)
        cp = src.copy()
        cp.name = spec["name"]
        bsdfs = [n for n in cp.node_tree.nodes if n.type == "BSDF_PRINCIPLED"]
        for bsdf in bsdfs:
            for k, v in spec["inputs"].items():
                bsdf.inputs[k].default_value = v
        cp["cot_s4"] = True
        report.setdefault("coat_copies", {})[spec["name"]] = len(bsdfs)
report["material_overrides"] = AS.material_overrides(SP.get("material_overrides", {}))
unconfigured = sorted(m.name for m in bpy.data.materials if m.name.startswith("MAT_S3_") and m.name[7:] not in CFG["materials"] and m.users)
report["materials"] = {"stage2_converted": len(converted), "stage3_rebuilt": len(made), "not_in_file_before": missing,
                       "stage3_unconfigured_in_use": unconfigured, "seconds": round(time.perf_counter() - t0, 1)}

# ------------------------------------------------------------------ the stage 2 plaza rain is replaced by the city rain
retired = []
for o in list(bpy.data.objects):
    if o.name.startswith("COT_Rain_Layer"):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        RETIRED.objects.link(o)
        o.hide_render = True
        retired.append(o.name)
report["retired_stage2_rain"] = retired

# ------------------------------------------------------------------ lights
t0 = time.perf_counter()
report["lamp_props"] = AS.lamp_props(SP.get("lamp_props", []))
report["lamp_lights"] = AL.build_lamp_lights(LIGHTS, CFG["lights"])
report["region_fill"] = AL.build_region_fill(LIGHTS, CFG["lights"])
if SP.get("window_lights"):
    report["window_lights"] = AS.window_lights(LIGHTS, SP["window_lights"])
spot_items = [s for s in SP.get("spots", []) if not s.get("requires_object") or s["requires_object"] in bpy.data.objects]
report["spots"] = AS.spots(LIGHTS, spot_items)
report["motes"] = AS.motes(LIGHTS, SP.get("motes", []), CFG["seed"])
report["lights_seconds"] = round(time.perf_counter() - t0, 1)

# ------------------------------------------------------------------ weather
for o in bpy.data.objects:
    for k in ("cot_wet", "cot_dry", "cot_wetf_used"):
        if k in o.keys():
            del o[k]
if "--no-weather" not in argv:
    t0 = time.perf_counter()
    hidden_for_cast = []
    for cname in ("COT_REFERENCE", "COT_S2_WEATHER", "COT_S2_OUTLINE", "COT_S4_RETIRED", "COT_S4_WEATHER", "COT_S4_FOG"):
        c = bpy.data.collections.get(cname)
        if c is not None and not c.hide_viewport:
            c.hide_viewport = True
            hidden_for_cast.append(c)
    flipped = []
    for o in bpy.data.objects:                                # render-hidden objects (greybox, helpers) must not stop rain
        if o.hide_render and not o.hide_viewport and o.type in ("MESH", "CURVE", "FONT"):
            o.hide_viewport = True
            flipped.append(o)
    bpy.context.view_layer.update()
    struct_sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:16]
    rain_key = hashlib.sha256(json.dumps([struct_sha, CFG["rain"]["zones"], CFG["rain"]["density_per_m2"], CFG["rain"]["drips"], CFG["seed"],
                                       AW.PLACEMENT_VERSION, CFG["rain"].get("exclude_regions"), CFG["rain"].get("edge_feather"),
                                       CFG["rain"].get("high_shelter_gap")], sort_keys=True).encode()).hexdigest()[:16]
    report["structure_sha"] = struct_sha
    tracks, drips, wet, stats, rays, rain_objs = AW.build_rain(WEATHER, scene, CFG["rain"], CFG["seed"],
                                                               cache_path=ROOT / "_work" / "stage04" / "rain_cache.json", cache_key=rain_key)
    puddles, n_puddles = AW.build_puddles(WEATHER, tracks, drips, CFG["rain"]["puddles"], CFG["seed"], AW.Caster(scene))
    report["puddles_rejected_not_flat"] = puddles.get("cot_rejected_not_flat") if puddles else None
    report["face_wetness"] = AW.face_wetness(scene, wet, ROOT / "_work" / "stage04" / "wetf_cache.json",
                                             hashlib.sha256(json.dumps([struct_sha, rain_key, 1]).encode()).hexdigest()[:16])
    if CFG.get("far"):
        import art_far
        report["far"] = art_far.build(coll("COT_S4_FAR", ROOT_C), CFG["far"], CFG["seed"], AW.Caster(scene))
    for o in flipped:
        o.hide_viewport = False
    for c in hidden_for_cast:
        c.hide_viewport = False
    for name, w in wet.items():
        o = bpy.data.objects.get(name)
        if o is not None:
            o["cot_wet"] = float(w)
    n_dry = 0
    for o in bpy.data.objects:                               # rain never reaches it: no wet-look gloss (stage 2 plaza untouched)
        if o.get("cot_s3") and o.type in ("MESH", "CURVE") and float(o.get("cot_wet", 0.0)) <= 0.0:
            o["cot_dry"] = 1.0
            n_dry += 1
    fog = AW.ground_fog(FOG, CFG["fog"]["ground_layers"])
    report["local_volumes"] = AS.local_volumes(FOG, SP.get("local_volumes", []))
    if SP.get("window_lights"):
        report["shaft_volumes"] = len(AS.shaft_volumes(FOG, scene, SP["window_lights"]))
    report["beam_volumes"] = AS.beam_volumes(FOG, scene, spot_items)
    report["weather"] = {"zones": stats, "drips": len(drips), "puddles": n_puddles, "rays": rays, "wet_objects": len(wet), "dry_objects": n_dry,
                         "fog_volumes": [o.name for o in fog], "seconds": round(time.perf_counter() - t0, 1)}
AW.setup_compositor(scene, cm, CFG["fog"]["mist"])
report["switch_problems"] = art_switch.install(scene, CFG["fog"]["mist"]["strength"])
art_switch.set_weather(scene, True)

# ------------------------------------------------------------------ art cameras (fixed reference views and moving shots)
try:
    import art_cameras
    report["cameras"] = art_cameras.build(scene, coll("COT_S4_CAMERAS", ROOT_C))
except ImportError:
    report["cameras"] = "art_cameras.py not present"

# The placed character comes from the structure source. Keep her staging and
# clear-air envelope when the art file is rebuilt, including --no-weather.
if 'MAR_Place_HouseOfPleasure' in bpy.data.objects:
    import runpy
    saved_argv = sys.argv
    try:
        for script in ('clear_marissa_stage.py', 'fix_marissa_spots.py'):
            sys.argv = [script, '--', '--out', str(TARGET), '--apply-only']
            runpy.run_path(str(ROOT / 'scripts/assets' / script), run_name='__main__')
        report['marissa_staging'] = {'asset': bpy.data.objects['MAR_Root'].get('cot_version'),
                                     'clearance': True, 'surface_fix': True}
    finally:
        sys.argv = saved_argv

report["objects_total"] = len(bpy.data.objects)
report["s4_objects"] = sum(1 for o in bpy.data.objects if o.get("cot_s4"))
report["lights_total"] = sum(1 for o in bpy.data.objects if o.type == "LIGHT")
report["seconds"] = round(time.perf_counter() - t_all, 1)
TARGET.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
if "--checkpoint" in argv:
    cp_dir = ROOT / "scenes" / "checkpoints"
    existing = sorted(cp_dir.glob("city_art_v*.blend"))
    version = (int(existing[-1].stem.split("_v")[-1]) + 1) if existing else 1
    cp = cp_dir / f"city_art_v{version:03d}.blend"
    shutil.copy2(TARGET, cp)
    report["checkpoint"] = str(cp)
(ROOT / "logs" / "stage04").mkdir(parents=True, exist_ok=True)
if "--file" not in argv:
    (ROOT / "logs" / "stage04" / "build_art_last.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("COT_S4_BUILD", json.dumps(report, ensure_ascii=False, default=str)[:3000])
