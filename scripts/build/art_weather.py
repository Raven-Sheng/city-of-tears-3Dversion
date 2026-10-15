"""Stage 4 weather: rain columns placed by ray casts, eave drips, puddles with rain rings, ground fog, depth haze.

Rain (same speed / shape / colour as the stage 2 plaza rain, docs/art_direction.md section 8):
  * In each rain zone (an open well, config art.json rain.zones) random (x, y) columns start at the zone top.
    A column is kept only if (1) the first surface below is an upward face, and (2) nothing but cave rock / cave
    ceiling is above the start (otherwise the start is inside or under a building). The column spans from that
    landing surface up to the cave ceiling, so rain stops on every roof, deck and floor it meets and never enters a
    room or passes under a bridge.
  * Each column carries cot_zlo / cot_zhi as vertex attributes; the rain shader is transparent outside that span.
    The whole layer scrolls down at the measured speed with a seamless period (fixed seed, linear keys + cycles
    modifier), so the motion is continuous and repeatable frame by frame.
  * Landing objects get cot_wet = 1, walls beside a column cot_wet = 0.7 (read by NG_COT_Paint).
Eave drips: where a column lands on a roof and a probe a little further out falls more than min_drop, a thin, slower
  streak column runs from the edge down to the lower surface. Puddles: flat irregular discs on level landings, with
  NG_COT_Water rain rings; one more ring disc under each drip.
"""
import math
import random

import bmesh
import bpy
from mathutils import Vector

PLACEMENT_VERSION = 4          # bump when the placement rules change (invalidates the ray-cast cache)
SKY_LAYERS = {"ROCK", "CEILING", "CAVESHELL", "HOSTROCK"}
SKY_REGIONS = {"_World", "TopCavern"}


def coll(name, parent):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in parent.children:
        parent.children.link(c)
    return c


def _is_sky(obj):
    if obj is None:
        return True
    o = obj.original if hasattr(obj, "original") else obj
    if o.get("cot_layer") in SKY_LAYERS or o.get("cot_region") in SKY_REGIONS:
        return True
    names = {c.name for c in o.users_collection}
    return any(n.startswith(("COT_L_CEILING", "COT_L_HOSTROCK", "COT_L_CAVESHELL")) or n.endswith(("_ROCK", "_CEILING", "_CAVESHELL")) for n in names)


class Caster:
    def __init__(self, scene):
        self.scene = scene
        self.dg = bpy.context.evaluated_depsgraph_get()
        self.n = 0

    def cast(self, origin, direction, dist=1.0e4):
        self.n += 1
        hit, loc, nrm, _i, obj, _m = self.scene.ray_cast(self.dg, Vector(origin), Vector(direction), distance=dist)
        if not hit:
            return None
        return loc, nrm, (obj.original if obj is not None else None)


def room_boxes():
    """Interior boxes recorded by the stage 3 stacks (cot_rooms on their _Walls objects)."""
    import json
    out = []
    for w in bpy.data.objects:
        if w.get("cot_rooms"):
            out += [tuple(r) for r in json.loads(w["cot_rooms"])]
    return out


def _region_box(rid):
    lo = Vector((1e9,) * 3)
    hi = Vector((-1e9,) * 3)
    for o in bpy.data.objects:
        if o.get("cot_region") != rid or not o.get("cot_s3") or o.type not in ("MESH", "CURVE") or o.hide_render:
            continue
        if o.get("cot_layer") in ("CAVESHELL", "BACKDROP"):
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
    return (lo.x, hi.x, lo.y, hi.y, lo.z, hi.z) if lo.x < hi.x else None


def _overlaps(b, x, y, zlo, zhi):
    return b[0] < x < b[1] and b[2] < y < b[3] and zlo < b[5] and zhi > b[4]


def in_room(rooms, x, y, zlo, zhi):
    return any(x0 - 0.3 < x < x1 + 0.3 and y0 - 0.3 < y < y1 + 0.3 and zlo < z1 and zhi > z0 for x0, x1, y0, y1, z0, z1 in rooms)


def sheltered(C, x, y, zlo, zhi, n=4):
    """True if a non-rock surface lies above any of n points inside the span (rain would be under cover)."""
    for k in range(n):
        z = zlo + 0.5 + (zhi - zlo - 1.0) * k / max(1, n - 1)
        hit = C.cast((x, y, z), (0, 0, 1))
        if hit is not None and hit[0].z < zhi - 0.5 and not _is_sky(hit[2]):
            return True
    return False


def place_rain(scene, zones, rcfg, seed):
    """Returns tracks [(x, y, zlo, zhi, landing object name, landing normal z)] per zone and wetness updates."""
    rnd = random.Random(seed)
    C = Caster(scene)
    rooms = room_boxes()
    out = {}
    wet = {}
    stats = {}
    excluded = []                                        # cave-interior regions under rock ceilings never get rain
    for rid in rcfg.get("exclude_regions", []):
        b = _region_box(rid)
        if b is not None:
            excluded.append(b)
    feather = rcfg.get("edge_feather", 0.0)
    high_gap = rcfg.get("high_shelter_gap", 0.0)
    for z in zones:
        x0, x1 = z["x"]
        y0, y1 = z["y"]
        want = int((x1 - x0) * (y1 - y0) * z.get("density_per_m2", rcfg["density_per_m2"]))
        tracks, tries, rej = [], 0, {"no_hit": 0, "not_up": 0, "covered": 0, "short": 0, "room": 0, "shelter": 0, "excluded": 0,
                                     "feather": 0, "under_high_deck": 0}
        while len(tracks) < want and tries < want * 6:
            tries += 1
            x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
            if feather > 0.0:                            # thin out towards the zone sides: no hard rectangular rain block
                d = min(x - x0, x1 - x, y - y0, y1 - y)
                if rnd.random() > min(1.0, d / feather):
                    rej["feather"] += 1
                    continue
            start = (x, y, z["z_top"])
            down = C.cast(start, (0, 0, -1))
            if down is None:
                rej["no_hit"] += 1
                continue
            loc, nrm, obj = down
            if nrm.z < 0.25:
                rej["not_up"] += 1
                continue
            up = C.cast(start, (0, 0, 1))
            if up is not None and not _is_sky(up[2]):
                # a cover high above the ground (a bridge deck, a tower overhang 30 m up) does not keep wind-driven
                # rain off the ground below it: the column starts just under the cover (faded in at its top);
                # rooms are still excluded by the room and shelter tests below
                if high_gap > 0.0 and up[1].z < -0.25 and up[0].z - loc.z >= high_gap:
                    zhi = up[0].z - 0.3
                    rej["under_high_deck"] += 1
                else:
                    rej["covered"] += 1
                    continue
            else:
                zhi = up[0].z - 0.2 if up is not None else z["z_top"] + 30.0
            zlo = loc.z
            if zhi - zlo < 3.0:
                rej["short"] += 1
                continue
            if in_room(rooms, x, y, zlo + 0.3, zhi):
                rej["room"] += 1
                continue
            if any(_overlaps(b, x, y, zlo, zhi) for b in excluded):
                rej["excluded"] += 1
                continue
            if sheltered(C, x, y, zlo, zhi):
                rej["shelter"] += 1
                continue
            tracks.append((x, y, zlo, zhi, obj.name if obj else "", nrm.z))
            if obj is not None:
                wet[obj.name] = 1.0
            # under a deck or bridge more than high_gap above the ground, wind-driven rain still reaches the ground:
            # a second column from just under the deck (faded in at its top) down to the next surface
            if high_gap > 0.0:
                b = C.cast((x, y, zlo - 0.02), (0, 0, -1))
                if b is not None and b[1].z < -0.25:
                    under = C.cast((x, y, b[0].z - 0.05), (0, 0, -1))
                    if under is not None and under[1].z > 0.25 and b[0].z - under[0].z >= high_gap:
                        lo2, hi2 = under[0].z, b[0].z - 0.3
                        if not in_room(rooms, x, y, lo2 + 0.3, hi2) and not any(_overlaps(e, x, y, lo2, hi2) for e in excluded) \
                                and not sheltered(C, x, y, lo2, hi2 - 0.5):
                            tracks.append((x, y, lo2, hi2, under[2].name if under[2] else "", under[1].z))
                            rej["under_high_deck"] += 1
                            if under[2] is not None:
                                wet[under[2].name] = 1.0
            # walls beside the column get wet too
            for hz in (zlo + 1.0, (zlo + zhi) / 2, zhi - 1.0):
                for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):
                    side = C.cast((x, y, hz), d, 1.6)
                    if side is not None and side[2] is not None and not _is_sky(side[2]):
                        wet[side[2].name] = max(wet.get(side[2].name, 0.0), 0.7)
        out[z["name"]] = tracks
        stats[z["name"]] = {"wanted": want, "placed": len(tracks), "tries": tries, "rejected": rej}
    return out, wet, stats, C


def find_drips(C, tracks_by_zone, dcfg, seed):
    rnd = random.Random(seed + 1)
    rooms = room_boxes()
    drips = []
    for zone, tracks in tracks_by_zone.items():
        for (x, y, zlo, zhi, oname, nz) in tracks:
            obj = bpy.data.objects.get(oname)
            if obj is None or _is_sky(obj) or "water" in " ".join(s.material.name for s in obj.material_slots if s.material):
                continue
            a0 = rnd.uniform(0, 2 * math.pi)
            for k in range(4):
                a = a0 + k * math.pi / 2
                dx, dy = math.cos(a), math.sin(a)
                p = dcfg["probe"]
                probe = C.cast((x + dx * p, y + dy * p, zlo + 0.4), (0, 0, -1))
                if probe is None or zlo - probe[0].z < dcfg["min_drop"]:
                    continue
                # bisect for the edge between the roof and the drop
                lo_t, hi_t = 0.0, p
                for _ in range(5):
                    m = (lo_t + hi_t) / 2
                    q = C.cast((x + dx * m, y + dy * m, zlo + 0.4), (0, 0, -1))
                    if q is not None and abs(q[0].z - zlo) < 0.3:
                        lo_t = m
                    else:
                        hi_t = m
                ex, ey = x + dx * (hi_t + 0.06), y + dy * (hi_t + 0.06)
                land = C.cast((ex, ey, zlo - 0.15), (0, 0, -1))
                if land is None or zlo - land[0].z < dcfg["min_drop"]:
                    continue
                if in_room(rooms, ex, ey, land[0].z + 0.3, zlo - 0.12) or sheltered(C, ex, ey, land[0].z, zlo - 0.12, 3):
                    continue
                drips.append((ex, ey, land[0].z, zlo - 0.12, land[2].name if land[2] else "", land[1].z))
                break
    rnd.shuffle(drips)
    return drips[: dcfg["max"]]


# ------------------------------------------------------------------------------------------------ geometry
def _streak_columns(name, c, columns, rcfg, rnd, radius, length, fill, speed, mat, props):
    """columns: (x, y, zlo, zhi). One mesh whose rows of streaks repeat every `period` and scroll down."""
    period = rcfg["period"]
    zmin = min(col[2] for col in columns)
    zmax = max(col[3] for col in columns)
    bm = bmesh.new()
    lay_lo = bm.verts.layers.float.new("cot_zlo")
    lay_hi = bm.verts.layers.float.new("cot_zhi")
    for (x, y, zlo, zhi) in columns:
        spans, z = [], 0.0
        while z < period:
            ln = rnd.uniform(*length)
            gap = ln * (1.0 / max(0.05, fill) - 1.0) * rnd.uniform(0.5, 1.5)
            if z + ln > period:
                break
            spans.append((z, ln))
            z += ln + gap
        phase = rnd.uniform(0.0, period)
        r = rnd.uniform(*radius)
        a0 = rnd.uniform(0, 6.28)
        pts = [(x + r * math.cos(a0 + 2.094395 * k), y + r * math.sin(a0 + 2.094395 * k)) for k in range(3)]
        for s0, ln in spans:
            s0 = (s0 + phase) % period
            pieces = [(s0, min(ln, period - s0))]
            if s0 + ln > period:
                pieces.append((0.0, s0 + ln - period))
            for za, lz in pieces:
                if lz < 0.05:
                    continue
                ring_lo = [bm.verts.new((px, py, za)) for px, py in pts]
                ring_hi = [bm.verts.new((px, py, za + lz)) for px, py in pts]
                for v in ring_lo + ring_hi:
                    v[lay_lo], v[lay_hi] = zlo, zhi
                for k in range(3):
                    bm.faces.new((ring_lo[k], ring_lo[(k + 1) % 3], ring_hi[(k + 1) % 3], ring_hi[k]))
                bm.faces.new(ring_lo[::-1])
                bm.faces.new(ring_hi)
    mesh = bpy.data.meshes.new(name + "_data")
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    c.objects.link(obj)
    copies = int(math.ceil((zmax - zmin) / period)) + 1
    mod = obj.modifiers.new("PeriodRepeat", "ARRAY")
    mod.count = copies
    mod.use_relative_offset = False
    mod.use_constant_offset = True
    mod.constant_offset_displace = (0.0, 0.0, period)
    # scroll down one period; geometry covers [zmin - period, zmin + (copies - 1) * period] at every frame
    obj.location.z = zmin
    obj.keyframe_insert("location", index=2, frame=1)
    obj.location.z = zmin - period
    obj.keyframe_insert("location", index=2, frame=1 + period / speed)
    action = obj.animation_data.action
    curves = []
    try:
        curves = list(action.fcurves)
    except AttributeError:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    curves += list(bag.fcurves)
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
        fc.modifiers.new("CYCLES")
    obj.visible_shadow = False
    obj.visible_diffuse = False
    obj.visible_glossy = True
    for k, v in props.items():
        obj[k] = v
    obj["cot_columns"] = len(columns)
    return obj


def rain_material(name, color, strength, alpha):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])

    def m(op, a, b, clamp=False):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        n.use_clamp = clamp
        for s, v in zip(n.inputs, (a, b)):
            if isinstance(v, bpy.types.NodeSocket):
                nt.links.new(v, s)
            else:
                s.default_value = v
        return n.outputs[0]

    lo = nt.nodes.new("ShaderNodeAttribute")
    lo.attribute_type, lo.attribute_name = "GEOMETRY", "cot_zlo"
    hi = nt.nodes.new("ShaderNodeAttribute")
    hi.attribute_type, hi.attribute_name = "GEOMETRY", "cot_zhi"
    inside = m("MULTIPLY", m("GREATER_THAN", sep.outputs["Z"], lo.outputs["Fac"]), m("LESS_THAN", sep.outputs["Z"], hi.outputs["Fac"]))
    # every column fades in over its top 10 m (cave ceiling or the underside of a high deck): no hard start line
    inside = m("MULTIPLY", inside, m("DIVIDE", m("SUBTRACT", hi.outputs["Fac"], sep.outputs["Z"]), 10.0, clamp=True))
    cam = nt.nodes.new("ShaderNodeCameraData")
    # streaks close to the lens fade out (they would cross the frame as thick bars); fully visible from 18 m
    near = m("DIVIDE", m("SUBTRACT", cam.outputs["View Distance"], 5.0), 13.0, clamp=True)
    # far streaks thin out (from 1.0 at 30 m to 0.2 at 170 m): a deep look down a well no longer stacks into a curtain
    far = m("ADD", 0.2, m("MULTIPLY", 0.8, m("SUBTRACT", 1.0, m("DIVIDE", m("SUBTRACT", cam.outputs["View Distance"], 30.0), 140.0, clamp=True))))
    near = m("MULTIPLY", near, far)
    # looking steeply up or down a column lines all its streaks up into one radial bar (the streaks of a whole column
    # stack on the same pixels, coverage ~ 1/sin of the angle to the fall axis); a real drop seen end-on is a short dot.
    # Opacity x (sin^2)^3 of that angle: 1 looking level, 0.69 at 20 deg up, 0.09 at 48 deg, 0.007 at 64 deg
    # (1.5 was tried first: the near columns of CentralWell_LookUp still read as bright radial bars)
    sep_i = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Incoming"], sep_i.inputs[0])
    sin2 = m("SUBTRACT", 1.0, m("MULTIPLY", sep_i.outputs["Z"], sep_i.outputs["Z"]), clamp=True)
    near = m("MULTIPLY", near, m("POWER", sin2, 3.0))
    # section cameras (front facades hidden) set scene["cot_rain_cut"] = depth of the cut plane: rain in front of it,
    # which is outdoors in front of the hidden facade, is not drawn over the opened room
    cut = nt.nodes.new("ShaderNodeAttribute")
    cut.attribute_type, cut.attribute_name = "VIEW_LAYER", "cot_rain_cut"
    behind_cut = m("GREATER_THAN", cam.outputs["View Z Depth"], cut.outputs["Fac"])
    nt.links.new(m("MULTIPLY", m("MULTIPLY", m("MULTIPLY", inside, near), behind_cut), alpha), mix.inputs["Fac"])
    nt.links.new(tr.outputs["BSDF"], mix.inputs[1])
    nt.links.new(em.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    try:
        mat.surface_render_method = "BLENDED"
    except Exception:
        pass
    mat.diffuse_color = (*color, 0.5)
    mat["cot_s4"] = True
    return mat


def build_rain(root_weather, scene, rcfg, seed, cache_path=None, cache_key=None):
    """Ray-cast placement is the slow part (tens of thousands of casts); its result is cached on disk under a key made
    of the structure file hash, the rain config and the seed, so an unchanged structure gives the identical placement."""
    import json
    cached = None
    if cache_path is not None and cache_path.exists():
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        if data.get("key") == cache_key:
            cached = data
    if cached is not None:
        tracks = {k: [tuple(t) for t in v] for k, v in cached["tracks"].items()}
        drips = [tuple(d) for d in cached["drips"]]
        wet, stats, n_rays = cached["wet"], cached["stats"], 0
    else:
        tracks, wet, stats, C = place_rain(scene, rcfg["zones"], rcfg, seed)
        drips = find_drips(C, tracks, rcfg["drips"], seed)
        for _x, _y, _zlo, _zhi, oname, _n in drips:
            if oname:
                wet[oname] = 1.0
        n_rays = C.n
        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps({"key": cache_key, "tracks": tracks, "drips": drips, "wet": wet, "stats": stats, "rays": n_rays}),
                                  encoding="utf-8")
    stats = dict(stats, cache="hit" if cached is not None else "computed")
    # final shelter filter with 8 test heights (the placement uses 4; a ray can slip between the hanging tiers of a
    # shell tower): failing columns are dropped, all others stay exactly as placed
    C2 = Caster(scene)
    dropped = []
    for zone in list(tracks):
        keep = []
        for t in tracks[zone]:
            if sheltered(C2, t[0], t[1], t[2], t[3], 8):
                dropped.append((zone, round(t[0], 2), round(t[1], 2)))
            else:
                keep.append(t)
        tracks[zone] = keep
    kept_drips = []
    for d in drips:
        if sheltered(C2, d[0], d[1], d[2], d[3], 8):
            dropped.append(("drip", round(d[0], 2), round(d[1], 2)))
        else:
            kept_drips.append(d)
    drips = kept_drips
    stats["dropped_by_final_shelter_filter"] = dropped
    n_rays += C2.n
    rnd = random.Random(seed + 7)
    mat = rain_material("MAT_S4_rain", rcfg["color"], rcfg["strength"], rcfg["alpha"])
    c = coll("COT_S4_RAIN", root_weather)
    objs = []
    zone_radius = {z["name"]: z.get("radius", rcfg["radius"]) for z in rcfg["zones"]}
    for zone, tr in tracks.items():
        if not tr:
            continue
        cols = [(x, y, zlo, zhi) for x, y, zlo, zhi, _o, _n in tr]
        objs.append(_streak_columns(f"COT_S4_Rain_{zone}", c, cols, rcfg, rnd, zone_radius[zone], rcfg["length"], rcfg["fill"],
                                    rcfg["speed_per_frame"], mat, {"cot_s4": True, "cot_weather": "rain", "cot_zone": zone}))
    dcfg = rcfg["drips"]
    dmat = rain_material("MAT_S4_drip", (0.55, 0.74, 1.0), 0.7, 0.42)
    cd = coll("COT_S4_DRIPS", root_weather)
    if drips:
        objs.append(_streak_columns("COT_S4_EaveDrips", cd, [(x, y, zlo, zhi) for x, y, zlo, zhi, _o, _n in drips], rcfg, rnd,
                                    (dcfg["radius"] * 0.7, dcfg["radius"] * 1.3), dcfg["length"], dcfg["fill"], dcfg["speed_per_frame"], dmat,
                                    {"cot_s4": True, "cot_weather": "drip"}))
    return tracks, drips, wet, stats, n_rays, objs


def _flat_under(C, x, y, z, r):
    """The whole puddle footprint lies on one level surface (not a beam, rail or roof edge)."""
    for k in range(8):
        a = 2 * math.pi * k / 8
        h = C.cast((x + 0.95 * r * math.cos(a), y + 0.95 * r * math.sin(a), z + 0.4), (0, 0, -1), 0.8)
        if h is None or abs(h[0].z - z) > 0.06 or h[1].z < 0.9:
            return False
    return True


def build_puddles(root_weather, tracks, drips, pcfg, seed, C=None):
    rnd = random.Random(seed + 11)
    spots = []
    rejected = 0
    for zone, tr in tracks.items():
        for (x, y, zlo, _zhi, oname, nz) in tr:
            if nz > 0.96 and rnd.random() < pcfg["fraction"]:
                obj = bpy.data.objects.get(oname)
                if obj is not None and any(s.material and "water" in s.material.name for s in obj.material_slots):
                    continue
                spots.append((x, y, zlo, rnd.uniform(*pcfg["radius"]), _landing_layer(obj)))
    rnd.shuffle(spots)
    for (x, y, zlo, _zhi, oname, nz) in drips:
        if nz > 0.9:
            spots.append((x, y, zlo, 0.45, _landing_layer(bpy.data.objects.get(oname))))
    if C is not None:
        ok = [s for s in spots if _flat_under(C, *s[:4])]
        rejected = len(spots) - len(ok)
        spots = ok
    spots = spots[: pcfg["max"]]
    mat = bpy.data.materials.get("MAT_S4_puddle") or bpy.data.materials.new("MAT_S4_puddle")
    import art_materials as AM
    # a puddle is a thin film: half see-through, so the paving under it shows and it keeps the lamp highlights; fully
    # opaque near-black water mirrored the dark cave and read as black holes on lit decks (LeftWell_Balcony, v008)
    AM.assign_group(mat, "NG_COT_Water", {"Base Color": (0.04, 0.07, 0.13), "Roughness": 0.08, "Waves": 0.03, "Ripples": 1.0,
                                          "Ripple Scale": 2.4, "Alpha": 0.5})
    mat.diffuse_color = (0.1, 0.2, 0.4, 1.0)
    # one object per landing layer: section cameras that hide a layer (e.g. the rock floor) hide its puddles too,
    # otherwise they would float in the air there (render_art reads cot_on_layer)
    first = None
    for layer in sorted({s[4] for s in spots}):
        bm = bmesh.new()
        for (x, y, z, r, lay) in spots:
            if lay != layer:
                continue
            ph = rnd.uniform(0, 6.28)
            ring = []
            for k in range(14):
                a = 2 * math.pi * k / 14
                rr = r * (0.75 + 0.25 * math.sin(3 * a + ph) + 0.12 * math.sin(5 * a + 2 * ph))
                ring.append(bm.verts.new((x + rr * math.cos(a), y + rr * math.sin(a), z + 0.012)))
            bm.faces.new(ring)
        name = "COT_S4_Puddles" + (f"_On{layer.title()}" if layer else "")
        mesh = bpy.data.meshes.new(name + "_data")
        bm.to_mesh(mesh)
        bm.free()
        mesh.materials.append(mat)
        obj = bpy.data.objects.new(name, mesh)
        obj.visible_shadow = False
        obj["cot_s4"] = True
        obj["cot_weather"] = "puddles"
        obj["cot_on_layer"] = layer
        # own collection per layer: object visibility is driven by the weather switch, the collection is free for the
        # per-camera layer hide
        coll(f"COT_S4_PUDDLES_{layer or 'OPEN'}", coll("COT_S4_WATERMARKS", root_weather)).objects.link(obj)
        first = first or obj
    if first is not None:
        first["cot_rejected_not_flat"] = rejected
    return first, len(spots)


def _landing_layer(obj):
    if obj is None:
        return ""
    lay = obj.get("cot_layer")
    if lay in ("ROCK", "CEILING", "CAVESHELL", "HOSTROCK", "FRONT", "BACKDROP"):
        return lay
    for c in obj.users_collection:
        for key in ("ROCK", "CEILING", "CAVESHELL", "HOSTROCK", "FRONT", "BACKDROP", "FOREGROUND"):
            if c.name.endswith("_" + key):
                return key
    return ""


def face_wetness(scene, wet, cache_path, key):
    """Objects that hold rooms (one mesh for several storeys) are wet only where a face is open to the cave sky:
    from every face centre (pushed 0.3 m out along its normal) a ray goes straight up; open sky -> wet (1 for upward
    faces, 0.7 for walls), anything else -> dry. Stored as FACE attribute cot_wetf; cot_wetf_used = 1 tells the
    material to use it. Mesh data shared by several objects is left at object level. Cached on disk by key."""
    import json
    rooms = room_boxes()
    cache = {}
    if cache_path.exists():
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        if data.get("key") == key:
            cache = data["faces"]
    C = Caster(scene)
    done, faces_total = [], 0
    for name, w in wet.items():
        o = bpy.data.objects.get(name)
        if o is None or o.type != "MESH" or o.data.users != 1:
            continue
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        if not any(lo[0] < r[1] and hi[0] > r[0] and lo[1] < r[3] and hi[1] > r[2] and lo[2] < r[5] and hi[2] > r[4] for r in rooms):
            continue
        me = o.data
        if name in cache and len(cache[name]) == len(me.polygons):
            vals = cache[name]
        else:
            nm = o.matrix_world.to_3x3().inverted().transposed()
            vals = []
            for p in me.polygons:
                c = o.matrix_world @ p.center
                n = (nm @ p.normal).normalized()
                hit = C.cast(c + n * 0.3, (0, 0, 1))
                if hit is not None and not _is_sky(hit[2]):
                    vals.append(0.0)
                else:
                    vals.append(round(w if n.z > 0.5 else 0.7 * w, 2))
            cache[name] = vals
        attr = me.attributes.get("cot_wetf") or me.attributes.new("cot_wetf", "FLOAT", "FACE")
        attr.data.foreach_set("value", vals)
        o["cot_wetf_used"] = 1.0
        o["cot_dry"] = 1.0                                   # no fixed stage 2 top gloss; wet faces get wet gloss
        done.append(name)
        faces_total += len(vals)
    cache_path.write_text(json.dumps({"key": key, "faces": cache}), encoding="utf-8")
    return {"objects": len(done), "faces": faces_total, "rays": C.n}


def ground_fog(root_fog, layers):
    out = []
    for L in layers:
        (x0, y0, z0), (x1, y1, z1) = L["box"]
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co = Vector((x0 if v.co.x < 0 else x1, y0 if v.co.y < 0 else y1, z0 if v.co.z < 0 else z1))
        mesh = bpy.data.meshes.new(f"COT_S4_GroundFog_{L['name']}_data")
        bm.to_mesh(mesh)
        bm.free()
        mat = bpy.data.materials.get("MAT_S4_groundfog_" + L["name"]) or bpy.data.materials.new("MAT_S4_groundfog_" + L["name"])
        if mat.node_tree is None:
            mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out_n = nt.nodes.new("ShaderNodeOutputMaterial")
        vol = nt.nodes.new("ShaderNodeVolumePrincipled")
        vol.inputs["Color"].default_value = (0.42, 0.62, 1.0, 1.0)
        vol.inputs["Anisotropy"].default_value = 0.3
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sep.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.interpolation_type = "SMOOTHSTEP"
        mr.inputs["From Min"].default_value = z0
        mr.inputs["From Max"].default_value = z1
        mr.inputs["To Min"].default_value = L["density"]
        mr.inputs["To Max"].default_value = 0.0
        nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 0.06
        nt.links.new(geo.outputs["Position"], noise.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        nt.links.new(mr.outputs["Result"], mul.inputs[0])
        mr2 = nt.nodes.new("ShaderNodeMapRange")
        mr2.inputs["From Min"].default_value = 0.3
        mr2.inputs["From Max"].default_value = 0.7
        mr2.inputs["To Min"].default_value = 0.4
        mr2.inputs["To Max"].default_value = 1.3
        nt.links.new(noise.outputs["Fac"], mr2.inputs["Value"])
        nt.links.new(mr2.outputs["Result"], mul.inputs[1])
        # fade to zero over 15 m towards the four sides of the box: no straight fog edges in wide views
        edge = None
        for axis, a0, a1 in (("X", x0, x1), ("Y", y0, y1)):
            for lo_side in (True, False):
                mrx = nt.nodes.new("ShaderNodeMapRange")
                mrx.interpolation_type = "SMOOTHSTEP"
                mrx.inputs["From Min"].default_value = a0 if lo_side else a1
                mrx.inputs["From Max"].default_value = (a0 + 15.0) if lo_side else (a1 - 15.0)
                nt.links.new(sep.outputs[axis], mrx.inputs["Value"])
                if edge is None:
                    edge = mrx.outputs["Result"]
                else:
                    mn = nt.nodes.new("ShaderNodeMath")
                    mn.operation = "MINIMUM"
                    nt.links.new(edge, mn.inputs[0])
                    nt.links.new(mrx.outputs["Result"], mn.inputs[1])
                    edge = mn.outputs[0]
        fin = nt.nodes.new("ShaderNodeMath")
        fin.operation = "MULTIPLY"
        nt.links.new(mul.outputs[0], fin.inputs[0])
        nt.links.new(edge, fin.inputs[1])
        nt.links.new(fin.outputs[0], vol.inputs["Density"])
        nt.links.new(vol.outputs["Volume"], out_n.inputs["Volume"])
        mat["cot_s4"] = True
        mesh.materials.append(mat)
        obj = bpy.data.objects.new(f"COT_S4_GroundFog_{L['name']}", mesh)
        obj.display_type = "WIRE"
        obj.visible_shadow = False
        obj["cot_s4"] = True
        obj["cot_weather"] = "fog"
        root_fog.objects.link(obj)
        obj["cot_rooms_carved"] = _carve_rooms(obj, (x0, x1, y0, y1, z0, z1))
        out.append(obj)
    return out


def _carve_rooms(obj, box):
    """Cut the recorded room interiors (cot_rooms, grown 0.3 m) out of a fog box with an exact Boolean, so ground fog
    never fills a room whose floor lies inside the fog layer (CentralBlock ground-floor shop, v013)."""
    x0, x1, y0, y1, z0, z1 = box
    rooms = [r for r in room_boxes() if r[0] < x1 and r[1] > x0 and r[2] < y1 and r[3] > y0 and r[4] < z1 and r[5] > z0]
    if not rooms:
        return 0
    bm = bmesh.new()
    for rx0, rx1, ry0, ry1, rz0, rz1 in rooms:
        res = bmesh.ops.create_cube(bm, size=1.0)
        for v in res["verts"]:
            v.co = Vector((rx0 - 0.3 if v.co.x < 0 else rx1 + 0.3, ry0 - 0.3 if v.co.y < 0 else ry1 + 0.3,
                           rz0 - 0.3 if v.co.z < 0 else rz1 + 0.3))
    cut_me = bpy.data.meshes.new(obj.name + "_cutter")
    bm.to_mesh(cut_me)
    bm.free()
    cutter = bpy.data.objects.new(obj.name + "_cutter", cut_me)
    obj.users_collection[0].objects.link(cutter)
    mod = obj.modifiers.new("carve_rooms", "BOOLEAN")
    mod.operation, mod.solver, mod.object = "DIFFERENCE", "EXACT", cutter
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    new_me = bpy.data.meshes.new_from_object(ev)
    # the cut faces come from the cutter, which has no material: without this they get an empty slot and render as an
    # opaque default surface (grey shells around the rooms in v016 finals, e.g. EastRainGap_ObliqueL)
    new_me.polygons.foreach_set("material_index", [0] * len(new_me.polygons))
    while len(new_me.materials) > 1:
        new_me.materials.pop()
    obj.modifiers.remove(mod)
    old = obj.data
    obj.data = new_me
    new_me.name = old.name
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(cutter)
    bpy.data.meshes.remove(cut_me)
    return len(rooms)


def setup_compositor(scene, cm, mist):
    """Render layers -> depth haze (mist pass x strength, mixed toward the haze colour) -> bloom -> output."""
    scene.render.engine = "CYCLES"                            # the mist socket of the render-layer node exists only for Cycles
    vl = scene.view_layers[0]
    vl.use_pass_mist = True
    world = scene.world
    world.mist_settings.start = mist["start"]
    world.mist_settings.depth = mist["depth"]
    world.mist_settings.falloff = "QUADRATIC"
    name = "COT_S4_Compositor"
    old = bpy.data.node_groups.get(name)
    if old is not None:
        bpy.data.node_groups.remove(old)
    tree = bpy.data.node_groups.new(name, "CompositorNodeTree")
    scene.compositing_node_group = tree
    rl = tree.nodes.new("CompositorNodeRLayers")
    rl.scene = scene
    rl.layer = vl.name
    if "Mist" not in rl.outputs:
        raise RuntimeError(f"render layer node has no Mist output: {[s.name for s in rl.outputs]}")
    strength = tree.nodes.new("ShaderNodeMath")
    strength.name = "COT_S4_MistMix"
    strength.operation = "MULTIPLY"
    strength.inputs[0].default_value = mist["strength"]
    # the mist pass is not denoised by the renderer and is speckled where thin transparent rain streaks cover a pixel
    # in some samples only: denoise it (as an image) before it drives the haze
    mist_src = rl.outputs["Mist"]
    try:
        dn = tree.nodes.new("CompositorNodeDenoise")
        try:
            dn.inputs["Prefilter"].default_value = "None"
        except Exception:
            pass
        tree.links.new(mist_src, dn.inputs["Image"])
        mist_src = dn.outputs["Image"]
    except RuntimeError:
        pass
    tree.links.new(mist_src, strength.inputs[1])
    mixn = tree.nodes.new("ShaderNodeMix")
    mixn.data_type = "RGBA"
    tree.links.new(strength.outputs[0], mixn.inputs[0])
    tree.links.new(rl.outputs["Image"], mixn.inputs[6])
    mixn.inputs[7].default_value = (*mist["color"], 1.0)
    glare = tree.nodes.new("CompositorNodeGlare")
    glare.inputs["Type"].default_value = "Bloom"
    for k, v in (("Threshold", cm["bloom"]["threshold"]), ("Strength", cm["bloom"]["strength"]), ("Size", cm["bloom"]["size"])):
        glare.inputs[k].default_value = v
    tree.links.new(mixn.outputs[2], glare.inputs["Image"])
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    gout = tree.nodes.new("NodeGroupOutput")
    tree.links.new(glare.outputs["Image"], gout.inputs[0])
    scene.render.use_compositing = True
    return tree
