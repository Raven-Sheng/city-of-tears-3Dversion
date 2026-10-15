"""Clear local stage sight lines in a placed-Marissa copy; preserve the source.

blender -b --factory-startup INPUT --python scripts/assets/clear_marissa_stage.py -- --out OUTPUT
Config: config/marissa_stage_clearance.json. Re-running restores archived source
meshes before applying the same component selection. Never clears the room roof.
"""
import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[args.index('--out') + 1]).resolve()
source = Path(bpy.data.filepath).resolve()
apply_only = '--apply-only' in args
assert apply_only or out != source, 'Save to a separate file, preserving the input'
assert out.is_relative_to(ROOT), 'Output must be in project'
assert 'MAR_Place_HouseOfPleasure' in bpy.data.objects, 'Marissa is not placed'
cfgpath = ROOT / 'config/marissa_stage_clearance.json'
cfg = json.loads(cfgpath.read_text(encoding='utf-8'))
box_lo, box_hi = cfg['clearance_box']
report = {'source': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'output': str(out), 'config_sha256': hashlib.sha256(cfgpath.read_bytes()).hexdigest(),
          'mesh_changes': [], 'hidden': []}

for name in cfg['component_objects']:
    obj = bpy.data.objects[name]
    archive_name = obj.get('cot_mar_clearance_original')
    if archive_name:
        original = bpy.data.meshes[archive_name]
    else:
        original = obj.data
        original.use_fake_user = True
        obj['cot_mar_clearance_original'] = original.name
    mesh = original.copy()
    obj.data = mesh
    bm = bmesh.new(); bm.from_mesh(mesh)
    seen = set(); remove = []; components = []
    for v in bm.verts:
        if v in seen:
            continue
        todo = [v]; seen.add(v); group = []
        while todo:
            a = todo.pop(); group.append(a)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b not in seen:
                    seen.add(b); todo.append(b)
        world = [obj.matrix_world @ a.co for a in group]
        lo = [min(p[i] for p in world) for i in range(3)]
        hi = [max(p[i] for p in world) for i in range(3)]
        # Narrow disconnected hanging pieces only; the continuous roof, rails,
        # wide side curtains and rear decorative arches remain untouched.
        if hi[0] - lo[0] <= cfg['max_component_width'] and all(
                lo[i] < box_hi[i] and hi[i] > box_lo[i] for i in range(3)):
            remove.extend(group)
            components.append({'vertices': len(group), 'min': lo, 'max': hi})
    if remove:
        bmesh.ops.delete(bm, geom=remove, context='VERTS')
    bm.to_mesh(mesh); bm.free(); mesh.update()
    obj['cot_mar_clearance'] = 'central hanging pieces removed; source mesh archived'
    obj['cot_mar_clearance_evidence'] = 'C: user-directed staging clearance, 2026-10-07'
    report['mesh_changes'].append({'object': name, 'components': components,
                                   'before_vertices': len(original.vertices), 'after_vertices': len(mesh.vertices)})

for name in cfg['hide_objects']:
    obj = bpy.data.objects[name]
    obj.hide_render = True
    obj.hide_viewport = True
    obj['cot_mar_clearance'] = 'removed from view for Marissa; recoverable via visibility'
    report['hidden'].append(name)
    # Keep any independent outline copy from leaving a ghost silhouette.
    for o in bpy.data.objects:
        if o.name.startswith(name + '_') and o.get('cot_role') == 'contour':
            o.hide_render = True; o.hide_viewport = True

report['lights'] = {}
for name, scale in cfg.get('light_energy_scale', {}).items():
    light = bpy.data.objects.get(name)
    if light is None:
        report['lights'][name] = {'status': 'not present in input; not created'}
        continue
    original_energy = light.get('cot_mar_clearance_original_energy', light.data.energy)
    light['cot_mar_clearance_original_energy'] = original_energy
    light.data.energy = original_energy * scale
    report['lights'][name] = {'before': original_energy, 'after': light.data.energy}

c = cfg['hero_camera']
cam = bpy.data.objects.get(c['name'])
if cam is None:
    cam = bpy.data.objects.new(c['name'], bpy.data.cameras.new(c['name']))
    bpy.data.collections['HouseOfPleasure_MAR_Marissa'].objects.link(cam)
cam.location = c['position']
cam.rotation_euler = (Vector(c['target']) - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.lens = c['lens']; cam.data.clip_start = 0.05; cam.data.clip_end = 400
cam['cot_region'] = 'HouseOfPleasure'; cam['cot_hide'] = ''; cam['cot_res'] = [1920, 1080]
cam['cot_mar_placed'] = True
bpy.context.scene.camera = cam
bpy.context.scene['cot_mar_clearance_config'] = bpy.path.relpath(str(cfgpath), start=str(out.parent))
bpy.context.scene['cot_mar_clearance_scope'] = ('integrated city source' if bpy.context.scene.get('cot_mar_integrated')
                                              else 'staged Marissa copy; not merged into city_art or city_structure')
bpy.context.view_layer.update()
out.parent.mkdir(parents=True, exist_ok=True)
if not apply_only:
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    report['output_sha256'] = hashlib.sha256(out.read_bytes()).hexdigest()
else:
    report['save_status'] = 'applied in memory; caller saves'
(ROOT / 'logs' / (out.stem + '_clearance.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('MAR_CLEARANCE', json.dumps({'output': str(out), 'removed_components': {x['object']:len(x['components']) for x in report['mesh_changes']}, 'hidden':report['hidden']}))
