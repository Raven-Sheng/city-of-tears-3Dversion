"""Stage 3 session: collections, materials, kit instancing, greybox supersede and check cameras.

Stage 3 builds the structure of every region on top of the plaza sample file. Rules it enforces:
  * every stage 3 object carries cot_s3, cot_region, cot_asset, cot_evidence (A / B / C) and cot_ref
  * a region rebuild removes only that region's cot_s3 objects; stage 2 sample objects and hand-made objects stay
  * the stage 1 greybox objects of a rebuilt region are hidden and tagged cot_s3_superseded, never deleted
  * repeated parts are KIT3_<key> datablocks shared by linked duplicates
Map coordinates are pixels of the 7600 px reading version of the master map (see config/project.json).
"""
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

from cot_geo import Geo, IronCurves

ROOT = Path(__file__).resolve().parents[1]
PROJECT = json.loads((ROOT / "config" / "project.json").read_text(encoding="utf-8"))
LAYOUT = json.loads((ROOT / "config" / "layout.json").read_text(encoding="utf-8"))
OX, OY = PROJECT["coordinates"]["origin_map"]
PPB = PROJECT["coordinates"]["px_per_bu"]
LAYERS = ("FRONT", "CEILING", "ROCK", "BACKDROP", "CAVESHELL", "CHARS")


def X(mx):
    return (mx - OX) / PPB


def Z(my):
    return (OY - my) / PPB


def MX(x):
    return x * PPB + OX


def MY(z):
    return OY - z * PPB


# key: (clay / viewport colour, lit base colour, roughness, metallic, emission (colour, strength) or None)
# Lit values are placeholders in the stage 2 palette; stage 4 owns the final look.
S3_MATS = {
    "floor": ((0.30, 0.38, 0.66), (0.034, 0.054, 0.120), 0.6, 0.0, None),
    "wall_blue": ((0.25, 0.32, 0.56), (0.016, 0.026, 0.062), 0.7, 0.0, None),
    "wall_deep": ((0.19, 0.23, 0.38), (0.008, 0.012, 0.030), 0.75, 0.0, None),
    "mass_black": ((0.075, 0.085, 0.14), (0.004, 0.005, 0.012), 0.8, 0.0, None),      # solid building mass the master draws black (D-376)
    "wall_purple": ((0.42, 0.33, 0.62), (0.034, 0.020, 0.066), 0.7, 0.0, None),
    "wall_pleasure": ((0.36, 0.28, 0.60), (0.026, 0.016, 0.070), 0.7, 0.0, None),
    "wall_sanctum": ((0.52, 0.58, 0.74), (0.060, 0.074, 0.130), 0.6, 0.0, None),
    "wall_green": ((0.28, 0.48, 0.52), (0.014, 0.040, 0.050), 0.7, 0.0, None),
    "pattern": ((0.50, 0.40, 0.74), (0.050, 0.030, 0.100), 0.6, 0.0, None),
    "pattern_blue": ((0.34, 0.44, 0.72), (0.030, 0.048, 0.110), 0.6, 0.0, None),
    "trim": ((0.36, 0.47, 0.84), (0.046, 0.076, 0.180), 0.5, 0.0, None),
    "trim_purple": ((0.55, 0.44, 0.80), (0.060, 0.040, 0.120), 0.5, 0.0, None),
    "trim_pale": ((0.66, 0.72, 0.88), (0.110, 0.130, 0.220), 0.45, 0.0, None),
    "wood": ((0.34, 0.30, 0.36), (0.020, 0.016, 0.022), 0.8, 0.0, None),
    "cloth_blue": ((0.26, 0.36, 0.70), (0.022, 0.040, 0.110), 0.85, 0.0, None),
    "cloth_purple": ((0.50, 0.30, 0.66), (0.060, 0.024, 0.090), 0.85, 0.0, None),
    "cloth_pink": ((0.80, 0.46, 0.66), (0.200, 0.060, 0.120), 0.85, 0.0, None),
    "cushion": ((0.60, 0.36, 0.56), (0.090, 0.034, 0.070), 0.85, 0.0, None),
    "glass_blue": ((0.34, 0.62, 0.90), (0.02, 0.05, 0.10), 0.3, 0.0, ((0.16, 0.36, 0.80), 0.55)),
    "glass_white": ((0.86, 0.92, 1.00), (0.10, 0.11, 0.14), 0.3, 0.0, ((0.80, 0.88, 1.00), 1.3)),
    "glass_pink": ((0.95, 0.66, 0.84), (0.10, 0.05, 0.08), 0.3, 0.0, ((0.95, 0.50, 0.74), 0.7)),
    "glass_purple": ((0.66, 0.50, 0.92), (0.05, 0.03, 0.10), 0.3, 0.0, ((0.46, 0.30, 0.92), 0.5)),
    "mirror": ((0.60, 0.68, 0.86), (0.060, 0.080, 0.150), 0.25, 0.2, None),
    "lamp_pink": ((1.0, 0.74, 0.88), (0.6, 0.4, 0.5), 0.3, 0.0, ((1.0, 0.62, 0.82), 6.0)),
    "lamp_warm": ((1.0, 0.86, 0.62), (0.6, 0.5, 0.3), 0.3, 0.0, ((1.0, 0.72, 0.40), 6.0)),
    "lamp_white": ((0.92, 0.96, 1.0), (0.6, 0.7, 0.9), 0.3, 0.0, ((0.80, 0.88, 1.0), 8.0)),
    "cluster": ((0.30, 0.40, 0.58), (0.020, 0.034, 0.066), 0.7, 0.0, None),
    "cluster_spot": ((0.78, 0.74, 0.58), (0.200, 0.180, 0.110), 0.6, 0.0, None),
    "lobe": ((0.20, 0.30, 0.52), (0.012, 0.022, 0.056), 0.6, 0.0, None),
    "pebble": ((0.24, 0.27, 0.36), (0.012, 0.016, 0.030), 0.8, 0.0, None),
    "pot": ((0.33, 0.40, 0.62), (0.030, 0.044, 0.090), 0.5, 0.0, None),
    "relief": ((0.40, 0.48, 0.76), (0.040, 0.060, 0.140), 0.55, 0.0, None),
    "chain": ((0.20, 0.24, 0.40), (0.016, 0.024, 0.060), 0.45, 0.6, None),
    "candle": ((0.94, 0.92, 0.84), (0.5, 0.5, 0.45), 0.5, 0.0, ((1.0, 0.86, 0.6), 2.0)),
    "jar_glass": ((0.70, 0.60, 0.92), (0.06, 0.04, 0.10), 0.2, 0.0, ((0.56, 0.40, 0.95), 0.35)),
    # creatures (D-347) and paintings (D-348); stage 4 owns the final look
    "creature_shell": ((0.46, 0.50, 0.62), (0.060, 0.070, 0.100), 0.55, 0.0, None),
    "creature_shell_pale": ((0.66, 0.72, 0.86), (0.200, 0.230, 0.320), 0.5, 0.0, None),
    "creature_dark": ((0.14, 0.15, 0.22), (0.006, 0.007, 0.014), 0.7, 0.0, None),
    "creature_pale": ((0.88, 0.88, 0.92), (0.500, 0.500, 0.540), 0.5, 0.0, None),
    "creature_pink": ((0.66, 0.50, 0.60), (0.150, 0.080, 0.120), 0.6, 0.0, None),
    "creature_cloak": ((0.48, 0.24, 0.32), (0.080, 0.020, 0.040), 0.8, 0.0, None),
    "creature_cloak_grey": ((0.44, 0.48, 0.58), (0.060, 0.066, 0.090), 0.8, 0.0, None),
    "creature_wing": ((0.58, 0.62, 0.74), (0.120, 0.130, 0.180), 0.4, 0.0, None),
    "creature_eye": ((1.00, 0.62, 0.30), (0.6, 0.3, 0.1), 0.3, 0.0, ((1.0, 0.55, 0.2), 4.0)),
    "creature_soul": ((1.00, 0.92, 0.62), (0.6, 0.55, 0.35), 0.3, 0.0, ((1.0, 0.88, 0.55), 5.0)),
    "paint": ((0.22, 0.24, 0.34), (0.012, 0.014, 0.024), 0.8, 0.0, None),
}
# stage 3 keys that simply reuse a validated stage 2 material
S2_ALIAS = {"rock": "rock", "stone": "stone", "stone_dark": "stone_dark", "stone_far": "stone_far", "stone_far_trim": "stone_far_trim",
            "iron": "iron", "iron_plate": "iron_plate", "iron_scaffold": "iron_scaffold", "window_frame": "window_frame",
            "louvre": "louvre", "louvre_core": "louvre_core", "louvre_frame": "louvre_frame", "glass": "glass",
            "glass_pillar": "glass_pillar", "glass_far": "glass_far", "glass_far_blue": "glass_far_blue", "fringe": "fringe",
            "tower_far": "tower_far", "fringe_dim": "fringe_dim", "tower_core": "tower_core", "curtain": "curtain", "lamp": "lamp",
            "water": "water", "shell": "shell", "shell_mound": "shell_mound", "cobble": "cobble", "house_wall": "house_wall",
            "statue": "statue", "sign": "sign", "petal": "petal"}


def collection(name, parent):
    coll = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if coll.name not in parent.children:
        parent.children.link(coll)
    return coll


def geo_to_mesh(geo, mesh, mats, smooth_angle=42.0):
    """Write a Geo into an (existing or new) mesh datablock, replacing its geometry and material slots."""
    bmesh.ops.remove_doubles(geo.bm, verts=geo.bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(geo.bm, faces=geo.bm.faces[:])
    # material slots first: clearing them after writing the geometry resets every face to material 0 (Blender 5.2)
    mesh.materials.clear()
    for key in geo.keys:
        mesh.materials.append(mats(key))
    geo.bm.to_mesh(mesh)
    geo.bm.free()
    try:
        mesh.set_sharp_from_angle(angle=math.radians(smooth_angle))
    except Exception:
        pass
    mesh.update()
    return mesh


def curves_to_data(ic, curve, material, bevel=0.03, resolution=2, bevel_res=2):
    curve.splines.clear()
    curve.dimensions = "3D"
    curve.bevel_depth = bevel
    curve.bevel_resolution = bevel_res
    curve.resolution_u = resolution
    curve.use_fill_caps = True
    for pts, radii, cyclic, smooth in ic.splines:
        if smooth and len(pts) > 2:
            sp = curve.splines.new("BEZIER")
            sp.bezier_points.add(len(pts) - 1)
            for bp, p, r in zip(sp.bezier_points, pts, radii):
                bp.co = p
                bp.radius = r
                bp.handle_left_type = bp.handle_right_type = "AUTO"
        else:
            sp = curve.splines.new("POLY")
            sp.points.add(len(pts) - 1)
            for pp, p, r in zip(sp.points, pts, radii):
                pp.co = (p.x, p.y, p.z, 1.0)
                pp.radius = r
        sp.use_cyclic_u = cyclic
    curve.materials.clear()
    curve.materials.append(material)
    return curve


class Session:
    def __init__(self, scene):
        self.scene = scene
        self.root = collection("COT_S3", scene.collection)
        self.cams = collection("COT_S3_CAMERAS", self.root)
        self.kit_done = {}
        self.kit_sites = {}
        self.kit_conflicts = []
        self.layout = {r["id"]: r for r in LAYOUT["regions"]}
        self.counts = {}
        self._mat_cache = {}

    # ------------------------------------------------------------------ layout access
    def el(self, rid, eid):
        for e in self.layout[rid]["elements"]:
            if e["id"] == eid:
                return e
        raise KeyError(f"{rid}/{eid}")

    def box(self, rid, eid):
        """World (x0, x1, z0, z1) of a layout element's map box."""
        m = self.el(rid, eid)["map"]
        return X(m[0]), X(m[2]), Z(m[3]), Z(m[1])

    # ------------------------------------------------------------------ collections, properties, materials
    def coll(self, rid, layer=None):
        base = collection("COT_S3_" + rid, self.root)
        base["cot_region"] = rid
        if layer:
            assert layer in LAYERS, layer
            return collection(f"COT_S3_{rid}_{layer}", base)
        return base

    def P(self, rid, asset, ev="A", ref="", note="", layer=None):
        props = {"cot_s3": True, "cot_region": rid, "cot_asset": asset, "cot_evidence": ev, "cot_ref": ref}
        if note:
            props["cot_note"] = note
        if layer:
            props["cot_layer"] = layer
        return props

    def mat(self, key):
        if key in self._mat_cache:
            return self._mat_cache[key]
        mat = None
        if key in S2_ALIAS:
            mat = bpy.data.materials.get("MAT_S2_" + S2_ALIAS[key])
        if mat is None:
            name = "MAT_S3_" + key
            mat = bpy.data.materials.get(name)
            if mat is None:
                mat = bpy.data.materials.new(name)
            spec = S3_MATS.get(key)
            if spec is None:
                raise KeyError(f"unknown stage 3 material key: {key}")
            clay, base, rough, metal, emit = spec
            mat.diffuse_color = (*clay, 1.0)
            mat.roughness = rough
            mat.metallic = metal
            if mat.node_tree is not None:
                bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                if bsdf is not None:
                    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
                    bsdf.inputs["Roughness"].default_value = rough
                    bsdf.inputs["Metallic"].default_value = metal
                    if emit:
                        bsdf.inputs["Emission Color"].default_value = (*emit[0], 1.0)
                        bsdf.inputs["Emission Strength"].default_value = emit[1]
            mat["cot_s3_material"] = True
        self._mat_cache[key] = mat
        return mat

    # ------------------------------------------------------------------ objects
    def _count(self, rid, n=1):
        self.counts[rid] = self.counts.get(rid, 0) + n

    def add(self, geo, name, rid, asset, ev="A", ref="", note="", layer=None, smooth=42.0):
        """Unique mesh object from a Geo."""
        if geo.empty():
            geo.bm.free()
            return None
        obj = geo.to_object(f"S3_{rid}_{name}", self.coll(rid, layer), self.mat, self.P(rid, asset, ev, ref, note, layer), smooth_angle=smooth)
        if asset == "SolidMass":                                # black masses read black, apart from the dark room walls (D-376)
            deep, black = self.mat("wall_deep"), self.mat("mass_black")
            for i, m in enumerate(obj.data.materials):
                if m == deep:
                    obj.data.materials[i] = black
        self._count(rid)
        return obj

    def add_iron(self, ic, name, rid, asset, ev="A", ref="", note="", layer=None, bevel=0.03, key="iron", resolution=2, bevel_res=1):
        if not ic.splines:
            return None
        obj = ic.to_object(f"S3_{rid}_{name}", self.coll(rid, layer), self.mat(key), bevel=bevel,
                           props=self.P(rid, asset, ev, ref, note, layer), resolution=resolution, bevel_res=bevel_res)
        self._count(rid)
        return obj

    def adopt(self, objs, rid, asset, ev="A", ref="", note="", layer=None):
        """Tag objects made by a stage 2 kit builder (which linked them to self.coll(rid, layer) already)."""
        props = self.P(rid, asset, ev, ref, note, layer)
        for o in objs:
            if o is None:
                continue
            for k in ("cot_s2",):
                if k in o:
                    del o[k]
            for k, v in props.items():
                o[k] = v
            if not o.name.startswith("S3_"):
                o.name = f"S3_{rid}_{o.name}"
            if o.data is not None and o.data.users == 1:        # stable data names (the builder's names collide across regions)
                o.data.name = o.name + "_data"
            self._count(rid)
        return objs

    def kit(self, key, build, smooth=42.0):
        """Shared datablock KIT3_<key>. build() returns a Geo, or (IronCurves, material key, bevel)."""
        code = getattr(build, "__code__", None)
        site = (code.co_filename, code.co_firstlineno) if code else None
        if key in self.kit_done:
            if site is not None and site not in self.kit_sites.setdefault(key, set()):
                # the same key asked for from another place: it must describe the same part
                self.kit_sites[key].add(site)
                again = build()
                data = self.kit_done[key]
                if isinstance(again, Geo):
                    n = len(again.bm.verts)
                    again.bm.free()
                    if hasattr(data, "vertices") and n != data.get("cot_s3_kit_verts", n):
                        self.kit_conflicts.append(f"{key}: {site[0].split('scripts')[-1]}:{site[1]} builds {n} vertices, first builder made {data['cot_s3_kit_verts']}")
            return self.kit_done[key]
        self.kit_sites.setdefault(key, set()).add(site)
        made = build()
        name = "KIT3_" + key
        if isinstance(made, Geo):
            data = bpy.data.meshes.get(name) or bpy.data.meshes.new(name)
            data["cot_s3_kit_verts"] = len(made.bm.verts)
            geo_to_mesh(made, data, self.mat, smooth)
        else:
            ic, mkey, bevel = made
            data = bpy.data.curves.get(name) or bpy.data.curves.new(name, "CURVE")
            curves_to_data(ic, data, self.mat(mkey), bevel, resolution=2, bevel_res=1)
        data["cot_s3_kit"] = key
        self.kit_done[key] = data
        return data

    def put(self, data, name, rid, asset, m, ev="A", ref="", note="", layer=None):
        """Linked duplicate of a kit datablock placed with matrix m."""
        obj = bpy.data.objects.new(f"S3_{rid}_{name}", data)
        obj.matrix_world = m
        for k, v in self.P(rid, asset, ev, ref, note, layer).items():
            obj[k] = v
        obj["cot_kit"] = data.get("cot_s3_kit", "")
        self.coll(rid, layer).objects.link(obj)
        self._count(rid)
        return obj

    # ------------------------------------------------------------------ region lifecycle
    def clear_region(self, rid):
        doomed = [o for o in bpy.data.objects if o.get("cot_s3") and o.get("cot_region") == rid]
        for obj in doomed:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data is not None and data.users == 0 and not data.get("cot_s3_kit"):
                for store in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
                    if data.name in store and store[data.name] == data:
                        store.remove(data)
                        break
        return len(doomed)

    def supersede(self, rid, keep=()):
        """Hide and tag the stage 1 greybox objects of a region (everything except names starting with keep)."""
        names = []
        for obj in bpy.data.objects:
            if obj.get("cot_s2") or obj.get("cot_s3") or not obj.get("cot_generated"):
                continue
            if obj.get("cot_region") != rid:
                continue
            if any(obj.name.startswith(k) for k in keep):
                continue
            obj.hide_render = True
            obj.hide_viewport = True
            obj["cot_s3_superseded"] = True
            names.append(obj.name)
        return names

    # ------------------------------------------------------------------ check cameras
    def camera(self, name, rid, loc, look=None, lens=35.0, ortho=None, hide=(), res=(1920, 1080), purpose="", rot=None, kind="view",
               shift=(0.0, 0.0), ref=""):
        cam_name = f"CAM_S3_{rid}_{name}"
        data = bpy.data.cameras.new(cam_name + "_data")
        cam = bpy.data.objects.new(cam_name, data)
        data.clip_start, data.clip_end = 0.1, 3000.0
        data.sensor_width = 36.0
        if ortho is not None:
            data.type = "ORTHO"
            data.ortho_scale = ortho
        else:
            data.lens = lens
        data.shift_x, data.shift_y = shift
        cam.location = loc
        if look is not None:
            direction = Vector(look) - Vector(loc)
            cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        elif rot is not None:
            cam.rotation_euler = [math.radians(v) for v in rot]
        cam["cot_s3"], cam["cot_region"] = True, rid
        cam["cot_hide"] = ",".join(hide)
        cam["cot_res"] = list(res)
        cam["cot_purpose"] = purpose
        cam["cot_kind"] = kind          # ref / oblique / side / back / interior / top / view
        cam["cot_ref"] = ref
        self.cams.objects.link(cam)
        return cam

    def cam_front(self, name, rid, mbox, y=-300.0, hide=("FRONT",), purpose="", ref="", width=1920):
        """Orthographic elevation of a master-map box (x0, y0, x1, y1 in map px): the comparison view for side-on references."""
        x0, x1, z0, z1 = X(mbox[0]), X(mbox[2]), Z(mbox[3]), Z(mbox[1])
        w, h = x1 - x0, z1 - z0
        res = (width, max(64, int(round(width * h / w))))
        cam = self.camera(name, rid, ((x0 + x1) / 2, y, (z0 + z1) / 2), ortho=max(w, h * res[0] / res[1]) if res[0] >= res[1] else h,
                          hide=hide, res=res, purpose=purpose, rot=(90.0, 0.0, 0.0), kind="ref", ref=ref)
        if res[0] < res[1]:
            cam.data.ortho_scale = h
        cam["cot_map_box"] = [float(v) for v in mbox]
        return cam

    def cam_auto(self, rid, box, hide=("ROCK", "CEILING", "BACKDROP", "CAVESHELL"), lens=26.0, tag="", front_hide=("FRONT",), ref="",
                 views=("front", "closed", "oblique", "obliqueR", "back", "side"), fit=0.74):
        """Standard check set for a region volume box = (x0, x1, y0, y1, z0, z1): section elevation, closed elevation,
        two front obliques, a back view and a side view. Elevation cameras stand just in front of the box."""
        x0, x1, y0, y1, z0, z1 = box
        cx, cy, cz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
        w, d, h = x1 - x0, y1 - y0, z1 - z0
        out = {}
        hide = tuple(hide)
        pad = 1.04
        res_w = 1920
        res_h = max(360, min(2400, int(round(res_w * h / w))))
        if res_h == 2400:
            res_w = max(480, int(round(2400 * w / h)))
        elev_hide = tuple(h for h in hide if h not in ("ROCK", "CEILING"))     # elevations keep the surrounding rock, as the master map does
        for key, hd in (("front", elev_hide + tuple(front_hide)), ("closed", elev_hide)):
            if key not in views:
                continue
            cam = self.camera(f"{tag}Elev{'Section' if key == 'front' else 'Closed'}", rid, (cx, y0 - 3.0, cz), ortho=max(w, h * res_w / res_h) * pad if res_w >= res_h else h * pad,
                              hide=hd, res=(res_w, res_h), rot=(90.0, 0.0, 0.0), kind="ref" if key == "front" else "closed", ref=ref,
                              purpose="section elevation, comparable with the master map" if key == "front" else "elevation with the viewer-side facades")
            cam["cot_map_box"] = [float(v) for v in ((x0 * PPB + OX), OY - z1 * PPB, x1 * PPB + OX, OY - z0 * PPB)]
            out[key] = cam
        radius = 0.5 * math.sqrt(w * w + d * d + h * h)
        portrait = h > 1.25 * max(w, d)
        res = (1080, 1920) if portrait else (1920, 1080)
        dist = radius / math.sin(math.atan(10.125 / lens)) * fit
        centre = Vector((cx, cy, cz))
        for key, name, direction, kind, purpose in (
                ("oblique", "ObliqueL", (-0.5, -0.82, 0.3), "oblique", "perspective from the front left, above"),
                ("obliqueR", "ObliqueR", (0.56, -0.82, -0.06), "oblique", "perspective from the front right, low"),
                ("back", "Back", (0.42, 0.86, 0.26), "back", "back of the region"),
                ("side", "Side", (-0.93, -0.3, 0.12), "side", "side of the region (from the west)"),
                ("sideE", "SideE", (0.93, -0.3, 0.12), "side", "side of the region (from the east)")):
            if key not in views:
                continue
            loc = centre + Vector(direction).normalized() * dist
            out[key] = self.camera(f"{tag}{name}", rid, tuple(loc), look=tuple(centre), lens=lens, hide=hide, kind=kind, purpose=purpose, res=res)
        return out
