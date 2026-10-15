"""Replace only upper left wall skins with the same skins pierced by 14 windows."""
import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cot_geo import Geo,place

def hull(points):
    pts=sorted(set((round(y,6),round(z,6)) for y,z in points))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lower=[];upper=[]
    for p in pts:
        while len(lower)>1 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper)>1 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
        upper.append(p)
    return lower[:-1]+upper[:-1]

def apply():
    wall=bpy.data.objects['S3_SoulSanctum_MainWest_Walls']
    assert not wall.get('cot_s4_window_openings'), 'Run from preserved base'
    panes=sorted((o for o in bpy.data.objects if o.name.startswith('S3_SoulSanctum_MainWest_XWinL_6_')),key=lambda o:o.name)
    assert len(panes)==14
    room=max(json.loads(wall['cot_rooms']),key=lambda r:r[4]);inner=room[0]
    bm=bmesh.new();bm.from_mesh(wall.data);bm.verts.ensure_lookup_table()
    # Storeys share welded corner vertices. Select the actual two box skins by
    # their corner planes, rather than deleting a connected component.
    def near(v,planes):return any(abs(v-p)<.001 for p in planes)
    selected_faces=[f for f in bm.faces if all(near(p.x,(inner-.6,inner-.46,inner)) and near(p.y,(room[2]-.4,room[3]+.6)) and near(p.z,(room[4],room[5])) for p in (wall.matrix_world@v.co for v in f.verts))]
    assert 10<=len(selected_faces)<=14,len(selected_faces)
    selected={v for f in selected_faces for v in f.verts}
    parts=[(list(selected),[wall.matrix_world@v.co for v in selected])]
    profiles=[];centres=[]
    for pane in panes:
        ids={v for f in pane.data.polygons if pane.material_slots[f.material_index].material.name=='MAT_S3_glass_white' for v in f.vertices}
        ps=[pane.matrix_world@pane.data.vertices[v].co for v in ids]
        poly=hull((p.y,p.z) for p in ps);assert len(poly)>4
        cy=(min(y for y,z in poly)+max(y for y,z in poly))/2;cz=(min(z for y,z in poly)+max(z for y,z in poly))/2
        poly=[(cy+(y-cy)*1.02,cz+(z-cz)*1.02) for y,z in poly]
        start=min(range(len(poly)),key=lambda i:(poly[i][1],-poly[i][0]));stop=min(range(len(poly)),key=lambda i:(poly[i][1],poly[i][0]))
        arc=[];i=start
        while True:
            arc.append(poly[i])
            if i==stop:break
            i=(i+1)%len(poly)
        profiles.append((cy,arc));centres.append((pane.name,cy,cz))
    g=Geo()
    for component,ps in parts:
        xa,xb=min(p.x for p in ps),max(p.x for p in ps);ya,yb=min(p.y for p in ps),max(p.y for p in ps);za,zb=min(p.z for p in ps),max(p.z for p in ps)
        slots={f.material_index for f in selected_faces}
        xs=[]
        for x in sorted(p.x for p in ps):
            if not xs or x-xs[-1]>1e-4:xs.append(x)
        assert len(xs) in (2,3),xs
        bounds=xs if len(xs)==3 else [xa,xb]
        faces=set(selected_faces)
        for la,lb in zip(bounds,bounds[1:]):
            sample=la if la==bounds[0] else lb
            candidates=[f for f in faces if all(abs((wall.matrix_world@v.co).x-sample)<1e-4 for v in f.verts)]
            slot=max(candidates,key=lambda f:f.calc_area()).material_index if candidates else min(slots)
            g.use(slot);m=place(lb,0,0,rz=math.pi/2)
            edges=[ya]+[(a[0]+b[0])/2 for a,b in zip(profiles,profiles[1:])]+[yb]
            for (a,b),(cy,arc) in zip(zip(edges,edges[1:]),profiles):
                sill=arc[0][1];g.box(a,b,0,lb-la,za,sill,m=m)
                g.prism([(a,sill),(a,zb),(b,zb),(b,sill)]+arc,0,lb-la,m=m)
    for f in selected_faces:bm.faces.remove(f)
    for e in list(bm.edges):
        if not e.link_faces:bm.edges.remove(e)
    for v in list(bm.verts):
        if not v.link_edges:bm.verts.remove(v)
    inverse=wall.matrix_world.inverted()
    mapping={v:bm.verts.new(inverse@v.co) for v in g.bm.verts}
    for f in g.bm.faces:
        face=bm.faces.new(tuple(mapping[v] for v in f.verts));face.material_index=g.keys[f.material_index]
    wall.data=wall.data.copy();bm.to_mesh(wall.data);bm.free();g.bm.free()
    added=[]
    for pane in panes:
        ids={v for f in pane.data.polygons if pane.material_slots[f.material_index].material.name=='MAT_S3_glass_white' for v in f.vertices}
        px=sum((pane.matrix_world@pane.data.vertices[v].co).x for v in ids)/len(ids)
        o=pane.copy();o.name='COT_S4_InnerWindow_'+pane.name.removeprefix('S3_SoulSanctum_');o.location.x+=inner+.015-px
        o['cot_s4']=True;o['cot_region']='SoulSanctum';o['cot_evidence']='C: inner lining of a through opening matching existing exterior window'
        bpy.data.collections['COT_S3_SoulSanctum'].objects.link(o);added.append(o.name)
    wall['cot_s4_window_openings']=json.dumps([p.name for p in panes]);wall['cot_evidence_window_openings']='C: local 3D completion; exterior silhouette retained'
    bpy.context.view_layer.update()
    tree=BVHTree.FromPolygons([wall.matrix_world@v.co for v in wall.data.vertices],[tuple(p.vertices) for p in wall.data.polygons]);hits=[]
    for name,y,z in centres:
        loc,normal,index,distance=tree.ray_cast(Vector((inner-1.6,y,z)),Vector((1,0,0)),2.2)
        hits.append({'pane':name,'wall_hit_in_opening':index is not None})
    assert not any(h['wall_hit_in_opening'] for h in hits),hits
    return {'wall':wall.name,'openings':14,'inner_windows':added,'rays':hits,'evidence':'C'}
