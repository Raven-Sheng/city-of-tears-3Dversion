"""Reduce only requested local air, preserving its existing edge/subject-clear masks."""
import hashlib,json,sys,array
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/qa'))
from check_local_fog import geometry_signature
config=ROOT/'config/stage04_local_fog.json';C=json.loads(config.read_text(encoding='utf-8'))
source=(ROOT/C['source']).resolve();out=(ROOT/C['output']).resolve()
assert Path(bpy.data.filepath).resolve()==source
assert out.is_relative_to(ROOT/'scenes/checkpoints') and out!=source and not out.exists()
assert hashlib.sha256(source.read_bytes()).hexdigest()=='8dfc5e8d4fd8a433f8f6afe2fdc7f831272bedd48f649f2f571e67d6b35b8114'
bpy.context.scene.frame_set(1)
report={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'geometry_signature':geometry_signature(),'materials':{},'config_sha256':hashlib.sha256(config.read_bytes()).hexdigest()}
for name,factor in C['materials'].items():
    mat=bpy.data.materials[name];nt=mat.node_tree
    users=[o for o in bpy.data.objects if any(s.material==mat for s in o.material_slots)]
    if name=='MAT_S4_shaft_air':assert all(o.get('cot_region')=='SoulSanctum' for o in users)
    else:assert all(any(s in o.name for s in ('SanctumHalls','PleasureStage','MarissaBeam')) for o in users)
    assert 0<factor<1 and not nt.nodes.get('COT_LocalFogDensityScale')
    volume=next(n for n in nt.nodes if n.type=='PRINCIPLED_VOLUME')
    changed=[]
    for socket,label in [('Density','Density'),('Emission Strength','Emission')]:
        inp=volume.inputs[socket]
        if socket=='Emission Strength' and not inp.links and inp.default_value==0:continue
        value=inp.links[0].from_socket if inp.links else inp.default_value
        node=nt.nodes.new('ShaderNodeMath');node.operation='MULTIPLY';node.name='COT_LocalFog'+label+'Scale'
        node.inputs[1].default_value=factor
        if isinstance(value,bpy.types.NodeSocket):nt.links.new(value,node.inputs[0])
        else:node.inputs[0].default_value=value
        nt.links.new(node.outputs[0],inp);changed.append(socket)
    mat['cot_local_fog_factor']=factor
    report['materials'][name]={'factor':factor,'objects':[o.name for o in users],'sockets':changed}
assert geometry_signature()==report['geometry_signature']
bpy.context.scene['cot_local_fog']='2026-10-08: less Sanctum and Marissa-stage air; geometry/lights unchanged'
bpy.ops.wm.save_as_mainfile(filepath=str(out))
report['output']=str(out);report['output_sha256']=hashlib.sha256(out.read_bytes()).hexdigest()
(ROOT/'_work/stage04/closeout/local_fog_build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('LOCAL_FOG_SAVED',str(out),report['output_sha256'])
