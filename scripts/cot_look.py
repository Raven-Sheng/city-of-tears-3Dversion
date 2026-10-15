"""Materials, lights, fog and rain for the stage 2 plaza sample.

Values here were tuned against the fountain plaza references and are recorded in docs/art_direction.md.
They are an exterior-plaza baseline; interiors (sanctum, House of Pleasure, cluster cave) need their own.
"""
import math

import bpy

from cot_geo import Geo, rng

# key: (base colour, roughness, metallic)
SURFACES = {
    "stone": ((0.050, 0.078, 0.170), 0.55, 0.0),
    "stone_dark": ((0.022, 0.034, 0.078), 0.6, 0.0),
    "cobble": ((0.055, 0.086, 0.185), 0.5, 0.0),
    "statue": ((0.056, 0.092, 0.215), 0.46, 0.0),
    "statue_dark": ((0.004, 0.005, 0.012), 0.7, 0.0),
    "statue_head": ((0.016, 0.028, 0.075), 0.5, 0.0),
    "shell": ((0.040, 0.066, 0.165), 0.45, 0.0),
    "petal": ((0.100, 0.170, 0.400), 0.42, 0.0),
    "shell_mound": ((0.095, 0.160, 0.400), 0.55, 0.0),
    "iron": ((0.020, 0.032, 0.080), 0.42, 0.5),
    "iron_plate": ((0.006, 0.010, 0.026), 0.75, 0.0),
    "window_frame": ((0.018, 0.028, 0.070), 0.45, 0.4),
    "tower_core": ((0.004, 0.006, 0.016), 0.85, 0.0),
    "louvre": ((0.040, 0.066, 0.160), 0.5, 0.2),
    "louvre_core": ((0.008, 0.012, 0.030), 0.8, 0.0),
    "louvre_frame": ((0.028, 0.046, 0.115), 0.45, 0.3),
    "stone_far": ((0.030, 0.052, 0.125), 0.65, 0.0),
    "gb_stone": ((0.014, 0.022, 0.052), 0.7, 0.0),
    "house_wall": ((0.009, 0.014, 0.034), 0.7, 0.0),
    "stone_far_trim": ((0.044, 0.074, 0.175), 0.6, 0.0),
    "rock": ((0.006, 0.009, 0.021), 0.85, 0.0),
    "gb_shell": ((0.018, 0.030, 0.075), 0.8, 0.0),
    "curtain": ((0.030, 0.052, 0.135), 0.8, 0.0),
}
# key: (emission colour, strength)
GLASS = {
    "glass": ((0.20, 0.50, 0.74), 0.72),
    "glass_screen": ((0.42, 0.66, 0.92), 0.6),
    "glass_pillar": ((0.72, 0.88, 1.00), 1.1),
    "glass_far": ((1.00, 0.62, 0.72), 0.7),
    "glass_far_blue": ((0.22, 0.44, 0.72), 0.3),
    "glass_room": ((0.72, 0.46, 0.92), 0.012),
}
# greybox palette key -> look key (the sample file re-dresses the stage 1 greybox as distant context)
GREYBOX_MAP = {
    "stone": "gb_stone", "floor": "gb_stone", "front": "gb_stone", "rock": "rock", "hostrock": "rock",
    "iron": "iron", "glass": "glass_far_blue", "louvre": "louvre", "shell": "gb_shell", "water": "water",
    "landmark": "stone", "placeholder": "stone", "backdrop": "gb_shell", "shaft": "stone_dark", "car": "louvre_frame",
}

_cache = {}
COURSED = {"stone_far", "house_wall", "gb_stone"}
# shell-tower fringe: (dark colour at the hem, light colour at the tuft top, painted self-light of the top)
FRINGE = {"fringe": ((0.004, 0.007, 0.020), (0.034, 0.070, 0.200), 0.042),
          "tower_far": ((0.003, 0.005, 0.014), (0.016, 0.032, 0.095), 0.016),
          "fringe_dim": ((0.003, 0.005, 0.014), (0.016, 0.032, 0.090), 0.008)}
TUNE = {"crevice": 0.0, "top_light": 0.0, "edge_dark": 0.0, "glass_scale": 1.0, "lamp_strength": 16.0, "rain_strength": 1.0, "rain_alpha": 0.55, "fog_anisotropy": 0.35,
        "fog_color": (0.5, 0.7, 1.0), "world_color": (0.0035, 0.009, 0.028), "world_strength": 1.0}


def _tree(name):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return mat, nt, out


def _mix_rgb(nt, fac, a, b):
    node = nt.nodes.new("ShaderNodeMix")
    node.data_type = "RGBA"
    for sock, val in ((node.inputs[0], fac), (node.inputs[6], a), (node.inputs[7], b)):
        if isinstance(val, bpy.types.NodeSocket):
            nt.links.new(val, sock)
        elif isinstance(val, (int, float)):
            sock.default_value = val
        else:
            sock.default_value = (*val, 1.0)
    return node.outputs[2]


def _math(nt, op, a, b=None, clamp=False):
    node = nt.nodes.new("ShaderNodeMath")
    node.operation = op
    node.use_clamp = clamp
    for sock, val in zip(node.inputs, (a, b)):
        if val is None:
            continue
        if isinstance(val, bpy.types.NodeSocket):
            nt.links.new(val, sock)
        else:
            sock.default_value = val
    return node.outputs[0]


def _noise(nt, scale, detail=3.0, vector=None, rough=0.55):
    node = nt.nodes.new("ShaderNodeTexNoise")
    node.inputs["Scale"].default_value = scale
    node.inputs["Detail"].default_value = detail
    node.inputs["Roughness"].default_value = rough
    if vector is not None:
        nt.links.new(vector, node.inputs["Vector"])
    return node


def _object_coords(nt, scale=(1.0, 1.0, 1.0)):
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = scale
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    return mapping.outputs["Vector"]


def surface_material(key, streaks=False):
    color, rough, metal = SURFACES[key]
    mat, nt, out = _tree("MAT_S2_" + key)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    vec = _object_coords(nt, (6.0, 6.0, 0.22) if streaks else (1.0, 1.0, 1.0))
    big = _noise(nt, 0.9 if not streaks else 1.0, 4.0, vec)
    lighter = tuple(min(1.0, c * 1.75) for c in color)
    darker = tuple(c * 0.55 for c in color)
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = 0.32
    ramp.inputs["From Max"].default_value = 0.72
    nt.links.new(big.outputs["Fac"], ramp.inputs["Value"])
    col = _mix_rgb(nt, ramp.outputs["Result"], darker, lighter)
    if key in COURSED:
        # drawn stone courses on large masonry faces: mortar lines darken the colour
        coord = nt.nodes.new("ShaderNodeTexCoord")
        sepc = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(coord.outputs["Object"], sepc.inputs["Vector"])
        comb = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(_math(nt, "ADD", sepc.outputs["X"], sepc.outputs["Y"]), comb.inputs["X"])
        nt.links.new(sepc.outputs["Z"], comb.inputs["Y"])
        brick = nt.nodes.new("ShaderNodeTexBrick")
        brick.inputs["Color1"].default_value = (1, 1, 1, 1)
        brick.inputs["Color2"].default_value = (0.8, 0.8, 0.8, 1)
        brick.inputs["Mortar"].default_value = (0.3, 0.3, 0.3, 1)
        brick.inputs["Scale"].default_value = 1.0
        brick.inputs["Mortar Size"].default_value = 0.022
        brick.inputs["Mortar Smooth"].default_value = 0.3
        brick.inputs["Brick Width"].default_value = 1.25
        brick.inputs["Row Height"].default_value = 0.56
        nt.links.new(comb.outputs["Vector"], brick.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(col, mul.inputs[6])
        nt.links.new(brick.outputs["Color"], mul.inputs[7])
        col = mul.outputs[2]
    if key == "petal":
        # drawn midrib and lighter rim from the petal UVs (u across the petal, v along it)
        uvc = nt.nodes.new("ShaderNodeTexCoord")
        sepu = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(uvc.outputs["UV"], sepu.inputs["Vector"])
        off = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", sepu.outputs["X"], 0.5))
        vein = nt.nodes.new("ShaderNodeMapRange")
        vein.interpolation_type = "SMOOTHSTEP"
        vein.inputs["From Min"].default_value = 0.0
        vein.inputs["From Max"].default_value = 0.035
        vein.inputs["To Min"].default_value = 0.7
        vein.inputs["To Max"].default_value = 0.0
        nt.links.new(off, vein.inputs["Value"])
        col = _mix_rgb(nt, vein.outputs["Result"], col, tuple(c * 0.25 for c in color))
        rim = nt.nodes.new("ShaderNodeMapRange")
        rim.interpolation_type = "SMOOTHSTEP"
        rim.inputs["From Min"].default_value = 0.38
        rim.inputs["From Max"].default_value = 0.5
        rim.inputs["To Min"].default_value = 0.0
        rim.inputs["To Max"].default_value = 0.55
        nt.links.new(off, rim.inputs["Value"])
        col = _mix_rgb(nt, rim.outputs["Result"], col, tuple(min(1.0, c * 2.2) for c in color))
    # painted light organisation of the references: upward faces are lighter, silhouettes carry a dark contour
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs["Vector"])
    up = _math(nt, "MAXIMUM", sep.outputs["Z"], 0.0)
    top = _math(nt, "MULTIPLY", _math(nt, "POWER", up, 1.5), TUNE.get("top_light", 0.0))
    col = _mix_rgb(nt, top, col, tuple(min(1.0, c * 2.4) for c in color))
    facing = nt.nodes.new("ShaderNodeLayerWeight")
    facing.inputs["Blend"].default_value = 0.5
    edge = nt.nodes.new("ShaderNodeMapRange")
    edge.interpolation_type = "SMOOTHSTEP"
    edge.inputs["From Min"].default_value = 0.62
    edge.inputs["From Max"].default_value = 0.93
    edge.inputs["To Max"].default_value = TUNE.get("edge_dark", 0.0)
    nt.links.new(facing.outputs["Facing"], edge.inputs["Value"])
    col = _mix_rgb(nt, edge.outputs["Result"], col, tuple(c * 0.1 for c in color))
    if TUNE.get("crevice", 0.0) > 0.0 and key not in ("iron", "window_frame", "louvre_core"):
        # drawn dark seams: surfaces close to other surfaces (joints, folds, undersides) go towards near black
        ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
        ao.samples = 4
        ao.inputs["Distance"].default_value = 0.45
        seam = nt.nodes.new("ShaderNodeMapRange")
        seam.interpolation_type = "SMOOTHSTEP"
        seam.inputs["From Min"].default_value = 0.25
        seam.inputs["From Max"].default_value = 0.9
        seam.inputs["To Min"].default_value = TUNE["crevice"]
        seam.inputs["To Max"].default_value = 0.0
        nt.links.new(ao.outputs["AO"], seam.inputs["Value"])
        col = _mix_rgb(nt, seam.outputs["Result"], col, tuple(c * 0.06 for c in color))
    nt.links.new(col, bsdf.inputs["Base Color"])
    # wet upward faces are glossier than vertical faces
    wet = _math(nt, "MULTIPLY", _math(nt, "POWER", up, 2.0), 0.62 * rough)
    nt.links.new(_math(nt, "SUBTRACT", rough, wet, clamp=True), bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = metal
    fine = _noise(nt, 14.0, 2.0, vec)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    nt.links.new(fine.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat.diffuse_color = (*[min(1.0, c * 4 + 0.15) for c in color], 1.0)
    return mat


def fringe_material(key):
    """Shell-tower tufts: light at the rounded top, falling to near black at the ragged hem, with vertical strokes.

    The gradient and a little self-light are painted from the tier UVs (v: 0 top, 1 hem), like the references where
    each tier is a lit tuft against the dark gap below it. Faces without tier UVs (caps) take the top colour.
    """
    dark, light, emit = FRINGE[key]
    mat, nt, out = _tree("MAT_S2_" + key)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    uv = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv.outputs["UV"], sep.inputs["Vector"])
    fall = nt.nodes.new("ShaderNodeMapRange")
    fall.interpolation_type = "SMOOTHSTEP"
    fall.inputs["From Min"].default_value = 0.05
    fall.inputs["From Max"].default_value = 0.68
    fall.inputs["To Min"].default_value = 1.0
    fall.inputs["To Max"].default_value = 0.0
    nt.links.new(sep.outputs["Y"], fall.inputs["Value"])
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (9.0, 0.45, 1.0)
    nt.links.new(uv.outputs["UV"], mapping.inputs["Vector"])
    strokes = _noise(nt, 1.0, 3.0, mapping.outputs["Vector"])
    stroke = nt.nodes.new("ShaderNodeMapRange")
    stroke.inputs["From Min"].default_value = 0.3
    stroke.inputs["From Max"].default_value = 0.7
    stroke.inputs["To Min"].default_value = 0.45
    stroke.inputs["To Max"].default_value = 1.0
    nt.links.new(strokes.outputs["Fac"], stroke.inputs["Value"])
    level = _math(nt, "MULTIPLY", fall.outputs["Result"], stroke.outputs["Result"])
    col = _mix_rgb(nt, level, dark, light)
    nt.links.new(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.8
    bsdf.inputs["Emission Color"].default_value = (*(min(1.0, c * 2.0) for c in light), 1.0)
    nt.links.new(_math(nt, "MULTIPLY", level, emit), bsdf.inputs["Emission Strength"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat.diffuse_color = (*[min(1.0, c * 4 + 0.15) for c in light], 1.0)
    return mat


def glass_material(key):
    color, strength = GLASS[key]
    strength *= TUNE["glass_scale"]
    mat, nt, out = _tree("MAT_S2_" + key)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    uv = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv.outputs["UV"], sep.inputs["Vector"])
    window_id = _math(nt, "FLOOR", sep.outputs["X"])
    white = nt.nodes.new("ShaderNodeTexWhiteNoise")
    white.noise_dimensions = "1D"
    nt.links.new(window_id, white.inputs["W"])
    per_window = _math(nt, "ADD", _math(nt, "MULTIPLY", white.outputs["Value"], 0.62), 0.38)
    along = _math(nt, "SINE", _math(nt, "MULTIPLY", sep.outputs["Y"], math.pi))
    along = _math(nt, "ADD", _math(nt, "MULTIPLY", along, 0.5), 0.5)
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (26.0, 1.3, 1.0)
    nt.links.new(uv.outputs["UV"], mapping.inputs["Vector"])
    streak = _noise(nt, 1.0, 2.0, mapping.outputs["Vector"])
    streaks = _math(nt, "ADD", _math(nt, "MULTIPLY", streak.outputs["Fac"], 0.7), 0.5)
    across = nt.nodes.new("ShaderNodeMapRange")          # side shading: each pane reads as a rounded cocoon
    across.interpolation_type = "SMOOTHSTEP"
    across.inputs["From Min"].default_value = 0.0
    across.inputs["From Max"].default_value = 0.7
    across.inputs["To Min"].default_value = 0.42
    across.inputs["To Max"].default_value = 1.0
    nt.links.new(_math(nt, "FRACT", sep.outputs["X"]), across.inputs["Value"])
    level = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", per_window, along), streaks), across.outputs["Result"])
    nt.links.new(_math(nt, "MULTIPLY", level, strength), bsdf.inputs["Emission Strength"])
    bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
    dim = 0.05 if key == "glass_room" else 0.25
    bsdf.inputs["Base Color"].default_value = (color[0] * dim, color[1] * dim, color[2] * dim * 1.2, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.25
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat.diffuse_color = (*color, 1.0)
    return mat


def emissive_material(key, color, strength, base=(0.02, 0.03, 0.06), rough=0.3):
    mat, nt, out = _tree("MAT_S2_" + key)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
    bsdf.inputs["Emission Strength"].default_value = strength
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat.diffuse_color = (*color, 1.0)
    return mat, nt, bsdf


def sign_material():
    """Glyph plaques: rows of short luminous strokes of varying height (the references show rows of glyphs)."""
    mat, nt, bsdf = emissive_material("sign", (0.72, 0.88, 1.0), 1.0, base=(0.03, 0.05, 0.12))
    uv = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv.outputs["UV"], sep.inputs["Vector"])
    cols, rows = 5.0, 4.0
    cx = _math(nt, "MULTIPLY", sep.outputs["X"], cols)
    cy = _math(nt, "MULTIPLY", sep.outputs["Y"], rows)
    cell = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(_math(nt, "FLOOR", cx), cell.inputs["X"])
    nt.links.new(_math(nt, "FLOOR", cy), cell.inputs["Y"])
    rnd = nt.nodes.new("ShaderNodeTexWhiteNoise")
    rnd.noise_dimensions = "2D"
    nt.links.new(cell.outputs["Vector"], rnd.inputs["Vector"])
    fx = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", _math(nt, "FRACT", cx), 0.5))
    fy = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", _math(nt, "FRACT", cy), 0.5))
    half_h = _math(nt, "ADD", _math(nt, "MULTIPLY", rnd.outputs["Value"], 0.2), 0.16)
    stroke = _math(nt, "MULTIPLY", _math(nt, "LESS_THAN", fx, 0.2), _math(nt, "LESS_THAN", fy, half_h))
    present = _math(nt, "GREATER_THAN", rnd.outputs["Value"], 0.18)
    dx = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", sep.outputs["X"], 0.5))
    dy = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", sep.outputs["Y"], 0.5))
    inside = _math(nt, "LESS_THAN", _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", dx, 1.2), dy), 0.4)
    level = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", stroke, present), inside)
    nt.links.new(_math(nt, "MULTIPLY", level, 1.8), bsdf.inputs["Emission Strength"])
    return mat


def water_material(key="water", rough=0.05, base=(0.006, 0.016, 0.045)):
    mat, nt, out = _tree("MAT_S2_" + key)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    vec = _object_coords(nt, (1.0, 1.0, 1.0))
    wave = nt.nodes.new("ShaderNodeTexNoise")
    wave.noise_dimensions = "4D"
    wave.inputs["Scale"].default_value = 2.6
    wave.inputs["Detail"].default_value = 3.0
    nt.links.new(vec, wave.inputs["Vector"])
    driver = wave.inputs["W"].driver_add("default_value").driver
    driver.expression = "frame / 24.0 * 1.6"
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.16
    bump.inputs["Distance"].default_value = 0.05
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat.diffuse_color = (0.1, 0.3, 0.5, 1.0)
    return mat


def streak_material(key, color, strength, alpha, scale=(18.0, 18.0, 0.35), animate=0.0, z_clip=None):
    """Emissive, partly transparent water streaks (rain, waterfalls, fountain jets)."""
    mat, nt, out = _tree("MAT_S2_" + key)
    emission = nt.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*color, 1.0)
    transparent = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    if animate:
        coord = nt.nodes.new("ShaderNodeTexCoord")
        mapping = nt.nodes.new("ShaderNodeMapping")
        mapping.inputs["Scale"].default_value = scale
        nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
        drv = mapping.inputs["Location"].driver_add("default_value", 2).driver
        drv.expression = f"frame / 24.0 * {animate}"
        tex = _noise(nt, 1.0, 2.0, mapping.outputs["Vector"])
        lvl = _math(nt, "ADD", _math(nt, "MULTIPLY", tex.outputs["Fac"], 1.2), 0.2)
        nt.links.new(_math(nt, "MULTIPLY", lvl, strength), emission.inputs["Strength"])
        nt.links.new(_math(nt, "MULTIPLY", lvl, alpha, clamp=True), mix.inputs["Fac"])
    else:
        emission.inputs["Strength"].default_value = strength
        mix.inputs["Fac"].default_value = alpha
    if z_clip is not None:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])
        below = _math(nt, "LESS_THAN", sep.outputs["Z"], z_clip)
        # streaks right in front of the lens fade out instead of crossing the frame as thick bars
        cam = nt.nodes.new("ShaderNodeCameraData")
        near = _math(nt, "DIVIDE", _math(nt, "SUBTRACT", cam.outputs["View Distance"], 4.0), 8.0, clamp=True)
        nt.links.new(_math(nt, "MULTIPLY", _math(nt, "MULTIPLY", below, near), alpha), mix.inputs["Fac"])
    nt.links.new(transparent.outputs["BSDF"], mix.inputs[1])
    nt.links.new(emission.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    try:
        mat.surface_render_method = "BLENDED"
    except Exception:
        pass
    mat.diffuse_color = (*color, 0.6)
    return mat


def fog_material(density=0.006, anisotropy=0.35, color=(0.50, 0.70, 1.0)):
    mat, nt, out = _tree("MAT_S2_fog")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (*color, 1.0)
    vol.inputs["Density"].default_value = density
    vol.inputs["Anisotropy"].default_value = anisotropy
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    return mat


def material(key):
    """Material lookup used by every stage 2 builder."""
    if key in _cache:
        return _cache[key]
    if key in FRINGE:
        mat = fringe_material(key)
    elif key in SURFACES:
        mat = surface_material(key)
    elif key in FRINGE:
        mat = fringe_material(key)
    elif key in GLASS:
        mat = glass_material(key)
    elif key == "iron_scaffold":
        # tall arched scaffolds read as mid-blue line work against black in the references
        mat = surface_material("iron")
        mat = mat.copy()
        mat.name = "MAT_S2_iron_scaffold"
        bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Emission Color"].default_value = (0.10, 0.21, 0.52, 1.0)
        bsdf.inputs["Emission Strength"].default_value = TUNE.get("scaffold_glow", 0.05)
    elif key == "lamp":
        mat = emissive_material("lamp", (0.80, 0.87, 1.0), TUNE["lamp_strength"], base=(0.6, 0.7, 0.9))[0]
    elif key == "sign":
        mat = sign_material()
    elif key == "water":
        mat = water_material("water", 0.05)
    elif key == "puddle":
        mat = water_material("puddle", 0.03)
    elif key == "water_dish":
        mat = water_material("water_dish", 0.16, base=(0.035, 0.075, 0.19))
    elif key == "waterfall":
        mat = streak_material("waterfall", (0.07, 0.16, 0.62), 0.16, 0.8, scale=(44.0, 44.0, 0.3), animate=-9.0)
    elif key == "rain":
        mat = streak_material("rain", tuple(TUNE.get("rain_color", (0.45, 0.66, 1.0))), TUNE["rain_strength"], TUNE["rain_alpha"], z_clip=TUNE.get("rain_z_clip"))
    else:
        raise KeyError(key)
    _cache[key] = mat
    return mat


def redress_greybox():
    """Give the stage 1 greybox look materials in this sample file (the master file is not touched)."""
    changed = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.get("cot_s2") or not obj.get("cot_generated"):
            continue
        for slot in obj.material_slots:
            current = slot.material
            name = current.name if current else ""
            source = obj.get("cot_gb_material", name)
            if not source.startswith("MAT_GB_"):
                continue
            key = source[len("MAT_GB_"):]
            look = GREYBOX_MAP.get(key)
            if look is None:
                continue
            if key == "backdrop" and obj.name.endswith("_Windows"):
                look = "glass_far_blue"
            obj["cot_gb_material"] = source
            slot.material = material(look)
            changed += 1
    return changed


# ---------------------------------------------------------------------------- lights and weather
def add_light(coll, name, kind, location, color, power, radius=0.2, size=None, rotation=None, props=None, spot=None):
    data = bpy.data.lights.new(name + "_data", kind)
    data.color = color
    data.energy = power
    if kind in ("POINT", "SPOT"):
        data.shadow_soft_size = radius
    if kind == "AREA":
        data.size = size or 1.0
    if kind == "SPOT" and spot:
        data.spot_size, data.spot_blend = spot
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    if kind == "AREA" or radius > 2.0:
        obj.visible_glossy = False          # big soft sources must not show up as shapes in the wet floor and water
    if rotation:
        obj.rotation_euler = rotation
    for k, v in (props or {}).items():
        obj[k] = v
    coll.objects.link(obj)
    return obj


def build_rain(coll, props, layers, covered=(), seed=77, speed_per_frame=8.6, period=96.0, z_top=64.0):
    """Rain as real streak geometry falling at the measured reference speed.

    layers: dicts with x0,x1,y0,y1,tracks,radius,len(min,max),fill. covered: (x0,x1,y0,y1) roofed footprints
    where no streak is placed, so interiors and loggias stay dry. Motion loops seamlessly every `period`.
    """
    rand = rng(seed)
    objs = []
    for li, layer in enumerate(layers):
        g = Geo().use("rain")
        placed = 0
        attempts = 0
        while placed < layer["tracks"] and attempts < layer["tracks"] * 6:
            attempts += 1
            x = rand(layer["x0"], layer["x1"])
            y = rand(layer["y0"], layer["y1"])
            if any(a <= x <= b and c <= y <= d for a, b, c, d in covered):
                continue
            placed += 1
            # Streaks and gaps fill the whole period, then the track gets a random phase and wraps round,
            # so the density is the same at every height and nothing pulses as the layer scrolls.
            spans, z = [], 0.0
            while z < period:
                ln = rand(*layer["len"])
                gap = ln * (1.0 / max(0.05, layer["fill"]) - 1.0) * rand(0.5, 1.5)
                if z + ln > period:
                    break
                spans.append((z, ln))
                z += ln + gap
            phase = rand(0.0, period)
            r = layer["radius"] * rand(0.7, 1.25)
            pts = []
            for k in range(3):
                a = 2.094395 * k + rand(0, 6.28)
                pts.append((x + r * math.cos(a), y + r * math.sin(a)))
            for z0, ln in spans:
                z0 = (z0 + phase) % period
                pieces = [(z0, min(ln, period - z0))]
                if z0 + ln > period:
                    pieces.append((0.0, z0 + ln - period))
                for za, lz in pieces:
                    if lz > 0.05:
                        g.grid([[(px, py, za) for px, py in pts], [(px, py, za + lz) for px, py in pts]], close_u=True, cap_start=True, cap_end=True)
        obj = g.to_object(f"COT_Rain_Layer{li}", coll, material, dict(props, cot_rain_tracks=placed))
        if obj is None:
            continue
        mod = obj.modifiers.new("PeriodRepeat", "ARRAY")
        mod.count = 2
        mod.use_relative_offset = False
        mod.use_constant_offset = True
        mod.constant_offset_displace = (0.0, 0.0, period)
        z_start = z_top - period
        obj.location.z = z_start
        obj.keyframe_insert("location", index=2, frame=1)
        obj.location.z = z_start - period
        obj.keyframe_insert("location", index=2, frame=1 + period / speed_per_frame)
        action = obj.animation_data.action
        curves = []
        try:
            curves = list(action.fcurves)
        except AttributeError:
            for layer_ in action.layers:
                for strip in layer_.strips:
                    for bag in strip.channelbags:
                        curves += list(bag.fcurves)
        for fc in curves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
            fc.modifiers.new("CYCLES")
        obj.visible_shadow = False
        objs.append(obj)
    return objs


def build_glow_haze(coll, props, centre, radii, density):
    """Local denser haze where the reference shows a bright blue glow between the back towers."""
    g = Geo().use("haze")
    g.ellipsoid(centre, radii, segs=24, steps=12)
    mat, nt, out = _tree("MAT_S2_glow_haze")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (0.45, 0.7, 1.0, 1.0)
    vol.inputs["Anisotropy"].default_value = 0.2
    # density falls off smoothly to zero at the surface so the haze has no visible outline
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Location"].default_value = tuple(-c / r for c, r in zip(centre, radii))
    mapping.inputs["Scale"].default_value = tuple(1.0 / r for r in radii)
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    length = nt.nodes.new("ShaderNodeVectorMath")
    length.operation = "LENGTH"
    nt.links.new(mapping.outputs["Vector"], length.inputs[0])
    fall = _math(nt, "SUBTRACT", 1.0, length.outputs["Value"], clamp=True)
    fall = _math(nt, "POWER", fall, 1.6)
    nt.links.new(_math(nt, "MULTIPLY", fall, density), vol.inputs["Density"])
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    obj = g.to_object("COT_S2_GlowHaze", coll, lambda key: mat, props)
    obj.display_type = "WIRE"
    obj.visible_shadow = False
    return obj


def build_fog(coll, props, lo, hi, density=0.006):
    g = Geo().use("fog")
    g.box(lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])
    fog = fog_material(density, TUNE["fog_anisotropy"], tuple(TUNE["fog_color"]))
    obj = g.to_object("COT_S2_FogDomain", coll, lambda key: fog, props)
    obj.display_type = "WIRE"
    obj.visible_shadow = False
    return obj


def setup_world(scene):
    world = scene.world or bpy.data.worlds.new("COT_World")
    scene.world = world
    if world.node_tree is None:
        world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (*TUNE["world_color"], 1.0)
    bg.inputs["Strength"].default_value = TUNE["world_strength"]
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    world.color = tuple(TUNE["world_color"])


def setup_bloom(scene, threshold=1.0, strength=0.6, size=0.5):
    """Compositor bloom so lamp globes and bright panes get the soft halo seen in the references."""
    name = "COT_S2_Compositor"
    old = bpy.data.node_groups.get(name)
    if old is not None:
        bpy.data.node_groups.remove(old)
    tree = bpy.data.node_groups.new(name, "CompositorNodeTree")
    scene.compositing_node_group = tree
    layers = tree.nodes.new("CompositorNodeRLayers")
    glare = tree.nodes.new("CompositorNodeGlare")
    glare.inputs["Type"].default_value = "Bloom"
    for key, value in (("Threshold", threshold), ("Strength", strength), ("Size", size)):
        glare.inputs[key].default_value = value
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    group_out = tree.nodes.new("NodeGroupOutput")
    tree.links.new(layers.outputs["Image"], glare.inputs["Image"])
    tree.links.new(glare.outputs["Image"], group_out.inputs[0])
    scene.render.use_compositing = True
    return tree



def outline_material():
    """Dark contour drawn by an inflated copy of the object: only its far (back-facing) side is visible."""
    mat, nt, out = _tree("MAT_S2_outline")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    transparent = nt.nodes.new("ShaderNodeBsdfTransparent")
    ink = nt.nodes.new("ShaderNodeEmission")
    ink.inputs["Color"].default_value = (*TUNE.get("outline_color", (0.004, 0.008, 0.03)), 1.0)
    ink.inputs["Strength"].default_value = 1.0
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(geo.outputs["Backfacing"], mix.inputs["Fac"])
    nt.links.new(transparent.outputs["BSDF"], mix.inputs[1])
    nt.links.new(ink.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    try:
        mat.surface_render_method = "BLENDED"
    except Exception:
        pass
    mat.diffuse_color = (0.0, 0.0, 0.02, 1.0)
    return mat


def add_outline_hull(coll, objs, thickness, props):
    """Inverted-hull contour for mesh objects. The hull shares the mesh data, is pushed out along the normals by a
    Displace modifier and uses the outline material on every slot. It is geometry, so it is stable from frame to
    frame; it casts no shadow and does not appear in reflections."""
    mat = _cache.get("outline") or outline_material()
    _cache["outline"] = mat
    out = []
    for obj in objs:
        if obj is None or obj.type != "MESH":
            continue
        hull = bpy.data.objects.new(obj.name + "_Outline", obj.data)
        hull.matrix_world = obj.matrix_world.copy()
        coll.objects.link(hull)
        for slot in hull.material_slots:
            slot.link = "OBJECT"
            slot.material = mat
        mod = hull.modifiers.new("OutlineInflate", "DISPLACE")
        mod.direction = "NORMAL"
        mod.mid_level = 0.0
        mod.strength = thickness
        hull.visible_shadow = False
        hull.visible_diffuse = False
        hull.visible_glossy = False
        hull.visible_transmission = False
        hull.visible_volume_scatter = False
        for k, v in props.items():
            hull[k] = v
        hull["cot_outline_of"] = obj.name
        out.append(hull)
    return out

