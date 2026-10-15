"""Independent audit of the saved v010 animation: timeline, markers, every camera frame incl. dissolve handles.

blender -b scenes/city_animation_v010.blend --python scripts/qa/check_film_v010.py
Checks per frame: camera centre + near-plane corners clearance (>= 0.2 H), path segment intersection,
speed, angular speed, roll, focus continuity. Weather excluded (not collision geometry). Read-only.
"""
import bpy, json, math, hashlib, sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
c = json.loads((ROOT / 'config/shots_v010.json').read_text(encoding='utf-8'))
s = bpy.context.scene
def exclude_weather(lc):
    if lc.name in ('COT_S2_WEATHER', 'COT_S4_WEATHER', 'COT_S4_FOG'): lc.exclude = True
    for ch in lc.children: exclude_weather(ch)
exclude_weather(bpy.context.view_layer.layer_collection)
dg = bpy.context.evaluated_depsgraph_get()
assert (s.frame_start, s.frame_end, s.render.fps, s.render.fps_base) == (1, 4272, 24, 1)
markers = sorted([m for m in s.timeline_markers if m.camera], key=lambda m: m.frame)
assert [(m.frame, m.camera.name) for m in markers] == [(t['frame_start'], t['camera']) for t in c['takes']]
shapes = []
for o in s.objects:
    if o.type not in ('MESH', 'CURVE') or o.hide_render or any(co.hide_render for co in o.users_collection): continue
    if o.get('cot_weather') or any(co.name in ('COT_S2_WEATHER', 'COT_S4_WEATHER', 'COT_S4_FOG') for co in o.users_collection): continue
    if o.name.startswith(('COT_S4_Rain', 'COT_S4_Fog', 'COT_S4_Beam')): continue
    if o.type == 'MESH' and o.data.materials and all(m and m.node_tree and any(n.type in ('VOLUME_PRINCIPLED', 'VOLUME_SCATTER', 'VOLUME_ABSORPTION') for n in m.node_tree.nodes) for m in o.data.materials): continue
    pts = [o.matrix_world @ Vector(v) for v in o.bound_box]
    shapes.append((o, Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])))
report = dict(blend=bpy.data.filepath, blend_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
              timeline='PASS', markers=len(markers), takes=[],
              method='Saved file evaluated at every frame of each take incl. dissolve handles; BVH of evaluated static visible geometry, '
                     'centre + near-plane corners within 0.2 H and segment ray test. Supplements visual review, not continuous viewing.')
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
only=args[args.index('--takes')+1].split(',') if '--takes' in args else [t['id'] for t in c['takes']]
for tk in c['takes']:
    if tk['id'] not in only: continue
    cam = bpy.data.objects[tk['camera']]
    f0 = tk['frame_start'] - tk['handle_in']; f1 = tk['frame_end'] + tk['handle_out']
    P, Q, foc, lens = [], [], [], []
    for f in range(f0, f1 + 1):
        s.frame_set(f); ec = cam.evaluated_get(dg); m = ec.matrix_world.copy()
        P.append(m.translation.copy()); Q.append(m.to_quaternion())
        foc.append((cam.data.dof.focus_object.evaluated_get(dg).matrix_world.translation - m.translation).length)
        lens.append(cam.data.lens)
    lo = Vector([min(p[i] for p in P) - 1 for i in range(3)]); hi = Vector([max(p[i] for p in P) + 1 for i in range(3)])
    trees = []
    for o, ol, oh in shapes:
        if any(oh[i] < lo[i] or ol[i] > hi[i] for i in range(3)): continue
        eo = o.evaluated_get(dg); me = eo.to_mesh(); me.calc_loop_triangles()
        if me.loop_triangles: trees.append((o.name, BVHTree.FromPolygons([eo.matrix_world @ v.co for v in me.vertices], [tuple(t.vertices) for t in me.loop_triangles], all_triangles=True)))
        eo.to_mesh_clear()
    issues = []; mind = 1e9; nearest = ''
    for i, p in enumerate(P):
        q = Q[i]; r = q @ Vector((1, 0, 0)); u = q @ Vector((0, 1, 0)); fw = q @ Vector((0, 0, -1))
        half = cam.data.clip_start * 36 / (2 * lens[i])
        samples = [p] + [p + fw * cam.data.clip_start + r * x * half + u * y * half * 9 / 16 for x in (-1, 1) for y in (-1, 1)]
        for name, tree in trees:
            hit = tree.find_nearest(p, 1.0)
            if hit[0] is not None and hit[3] < mind: mind = hit[3]; nearest = name
            if any(tree.find_nearest(v, 0.2)[0] is not None for v in samples): issues.append(dict(frame=f0 + i, object=name, reason='within 0.2 H')); break
        if i:
            d = p - P[i - 1]
            if d.length > 0:
                for name, tree in trees:
                    if tree.ray_cast(P[i - 1], d.normalized(), d.length)[0] is not None: issues.append(dict(frame=f0 + i, object=name, reason='segment')); break
    sp = [(P[i] - P[i - 1]).length * 24 for i in range(1, len(P))]
    fwd = [q @ Vector((0, 0, -1)) for q in Q]
    ang = [math.degrees(fwd[i].angle(fwd[i - 1])) * 24 for i in range(1, len(fwd))]
    roll = [math.degrees(math.asin(max(-1, min(1, (q @ Vector((1, 0, 0))).z)))) for q in Q]
    item = dict(id=tk['id'], camera=tk['camera'], frames=[tk['frame_start'], tk['frame_end']], rendered=[f0, f1],
                max_speed_H_s=round(max(sp), 2), mean_speed_H_s=round(sum(sp) / len(sp), 2), max_angular_deg_s=round(max(ang), 1),
                p95_angular_deg_s=round(sorted(ang)[int(len(ang) * 0.95)], 1), max_abs_roll_deg=round(max(abs(x) for x in roll), 2),
                focus_range=[round(min(foc), 2), round(max(foc), 2)], max_focus_step=round(max(abs(foc[i] - foc[i - 1]) for i in range(1, len(foc))), 3),
                lens_range=[round(min(lens), 1), round(max(lens), 1)], min_distance_H=round(mind, 3), nearest=nearest,
                issues=len(issues), examples=issues[:20], result='PASS' if not issues else 'FAIL')
    report['takes'].append(item); print('V010_QA', json.dumps(item, ensure_ascii=False), flush=True)
out = ROOT / '_work/stage05_v010/animation_audit_v010.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
print('V010_AUDIT_DONE', all(t['result'] == 'PASS' for t in report['takes']), flush=True)
