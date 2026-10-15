"""Stage 4 region accents: per-region material overrides, window light, stage / accent spots, floating motes and
local volumes (light shafts). Everything is driven by config/art.json "specials"; all objects carry cot_s4.

* Material overrides: a stage 3 room that reused a stage 2 material meant for an exterior mask (e.g. the near-black
  house wall) gets its region's wall material on the object's own slot (slot link = OBJECT), so shared mesh data and
  the stage 2 plaza stay untouched.
* Window light: every pane of a window material taller than min_height gets a rectangle light just inside it, facing
  the room (back-wall panes face -Y, viewer-side panes +Y, side panes toward the region centre), with a narrow spread,
  so tall cold-white windows really throw light into the hall; inside a local volume this reads as vertical shafts.
* Motes: tiny emissive spheres (one mesh per region) = the sparse small lights of the cluster caves; static.
"""
import math
import random
import re

import bmesh
import bpy
from mathutils import Vector

import art_lights as AL


def material_overrides(over):
    n = 0
    for rid, table in over.items():                         # rid "*" = every region (stage 3 objects only)
        for o in bpy.data.objects:
            if (rid != "*" and o.get("cot_region") != rid) or not o.get("cot_s3") or o.type not in ("MESH", "CURVE"):
                continue
            for slot in o.material_slots:
                if slot.material is not None and slot.material.name in table:
                    new = bpy.data.materials.get(table[slot.material.name])
                    if new is None:
                        raise KeyError(table[slot.material.name])
                    slot.link = "OBJECT"
                    slot.material = new
                    n += 1
    return n


def lamp_props(items):
    """Hang linked copies of an existing stage 3 lamp in rooms the structure left without any light fixture; the copies
    keep the template's custom properties (cot_s3, lamp material), so build_lamp_lights gives them real lights.
    item: {"template": object name, "region": rid, "ceiling": z, "points": [[x, y], ...]}"""
    made = []
    for it in items:
        src = bpy.data.objects.get(it["template"])
        if src is None:
            raise KeyError(it["template"])
        top = max((src.matrix_world @ Vector(c)).z for c in src.bound_box) - src.matrix_world.translation.z
        coll = bpy.data.collections["COT_S3_" + it["region"]]
        for k, (x, y) in enumerate(it["points"]):
            o = src.copy()                                   # linked duplicate: shares the mesh
            o.name = f"S4_{it['region']}_HungLamp_{k:02d}"
            o.location = Vector((x, y, it["ceiling"] - 0.02 - top))
            o["cot_region"] = it["region"]
            o["cot_s4"] = True
            o["cot_s4_note"] = "art-stage lamp (room had no fixture)"
            o["cot_lamp_gain"] = float(it.get("gain", 1.0))            # read by art_lights.lamp_sites
            coll.objects.link(o)
            made.append(o.name)
    bpy.context.view_layer.update()      # matrix_world of the copies, read by lamp_sites right after (v013 put the lights at the template)
    return made


def _bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def window_lights(root, spec):
    made = 0
    mat = bpy.data.materials.get(spec["material"])
    for rid in spec["regions"]:
        b = AL.region_bounds(rid)
        if b is None:
            continue
        centre = (b[0] + b[1]) / 2
        c = AL.coll(f"COT_S4_LIGHTS_{rid}", root)
        for o in bpy.data.objects:
            if o.get("cot_region") != rid or o.type != "MESH" or o.hide_render or mat not in [s.material for s in o.material_slots]:
                continue
            # Furniture can contain a glass insert; only actual wall windows emit window light.
            if not re.search(r"_(?:B\d+_\d+|XWin[LRN]_\d+_\d+)$", o.name):
                continue
            lo, hi = _bbox(o)
            size = hi - lo
            if size.z < spec["min_height"]:
                continue
            if size.y <= size.x:                     # pane in an X-Z wall
                # _B panes are in this stack's rear wall; a region can contain
                # several stacks at different depths, so its centre is unsuitable.
                d = -1.0 if re.search(r'_B\d+_\d+$',o.name) or (lo.y + hi.y) / 2 > centre.y else 1.0
                rot = (math.radians(90), 0.0, 0.0) if d > 0 else (math.radians(-90), 0.0, 0.0)
                loc = Vector(((lo.x + hi.x) / 2, (hi.y if d > 0 else lo.y) + 0.35 * d, (lo.z + hi.z) / 2))
                w = size.x
            else:                                    # pane in a Y-Z wall
                # Side-window labels belong to their own stack, not the whole region.
                side = re.search(r'_XWin([LR])_', o.name)
                d = (1.0 if side.group(1) == 'L' else -1.0) if side else (-1.0 if (lo.x + hi.x) / 2 > centre.x else 1.0)
                rot = (0.0, math.radians(-90 if d > 0 else 90), 0.0)
                loc = Vector(((hi.x if d > 0 else lo.x) + 0.35 * d, (lo.y + hi.y) / 2, (lo.z + hi.z) / 2))
                w = size.y
            h = size.z
            AL.new_light(c, f"COT_S4_Window_{rid}_{made:04d}", "AREA", loc, spec["color"], spec["power_per_m2"] * w * h,
                         size=(max(0.2, w * 0.9), h * 0.95), rot=rot, shadow=True, spread=spec["spread"],
                         props={"cot_region": rid, "cot_light_kind": "window", "cot_window": o.name})
            extra = any(o.name.startswith(p) for p in spec.get('shaft_extra_prefixes', []))
            if spec.get("down_power") and h >= spec.get("down_min_height", 5.0) and rid in spec.get("shaft_regions", spec["regions"]) and ('_XWin' not in o.name or extra):
                # cold white vertical shaft: a narrow spot just inside the window top, straight down to the floor;
                # in the hall's thin air volume it reads as the vertical light of Soul_Sanctuary_core.jpg
                top = Vector((loc.x, loc.y, hi.z - 0.3))
                inward = Vector((0.0, d, 0.0)) if size.y <= size.x else Vector((d, 0.0, 0.0))
                top += inward * 1.2
                # tilted into the room (shaft_tilt = horizontal run per metre of fall): the beam crosses open air and
                # lands on the floor away from the wall, instead of grazing the wall under the window
                direction = (Vector((0.0, 0.0, -1.0)) + inward * spec.get("shaft_tilt", 0.0)).normalized()
                rot = direction.to_track_quat("-Z", "Y").to_euler()
                s = AL.new_light(c, f"COT_S4_Shaft_{rid}_{made:04d}", "SPOT", top, spec["color"], spec["down_power"] * w,
                                 radius=w * spec.get('down_radius_scale',0.3), rot=tuple(rot), shadow=True,
                                 props={"cot_region": rid, "cot_light_kind": "shaft", "cot_window": o.name})
                s.data.spot_size = math.radians(spec.get("down_angle", 16.0))
                s.data.spot_blend = 0.45
            made += 1
    return made


def spots(root, items):
    out = []
    for s in items:
        c = AL.coll(f"COT_S4_LIGHTS_{s['region']}", root)
        loc, tgt = Vector(s["loc"]), Vector(s["target"])
        rot = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
        L = AL.new_light(c, f"COT_S4_Spot_{s['name']}", "SPOT", loc, s["color"], s["power"], radius=s.get("radius", 0.3), rot=rot,
                         props={"cot_region": s["region"], "cot_light_kind": "accent", "cot_note": s.get("note", "")})
        L.data.spot_size = math.radians(s.get("angle", 40.0))
        L.data.spot_blend = s.get("blend", 0.5)
        if s.get("link_region"):
            L.light_linking.receiver_collection = bpy.data.collections["COT_S3_" + s["region"]]
        if s.get("link_box"):
            # light only the region's objects whose bounds centre lies in the box (e.g. the stage, not the audience)
            lo, hi = Vector(s["link_box"][0]), Vector(s["link_box"][1])
            rc = bpy.data.collections.get(f"COT_S4_LINK_{s['name']}") or bpy.data.collections.new(f"COT_S4_LINK_{s['name']}")
            for o in [o for o in bpy.data.objects if o.get("cot_region") == s["region"] and o.type in ("MESH", "CURVE")]:
                b0, b1 = _bbox(o)
                c = (b0 + b1) / 2
                inside = lo.x <= c.x <= hi.x and lo.y <= c.y <= hi.y and lo.z <= c.z <= hi.z
                if (inside or (s.get("link_prop") and o.get(s["link_prop"]))) and o.name not in rc.objects:
                    rc.objects.link(o)
            L.light_linking.receiver_collection = rc
            L["cot_link_count"] = len(rc.objects)
        out.append(L.name)
    return out


def motes(root, items, seed):
    rnd = random.Random(seed + 23)
    out = {}
    for m in items:
        b = AL.region_bounds(m["region"])
        if b is None:
            continue
        lo, hi = b
        bm = bmesh.new()
        for _ in range(m["count"]):
            p = Vector((rnd.uniform(lo.x, hi.x), rnd.uniform(lo.y, min(hi.y, lo.y + m.get("depth", 40.0))), rnd.uniform(lo.z + 0.5, hi.z)))
            r = m["radius"] * rnd.uniform(0.6, 1.4)
            res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
            bmesh.ops.translate(bm, verts=res["verts"], vec=p)
        mesh = bpy.data.meshes.new(f"COT_S4_Motes_{m['region']}_data")
        bm.to_mesh(mesh)
        bm.free()
        mat = bpy.data.materials.get(f"MAT_S4_mote_{m['region']}") or bpy.data.materials.new(f"MAT_S4_mote_{m['region']}")
        import art_materials as AM
        AM.assign_group(mat, "NG_COT_Emit", {"Color": m["color"], "Strength": m["strength"], "Base Color": m["color"]})
        mesh.materials.append(mat)
        obj = bpy.data.objects.new(f"COT_S4_Motes_{m['region']}", mesh)
        obj.visible_shadow = False
        obj["cot_s4"] = True
        obj["cot_region"] = m["region"]
        AL.coll(f"COT_S4_LIGHTS_{m['region']}", root).objects.link(obj)
        out[m["region"]] = m["count"]
    return out


def _shaft_material(spec):
    """Shared beam air: density falls off radially (object space, radius in cot_beam_r) and toward the floor
    (cot_beam_len), so a beam has no hard cylinder edge and is densest just under the window."""
    mat = bpy.data.materials.get("MAT_S4_shaft_air") or bpy.data.materials.new("MAT_S4_shaft_air")
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    def m(op, a, b=0.0, clamp=False):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation, n.use_clamp = op, clamp
        for s, v in zip(n.inputs, (a, b)):
            if isinstance(v, bpy.types.NodeSocket):
                nt.links.new(v, s)
            else:
                s.default_value = v
        return n.outputs[0]

    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    r_at = nt.nodes.new("ShaderNodeAttribute")
    r_at.attribute_type, r_at.attribute_name = "OBJECT", "cot_beam_r"
    l_at = nt.nodes.new("ShaderNodeAttribute")
    l_at.attribute_type, l_at.attribute_name = "OBJECT", "cot_beam_len"
    rad = m("SQRT", m("ADD", m("MULTIPLY", sep.outputs["X"], sep.outputs["X"]), m("MULTIPLY", sep.outputs["Y"], sep.outputs["Y"])))
    radial = m("POWER", m("SUBTRACT", 1.0, m("DIVIDE", rad, r_at.outputs["Fac"]), clamp=True), 1.5)
    along = m("DIVIDE", m("MULTIPLY", sep.outputs["Z"], -1.0), l_at.outputs["Fac"], clamp=True)      # 0 at the top, 1 at the floor
    vert = m("MULTIPLY", m("SUBTRACT", 1.0, m("MULTIPLY", along, 0.7)), m("MINIMUM", m("DIVIDE", m("MULTIPLY", sep.outputs["Z"], -1.0), 1.0, clamp=True), 1.0))
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (*spec.get("shaft_color", spec["color"]), 1.0)
    vol.inputs["Anisotropy"].default_value = spec.get("shaft_anisotropy", 0.3)
    nt.links.new(m("MULTIPLY", m("MULTIPLY", radial, vert), spec["shaft_density"]), vol.inputs["Density"])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    mat["cot_s4"] = True
    return mat


def shaft_volumes(fog_coll, scene, spec):
    """A thin air column under every shaft spot (window top to the floor found by a ray): the spot's light scatters in
    it and reads as the cold-white vertical light of the sanctum, while the rest of the hall keeps clear air."""
    if not spec.get("shaft_density"):
        return []
    mat = _shaft_material(spec)
    was = fog_coll.hide_viewport
    fog_coll.hide_viewport = True
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    tan_half = math.tan(math.radians(spec.get("down_angle", 16.0)) / 2)
    made = []
    for s in [o for o in bpy.data.objects if o.get("cot_light_kind") == "shaft"]:
        top = s.matrix_world.translation.copy()
        axis = (s.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()     # the spot's beam direction
        hit, loc, _n, _i, _o, _m = scene.ray_cast(dg, top + axis * 0.05, axis, distance=80.0)
        length = (loc - top).length if hit else 20.0
        r = s.data.shadow_soft_size + length * tan_half * 1.15
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=r, radius2=r, depth=length)
        bmesh.ops.translate(bm, verts=bm.verts, vec=Vector((0, 0, -length / 2)))
        mesh = bpy.data.meshes.new(s.name.replace("Shaft", "ShaftAir") + "_data")
        bm.to_mesh(mesh)
        bm.free()
        mesh.materials.append(mat)
        obj = bpy.data.objects.new(s.name.replace("Shaft", "ShaftAir"), mesh)
        obj.location = top
        obj.rotation_euler = s.matrix_world.to_euler()        # column local -Z follows the tilted beam
        obj.display_type = "WIRE"
        obj.visible_shadow = False
        obj["cot_s4"] = True
        obj["cot_weather"] = "fog"
        obj["cot_region"] = s.get("cot_region")
        obj["cot_beam_r"] = r
        obj["cot_beam_len"] = length
        fog_coll.objects.link(obj)
        made.append(obj.name)
    fog_coll.hide_viewport = was
    return made


def _beam_material(name, b, r0, tan_half, length):
    """Air of one visible beam (object space: the beam runs down local -Z from the lamp). Density is highest on the axis
    and falls to 0 at the cone wall (radius r0 + d * tan_half at distance d), fades in over the first metres below the
    lamp (the beam comes out of the dark, no hard start) and out toward the far end."""
    mat = bpy.data.materials.get(f"MAT_S4_beam_{name}") or bpy.data.materials.new(f"MAT_S4_beam_{name}")
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    def m(op, a, c=0.0, clamp=False):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation, n.use_clamp = op, clamp
        for s, v in zip(n.inputs, (a, c)):
            if isinstance(v, bpy.types.NodeSocket):
                nt.links.new(v, s)
            else:
                s.default_value = v
        return n.outputs[0]

    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    d = m("MULTIPLY", sep.outputs["Z"], -1.0)                                         # distance below the lamp
    rad = m("SQRT", m("ADD", m("MULTIPLY", sep.outputs["X"], sep.outputs["X"]), m("MULTIPLY", sep.outputs["Y"], sep.outputs["Y"])))
    r_d = m("ADD", m("MULTIPLY", d, tan_half), r0)
    radial = m("POWER", m("SUBTRACT", 1.0, m("DIVIDE", rad, r_d), clamp=True), b.get("falloff", 1.6))
    fade_in = m("DIVIDE", d, b.get("fade_in", 1.5), clamp=True)
    fade_out = m("DIVIDE", m("SUBTRACT", length, d), max(0.01, length * b.get("fade_out", 0.35)), clamp=True)
    dens = m("MULTIPLY", m("MULTIPLY", m("MULTIPLY", radial, fade_in), fade_out), b["density"])
    if b.get("clear"):
        # no beam air in a soft ellipsoid round the lit figure (world space): a dense shaft would veil her; the beams
        # read as converging on her and carry on past her to the stage, while she stays crisp
        cx, cy, cz, rxy, rz, soft = b["clear"]
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sw = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sw.inputs[0])
        q = m("ADD", m("ADD", m("POWER", m("DIVIDE", m("SUBTRACT", sw.outputs["X"], cx), rxy), 2.0),
                       m("POWER", m("DIVIDE", m("SUBTRACT", sw.outputs["Y"], cy), rxy), 2.0)),
              m("POWER", m("DIVIDE", m("SUBTRACT", sw.outputs["Z"], cz), rz), 2.0))
        keep = m("DIVIDE", m("SUBTRACT", m("SQRT", q), 1.0), soft, clamp=True)
        dens = m("MULTIPLY", dens, m("MULTIPLY", keep, keep))
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (*b.get("color", (1.0, 1.0, 1.0)), 1.0)
    vol.inputs["Anisotropy"].default_value = b.get("anisotropy", 0.1)
    nt.links.new(dens, vol.inputs["Density"])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    mat["cot_s4"] = True
    return mat


def beam_volumes(fog_coll, scene, items):
    """Visible stage beams: for every spot with a "beam" entry, a cone of air along the spot's axis from the lamp to the
    first surface the axis meets beyond its target (objects carrying the spot's link_prop, e.g. the singer, do not stop
    it, so the beam goes on past her to the stage). The cone joins the spot's light-link collection, so only that
    spot lights it: the shaft reads clearly while the rest of the room keeps its own thin air."""
    made = []
    skip = [o for o in bpy.data.objects if any(s.get("link_prop") and o.get(s["link_prop"]) for s in items if s.get("beam"))
            and o.type in ("MESH", "CURVE") and not o.hide_viewport]
    was = fog_coll.hide_viewport
    fog_coll.hide_viewport = True
    for o in skip:
        o.hide_viewport = True
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    for s in [s for s in items if s.get("beam")]:
        b = s["beam"]
        L = bpy.data.objects.get(f"COT_S4_Spot_{s['name']}")
        if L is None:
            continue
        top = Vector(s["loc"])
        axis = (Vector(s["target"]) - top).normalized()
        hit, loc, _n, _i, hit_obj, _m = scene.ray_cast(dg, top + axis * 0.05, axis, distance=60.0)
        length = min((loc - top).length if hit else 20.0, b.get("max_length", 30.0))
        tan_half = math.tan(math.radians(s.get("angle", 30.0)) / 2) * b.get("spread", 1.0)
        r0 = s.get("radius", 0.3)
        bm = bmesh.new()
        r_end = r0 + length * tan_half
        bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=r_end * 1.05, radius2=r0 * 1.05, depth=length)
        bmesh.ops.translate(bm, verts=bm.verts, vec=Vector((0, 0, -length / 2)))
        mesh = bpy.data.meshes.new(f"COT_S4_BeamAir_{s['name']}_data")
        bm.to_mesh(mesh)
        bm.free()
        mesh.materials.append(_beam_material(s["name"], b, r0, tan_half, length))
        obj = bpy.data.objects.new(f"COT_S4_BeamAir_{s['name']}", mesh)
        obj.location = top
        obj.rotation_euler = axis.to_track_quat("-Z", "Y").to_euler()
        obj.display_type = "WIRE"
        obj.visible_shadow = False
        obj["cot_s4"] = True
        obj["cot_weather"] = "fog"
        obj["cot_region"] = s["region"]
        obj["cot_beam_len"] = round(length, 3)
        obj["cot_beam_stop"] = hit_obj.name if hit else ""
        fog_coll.objects.link(obj)
        rc = L.light_linking.receiver_collection
        if rc is not None and obj.name not in rc.objects:
            rc.objects.link(obj)
        made.append({"beam": obj.name, "length": round(length, 2), "stops_at": obj["cot_beam_stop"], "end_radius": round(r_end, 2)})
    for o in skip:
        o.hide_viewport = False
    fog_coll.hide_viewport = was
    return made


def local_volumes(fog_coll, items):
    out = []
    for v in items:
        if "region" in v:
            b = AL.region_bounds(v["region"])
            lo, hi = b
            if "shrink" in v:
                s = v["shrink"]
                lo, hi = lo + Vector((s, s, s)), hi - Vector((s, s, s))
        else:
            lo, hi = Vector(v["box"][0]), Vector(v["box"][1])
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for vert in bm.verts:
            vert.co = Vector((lo.x if vert.co.x < 0 else hi.x, lo.y if vert.co.y < 0 else hi.y, lo.z if vert.co.z < 0 else hi.z))
        mesh = bpy.data.meshes.new(f"COT_S4_Air_{v['name']}_data")
        bm.to_mesh(mesh)
        bm.free()
        mat = bpy.data.materials.get(f"MAT_S4_air_{v['name']}") or bpy.data.materials.new(f"MAT_S4_air_{v['name']}")
        if mat.node_tree is None:
            mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out_n = nt.nodes.new("ShaderNodeOutputMaterial")
        vol = nt.nodes.new("ShaderNodeVolumePrincipled")
        vol.inputs["Color"].default_value = (*v.get("color", (0.6, 0.75, 1.0)), 1.0)
        vol.inputs["Density"].default_value = v["density"]
        vol.inputs["Anisotropy"].default_value = v.get("anisotropy", 0.4)
        nt.links.new(vol.outputs["Volume"], out_n.inputs["Volume"])
        mat["cot_s4"] = True
        mesh.materials.append(mat)
        obj = bpy.data.objects.new(f"COT_S4_Air_{v['name']}", mesh)
        obj.display_type = "WIRE"
        obj.visible_shadow = False
        obj["cot_s4"] = True
        obj["cot_weather"] = "fog"
        fog_coll.objects.link(obj)
        out.append(obj.name)
    return out
