"""Apply scoped stage-four repairs to a saved city; preserve source and hand assets.
blender -b INPUT --python closeout_stage04.py -- --out OUTPUT
"""
import hashlib, json, math, re, sys
from pathlib import Path
import bpy, bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/build'))
import art_materials as AM, art_specials as AS, art_lights as AL, art_weather as AW, art_switch
args=sys.argv[sys.argv.index('--')+1:]
out=Path(args[args.index('--out')+1]).resolve()
source=Path(bpy.data.filepath).resolve()
assert out != source and out.is_relative_to(ROOT)
assert not out.exists(), 'Preserve existing checkpoints; choose a new output name'
cfgpath=ROOT/'config/stage04_closeout.json'
C=json.loads(cfgpath.read_text(encoding='utf-8'))
assert source == (ROOT/C['source']).resolve(), 'Re-run from the configured preserved source, never from an already repaired output'
A=json.loads((ROOT/'config/art.json').read_text(encoding='utf-8'))
scene=bpy.context.scene
report={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'config_sha256':hashlib.sha256(cfgpath.read_bytes()).hexdigest(),'changes':{}}
# Rebuilding a group interface invalidates sockets on its material users.
# Preserve every instance's values and external wires before rebuilding it.
instances=[]
for m in bpy.data.materials:
    if not m.node_tree:continue
    for n in m.node_tree.nodes:
        if n.type=='GROUP' and n.node_tree and n.node_tree.name.startswith('NG_COT_'):
            values={s.name:(list(s.default_value) if hasattr(s.default_value,'__len__') else s.default_value) for s in n.inputs if hasattr(s,'default_value')}
            wires=[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links if l.from_node==n or l.to_node==n]
            instances.append((m.name,n.name,values,wires))
AM.build_groups(A['global'])
for mn,nn,values,wires in instances:
    nt=bpy.data.materials[mn].node_tree;n=nt.nodes[nn]
    for key,value in values.items():
        if key in n.inputs:n.inputs[key].default_value=value
    for fn,fs,tn,ts in wires:
        a,b=nt.nodes.get(fn),nt.nodes.get(tn)
        if a and b and fs in a.outputs and ts in b.inputs:nt.links.new(a.outputs[fs],b.inputs[ts])
report['changes']['preserved_material_group_instances']=len(instances)
# Keep existing material assignments and bespoke Marissa shader masks.
for key in ('rock_cave','wall_pleasure','pattern','pattern_blue','mass_black','pebble'):
    spec=dict(A['materials'][key]);spec['Seam Depth']=0.0
    AM.make_material('MAT_S3_'+key,spec)
spec=dict(A['materials']['cluster']);spec['Dots']=C['cluster_dots']
AM.make_material('MAT_S3_cluster',spec)
AM.assign_group(bpy.data.materials['MAT_S3_cluster_spot'],'NG_COT_Emit',{'Color':(.35,.32,.27),'Strength':.09,'Base Color':(.085,.080,.072)})
cave_stone=AM.make_material('MAT_S4_cave_stone',{'group':'Paint','Base Color':[.026,.032,.055],'Roughness':.78,'Gloss Up':.12,'Seams':0.,'Seam Depth':0.})
for o in bpy.data.objects:
    if o.get('cot_region')=='SouthwestCave' and o.type=='MESH':
        for slot in o.material_slots:
            if slot.material and slot.material.name in ('MAT_S3_trim','MAT_S3_trim_pale','MAT_S2_stone'):
                slot.link='OBJECT';slot.material=cave_stone
spec=dict(A['materials']['floor']);spec.update(C['floor'])
floor=AM.make_material('MAT_S3_floor',spec)
node=next(n for n in floor.node_tree.nodes if n.type=='GROUP')
# Floors use long slabs; ceilings have a separate calm material.
vals=dict(AM.FAMILY['Stone']);vals.update({k:v for k,v in spec.items() if k not in ('group','Dots','note')})
vals.update({'Brick Width':2.8,'Row Height':1.15,'Gloss Up':.08})
AM.assign_group(floor,'NG_COT_Paint',vals)
ceil=AM.make_material('MAT_S4_ceiling',dict(group='Stone',**C['ceiling']))
ceiling_count=0
for o in bpy.data.objects:
    if o.get('cot_s3') and o.type=='MESH' and ('_Ceiling' in o.name or o.get('cot_layer')=='CEILING'):
        for slot in o.material_slots:
            if slot.material and slot.material.name.startswith(('MAT_S3_wall','MAT_S3_trim')):
                slot.link='OBJECT';slot.material=ceil;ceiling_count+=1
report['changes']['ceiling_slots']=ceiling_count
for name,values in C['plaza'].items():
    mat=bpy.data.materials.get(name)
    if mat:
        node=next((n for n in mat.node_tree.nodes if n.type=='GROUP' and n.node_tree.name=='NG_COT_Paint'),None)
        if node:
            for k,v in values.items():node.inputs[k].default_value=(*v,1) if isinstance(v,list) else v
# Globe emission has a spherical falloff; point lights continue lighting nearby surfaces.
ng=bpy.data.node_groups['NG_COT_Emit'];t=AM.T(ng)
bsdf=next(n for n in ng.nodes if n.type=='BSDF_PRINCIPLED')
base=bsdf.inputs['Emission Strength'].links[0].from_socket
geo=t.node('ShaderNodeNewGeometry');dot=t.node('ShaderNodeVectorMath',operation='DOT_PRODUCT')
t.link(geo.outputs['Normal'],dot.inputs[0]);t.link(geo.outputs['Incoming'],dot.inputs[1])
f=t.math('ADD',.18,t.math('MULTIPLY',t.math('ABSOLUTE',dot.outputs['Value']),.70))
t.link(t.math('MULTIPLY',base,f),bsdf.inputs['Emission Strength'])
bsdf.inputs['Specular IOR Level'].default_value=.1
AM.assign_group(bpy.data.materials['MAT_S2_lamp'],'NG_COT_Emit',{'Color':(.66,.78,1.),'Strength':1.3,'Base Color':(.008,.011,.017)})
for key in ('lamp_white','lamp_pink','lamp_warm'):
    spec=dict(A['materials'][key]);spec['Strength']=.85;spec['Base Color']=[.005,.007,.011]
    AM.make_material('MAT_S3_'+key,spec)
# Genuine ceramic jars: weak rim reflection and body; they do not glow like lamps.
jar=bpy.data.materials['MAT_S3_jar_glass'];AM.assign_group(jar,'NG_COT_Paint',{'Base Color':(.034,.023,.055),'Roughness':.24,'Coat':.65,'Metallic':.05,'Variation':.6,'Gloss Up':.1,'Seams':0.,'Seam Depth':0.,'Emission Strength':0.})
# Round-pad spots are disconnected low-segment meshes. Subdivide only their faces,
# preserving the wall pad bodies and their shared instances.
done=set();spot_faces=0
for o in bpy.data.objects:
    if not o.get('cot_s3') or o.type!='MESH' or o.data.name in done:continue
    ids={i for i,s in enumerate(o.material_slots) if s.material and s.material.name=='MAT_S3_cluster_spot'}
    if not ids:continue
    done.add(o.data.name);bm=bmesh.new();bm.from_mesh(o.data)
    faces=[f for f in bm.faces if f.material_index in ids]
    verts={v for f in faces for v in f.verts};spot_faces+=len(faces)
    if faces:
        unseen=set(verts)
        while unseen:
            todo=[unseen.pop()];part=[]
            while todo:
                v=todo.pop();part.append(v)
                for edge in v.link_edges:
                    q=edge.other_vert(v)
                    if q in unseen:unseen.remove(q);todo.append(q)
            centre=sum((v.co for v in part),Vector())/len(part)
            for v in part:v.co=centre+(v.co-centre)*C['cluster_spot_scale']
        bmesh.ops.subdivide_edges(bm,edges=list({e for f in faces for e in f.edges}),cuts=2,use_grid_fill=True,smooth=1.)
        for f in bm.faces:
            if f.material_index in ids:f.smooth=True
        bm.to_mesh(o.data);o.data.update()
    bm.free()
report['changes']['spot_meshes']=len(done);report['changes']['spot_faces_before']=spot_faces
# Restore rock skin on the flat backdrops; displace only exposed visual skins,
# within the existing rock volume, keeping rooms and support cores untouched.
rock=bpy.data.materials['MAT_S3_rock_cave'];backdrops=[]
for o in list(bpy.data.objects):
    if not o.get('cot_s3') or o.type!='MESH' or 'Backdrop' not in o.name:continue
    if o.get('cot_closeout_rock'):continue
    o.data=o.data.copy()
    for slot in o.material_slots:
        if slot.material and 'glass' not in slot.material.name:
            slot.link='OBJECT';slot.material=rock
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=5,use_grid_fill=True)
    for v in bm.verts:
        p=o.matrix_world@v.co
        v.co.y+=C['background_relief']*(.45*math.sin(p.x*.13+p.z*.09)+.35*math.sin(p.x*.33-p.z*.19))
    for f in bm.faces:f.smooth=True
    bm.to_mesh(o.data);bm.free();o.data.update()
    o['cot_closeout_rock']=True;o['cot_evidence']='C: local rock relief on existing backdrop volume'
    backdrops.append(o.name)
report['changes']['backdrops']=backdrops
# Unite exposed frontal host-rock skins on one grid, leaving all recorded rooms
# open. Original structural cores remain intact behind this local relief.
boxes=[];rooms=[]
for host in bpy.data.objects:
    if host.get('cot_rooms'):rooms.extend(json.loads(host['cot_rooms']))
    if host.type=='MESH' and host.name.startswith('S3__World_Host') and host.get('cot_layer')=='ROCK':
        lo,hi=AS._bbox(host)
        if -15<lo.y<-5 and hi.x-lo.x>8 and hi.z-lo.z>8:boxes.append((lo,hi))
bm=bmesh.new();grid={};cells=[]
def vertex(ix,iz,back):
    key=(ix,iz,back)
    if key not in grid:
        x=-260+ix*2;z=-16+iz*2
        near=[lo.y for lo,hi in boxes if lo.x-2<=x<=hi.x+2 and lo.z-2<=z<=hi.z+2]
        front=-14.5 if near and min(near)<-10 else -9.0
        y=front-.65*math.sin(x*.097+z*.063)-.35*math.sin(x*.21-z*.13)+back*2.2
        grid[key]=bm.verts.new((x,y,z))
    return grid[key]
for iz in range(128):
    for ix in range(260):
        x=-259+ix*2;z=-15+iz*2
        if not any(lo.x<=x<=hi.x and lo.z<=z<=hi.z for lo,hi in boxes):continue
        if any(r[0]-1<=x<=r[1]+1 and r[4]-1<=z<=r[5]+1 for r in rooms):continue
        corners=((ix,iz),(ix+1,iz),(ix+1,iz+1),(ix,iz+1));cells.append(corners)
        bm.faces.new([vertex(i,j,0) for i,j in corners]);bm.faces.new([vertex(i,j,1) for i,j in reversed(corners)])
vertex_keys={v:k for k,v in grid.items()}
for edge in list(bm.edges):
    if edge.is_boundary and all(vertex_keys[v][2]==0 for v in edge.verts):
        a,b=edge.verts;ka=vertex_keys[a];kb=vertex_keys[b]
        bm.faces.new((a,b,grid[(kb[0],kb[1],1)],grid[(ka[0],ka[1],1)]))
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges)
mesh=bpy.data.meshes.new('COT_S4_HostRockSkin_data');bm.to_mesh(mesh);bm.free();mesh.materials.append(rock)
o=bpy.data.objects.new('COT_S4_HostRockSkin',mesh);bpy.data.collections['COT_S4_FAR'].objects.link(o)
o['cot_s4']=True;o['cot_region']='_World';o['cot_layer']='DEEPROCK';o['cot_evidence']='C: joined frontal host-rock relief, recorded rooms kept open';o['cot_amb']=[.07,.10,.18]
for p in mesh.polygons:p.use_smooth=True
report['changes']['host_rock_skin']={'cells':len(cells),'room_boxes_kept_open':len(rooms),'nonmanifold_edges':0}
# A continuous deep rock volume closes the distant field behind the existing
# host cores. It is never used to replace rooms, towers, or their rear walls.
bm=bmesh.new();verts=[];NX,NZ=121,57
for j in range(NZ):
    z=-24+j*5.0
    row=[]
    for i in range(NX):
        x=-300+i*5.0
        y=113+4.0*math.sin(x*.039+z*.061)+2.0*math.sin(x*.11-z*.067)
        row.append(bm.verts.new((x,y,z)))
    verts.append(row)
for j in range(NZ-1):
    for i in range(NX-1):bm.faces.new((verts[j][i],verts[j+1][i],verts[j+1][i+1],verts[j][i+1]))
for f in bm.faces:f.smooth=True
edges=[e for e in bm.edges if e.is_boundary]
ext=bmesh.ops.extrude_edge_only(bm,edges=edges)
backverts=[v for v in ext['geom'] if isinstance(v,bmesh.types.BMVert)]
for v in backverts:v.co.y=151
backedges=[e for e in bm.edges if e.is_boundary]
bmesh.ops.holes_fill(bm,edges=backedges,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
mesh=bpy.data.meshes.new('COT_S4_DeepRock_data');bm.to_mesh(mesh);bm.free();mesh.materials.append(rock)
o=bpy.data.objects.new('COT_S4_DeepRock',mesh)
bpy.data.collections['COT_S4_FAR'].objects.link(o)
o['cot_s4']=True;o['cot_region']='_World';o['cot_evidence']='C: continuous thick distant cavern rock, behind all rooms';o['cot_amb']=[.12,.19,.34]
o['cot_layer']='DEEPROCK'
rc=bpy.data.collections.new('COT_S4_LINK_DeepRock');rc.objects.link(o)
L=AL.new_light(bpy.data.collections['COT_S4_LIGHTS'],'COT_S4_DeepRockWash','AREA',(0,80,180),(.32,.48,.82),90000,size=(500,180),rot=(math.pi/2,0,0),shadow=False)
L.light_linking.receiver_collection=rc
report['changes']['deep_rock']={'vertices':len(mesh.vertices),'faces':len(mesh.polygons),'evidence':'C','closed':True}
# Rain positions / shelter attributes remain unchanged. Shrink cross sections.
rain=[]
for o in bpy.data.objects:
    if o.get('cot_weather')!='rain' or o.type!='MESH':continue
    bm=bmesh.new();bm.from_mesh(o.data);seen=set()
    for v in bm.verts:
        if v in seen:continue
        todo=[v];seen.add(v);vs=[]
        while todo:
            a=todo.pop();vs.append(a)
            for e in a.link_edges:
                b=e.other_vert(a)
                if b not in seen:seen.add(b);todo.append(b)
        cx=sum(v.co.x for v in vs)/len(vs);cy=sum(v.co.y for v in vs)/len(vs)
        for v in vs:
            v.co.x=cx+(v.co.x-cx)*C['rain_radius_scale'];v.co.y=cy+(v.co.y-cy)*C['rain_radius_scale']
    bm.to_mesh(o.data);bm.free();o.data.update();rain.append(o.name)
AW.rain_material('MAT_S4_rain',C['rain_color'],C['rain_strength'],C['rain_alpha'])
report['changes']['rain']=rain
# Retire erroneous shafts (including glass furniture) and regenerate from windows.
old=[o for o in bpy.data.objects if o.get('cot_light_kind') in ('window','shaft') or o.name.startswith('COT_S4_ShaftAir_')]
for o in old:bpy.data.objects.remove(o,do_unlink=True)
w=dict(A['specials']['window_lights']);w.update(C['window'])
report['changes']['window_lights']=AS.window_lights(bpy.data.collections['COT_S4_LIGHTS'],w)
report['changes']['shaft_air']=len(AS.shaft_volumes(bpy.data.collections['COT_S4_FOG'],scene,w))
# Actual window accents in dark rooms (light-linked by region).
roomlights=[]
for rid,power in C['room_window_power'].items():
    coll=AL.coll('COT_S4_LIGHTS_'+rid,bpy.data.collections['COT_S4_LIGHTS'])
    for o in list(bpy.data.objects):
        if o.get('cot_region')!=rid or o.type!='MESH' or o.hide_render or not re.search(r'_B\d+_\d+$',o.name):continue
        if not any(s.material and s.material.name in ('MAT_S3_glass_purple','MAT_S3_glass_pink','MAT_S3_glass_blue') for s in o.material_slots):continue
        lo,hi=AS._bbox(o);size=hi-lo
        loc=Vector(((lo.x+hi.x)/2,lo.y-.35,(lo.z+hi.z)/2))
        L=AL.new_light(coll,'COT_S4_CloseWindow_'+o.name,'AREA',loc,C['room_window_color'][rid],power*size.x*size.z,size=(size.x*.85,size.z*.85),rot=(-math.pi/2,0,0),spread=70)
        L.light_linking.receiver_collection=bpy.data.collections['COT_S3_'+rid];roomlights.append(L.name)
report['changes']['room_lights']=len(roomlights)
# Cold-white tower glass keeps volume and frames; replace only glass slots.
tower=AM.make_material('MAT_S4_tower_glass',{'group':'Glass','Glow Color':[.62,.78,1.],'Glow Strength':1.15,'Base Color':[.012,.023,.044]})
for o in bpy.data.objects:
    if o.get('cot_region')=='EastTower' and o.type=='MESH':
        for s in o.material_slots:
            if s.material and s.material.name in ('MAT_S2_glass','MAT_S2_glass_pillar'):
                s.link='OBJECT';s.material=tower
# Reflective water lit from a broad source, without a luminous surface.
wc=AL.coll('COT_S4_LIGHTS_CentralWell',bpy.data.collections['COT_S4_LIGHTS'])
L=AL.new_light(wc,'COT_S4_CloseWater','AREA',(-10,48,42),(.42,.63,1.),14000,size=(85,60),rot=(0,0,0),shadow=True)
rc=bpy.data.collections.new('COT_S4_LINK_CloseWater')
for o in bpy.data.objects:
    if o.type=='MESH' and any(s.material and s.material.name=='MAT_S2_water' for s in o.material_slots) and not o.hide_render:rc.objects.link(o)
L.light_linking.receiver_collection=rc
water=bpy.data.materials['MAT_S2_water'];AM.assign_group(water,'NG_COT_Water',{'Base Color':(.012,.036,.065),'Roughness':.14,'Waves':.12,'Ripples':.22,'Ripple Scale':1.2,'Alpha':1.})
# Fade box fog to zero at all six faces; retain its interior density.
for mat in bpy.data.materials:
    if not mat.name.startswith('MAT_S4_air_') or 'PleasureStage' in mat.name:continue
    nt=mat.node_tree;vol=next((n for n in nt.nodes if n.type=='PRINCIPLED_VOLUME'),None)
    if not vol or vol.inputs['Density'].is_linked:continue
    density=vol.inputs['Density'].default_value;t=AM.T(nt)
    tc=t.node('ShaderNodeTexCoord');xyz=t.node('ShaderNodeSeparateXYZ');t.link(tc.outputs['Generated'],xyz.inputs[0])
    edge=None
    for key in ('X','Y','Z'):
        v=xyz.outputs[key];e=t.math('MINIMUM',v,t.math('SUBTRACT',1.,v))
        edge=e if edge is None else t.math('MINIMUM',edge,e)
    mask=t.math('MINIMUM',1.,t.math('MAXIMUM',0.,t.math('DIVIDE',edge,.14)))
    t.link(t.math('MULTIPLY',density,t.math('MULTIPLY',mask,mask)),vol.inputs['Density'])
# Reduce remaining fog-box boundary visibility by keeping mist restrained.
cam_data=bpy.data.cameras.new('CAM_S4_WaterCheck_data');cam=bpy.data.objects.new('CAM_S4_WaterCheck',cam_data)
bpy.data.collections['COT_S4_CAMERAS'].objects.link(cam)
cam.location=(-8,-32,6);cam.rotation_euler=(Vector((-8,30,-.45))-cam.location).to_track_quat('-Z','Y').to_euler();cam_data.lens=24
cam['cot_s4']=True;cam['cot_region']='CentralWell';cam['cot_kind']='check';cam['cot_res']='960x540';cam['cot_hide']='FRONT'
report['switch_problems']=art_switch.install(scene,C['mist_strength']);assert not report['switch_problems']
art_switch.set_weather(scene,True)
scene['cot_closeout']='2026-10-08 stage 4 local repairs; stage 5 not begun'
scene['cot_mar_integrated']=True
if bpy.data.objects.get('MAR_Root'):bpy.data.objects['MAR_Root']['cot_version']='v002'
for obj in bpy.data.objects:
    if obj.get('cot_mar_placed'):obj['cot_mar_asset']='Marissa_v002'
scene.camera=bpy.data.objects['CAM_S3__World_CityClosed']
scene.render.resolution_x=1920;scene.render.resolution_y=929;scene.frame_set(1)
out.parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(out))
report['output_sha256']=hashlib.sha256(out.read_bytes()).hexdigest()
p=ROOT/'_work/stage04/closeout/build_report.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('CLOSEOUT_SAVED',out)
