"""Add restrained stylized emission to window air, preserving its soft density profile."""
import bpy,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/build'))
import art_lights as AL,math
from mathutils import Vector
import closeout_window_openings
cfgpath=ROOT/'config/stage04_finish.json';C=json.loads(cfgpath.read_text(encoding='utf-8'))
source=Path(bpy.data.filepath).resolve();args=sys.argv[sys.argv.index('--')+1:];out=(ROOT/args[args.index('--out')+1]).resolve()
assert out!=source and not out.exists() and out.is_relative_to(ROOT/'scenes/checkpoints')
assert source==(ROOT/C['source']).resolve()
window_openings=closeout_window_openings.apply()
mat=bpy.data.materials['MAT_S4_shaft_air'];nt=mat.node_tree
assert 'COT_Closeout_ShaftEmission' not in nt.nodes
vol=next(n for n in nt.nodes if n.type=='PRINCIPLED_VOLUME');density=vol.inputs['Density'].links[0].from_socket
n=nt.nodes.new('ShaderNodeMath');n.name='COT_Closeout_ShaftEmission';n.operation='MULTIPLY';n.inputs[1].default_value=C['shaft_emission_per_density']
nt.links.new(density,n.inputs[0]);nt.links.new(n.outputs[0],vol.inputs['Emission Strength']);vol.inputs['Emission Color'].default_value=(.65,.78,1.,1.)
mat['cot_evidence']='C: restrained volumetric glow on actual window shafts, density/edge/floor fade retained'
bpy.data.objects['COT_S4_Spot_TopCavernUplight'].data.energy=C['cavern_spot_power']
bpy.data.objects['COT_S4_DeepRockWash'].data.energy=C['deep_rock_power']
receivers=bpy.data.collections.new('COT_S4_LINK_RockFrontWash')
for o in bpy.data.objects:
    if o.name == 'S3_TopCavern_CaveSheet':
        for s in o.material_slots:
            s.link='OBJECT';s.material=bpy.data.materials['MAT_S3_rock_cave']
        # The continuous thick deep-rock surface now performs this background role.
        # Retain the old mesh for recovery while avoiding two overlapping backdrops.
        o.hide_render=True;o.hide_viewport=True;o['cot_retired']='Replaced by COT_S4_DeepRock; original checkpoint retained'
    if o.type=='MESH' and o.get('cot_region') in ('_World','TopCavern') and any(s.material and s.material.name in ('MAT_S3_rock_cave','MAT_S3_pebble') for s in o.material_slots):
        o['cot_amb']=C['far_ambient'];receivers.objects.link(o)
lamp=AL.new_light(bpy.data.collections['COT_S4_LIGHTS'],'COT_S4_RockFrontWash','AREA',(0,-140,160),(.35,.52,.82),C['front_rock_power'],size=(500,180),rot=(math.pi/2,0,0),shadow=True)
lamp.light_linking.receiver_collection=receivers
data=bpy.data.cameras.new('CAM_S4_SanctumWindowCheck_data');cam=bpy.data.objects.new('CAM_S4_SanctumWindowCheck',data)
bpy.data.collections['COT_S4_CAMERAS'].objects.link(cam)
cam.location=(-43.4,27,164.5);cam.rotation_euler=(Vector((-43,50,164))-cam.location).to_track_quat('-Z','Y').to_euler();data.lens=32
cam['cot_s4']=True;cam['cot_region']='SoulSanctum';cam['cot_kind']='check';cam['cot_hide']='FRONT,CAVESHELL'
bpy.context.scene['cot_closeout']='2026-10-08 stage 4 repairs + window shaft glow; stage 5 not begun'
bpy.ops.wm.save_as_mainfile(filepath=str(out))
record={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'out':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'config_sha256':hashlib.sha256(cfgpath.read_bytes()).hexdigest(),'change':'Through-window openings, soft shafts and continuous deep-rock backdrop','window_openings':window_openings,'coefficient':C['shaft_emission_per_density'],'evidence':'C'}
(ROOT/'_work/stage04/closeout/finish_report.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print('SHAFT_FINISH_SAVED',out)
