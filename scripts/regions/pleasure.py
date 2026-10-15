"""Stage 3 structure: HouseOfPleasure - the performance room (02_Marissa/Marissa.jpg), the lobby with its patterned
shaft (02_Marissa/Marrisa_home.jpg), the porch on the rain column and the upper room known only from the master map.

Scale note: Marissa.jpg is zoomed in about 1.7 times compared with Marrisa_home.jpg (the singer and the stage are larger
relative to the player than the master map allows), so sizes follow the master map (C1) and proportions follow the
screenshot. The character, her wings, the light beam and the HUD are not built. Connections to the east well and to the
east tower are not confirmed and not built.
"""
import math

import cot_assets as A
import cot_furnish as FU
import cot_kit as K
import cot_parts as P
import cot_shell as SH
from cot_geo import Geo, IronCurves, TAU, lerp, place, rng, spiral_pts
from cot_s3 import X, Z

REF_S = "02_Marissa/Marissa.jpg; master C1"
REF_L = "02_Marissa/Marrisa_home.jpg; master C1"
FLOOR = Z(2436)                 # 77.6
STYLE = dict(wall="wall_pleasure", floor="floor", trim="trim_purple", front="cusp", bay=4.6, back=("niche",), glass="glass_pink", lamp=None,
             partition=0, fringe=False, ext="house_wall", inner=False, rail=False)


def k_bouquet(seed=0, n=9, r=0.9):
    """Mound of rose heads with a few leaves tucked under them (A: Marissa.jpg - the flower clusters on and around the stage)."""
    g = Geo()
    rand = rng(seed * 43 + 3)
    heads = []
    for k in range(n):
        a = TAU * rand()
        d = r * rand(0.0, 0.8)
        z = r * (0.95 - 0.55 * (d / r) ** 1.5) + r * rand(-0.08, 0.08)
        heads.append((d * math.cos(a), d * math.sin(a) * 0.85, z, r * rand(0.24, 0.34)))
    g.use("cloth_purple")
    g.ellipsoid((0, 0, r * 0.35), (r * 0.85, r * 0.7, r * 0.45), segs=12, steps=6)          # body of the mound
    for hk, (x, y, z, rr) in enumerate(heads):
        g.use("trim_purple")
        g.ellipsoid((x, y, z + rr * 0.1), (rr * 0.42, rr * 0.42, rr * 0.5), segs=8, steps=5)       # bud
        g.use("cloth_purple")
        for j in range(6):                                # cupped petals leaning out round the bud
            a = TAU * j / 6 + hk
            px, py = x + rr * 0.55 * math.cos(a), y + rr * 0.55 * math.sin(a)
            g.ellipsoid((0, 0, 0), (rr * 0.48, rr * 0.16, rr * 0.5), segs=8, steps=5, m=place(px, py, z, rz=a + math.pi / 2, rx=-0.45))
    g.use("cloth_blue")
    for k in range(6):                                    # leaves lying against the mound, pointing out and up
        a = TAU * k / 6 + rand(0, 0.5)

        def centre(u):
            return (r * (0.55 + 0.45 * u), r * (0.15 + 0.25 * u))

        g.lens(centre, lambda u: 0.13 * r * math.sin(math.pi * u ** 0.7), lambda u: 0.03, nu=6, nv=6, m=place(rz=a), cup=0.25)
    return g


def k_chair():
    """Round-backed audience chair seen from behind in the foreground of Marissa.jpg (A)."""
    g = Geo()
    g.use("cushion")
    g.ellipsoid((0, 0, 0.62), (0.42, 0.4, 0.12), segs=12, steps=6, e=0.7)
    g.ellipsoid((0, -0.36, 1.25), (0.4, 0.07, 0.5), segs=12, steps=8, e=0.9)
    g.use("trim_purple")
    g.ring_arc((0, -0.38, 1.25), 1.0, 0, TAU, 0.05, n=20, plane="XZ", segs=5, m=place(s=(0.44, 1.0, 0.54)))
    g.ellipsoid((0, -0.38, 1.83), (0.1, 0.05, 0.08), segs=8, steps=5)
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.tube([(sx * 0.34, sy * 0.3, 0.55), (sx * 0.38, sy * 0.34, 0.0)], 0.035, segs=5)
        g.tube([(sx * 0.4, -0.36, 0.62), (sx * 0.42, -0.36, 0.95)], 0.035, segs=5)
    return g


def k_hood_lamp():
    """Dark hood carved with scrolls, a heart lamp hanging under it (A: Marrisa_home.jpg centre; master C1 shows it
    repeated up the patterned shaft, so it is read as a lamp housing - B). Hangs on the wall at the origin, faces -Y."""
    g = Geo()
    g.use("wall_deep")
    g.ellipsoid((0, -0.45, 0.0), (0.95, 0.45, 0.62), segs=14, steps=8, e=0.5)
    g.use("trim_purple")
    for z in (-0.52, 0.52):
        g.tube([(-0.95, -0.9, z), (0.95, -0.9, z)], 0.07, segs=5)
    for sx in (-1, 1):
        g.tube([(sx * px, -0.92, pz) for px, pz in spiral_pts(0.42, 0.0, 0.34, 1.4, math.pi / 2, ccw=sx > 0)], 0.04, segs=4, ref=(0, 1, 0))
    g.tube([(0, -0.5, -0.62), (0, -0.5, -0.95)], 0.025, segs=4)
    g.revolve([(0.03, -0.95), (0.16, -1.0), (0.2, -1.08)], segs=8, m=place(0, -0.5, 0))
    g.use("lamp_pink")
    for sx in (-1, 1):
        g.ellipsoid((sx * 0.08, -0.5, -1.2), (0.11, 0.11, 0.13), segs=8, steps=6)
    g.revolve([(0.14, -1.25), (0.07, -1.36), (0.01, -1.45)], segs=8, m=place(0, -0.5, 0))
    return g


def tattered_strips(g, x0, x1, y, z_top, count, lmin, lmax, seed=0, key="cloth_blue", wmin=0.12, wmax=0.34, gap=(0.0, 0.0)):
    """Long ragged strips of cloth hanging side by side (A: the top of Marissa.jpg). Each is a thin flat strip with a
    pointed, torn end and a slight sway."""
    rand = rng(seed * 59 + 5)
    g.use(key)
    x = x0
    while x < x1:
        w = rand(wmin, wmax)
        ln = rand(lmin, lmax)
        sway = rand(-0.12, 0.12)
        yy = y + rand(-0.15, 0.15)
        pts = [(x, z_top), (x + w, z_top)]
        n = 6
        for i in range(1, n + 1):
            t = i / n
            pts.append((x + w * (1.0 - 0.45 * t) + sway * t * t, z_top - ln * t + (0.0 if i < n else 0.0)))
        pts.append((x + w * 0.3 + sway, z_top - ln - rand(0.1, 0.4)))
        for i in range(n, 0, -1):
            t = i / n
            pts.append((x + w * 0.45 * t * 0.6 + sway * t * t, z_top - ln * t * rand(0.92, 1.0)))
        g.prism(pts, yy - 0.03, yy + 0.03)
        x += w * rand(0.55, 0.9) + rand(*gap)


def curled_corbel(g, m, length=2.6, key="trim_purple"):
    """Great segmented bracket curling up and inward like a shell limb (A: Marrisa_home.jpg upper right and upper centre)."""
    g.use(key)
    path, radii = [], []
    n = 22
    for i in range(n + 1):
        t = i / n
        a = math.pi * 1.25 * t
        rr = length * (0.55 - 0.35 * t)
        path.append((length * 0.5 * t + rr * 0.2 * math.sin(a), 0.0, length * 0.2 + rr * math.sin(a * 0.9) + length * 0.25 * t))
        radii.append(length * (0.13 - 0.085 * t) * (1.0 + 0.25 * (i % 3 == 0)))
    g.tube(path, radii, segs=8, ref=(0, 1, 0), m=m)


def house_of_pleasure(S):
    R = "HouseOfPleasure"
    lx0, lx1 = X(5842), 150.4            # lobby
    sx0, sx1 = 150.4, 164.4              # performance room
    ly0, ly1 = -7.0, 11.0
    sy0, sy1 = -8.0, 14.0
    LCEIL, SCEIL = Z(2360), Z(2340)      # 82.67, 84.0

    # ================================================================== performance room (Marissa.jpg)
    stage = P.wel("Stage", sx0, sx1, FLOOR, SCEIL, [FLOOR], doors=[("L", FLOOR)], ev="A", ref=REF_S)
    P.stack(S, R, stage, STYLE, y=(sy0, sy1), front="solid", decor=False, lamps=False, door_y={"L": -1.0}, ext_faces=("N", "R", "S"),
            note="room shell: width, floor and ceiling from master C1; depth is completion")
    # raised stage with its ornate front and a solid base (A front; C depth and underside)
    px0, py0, pz = sx0 + 4.6, 3.0, FLOOR + 1.5
    g = Geo()
    g.use("wall_deep")
    g.box(px0, sx1 - 0.6, py0 + 0.25, sy1 - 0.6, FLOOR, pz - 0.3)
    K.slab(g, px0 - 0.1, sx1 - 0.6, py0, sy1 - 0.6, pz, 0.3, "floor", lip=("front", "left"), trim="trim_purple", drops=False)
    g.use("trim_purple")
    g.box(px0 - 0.15, sx1 - 0.6, py0 - 0.12, py0 + 0.3, FLOOR, FLOOR + 0.22)                 # plinth course
    posts = [px0 + (sx1 - 0.6 - px0) * k / 5 for k in range(6)]
    for xk in posts:                                                                         # carved posts with heart crests
        g.use("trim_purple")
        g.revolve([(0.2, FLOOR), (0.22, FLOOR + 0.2), (0.13, FLOOR + 0.4), (0.15, pz - 0.5), (0.22, pz - 0.3), (0.24, pz + 0.05)], segs=8, m=place(xk, py0, 0))
        for sx in (-1, 1):
            g.ellipsoid((xk + sx * 0.12, py0, pz + 0.3), (0.14, 0.1, 0.16), segs=8, steps=5)
        g.spike((xk, py0, pz + 0.38), (xk, py0, pz + 0.75), 0.05, segs=5)
    for a, b in zip(posts, posts[1:]):                                                       # swags of cloth along the lip
        K.swag(g, a + 0.15, b - 0.15, py0 - 0.06, pz - 0.05, sag=0.45, depth=0.6, key="cloth_purple", folds=4)
        g.use("trim_purple")
        g.tube([(a, py0, pz + 0.06), (b, py0, pz + 0.06)], 0.06, segs=5)
    S.add(g, "StagePlatform", R, "StagePlatform", "A", REF_S, note="front lip observed; platform depth, side and solid base are completion (C)")
    # round draped canopy with the oval segmented ornament (A)
    cx, cy, cr = (X(6105) + X(6180)) / 2 - 1.0, 8.4, 3.1
    ztop, zval = SCEIL - 0.1, Z(2366) - 0.2
    g = Geo()
    g.use("trim_purple")
    for zz, rr in ((zval + 1.25, cr), (zval, cr + 0.08)):
        g.ring_arc((cx, cy, zz), rr, 0, TAU, 0.09, n=40, plane="XY", segs=6)
    g.use("cloth_purple")
    n = 48
    rows = []
    for j in range(5):                                                                       # valance with a scalloped hem
        v = j / 4
        ring_o, ring_i = [], []
        for i in range(n):
            a = TAU * i / n
            rr = cr + 0.1 * math.sin(a * 12)
            z = lerp(zval + 1.2, zval - 0.25 - 0.3 * abs(math.sin(a * 6)), v)
            ring_o.append((cx + (rr + 0.04) * math.cos(a), cy + (rr + 0.04) * math.sin(a), z))
            ring_i.append((cx + (rr - 0.04) * math.cos(a), cy + (rr - 0.04) * math.sin(a), z))
        rows.append((ring_o, ring_i))
    g.grid([r[0] for r in rows] + [r[1] for r in reversed(rows)], close_u=True)
    for k in range(7):                                                                       # long curtains hanging round the back half
        a0 = math.pi * (0.06 + 0.88 * k / 7)
        a1 = math.pi * (0.06 + 0.88 * (k + 1) / 7)
        xa, ya = cx + cr * math.cos(a0), cy + cr * math.sin(a0)
        xb, yb = cx + cr * math.cos(a1), cy + cr * math.sin(a1)
        mid = ((xa + xb) / 2, (ya + yb) / 2)
        ang = math.atan2(yb - ya, xb - xa)
        gg = Geo()
        K.drape(gg, -math.hypot(xb - xa, yb - ya) / 2, math.hypot(xb - xa, yb - ya) / 2, 0.0, zval + 0.1, pz + 0.05, folds=3, amp=0.1, thick=0.06, key="cloth_purple",
                seed=k, hem=0.2, nx=14, nz=8, gather=(pz + 2.2, 0.75) if k in (0, 6) else None)
        o = S.add(gg, f"Canopy_Curtain_{k}", R, "CanopyCurtain", "A", REF_S, note="curtain behind the performer; its back and the space behind are completion")
        o.matrix_world = place(mid[0], mid[1], 0.0, rz=ang)
    g.use("cloth_purple")                                                                    # gathered cap rising to the ceiling
    g.revolve([(cr, zval + 1.2), (cr * 0.8, zval + 1.45), (cr * 0.45, ztop - 0.2), (0.3, ztop)], segs=24, m=place(cx, cy, 0), mod=lambda th, k: 1.0 + 0.04 * math.sin(th * 12))
    g.use("iron")                                                                            # oval segmented ornament on its hanger
    g.tube([(cx, cy, zval + 1.2), (cx, cy, zval + 0.2)], 0.03, segs=4)
    g.use("relief")
    oz = zval - 0.55
    g.ellipsoid((cx, cy, oz), (0.42, 0.3, 0.8), segs=14, steps=10)
    g.use("trim_purple")
    for k in range(-3, 4):
        zz = oz + 0.2 * k
        rr = 0.43 * math.sqrt(max(0.05, 1 - (0.2 * k / 0.8) ** 2))
        g.ring_arc((cx, cy, zz), 1.0, 0, TAU, 0.025, n=16, plane="XY", segs=4, m=place(cx, cy, zz) @ place(s=(rr, rr * 0.72, 1.0)) @ place(-cx, -cy, -zz))
    g.spike((cx, cy, oz - 0.78), (cx, cy, oz - 1.2), 0.05, segs=5, bulb=1.0)
    S.add(g, "DrapeCanopy", R, "DrapeCanopy", "A", REF_S, note="round canopy over the stage; the oval segmented ornament hangs in it. The performer's wings and light beam are not built")
    # proscenium: long tattered strips hanging across the top and two hanging lamps, side curtains tied back (A)
    g = Geo()
    pel_x0, pel_x1 = sx0 + 0.6, sx1 - 0.6
    g.use("cloth_blue")
    g.box(pel_x0, pel_x1, py0 - 1.0, py0 - 0.8, SCEIL - 0.25, SCEIL)                  # rail the strips hang from
    tattered_strips(g, pel_x0 + 0.2, pel_x1 - 0.2, py0 - 0.9, SCEIL - 0.2, 0, 0.6, 2.6, seed=11, gap=(0.2, 0.9))
    K.drape(g, pel_x0, pel_x0 + 2.3, py0 - 0.75, SCEIL - 0.3, FLOOR + 0.1, folds=5, amp=0.14, key="cloth_blue", gather=(FLOOR + 2.3, 0.4), seed=3)
    K.drape(g, pel_x1 - 1.4, pel_x1 + 0.3, py0 - 0.75, SCEIL - 0.3, pz + 0.05, folds=4, amp=0.14, key="cloth_blue", gather=(pz + 2.0, 0.45), seed=4)
    K.drape(g, sy0 + 1.0, sy0 + 4.2, sx0 + 0.85, FLOOR + 4.6, FLOOR + 0.1, folds=5, amp=0.12, key="cloth_blue", gather=(FLOOR + 2.0, 0.4), seed=5, axis="Y")
    S.add(g, "Curtains", R, "Curtains", "A", REF_S, note="tattered strips and curtains with folds and thickness; what lies behind the curtains (wall and wings of the stage) is completion")
    lampk = S.kit("pelmet_lamp", lambda: pelmet_lamp())
    for k in (1, 2):
        S.put(lampk, f"PelmetLamp_{k}", R, "PelmetLamp", place(lerp(pel_x0, pel_x1, k / 3), py0 - 0.9, SCEIL - 3.15), "A", REF_S)
    # wall pattern as a separate raised layer (A), hanging dark fringe (A), bouquets (A), chairs (A)
    g = Geo()
    K.pattern_relief(g, sx0 + 0.8, sx1 - 0.8, FLOOR + 0.4, SCEIL - 0.6, sy1 - 0.62, cell=1.15, key="pattern")
    S.add(g, "WallPattern_Stage", R, "WallPattern", "A", REF_S, note="pattern panels stand 5 cm proud of the wall and are a separate object")
    g = Geo()
    for k, yy in enumerate((12.5, -3.5)):
        tattered_strips(g, sx0 + 0.8, sx1 - 0.8, yy, SCEIL, 0, 0.4, 1.4, seed=20 + k, key="curtain", wmin=0.15, wmax=0.4, gap=(0.3, 1.2))
    # stalactites under the ceiling: the stage room is a cave hung with rock points on the master (A)
    S.add(g, "CeilingFringe", R, "CeilingFringe", "A", REF_S)
    # the hall is a cave: an uneven rock ceiling with a few long dark points (A: master C1, Marissa.jpg)
    g = Geo()
    K.rock_roof(g, sx0 + 0.4, sx1 - 0.4, sy0 + 0.3, sy1 - 0.3, lambda x: SCEIL - 0.7 - 0.5 * math.sin((x - sx0) * 0.7), SCEIL + 0.2, step=0.8, amp=0.55, seed=33, key="rock")
    rand = rng(35)
    for k in range(7):
        px, py = lerp(sx0 + 1.2, sx1 - 1.2, (k + 0.5) / 7) + rand(-0.6, 0.6), rand(sy0 + 1.0, 4.0)
        K.stalactite(g, px, py, SCEIL - 0.6, rand(2.4, 4.6), rand(0.25, 0.42), seed=36 + k, key="rock")
    g.use("trim_purple")                                         # scalloped arch line along the top of the back wall (A: Marissa.jpg)
    n_sc = 11
    for k in range(n_sc):
        xa, xb = lerp(sx0 + 0.8, sx1 - 0.8, k / n_sc), lerp(sx0 + 0.8, sx1 - 0.8, (k + 1) / n_sc)
        g.tube([((xa + xb) / 2 - (xb - xa) / 2 * math.cos(math.pi * i / 10), sy1 - 0.7, SCEIL - 1.9 + 0.55 * math.sin(math.pi * i / 10)) for i in range(11)], 0.07, segs=5)
        g.ellipsoid((xb, sy1 - 0.72, SCEIL - 1.95), (0.1, 0.06, 0.16), segs=8, steps=5)
    S.add(g, "CaveCeiling", R, "CaveCeiling", "A", "master C1; 02_Marissa/Marissa.jpg", note="uneven ceiling, long points and scalloped arch line; exact forms are completion", smooth=50)
    bq = [S.kit(f"bouquet_{v}", lambda v=v: k_bouquet(v)) for v in range(3)]
    spots = [(px0 + 2.2, py0 + 1.6, pz, 1.25), (px0 + 4.1, py0 + 2.2, pz, 0.8), (sx1 - 2.0, py0 + 1.2, pz, 0.7), (sx1 - 1.4, py0 + 3.6, pz, 1.2),
             (px0 - 1.6, 2.0, FLOOR, 0.9), (px0 - 3.2, 4.5, FLOOR, 1.0), (sx0 + 1.6, 9.0, FLOOR, 1.1), (px0 - 0.8, -0.5, FLOOR, 0.7), (sx0 + 3.0, 12.2, FLOOR, 1.2)]
    for k, (bx, by, bz, s) in enumerate(spots):
        S.put(bq[k % 3], f"Bouquet_{k}", R, "Bouquet", place(bx, by, bz, rz=k * 1.1, s=s), "A", REF_S)
    ch = S.kit("chair", lambda: k_chair())
    for row, yy in enumerate((-2.2, -4.6)):
        for k in range(6):
            S.put(ch, f"Chair_{row}_{k}", R, "AudienceChair", place(sx0 + 3.2 + 1.75 * k + 0.5 * row, yy, FLOOR), "A", REF_S)

    # ================================================================== lobby and patterned shaft (Marrisa_home.jpg)
    lobby = P.wel("Lobby", lx0, lx1, FLOOR, LCEIL, [FLOOR], doors=[("L", FLOOR), ("R", FLOOR)], ev="A", ref=REF_L)
    P.stack(S, R, lobby, STYLE, y=(ly0, ly1), front="solid", roof=False, decor=False, lamps=False, door_y={"L": 0.0, "R": -1.0}, ext_faces=("N", "S"),
            note="room shell from master C1; depth is completion")
    shx0, shx1, shy0, shy1, shz = X(5860), X(5908), 6.2, ly1, Z(2190)
    g = Geo()
    for a, b, c, d in ((lx0 - 0.3, shx0, ly0 - 0.45, ly1 + 0.3), (shx1, lx1 + 0.3, ly0 - 0.45, ly1 + 0.3), (shx0, shx1, ly0 - 0.45, shy0)):
        K.slab(g, a, b, c, d, LCEIL + 0.5, 0.5, "floor", lip=("front",) if c < ly0 else (), trim="trim_purple")
    g.use("wall_pleasure")                                                                   # shaft walls rising from the lobby's back wall
    g.box(shx0 - 0.5, shx0, shy0 - 0.5, shy1, LCEIL, shz)
    g.box(shx1, shx1 + 0.5, shy0 - 0.5, shy1, LCEIL, shz)
    g.box(shx0, shx1, shy1 - 0.6, shy1, LCEIL, shz)
    g.box(shx0 - 0.5, shx1 + 0.5, shy0 - 0.5, shy1, shz, shz + 0.5)
    S.add(g, "Shaft", R, "PatternShaft", "A", "master C1: patterned wall column above the lobby", note="shaft plan (depth) is completion")
    g = Geo().use("wall_pleasure")
    g.box(shx0, shx1, shy0 - 0.5, shy0, LCEIL + 0.5, shz)
    S.add(g, "Shaft_Front", R, "PatternShaft", "C", REF_L, note="viewer-side wall of the shaft", layer="FRONT")
    g = Geo()
    K.pattern_relief(g, lx0 + 0.8, lx1 - 0.8, FLOOR + 0.4, LCEIL - 0.3, ly1 - 0.62, cell=1.15, key="pattern")
    K.pattern_relief(g, shx0 + 0.1, shx1 - 0.1, LCEIL + 0.2, shz - 0.3, shy1 - 0.62, cell=1.05, key="pattern")
    S.add(g, "WallPattern_Lobby", R, "WallPattern", "A", REF_L, note="pattern panels stand proud of the wall and are a separate object")
    hood = S.kit("hood_lamp", lambda: k_hood_lamp())
    mx = (shx0 + shx1) / 2
    for k, zz in enumerate((Z(2406) + 1.1, Z(2292) + 0.6)):
        S.put(hood, f"Hood_{k}", R, "HoodLamp", place(mx, shy1 - 0.66, zz), "A" if k == 0 else "B", REF_L,
              note="hood over a heart lamp; the master shows a second one higher in the shaft, so it is read as a lamp housing rather than a doorway or a window")
    # arch piers with heart lamps (A)
    heart = S.kit("walllamp_heart", lambda: K.k_wall_lamp("lamp_pink", "heart"))
    g = Geo()
    for k, xk in enumerate((shx0 - 0.9, shx1 + 0.9, lx1 - 3.6)):
        g.use("trim_purple")
        g.revolve([(0.42, FLOOR), (0.45, FLOOR + 0.25), (0.26, FLOOR + 0.5), (0.22, FLOOR + 2.6), (0.36, FLOOR + 2.8), (0.3, FLOOR + 3.0), (0.5, FLOOR + 3.3), (0.56, FLOOR + 3.5)],
                  segs=12, m=place(xk, ly1 - 1.1, 0))
        S.put(heart, f"HeartLamp_{k}", R, "HeartLamp", place(xk + (0.5 if k != 1 else -0.5), ly1 - 1.5, FLOOR + 2.7, rz=0.0), "A", REF_L)
    g.use("wall_pleasure")
    for a, b in ((lx0 + 0.6, shx0 - 0.9), (shx0 - 0.9, shx1 + 0.9), (shx1 + 0.9, lx1 - 3.6)):
        w = b - a - 0.5
        kind, rise, spring = P.fit_arch("cusp", w, LCEIL - FLOOR - 3.5, 0.2, 0.05)
        K.arcade(g, a, b, FLOOR + 3.5, LCEIL, ly1 - 1.3, ly1 - 0.9, [((a + b) / 2, w, FLOOR + 3.5 + spring, kind, rise, FLOOR + 3.5)])
    curled_corbel(g, place(shx1 + 2.4, ly1 - 1.6, LCEIL + 0.05, rx=math.pi, rz=math.pi), 4.4)     # hangs from the ceiling, curls onto the pier (large, as on Marrisa_home.jpg)
    curled_corbel(g, place(shx0 - 1.2, ly1 - 1.6, LCEIL + 0.05, rx=math.pi), 2.2)
    S.add(g, "ArchPiers", R, "ArchPiers", "A", REF_L, note="the great curled brackets are the scroll-shaped members at the upper right and centre of Marrisa_home.jpg")
    # scroll niche with its iron screen and the counter with stacks (A)
    nx = lx1 - 2.4
    g = Geo()
    g.use("wall_deep")
    g.box(nx - 1.5, nx + 1.5, ly1 - 0.9, ly1 - 0.62, FLOOR, FLOOR + 3.4)
    g.use("trim_purple")
    K.arch_trim(g, nx, 2.8, FLOOR + 2.0, FLOOR, "round", y=ly1 - 0.95, r=0.14)
    g.ellipsoid((nx, ly1 - 1.0, FLOOR + 3.6), (0.4, 0.14, 0.3), segs=10, steps=6)
    g.use("cushion")
    g.revolve([(1.25, 0.0), (1.4, 0.2), (1.3, 0.85), (1.45, 1.0), (1.45, 1.12), (0.02, 1.12)], segs=18, sx=1.0, sy=0.45, m=place(nx, ly1 - 2.0, FLOOR))
    S.add(g, "ScrollNiche", R, "ScrollNiche", "A", REF_L)
    ic = IronCurves()
    for sx in (-1, 1):
        ic.add([(nx + sx * px, ly1 - 1.0, FLOOR + pz) for px, pz in spiral_pts(0.55, 2.45, 0.42, 1.6, math.pi / 2, ccw=sx > 0)], r=1.2, taper="end")
        ic.add([(nx + sx * px, ly1 - 1.0, FLOOR + pz) for px, pz in spiral_pts(0.5, 1.75, 0.3, 1.4, -math.pi / 2, ccw=sx < 0)], r=1.0, taper="end")
        ic.add([(nx + sx * 1.3, ly1 - 1.0, FLOOR + 1.15), (nx + sx * 1.3, ly1 - 1.0, FLOOR + 2.0)], r=1.2, smooth=False)
    ic.add([(nx, ly1 - 1.0, FLOOR + 1.15), (nx, ly1 - 1.0, FLOOR + 3.3)], r=1.2, smooth=False)
    S.add_iron(ic, "ScrollNiche_Iron", R, "ScrollNiche", "A", REF_L, bevel=0.035)
    stack_k = [S.kit(f"paper_stack_{v}", lambda v=v: K.k_shelf_stack(v)) for v in range(3)]
    for k, (bx, by, bz, s) in enumerate(((nx - 2.3, ly1 - 2.0, FLOOR, 0.9), (nx + 1.9, ly1 - 2.4, FLOOR, 1.0), (nx - 0.5, ly1 - 2.0, FLOOR + 1.12, 0.45), (nx + 0.5, ly1 - 2.1, FLOOR + 1.12, 0.4),
                                         (nx - 3.6, ly1 - 4.6, FLOOR, 0.8), (shx1 + 2.0, -3.0, FLOOR + 0.8, 0.7))):
        S.put(stack_k[k % 3], f"Stack_{k}", R, "PaperStack", place(bx, by, bz, rz=k * 0.8, s=s), "A", REF_L)
    # stepped low platforms in the right half of the lobby (A that the floor steps; C their plan)
    g = Geo()
    K.slab(g, shx1 + 0.6, lx1 - 1.0, -5.5, -1.2, FLOOR + 0.42, 0.42, "floor", lip=("front", "back", "left"), trim="trim_purple", drops=False)
    K.slab(g, shx1 + 2.0, lx1 - 1.6, -4.6, -2.0, FLOOR + 0.84, 0.42, "floor", lip=("front", "back", "left", "right"), trim="trim_purple", drops=False)
    g.use("cushion")                                                                         # pink cobbled edge of the floor (A)
    rand = rng(7)
    x = lx0 + 0.8
    while x < lx1 - 0.8:
        w = rand(0.5, 0.8)
        g.ellipsoid((x + w / 2, ly0 + 0.9, FLOOR + 0.02), (w * 0.5, 0.32, 0.1), segs=8, steps=4, e=0.6)
        x += w
    S.add(g, "SteppedPlatforms", R, "SteppedPlatforms", "A", REF_L, note="staggered platforms seen as foreground silhouettes; their plan is completion")
    g = Geo()
    for k, yy in enumerate((ly0 + 1.5, 2.0, ly1 - 2.6)):
        SH.hanging_fringe(g, shx1 + 1.2, lx1 - 0.8, yy, LCEIL, 1.1, seed=30 + k, key="curtain", n=36)
    K.drape(g, ly0 + 0.9, ly0 + 3.6, lx1 - 0.75, FLOOR + 4.4, FLOOR + 0.1, folds=5, amp=0.12, key="cloth_blue", gather=(FLOOR + 2.0, 0.45), seed=9, axis="Y")
    S.add(g, "Lobby_FringeAndCurtain", R, "CeilingFringe", "A", REF_L)

    # ---- porch on the rain column: louvre canopy with spikes, arches, glass pillar (A)
    pe = S.el(R, "Porch")
    ppx0 = X(pe["map"][0])
    g = Geo()
    K.slab(g, ppx0, lx0, -4.2, 4.2, FLOOR, 0.7, "stone", lip=("front", "back", "left"), trim="stone_far_trim")
    g.use("stone_far")
    K.arcade(g, -4.0, 4.0, FLOOR, Z(2382), 0.0, 0.35, [(-2.0, 3.2, FLOOR + 1.9, "pointed", 1.4, None), (2.0, 3.2, FLOOR + 1.9, "pointed", 1.4, None)], m=place(ppx0 + 0.45, 0, 0, rz=math.pi / 2))
    A.add_corbel_wing(g, place(ppx0 + 0.5, 0.0, FLOOR - 0.72, rz=math.pi), length=2.0, blades=5, key="louvre_frame")
    S.add(g, "Porch", R, "Porch", "A", REF_L, note="how the porch is reached from the east well is not confirmed; it ends at a railing")
    pc = S.el(R, "PorchCanopy")
    P.louvre_roof(S, R, "PorchCanopy", ppx0 - 0.4, lx0 + 0.2, Z(pc["map"][3]), Z(pc["map"][1]), -4.5, 4.5, bays=1, curve_end="W", ev="A", ref=REF_L)
    P.spike_rail(S, R, "Porch_Rail", [((ppx0 + 0.15, -4.0), (ppx0 + 0.15, 4.0)), ((ppx0 + 0.15, -4.0), (lx0, -4.0)), ((ppx0 + 0.15, 4.0), (lx0, 4.0))], z=FLOOR, ev="A", ref=REF_L)
    gp = S.el(R, "GlassPillar")
    P.glass_pillar(S, R, "GlassPillar", X(gp["x"]) - 0.9, -3.0, 0.62, Z(gp["map_y"][1]), Z(gp["map_y"][0]), "A", "master C1")

    # ---- upper room known only from the master (A, low detail): pale columns and great round pale panes
    ue = S.el(R, "UpperRoom")
    ust = dict(STYLE, wall="wall_sanctum", trim="trim_pale", front="round", bay=4.0, glass="glass_pink")
    ui = P.stack(S, R, ue, ust, front="solid", decor=False, lamps=False, ext_faces=("N", "R", "L", "S"))
    zf_u, zt_u = ui["floors"][0], ui["zt"]
    g = Geo()
    cols = [lerp(ui["x0"], ui["x1"], f) for f in (0.38, 0.62)]
    for k, cxk in enumerate(cols):                         # tall slender columns whose capitals branch into pointed arches
        g.use("trim_pale")
        g.revolve([(0.36, zf_u), (0.4, zf_u + 0.3), (0.24, zf_u + 0.6), (0.2, zt_u - 2.4), (0.3, zt_u - 2.1), (0.26, zt_u - 1.9)], segs=12, m=place(cxk, ui["yb"] - 3.0, 0))
        for sx in (-1, 1):
            g.tube([(cxk, ui["yb"] - 3.0, zt_u - 2.0), (cxk + sx * 0.9, ui["yb"] - 3.0, zt_u - 0.9), (cxk + sx * 2.2, ui["yb"] - 3.0, zt_u - 0.15)], [0.2, 0.16, 0.12], segs=6, ref=(0, 1, 0))
    g.use("glass_pink")                                    # great pale round glows behind the columns
    for k, (gx, rr) in enumerate(((lerp(ui["x0"], ui["x1"], 0.5), 2.6), (lerp(ui["x0"], ui["x1"], 0.2), 1.9), (lerp(ui["x0"], ui["x1"], 0.8), 2.1))):
        g.ellipsoid((gx, ui["yb"] - 0.75, zf_u + 2.9), (rr, 0.12, rr), segs=22, steps=10)
    g.use("curtain")
    tattered_strips(g, ui["x0"] + 0.8, ui["x1"] - 0.8, ui["yb"] - 4.5, zt_u, 16, 0.6, 2.4, seed=41, key="curtain", gap=(0.4, 1.4))
    tattered_strips(g, ui["x0"] + 0.8, ui["x1"] - 0.8, ui["yb"] - 1.4, zt_u, 12, 0.8, 2.8, seed=42, key="curtain", gap=(0.3, 1.0))
    K.drape(g, ui["x0"] + 0.8, ui["x0"] + 3.2, ui["yf"] + 2.0, zt_u - 0.2, zf_u + 0.1, folds=5, amp=0.14, key="cloth_purple", gather=(zf_u + 2.0, 0.4), seed=13)
    S.add(g, "UpperRoom_ColumnsAndGlows", R, "UpperRoomColumns", "A", "master C1: pale room with two tall branching columns, great round pale glows and stalactites; no local screenshot",
          note="the round glows may be lamps or windows; they are modelled as pale panes (B)")
    heap = [S.kit(f"heap_{v}", lambda v=v: SH.k_heap(v)) for v in range(2)]
    for k, (hx, hy, hs) in enumerate(((ui["x0"] + 1.8, ui["yb"] - 2.2, 1.6), (ui["x1"] - 2.0, ui["yb"] - 2.2, 1.7), (ui["x0"] + 4.6, ui["yb"] - 1.7, 1.2),
                                       (lerp(ui["x0"], ui["x1"], 0.5), ui["yb"] - 1.7, 1.0), (ui["x1"] - 4.8, ui["yb"] - 1.6, 1.3), (ui["x0"] + 2.2, ui["yf"] + 3.6, 1.4),
                                       (ui["x1"] - 2.4, ui["yf"] + 6.0, 1.2))):
        S.put(heap[k % 2], f"UpperRoom_Heap_{k}", R, "ScrapHeap", place(hx, hy, zf_u, rz=k * 1.1, s=hs), "A", "master C1 (heaps along the floor of the bright room)")
    g = Geo()                                                    # long dark points hanging into the room (A: master C1)
    for k, (fx, ln) in enumerate(((0.12, 2.4), (0.27, 3.4), (0.47, 2.8), (0.55, 3.8), (0.73, 3.0), (0.88, 2.2))):
        K.stalactite(g, lerp(ui["x0"], ui["x1"], fx), ui["yb"] - 5.2 + 0.6 * (k % 2), zt_u - 0.1, ln, 0.3, seed=60 + k, key="rock")
    g.use("cushion")                                             # low round seats facing the glows (C)
    for k, fx in enumerate((0.4, 0.5, 0.6)):
        g.revolve([(0.55, 0.0), (0.62, 0.15), (0.6, 0.38), (0.02, 0.45)], segs=14, m=place(lerp(ui["x0"], ui["x1"], fx), ui["yb"] - 9.0, zf_u))
    S.add(g, "UpperRoom_PointsAndSeats", R, "UpperRoomFittings", "A", "master C1", note="points read from the master; the seats are completion (C)", smooth=40)
    sett = S.kit("FU_settee_f", lambda: FU.k_settee())
    for k, fx in enumerate((0.22, 0.78)):
        S.put(sett, f"UpperRoom_Settee_{k}", R, "Furniture", place(lerp(ui["x0"], ui["x1"], fx), ui["yb"] - 5.6, zf_u + 0.01, rz=math.pi), "C", "master C1",
              note="seats in the bright room: completion")
    mxu, myu = lerp(ui["x0"], ui["x1"], 0.5), ui["yf"] + 6.5               # a low table with chairs on a rug in the front half (C)
    S.put(S.kit("FU_rug_up", lambda: FU.k_rug(4.6, 3.2)), "UpperRoom_FurnG_0_rug", R, "Furniture", place(mxu, myu, zf_u + 0.005), "C", "master C1")
    S.put(S.kit("FU_table_up", lambda: FU.k_table(1)), "UpperRoom_FurnG_0_table", R, "Furniture", place(mxu, myu, zf_u + 0.02), "C", "master C1")
    for k, (dx, dy, rz) in enumerate(((-1.3, 0.0, -math.pi / 2), (1.3, 0.0, math.pi / 2), (0.0, -1.0, 0.0), (0.0, 1.0, math.pi))):
        S.put(S.kit("FU_chair_up", lambda: FU.k_chair()), f"UpperRoom_FurnG_0_chair_{k}", R, "Furniture", place(mxu + dx, myu + dy, zf_u + 0.02, rz=rz), "C", "master C1")
    P.pad_field(S, R, "UpperRoom_Pads", ui["x1"] - 4.5, ui["x1"] - 0.6, zt_u - 2.6, zt_u - 0.4, ui["yb"] - 0.4, 14, seed=63, facing="front", size=(0.5, 1.0),
                ev="A", ref="master C1 (pad cluster in the upper right corner)")

    # ---- rock shelf under the house and infill between the rooms (C)
    P.host(S, R, "Podium", (X(5770), X(6224), -8.0, 30.0, Z(2560), FLOOR - 0.6), ("front", "bottom", "west", "east"), ev="C",
           ref="black on master under the house; rock shelf tied back to the cavern wall", a=0.7)
    P.host(S, R, "Infill", (shx1 + 0.6, X(6224) + 1.5, -8.8, 14.8, SCEIL + 0.6, Z(2256) - 0.3), ("front", "back", "east", "bottom"), ev="C",
           ref="black on master between the upper room and the stage", a=1.1)
    g = Geo()                                                    # dark points hanging from the ledge's edge over both sides of the stage room (A: master C1)
    rand = rng(64)
    for k in range(14):
        K.stalactite(g, rand(sx0 + 0.6, X(6224) + 1.0), rand(-8.7, -8.15), SCEIL + 0.7, rand(0.8, 2.4), rand(0.18, 0.32), seed=70 + k, key="rock")
    for k in range(7):
        K.stalactite(g, rand(sx1 + 0.5, X(6224) + 1.2), rand(-7.5, 14.0), SCEIL + 0.7, rand(1.0, 3.2), rand(0.2, 0.35), seed=90 + k, key="rock")
    S.add(g, "LedgeStalactites", R, "Stalactites", "A", "master C1: long dark points under the rock between the rooms", note="their places are completion", smooth=40)

    # ---- cameras: both screenshots get their own comparison camera (zoom noted above), plus sections and obliques
    # ---- audience (D-347): residents seated on the chairs, facing the stage (A: chair backs and audience in Marissa.jpg)
    for row, yy in enumerate((-2.2, -4.6)):
        for k in range(6):
            if (row * 6 + k) % 3 == 2:
                continue
            P.creature(S, R, f"resident_seated_{(row + k) % 3}", f"Audience_{row}_{k}", sx0 + 3.2 + 1.75 * k + 0.5 * row, yy + 0.06, FLOOR + 0.6, rz=math.pi)
    P.creature(S, R, "resident_1", "Lobby_0", lx0 + 3.0, 2.0, FLOOR + 0.01, rz=-0.3)
    P.creature(S, R, "resident_2", "Lobby_1", shx1 + 3.4, -3.3, FLOOR + 0.85, rz=0.5)
    S.cam_auto(R, (ppx0, sx1, sy0, sy1, FLOOR - 1.5, Z(2160) + 1.0), ref="master C1", views=("front", "closed", "oblique", "back"))
    S.camera("Side", R, (ppx0 - 30.0, -26.0, FLOOR + 5.0), look=((ppx0 + sx1) / 2, 2.0, FLOOR + 3.0), lens=26.0, kind="side", hide=("ROCK", "CEILING", "BACKDROP", "CAVESHELL"),
             purpose="the house from the west: porch, lobby, upper room and the rock they stand on")
    S.camera("Underside", R, (sx0 - 6.0, -22.0, FLOOR - 12.0), look=(sx0 + 2.0, 3.0, FLOOR - 1.0), lens=24.0, kind="view", hide=("CAVESHELL",),
             purpose="from below: the rock shelf under the rooms and the stage room floor")
    S.camera("Stage_Underneath", R, (px0 - 3.0, -2.6, FLOOR + 0.9), look=(sx1 - 1.0, 6.0, FLOOR + 0.6), lens=18.0, kind="interior",
             purpose="the raised stage from the floor: its lip, posts and solid base")
    S.camera("REF_Marissa", R, (157.3, -26.0, FLOOR + 3.4), look=(157.6, 10.0, FLOOR + 3.3), lens=62.0, kind="ref", hide=("FRONT",), ref="02_Marissa/Marissa.jpg",
             purpose="performance room framed like Marissa.jpg (audience side toward the stage)")
    S.camera("REF_Home", R, (144.4, -30.0, FLOOR + 3.6), look=(144.4, 10.0, FLOOR + 3.9), lens=58.0, kind="ref", hide=("FRONT",), ref="02_Marissa/Marrisa_home.jpg",
             purpose="lobby framed like Marrisa_home.jpg (porch canopy left, patterned wall and hood centre, scroll niche right)")
    S.camera("Stage_Side", R, (sx0 + 1.4, -5.5, FLOOR + 2.4), look=(sx1 - 2.0, 9.0, FLOOR + 2.6), lens=18.0, kind="interior", purpose="stage lip, its side and thickness, from the door")
    S.camera("Stage_Behind", R, (sx0 + 0.9, 12.8, FLOOR + 3.4), look=(sx1 - 3.0, -6.0, FLOOR + 1.5), lens=16.0, kind="back", purpose="behind the curtains and the canopy, looking back at the audience")
    S.camera("Stage_Top", R, ((sx0 + sx1) / 2, 3.0, SCEIL - 0.9), look=((sx0 + sx1) / 2, 3.0, FLOOR), ortho=26.0, hide=("CEILING", "ROCK"), kind="top", purpose="plan of the stage room from just under its ceiling")
    S.camera("Lobby_Shaft", R, (mx, shy0 - 3.0, FLOOR + 2.0), look=(mx, shy1, FLOOR + 6.5), lens=18.0, kind="interior", hide=("FRONT",), purpose="up the patterned shaft with its hoods")
    S.camera("Porch", R, (ppx0 - 14.0, -16.0, FLOOR + 6.0), look=(lx0, 0.0, FLOOR + 5.0), lens=30.0, kind="view", purpose="porch, canopy and glass pillar from the rain column")
    S.camera("UpperRoom", R, (ui["x1"] - 1.4, ui["yf"] + 1.4, ui["floors"][0] + 2.0), look=(ui["x0"] + 2.0, ui["yb"] - 1.0, ui["floors"][0] + 2.8), lens=18.0, kind="interior",
             purpose="upper pale room (master only)")
    cam = S.camera("Section_Inside", R, ((ppx0 + sx1) / 2, -6.6, (FLOOR + Z(2160)) / 2), ortho=34.0, rot=(90.0, 0.0, 0.0), kind="ref", ref="master C1", res=(1920, 1300),
                   purpose="section just inside the front walls, comparable with master C1")
    cam.data.clip_start = 0.05


def pelmet_lamp():
    """Small dark-cased lamp hanging at the cusps of the pelmet (A: Marissa.jpg)."""
    g = Geo()
    g.use("iron")
    g.tube([(0, 0, 0.9), (0, 0, 0.3)], 0.02, segs=4)
    g.revolve([(0.03, 0.3), (0.2, 0.2), (0.26, 0.05), (0.22, -0.1), (0.1, -0.2), (0.02, -0.3)], segs=10)
    g.use("lamp_warm")
    g.ellipsoid((0, -0.02, 0.0), (0.2, 0.2, 0.09), segs=10, steps=5)
    return g


REGIONS = {"HouseOfPleasure": house_of_pleasure}
