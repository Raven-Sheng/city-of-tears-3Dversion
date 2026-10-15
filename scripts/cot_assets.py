"""Stage 2 asset kit for the fountain plaza sample (all Blender-built, parametric where it repeats).

Each builder creates real meshes / bevelled curves in the given collection and returns the objects.
`mats(key)` maps a material key to a bpy material. `P(asset, ev, ref)` makes the custom properties:
cot_s2 marks stage-2 generated objects (build_plaza.py only ever rebuilds those), cot_asset is the stable
asset id used by docs/asset_catalog.csv, cot_evidence is A / B / C.
"""
import math

from cot_geo import Geo, IronCurves, TAU, arc_pts, bez, catmull, fbm, instance, lerp, place, resample, rng, spiral_pts
from cot_statue import build_statue


def P(asset, ev="A", ref="", **extra):
    props = {"cot_s2": True, "cot_asset": asset, "cot_evidence": ev, "cot_ref": ref}
    props.update(extra)
    return props


def place_all(objs, matrices, coll, base):
    """Put the built objects at matrices[0] and linked duplicates at the rest. Returns every object."""
    out = []
    for i, m in enumerate(matrices):
        for o in objs:
            if i == 0:
                o.matrix_world = m
                out.append(o)
            else:
                out.append(instance(o, f"{o.name}.{i:03d}", coll, m))
    return out


# ============================================================================ ironwork
LAMP_ARM_X, LAMP_GLOBE_Z, LAMP_GLOBE_R = 0.71, 1.75, 0.155


def build_lamp(coll, mats, name="COT_Lamp_Double", props=None):
    """Double-headed street lamp (12_Materials/Materials_01, 13_Lighting/Lighting_01, user close-up). Height 2.9.

    Read from the main reference at the play-plane scale: arm shoulders 2.8 above the paving, globes 0.3 across
    hanging 1.75 up and 1.42 apart. Each arm is a heavy S stroke that ends in an outward curl; the post carries
    back-to-back volutes above and below the arm joint and a short leaf finial.
    """
    ax = LAMP_ARM_X
    ic = IronCurves()
    ic.add([(0, 0, 0), (0, 0, 0.05), (0, 0, 0.13), (0, 0, 0.2), (0, 0, 0.34), (0, 0, 0.5), (0, 0, 1.4), (0, 0, 2.3), (0, 0, 2.62)],
           r=[5.6, 5.0, 3.0, 3.4, 1.7, 1.15, 1.05, 1.05, 0.9], smooth=False)
    for z, rr in ((0.5, 2.1), (0.62, 1.6), (2.3, 2.3), (2.4, 1.7)):
        ic.add([(0, 0, z), (0, 0, z + 0.06)], r=rr, smooth=False)
    for k in range(6):                                           # ribbed skirt of the foot
        a = TAU * k / 6
        ic.add([(0.045 * math.cos(a), 0.045 * math.sin(a), 0.5), (0.085 * math.cos(a), 0.085 * math.sin(a), 0.3),
                (0.15 * math.cos(a), 0.15 * math.sin(a), 0.06)], r=[0.5, 0.75, 0.9])
    ic.spike(0, 2.62, 2.92, r=1.5)
    # arm: out of the joint, up over the shoulder, down to the hook
    arm = [(0.02, 2.33), (0.09, 2.5), (0.2, 2.69), (0.36, 2.8), (0.52, 2.76), (0.63, 2.6), (0.69, 2.4), (ax, 2.24)]
    ic.add(arm, r=[1.9, 1.8, 1.7, 1.6, 1.5, 1.4, 1.3, 1.2], mirror_x=0)
    ic.add(spiral_pts(ax + 0.075, 2.235, 0.075, 1.15, math.pi, ccw=False), r=1.15, mirror_x=0, taper="end")
    ic.add(bez((0.36, 2.8), (0.4, 2.9), (0.5, 2.95), (0.57, 2.9), 6), r=0.9, mirror_x=0, taper="end")       # shoulder tendril
    # volutes hugging the post: a pair above the joint, a pair below, and a heart-shaped tie between them
    ic.add(spiral_pts(0.19, 2.52, 0.125, 1.35, -math.pi / 2, ccw=True), r=1.1, mirror_x=0, taper="end")
    ic.add(bez((0.02, 2.36), (0.1, 2.36), (0.17, 2.38), (0.19, 2.395), 5), r=1.1, mirror_x=0)
    ic.add(spiral_pts(0.15, 2.15, 0.105, 1.25, math.pi / 2, ccw=False), r=1.0, mirror_x=0, taper="end")
    ic.add(bez((0.02, 2.3), (0.08, 2.3), (0.13, 2.28), (0.15, 2.255), 5), r=1.0, mirror_x=0)
    ic.add(bez((0.0, 2.62), (0.1, 2.72), (0.23, 2.76), (0.3, 2.68), 6) + bez((0.3, 2.68), (0.33, 2.62), (0.3, 2.58), (0.26, 2.6), 4)[1:],
           r=0.85, mirror_x=0, taper="end")
    ic.add(bez((0.02, 2.0), (0.1, 2.02), (0.2, 1.96), (0.2, 1.88), 6) + bez((0.2, 1.88), (0.2, 1.82), (0.14, 1.8), (0.11, 1.85), 4)[1:],
           r=0.8, mirror_x=0, taper="end")
    ic.add([(ax, 2.24), (ax, 2.08)], r=0.9, mirror_x=0, smooth=False)
    iron = ic.to_object(name + "_Iron", coll, mats("iron"), bevel=0.036, props=props)
    g = Geo()
    gz, gr = LAMP_GLOBE_Z, LAMP_GLOBE_R
    for sx in (-1, 1):
        g.use("iron")                                            # bell cap with a collar and a small top knob
        g.revolve([(0.02, gz + 0.33), (0.04, gz + 0.31), (0.028, gz + 0.28), (0.05, gz + 0.25), (0.085, gz + 0.19), (0.1, gz + 0.13),
                   (0.09, gz + 0.105), (0.0, gz + 0.105)], segs=14, m=place(sx * ax, 0, 0))
        g.use("lamp")
        g.ellipsoid((sx * ax, 0, gz), (gr, gr, gr), segs=18, steps=12)
    globes = g.to_object(name + "_Globes", coll, mats, props)
    return [iron, globes]


LAMP_GLOBES = ((-LAMP_ARM_X, 0.0, LAMP_GLOBE_Z), (LAMP_ARM_X, 0.0, LAMP_GLOBE_Z))


def build_sign_oval(coll, mats, name="COT_Sign_Oval", props=None):
    """Oval glyph plaque on a post with a spike finial (left of the fountain in the main reference)."""
    ic = IronCurves()
    ic.add([(0, 0, 0), (0, 0, 0.08), (0, 0, 0.3), (0, 0, 2.62)], r=[3.6, 3.0, 1.2, 1.0], smooth=False)
    ic.add([(0.42 * math.cos(TAU * i / 24), 3.04 + 0.33 * math.sin(TAU * i / 24)) for i in range(24)], r=1.3, cyclic=True)
    ic.spike(0, 3.36, 4.1, r=1.6)
    ic.add(spiral_pts(0.2, 2.6, 0.11, 1.2, math.pi / 2, ccw=False), r=0.8, mirror_x=0, taper="end")
    ic.add([(0.42, 3.04), (0.52, 3.1), (0.56, 3.0), (0.5, 2.94)], r=0.7, mirror_x=0, taper="end")
    iron = ic.to_object(name + "_Iron", coll, mats("iron"), bevel=0.024, props=props)
    g = Geo().use("sign")
    rows, uvs = [], []
    for k in range(7):
        a = -math.pi / 2 + math.pi * k / 6
        s = max(0.04, math.cos(a))
        rows.append([(0.4 * s * math.cos(TAU * i / 24), 0.06 * math.sin(a), 3.04 + 0.31 * s * math.sin(TAU * i / 24)) for i in range(24)])
        uvs.append([(0.5 + 0.5 * s * math.cos(TAU * i / 24), 0.5 + 0.5 * s * math.sin(TAU * i / 24)) for i in range(24)])
    g.grid(rows, close_u=True, cap_start=True, cap_end=True, uvs=uvs)
    plaque = g.to_object(name + "_Plaque", coll, mats, props)
    return [iron, plaque]


def build_sign_spear(coll, mats, name="COT_Sign_Spear", props=None):
    """Tall leaf-shaped glyph sign with scroll wings (right of the fountain; 12_Materials/Materials_02)."""
    ic = IronCurves()
    ic.add([(0, 0, 0), (0, 0, 0.08), (0, 0, 0.3), (0, 0, 2.3)], r=[3.6, 3.0, 1.2, 1.0], smooth=False)
    ic.spike(0, 3.5, 4.35, r=1.7)
    for sx in (-1, 1):
        ic.add([(0.0, 2.3), (sx * 0.2, 2.42), (sx * 0.34, 2.62), (sx * 0.3, 2.82)], r=0.9, taper="end")
        ic.add(spiral_pts(sx * 0.36, 2.5, 0.12, 1.2, math.pi / 2 if sx > 0 else math.pi / 2, ccw=sx < 0), r=0.8, taper="end")
        ic.add([(0.0, 2.36), (sx * 0.14, 2.3), (sx * 0.24, 2.18), (sx * 0.18, 2.08)], r=0.7, taper="end")
    outline = [(0.27 * math.sin(math.pi * t) ** 0.8 * s, 2.36 + 1.16 * t) for s, ts in ((1, range(0, 13)), (-1, range(12, -1, -1)))
               for t in [k / 12 for k in ts]]
    ic.add(outline, r=1.1, cyclic=True)
    iron = ic.to_object(name + "_Iron", coll, mats("iron"), bevel=0.024, props=props)
    g = Geo().use("sign")
    rows, uvs = [], []
    for i in range(13):
        t = i / 12
        hw = max(0.25 * math.sin(math.pi * t) ** 0.8, 0.004)
        rows.append([(hw * math.cos(TAU * k / 10), 0.05 * math.sin(TAU * k / 10), 2.36 + 1.16 * t) for k in range(10)])
        uvs.append([(0.5 + 0.5 * math.cos(TAU * k / 10), t) for k in range(10)])
    g.grid(rows, close_u=True, cap_start=True, cap_end=True, uvs=uvs)
    plaque = g.to_object(name + "_Plaque", coll, mats, props)
    return [iron, plaque]


def fence_web_curves(width=1.5, posts=True):
    """Low gate-like fence panel with a barred oval and web arcs (13_Lighting/Lighting_01, 20260911201846_1)."""
    w = width
    c = w / 2
    ic = IronCurves()
    if posts:
        for x in (0.0, w):
            ic.add([(x, 0, 0), (x, 0, 1.15)], r=1.5, smooth=False)
            ic.spike(x, 1.15, 1.74, r=1.5)
    ic.add([(0, 0.06), (w, 0.06)], r=1.0, smooth=False)
    ic.add(bez((0, 1.12), (w * 0.3, 0.84), (w * 0.7, 0.84), (w, 1.12), 10), r=1.1)
    ic.add(bez((0, 1.0), (w * 0.3, 0.75), (w * 0.7, 0.75), (w, 1.0), 10), r=0.8)
    ic.add(bez((0, 0.86), (w * 0.3, 0.69), (w * 0.7, 0.69), (w, 0.86), 10), r=0.7)
    ic.add([(c + 0.24 * math.cos(TAU * i / 20), 0.47 + 0.33 * math.sin(TAU * i / 20)) for i in range(20)], r=1.0, cyclic=True)
    for z in (0.38, 0.57):
        hw = 0.24 * math.sqrt(max(0.0, 1 - ((z - 0.47) / 0.33) ** 2))
        ic.add([(c - hw, z), (c + hw, z)], r=0.8, smooth=False)
    ic.add([(c, 0.8), (c, 0.9)], r=0.9, smooth=False)
    ic.add([(c, 0.06), (c, 0.14)], r=0.9, smooth=False)
    ic.add(bez((0.02, 0.08), (0.28, 0.12), (0.42, 0.28), (c - 0.24, 0.47), 8), r=0.8, mirror_x=c)
    ic.add(bez((0.02, 0.92), (0.2, 0.74), (0.36, 0.7), (c - 0.2, 0.66), 8), r=0.8, mirror_x=c)
    ic.add(spiral_pts(0.27, 0.6, 0.1, 1.25, 0.0, ccw=True), r=0.7, mirror_x=c, taper="end")
    ic.add(spiral_pts(0.2, 0.3, 0.085, 1.2, math.pi, ccw=False), r=0.7, mirror_x=c, taper="end")
    return ic


def railing_bay_curves(bay=1.05, final_post=False):
    """Ornate railing bay with a turned baluster and tall spike (12_Materials/Materials_01)."""
    ic = IronCurves()
    xs = (0.0, bay) if final_post else (0.0,)
    for x in xs:
        ic.add([(x, 0, z) for z in (0, 0.08, 0.16, 0.3, 0.42, 0.5, 0.62, 0.74, 0.82, 0.9)],
               r=[2.4, 2.8, 1.5, 1.3, 2.6, 1.4, 1.2, 2.4, 1.3, 1.7], smooth=True)
        ic.spike(x, 0.9, 2.02, r=2.0)
    c = bay / 2
    ic.add([(0, 0.82), (bay, 0.82)], r=1.5, smooth=False)
    ic.add([(0, 0.08), (bay, 0.08)], r=1.5, smooth=False)
    ic.add([(0, 0.22), (bay, 0.22)], r=0.9, smooth=False)                      # lower band holding a row of small links
    for k in range(4):
        cx_ = bay * (k + 0.5) / 4
        ic.add([(cx_ + 0.085 * math.cos(TAU * i / 10), 0.15 + 0.05 * math.sin(TAU * i / 10)) for i in range(10)], r=0.55, cyclic=True)
    ic.add([(c + 0.19 * math.cos(TAU * i / 16), 0.5 + 0.23 * math.sin(TAU * i / 16)) for i in range(16)], r=1.0, cyclic=True)
    ic.add([(c + 0.1 * math.cos(TAU * i / 12), 0.5 + 0.13 * math.sin(TAU * i / 12)) for i in range(12)], r=0.6, cyclic=True)
    for sx in (-1, 1):
        for sz in (-1, 1):
            ic.add(spiral_pts(c + sx * 0.35, 0.5 + sz * 0.16, 0.11, 1.3, (0 if sx < 0 else math.pi), ccw=(sx * sz > 0)), r=0.8, taper="end")
            # tendril from the post into the corner of the panel
            ic.add(bez((c + sx * 0.5, 0.5 + sz * 0.3), (c + sx * 0.4, 0.5 + sz * 0.34), (c + sx * 0.28, 0.5 + sz * 0.33), (c + sx * 0.17, 0.5 + sz * 0.26), 6),
                   r=0.65, taper="end")
        ic.add(bez((c + sx * 0.19, 0.5), (c + sx * 0.3, 0.5), (c + sx * 0.42, 0.55), (c + sx * 0.5, 0.5), 6), r=0.75)
    ic.add([(c, 0.73), (c, 0.82)], r=0.9, smooth=False)
    ic.add([(c, 0.22), (c, 0.27)], r=0.9, smooth=False)
    # cresting on the top rail: a pointed leaf between two rising scrolls (A: Materials_01)
    ic.spike(c, 0.82, 1.1, r=1.5, bulb=True)
    for sx in (-1, 1):
        ic.add(bez((c + sx * 0.5, 0.84), (c + sx * 0.38, 0.86), (c + sx * 0.22, 0.9), (c + sx * 0.1, 1.0), 7), r=0.75, taper="end")
        ic.add(spiral_pts(c + sx * 0.27, 0.91, 0.055, 1.1, math.pi / 2, ccw=sx > 0), r=0.6, taper="end")
    return ic


TRUSS_POINT = 1.6       # exponent of the arch curve: 2 is a parabola, lower gives the soft point seen in the reference


def truss_dims(span, rise=None, depth=None):
    """Band proportions read from the main reference: rise 0.2 of the span, band depth 0.13 of the span."""
    rise = 0.2 * span if rise is None else rise
    depth = min(0.56, max(0.24, 0.13 * span)) if depth is None else depth
    return rise, depth


def truss_samples(span, rise, half=None, n=28):
    """Top chord of a shallow pointed arch with its inward (downward) normals: (x, z, nx, nz) per sample.

    half="L" is the left half of an arch only (low end at x=0, apex at x=span); "R" is its mirror.
    """
    pts = []
    for i in range(n + 1):
        x = span * i / n
        u = (span - x) / span if half == "L" else (x / span if half == "R" else abs(x - span / 2) / (span / 2))
        pts.append((x, rise * (1 - u ** TRUSS_POINT)))
    out = []
    for i, (x, z) in enumerate(pts):
        (ax, az), (bx, bz) = pts[max(i - 1, 0)], pts[min(i + 1, n)]
        ln = math.hypot(bx - ax, bz - az) or 1.0
        out.append((x, z, (bz - az) / ln, -(bx - ax) / ln))
    return out


def arch_truss_curves(span, rise=None, depth=None, spikes=True, half=None):
    """Arched iron truss of the scaffold towers (11_Lower_City/Lower_City_statue.jpg left side, 13_Lighting/Lighting_01).

    A band between three chords that follows a shallow pointed arch, with two rows of key fret, a turned finial
    and pendant at the apex, and at each springing a spike above and a wing of pointed blades hanging down the post.
    Local frame: XZ plane, springing (top chord at the ends) on z=0. The dark backing plate is add_truss_plate().
    """
    rise, depth = truss_dims(span, rise, depth)
    sm = truss_samples(span, rise, half)
    n = len(sm) - 1
    ic = IronCurves()

    def at(s, d):
        f = min(max(s, 0.0), 1.0) * n
        i = min(int(f), n - 1)
        t = f - i
        x, z, nx, nz = (lerp(a, b, t) for a, b in zip(sm[i], sm[i + 1]))
        return (x + nx * d, z + nz * d)

    for d, rr in ((0.0, 1.7), (depth / 2, 0.9), (depth, 1.7)):
        ic.add([at(i / n, d) for i in range(n + 1)], r=rr)
    cells = max(4, round(span / 0.3))
    key = ((0.0, 0.16), (0.0, 0.84), (0.7, 0.84), (0.7, 0.48), (0.35, 0.48), (0.35, 0.16), (1.0, 0.16))
    for row in (0, 1):
        pts = []
        for c in range(cells):
            for u, v in (key if c == 0 else key[1:]):
                v = v if row == 0 else 1.0 - v
                pts.append(at((c + u) / cells, depth * (row + 0.1 + 0.8 * v) / 2))
        ic.add(pts, r=0.75, smooth=False)
    ends = [(0, 1, True)] if half == "L" else ([(n, -1, True)] if half == "R" else [(0, 1, True), (n, -1, True)])
    apex = n if half == "L" else (0 if half == "R" else n // 2)
    ax_, az_ = sm[apex][0], sm[apex][1]
    if spikes:
        fin = min(1.45, max(0.6, 0.34 * span * (2 if half else 1)))
        ic.add([(ax_, az_ - depth - 0.06), (ax_, az_ + 0.1)], r=2.1, smooth=False)
        for z, rr in ((az_ + 0.06, 3.0), (az_ + 0.17, 2.3)):
            ic.add([(ax_, z), (ax_, z + 0.05)], r=rr, smooth=False)
        ic.spike(ax_, az_ + 0.2, az_ + fin, r=2.0)
        ic.add([(ax_, az_ - depth), (ax_, az_ - depth - 0.16), (ax_, az_ - depth - 0.4)], r=[1.4, 2.0, 0.1], smooth=False)
        for sx in ((-1, 1) if half is None else ((-1,) if half == "L" else (1,))):                 # small leaves beside the finial
            ic.add([(ax_, az_ + 0.1), (ax_ + sx * 0.2, az_ + 0.2), (ax_ + sx * 0.36, az_ + 0.1)], r=1.5, taper="end")
    wing = min(1.3, max(0.7, 2.4 * depth))
    for i, sx, low in ends:
        x, z = sm[i][0], sm[i][1]
        bx, bz = at(i / n, depth)
        ic.add([(x, bz - 0.3), (x, z + 0.12)], r=1.9, smooth=False)
        if spikes:
            ic.spike(x, z + 0.1, z + 0.72, r=1.7)
        for k in range(6):                                       # wing of blades hanging from the end of the band
            f = k / 5
            sx_, sz_ = at((i / n) + sx * 0.13 * f, depth)
            tip = (x + sx * (0.03 + 0.4 * f), bz - wing * (1.0 - 0.62 * f))
            ic.add(bez((sx_, sz_ + 0.02), (sx_, sz_ - 0.3 * wing), (tip[0] + sx * 0.05, tip[1] + 0.4 * wing), tip, 7),
                   r=3.6 - 0.8 * f, taper="end")
    return ic


def add_truss_plate(g, span, m, rise=None, depth=None, half=None, key="iron_plate", thick=0.022):
    """Dark backing plate of a truss band (the reference draws the band solid, with the fret lighter on it)."""
    rise, depth = truss_dims(span, rise, depth)
    g.use(key)
    rows = []
    for x, z, nx, nz in truss_samples(span, rise, half):
        bx, bz = x + nx * depth, z + nz * depth
        rows.append([(x, -thick, z), (bx, -thick, bz), (bx, thick, bz), (x, thick, z)])
    g.grid(rows, close_u=True, cap_start=True, cap_end=True, m=m)


def add_truss(ic, g, span, m, rise=None, depth=None, half=None, spikes=True):
    """One truss: curves into ic, backing plate into g, both placed with m."""
    ic.extend(arch_truss_curves(span, rise, depth, spikes=spikes, half=half), m)
    add_truss_plate(g, span, m, rise, depth, half)


def build_scaffold(coll, mats, name, posts, bays, props=None, bevel=0.034):
    """Tall iron scaffold made of posts and arched trusses standing in vertical planes.

    posts: (x, y, z_base, z_top). bays: (ax, ay, bx, by, tiers, half, rise, depth) - a truss from post a to post b
    at each height in tiers (Z of the springing); half None / "L" / "R" as in arch_truss_curves; rise / depth None
    take the default proportions. Returns [iron curves, backing plates].
    """
    ic = IronCurves()
    g = Geo()
    for x, y, zb, zt in posts:
        ic.add([(x, y, zb), (x, y, zt)], r=1.9, smooth=False)
        ic.add([(x, y, zb), (x, y, zb + 0.12), (x, y, zb + 0.3)], r=[4.2, 3.6, 1.9], smooth=False)
        ic.spike(x, zt, zt + 0.9, r=1.7, y=y)
    for ax, ay, bx, by, tiers, half, rise, depth in bays:
        span = math.hypot(bx - ax, by - ay)
        truss = arch_truss_curves(span, rise, depth, half=half)
        for z in tiers:
            m = place(ax, ay, z, rz=math.atan2(by - ay, bx - ax))
            ic.extend(truss, m)
            add_truss_plate(g, span, m, rise, depth, half=half)
    return [ic.to_object(name, coll, mats("iron_scaffold"), bevel=bevel, props=props), g.to_object(name + "_Plates", coll, mats, props)]


# ============================================================================ leaf windows and towers
def leaf_half_width(t, w):
    return 0.5 * w * max(math.sin(math.pi * t), 0.0) ** 0.86


def add_leaf_window(gf, gg, m, w, h, index=0, bulge=0.16, ribs=4, frame=None, frame_key="window_frame", glass_key="glass"):
    """Leaf / cocoon window: bulged luminous pane, thick rim, chevron ribs and tip knobs. Faces local -Y."""
    frame = frame if frame is not None else 0.045 * w + 0.02
    nt, ns = 18, 8

    def pane(t, s):
        hw = leaf_half_width(t, w)
        return (hw * s, -bulge * w * (1 - s * s) * math.sin(math.pi * t) ** 0.6, (t - 0.5) * h)

    gg.use(glass_key)
    rows, uvs = [], []
    for i in range(nt + 1):
        t = i / nt
        rows.append([pane(t, -1 + 2 * k / ns) for k in range(ns + 1)] + [(leaf_half_width(t, w) * (1 - 2 * k / ns), 0.05 * w, (t - 0.5) * h) for k in range(1, ns)])
        uvs.append([(index + 0.02 + 0.96 * k / ns, t) for k in range(ns + 1)] + [(index + 0.98 - 0.96 * k / ns, t) for k in range(1, ns)])
    gg.grid(rows, close_u=True, cap_start=True, cap_end=True, m=m, uvs=uvs)
    gf.use(frame_key)
    for s in (-1, 1):
        path = [(leaf_half_width(i / nt, w) * s, -0.01, (i / nt - 0.5) * h) for i in range(nt + 1)]
        gf.tube(path, frame * 0.9, frame, segs=6, ref=(0, 1, 0), m=m)
    for k in range(1, ribs + 1):
        tk = k / (ribs + 1) - 0.03
        path = []
        for j in range(9):
            s = -1 + 2 * j / 8
            t = tk + 0.085 * (1 - abs(s))
            x, y, z = pane(t, s * 0.985)
            path.append((leaf_half_width(tk, w) * s, y - 0.012 * w, z))
        gf.tube(path, frame * 0.5, frame * 0.5, segs=5, ref=(0, 1, 0), m=m)
    gf.spike((0, -0.01, -0.5 * h), (0, -0.01, -0.5 * h - 0.09 * h), frame * 1.5, segs=6, m=m, bulb=0.8)
    gf.spike((0, -0.01, 0.5 * h), (0, -0.01, 0.5 * h + 0.06 * h), frame * 1.3, segs=6, m=m)


def add_fringe_tier(g, cx, cy, z_top, z_bot, r_top, r_bot, ry_scale=1.0, segs=72, seed=0, ragged=0.34, a0=0.0, a1=TAU):
    """One shell-fringe tier: a rounded tuft that bulges out below its top and droops into a ragged hem.

    Real thickness (outer skin, hem, inner skin). UVs: u runs round the tier in lock widths, v from the top (0)
    to the hem (1); the fringe material paints the light-to-dark gradient and the vertical strokes from them.
    """
    rand = rng(seed * 7919 + 13)
    h = z_top - z_bot
    hem = []
    for i in range(segs):
        v = fbm(i * 0.55 + seed * 3.1, seed * 1.7, 0.0, 3)
        tooth = (rand() ** 2.0) * 1.25 + (0.3 if i % 4 == 0 else 0.0)
        hem.append(h * ragged * (0.3 * v + tooth * 0.8))
    wob = [1.0 + 0.022 * math.sin(i * 2.399 + seed) + 0.03 * fbm(i * 0.9, seed * 0.37, 1.7, 2) for i in range(segs)]
    closed = abs((a1 - a0) - TAU) < 1e-6
    if closed:
        a0, a1 = a0 + math.pi / 2, a1 + math.pi / 2          # UV seam on the far (+Y) side
    count = segs if closed else segs + 1
    locks = max(5, round(r_bot * 1.5))
    phase = seed * 1.37
    steps = 8
    rows, uvs = [], []
    for k in range(steps + 1):
        t = k / steps
        shoulder = math.sin(math.pi / 2 * min(1.0, t / 0.38))
        rr = r_top + (r_bot * 1.07 - r_top) * shoulder - r_bot * 0.07 * max(0.0, (t - 0.38) / 0.62) ** 1.5
        row, uvrow = [], []
        for i in range(count):
            a = a0 + (a1 - a0) * i / segs
            z = z_top - h * t ** 1.35
            if k == steps:
                z -= hem[i % segs]
            elif k == steps - 1:
                z -= hem[i % segs] * 0.5
            elif k == steps - 2:
                z -= hem[i % segs] * 0.15
            lock = 1.0 + 0.045 * math.sin(locks * a + phase) * min(1.0, t * 2.0)
            rw = rr * lock * (1.0 + (wob[i % segs] - 1.0) * t)
            row.append((cx + rw * math.cos(a), cy + rw * math.sin(a) * ry_scale, z))
            uvrow.append((locks * i / segs, t))
        rows.append(row)
        uvs.append(uvrow)
    inner, top_in, uv_dark = [], [], []
    for i in range(count):
        a = a0 + (a1 - a0) * i / segs
        inner.append((cx + r_bot * 0.9 * math.cos(a), cy + r_bot * 0.9 * math.sin(a) * ry_scale, lerp(z_top, z_bot, 0.55)))
        top_in.append((cx + r_top * 0.9 * math.cos(a), cy + r_top * 0.9 * math.sin(a) * ry_scale, z_top))
        uv_dark.append((locks * i / segs, 1.0))
    g.grid([top_in] + rows + [inner, top_in], close_u=closed, uvs=[uv_dark] + uvs + [uv_dark, uv_dark])


WINDOW_R = 1.13      # leaf windows sit just proud of the bulged tiers


def build_tower(coll, mats, name, cx, cy, z0, z1, r, tier_h, windows, roof="dome", seed=1, props=None, ry_scale=1.0,
                glass_key="glass", core_key="tower_core", fringe_key="fringe", taper=None, window_bulge=0.16):
    """Shell tower: dark core, overlapping fringe tiers, leaf windows. windows: (theta, z, w, h).

    theta is measured from the viewer-facing direction (-Y) toward +X. taper(z) -> radius factor.
    """
    taper = taper or (lambda z: 1.0)
    g = Geo().use(core_key)
    prof = []
    steps = max(4, int((z1 - z0) / 4))
    for i in range(steps + 1):
        z = lerp(z0, z1, i / steps)
        prof.append((r * 0.88 * taper(z), z))
    g.revolve(prof, segs=40, sx=1.0, sy=ry_scale, m=place(cx, cy, 0))
    g.use(fringe_key)
    tiers = max(1, round((z1 - z0) / tier_h))
    th = (z1 - z0) / tiers
    segs = max(72, int(r * 18))
    for k in range(tiers):
        zt = z0 + th * (k + 1)
        zb = z0 + th * k - th * 0.3
        add_fringe_tier(g, cx, cy, zt, zb, r * 0.95 * taper(zt), r * 1.05 * taper(zb), ry_scale, segs=segs, seed=seed * 31 + k)
    if roof == "dome":
        add_fringe_tier(g, cx, cy, z1 + r * 0.5, z1 - th * 0.18, r * 0.42, r * 1.08, ry_scale, segs=segs, seed=seed * 31 + 97, ragged=0.22)
        g.ellipsoid((cx, cy, z1 + r * 0.42), (r * 0.5, r * 0.5 * ry_scale, r * 0.32), segs=24, steps=8)
    elif roof == "umbrella":
        add_fringe_tier(g, cx, cy, z1 + r * 0.36, z1 - th * 0.2, r * 0.12, r * 1.2, ry_scale, segs=segs, seed=seed * 31 + 97, ragged=0.2)
        # the umbrella itself: a wide shallow cone with ribs and a spike over the fringe (A: umbrella-capped tower, master B1)
        g.revolve([(r * 1.42, z1 + r * 0.1), (r * 1.3, z1 + r * 0.2), (r * 0.6, z1 + r * 0.5), (r * 0.16, z1 + r * 0.72), (0.02, z1 + r * 0.78)], segs=40,
                  m=place(cx, cy, 0) @ place(s=(1.0, ry_scale, 1.0)))
        for k in range(12):
            a_ = TAU * k / 12
            g.tube([(cx + r * 1.4 * math.cos(a_), cy + r * 1.4 * ry_scale * math.sin(a_), z1 + r * 0.12),
                    (cx + r * 0.18 * math.cos(a_), cy + r * 0.18 * ry_scale * math.sin(a_), z1 + r * 0.74)], max(0.06, r * 0.02), segs=5)
            g.spike((cx + r * 1.4 * math.cos(a_), cy + r * 1.4 * ry_scale * math.sin(a_), z1 + r * 0.12),
                    (cx + r * 1.5 * math.cos(a_), cy + r * 1.5 * ry_scale * math.sin(a_), z1 - r * 0.12), max(0.05, r * 0.02), segs=5)
        g.spike((cx, cy, z1 + r * 0.7), (cx, cy, z1 + r * 1.3), max(0.1, r * 0.05), segs=6, bulb=1.0)
    body = g.to_object(name + "_Body", coll, mats, props, smooth_angle=60)
    gf, gg = Geo(), Geo()
    for i, (theta, z, w, h) in enumerate(windows):
        rr = r * WINDOW_R * taper(z) + 0.06
        px, py = cx + rr * math.sin(theta), cy - rr * math.cos(theta) * ry_scale
        add_leaf_window(gf, gg, place(px, py, z, rz=theta), w, h, index=i + seed * 7, bulge=window_bulge, glass_key=glass_key)
    frames = gf.to_object(name + "_WindowFrames", coll, mats, props)
    glass = gg.to_object(name + "_WindowGlass", coll, mats, props)
    return [o for o in (body, frames, glass) if o is not None]


# ============================================================================ stone, shells, ground
def add_shell_mound(g, m, rx, ry, rz, lobes=4, key="shell_mound", slant=0.0, step=0.07):
    """Low shell loaf: segments along its length that overlap like carapace plates.

    Each segment stands a little proud of the next one (step), so the joints read as drawn lines; slant leans the
    joints over with height, as on the loaves left and right of the fountain in the main reference.
    """
    g.use(key)
    per, ns = 7, 18
    rows = []
    for b in range(lobes):
        for j in range(per + 1):
            t = min(0.997, max(0.003, (b + j / per) / lobes))
            env = (1 - (2 * t - 1) ** 2) ** 0.55
            proud = 1.0 + step * (1.0 - j / per) ** 1.5 * (1.0 if b > 0 else 0.3)
            row = []
            for k in range(ns + 1):
                a = math.pi * k / ns
                z = rz * env * proud * math.sin(a) ** 0.8
                row.append(((2 * t - 1) * rx + slant * z, ry * env * proud * math.cos(a), z))
            rows.append(row)
    g.grid(rows, close_u=True, cap_start=True, cap_end=True, m=m)


def add_shell_dome(g, m, rx, ry, h, bands=5, tilt=0.0, lean=0.0, key="shell_mound", step=0.04, segs=40):
    """Tall beehive shell mound: a rounded dome built of stacked bands, each overhanging the one below.

    Seen from the low camera the band edges are the upward-bowed lines drawn on the big mounds right of the
    fountain (A: main reference). tilt leans the bands over to one side (towards local +X), lean shifts the top.
    """
    g.use(key)
    per = 5
    rows = []
    for b in range(bands):
        for j in range(per + 1):
            w = (b + j / per) / bands
            proud = 1.0 + step * (1.0 - j / per) ** 1.4 * (1.0 if b > 0 else 0.4)
            row = []
            for i in range(segs):
                th = TAU * i / segs
                t = min(0.999, max(0.0, w + tilt * math.cos(th) * math.sin(math.pi * w)))
                f = (1.0 - t ** 2.6) ** (1 / 2.0) * proud
                row.append((rx * f * math.cos(th) + lean * h * t * t, ry * f * math.sin(th), h * t))
            rows.append(row)
    g.grid(rows, close_u=True, cap_start=True, cap_end=True, m=m)


def add_stone_course(g, x0, x1, y0, y1, z0, z1, block=0.95, seed=0, e=0.42, key="stone"):
    """Courses of rounded blocks filling a box (piers, quay faces). Blocks span the full depth."""
    g.use(key)
    rand = rng(seed + 101)
    course_h = 0.52
    n_course = max(1, round((z1 - z0) / course_h))
    ch = (z1 - z0) / n_course
    for c in range(n_course):
        zc = z0 + ch * (c + 0.5)
        n = max(1, round((x1 - x0) / block))
        cuts = [x0] + sorted(x0 + (x1 - x0) * (i + rand(-0.22, 0.22)) / n for i in range(1, n)) + [x1]
        if c % 2 == 1 and n > 1:
            cuts = [x0] + [min(x1 - 0.2, v + (x1 - x0) / n * 0.35) for v in cuts[1:-1]] + [x1]
        for a, b in zip(cuts, cuts[1:]):
            dy = rand(-0.05, 0.05)
            g.ellipsoid(((a + b) / 2, (y0 + y1) / 2, zc), ((b - a) / 2 * 1.02, (y1 - y0) / 2 + dy + 0.03, ch / 2 * 1.04), segs=10, steps=6, e=e)


def add_cobbles(g, x0, x1, y0, y1, z_top, exclude=(), size=(0.66, 0.52), seed=3, key="cobble", height=0.2):
    """Cobble paving as real stones. exclude: (xa, xb, ya, yb) rectangles left free."""
    g.use(key)
    rand = rng(seed)
    sx, sy = size
    rows = int((y1 - y0) / sy)
    count = 0
    for r in range(rows):
        y = y0 + sy * (r + 0.5)
        offset = (0.5 * sx) if r % 2 else 0.0
        x = x0 + offset * rand(0.6, 1.2)
        while x < x1 - 0.15:
            w = sx * rand(0.72, 1.3)
            cx, cy = x + w / 2, y + rand(-0.05, 0.05)
            x += w
            if cx > x1:
                break
            if any(xa <= cx <= xb and ya <= cy <= yb for xa, xb, ya, yb in exclude):
                continue
            hz = height * rand(0.8, 1.15)
            g.ellipsoid((cx, cy, z_top - hz * 0.5 + rand(-0.012, 0.012)), (w * 0.49, sy * rand(0.46, 0.5), hz * 0.5), segs=8, steps=4,
                        e=0.62, m=None)
            count += 1
    return count


def build_ring_post(coll, mats, name="COT_RingPost", height=1.0, props=None):
    """Thin post with a loop head standing on the plaza (short) or in the water (tall)."""
    g = Geo().use("iron")
    g.revolve([(0.11, 0.0), (0.09, 0.05), (0.055, 0.16), (0.045, height - 0.3), (0.06, height - 0.26)], segs=8)
    g.ring_arc((0, 0, height - 0.11), 0.15, 0, TAU, 0.05, n=18, plane="XZ")
    return [g.to_object(name, coll, mats, props)]


def build_drain_ring(coll, mats, name="COT_DrainRing", props=None):
    """Ring-shaped spout on the quay face with a thin stream of water (A: main reference bottom edge)."""
    g = Geo().use("iron")
    g.ring_arc((0, 0, 0), 0.3, 0, TAU, 0.085, n=24, plane="XZ", segs=8)
    g.use("stone_dark")
    g.revolve([(0.22, 0.0), (0.22, 0.25)], segs=16, m=place(0, 0.02, 0, rx=-math.pi / 2))
    return [g.to_object(name, coll, mats, props)]


def add_corbel_wing(g, m, length=1.5, blades=5, key="stone_dark", spread=1.0):
    """Feathered bracket: a fan of overlapping blades sweeping out and down (under ledges and canopy tips)."""
    g.use(key)
    for k in range(blades):
        f = k / max(1, blades - 1)
        ang = lerp(-0.15, -1.25 * spread, f)
        ln = length * lerp(1.0, 0.6, f)

        def centre(u, ang=ang, ln=ln):
            return (ln * u * math.cos(ang), ln * u * math.sin(ang) + 0.12 * math.sin(math.pi * u))

        g.lens(centre, lambda u: 0.26 * math.sin(math.pi * u ** 0.6) ** 0.7, lambda u: 0.14 * (1 - u) + 0.03, nu=8, nv=8,
               m=m @ place(y=0.0, x=0.0, z=-0.12 * k), cup=0.1)


# ============================================================================ louvre canopy roof
def build_louvre_roof(coll, mats, name, x0, x1, zb, zt, y0, y1, bays=3, curve_end="W", props=None, spikes=True, scallop=True):
    """Louvred roof with a quarter-round end, spike rows and scalloped trim (Lower_City_statue_upper_right.jpg).

    The viewer-facing gable (y0) and the far gable (y1) are louvred planes; the rounded end wraps down to the eave.
    """
    sign = 1 if curve_end == "W" else -1
    xe = x0 if curve_end == "W" else x1          # eave end
    xf = x1 if curve_end == "W" else x0          # flat end
    R = zt - zb
    cx = xe + sign * R

    def arc_point(a, rad=R):
        return (cx - sign * rad * math.cos(a), zb + rad * math.sin(a))

    g = Geo().use("louvre_core")
    profile = [arc_point(math.pi / 2 * i / 12, R - 0.12) for i in range(13)] + [(xf, zt - 0.12), (xf, zb)]
    profile = [(x, z) for x, z in profile]
    g.prism(profile if sign > 0 else list(reversed(profile)), y0 + 0.1, y1 - 0.1)
    g.use("louvre")
    n_sl = max(6, int(R / 0.17))
    for k in range(n_sl):
        z = zb + (k + 0.5) * R / n_sl
        xa = cx - sign * math.sqrt(max(0.0, R * R - (z - zb) ** 2)) + sign * 0.05
        for yy in (y0, y1):
            g.box(min(xa, xf), max(xa, xf), yy - 0.06, yy + 0.06, z - 0.055, z + 0.055)
    n_q = max(8, int(R * math.pi / 2 / 0.19))
    for k in range(n_q):
        a = (k + 0.5) / n_q * math.pi / 2
        px, pz = arc_point(a)
        g.box(-0.05, 0.05, y0, y1, -0.075, 0.075, m=place(px, 0, pz, ry=sign * (a - math.pi / 2)) if sign > 0 else place(px, 0, pz, ry=-(a - math.pi / 2)))
    g.use("louvre_frame")
    span = abs(xf - cx)
    post_x = [cx + sign * span * i / bays for i in range(bays + 1)]
    for yy in (y0 - 0.09, y1 + 0.09):
        for px in post_x:
            g.box(px - 0.09, px + 0.09, yy - 0.07, yy + 0.07, zb, zt + 0.12)
        g.box(min(cx, xf), max(cx, xf), yy - 0.08, yy + 0.08, zt, zt + 0.14)
        g.tube([(arc_point(math.pi / 2 * i / 14)[0], yy, arc_point(math.pi / 2 * i / 14)[1]) for i in range(15)], 0.1, 0.1, segs=6, ref=(0, 1, 0))
        inner = [(cx - sign * R * math.cos(math.pi / 2 * i / 14) * (1 - 0.42 * i / 14), yy, zb + R * math.sin(math.pi / 2 * i / 14)) for i in range(15)]
        g.tube(inner, 0.085, 0.085, segs=6, ref=(0, 1, 0))
    g.use("stone_dark")
    g.box(min(xe - sign * 0.3, xf), max(xe - sign * 0.3, xf), y0 - 0.32, y1 + 0.32, zb - 0.26, zb)
    g.tube([(xe - sign * 0.32, y0 - 0.34, zb - 0.02), (xf, y0 - 0.34, zb - 0.02)], 0.09, segs=6)
    g.tube([(xe - sign * 0.32, y1 + 0.34, zb - 0.02), (xf, y1 + 0.34, zb - 0.02)], 0.09, segs=6)
    if spikes:
        g.use("iron")
        for yy in (y0 - 0.09, y1 + 0.09):
            for i, px in enumerate(post_x):
                g.spike((px, yy, zt + 0.12), (px, yy, zt + 1.35), 0.11, bulb=1.2)
            n = int(span / 0.5)
            for i in range(1, n):
                px = cx + sign * span * i / n
                if min(abs(px - q) for q in post_x) > 0.2:
                    g.spike((px, yy, zt + 0.12), (px, yy, zt + 0.62), 0.05, segs=5, bulb=0.6)
            for i in range(1, 8):
                a = math.pi / 2 * i / 8
                px, pz = arc_point(a)
                ox, oz = arc_point(a, R + (0.52 if i % 4 else 0.85))
                g.spike((px, yy, pz), (ox, yy, oz), 0.05 if i % 4 else 0.075, segs=5, bulb=0.6)
    if scallop:
        g.use("iron")
        step = 0.92
        n = max(2, int(abs(xf - xe) / step))
        for yy in (y0 - 0.34, y1 + 0.34):
            for i in range(n):
                xa = xe + sign * abs(xf - xe) * i / n
                xb = xe + sign * abs(xf - xe) * (i + 1) / n
                mid, rad = (xa + xb) / 2, abs(xb - xa) / 2
                g.tube([(mid + rad * math.cos(math.pi + math.pi * j / 10), yy, zb + 0.02 + 0.3 * math.sin(math.pi * j / 10) - 0.3) for j in range(11)],
                       0.045, segs=5, ref=(0, 1, 0))
                g.ring_arc((xa, yy, zb + 0.16), 0.13, 0, TAU, 0.04, n=12, plane="XZ", segs=5)
                g.spike((xa, yy, zb + 0.28), (xa, yy, zb + 0.5), 0.04, segs=4)
    return [g.to_object(name, coll, mats, props, smooth_angle=35)]


# ============================================================================ viaduct behind the plaza
def build_viaduct(coll, mats, name, x0, x1, y0, y1, z_ground, z_deck, centres, arch_w=2.4, spring=7.8, props=None):
    g = Geo().use("stone_far")
    deck_t = 0.62
    hw = arch_w / 2
    edges = [x0] + [(a + b) / 2 for a, b in zip(centres, centres[1:])] + [x1]
    for (xa, xb), c in zip(zip(edges, edges[1:]), centres):
        pts = [(xa, z_ground), (xa, z_deck - deck_t), (xb, z_deck - deck_t), (xb, z_ground), (c + hw, z_ground), (c + hw, spring)]
        pts += [(c + hw * math.cos(math.pi * k / 12), spring + hw * math.sin(math.pi * k / 12)) for k in range(1, 12)]
        pts += [(c - hw, spring), (c - hw, z_ground)]
        g.prism(pts, y0, y1)
    g.box(x0, x1, y0 - 0.4, y1 + 0.4, z_deck - deck_t, z_deck)
    g.use("stone_far_trim")
    for yy in (y0 - 0.42, y1 + 0.42):
        g.tube([(x0, yy, z_deck - deck_t + 0.05), (x1, yy, z_deck - deck_t + 0.05)], 0.12, segs=6)
        g.tube([(x0, yy, z_deck - 0.06), (x1, yy, z_deck - 0.06)], 0.1, segs=6)
    for c in centres:
        for yy in (y0 - 0.04, y1 + 0.04):
            path = [(c + (hw + 0.14) * math.cos(math.pi * k / 14), yy, spring + (hw + 0.14) * math.sin(math.pi * k / 14)) for k in range(15)]
            g.tube([(c + hw + 0.14, yy, z_ground)] + path + [(c - hw - 0.14, yy, z_ground)], 0.13, segs=6, ref=(0, 1, 0))
    # Rough masonry dressing (A: main reference, the wall behind the fountain): every arch is ringed by rubble
    # voussoirs and jamb stones, a pier of stacked blocks stands between the arches, and a wreath of stones sits
    # above each pier. The north face repeats the south face (C).
    rand = rng(613)
    ring_r = hw + 0.36
    wreath_z = spring + hw * 0.55
    for yy, sgn in ((y0 - 0.05, -1), (y1 + 0.05, 1)):
        g.use("stone_far_trim")
        for c in centres:
            count = 13
            for k in range(count):
                a = math.pi * (k + 0.5) / count
                g.ellipsoid((0, 0, 0), (0.3 * rand(0.85, 1.2), 0.17, math.pi * ring_r / count * 0.5 * rand(0.86, 1.0)), segs=8, steps=6, e=0.55,
                            m=place(c + ring_r * math.cos(a), yy, spring + ring_r * math.sin(a), ry=-a))
            for side in (-1, 1):
                z = z_ground + 0.3
                while z < spring - 0.1:
                    bh = rand(0.42, 0.62)
                    g.ellipsoid((c + side * (ring_r + rand(-0.04, 0.04)), yy, z + bh / 2), (0.3 * rand(0.85, 1.15), 0.17, bh * 0.5), segs=8, steps=6, e=0.55)
                    z += bh * 0.96
        for xa in edges[1:-1]:
            add_stone_course(g, xa - 0.44, xa + 0.44, yy - 0.16, yy + 0.16, z_ground, wreath_z - 1.0, block=0.5, seed=int(xa * 10) + (7 if sgn > 0 else 0),
                             key="stone_far_trim")
            g.use("stone_far_trim")
            for k in range(11):                                  # wreath: radial stones round a dark boss
                a = TAU * k / 11
                g.ellipsoid((0, 0, 0), (0.25, 0.13, 0.16), segs=8, steps=5, e=0.7,
                            m=place(xa + 0.5 * math.cos(a), yy, wreath_z + 0.5 * math.sin(a), ry=-a))
            for k in range(7):
                a = TAU * (k + 0.5) / 7
                g.ellipsoid((0, 0, 0), (0.15, 0.14, 0.11), segs=8, steps=5, e=0.7,
                            m=place(xa + 0.2 * math.cos(a), yy, wreath_z + 0.2 * math.sin(a), ry=-a))
            g.ring_arc((xa, yy, wreath_z), 0.84, 0, TAU, 0.075, n=24, plane="XZ", segs=6)
            g.ring_arc((xa, yy, z_ground + 2.2), 0.3, 0, TAU, 0.085, n=16, plane="XZ", segs=6)
        # corbel course under the deck
        n_cb = int((x1 - x0) / 0.62)
        for k in range(n_cb):
            xc = x0 + (x1 - x0) * (k + 0.5) / n_cb
            g.ellipsoid((xc, yy + sgn * 0.3, z_deck - deck_t - 0.14), (0.2, 0.16, 0.15), segs=8, steps=5, e=0.5)
    g.use("curtain")                                             # ragged drapes filling the heads of the arches
    for i, c in enumerate(centres):
        rand = rng(40 + i)
        rows = []
        n = 22
        for k in range(n + 1):
            x = c - hw * 0.98 + 2 * hw * 0.98 * k / n
            zt = spring + math.sqrt(max(0.0, hw * hw - (x - c) ** 2)) + 0.03
            zb = spring + hw * 0.25 - 1.5 * rand() ** 1.6 - 0.5 * abs(x - c) / hw
            ym = (y0 + y1) / 2
            rows.append([(x, ym - 0.08, zt), (x, ym + 0.08, zt), (x, ym + 0.03, zb), (x, ym - 0.03, zb)])
        g.grid(rows, close_u=True, cap_start=True, cap_end=True)
    return [g.to_object(name, coll, mats, props, smooth_angle=35)]


# ============================================================================ fountain screen
def build_fountain_screen(coll, mats, name="COT_FountainScreen", props=None):
    """Crowned iron screen with a tall leaf pane that stands behind the fountain.

    Front silhouette from Lower_City_statue.jpg, Lower_City_statue_upper_right.jpg and 12_Materials/Materials_02.jpg.
    Local frame: origin on the ground, faces -Y. Height about 10.3.
    """
    ic = IronCurves()
    z_rail = 4.0
    for i in range(-8, 9):
        x = i * 0.24
        ic.add([(x, 0, 0), (x, 0, z_rail)], r=0.75, smooth=False)
    for z in (0.12, 2.0, z_rail):
        ic.add([(-1.98, z), (1.98, z)], r=1.4, smooth=False)
    for sx in (-1, 1):
        ic.add([(sx * 1.98, 0, 0), (sx * 1.98, 0, z_rail + 0.2)], r=1.8, smooth=False)
        ic.spike(sx * 1.98, z_rail + 0.2, z_rail + 1.1, r=1.7)
        # sweeping wing bands
        ic.add(bez((sx * 0.35, 8.75), (sx * 1.2, 8.3), (sx * 1.9, 7.2), (sx * 2.2, 6.0), 14), r=1.5)
        ic.add(bez((sx * 0.5, 8.2), (sx * 1.15, 7.8), (sx * 1.7, 6.9), (sx * 1.95, 5.75), 14), r=1.1)
        ic.add(bez((sx * 0.75, 7.55), (sx * 1.2, 7.2), (sx * 1.55, 6.5), (sx * 1.72, 5.5), 12), r=0.9)
        ic.add(bez((sx * 2.2, 6.0), (sx * 2.3, 5.3), (sx * 2.1, 4.6), (sx * 1.98, z_rail), 8), r=1.3)
        ic.add(bez((sx * 1.72, 5.5), (sx * 1.7, 5.0), (sx * 1.5, 4.4), (sx * 1.2, z_rail), 8), r=0.9)
        # graduated spears standing on the upper band
        for k, (x, zb, zt) in enumerate(((0.78, 8.45, 9.55), (1.14, 8.1, 9.05), (1.48, 7.6, 8.5), (1.8, 7.0, 7.9), (2.08, 6.35, 7.3))):
            ic.add([(sx * x, 0, zb - 0.9), (sx * x, 0, zb)], r=0.8, smooth=False)
            ic.spike(sx * x, zb, zt, r=1.5)
        ic.add(spiral_pts(sx * 1.0, 6.95, 0.5, 1.7, math.pi / 2, ccw=sx > 0), r=1.1, taper="end")
        ic.add(spiral_pts(sx * 1.42, 5.95, 0.42, 1.6, math.pi / 2, ccw=sx < 0), r=1.0, taper="end")
        ic.add(spiral_pts(sx * 0.74, 5.2, 0.4, 1.6, -math.pi / 2, ccw=sx > 0), r=0.95, taper="end")
        ic.add(bez((sx * 0.95, 4.05), (sx * 1.0, 4.7), (sx * 0.7, 4.95), (sx * 0.72, 5.55), 8), r=0.8)
        # tall ribbed horn spikes at the crown
        horn = catmull([(sx * 0.3, 8.7), (sx * 0.42, 9.3), (sx * 0.4, 9.85), (sx * 0.27, 10.3)], per=5)
        n = len(horn)
        ic.add(horn, r=resample([3.6, 3.2, 2.0, 0.1], n))
        for j in range(5):
            f = 0.15 + 0.16 * j
            hx, hz = horn[int(f * (n - 1))]
            ic.add([(hx - sx * 0.1, hz - 0.03), (hx + sx * 0.1, hz + 0.05)], r=0.6, smooth=False)
    # scrollwork laid over the pane (A: 12_Materials/Materials_02.jpg, Lower_City_statue_upper_right.jpg)
    for cx_, cz_, r_, a0_, ccw_ in ((0.22, 6.75, 0.6, math.pi / 2, True), (-0.3, 5.55, 0.46, -math.pi / 2, False),
                                   (-0.12, 7.85, 0.4, math.pi, True), (0.34, 4.75, 0.34, 0.0, False)):
        ic.add([(px, -0.26, pz) for px, pz in spiral_pts(cx_, cz_, r_, 1.9, a0_, ccw=ccw_)], r=0.95, taper="end")
    ic.add([(px, -0.26, pz) for px, pz in bez((-0.75, 4.3), (-0.2, 5.0), (0.75, 5.6), (0.6, 6.4), 12)], r=0.8)
    ic.add([(px, -0.26, pz) for px, pz in bez((0.7, 7.3), (0.3, 8.0), (-0.5, 8.2), (-0.3, 8.75), 12)], r=0.8)
    # the screen is a double grille 0.36 deep with ties between the layers, so it has a body when seen from the side
    back = ic.transformed(place(0, 0.36, 0))
    ic.extend(back)
    for sx in (-1, 1):
        for z in (0.12, 2.0, z_rail, 5.6, 7.2):
            xx = sx * (1.98 if z <= z_rail else (2.2 if z < 6.5 else 1.75))
            ic.add([(xx, 0.0, z), (xx, 0.36, z)], r=1.2, smooth=False)
    for z in (0.12, z_rail):
        ic.add([(0.0, 0.0, z), (0.0, 0.36, z)], r=1.2, smooth=False)
    iron = ic.to_object(name + "_Iron", coll, mats("iron"), bevel=0.03, props=props)
    gf, gg = Geo(), Geo()
    add_leaf_window(gf, gg, place(0, 0.18, 6.55), 1.9, 4.9, index=3, bulge=0.12, ribs=4, frame=0.07, glass_key="glass_screen")
    frame = gf.to_object(name + "_PaneFrame", coll, mats, props)
    pane = gg.to_object(name + "_Pane", coll, mats, props)
    return [iron, frame, pane]


# ============================================================================ glass pillar under the terrace
def build_glass_pillar(coll, mats, name, radius, z0, z1, props=None):
    g = Geo().use("glass_pillar")
    rows, uvs = [], []
    for k in range(9):
        t = k / 8
        rows.append([(radius * math.cos(TAU * i / 28), radius * math.sin(TAU * i / 28), lerp(z0, z1, t)) for i in range(28)])
        uvs.append([(i / 28, t) for i in range(28)])
    g.grid(rows, close_u=True, cap_start=True, cap_end=True, uvs=uvs)
    g.use("stone_dark")
    for z, s in ((z0, 1), (z1, -1)):
        g.revolve([(radius * 1.18, z - 0.14 * s), (radius * 1.22, z), (radius * 1.08, z + 0.2 * s), (radius * 1.02, z + 0.26 * s)] if s > 0 else
                  [(radius * 1.02, z - 0.26), (radius * 1.08, z - 0.2), (radius * 1.22, z), (radius * 1.18, z + 0.14)], segs=28)
    g.use("window_frame")
    h = z1 - z0
    for k in range(3):
        zc = z0 + h * (0.26 + 0.25 * k)
        path = [(radius * 1.03 * math.cos(TAU * i / 32), radius * 1.03 * math.sin(TAU * i / 32), zc + 0.2 * h * math.sin(TAU * i / 32 + 0.5)) for i in range(33)]
        g.tube(path, 0.07, segs=6, ref=(0, 0, 1), cap=False)
    for i in range(4):
        a = TAU * (i + 0.5) / 4
        g.tube([(radius * 1.03 * math.cos(a), radius * 1.03 * math.sin(a), z0), (radius * 1.03 * math.cos(a), radius * 1.03 * math.sin(a), z1)], 0.05, segs=5)
    return [g.to_object(name, coll, mats, props)]


def add_curtain(g, xa, xb, y, z_top, drop, seed=0, key="curtain", n=26, axis="X"):
    """Hanging ragged fringe strip with thickness (under eaves and ledges)."""
    g.use(key)
    rand = rng(seed + 5)
    rows = []
    for i in range(n + 1):
        t = i / n
        p = lerp(xa, xb, t)
        zb = z_top - drop * (0.35 + 0.65 * rand() ** 1.5) * (0.5 + 0.5 * math.sin(math.pi * min(1.0, t * 1.4 + 0.15)))
        if axis == "X":
            rows.append([(p, y - 0.07, z_top), (p, y + 0.07, z_top), (p, y + 0.03, zb), (p, y - 0.03, zb)])
        else:
            rows.append([(y - 0.07, p, z_top), (y + 0.07, p, z_top), (y + 0.03, p, zb), (y - 0.03, p, zb)])
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)


def build_spear_post(coll, mats, name="COT_SpearPost", height=2.6, props=None):
    """Staff with a leafy bulb and spike (terrace tip; 13_Lighting/Lighting_01 left of the fence)."""
    ic = IronCurves()
    ic.add([(0, 0, 0), (0, 0, 0.06), (0, 0, 0.2), (0, 0, height - 0.75)], r=[3.4, 2.8, 1.2, 1.0], smooth=False)
    ic.spike(0, height - 0.32, height, r=1.4, bulb=False)
    iron = ic.to_object(name + "_Iron", coll, mats("iron"), bevel=0.024, props=props)
    g = Geo().use("iron")
    zc = height - 0.55
    g.ellipsoid((0, 0, zc), (0.11, 0.11, 0.24), segs=10, steps=8)
    for k in range(6):
        a = TAU * k / 6

        def centre(u):
            return (0.06 + 0.2 * u, zc - 0.18 + 0.36 * u ** 0.8)

        g.lens(centre, lambda u: 0.07 * math.sin(math.pi * u ** 0.6), lambda u: 0.03, nu=6, nv=6, m=place(rz=a), cup=0.2)
    return [iron, g.to_object(name + "_Bulb", coll, mats, props)]


def _mound_test(coll, mats):
    g = Geo()
    add_shell_mound(g, place(-3.2, 0, 0, rz=0.1), 2.6, 1.5, 2.5, 4, slant=0.3)
    add_shell_dome(g, place(2.6, 0, 0), 1.7, 1.6, 5.4, bands=5, tilt=0.1)
    add_shell_dome(g, place(6.4, 0, 0), 1.9, 1.6, 3.9, bands=4)
    return [g.to_object("mound", coll, mats)]


def _viaduct_test(coll, mats):
    return build_viaduct(coll, mats, "via", -7.0, 7.0, 0.0, 3.5, 0.0, 9.1, [-4.57, 0.0, 4.57], arch_w=2.4, spring=7.1)


TEST_BUILDERS = {
    "statue": lambda coll, mats: build_statue(coll, mats, P("FountainStatue")),
    "lamp": lambda coll, mats: build_lamp(coll, mats),
    "screen": lambda coll, mats: build_fountain_screen(coll, mats),
    "signs": lambda coll, mats: place_all(build_sign_oval(coll, mats), [place(-1.2, 0, 0)], coll, "s") + place_all(build_sign_spear(coll, mats), [place(1.2, 0, 0)], coll, "s"),
    "fence": lambda coll, mats: [fence_web_curves(1.675).transformed(place(-2.3, 0, 0)).to_object("fence", coll, mats("iron"), bevel=0.018),
                                 railing_bay_curves(final_post=False).transformed(place(0.2, 0, 0)).to_object("rail_a", coll, mats("iron"), bevel=0.02),
                                 railing_bay_curves(final_post=True).transformed(place(1.25, 0, 0)).to_object("rail_b", coll, mats("iron"), bevel=0.02)],
    "pillar_mound": lambda coll, mats: build_glass_pillar(coll, mats, "pillar", 0.78, 0.4, 3.8),
    "mounds": _mound_test,
    "viaduct": _viaduct_test,
    "scaffold": lambda coll, mats: build_scaffold(coll, mats, "sc", [(-4, 0, 0, 14), (-2, 0, 0, 14), (2, 0, 0, 14), (2, 4.6, 0, 14)],
                                                  [(-2, 0, 2, 0, [3.0, 8.8], None, None, None), (2, 0, 2, 4.6, [5.9, 11.6], None, None, None),
                                                   (-4, 0, -2, 0, [6.0], "L", 0.87, 0.5)]),
    "roof": lambda coll, mats: build_louvre_roof(coll, mats, "roof", -4.5, 4.5, 0.5, 3.7, -2, 2),
    "tower": lambda coll, mats: build_tower(coll, mats, "tw", 0, 0, 0, 30, 5, 8.5, [(-0.5, 8, 3, 7.4), (0.4, 16, 3, 7.4), (-0.2, 24, 3, 7.4), (2.4, 12, 3, 7.4)]),
}
