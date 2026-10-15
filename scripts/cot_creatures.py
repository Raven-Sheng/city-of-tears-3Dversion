"""Static creature figures of the City of Tears (user decision D-347): set dressing only, no rig, no animation, no combat.

Each builder returns a Geo in local space: standing on z = 0 (or hovering, for flying kinds the body is lifted),
facing -Y (toward the viewer side of the city). One unit is the project yardstick H.

Evidence (see docs/decisions.md D-349):
  husk_sentry, heavy_sentry   A  11_Lower_City/Lower_City_middle.jpg (grey banded bodies, round horned heads, orange eyes, nails)
  resident                    A  08_Tower/Tower_step1.jpg, Tower_step3.jpg (pink banded bodies, pale spiral cone hats, dark masks)
  lance_sentry, winged_sentry A  08_Tower/Tower_step3.jpg (red cloaked lancer; dark winged figure with orange eyes)
  soul_twister                A  master B3 enlarged (pale dome with a row of glowing dots, hanging grey tendrils)
  soul_warrior                A  master B3 enlarged (round pale banded body, two yellow eyes and a small white one, nail)
  mistake                     C  small soul blob of the sanctum (game knowledge; not visible in the local references)
Shapes are simplified readings of those drawings; proportions are completion (C).
"""
import math

from cot_geo import Geo, TAU, lerp, place


def _band(g, rx, ry, z, r=0.028, n=24, y_off=0.0):
    """Closed band hugging an elliptic cross-section of radius rx, ry at height z."""
    pts = [(rx * math.cos(TAU * i / n), y_off + ry * math.sin(TAU * i / n), z) for i in range(n + 1)]
    g.tube(pts, r, segs=5, ref=(0, 0, 1))


def _ell_half(r, z, cz, rz):
    """Half-width of an ellipsoid of radius r (vertical radius rz, centre cz) at height z."""
    t = (z - cz) / rz
    return r * math.sqrt(max(0.0, 1.0 - t * t))


def _nail(g, hand, tip, key="iron"):
    """Nail (sword): tapered blade with a crossguard and a short grip."""
    from mathutils import Vector
    h, t = Vector(hand), Vector(tip)
    d = (t - h).normalized()
    g.use(key)
    g.tube([h - d * 0.18, h + d * 0.02], 0.035, segs=5)
    g.tube([h + d * 0.05, t], [0.045, 0.008], segs=4)
    side = d.cross(Vector((0, 1, 0)))
    if side.length < 1e-3:
        side = Vector((1, 0, 0))
    side.normalize()
    g.tube([h + d * 0.05 - side * 0.16, h + d * 0.05 + side * 0.16], 0.03, segs=4)


def k_husk_sentry(v=0):
    """Husk Sentry: banded grey round body, round head with two horns, big orange eyes, nail held ready."""
    g = Geo()
    bz, brx, bry, brz = 0.78, 0.48, 0.4, 0.5
    g.use("creature_shell")
    g.ellipsoid((0, 0, bz), (brx, bry, brz), segs=18, steps=10)
    g.use("creature_dark")
    for z in (bz - 0.28, bz - 0.05, bz + 0.2):
        _band(g, _ell_half(brx, z, bz, brz) + 0.012, _ell_half(bry, z, bz, brz) + 0.012, z)
    for sx in (-1, 1):                                    # short legs and feet
        g.tube([(sx * 0.18, 0.0, bz - 0.4), (sx * 0.2, -0.04, 0.08)], 0.07, segs=6)
        g.ellipsoid((sx * 0.21, -0.1, 0.06), (0.11, 0.16, 0.06), segs=8, steps=4)
    hz = bz + brz + 0.22                                  # head
    g.use("creature_shell")
    g.ellipsoid((0, -0.02, hz), (0.38, 0.34, 0.32), segs=16, steps=8)
    for sx in (-1, 1):
        g.spike((sx * 0.2, 0.0, hz + 0.18), (sx * 0.36, 0.02, hz + 0.6), 0.1, segs=6)
    g.use("creature_dark")
    g.ellipsoid((0, -0.22, hz - 0.04), (0.29, 0.14, 0.2), segs=12, steps=6)
    g.use("creature_eye")
    for sx in (-1, 1):
        g.ellipsoid((sx * 0.12, -0.33, hz - 0.02), (0.085, 0.04, 0.095), segs=10, steps=6)
    g.use("creature_dark")                                # arms
    arm = (0.62, -0.28, bz + 0.05) if v % 2 == 0 else (0.58, -0.3, bz - 0.12)
    g.tube([(0.42, 0.0, bz + 0.12), arm], 0.06, segs=5)
    g.tube([(-0.42, 0.0, bz + 0.12), (-0.55, -0.15, bz - 0.15)], 0.06, segs=5)
    tip = (1.05, -0.5, bz + 0.9) if v % 2 == 0 else (1.35, -0.55, bz - 0.25)
    _nail(g, arm, tip)
    return g


def k_heavy_sentry():
    """Heavy Sentry: the sentry build half again as large, broader, with a round shield and a club."""
    g = Geo()
    bz, brx, bry, brz = 1.1, 0.78, 0.62, 0.72
    g.use("creature_shell")
    g.ellipsoid((0, 0, bz), (brx, bry, brz), segs=20, steps=10)
    g.use("creature_dark")
    for z in (bz - 0.42, bz - 0.12, bz + 0.18, bz + 0.42):
        _band(g, _ell_half(brx, z, bz, brz) + 0.015, _ell_half(bry, z, bz, brz) + 0.015, z, r=0.04)
    for sx in (-1, 1):
        g.tube([(sx * 0.28, 0.0, bz - 0.55), (sx * 0.3, -0.05, 0.1)], 0.11, segs=6)
        g.ellipsoid((sx * 0.31, -0.14, 0.08), (0.16, 0.22, 0.08), segs=8, steps=4)
    hz = bz + brz + 0.25
    g.use("creature_shell")
    g.ellipsoid((0, -0.04, hz), (0.46, 0.4, 0.36), segs=16, steps=8)
    for sx in (-1, 1):
        g.spike((sx * 0.25, 0.0, hz + 0.2), (sx * 0.5, 0.03, hz + 0.62), 0.12, segs=6)
    g.use("creature_dark")
    g.ellipsoid((0, -0.26, hz - 0.05), (0.34, 0.15, 0.22), segs=12, steps=6)
    g.use("creature_eye")
    for sx in (-1, 1):
        g.ellipsoid((sx * 0.14, -0.39, hz - 0.03), (0.1, 0.045, 0.1), segs=10, steps=6)
    g.use("creature_dark")
    g.tube([(-0.7, 0.0, bz + 0.15), (-0.85, -0.45, bz - 0.1)], 0.09, segs=5)
    g.use("creature_shell")                               # round shield on the left arm
    g.revolve([(0.0, -0.06), (0.55, 0.0), (0.5, 0.06), (0.0, 0.1)], segs=20, m=place(-0.9, -0.62, bz - 0.05, rx=math.pi / 2))
    g.use("creature_dark")
    g.tube([(0.7, 0.0, bz + 0.15), (0.95, -0.3, bz - 0.05)], 0.09, segs=5)
    g.use("iron")                                         # club
    g.tube([(0.95, -0.3, bz - 0.25), (1.1, -0.45, bz + 1.05)], [0.06, 0.06, 0.16], segs=6)
    return g


def k_lance_sentry():
    """Lance Sentry: tall lancer in a dark red cloak with a pale masked head and a long lance."""
    g = Geo()
    g.use("creature_cloak")
    g.fluted(0.0, 1.35, lambda t: lerp(0.5, 0.2, t ** 0.8), folds=7, depth_fn=lambda t: 0.16, nz=8, per_fold=5)
    g.use("creature_shell")
    g.ellipsoid((0, 0, 1.45), (0.27, 0.24, 0.26), segs=14, steps=8)
    g.use("creature_cloak")                               # hood rim and two ear points
    for sx in (-1, 1):
        g.spike((sx * 0.14, 0.0, 1.62), (sx * 0.3, 0.05, 1.98), 0.07, segs=5)
    g.use("creature_dark")
    g.ellipsoid((0, -0.16, 1.42), (0.2, 0.1, 0.15), segs=10, steps=6)
    g.use("creature_eye")
    for sx in (-1, 1):
        g.ellipsoid((sx * 0.08, -0.24, 1.44), (0.06, 0.03, 0.07), segs=8, steps=5)
    g.use("iron")
    g.tube([(0.45, -0.25, 0.1), (0.62, -0.32, 2.7)], 0.03, segs=5)
    g.spike((0.62, -0.32, 2.65), (0.66, -0.34, 3.15), 0.07, segs=5)
    g.use("creature_dark")
    g.tube([(0.2, -0.05, 1.1), (0.52, -0.28, 1.15)], 0.05, segs=5)
    return g


def k_winged_sentry():
    """Winged Sentry: a sentry body with two pairs of veined wings, hovering with its lance couched. Base at the feet."""
    g = Geo()
    lift = 0.6
    bz = 0.62 + lift
    g.use("creature_dark")
    g.ellipsoid((0, 0, bz), (0.36, 0.3, 0.42), segs=14, steps=8)
    g.use("creature_shell")
    _band(g, 0.37, 0.31, bz + 0.05, r=0.03)
    g.ellipsoid((0, -0.02, bz + 0.6), (0.3, 0.27, 0.27), segs=14, steps=8)
    for sx in (-1, 1):
        g.spike((sx * 0.16, 0.0, bz + 0.78), (sx * 0.3, 0.0, bz + 1.1), 0.07, segs=5)
    g.use("creature_dark")
    g.ellipsoid((0, -0.18, bz + 0.56), (0.22, 0.11, 0.16), segs=10, steps=6)
    g.use("creature_eye")
    for sx in (-1, 1):
        g.ellipsoid((sx * 0.09, -0.27, bz + 0.58), (0.07, 0.03, 0.08), segs=8, steps=5)
    g.use("creature_wing")
    for sx in (-1, 1):
        for k, (ang, ln) in enumerate(((35.0, 1.1), (10.0, 0.85))):
            a = math.radians(ang)

            def centre(u, a=a, ln=ln):
                return (u * ln * math.cos(a), u * ln * math.sin(a) + 0.12 * math.sin(math.pi * u))

            g.lens(centre, lambda u: 0.22 * math.sin(math.pi * u ** 0.6), lambda u: 0.02, nu=8, nv=6,
                   m=place(sx * 0.18, 0.22, bz + 0.25, rz=(0.0 if sx > 0 else math.pi)))
    for sx in (-1, 1):
        g.use("creature_dark")
        g.tube([(sx * 0.1, 0.0, bz - 0.38), (sx * 0.12, 0.05, lift)], 0.05, segs=5)
    g.use("iron")
    g.tube([(-0.6, -0.3, bz - 0.2), (1.4, -0.45, bz + 0.15)], 0.03, segs=5)
    g.spike((1.38, -0.45, bz + 0.15), (1.8, -0.48, bz + 0.22), 0.06, segs=5)
    return g


def k_resident(v=0, seated=False):
    """City resident: pink banded round body, dark mask face with pale eyes, pale cone hat wound with a spiral."""
    g = Geo()
    s = (1.0, 0.9, 1.1)[v % 3]
    bz = 0.5 * s if not seated else 0.42 * s
    g.use("creature_pink")
    g.ellipsoid((0, 0, bz), (0.42 * s, 0.38 * s, 0.42 * s), segs=16, steps=8)
    g.use("creature_dark")
    for z in (bz - 0.15 * s, bz + 0.1 * s):
        _band(g, _ell_half(0.42 * s, z, bz, 0.42 * s) + 0.01, _ell_half(0.38 * s, z, bz, 0.42 * s) + 0.01, z, r=0.025)
    if seated:
        for sx in (-1, 1):
            g.tube([(sx * 0.15 * s, -0.1, bz - 0.25 * s), (sx * 0.17 * s, -0.42 * s, bz - 0.28 * s), (sx * 0.17 * s, -0.48 * s, 0.05)], 0.05, segs=5)
    else:
        for sx in (-1, 1):
            g.tube([(sx * 0.15 * s, 0.0, bz - 0.3 * s), (sx * 0.16 * s, -0.04, 0.05)], 0.05, segs=5)
    hz = bz + 0.42 * s + 0.12 * s
    g.ellipsoid((0, -0.05, hz), (0.3 * s, 0.26 * s, 0.24 * s), segs=14, steps=7)
    g.use("creature_pale")
    for sx in (-1, 1):
        g.ellipsoid((sx * 0.1 * s, -0.27 * s, hz + 0.02), (0.065 * s, 0.03, 0.075 * s), segs=8, steps=5)
    hat = [(0.33 * s, 0.0), (0.3 * s, 0.1 * s), (0.22 * s, 0.32 * s), (0.13 * s, 0.52 * s), (0.04 * s, 0.68 * s), (0.0, 0.72 * s)]
    if v % 3 == 1:
        hat = [(0.34 * s, 0.0), (0.33 * s, 0.14 * s), (0.25 * s, 0.26 * s), (0.08 * s, 0.34 * s), (0.0, 0.36 * s)]
    g.revolve(hat, segs=16, m=place(0, -0.02, hz + 0.12 * s))
    g.use("creature_dark")                                # spiral groove round the hat
    top = hat[-2][1]
    path = []
    for i in range(41):
        t = i / 40
        z = t * top * 0.92
        r = lerp(hat[0][0], hat[-2][0], t) + 0.012
        a = TAU * 2.6 * t
        path.append((r * math.cos(a), -0.02 + r * math.sin(a), hz + 0.12 * s + z))
    g.tube(path, 0.015, segs=4)
    return g


def k_soul_twister():
    """Soul Twister: pale dome with a row of glowing dots, banded pale torso, long grey tendrils; hovers."""
    g = Geo()
    hz = 1.75
    g.use("creature_pale")
    g.revolve([(0.0, -0.02), (0.44, 0.0), (0.45, 0.14), (0.38, 0.32), (0.22, 0.44), (0.0, 0.48)], segs=24, m=place(0, 0, hz))
    g.use("creature_soul")
    for k in range(5):
        a = math.radians(-90 + (k - 2) * 26)
        g.ellipsoid((0.4 * math.cos(a), 0.4 * math.sin(a), hz + 0.22), (0.06, 0.04, 0.08), segs=8, steps=5, m=None)
    g.use("creature_pale")
    g.ellipsoid((0, 0, hz - 0.45), (0.3, 0.26, 0.42), segs=14, steps=8)
    g.use("creature_dark")
    for z in (hz - 0.6, hz - 0.35):
        _band(g, _ell_half(0.3, z, hz - 0.45, 0.42) + 0.01, _ell_half(0.26, z, hz - 0.45, 0.42) + 0.01, z, r=0.02)
    g.use("creature_cloak_grey")
    n = 22
    for k in range(n):
        a = TAU * k / n
        if abs(math.sin(a) + 1.0) < 0.25:                 # leave the front middle open so the torso shows
            continue
        ln = 1.05 + 0.25 * math.sin(k * 2.3)
        sway = 0.18 * math.sin(k * 1.7)

        def centre(u, ln=ln, sway=sway):
            return (u * 0.35 + sway * u * u, -u * ln)

        g.lens(centre, lambda u: 0.07 * (1.0 - 0.7 * u), lambda u: 0.025, nu=6, nv=5,
               m=place(0.42 * math.cos(a), 0.4 * math.sin(a), hz + 0.04, rz=a))
    return g


def k_soul_warrior():
    """Soul Warrior: round pale banded body with two big glowing eyes and a small white one, a curled left hand,
    a nail in the right hand."""
    g = Geo()
    bz, r = 1.0, 0.82
    g.use("creature_shell_pale")
    g.ellipsoid((0, 0, bz), (r, r * 0.85, r * 0.95), segs=22, steps=12)
    g.use("creature_dark")                                # wrapped bands, tilted like the drawing
    for k, (z, tilt) in enumerate(((bz - 0.45, 0.12), (bz - 0.2, -0.1), (bz + 0.05, 0.14), (bz + 0.3, -0.06))):
        pts = []
        for i in range(29):
            a = TAU * i / 28
            zz = z + tilt * math.cos(a)
            hw = _ell_half(r, zz, bz, r * 0.95) + 0.015
            pts.append((hw * math.cos(a), hw * 0.85 * math.sin(a), zz))
        g.tube(pts, 0.035, segs=5)
    g.use("creature_soul")
    for sx in (-1, 1):
        g.ellipsoid((sx * 0.33, -0.66, bz + 0.38), (0.15, 0.06, 0.17), segs=12, steps=6)
    g.use("creature_pale")
    g.ellipsoid((0, -0.75, bz + 0.56), (0.06, 0.03, 0.11), segs=8, steps=5)
    g.use("creature_dark")
    for sx in (-1, 1):
        g.tube([(sx * 0.3, 0.0, bz - 0.7), (sx * 0.32, -0.05, 0.06)], 0.09, segs=6)
        g.ellipsoid((sx * 0.33, -0.15, 0.06), (0.14, 0.2, 0.07), segs=8, steps=4)
    g.tube([(-0.78, -0.1, bz + 0.3)] + [(-0.95 + 0.12 * math.cos(a), -0.15, bz + 0.65 + 0.12 * math.sin(a)) for a in (0.0, 1.5, 3.0, 4.5)], 0.045, segs=5)
    g.tube([(0.75, -0.2, bz - 0.1), (0.95, -0.45, bz - 0.35)], 0.06, segs=5)
    _nail(g, (0.95, -0.45, bz - 0.35), (1.55, -0.7, bz + 0.25))
    return g


def k_mistake(v=0):
    """Mistake (soul blob): small pale lump with a dark face and one glowing eye, hovering."""
    g = Geo()
    s = (1.0, 0.8)[v % 2]
    z = 1.2
    g.use("creature_pale")
    g.ellipsoid((0, 0, z), (0.32 * s, 0.28 * s, 0.26 * s), segs=12, steps=7)
    for k in range(4):
        a = TAU * k / 4 + 0.4
        g.ellipsoid((0.25 * s * math.cos(a), 0.2 * s * math.sin(a), z - 0.18 * s), (0.1 * s, 0.1 * s, 0.14 * s), segs=8, steps=5)
    g.use("creature_dark")
    g.ellipsoid((0, -0.2 * s, z + 0.03), (0.16 * s, 0.07 * s, 0.12 * s), segs=10, steps=5)
    g.use("creature_soul")
    g.ellipsoid((0, -0.25 * s, z + 0.04), (0.06 * s, 0.03, 0.06 * s), segs=8, steps=5)
    return g


BUILDERS = {
    "husk_sentry": lambda: k_husk_sentry(0), "husk_sentry_low": lambda: k_husk_sentry(1), "heavy_sentry": k_heavy_sentry,
    "lance_sentry": k_lance_sentry, "winged_sentry": k_winged_sentry,
    "resident_0": lambda: k_resident(0), "resident_1": lambda: k_resident(1), "resident_2": lambda: k_resident(2),
    "resident_seated_0": lambda: k_resident(0, True), "resident_seated_1": lambda: k_resident(1, True), "resident_seated_2": lambda: k_resident(2, True),
    "soul_twister": k_soul_twister, "soul_warrior": k_soul_warrior, "mistake_0": lambda: k_mistake(0), "mistake_1": lambda: k_mistake(1),
}
SCALE = {"soul_warrior": 1.2}                              # larger than a sentry so the silhouettes read apart (C, D-361)
NAMES_ZH = {"husk_sentry": "哨兵", "husk_sentry_low": "哨兵", "heavy_sentry": "重型哨兵", "lance_sentry": "长枪哨兵", "winged_sentry": "飞行哨兵",
            "resident": "城市居民", "resident_seated": "城市居民（坐姿）", "soul_twister": "灵魂扭曲者", "soul_warrior": "灵魂战士", "mistake": "灵魂团块"}
EVIDENCE = {"husk_sentry": ("A", "11_Lower_City/Lower_City_middle.jpg"), "heavy_sentry": ("A", "11_Lower_City/Lower_City_middle.jpg"),
            "lance_sentry": ("A", "08_Tower/Tower_step3.jpg"), "winged_sentry": ("A", "08_Tower/Tower_step3.jpg"),
            "resident": ("A", "08_Tower/Tower_step1.jpg; Tower_step3.jpg"), "soul_twister": ("A", "master B3 enlarged (Soul Sanctum)"),
            "soul_warrior": ("A", "master B3 enlarged (Soul Sanctum, gatehouse level)"), "mistake": ("C", "soul blob of the sanctum; not in the local references")}


def family(kind):
    for k in ("resident_seated", "resident", "husk_sentry", "mistake"):
        if kind.startswith(k):
            return k if k != "husk_sentry" else "husk_sentry"
    return kind


# footprint radius (including the weapon) and height, for placement
RADIUS = {"husk_sentry": 1.05, "heavy_sentry": 1.45, "lance_sentry": 0.75, "winged_sentry": 1.85, "resident": 0.5, "resident_seated": 0.55,
          "soul_twister": 0.75, "soul_warrior": 1.9, "mistake": 0.45}
HEIGHT = {"husk_sentry": 2.3, "heavy_sentry": 3.1, "lance_sentry": 3.2, "winged_sentry": 2.6, "resident": 1.9, "resident_seated": 1.7,
          "soul_twister": 2.3, "soul_warrior": 2.65, "mistake": 1.5}

