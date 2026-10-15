"""Fresh-load validation: exact local factors plus unchanged city meshes/transforms."""
import json,hashlib,array
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]

def geometry_signature():
    digest=hashlib.sha256()
    for o in sorted(bpy.data.objects,key=lambda x:x.name):
        digest.update((o.name+'|'+o.type+'|'+(o.parent.name if o.parent else '')).encode())
        digest.update(array.array('f',[v for row in o.matrix_world for v in row]).tobytes())
        if o.type=='MESH':
            mesh=o.data;coords=array.array('f',[0.])*len(mesh.vertices)*3
            mesh.vertices.foreach_get('co',coords);digest.update(coords.tobytes())
            vertices=array.array('i',[0])*len(mesh.loops);mesh.loops.foreach_get('vertex_index',vertices);digest.update(vertices.tobytes())
            ends=array.array('i',[0])*len(mesh.polygons);mesh.polygons.foreach_get('loop_total',ends);digest.update(ends.tobytes())
    return digest.hexdigest()

if __name__=='__main__':
    report=json.loads((ROOT/'_work/stage04/closeout/local_fog_build.json').read_text(encoding='utf-8'))
    bpy.context.scene.frame_set(1)
    assert geometry_signature()==report['geometry_signature'],'Geometry or transforms changed'
    assert hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()==report['output_sha256']
    for name,item in report['materials'].items():
        mat=bpy.data.materials[name]
        for label in ['Density']+(['Emission'] if 'Emission Strength' in item['sockets'] else []):
            node=mat.node_tree.nodes['COT_LocalFog'+label+'Scale']
            assert abs(node.inputs[1].default_value-item['factor'])<1e-6
        if 'MarissaBeam' in name or 'PleasureStage' in name:assert mat.node_tree.nodes.get('MAR_ClearAirDensity')
    out={'source':bpy.data.filepath,'sha256':report['output_sha256'],'geometry_unchanged':True,'materials':report['materials'],'pass':True}
    (ROOT/'_work/stage04/closeout/local_fog_check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('LOCAL_FOG_CHECK_PASS')
