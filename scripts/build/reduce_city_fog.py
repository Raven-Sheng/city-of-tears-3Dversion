"""Apply a versioned, bounded full-city clarity adjustment; keep upstream volume masks."""
import hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/qa'));sys.path.insert(0,str(ROOT/'scripts/build'))
from check_local_fog import geometry_signature
import art_switch

def lighting_signature():
    values={'lights':[(o.name,o.data.type,o.data.energy,list(o.data.color)) for o in sorted(bpy.data.objects,key=lambda o:o.name) if o.type=='LIGHT'],
            'cameras':[(o.name,o.data.lens,o.data.type,o.data.dof.use_dof,o.data.dof.aperture_fstop) for o in sorted(bpy.data.objects,key=lambda o:o.name) if o.type=='CAMERA'],
            'exposure':bpy.context.scene.view_settings.exposure}
    return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()

def apply(config):
    found={m.name for m in bpy.data.materials if m.node_tree and any(n.type in ('PRINCIPLED_VOLUME','VOLUME_SCATTER','VOLUME_ABSORPTION') for n in m.node_tree.nodes)}
    assert found==set(config['materials']), 'Inventory changed; inspect every new volume before applying'
    changes={}
    for name,factor in config['materials'].items():
        assert 0<factor<1
        mat=bpy.data.materials[name];nt=mat.node_tree;volume=next(n for n in nt.nodes if n.type=='PRINCIPLED_VOLUME')
        sockets=[]
        for socket,label in [('Density','Density'),('Emission Strength','Emission')]:
            inp=volume.inputs[socket]
            if socket=='Emission Strength' and not inp.links and inp.default_value==0:continue
            node=nt.nodes.get('COT_CityFog'+label+'Scale')
            if node is None:
                old=inp.links[0].from_socket if inp.links else inp.default_value
                node=nt.nodes.new('ShaderNodeMath');node.name='COT_CityFog'+label+'Scale';node.operation='MULTIPLY'
                if isinstance(old,bpy.types.NodeSocket):nt.links.new(old,node.inputs[0])
                else:node.inputs[0].default_value=old
                nt.links.new(node.outputs[0],inp)
            assert inp.links[0].from_node==node
            node.inputs[1].default_value=factor;sockets.append(socket)
        mat['cot_city_fog_factor']=factor
        changes[name]={'factor':factor,'sockets':sockets,'objects':[o.name for o in bpy.data.objects if any(s.material==mat for s in o.material_slots)]}
    tree=bpy.context.scene.compositing_node_group;mist=tree.nodes[art_switch.MIST_NODE]
    mist['cot_strength']=config['mist_strength']
    assert art_switch._add_driver(tree,f'nodes["{art_switch.MIST_NODE}"].inputs[0].default_value',bpy.context.scene,f"{config['mist_strength']} * w") is None
    glare=next(n for n in tree.nodes if n.type=='GLARE')
    glare.inputs['Strength'].default_value=config['bloom_strength'];glare.inputs['Size'].default_value=config['bloom_size']
    art_switch.set_weather(bpy.context.scene,True)
    return changes

if __name__=='__main__':
    config=ROOT/'config/stage04_city_fog.json';C=json.loads(config.read_text(encoding='utf-8'))
    source=ROOT/C['source'];out=ROOT/C['output'];assert Path(bpy.data.filepath).resolve()==source.resolve()
    assert hashlib.sha256(source.read_bytes()).hexdigest()==C['source_sha256']
    assert not out.exists() and out.is_relative_to(ROOT/'scenes/checkpoints') and out!=source
    bpy.context.scene.frame_set(1);geometry=geometry_signature();lighting=lighting_signature()
    changes=apply(C)
    assert geometry_signature()==geometry and lighting_signature()==lighting
    bpy.context.scene['cot_city_fog']='2026-10-08: full-city low fog and restrained bloom, prioritize readable near-field detail'
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    report={'source':C['source'],'source_sha256':C['source_sha256'],'output':C['output'],'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'geometry_signature':geometry,'lighting_signature':lighting,'config_sha256':hashlib.sha256(config.read_bytes()).hexdigest(),'materials':changes,'mist_strength':C['mist_strength'],'bloom_strength':C['bloom_strength'],'bloom_size':C['bloom_size']}
    (ROOT/'_work/stage04/closeout/city_fog_build_v014.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('CITY_FOG_SAVED',report['output_sha256'])
