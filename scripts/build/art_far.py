"""Stage 4 far layer: a band of simplified shell towers between the city and the back cave wall, with clusters of
lit leaf windows, so the wells keep three depths (near city, stage 2/3 back towers, this far band) and a moving
camera sees them slide against each other. Real volumes (cylindrical cores, bell tiers, window panes with frames),
not cards; all evidence C (three-dimensional completion: the references show blue towers fading into the haze
behind the wells, positions are not known). Placement is checked by ray casts: a tower is kept only where its
footprint is free of existing geometry from its base to its top.
"""
import math
import random

import bmesh
import bpy
from mathutils import Vector


def _tower_mesh(name, height, radius, tiers, rnd, glass_slots):
    """Core + bell tiers (slot 0 core, 1 tier) + leaf panes on the tiers (slot 2 blue glass, 3 pink glass)."""
    bm = bmesh.new()
    seg = 16
    # core
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=radius * 0.62, radius2=radius * 0.5, depth=height)
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = 0
    bmesh.ops.translate(bm, verts=res["verts"], vec=(0, 0, height / 2))
    # tiers: bells hanging down from rings, wider low, narrower high
    for k in range(tiers):
        t = (k + 0.6) / tiers
        z = height * (0.18 + 0.78 * t)
        r = radius * (1.15 - 0.45 * t) * rnd.uniform(0.92, 1.08)
        h = height / tiers * 0.85
        res = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r * 0.55, depth=h)
        for f in {f for v in res["verts"] for f in v.link_faces}:
            f.material_index = 1
        bmesh.ops.translate(bm, verts=res["verts"], vec=(0, 0, z - h / 2))
        # leaf panes on the front half of the tier
        for j in range(rnd.randint(1, 3)):
            a = math.radians(rnd.uniform(-70, 70)) - math.pi / 2
            pw, ph = r * 0.32, h * 0.62
            cx, cy = (r * 0.82) * math.cos(a), (r * 0.82) * math.sin(a)
            nrm = Vector((math.cos(a), math.sin(a), 0))
            side = Vector((-nrm.y, nrm.x, 0))
            pts = []
            for s in range(12):
                u = s / 11.0
                wv = math.sin(u * math.pi) * pw / 2
                pts.append((u, wv))
            ring = [Vector((cx, cy, z - h * 0.55)) + nrm * 0.05 + side * w + Vector((0, 0, (u - 0.5) * ph)) for u, w in pts] + \
                   [Vector((cx, cy, z - h * 0.55)) + nrm * 0.05 - side * w + Vector((0, 0, (u - 0.5) * ph)) for u, w in reversed(pts[1:-1])]
            verts = [bm.verts.new(p) for p in ring]
            face = bm.faces.new(verts)
            face.material_index = 3 if rnd.random() < glass_slots.get("pink_share", 0.12) else 2
            ext = bmesh.ops.extrude_face_region(bm, geom=[face])
            moved = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
            bmesh.ops.translate(bm, verts=moved, vec=nrm * 0.12)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def build(coll, cfg, seed, caster):
    rnd = random.Random(seed + 31)
    mats = [bpy.data.materials["MAT_S2_tower_core"], bpy.data.materials["MAT_S2_tower_far"],
            bpy.data.materials["MAT_S2_glass_far_blue"], bpy.data.materials["MAT_S2_glass_far"]]
    made, rejected = [], 0
    for band in cfg["bands"]:
        x0, x1 = band["x"]
        n = band["count"]
        tries = 0
        while sum(1 for m in made if m["band"] == band["name"]) < n and tries < n * 8:
            tries += 1
            x = rnd.uniform(x0, x1)
            y = rnd.uniform(*band["y"])
            r = rnd.uniform(*band["radius"])
            h = rnd.uniform(*band["height"])
            z0 = band["z0"]
            # footprint free from the base to the top: eight vertical probes around and one at the centre
            clear = True
            for k in range(9):
                a = 2 * math.pi * k / 8
                px, py = (x, y) if k == 8 else (x + r * 1.2 * math.cos(a), y + r * 1.2 * math.sin(a))
                hit = caster.cast((px, py, z0 + 3.0), (0, 0, 1), h - 3.0)
                if hit is not None:
                    clear = False
                    break
            if clear:                                   # nothing standing between it and the city at mid height
                for zz in (z0 + h * 0.3, z0 + h * 0.7):
                    hit = caster.cast((x, y - r * 1.2, zz), (0, 1, 0), r * 2.4)
                    if hit is not None:
                        clear = False
                        break
            if not clear or any((Vector((x, y)) - Vector((m["x"], m["y"]))).length < (r + m["r"]) * 1.1 for m in made):
                rejected += 1
                continue
            name = f"COT_S4_FarTower_{band['name']}_{len(made):02d}"
            mesh = _tower_mesh(name + "_data", h, r, max(3, int(h / band.get("tier_height", 14.0))), rnd, cfg)
            for m in mats:
                mesh.materials.append(m)
            obj = bpy.data.objects.new(name, mesh)
            obj.location = (x, y, z0)
            obj.rotation_euler.z = math.radians(rnd.uniform(-15, 15))
            obj["cot_s4"] = True
            obj["cot_region"] = band.get("region", "_World")
            obj["cot_layer"] = "BACKDROP"
            obj["cot_evidence"] = "C"
            obj["cot_ref"] = "15_Background, 03_Left_City total: blue towers fading into haze behind the wells; positions are completion"
            coll.objects.link(obj)
            made.append({"name": name, "band": band["name"], "x": x, "y": y, "r": r, "h": h})
    return {"towers": len(made), "rejected": rejected, "list": [{k: (round(v, 1) if isinstance(v, float) else v) for k, v in m.items()} for m in made]}
