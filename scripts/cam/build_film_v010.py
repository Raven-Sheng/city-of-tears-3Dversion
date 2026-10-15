"""Stage 5 v010 cameras only. Source art file is immutable; refuses an existing output.

blender -b scenes/city_art.blend --python scripts/cam/build_film_v010.py
"""
import bpy, json, csv, math, hashlib, sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/cam'))
from cot_camrig import Sequence, matrix

CFG = ROOT / 'config/shots_v010.json'
c = json.loads(CFG.read_text(encoding='utf-8'))
source = ROOT / c['source']; out = ROOT / c['output']
assert hashlib.sha256(source.read_bytes()).hexdigest() == c['source_sha256']
assert Path(bpy.data.filepath).resolve() == source.resolve()
assert not out.exists(), 'Use a new output version; preserve checkpoints'

s = bpy.context.scene
coll = bpy.data.collections.new('COT_S5V8_CAMERAS'); s.collection.children.link(coll)
# Camera-only: no geometry, material, light, weather or visibility changes.
for m in list(s.timeline_markers):
    if m.camera: m.camera = None
s.render.fps = c['fps']; s.render.fps_base = 1
s.render.resolution_x, s.render.resolution_y = c['resolution']
s.frame_start, s.frame_end = c['frames']
s['cot_stage5'] = 'v010'; s['cot_s5_config'] = hashlib.sha256(CFG.read_bytes()).hexdigest()

def set_linear(idb):
    for layer in idb.animation_data.action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for k in fc.keyframe_points: k.interpolation = 'LINEAR'

rows = []
for tk in c['takes']:
    seq = Sequence(tk, fps=c['fps'])
    name = tk['camera']
    data = bpy.data.cameras.new(name + '_data')
    data.type = 'PERSP'; data.sensor_width = 36; data.clip_start = 0.1; data.clip_end = 2000
    data.dof.use_dof = True; data.dof.aperture_fstop = 11
    cam = bpy.data.objects.new(name, data); coll.objects.link(cam)
    cam.rotation_mode = 'XYZ'
    look = bpy.data.objects.new(name + '_LOOK', None); coll.objects.link(look)
    focus = bpy.data.objects.new(name + '_FOCUS', None); coll.objects.link(focus)
    data.dof.focus_object = focus
    for o in (cam, look, focus):
        o['cot_s5'] = 'v010'; o['cot_take'] = tk['id']
    cam['cot_frames'] = [tk['frame_start'], tk['frame_end']]
    cam['cot_handles'] = [tk['handle_in'], tk['handle_out']]
    cam['cot_regions'] = ','.join(dict.fromkeys(b['region'] for b in tk['beats']))
    cam['cot_kind'] = 'film'; cam['cot_hide'] = ''
    prev = None
    f0 = tk['frame_start'] - tk['handle_in']; f1 = tk['frame_end'] + tk['handle_out']
    for frame in range(f0, f1 + 1):
        t = seq.t0 + (frame - tk['frame_start']) / c['fps']
        p, q, lens, lk = seq.sample(t)
        e = q.to_euler('XYZ', prev) if prev is not None else q.to_euler('XYZ')
        prev = e
        cam.location = p; cam.rotation_euler = e; data.lens = lens
        look.location = lk; focus.location = lk
        cam.keyframe_insert('location', frame=frame); cam.keyframe_insert('rotation_euler', frame=frame)
        data.keyframe_insert('lens', frame=frame)
        look.keyframe_insert('location', frame=frame); focus.keyframe_insert('location', frame=frame)
    for idb in (cam, data, look, focus): set_linear(idb)
    marker = s.timeline_markers.new('S5V8_' + tk['id'] + '_' + tk['title'][:24], frame=tk['frame_start']); marker.camera = cam
    for b in tk['beats']:
        rows.append(dict(take=tk['id'], take_title=tk['title'], take_frames=f"{tk['frame_start']}-{tk['frame_end']}",
                         region=b['region'], beat_frames=f"{b['frames'][0]}-{b['frames'][1]}",
                         beat_seconds=f"{(b['frames'][0]-1)/24:.2f}-{b['frames'][1]/24:.2f}", content=b['content'],
                         camera=name, handles=f"{tk['handle_in']}/{tk['handle_out']}", hero=tk['hero'], reference=b['reference']))
s.frame_set(1); s.camera = bpy.data.objects[c['takes'][0]['camera']]
bpy.ops.wm.save_as_mainfile(filepath=str(out), compress=True)
with (ROOT / 'docs/camera_shotlist_v010.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
man = ROOT / '_work/stage05_v010/build_manifest_v010.json'
man.write_text(json.dumps(dict(config_sha256=s['cot_s5_config'], output=c['output'],
                               output_sha256=hashlib.sha256(out.read_bytes()).hexdigest()), indent=2), encoding='utf-8')
print('STAGE05_V010_SAVED', out, flush=True)
