"""Repair a saved Marissa asset or placed scene into a separate checkpoint.

blender -b INPUT --python scripts/assets/fix_marissa_spots.py -- --out OUTPUT
The source meshes, colour/wing patterns, room and light powers are preserved.
"""
import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[args.index('--out') + 1]).resolve()
source = Path(bpy.data.filepath).resolve()
apply_only = '--apply-only' in args
assert (apply_only or out != source) and out.is_relative_to(ROOT)
cfgpath = ROOT / 'config/marissa_surface_fix.json'
cfg = json.loads(cfgpath.read_text(encoding='utf-8'))
report = {'source': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'output': str(out), 'config_sha256': hashlib.sha256(cfgpath.read_bytes()).hexdigest(),
          'contours': [], 'volumes': []}
for obj in bpy.data.objects:
    if obj.get('cot_role') != 'contour':
        continue
    for prefix, strength in cfg['contour_strength'].items():
        if obj.name.startswith(prefix):
            mod = obj.modifiers.get('InkInflate')
            if mod is None:
                continue
            original = obj.get('cot_mar_spots_original_strength', mod.strength)
            obj['cot_mar_spots_original_strength'] = original
            mod.strength = strength
            obj['cot_mar_surface_fix'] = 'thin contour to prevent tip/vein punctures'
            report['contours'].append({'object': obj.name, 'before': original, 'after': strength})

clear = cfg['clear_air']
sys.path.insert(0, str(ROOT / 'scripts/build'))
import art_switch
for name in clear['objects']:
    obj = bpy.data.objects.get(name)
    if obj is None:
        continue  # Independent asset has no city atmosphere.
    # Locally appended beams may arrive after the city's weather installation.
    if name.startswith('COT_S4_BeamAir_MarissaBeam'):
        for path in ('hide_render', 'hide_viewport'):
            error = art_switch._add_driver(obj, path, bpy.context.scene, 'w < 0.5')
            assert error is None, error
    mat = obj.active_material
    assert mat is not None and mat.use_nodes, name
    nt = mat.node_tree
    vol = next(n for n in nt.nodes if n.type == 'PRINCIPLED_VOLUME')
    density = vol.inputs['Density']
    # Store the density source before the first insertion; repeats replace only
    # our mask nodes, without multiplying masks or changing the original field.
    old = nt.nodes.get('MAR_ClearAirDensity')
    if old:
        incoming = list(old.inputs[0].links)
        density_source = incoming[0].from_socket if incoming else old.inputs[0].default_value
    else:
        incoming = list(density.links)
        density_source = incoming[0].from_socket if incoming else density.default_value
    for n in list(nt.nodes):
        if n.name.startswith('MAR_ClearAir'):
            nt.nodes.remove(n)
    def math_node(op, a, b=0.0):
        n = nt.nodes.new('ShaderNodeMath'); n.name = 'MAR_ClearAir_' + op
        n.operation = op
        for sock, value in zip(n.inputs, (a, b)):
            if isinstance(value, bpy.types.NodeSocket): nt.links.new(value, sock)
            else: sock.default_value = value
        return n.outputs[0]
    geo = nt.nodes.new('ShaderNodeNewGeometry'); geo.name = 'MAR_ClearAir_Position'
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); sep.name = 'MAR_ClearAir_Axes'
    nt.links.new(geo.outputs['Position'], sep.inputs[0])
    terms = [math_node('POWER', math_node('DIVIDE', math_node('SUBTRACT', sep.outputs[i], clear['centre'][i]),
                                        clear['radii'][i]), 2.0) for i in range(3)]
    radius = math_node('SQRT', math_node('ADD', math_node('ADD', terms[0], terms[1]), terms[2]))
    edge = math_node('DIVIDE', math_node('SUBTRACT', radius, 1.0), clear['soft_edge'])
    edge.node.use_clamp = True
    keep = math_node('MULTIPLY', edge, edge)
    result = math_node('MULTIPLY', density_source, keep)
    result.node.name = 'MAR_ClearAirDensity'
    nt.links.new(result, density)
    obj['cot_mar_surface_fix'] = 'soft clear-air envelope around full subject'
    report['volumes'].append({'object': name, 'material': mat.name, 'clear_air': clear})

scene = bpy.context.scene
if scene.get('cot_asset') == 'Marissa':
    scene['cot_version'] = out.parent.name.rsplit('_', 1)[-1]
    bpy.data.objects['MAR_Root']['cot_version'] = scene['cot_version']
scene.cycles.samples = cfg['samples']
scene.cycles.transparent_max_bounces = cfg['transparent_bounces']
scene['cot_mar_surface_fix_config'] = bpy.path.relpath(str(cfgpath), start=str(out.parent))
scene['cot_mar_surface_fix'] = '2026-10-08: contour punctures and subject fog mottling'
bpy.context.view_layer.update()
out.parent.mkdir(parents=True, exist_ok=True)
if not apply_only:
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    report['output_sha256'] = hashlib.sha256(out.read_bytes()).hexdigest()
else:
    report['save_status'] = 'applied in memory; caller saves'
(ROOT / 'logs' / (out.stem + '_surface_fix.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('MAR_SURFACE_FIX', len(report['contours']), len(report['volumes']), str(out))
