"""Render regression: Seams=0 must remove mortar even with Seam Depth > 0."""
import sys
from pathlib import Path
import bpy
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/build'))
import art_materials as AM
bpy.ops.wm.read_factory_settings(use_empty=True)
AM.build_groups({})
m=AM.make_material('test',{'group':'Stone','Base Color':[.3,.3,.3],'Seams':0.,'Seam Depth':.8,'Variation':0.,'Wear':0.})
bpy.ops.mesh.primitive_plane_add(size=6)
o=bpy.context.object;o.data.materials.append(m);o['cot_amb']=[1.,1.,1.]
bpy.ops.object.camera_add(location=(0,0,5))
scene=bpy.context.scene;scene.camera=bpy.context.object;scene.camera.data.type='ORTHO';scene.camera.data.ortho_scale=6
scene.render.engine='CYCLES';scene.cycles.samples=1;scene.cycles.use_denoising=False
scene.render.resolution_x=128;scene.render.resolution_y=128;scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard'
p=ROOT/'_work/stage04/closeout/seam_test';p.mkdir(parents=True,exist_ok=True)
g=next(n for n in m.node_tree.nodes if n.type=='GROUP')
imgs=[]
for depth in (.8,0.):
    g.inputs['Seam Depth'].default_value=depth
    scene.render.filepath=str(p/f'{depth}.png');bpy.ops.render.render(write_still=True)
    im=bpy.data.images.load(scene.render.filepath,check_existing=False)
    imgs.append(np.array(im.pixels[:]))
delta=float(np.max(np.abs(imgs[0]-imgs[1])))
print('SEAM_OFF_MAX_DELTA',delta)
assert delta < .001, 'Seams=0 still shows mortar from Seam Depth'
