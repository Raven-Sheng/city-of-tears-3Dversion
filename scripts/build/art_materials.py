"""Stage 4 materials: node groups shared by the whole city.

Hierarchy (edit one group, every material that uses it follows):
  NG_COT_Global            city-wide knobs (wetness, wear, seams, top light, contour, window and lamp gain, wet streaks)
  NG_COT_Paint             painted surface core: low-frequency colour variation, lighter upward faces, dark contour,
                           stone courses, worn chips, wet darkening / gloss / vertical run marks, fine bump, coat, sheen,
                           cloth folds. Wetness = object property cot_wet (set from the rain ray casts) x Global.Wet
  NG_COT_Stone / Metal / Shell / Cloth / Wood     family presets around the core
  NG_COT_Glass             painted translucent pane (cocoon windows): per-object brightness, bright middle, strokes
  NG_COT_Water             dark water with animated noise waves and rain ripple rings (continuous time from the frame)
  NG_COT_Emit              lamp globes and candles (strength x Global.LampGain)
Stage 2 surface materials (MAT_S2_<key>) are rebuilt on NG_COT_Paint with the exact stage 2 parameters and with the
stage 4 extras (wetness response, wear, run marks) at zero, so the validated plaza look is kept (checked by rendering
the plaza reference camera before and after). Stage 2 special materials (fringe, glass, sign, water, rain, outline,
volumes) keep their own trees; the stage 2 glass panes get the Global window gain inserted.
"""
import math

import bpy

GLOBAL_DEFAULTS = {"Wet": 1.0, "Wear": 1.0, "Seams": 1.0, "TopLight": 0.7, "EdgeDark": 0.85, "GlassGain": 1.0, "LampGain": 1.0,
                   "Streaks": 1.0, "Ambient": 1.0}


# ----------------------------------------------------------------------------------------------- small node helpers
class T:
    """Node-tree writer with short helpers (works on materials and node groups)."""

    def __init__(self, nt):
        self.nt = nt
        self.x = 0

    def node(self, kind, **props):
        n = self.nt.nodes.new(kind)
        n.location = (self.x, 0)
        self.x += 30
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def set(self, sock, val):
        if isinstance(val, bpy.types.NodeSocket):
            self.link(val, sock)
        elif isinstance(val, (tuple, list)):
            sock.default_value = tuple(val) + ((1.0,) if len(val) == 3 and len(sock.default_value) == 4 else ())
        else:
            sock.default_value = val
        return sock

    def math(self, op, a, b=None, clamp=False):
        n = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        self.set(n.inputs[0], a)
        if b is not None:
            self.set(n.inputs[1], b)
        return n.outputs[0]

    def vmath(self, op, a, b=None, out=0):
        n = self.node("ShaderNodeVectorMath", operation=op)
        self.set(n.inputs[0], a)
        if b is not None:
            self.set(n.inputs[1], b)
        return n.outputs[out]

    def mix(self, fac, a, b, blend="MIX"):
        n = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend)
        self.set(n.inputs[0], fac)
        self.set(n.inputs[6], a)
        self.set(n.inputs[7], b)
        return n.outputs[2]

    def mixv(self, fac, a, b):
        n = self.node("ShaderNodeMix", data_type="VECTOR")
        self.set(n.inputs[0], fac)
        self.set(n.inputs[4], a)
        self.set(n.inputs[5], b)
        return n.outputs[1]

    def maprange(self, val, fmin, fmax, tmin=0.0, tmax=1.0, smooth=False):
        n = self.node("ShaderNodeMapRange")
        if smooth:
            n.interpolation_type = "SMOOTHSTEP"
        for k, v in (("Value", val), ("From Min", fmin), ("From Max", fmax), ("To Min", tmin), ("To Max", tmax)):
            self.set(n.inputs[k], v)
        return n.outputs["Result"]

    def noise(self, vec, scale, detail=3.0, rough=0.55, dims="3D", w=None):
        n = self.node("ShaderNodeTexNoise")
        n.noise_dimensions = dims
        self.set(n.inputs["Scale"], scale)
        self.set(n.inputs["Detail"], detail)
        self.set(n.inputs["Roughness"], rough)
        if vec is not None:
            self.link(vec, n.inputs["Vector"])
        if w is not None:
            self.set(n.inputs["W"], w)
        return n

    def sep(self, vec):
        n = self.node("ShaderNodeSeparateXYZ")
        self.link(vec, n.inputs[0])
        return n.outputs

    def comb(self, x, y, z):
        n = self.node("ShaderNodeCombineXYZ")
        for s, v in zip(n.inputs, (x, y, z)):
            self.set(s, v)
        return n.outputs[0]

    def scale_col(self, col, f):
        return self.vmath("SCALE", col, None, 0) if False else self._scale(col, f)

    def _scale(self, col, f):
        n = self.node("ShaderNodeVectorMath", operation="SCALE")
        self.set(n.inputs[0], col)
        self.set(n.inputs["Scale"], f)
        return n.outputs[0]

    def clamp1(self, vec):
        return self.vmath("MINIMUM", vec, (1.0, 1.0, 1.0))


def _group(name):
    ng = bpy.data.node_groups.get(name)
    if ng is None:
        ng = bpy.data.node_groups.new(name, "ShaderNodeTree")
    ng.nodes.clear()
    ng.interface.clear()
    return ng


def _io(ng, inputs, outputs):
    for name, kind, default in inputs:
        s = ng.interface.new_socket(name, in_out="INPUT", socket_type=kind)
        if default is not None:
            try:
                s.default_value = default
            except Exception:
                s.default_value = tuple(default) + (1.0,)
        if kind == "NodeSocketFloat":
            s.min_value, s.max_value = -10.0, 10.0
    for name, kind in outputs:
        ng.interface.new_socket(name, in_out="OUTPUT", socket_type=kind)
    t = T(ng)
    gi = t.node("NodeGroupInput")
    go = t.node("NodeGroupOutput")
    return t, gi.outputs, go.inputs


FLOAT, COLOR, SHADER, VECTOR = "NodeSocketFloat", "NodeSocketColor", "NodeSocketShader", "NodeSocketVector"


# ----------------------------------------------------------------------------------------------- groups
def build_global(values):
    ng = _group("NG_COT_Global")
    t, gi, go = _io(ng, [], [(k, FLOAT) for k in GLOBAL_DEFAULTS])
    for k in GLOBAL_DEFAULTS:
        v = t.node("ShaderNodeValue")
        v.name = v.label = "COT_" + k
        v.outputs[0].default_value = float(values.get(k, GLOBAL_DEFAULTS[k]))
        t.link(v.outputs[0], go[k])
    ng["cot_s4"] = True
    return ng


def _frame_time(t, rate):
    """Value node driven by the frame number: continuous time, identical on every render of the same frame."""
    v = t.node("ShaderNodeValue")
    drv = v.outputs[0].driver_add("default_value").driver
    drv.expression = f"frame / 24.0 * {rate}"
    return v.outputs[0]


def build_paint():
    ng = _group("NG_COT_Paint")
    inputs = [("Base Color", COLOR, (0.05, 0.08, 0.17, 1.0)), ("Roughness", FLOAT, 0.6), ("Metallic", FLOAT, 0.0),
              ("Variation", FLOAT, 1.0), ("Noise Scale", FLOAT, 0.9), ("World Coords", FLOAT, 1.0),
              ("Top Light", FLOAT, 1.0), ("Edge Dark", FLOAT, 1.0), ("Gloss Up", FLOAT, 0.15), ("Wet Response", FLOAT, 1.0),
              ("Seams", FLOAT, 0.0), ("Seam Top Proj", FLOAT, 1.0), ("Brick Width", FLOAT, 1.25), ("Row Height", FLOAT, 0.56),
              ("Wear", FLOAT, 0.0), ("Streaks", FLOAT, 0.0), ("Bump", FLOAT, 0.12), ("Coat", FLOAT, 0.0), ("Sheen", FLOAT, 0.0),
              ("Folds", FLOAT, 0.0), ("Emission Color", COLOR, (0.0, 0.0, 0.0, 1.0)), ("Emission Strength", FLOAT, 0.0),
              ("Seam Depth", FLOAT, 0.0)]
    t, gi, go = _io(ng, inputs, [("BSDF", SHADER)])
    glob = t.node("ShaderNodeGroup")
    glob.node_tree = bpy.data.node_groups["NG_COT_Global"]
    G = glob.outputs
    base = gi["Base Color"]
    # coordinates: object space (stage 2 behaviour) or world space (no stretching on scaled kit instances)
    tc = t.node("ShaderNodeTexCoord")
    geo = t.node("ShaderNodeNewGeometry")
    vec = t.mixv(gi["World Coords"], tc.outputs["Object"], geo.outputs["Position"])
    # 1 low-frequency variation between a darker and a lighter tone of the base colour
    # cot_dry = 1 on stage 3 objects the rain never reaches (interiors): calmer colour variation and lighter courses
    # on their large faces; stage 2 plaza objects have no cot_dry and keep the stage 2 look exactly
    dry = t.node("ShaderNodeAttribute", attribute_type="OBJECT", attribute_name="cot_dry")
    calm = t.math("SUBTRACT", 1.0, t.math("MULTIPLY", dry.outputs["Fac"], 0.6), clamp=True)
    big = t.noise(vec, gi["Noise Scale"], 4.0)
    ramp = t.maprange(big.outputs["Fac"], 0.32, 0.72)
    ramp = t.math("ADD", t.math("MULTIPLY", t.math("SUBTRACT", ramp, 0.5), t.math("MULTIPLY", gi["Variation"], calm)), 0.5)
    darker = t._scale(base, 0.55)
    lighter = t.clamp1(t._scale(base, 1.75))
    col = t.mix(ramp, darker, lighter)
    # 2 stone courses (mortar lines); vertical faces use (x+y, z), upward faces (x, y) when Seam Top Proj = 1
    p = t.sep(vec)
    side_uv = t.comb(t.math("ADD", p[0], p[1]), p[2], 0.0)
    top_uv = t.comb(p[0], p[1], 0.0)
    nz = t.sep(geo.outputs["Normal"])
    up = t.math("MAXIMUM", nz[2], 0.0)
    is_top = t.math("MULTIPLY", t.math("GREATER_THAN", t.math("ABSOLUTE", nz[2]), 0.7), gi["Seam Top Proj"])
    brick_uv = t.mixv(is_top, side_uv, top_uv)
    brick = t.node("ShaderNodeTexBrick")
    t.set(brick.inputs["Color1"], (1.0, 1.0, 1.0))
    t.set(brick.inputs["Color2"], (0.8, 0.8, 0.8))
    t.set(brick.inputs["Mortar"], (0.3, 0.3, 0.3))
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = 0.022
    brick.inputs["Mortar Smooth"].default_value = 0.3
    t.link(gi["Brick Width"], brick.inputs["Brick Width"])
    t.link(gi["Row Height"], brick.inputs["Row Height"])
    t.link(brick_uv, brick.inputs["Vector"])
    seam_f = t.math("MULTIPLY", t.math("MULTIPLY", gi["Seams"], G["Seams"], clamp=True),
                    t.math("SUBTRACT", 1.0, t.math("MULTIPLY", dry.outputs["Fac"], 0.5)))
    col = t.mix(seam_f, col, t.mix(1.0, col, brick.outputs["Color"], "MULTIPLY"))
    # Seam Depth: extra darkening of the mortar lines only (brick Fac = mortar mask), not reduced indoors; 0 keeps the
    # stage 2 look (stage2_surface leaves it at the default 0), stage 3 stone gets readable coursing
    depth_f = t.math("MULTIPLY", brick.outputs["Fac"],
                     t.math("MULTIPLY", gi["Seam Depth"], t.math("MULTIPLY", gi["Seams"], G["Seams"], clamp=True)), clamp=True)
    col = t.mix(depth_f, col, t._scale(col, 0.25))
    # 3 worn chips: lighter flecks, more on upward faces
    chipn = t.noise(vec, 5.5, 3.0, 0.6)
    chips = t.maprange(chipn.outputs["Fac"], 0.665, 0.71, smooth=True)
    wear_f = t.math("MULTIPLY", t.math("MULTIPLY", chips, t.math("MULTIPLY", gi["Wear"], G["Wear"])),
                    t.math("ADD", 0.3, t.math("MULTIPLY", up, 0.7)), clamp=True)
    col = t.mix(t.math("MULTIPLY", wear_f, 0.35), col, t.clamp1(t._scale(base, 1.8)))
    # 4 cloth folds: long vertical bands
    mp = t.node("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2.6, 2.6, 0.12)
    t.link(vec, mp.inputs["Vector"])
    foldn = t.noise(mp.outputs["Vector"], 1.0, 2.0, 0.5)
    fold = t.maprange(foldn.outputs["Fac"], 0.3, 0.7, 0.5, 1.15)
    col = t.mix(gi["Folds"], col, t.mix(1.0, col, t.comb(fold, fold, fold), "MULTIPLY"))
    # 5 wetness: object property cot_wet (rain ray casts) x global x per-material response
    attr = t.node("ShaderNodeAttribute", attribute_type="OBJECT", attribute_name="cot_wet")
    # multi-storey objects (one mesh for every floor of a stack) carry a per-face wetness cot_wetf: only faces open to
    # the cave sky are wet, the storey floors inside stay dry (cot_wetf_used = 1 selects it)
    wf = t.node("ShaderNodeAttribute", attribute_type="GEOMETRY", attribute_name="cot_wetf")
    wf_used = t.node("ShaderNodeAttribute", attribute_type="OBJECT", attribute_name="cot_wetf_used")
    face_wet = t.mixv(wf_used.outputs["Fac"], (1.0, 1.0, 1.0), t.comb(wf.outputs["Fac"], wf.outputs["Fac"], wf.outputs["Fac"]))
    obj_wet = t.math("MULTIPLY", attr.outputs["Fac"], t.sep(face_wet)[0])
    wet = t.math("MULTIPLY", t.math("MULTIPLY", obj_wet, G["Wet"]), gi["Wet Response"], clamp=True)
    col = t.mix(t.math("MULTIPLY", wet, 0.28), col, t._scale(col, 0.5))
    # vertical run marks on wet walls
    ms = t.node("ShaderNodeMapping")
    ms.inputs["Scale"].default_value = (6.0, 6.0, 0.22)
    t.link(vec, ms.inputs["Vector"])
    stn = t.noise(ms.outputs["Vector"], 1.0, 2.0, 0.55)
    streak = t.maprange(stn.outputs["Fac"], 0.5, 0.72, smooth=True)
    streak_f = t.math("MULTIPLY", t.math("MULTIPLY", streak, t.math("SUBTRACT", 1.0, up)),
                      t.math("MULTIPLY", t.math("MULTIPLY", wet, gi["Streaks"]), G["Streaks"]), clamp=True)
    col = t.mix(t.math("MULTIPLY", streak_f, 0.45), col, t._scale(col, 0.45))
    # 6 painted light organisation: upward faces lighter, contour darker (stage 2 rules)
    top = t.math("MULTIPLY", t.math("POWER", up, 1.5), t.math("MULTIPLY", G["TopLight"], gi["Top Light"]))
    col = t.mix(top, col, t.clamp1(t._scale(base, 2.4)))
    lw = t.node("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.5
    edge = t.maprange(lw.outputs["Facing"], 0.62, 0.93, 0.0, t.math("MULTIPLY", G["EdgeDark"], gi["Edge Dark"]), smooth=True)
    col = t.mix(edge, col, t._scale(base, 0.1))
    # roughness: wet upward faces and run marks are glossier
    # cot_dry = 1 on stage 3 objects the rain never reaches: they lose the fixed top-face gloss that the stage 2 plaza
    # materials carry (stage 2 plaza objects have no cot_dry and keep it)
    dry = t.node("ShaderNodeAttribute", attribute_type="OBJECT", attribute_name="cot_dry")
    gloss_up = t.math("MULTIPLY", gi["Gloss Up"], t.math("SUBTRACT", 1.0, dry.outputs["Fac"], clamp=True))
    gloss = t.math("MINIMUM", t.math("ADD", gloss_up, t.math("MULTIPLY", wet, 0.62)), 0.85)
    rough = t.math("MULTIPLY", gi["Roughness"], t.math("SUBTRACT", 1.0, t.math("MULTIPLY", t.math("POWER", up, 2.0), gloss)))
    rough = t.math("MULTIPLY", rough, t.math("SUBTRACT", 1.0, t.math("MULTIPLY", streak_f, 0.6)), clamp=True)
    bsdf = t.node("ShaderNodeBsdfPrincipled")
    t.link(col, bsdf.inputs["Base Color"])
    t.link(rough, bsdf.inputs["Roughness"])
    t.link(gi["Metallic"], bsdf.inputs["Metallic"])
    t.link(gi["Coat"], bsdf.inputs["Coat Weight"])
    bsdf.inputs["Coat Roughness"].default_value = 0.42
    t.link(gi["Sheen"], bsdf.inputs["Sheen Weight"])
    bsdf.inputs["Sheen Roughness"].default_value = 0.4
    # painted ambient: the region's ambient colour (object property cot_amb, set from the region family) times the
    # painted surface colour, added as self-light on every face. Noise-free and independent of light direction; the
    # materials are not sampled as light sources (emission sampling off), so it does not light the neighbours.
    amb = t.node("ShaderNodeAttribute", attribute_type="OBJECT", attribute_name="cot_amb")
    ambient = t.vmath("MULTIPLY", t.vmath("MULTIPLY", col, amb.outputs["Color"]), t.comb(G["Ambient"], G["Ambient"], G["Ambient"]))
    own = t._scale(gi["Emission Color"], gi["Emission Strength"])
    t.link(t.vmath("ADD", own, ambient), bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 1.0
    fine = t.noise(vec, 14.0, 2.0)
    bump = t.node("ShaderNodeBump")
    t.link(gi["Bump"], bump.inputs["Strength"])
    t.link(fine.outputs["Fac"], bump.inputs["Height"])
    t.link(bump.outputs["Normal"], bsdf.inputs["Normal"])
    t.link(bsdf.outputs["BSDF"], go["BSDF"])
    ng["cot_s4"] = True
    return ng


# family presets: values passed to NG_COT_Paint (inputs not listed keep the core default)
FAMILY = {
    "Stone": {"Variation": 0.6, "Noise Scale": 0.45, "World Coords": 1.0, "Seams": 0.8, "Seam Top Proj": 1.0, "Brick Width": 1.8, "Row Height": 0.75,
              "Wear": 0.6, "Streaks": 1.0, "Bump": 0.12,
              "Gloss Up": 0.12, "Wet Response": 1.0, "Seam Depth": 0.8},
    "Metal": {"Variation": 0.6, "World Coords": 1.0, "Seams": 0.0, "Wear": 0.45, "Streaks": 0.5, "Bump": 0.04, "Gloss Up": 0.2,
              "Wet Response": 1.0, "Noise Scale": 1.6},
    "Shell": {"Variation": 0.8, "World Coords": 0.0, "Seams": 0.0, "Wear": 0.15, "Streaks": 0.6, "Bump": 0.06, "Gloss Up": 0.2,
              "Wet Response": 1.0, "Coat": 0.45, "Sheen": 0.25},
    "Cloth": {"Variation": 0.7, "World Coords": 1.0, "Seams": 0.0, "Wear": 0.0, "Streaks": 0.0, "Bump": 0.03, "Gloss Up": 0.0,
              "Wet Response": 0.5, "Sheen": 0.6, "Folds": 1.0, "Top Light": 0.6},
    "Wood": {"Variation": 0.6, "World Coords": 1.0, "Seams": 0.0, "Wear": 0.25, "Streaks": 0.0, "Bump": 0.05, "Gloss Up": 0.05,
             "Wet Response": 0.3, "Coat": 0.04, "Top Light": 0.8},
}
FAMILY_EXPOSED = {"Stone": ("Seams", "Wear", "Variation", "Seam Depth"), "Metal": ("Metallic", "Wear"), "Shell": ("Coat",), "Cloth": ("Sheen",), "Wood": ()}


def build_family(name):
    preset = FAMILY[name]
    exposed = FAMILY_EXPOSED[name]
    ng = _group("NG_COT_" + name)
    ins = [("Base Color", COLOR, (0.05, 0.08, 0.17, 1.0)), ("Roughness", FLOAT, 0.6)]
    for k in exposed:
        ins.append((k, FLOAT, {"Metallic": 0.75}.get(k, preset.get(k, 0.0))))
    ins += [("Emission Color", COLOR, (0.0, 0.0, 0.0, 1.0)), ("Emission Strength", FLOAT, 0.0)]
    t, gi, go = _io(ng, ins, [("BSDF", SHADER)])
    core = t.node("ShaderNodeGroup")
    core.node_tree = bpy.data.node_groups["NG_COT_Paint"]
    for k, v in preset.items():
        if k not in exposed:
            core.inputs[k].default_value = v
    base = gi["Base Color"]
    if name == "Stone":
        # stone is a little greyer than the painted blue of shells and glass, so the families separate
        lum = t.node("ShaderNodeRGBToBW")
        t.link(base, lum.inputs[0])
        grey = t.comb(lum.outputs[0], lum.outputs[0], t.math("MULTIPLY", lum.outputs[0], 1.25))
        base = t.mix(0.28, base, grey)
    if name == "Shell":
        # segment bands of a carapace: soft dark grooves around the object's height
        tc = t.node("ShaderNodeTexCoord")
        p = t.sep(tc.outputs["Object"])
        band = t.math("SINE", t.math("MULTIPLY", p[2], 7.0))
        band = t.maprange(band, -1.0, 1.0, 0.72, 1.08, smooth=True)
        base = t.mix(1.0, base, t.comb(band, band, band), "MULTIPLY")
    if name == "Wood":
        geo = t.node("ShaderNodeNewGeometry")
        wave = t.node("ShaderNodeTexWave")
        wave.inputs["Scale"].default_value = 2.2
        wave.inputs["Distortion"].default_value = 6.0
        wave.inputs["Detail"].default_value = 2.0
        t.link(geo.outputs["Position"], wave.inputs["Vector"])
        g = t.maprange(wave.outputs["Fac"], 0.0, 1.0, 0.7, 1.1)
        base = t.mix(1.0, base, t.comb(g, g, g), "MULTIPLY")
    t.link(base, core.inputs["Base Color"])
    t.link(gi["Roughness"], core.inputs["Roughness"])
    for k in exposed:
        t.link(gi[k], core.inputs[k])
    if name == "Metal" and "Metallic" not in exposed:
        core.inputs["Metallic"].default_value = 0.6
    t.link(gi["Emission Color"], core.inputs["Emission Color"])
    t.link(gi["Emission Strength"], core.inputs["Emission Strength"])
    t.link(core.outputs["BSDF"], go["BSDF"])
    ng["cot_s4"] = True
    return ng


def build_glass():
    ng = _group("NG_COT_Glass")
    t, gi, go = _io(ng, [("Glow Color", COLOR, (0.2, 0.5, 0.74, 1.0)), ("Glow Strength", FLOAT, 0.7), ("Base Color", COLOR, (0.02, 0.04, 0.08, 1.0)),
                         ("Spread", FLOAT, 0.45)], [("BSDF", SHADER)])
    glob = t.node("ShaderNodeGroup")
    glob.node_tree = bpy.data.node_groups["NG_COT_Global"]
    tc = t.node("ShaderNodeTexCoord")
    gen = t.sep(tc.outputs["Generated"])
    info = t.node("ShaderNodeObjectInfo")
    per_obj = t.math("ADD", t.math("MULTIPLY", info.outputs["Random"], gi["Spread"]), t.math("SUBTRACT", 1.0, gi["Spread"]))
    along = t.math("ADD", t.math("MULTIPLY", t.math("SINE", t.math("MULTIPLY", gen[2], math.pi)), 0.45), 0.55)
    mp = t.node("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (22.0, 22.0, 1.2)
    t.link(tc.outputs["Generated"], mp.inputs["Vector"])
    strokes = t.noise(mp.outputs["Vector"], 1.0, 2.0)
    st = t.maprange(strokes.outputs["Fac"], 0.25, 0.75, 0.7, 1.15)
    level = t.math("MULTIPLY", t.math("MULTIPLY", per_obj, along), st)
    strength = t.math("MULTIPLY", t.math("MULTIPLY", level, gi["Glow Strength"]), glob.outputs["GlassGain"])
    bsdf = t.node("ShaderNodeBsdfPrincipled")
    t.link(gi["Base Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.22
    t.link(gi["Glow Color"], bsdf.inputs["Emission Color"])
    t.link(strength, bsdf.inputs["Emission Strength"])
    t.link(bsdf.outputs["BSDF"], go["BSDF"])
    ng["cot_s4"] = True
    return ng


def build_emit():
    ng = _group("NG_COT_Emit")
    t, gi, go = _io(ng, [("Color", COLOR, (0.8, 0.87, 1.0, 1.0)), ("Strength", FLOAT, 2.4), ("Base Color", COLOR, (0.6, 0.7, 0.9, 1.0))],
                    [("BSDF", SHADER)])
    glob = t.node("ShaderNodeGroup")
    glob.node_tree = bpy.data.node_groups["NG_COT_Global"]
    bsdf = t.node("ShaderNodeBsdfPrincipled")
    t.link(gi["Base Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.3
    t.link(gi["Color"], bsdf.inputs["Emission Color"])
    t.link(t.math("MULTIPLY", gi["Strength"], glob.outputs["LampGain"]), bsdf.inputs["Emission Strength"])
    t.link(bsdf.outputs["BSDF"], go["BSDF"])
    ng["cot_s4"] = True
    return ng


def build_water():
    """Dark water: slow noise waves plus expanding rain rings; time comes from the frame (continuous, repeatable)."""
    ng = _group("NG_COT_Water")
    t, gi, go = _io(ng, [("Base Color", COLOR, (0.006, 0.016, 0.045, 1.0)), ("Roughness", FLOAT, 0.06), ("Waves", FLOAT, 0.16),
                         ("Ripples", FLOAT, 0.0), ("Ripple Scale", FLOAT, 2.2), ("Alpha", FLOAT, 1.0)], [("BSDF", SHADER)])
    glob = t.node("ShaderNodeGroup")
    glob.node_tree = bpy.data.node_groups["NG_COT_Global"]
    geo = t.node("ShaderNodeNewGeometry")
    time = _frame_time(t, 1.6)
    wave = t.noise(geo.outputs["Position"], 2.6, 3.0, dims="4D", w=time)
    # rain rings: one ring per Voronoi cell, radius grows with a per-cell phase and repeats (no jump: fades at both ends)
    p = t.sep(geo.outputs["Position"])
    xy = t.comb(p[0], p[1], 0.0)
    vor = t.node("ShaderNodeTexVoronoi")
    vor.voronoi_dimensions = "2D"
    t.link(gi["Ripple Scale"], vor.inputs["Scale"])
    vor.inputs["Randomness"].default_value = 0.85
    t.link(xy, vor.inputs["Vector"])
    cell_rand = t.sep(vor.outputs["Color"])[0]
    tr = _frame_time(t, 1.25)
    phase = t.math("FRACT", t.math("ADD", tr, cell_rand))
    radius = t.math("MULTIPLY", phase, 0.42)
    ring = t.math("ABSOLUTE", t.math("SUBTRACT", vor.outputs["Distance"], radius))
    ring = t.maprange(ring, 0.0, 0.045, 1.0, 0.0, smooth=True)
    fade = t.math("MULTIPLY", t.math("SUBTRACT", 1.0, phase), t.maprange(phase, 0.0, 0.08, 0.0, 1.0))
    ripple = t.math("MULTIPLY", t.math("MULTIPLY", ring, fade), t.math("MULTIPLY", gi["Ripples"], glob.outputs["Wet"]))
    height = t.math("ADD", t.math("MULTIPLY", wave.outputs["Fac"], gi["Waves"]), t.math("MULTIPLY", ripple, 0.6))
    bump = t.node("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.05
    t.link(height, bump.inputs["Height"])
    bsdf = t.node("ShaderNodeBsdfPrincipled")
    t.link(gi["Base Color"], bsdf.inputs["Base Color"])
    t.link(gi["Roughness"], bsdf.inputs["Roughness"])
    t.link(gi["Alpha"], bsdf.inputs["Alpha"])
    t.link(bump.outputs["Normal"], bsdf.inputs["Normal"])
    t.link(bsdf.outputs["BSDF"], go["BSDF"])
    ng["cot_s4"] = True
    return ng


def build_groups(global_values):
    build_global(global_values)
    build_paint()
    for fam in FAMILY:
        build_family(fam)
    build_glass()
    build_emit()
    build_water()


# ----------------------------------------------------------------------------------------------- materials
def _fresh(mat):
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    t = T(nt)
    out = t.node("ShaderNodeOutputMaterial")
    return t, out


def _rgba(c):
    return tuple(c[:3]) + (1.0,)


def assign_group(mat, group, values):
    t, out = _fresh(mat)
    g = t.node("ShaderNodeGroup")
    g.node_tree = bpy.data.node_groups[group]
    for k, v in values.items():
        if k not in g.inputs:
            raise KeyError(f"{group} has no input {k} (material {mat.name})")
        sock = g.inputs[k]
        sock.default_value = _rgba(v) if isinstance(v, (list, tuple)) else float(v)
    t.link(g.outputs["BSDF"], out.inputs["Surface"])
    if group in ("NG_COT_Paint", "NG_COT_Stone", "NG_COT_Metal", "NG_COT_Shell", "NG_COT_Cloth", "NG_COT_Wood"):
        try:
            mat.cycles.emission_sampling = "NONE"          # painted ambient is not a light source
        except (AttributeError, TypeError):
            pass
    mat["cot_s4_group"] = group
    mat["cot_s4"] = True
    return g


def add_dots(mat, g, dots):
    """Fine dot speckle in object space over the group's Base Color (the dense small grey-brown dots on the cluster
    pads of 09_Bench). dots: {"scale": cells per m, "size": 0..1 dot radius in a cell, "color": rgb, "amount": 0..1}."""
    nt = mat.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "F1"
    vor.inputs["Scale"].default_value = dots.get("scale", 9.0)
    vor.inputs["Randomness"].default_value = 0.9
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")                 # distance below size -> dot (1), soft 20 % rim
    s = dots.get("size", 0.32)
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = s * 0.8, (1, 1, 1, 1)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = s, (0, 0, 0, 1)
    nt.links.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    rnd = nt.nodes.new("ShaderNodeMath")                       # not every cell has a dot
    rnd.operation = "GREATER_THAN"
    rnd.inputs[1].default_value = 1.0 - dots.get("coverage", 0.75)
    nt.links.new(vor.outputs["Color"], rnd.inputs[0])
    mask = nt.nodes.new("ShaderNodeMath")
    mask.operation = "MULTIPLY"
    nt.links.new(ramp.outputs["Color"], mask.inputs[0])
    nt.links.new(rnd.outputs[0], mask.inputs[1])
    amt = nt.nodes.new("ShaderNodeMath")
    amt.operation = "MULTIPLY"
    amt.inputs[1].default_value = dots.get("amount", 1.0)
    nt.links.new(mask.outputs[0], amt.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = tuple(g.inputs["Base Color"].default_value)
    mix.inputs["B"].default_value = _rgba(dots["color"])
    nt.links.new(amt.outputs[0], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], g.inputs["Base Color"])
    mat["cot_s4_dots"] = True


def make_material(name, spec):
    """spec: {"group": "Stone", "Base Color": [...], ...} -> material rebuilt on NG_COT_<group>.
    Optional "Dots": {...} adds a fine object-space dot speckle over the base colour (add_dots)."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    vals = {k: v for k, v in spec.items() if k not in ("group", "note", "clay", "Dots")}
    g = assign_group(mat, "NG_COT_" + spec["group"], vals)
    if spec.get("Dots"):
        add_dots(mat, g, spec["Dots"])
    base = spec.get("Base Color") or spec.get("Glow Color") or spec.get("Color") or (0.2, 0.2, 0.3)
    clay = spec.get("clay")
    mat.diffuse_color = _rgba(clay) if clay else tuple(min(1.0, c * 4 + 0.15) for c in base[:3]) + (1.0,)
    mat.roughness = float(spec.get("Roughness", 0.6))
    return mat


STAGE2_KEEP = {"petal"}        # drawn midrib and rim from the petal UVs: kept as the stage 2 tree (checked 2026-10-05)


def stage2_surface(key, color, rough, metal, coursed, emission=None):
    """Rebuild MAT_S2_<key> on NG_COT_Paint with the stage 2 parameters (stage 4 extras off)."""
    mat = bpy.data.materials.get("MAT_S2_" + key)
    if mat is None:
        return None
    clay = tuple(mat.diffuse_color)
    vals = {"Base Color": color, "Roughness": rough, "Metallic": metal, "Variation": 1.0, "Noise Scale": 0.9, "World Coords": 0.0,
            "Top Light": 1.0, "Edge Dark": 1.0, "Gloss Up": 0.62, "Wet Response": 0.0, "Seams": 1.0 if coursed else 0.0,
            "Seam Top Proj": 0.0, "Brick Width": 1.25, "Row Height": 0.56, "Wear": 0.0, "Streaks": 0.0, "Bump": 0.12,
            "Coat": 0.0, "Sheen": 0.0, "Folds": 0.0}
    if emission:
        vals["Emission Color"], vals["Emission Strength"] = emission
    assign_group(mat, "NG_COT_Paint", vals)
    mat.diffuse_color = clay
    mat["cot_s4_from_s2"] = True
    return mat


def add_glass_gain(mat):
    """Insert Global.GlassGain into a stage 2 pane material: emission strength x gain (gain 1 = unchanged)."""
    if mat is None or mat.get("cot_s4_gain"):
        return
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return
    sock = bsdf.inputs["Emission Strength"]
    t = T(nt)
    glob = t.node("ShaderNodeGroup")
    glob.node_tree = bpy.data.node_groups["NG_COT_Global"]
    if sock.is_linked:
        src = sock.links[0].from_socket
        nt.links.remove(sock.links[0])
        t.link(t.math("MULTIPLY", src, glob.outputs["GlassGain"]), sock)
    else:
        t.link(t.math("MULTIPLY", sock.default_value, glob.outputs["GlassGain"]), sock)
    mat["cot_s4_gain"] = True


def add_ambient(mat):
    """Painted ambient for a stage 2 special material (shell-tower tiers): emission = own emission + base x cot_amb.
    Stage 2 plaza objects carry no cot_amb, so the plaza look is unchanged."""
    if mat is None or mat.get("cot_s4_amb"):
        return
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return
    t = T(nt)
    glob = t.node("ShaderNodeGroup")
    glob.node_tree = bpy.data.node_groups["NG_COT_Global"]
    col_in, str_in, base_in = bsdf.inputs["Emission Color"], bsdf.inputs["Emission Strength"], bsdf.inputs["Base Color"]
    col = col_in.links[0].from_socket if col_in.is_linked else tuple(col_in.default_value)[:3]
    stren = str_in.links[0].from_socket if str_in.is_linked else str_in.default_value
    base = base_in.links[0].from_socket if base_in.is_linked else tuple(base_in.default_value)[:3]
    for s in (col_in, str_in):
        for l in list(s.links):
            nt.links.remove(l)
    own = t._scale(col, stren)
    amb = t.node("ShaderNodeAttribute", attribute_type="OBJECT", attribute_name="cot_amb")
    ambient = t.vmath("MULTIPLY", t.vmath("MULTIPLY", base, amb.outputs["Color"]), t.comb(glob.outputs["Ambient"], glob.outputs["Ambient"], glob.outputs["Ambient"]))
    t.link(t.vmath("ADD", own, ambient), col_in)
    str_in.default_value = 1.0
    mat["cot_s4_amb"] = True


def add_lamp_gain(mat):
    if mat is None or mat.get("cot_s4_gain"):
        return
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return
    sock = bsdf.inputs["Emission Strength"]
    t = T(nt)
    glob = t.node("ShaderNodeGroup")
    glob.node_tree = bpy.data.node_groups["NG_COT_Global"]
    t.link(t.math("MULTIPLY", sock.default_value, glob.outputs["LampGain"]), sock)
    mat["cot_s4_gain"] = True
