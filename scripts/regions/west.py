"""Stage 3 structure: the west - WestFaceChamber, WestStreets, WestStation, GreenAtrium, WestLowCorridor."""
import math

import cot_assets as A
import cot_kit as K
import cot_parts as P
import cot_shell as SH
from cot_geo import Geo, IronCurves, TAU, lerp, place, rng
from cot_s3 import X, Z

HALL_Z = Z(1448)             # 143.47 main street floor
ARC_Z = Z(1412)              # 145.87 low arcade floor
STN_Z = Z(1331)              # 151.27 station floor
CEIL = [(X(800), Z(1330)), (X(1040), Z(1250)), (X(1260), Z(1175)), (X(1500), Z(1165))]


def ceil_z(x):
    if x <= CEIL[0][0]:
        return CEIL[0][1]
    for (xa, za), (xb, zb) in zip(CEIL, CEIL[1:]):
        if xa <= x <= xb:
            return lerp(za, zb, (x - xa) / (xb - xa))
    return CEIL[-1][1]


def aedicules(S, R, name, xs, y, z, w=2.6, h=4.3, ref="", ev="A", pendant=True):
    kit = S.kit(f"aedicule_{w:.1f}_{h:.1f}_{int(pendant)}", lambda: SH.k_aedicule(w, h, pendant=pendant))
    return [S.put(kit, f"{name}_{i:02d}", R, "Aedicule", place(x, y, z), ev, ref) for i, x in enumerate(xs)]


def hive_jars(S, R, name, items, ref="", ev="A"):
    kits = [S.kit(f"hivejar_{v}", lambda v=v: SH.k_hive_jar(v)) for v in range(3)]
    return [S.put(kits[i % 3], f"{name}_{i:03d}", R, "HiveJar", place(x, y, z, rz=i * 1.3), ev, ref) for i, (x, y, z) in enumerate(items)]


def lobes(S, R, name, items, ref="", ev="A", layer=None):
    kits = [S.kit(f"lobes_{v}", lambda v=v: K.k_lobes(seed=v, n=5 + v)) for v in range(3)]
    return [S.put(kits[i % 3], f"{name}_{i:03d}", R, "RockLobes", place(x, y, z, rz=i * 2.1, s=s), ev, ref, layer=layer) for i, (x, y, z, s) in enumerate(items)]


# ============================================================================ WestFaceChamber
def west_face_chamber(S):
    R = "WestFaceChamber"
    REF = "master D1 (no local screenshot)"
    e = S.el(R, "Room")
    st = dict(P.STYLES["street"], bay=5.0)
    info = P.stack(S, R, e, st, decor=False, lamps=False, ext_faces=())
    x0, x1, yb, zf, zt = info["x0"], info["x1"], info["yb"], info["floors"][0], info["zt"]
    g = Geo()
    mx_, mz_ = X(211), Z(1347)
    SH.shell_mask(g, 3.9, 5.6, wing=0.8, m=place(mx_, yb - 0.72, mz_ - 0.6))
    # broad dark wings spreading low from the mask's lower half, three layers a side (A: master D1)
    g.use("shell")
    L0 = min(7.5, (x1 - x0) * 0.3)
    for sx in (-1, 1):
        for k in range(3):
            L = L0 * (1.0 - 0.18 * k)
            dz = -1.0 * k
            pts = [(0.0, 0.9 + dz), (L * 0.45, 1.3 + dz), (L, 0.4 + dz - 0.5 * k), (L * 0.97, -0.6 + dz - 0.5 * k), (L * 0.55, -0.9 + dz), (0.0, -0.5 + dz)]
            pts = [(mx_ + sx * (1.6 + px), mz_ + 1.2 + pz) for px, pz in pts]
            if sx < 0:
                pts = pts[::-1]
            g.prism(pts, yb - 0.95 + 0.12 * k, yb - 0.65 + 0.12 * k)
    S.add(g, "FaceRelief", R, "FaceRelief", "A", REF, note="size and place read from master D1: a banded shell mask with broad layered wings, no human features")
    # rounded top corners: quarter-round fillets in front of the back wall, with a moulding along the curve (A: rounded outline on master D1)
    g = Geo().use("stone_far")
    Rc = (zt - zf) * 0.45
    for sx, xc in ((1, x0), (-1, x1)):
        arc = [(xc + sx * (Rc - Rc * math.cos(math.pi / 2 * i / 12)), zt - Rc + Rc * math.sin(math.pi / 2 * i / 12)) for i in range(13)]
        pts = [(xc, zt)] + arc[::-1] if sx > 0 else arc + [(xc, zt)]
        pts = [(xc, zt - Rc)] + arc + [(xc, zt)]
        if sx < 0:
            pts = pts[::-1]
        g.prism(pts, yb - 2.8, yb - 0.1)
    g.use("stone_far_trim")
    for sx, xc in ((1, x0), (-1, x1)):
        g.tube([(xc + sx * (Rc - (Rc - 0.15) * math.cos(math.pi / 2 * i / 12)), yb - 2.85, zt - Rc + (Rc - 0.15) * math.sin(math.pi / 2 * i / 12)) for i in range(13)], 0.18, segs=6)
    g.tube([(x0 + Rc, yb - 2.85, zt - 0.15), (x1 - Rc, yb - 2.85, zt - 0.15)], 0.18, segs=6)
    S.add(g, "CornerFillets", R, "ArchScreen", "B", REF, note="rounded corners read from the outline on master D1; their depth is completion")
    for sx, xe in ((1, x0 + 0.5), (-1, x1 - 0.5)):             # column clusters at both ends (A: master D1)
        for k in range(3):
            S.put(P.kit_column(S, zt - zf - 0.6, 0.18 + 0.04 * (k % 2), "stone_far_trim"), f"EndColumn_{'L' if sx > 0 else 'R'}_{k}", R, "Column",
                  place(xe + sx * 0.5 * k, yb - 3.2 - 0.6 * (k % 2), zf), "A", REF)
    g = Geo()
    for k, (xa, xb) in enumerate(((x0 + 2.0, x0 + 5.5), (x0 + 3.2, x0 + 8.4))):   # chains slanting down across the room
        n = 26
        path = [(lerp(xa, xb, i / n), 2.0 + k * 1.5, lerp(zt - 0.3, zf + 0.2, i / n)) for i in range(n + 1)]
        g.use("chain")
        g.tube(path, [0.03 * (1.9 if i % 2 else 0.8) for i in range(n + 1)], segs=5, ref=(0, 1, 0))
    S.add(g, "Chains", R, "SlantChains", "A", REF)
    S.put(S.kit("signlamp_w", lambda: sign_lamp()), "LampPost", R, "SignLamp", place(x1 - 3.4, 4.0, zf), "A", REF)
    P.pad_field(S, R, "FloorPads", x0 + 0.5, x0 + 6.0, -6.0, 9.0, zf, 16, seed=2, facing="up", size=(0.5, 0.9), ev="A", ref=REF)
    P.pad_field(S, R, "FloorPadsR", x1 - 6.5, x1 - 0.5, -6.0, 3.0, zf, 12, seed=5, facing="up", size=(0.5, 0.9), ev="A", ref=REF)
    P.pad_field(S, R, "EdgePads", x0 - 1.0, x1 + 2.0, zf - 2.6, zf - 0.6, info["yf"] - 0.6, 30, seed=3, facing="front", size=(0.6, 1.2), ev="A", ref=REF, layer="FRONT")
    aedicules(S, R, "DoorArch", [x1 - 1.5], 6.0, zf, w=2.4, h=5.2, ref=REF, pendant=False)
    P.creature(S, R, "husk_sentry", "Guard", (x0 + x1) / 2 + 2.6, 1.0, zf + 0.01, rz=0.3, note="a guard in front of the mask; completion")
    S.cam_auto(R, (x0, x1, info["yf"], yb, zf - 2.0, zt + 1.0), ref=REF, views=("front", "closed", "oblique"))
    S.camera("Interior", R, (x1 - 1.6, info["yf"] + 1.6, zf + 1.8), look=(x0 + 6.0, yb, zf + 4.6), lens=18.0, kind="interior", purpose="the great face on the back wall")


def sign_lamp():
    g = Geo()
    g.use("iron")
    g.revolve([(0.2, 0.0), (0.22, 0.06), (0.07, 0.16), (0.045, 1.5), (0.09, 1.58), (0.05, 1.66)], segs=8)
    g.ring_arc((0, 0, 2.2), 0.56, 0, TAU, 0.05, n=22, plane="XZ", segs=5)
    g.spike((0, 0, 2.76), (0, 0, 3.3), 0.05, segs=5, bulb=1.1)
    g.use("lamp_pink")
    g.ellipsoid((0, 0, 2.2), (0.5, 0.16, 0.5), segs=16, steps=8)
    return g


# ============================================================================ WestStreets
def west_streets(S):
    R = "WestStreets"
    REF_T = "05_Streets/Streets_total.jpg; master D1, D2"
    REF_L = "05_Streets/Streets_left.jpg"
    REF_M = "05_Streets/Streets_middle.jpg"
    REF_R = "05_Streets/Streets_right.jpg"
    xa0, xa1 = X(330), X(800)            # low arcade
    xh0, xh1 = X(800), X(1440)           # hall
    y0, y1 = -7.0, 9.0

    # ---- low round-arched arcade (A)
    st = dict(P.STYLES["street"], bay=4.4)
    la = P.stack(S, R, S.el(R, "LowArcade"), st, decor=False, lamps=False, ext_faces=())
    xs = [xa0 + 2.4 + 2.95 * k for k in range(int((xa1 - xa0 - 3.0) / 2.95))]
    aedicules(S, R, "ArcadeBack", xs, la["yb"] - 1.2, ARC_Z, w=2.5, h=4.0, ref=REF_L)
    aedicules(S, R, "ArcadeMid", xs[::2], 2.0, ARC_Z, w=2.5, h=4.0, ref=REF_L, pendant=False)
    drop = S.kit("lampdrop_1.2", lambda: K.k_lamp_string(1, 1.2))
    for k, x in enumerate(xs[1::3]):
        S.put(drop, f"ArcadeLamp_{k}", R, "LampString", place(x, la["yb"] - 1.2, ARC_Z + 3.6), "A", REF_L)

    # ---- hall floor with the well opening under the kiosk, step terrace, stairs (A; stairs C)
    kx = (X(1176) + X(1296)) / 2
    g = Geo()
    for a, b, c, d in ((xh0, kx - 1.6, y0, y1), (kx + 1.6, xh1, y0, y1), (kx - 1.6, kx + 1.6, y0, -1.6), (kx - 1.6, kx + 1.6, 1.6, y1)):
        K.slab(g, a, b, c - 0.3, d, HALL_Z, Z(1448) - Z(1464), "stone", lip=("front",) if c == y0 else (), trim="stone_far_trim")
    st_ = S.el(R, "StepTerrace")
    tx0, tx1, tz = X(st_["map"][0]), X(st_["map"][2]), Z(st_["map"][1])
    g.use("stone")
    g.box(tx0, tx1 - 2.0, y0, y1, HALL_Z, tz)
    P.stairs(g, tx1 - 2.0, tx1 + 1.6, y0, y1, tz, HALL_Z, step=0.5, key="stone")
    g.box(xa1 - 0.6, tx0, y0, y1, ARC_Z - 0.5, ARC_Z)
    P.stairs(g, tx0 - 0.9, tx0, -3.0, 3.0, ARC_Z, tz, step=0.3, key="stone")
    S.add(g, "HallFloor", R, "HallFloor", "A", REF_T)
    g = Geo()
    P.stairs(g, xh1 - 10.6, xh1 - 0.4, 5.6, 8.6, HALL_Z, STN_Z, step=0.52, key="stone")
    S.add(g, "StationStairs", R, "StationStairs", "B", "master D2: the street reaches the raised station at its east end",
          note="the reading notes record steps here; their exact form is completion")
    g = Geo()                                                   # noded pier at the foot of the station (A: Streets_right.jpg, master D2)
    g.use("stone_far_trim")
    zz = HALL_Z
    while zz < STN_Z + 4.0:
        g.ellipsoid((xh1 - 1.4, 0.0, zz + 0.35), (0.85, 0.85, 0.38), segs=12, steps=6, e=0.6)
        zz += 0.66
    S.add(g, "NodedPier", R, "NodedPier", "A", REF_R)

    # ---- cave envelope: back wall, viewer-side arches, sloping stalactite ceiling (A outline, C depth)
    P.rock(S, R, "BackWall", xh0 - 1.0, xh1 + 1.0, y1, y1 + 3.5, HALL_Z - 1.5, Z(1125), ev="C", ref="depth completion", layer=None, amp=1.2)
    g = Geo().use("stone_far")                                   # a thick wall whose top follows the sloping cave roof
    seg = (xh1 - xh0) / 4
    for k in range(4):
        a, b = xh0 + seg * k, xh0 + seg * (k + 1)
        zlo = ceil_z(a) + 0.6
        K.arcade(g, a, b, HALL_Z, zlo, y0 - 1.2, y0, [((a + b) / 2, 7.4, HALL_Z + 3.0, "round", None, None)])
        if ceil_z(b) > ceil_z(a) + 0.05:
            g.prism([(a, zlo), (b, zlo), (b, ceil_z(b) + 0.6)], y0 - 1.2, y0)
        g.box(a - 0.3, a + 0.3, y0 - 1.5, y0 - 1.2, HALL_Z, HALL_Z + 3.0)       # pilaster between the arches
    g.use("stone_far_trim")
    for k in range(4):
        cxk = xh0 + seg * (k + 0.5)
        K.arch_trim(g, cxk, 7.4, HALL_Z + 3.0, HALL_Z, "round", y=y0 - 1.25, r=0.16)
    S.add(g, "FrontArches", R, "FrontArches", "C", REF_T, note="viewer-side closure of the street: great round arches like the ones drawn inside; the wall rises into the cave roof (C)", layer="FRONT")
    g = Geo()                                                    # one rock roof whose underside follows the sloping roof line
    K.rock_roof(g, CEIL[0][0] - 0.6, CEIL[-1][0] + 0.6, y0 - 1.0, y1 + 2.0, lambda x: ceil_z(x) + 0.35, Z(1125), step=1.0, amp=0.35, seed=21)
    S.add(g, "Ceiling", R, "Ceiling", "A", "master D1/D2 stalactite ceiling line", layer="CEILING", smooth=50)
    g = Geo()
    K.stalactite_field(g, xh0 + 0.5, X(1500) - 0.5, y0, y1, lambda x, y: ceil_z(x) + 0.6, 240, seed=5, lmin=0.8, lmax=3.4)
    S.add(g, "Stalactites", R, "Stalactites", "A", REF_T, layer="CEILING", smooth=50)
    lobes(S, R, "CeilLobes", [(lerp(xh0 + 2, xh1 - 6, (k * 0.37) % 1.0), y1 - 0.4 - (k % 3) * 0.6, ceil_z(lerp(xh0 + 2, xh1 - 6, (k * 0.37) % 1.0)) - 1.4 - (k % 4) * 0.7, 0.5 + 0.1 * (k % 3))
                               for k in range(40)], ref=REF_M)
    lobes(S, R, "ColumnLobes", [(-168.6 + 0.4 * (k % 2), 7.0, HALL_Z + 0.95 * k, 0.55) for k in range(15)], ref=REF_M)

    # ---- arcades of the street: aedicule rows on the floor and the great arches high up (A)
    aedicules(S, R, "HallBack", [xh0 + 2.2 + 2.95 * k for k in range(7)], 7.4, HALL_Z, w=2.5, h=4.2, ref=REF_M)
    aedicules(S, R, "TerraceBack", [tx0 + 1.6 + 2.95 * k for k in range(3)], 7.4, tz, w=2.5, h=4.0, ref=REF_L)
    g = Geo()
    hi = [(-176.0, 9.0), (-166.6, 9.0), (-157.2, 9.0)]
    for yy in (6.2,):
        g.use("stone_far")
        K.arcade(g, hi[0][0] - 4.9, hi[-1][0] + 4.9, 154.4, 159.2, yy, yy + 0.45, [(cx, w, 154.45, "round", None, 154.4) for cx, w in hi])
        g.use("stone_far_trim")
        for cx, w in hi:
            K.arch_trim(g, cx, w, 154.45, 154.45, "round", y=yy - 0.03, r=0.12)
        g.use("iron")
        for k in range(4):
            px = hi[0][0] - 4.7 + 9.4 * k
            g.spike((px, yy + 0.2, 154.4), (px, yy + 0.2, 152.6), 0.16, segs=6, bulb=1.2)
            g.ellipsoid((px, yy + 0.2, 154.7), (0.5, 0.3, 0.34), segs=10, steps=6)
    S.add(g, "HighArches", R, "HighArches", "A", REF_M, note="depth position is completion")

    # ---- hanging terraces on chains (A: Streets_middle.jpg, master D2)
    t1, t2 = S.el(R, "Tier1"), S.el(R, "Tier2")
    g = Geo()
    for e_, yy in ((t1, (-3.0, 3.0)), (t2, (-2.4, 2.4))):
        ex0, ex1, ez = X(e_["map"][0]), X(e_["map"][2]), Z(e_["map"][1])
        K.slab(g, ex0, ex1, yy[0], yy[1], ez, 0.6, "stone", lip=("front", "back"), trim="stone_far_trim")
        g.use("stone_far")
        K.arcade(g, ex0 + 0.2, ex1 - 0.2, ez - 2.6, ez - 0.6, yy[0] + 0.1, yy[0] + 0.45, [(ex0 + 0.2 + (ex1 - ex0 - 0.4) * (k + 0.5) / 3, (ex1 - ex0 - 0.4) / 3 - 0.5, ez - 2.55, "round", None, ez - 2.6) for k in range(3)])
        SH.hanging_fringe(g, ex0 + 0.3, ex1 - 0.3, yy[0] + 0.3, ez - 2.6, 1.7, seed=int(ez))
        for cx_ in (ex0 + 0.4, ex1 - 0.4):
            for cy_ in (yy[0] + 0.3, yy[1] - 0.3):
                K.chain(g, cx_, cy_, ez, ceil_z(cx_) + 0.5)
    S.add(g, "HangingTerraces", R, "HangingTerrace", "A", REF_M)
    e2x0, e2x1, e2z = X(t2["map"][0]), X(t2["map"][2]), Z(t2["map"][1])
    aedicules(S, R, "TerraceKiosk", [e2x0 + 1.7, e2x1 - 1.7], 0.0, e2z, w=2.4, h=4.4, ref=REF_M)
    P.lamp(S, R, "Lamp_T2", e2x1 + 1.0, 0.0, Z(t1["map"][1]) if e2x1 + 1.0 < X(t1["map"][2]) else HALL_Z, ref=REF_M)
    hp = S.el(R, "HangPlatform")
    hx0, hx1, hz = X(hp["map"][0]), X(hp["map"][2]), Z(hp["map"][1])
    g = Geo()
    SH.iron_walk(g, hx0, hx1, -2.0, 2.0, hz)
    for cx_ in (hx0 + 0.2, hx1 - 0.2):
        K.chain(g, cx_, 0.0, hz, ceil_z(cx_) + 0.5)
    K.chain(g, hx1 + 2.2, 0.5, hz - 2.2, ceil_z(hx1 + 2.2) + 0.5)
    g.use("iron")
    g.revolve([(1.3, hz - 5.4), (1.4, hz - 5.2), (1.4, hz - 2.4), (1.2, hz - 2.2), (0.1, hz - 2.2)], segs=10, m=place(hx1 + 2.2, 0.5, 0))
    S.add(g, "HangPlatform", R, "HangPlatform", "A", REF_R, note="the hanging basket of jars beside it is read as a counterweight")
    hive_jars(S, R, "PlatformJars", [(hx0 + 0.9 + 1.0 * k, 0.4 * (k % 2), hz) for k in range(4)] + [(hx1 + 2.2 + 0.5 * math.cos(k * 2.1), 0.5 + 0.5 * math.sin(k * 2.1), hz - 2.2) for k in range(3)], REF_R)

    # ---- louvred dome kiosk over the well into the atrium (A kiosk; B that it covers the opening)
    dp = S.el(R, "DomePavilion")
    eave, dtop = Z(dp["roof_to"]), Z(dp["map"][1])
    rx, ry = (X(dp["map"][2]) - X(dp["map"][0])) / 2, 3.6
    g = Geo()
    K.louvre_dome(g, rx, ry, dtop - eave, ribs=10, m=place(kx, 0.0, eave + 0.2))
    g.use("iron")
    for i in range(20):
        a = TAU * i / 20
        g.spike((kx + (rx + 0.1) * math.cos(a), (ry + 0.1) * math.sin(a), eave + 0.2), (kx + (rx + 0.1) * math.cos(a), (ry + 0.1) * math.sin(a), eave + (1.3 if i % 2 == 0 else 0.8)), 0.06, segs=5, bulb=0.9)
    g.use("stone_dark")
    g.revolve([(rx * 1.02, eave - 0.1), (rx * 1.05, eave + 0.2), (rx * 0.9, eave + 0.2)], segs=28, sx=1.0, sy=ry / rx, m=place(kx, 0, 0))
    for a in [TAU * (i + 0.5) / 6 for i in range(6)]:
        SH.scallop_trim(g, -0.9, 0.9, 0.0, eave - 0.12, step=0.9, m=place(kx + rx * 0.98 * math.cos(a), ry * 0.98 * math.sin(a), 0, rz=a + math.pi / 2))
    g.use("iron")                                               # ornate grille round the well mouth
    for i in range(16):
        a = TAU * i / 16
        g.tube([(kx + 1.75 * math.cos(a), 1.75 * math.sin(a), HALL_Z), (kx + 1.75 * math.cos(a), 1.75 * math.sin(a), HALL_Z + 0.95)], 0.03, segs=4, cap=False)
    g.ring_arc((kx, 0, HALL_Z + 0.95), 1.75, 0, TAU, 0.05, n=28, plane="XY", segs=5)
    g.ring_arc((kx, 0, HALL_Z + 0.2), 1.75, 0, TAU, 0.04, n=28, plane="XY", segs=5)
    S.add(g, "Kiosk", R, "DomeKiosk", "A", REF_M, note="read as the head of the well into the green atrium below (B)", smooth=35)
    col = P.kit_column(S, eave - HALL_Z, 0.13, "stone_far_trim")
    for i in range(6):
        a = TAU * (i + 0.5) / 6
        S.put(col, f"Kiosk_Col_{i}", R, "Column", place(kx + rx * 0.92 * math.cos(a), ry * 0.92 * math.sin(a), HALL_Z), "A", REF_M)

    # ---- jars in rows on the terraces and floor, snail shells, lamps (A)
    rand = rng(9)
    jars = [(tx0 + 0.8 + 0.95 * k, 4.6 + 0.3 * (k % 2), tz) for k in range(8)]
    jars += [(xh0 + 9.0 + 0.95 * k, 4.2 + 0.4 * (k % 3), HALL_Z) for k in range(16)]
    jars += [(X(t1["map"][0]) + 0.6 + 0.9 * k, -2.2, Z(t1["map"][1])) for k in range(4)] + [(e2x0 + 0.5 + 0.9 * k, 1.6, e2z) for k in range(3)]
    jars += [(rand(xh0 + 14.0, xh1 - 12.0), rand(-5.5, -1.0), HALL_Z) for _ in range(14)]
    hive_jars(S, R, "Jars", jars, REF_M)
    snail = S.kit("snail_0", lambda: K.k_snail(0.75, 0))
    P.scatter(S, R, snail, "Snail", "SnailShell", [(xh0 + 13.0, 3.0, HALL_Z, 0.3, 1.5), (-159.0, 4.5, HALL_Z, 2.8, 1.6), (-156.0, -3.0, HALL_Z, 0.9, 1.3)], "A", REF_M)
    P.lamp(S, R, "Lamp_0", xh0 + 7.0, 2.5, HALL_Z, ref=REF_L)
    P.lamp(S, R, "Lamp_1", -163.0, -4.4, HALL_Z, ref=REF_R)
    P.lamp(S, R, "Lamp_2", tx0 + 4.0, 1.0, tz, ref=REF_L)
    S.put(S.kit("signlamp_w", lambda: sign_lamp()), "SignLamp", R, "SignLamp", place(-170.5, -3.4, HALL_Z), "A", REF_M)

    box = (xa0, xh1, y0, y1 + 2.0, HALL_Z - 2.0, Z(1125))
    for k, (kind, cx_, cy_, cz_) in enumerate((("resident_0", xh0 + 6.0, -2.5, HALL_Z), ("husk_sentry", xh0 + 14.0, -1.0, HALL_Z), ("resident_1", kx - 7.0, 3.0, HALL_Z),
                                               ("resident_2", kx + 6.0, -2.0, HALL_Z), ("husk_sentry_low", xh1 - 15.0, 1.5, HALL_Z),
                                               ("resident_0", xa0 + 8.0, -3.0, ARC_Z), ("resident_2", xa0 + 16.5, -3.2, ARC_Z))):
        P.creature(S, R, kind, f"Street_{k}", cx_, cy_, cz_ + 0.01, rz=(k * 1.3) % 6.28 - 3.14)
    S.cam_auto(R, box, ref="master D1, D2; 05_Streets/Streets_total.jpg", views=("front", "closed", "oblique", "back"))
    S.camera("Along", R, (tx0 + 2.0, -4.0, tz + 1.8), look=(xh1 - 4.0, 2.0, HALL_Z + 6.0), lens=20.0, kind="interior", purpose="along the street toward the kiosk and the station, compare Streets_middle.jpg", ref=REF_M)
    S.camera("Kiosk", R, (kx - 9.0, -6.0, HALL_Z + 2.4), look=(kx, 0.5, HALL_Z + 3.4), lens=24.0, kind="interior", purpose="dome kiosk and well mouth, compare Streets_right.jpg", ref=REF_R)
    S.camera("Arcade", R, (xa1 - 1.5, -5.0, ARC_Z + 1.6), look=(xa0 + 6.0, 6.0, ARC_Z + 2.0), lens=20.0, kind="interior", purpose="low arcade, compare Streets_left.jpg", ref=REF_L)
    S.camera("FromStation", R, (xh1 - 1.5, -3.6, STN_Z + 3.0), look=(xh0 + 10.0, 2.0, HALL_Z + 3.0), lens=20.0, kind="interior", purpose="back down the street from the station end")


# ============================================================================ WestStation
def west_station(S):
    R = "WestStation"
    REF = "05_Streets/Streets_station.jpg; master C7"
    e = S.el(R, "Hall")
    st = dict(P.STYLES["street"], bay=4.4, fringe=True)
    info = P.stack(S, R, e, st, decor=False, lamps=False, side_open=("L", "R"), ext_faces=())
    x0, x1, yf, yb, zt = info["x0"], info["x1"], info["yf"], info["yb"], info["zt"]
    ta = S.el(R, "TunnelArch")
    tw, th = X(ta["map"][2]) - X(ta["map"][0]), Z(ta["map"][1]) - STN_Z
    yc = (yf + yb) / 2
    g = Geo()                                                    # east end wall with the great arch opening (A: Streets_station.jpg)
    m_end = place(x1, 0, 0, rz=math.pi / 2)
    spring = (th + 0.6) - (tw + 0.3) / 2
    for la, lb, key in ((0.0, 0.14, "stone_far"), (0.14, 0.6, "stone_far")):
        g.use(key)
        K.arcade(g, yf, yb, STN_Z, zt, la, lb, [(yc, tw + 0.3, STN_Z + spring, "round", None, None)], m=m_end)
        g.box(yf, yb, la, lb, info["bottom"], STN_Z, m=m_end)
    S.add(g, "EndWall", R, "Hall", "A", REF, note="east end of the hall with the tunnel arch")
    P.host(S, R, "Podium", (x0, x1, yf, yb, HALL_Z - 1.0, STN_Z - 0.5), ("front", "back"), ev="C", ref="black on master; support under the raised station floor", layer=None, a=0.5)
    g = Geo()
    SH.block_course(g, yb - yf, HALL_Z, STN_Z - 0.5, 0.6, 1.0, 5, place(x0 - 0.1, yf, 0, rz=math.pi / 2), "stone")
    S.add(g, "PodiumFace", R, "PodiumFace", "C", REF, smooth=35)
    # niches with glyph tablets, hanging lamps, jars, bench, bell (A)
    xs = info["bay_x"][:-1]
    tab = [S.kit(f"rune_{v}", lambda v=v: SH.k_rune_tablet(0.75, 2.2 + 0.3 * v, v)) for v in range(3)]
    for k, cx in enumerate(xs):
        g = Geo().use("stone_far_trim")
        w = info["bw"] - 1.0
        kind, rise, spring = P.fit_arch("round", w, zt - STN_Z, 0.4, 1.4)
        K.arch_trim(g, cx, w, STN_Z + spring, STN_Z, kind, rise, y=yb - 0.7, r=0.14)
        S.add(g, f"Niche_{k}", R, "StationNiche", "A", REF)
        for j, dx in enumerate((-0.6, 0.6)):
            S.put(tab[(k + j) % 3], f"Tablet_{k}_{j}", R, "RuneTablet", place(cx + dx, yb - 0.85, zt - 0.3), "A", REF)
    drop = S.kit("lampdrop_1.6", lambda: K.k_lamp_string(1, 1.6))
    for k, cx in enumerate(xs[::2]):
        S.put(drop, f"Lamp_{k}", R, "LampString", place(cx + 1.2, 2.0, zt), "A", REF)
    hive_jars(S, R, "Jars", [(x0 + 4.0 + 1.0 * k, yb - 2.2 - 0.4 * (k % 2), STN_Z) for k in range(18)], REF)
    S.put(S.kit("bench", lambda: K.k_bench()), "Bench", R, "Bench", place(x0 + 13.0, 4.0, STN_Z), "A", REF)
    S.put(S.kit("bell", lambda: K.k_bell()), "Bell", R, "StationBell", place(x1 - 9.2, 3.0, STN_Z), "A", REF)
    S.put(S.kit("signlamp_w", lambda: sign_lamp()), "SignLamp", R, "SignLamp", place(x1 - 7.0, 4.6, STN_Z), "A", REF)
    # the tunnel portal at the east end (A); the line beyond is not built
    g = Geo()
    SH.tunnel_arch(g, tw, th + 0.6, depth=13.0, m=place(x1 - 0.6, yc, STN_Z, rz=-math.pi / 2))
    S.add(g, "TunnelArch", R, "StationPortal", "A", REF, note="portal at the east end of the hall as on Streets_station.jpg; the tunnel runs east, its far end is a closed stub (C)",
          smooth=40)
    lobes(S, R, "PortalLobes", [(x1 + 1.2 + 1.0 * k, yc + (tw / 2 - 0.6) * (1 if k % 2 else -1), STN_Z + 0.3 + 0.7 * k, 0.5) for k in range(4)], ref=REF)
    uc = S.el("WestStreets", "UpperCanopy")
    P.louvre_roof(S, R, "WestCanopy", X(uc["map"][0]), X(uc["map"][2]) + 1.5, zt + 0.5, zt + 0.5 + (Z(uc["map"][1]) - Z(uc["map"][3])), yf - 0.4, yb + 0.4, bays=1, curve_end="W",
                  ev="A", ref="05_Streets/Streets_right.jpg; master D2", note="louvre canopy over the west end of the station; depth is completion")
    for k, (kind, cx_, cy_) in enumerate((("resident_0", x0 + 8.0, 1.0), ("resident_1", x0 + 18.0, 0.0), ("resident_2", x0 + 22.0, 1.5), ("husk_sentry", x1 - 12.0, 0.5))):
        P.creature(S, R, kind, f"Waiting_{k}", cx_, cy_, STN_Z + 0.01, rz=0.4 * (k - 1.5))
    S.cam_auto(R, (x0, x1, yf, yb, HALL_Z - 1.0, zt + 4.0), ref="master C7", views=("front", "closed", "oblique"))
    S.camera("Interior", R, (x0 + 1.5, yf + 1.4, STN_Z + 1.7), look=(x1 - 4.0, yb - 1.0, STN_Z + 2.4), lens=18.0, kind="interior", purpose="station hall, compare Streets_station.jpg", ref=REF)


# ============================================================================ GreenAtrium
def green_atrium(S):
    R = "GreenAtrium"
    REF = "07_Interior/Interior_total.jpg; master A_green_shaft"
    x0, x1 = X(1194), X(1650)
    y0, y1 = -9.0, 13.0
    zf, zt = Z(1989), HALL_Z - (Z(1448) - Z(1464))
    levels = [Z(1809), Z(1713), Z(1620)]
    sx0, sx1 = X(1209), X(1254)                                  # shaft down to the low corridor

    g = Geo()
    for a, b, c, d in ((x0, sx0, y0, y1), (sx1, x1, y0, y1), (sx0, sx1, y0, -2.2), (sx0, sx1, 2.2, y1)):
        K.slab(g, a, b, c - (0.3 if c == y0 else 0.0), d, zf, 0.7, "floor", lip=("front",) if c == y0 else ())
    g.use("wall_green")
    g.box(x0, x1, y1 - 0.6, y1, zf - 0.7, zt)
    K.arcade(g, y0, y1, zf - 0.7, zt, 0.0, 0.8, [(0.0, 5.0, Z(1524) + 1.6, "round", None, Z(1524))], m=place(x0 + 0.8, 0, 0, rz=math.pi / 2))
    bands = [(zf - 0.7, levels[0] - 0.5, zf), (levels[0] - 0.5, levels[1] - 0.5, levels[0]), (levels[1] - 0.5, levels[2] - 0.5, levels[1]), (levels[2] - 0.5, zt, levels[2])]
    for zl, zh, sill in bands:
        K.arcade(g, y0, y1, zl, zh, 0.0, 0.8, [(0.0, 3.4, sill + 2.3, "round", None, sill)], m=place(x1, 0, 0, rz=math.pi / 2))
    # stepped row of small round arches under the roof (A: Interior_upper_left / upper_right)
    n_top = 7
    for yy in (y1 - 1.1,):
        K.arcade(g, x0 + 0.8, x1 - 0.8, zt - 3.4, zt, yy, yy + 0.45, [(x0 + 0.8 + (x1 - x0 - 1.6) * (k + 0.5) / n_top, 3.3, zt - 3.35, "round", None, zt - 3.4) for k in range(n_top)])
    g.use("trim")                                               # great faint arches and rails drawn on the back wall
    for cx, w, zs in ((x0 + 10.0, 9.0, zf + 20.0), (x0 + 20.0, 9.0, zf + 20.0), (x0 + 15.0, 11.0, zf + 9.0)):
        K.arch_trim(g, cx, w, zs, zs - 6.0, "round", y=y1 - 0.68, r=0.12)
    g.tube([(x0 + 1.0, y1 - 0.68, zf + 17.0), (x1 - 1.0, y1 - 0.68, zf + 17.0)], 0.1, segs=5)
    S.add(g, "Shell", R, "AtriumShell", "A", REF, note="depth of the atrium is completion")
    g = Geo().use("wall_green")
    K.arcade(g, x0, x1, zf - 0.7, zt, y0, y0 + 0.6, [(x0 + (x1 - x0) * (k + 0.5) / 3, 7.6, zt - 9.0, "round", None, zf) for k in range(3)])
    S.add(g, "Front", R, "AtriumShell", "C", REF, note="viewer-side wall with tall openings: completion", layer="FRONT")

    # ---- cables and hanging platforms (A)
    ce = S.el(R, "Cables")
    ys = [-2.0, 3.5, 0.0, 5.5, 1.5]
    col_y = {round(X(mx), 2): ys[i] for i, mx in enumerate(ce["xs"])}
    g = Geo().use("iron")
    for mx in ce["xs"]:
        for dx in (-1.0, 1.0):
            g.tube([(X(mx) + dx, col_y[round(X(mx), 2)], zf + 0.3), (X(mx) + dx, col_y[round(X(mx), 2)], zt)], 0.022, segs=4, cap=False)
    S.add(g, "Cables", R, "Cables", "A", "07_Interior/Interior_centre.jpg", note="depth positions are completion")
    g = Geo()
    plats = []
    for mx, my in S.el(R, "HangPlatforms")["items"]:
        px, py, pz = X(mx), col_y[round(X(mx), 2)], Z(my)
        SH.hang_platform(g, px, py, pz, pz + 0.05)
        plats.append((px, py, pz))
    S.add(g, "HangPlatforms", R, "HangPlatform", "A", "master A_green_shaft; 07_Interior/*", smooth=40)
    hive_jars(S, R, "PlatformJars", [(px + 0.3, py, pz) for px, py, pz in plats[::3]], "07_Interior/Interior_centre.jpg")

    # ---- the two louvre canopies at the foot with their windowed passages (A)
    for name, key, curve in (("DomeLeft", "DomeLeft", "E"), ("DomeRight", "DomeRight", "W")):
        e = S.el(R, key)
        cx0, cx1, czb, czt = X(e["map"][0]), X(e["map"][2]), Z(e["map"][3]), Z(e["map"][1])
        if curve == "W":
            cx1 -= 0.9
        P.louvre_roof(S, R, name, cx0, cx1, czb, czt, 3.0, y1 - 0.7, bays=max(1, int((cx1 - cx0) / 3.6)), curve_end=curve, ev="A", ref=e["ref"], note="depth is completion")
        n = max(2, int((cx1 - cx0) / 2.8))
        col = P.kit_column(S, czb - zf - 0.26, 0.12, "trim")
        win = P.kit_window(S, "lancet", 1.4, czb - zf - 0.9, "glass_blue")
        for k in range(n + 1):
            S.put(col, f"{name}_Col_{k}", R, "Column", place(lerp(cx0 + 0.4, cx1 - 0.4, k / n), 3.2, zf), "A", e["ref"])
        for k in range(n):
            S.put(win, f"{name}_Win_{k}", R, "WindowLancet", place(lerp(cx0, cx1, (k + 0.5) / n), y1 - 0.72, zf + 0.4), "A", e["ref"])
        S.put(S.kit("lampdrop_1.2", lambda: K.k_lamp_string(1, 1.2)), f"{name}_Lamp", R, "LampString", place((cx0 + cx1) / 2, 7.0, czb - 0.26), "A", e["ref"])

    # ---- balconies on the east side with spiked rails and feathered brackets, rooms behind (A)
    REF_B = "07_Interior/Interior_middle_right.jpg; master A_green_shaft"
    g = Geo()
    runs = []
    for i, zl in enumerate(levels):
        bx0 = X(1587)
        K.slab(g, bx0, x1 - 0.8, -3.2, 3.2, zl, 0.6, "floor", lip=("front", "back", "left"))
        A.add_corbel_wing(g, place(bx0 + 0.6, 0.0, zl - 0.62, rz=math.pi), length=2.2, blades=5, key="louvre_frame")
        SH.hanging_fringe(g, bx0 + 0.3, x1 - 1.0, -2.9, zl - 0.6, 1.5, seed=i)
        runs += [((bx0 + 0.15, -3.0), (bx0 + 0.15, 3.0), zl), ((bx0 + 0.15, -3.0), (x1 - 0.9, -3.0), zl), ((bx0 + 0.15, 3.0), (x1 - 0.9, 3.0), zl)]
    ul = S.el(R, "UpperLeftLedge")
    uz = Z(ul["map"][1])
    K.slab(g, x0 + 0.8, X(ul["map"][2]), -3.0, 3.0, uz, 0.5, "floor", lip=("front", "back", "right"))
    g.use("wall_green")
    g.box(x0 - 4.2, x0, -3.4, 3.4, uz - 0.5, uz)
    g.box(x0 - 4.8, x0 - 4.2, -3.4, 3.4, uz - 0.5, zt)
    runs.append(((X(ul["map"][2]) - 0.15, -2.8), (X(ul["map"][2]) - 0.15, 2.8), uz))
    S.add(g, "Balconies", R, "AtriumBalcony", "A", REF_B)
    P.spike_rail(S, R, "BalconyRails", runs, ev="A", ref=REF_B)
    green = dict(P.STYLES["green"], fringe=True)
    br_i = P.stack(S, R, S.el(R, "BalconyRooms"), green, ext_faces=("N",))
    bc_i = P.stack(S, R, S.el(R, "BottomCorridor"), dict(green, bay=3.6), ext_faces=("N",))
    P.populate(S, R, "Balcony", br_i, ["resident_0", "resident_2", "lance_sentry"], 3, seed=16)
    P.populate(S, R, "Bottom", bc_i, ["resident_1", "husk_sentry"], 2, seed=17)

    # ---- rock column of lobes, spotted pads heaped at the bottom, medallions, shells, jars (A)
    rc = S.el(R, "RockColumn")
    P.rock(S, R, "RockColumn", X(rc["map"][0]), X(rc["map"][2]), 6.0, 12.4, Z(rc["map"][3]) - 5.0, Z(rc["map"][1]), ev="A", ref=rc["ref"], layer=None, amp=1.3)
    lobes(S, R, "ColumnLobes", [(X(rc["map"][0]) + 2.2 + 0.6 * (k % 3), 6.4, Z(rc["map"][3]) - 4.0 + 1.9 * k, 0.75) for k in range(13)], ref=rc["ref"])
    P.pad_field(S, R, "PadsBack", x0 + 1.0, x1 - 1.0, zf + 0.4, zf + 15.0, y1 - 0.8, 190, seed=11, facing="front", size=(0.7, 1.5), ev="A", ref="07_Interior/Interior_centre.jpg",
                keep=lambda a, b: b < zf + 15.0 - 6.0 * abs(a - (x0 + x1) / 2) / (x1 - x0) and not (a < X(1380) + 0.5 and b < Z(1884) + 0.5) and not (a > X(1578) - 0.5 and b < Z(1860) + 0.5))
    P.pad_field(S, R, "PadsFloor", X(1390), X(1570), 3.0, 11.5, zf, 40, seed=12, facing="up", size=(0.6, 1.2), ev="A", ref="07_Interior/Interior_middle_bottom.jpg")
    med = S.kit("medallion", lambda: SH.k_medallion())
    for k, (mx, mz, s) in enumerate(((x0 + 11.0, zf + 24.0, 1.0), (x0 + 19.5, zf + 28.5, 0.8), (x0 + 17.0, zf + 16.5, 0.9), (x0 + 8.0, zf + 31.0, 0.7))):
        S.put(med, f"Medallion_{k}", R, "Medallion", place(mx, y1 - 0.75, mz, s=s), "A", "07_Interior/Interior_centre.jpg; Interior_middle_upper.jpg")
    snail = S.kit("snail_0", lambda: K.k_snail(0.75, 0))
    P.scatter(S, R, snail, "Snail", "SnailShell", [(X(1500), 2.0, zf, 0.4, 1.5), (X(1545), 5.0, zf, 2.7, 1.7), (X(1470), 6.0, zf, 1.4, 1.2)], "A", "07_Interior/Interior_bottom_right.jpg")
    rand = rng(13)
    hive_jars(S, R, "FloorJars", [(rand(X(1390), X(1640)), rand(-3.0, 6.0), zf) for _ in range(16)], "07_Interior/Interior_bottom_right.jpg")
    g = Geo()
    K.stalactite_field(g, x0 + 2.0, x1 - 6.0, 9.0, 12.2, lambda x, y: zf + 17.2, 40, seed=7, lmin=0.6, lmax=2.2, key="wall_green")
    S.add(g, "Stalactites", R, "Stalactites", "A", "07_Interior/Interior_centre.jpg", note="hang from the rail drawn across the back wall", smooth=50)
    P.spike_rail(S, R, "FloorRail", [((X(1390), y0 + 0.3), (x1 - 1.0, y0 + 0.3), zf)], ev="A", ref="07_Interior/Interior_bottom_right.jpg", layer="FRONT")

    S.cam_auto(R, (x0, X(1905), y0, y1, zf - 1.5, zt + 1.0), ref="master A_green_shaft; 07_Interior/Interior_total.jpg", views=("front", "closed", "oblique", "back"))
    S.camera("FromFloor", R, (x0 + 4.0, -6.0, zf + 1.8), look=(x1 - 6.0, 9.0, zf + 16.0), lens=18.0, kind="interior", purpose="up through the platforms from the floor, compare Interior_centre.jpg", ref="07_Interior/Interior_centre.jpg")
    S.camera("FromBalcony", R, (x1 - 2.0, 0.0, levels[2] + 1.7), look=(x0 + 6.0, 6.0, zf + 10.0), lens=18.0, kind="interior", purpose="from the top balcony across the atrium", ref=REF_B)
    S.camera("Canopy", R, (X(1420), -5.0, zf + 1.8), look=(X(1260), 9.0, zf + 3.0), lens=20.0, kind="interior", purpose="left canopy and its passage, compare Interior_bottom_left.jpg", ref="07_Interior/Interior_bottom_left.jpg")
    S.camera("Down", R, (x0 + 6.0, -6.0, zt - 3.0), look=(x0 + 20.0, 8.0, zf + 4.0), lens=18.0, kind="interior", purpose="down from under the roof arches")


# ============================================================================ WestLowCorridor
def west_low_corridor(S):
    R = "WestLowCorridor"
    REF = "master B5 (no local screenshot)"
    st = dict(P.STYLES["corridor"], bay=4.6, fringe=True, back=("blind", "niche"), lamp="string")
    ce = dict(S.el(R, "Corridor"))
    ce["voids"] = list(ce["voids"]) + [[1173, 1300, 2195, 2215, 1], [1183, 1288, 2100, 2122, 1]]   # lower floor; open ceiling into the well (A: master B5)
    c = P.stack(S, R, ce, st, ext_faces=(), keep_clear=[(0, X(1173) - 1.2, X(1300) + 1.2, -9.0, 12.0)])
    P.populate(S, R, "Corridor", c, ["resident_0", "resident_1", "husk_sentry"], 4, seed=18)
    # sunken middle room under the atrium shaft: floor 1.8 lower, two steps down at each end, walls to the new floor
    px0, px1, pz = X(1173), X(1300), Z(2230)
    zf = c["floors"][0]
    g = Geo()
    K.slab(g, px0, px1, c["yf"] - 0.3, c["yb"] - 0.6, pz, 0.5, "floor", lip=("front",), trim="trim")
    g.use("wall_deep")
    for xa, xb in ((px0 - 0.4, px0), (px1, px1 + 0.4)):
        g.box(xa, xb, c["yf"], c["yb"], pz - 0.5, zf - 0.5)
    g.box(px0, px1, c["yb"] - 0.6, c["yb"], pz - 0.5, zf - 0.5)
    for sgn, xe in ((1, px0), (-1, px1)):
        for k in range(2):
            xa = xe + sgn * 0.9 * k
            g.use("floor")
            g.box(min(xa, xa + sgn * 0.9 * (2 - k)), max(xa, xa + sgn * 0.9 * (2 - k)), c["yf"] + 0.6, c["yf"] + 3.4, pz, pz + 0.6 * (2 - k))
    S.add(g, "SunkenRoom", R, "SunkenRoom", "A", "master B5 enlarged: the middle room of the corridor lies lower, under the shaft",
          note="depth of the drop read from the master; steps are completion")
    g = Geo().use("stone_far")
    g.box(px0 - 0.4, px1 + 0.4, c["yf"], c["yf"] + 0.6, pz - 0.5, zf)
    S.add(g, "SunkenRoom_Front", R, "SunkenRoom", "C", REF, note="viewer-side wall of the sunken room", layer="FRONT")
    # the well over the middle room (A: master B5 shows the room rising into a wide shaft); the climbing shaft starts at its top
    wx0, wx1, wz0, wz1 = X(1183), X(1288), c["zt"] - 0.05, Z(2040)
    g = Geo().use("wall_deep")
    for xa, xb in ((wx0 - 0.4, wx0), (wx1, wx1 + 0.4)):
        g.box(xa, xb, c["yf"], c["yb"], wz0, wz1)
    g.box(wx0, wx1, c["yb"] - 0.4, c["yb"], wz0, wz1)
    for xa, xb in ((wx0 - 0.4, X(1209)), (X(1254), wx1 + 0.4)):    # cap over the well, open under the climbing shaft
        g.box(xa, xb, c["yf"], c["yb"], wz1, wz1 + 0.5)
    SH.hanging_fringe(g, wx0 + 0.2, wx1 - 0.2, c["yb"] - 0.5, wz1 - 0.1, 1.8, seed=81)
    S.add(g, "MiddleWell", R, "SunkenRoom", "A", "master B5: the middle room continues up as a wide shaft", note="its height is read from the master; the top is completion (C)")
    g = Geo().use("stone_far")
    g.box(wx0 - 0.4, wx1 + 0.4, c["yf"], c["yf"] + 0.4, wz0, wz1 + 0.5)
    S.add(g, "MiddleWell_Front", R, "SunkenRoom", "C", REF, note="viewer-side wall of the well", layer="FRONT")
    g = Geo()                                                    # uneven corridor ceiling: rock lumps and a deeper ragged fringe (A: master B5)
    rand = rng(83)
    for k in range(10):
        xa = lerp(c["x0"] + 2.0, c["x1"] - 2.0, (k + 0.5) / 10) + rand(-1.5, 1.5)
        if wx0 - 2.5 < xa < wx1 + 2.5:
            continue
        K.rock(g, xa - rand(1.6, 2.6), xa + rand(1.6, 2.6), c["yf"] + 0.8, c["yb"] - 0.6, c["zt"] - rand(0.4, 0.9), c["zt"] - 0.05, seed=300 + k, amp=0.35, key="wall_deep")
    for k, (xa, xb) in enumerate(((c["x0"] + 1.0, wx0 - 1.0), (wx1 + 1.0, c["x1"] - 1.0))):     # clusters of dark points under the ceiling (A: master B5)
        K.stalactite_field(g, xa, xb, c["yf"] + 0.8, c["yb"] - 0.8, lambda x, y: c["zt"] - 0.35, 26 if k == 0 else 34, seed=85 + k, lmin=0.6, lmax=2.4, key="wall_deep")
    S.add(g, "CeilingLumps", R, "CeilingRock", "C", REF, note="uneven ceiling read from the master; form is completion")
    P.stack(S, R, S.el(R, "LowerRoom"), st, ext_faces=())
    for eid in ("ShaftUp", "ShaftDown", "LinkStub"):
        e = dict(S.el(R, eid))
        if eid == "ShaftUp":
            e["map"] = [e["map"][0], e["map"][1], e["map"][2], 2040]    # starts at the top of the well
        P.lift(S, R, e, back="plain", car=None, closed=True, ev=e["ev"], ref=e["ref"], panels=[Z(e["map"][3]) + 0.6] if Z(e["map"][1]) - Z(e["map"][3]) > 4.5 else ())
        g = Geo().use("iron")                                    # rungs: these are climbing shafts, not lifts (no car on the master)
        x0, x1, zb, zt = X(e["map"][0]), X(e["map"][2]), Z(e["map"][3]), Z(e["map"][1])
        zz = zb + 0.5
        while zz < zt:
            g.tube([(x0 + 0.5, 1.9, zz), (x1 - 0.5, 1.9, zz)], 0.035, segs=4)
            zz += 0.5
        S.add(g, eid + "_Rungs", R, "ShaftRungs", "C", e["ref"], note="how the shaft is climbed is not shown; rungs are completion")
    g = Geo()                                                    # chains slanting down through the corridor (A: master B5)
    for k, (xa, xb) in enumerate(((c["x0"] + 3.0, c["x0"] + 12.0), (c["x1"] - 14.0, c["x1"] - 4.0), ((px0 + px1) / 2 - 6.0, (px0 + px1) / 2 + 2.0))):
        n = 26
        path = [(lerp(xa, xb, i / n), 3.0 + 1.6 * k, lerp(c["zt"] - 0.3, (pz if k == 2 else zf) + 0.4, i / n)) for i in range(n + 1)]
        g.use("chain")
        g.tube(path, [0.03 * (1.9 if i % 2 else 0.8) for i in range(n + 1)], segs=5, ref=(0, 1, 0))
    S.add(g, "Chains", R, "SlantChains", "A", REF)
    snail = S.kit("snail_0", lambda: K.k_snail(0.75, 0))
    P.scatter(S, R, snail, "Snail", "SnailShell", [(X(1232) + 2.6, 3.5, pz, 0.5, 1.2), (X(1232) - 2.4, 4.6, pz, 2.2, 1.1)], "A",
              "master B5: snail shells in the sunken middle room")
    box = (c["x0"], c["x1"], c["yf"], c["yb"], Z(2428), Z(2040) + 1.5)      # up to the top of the middle well
    S.cam_auto(R, box, ref=REF, views=("front", "closed", "oblique"))
    S.camera("Interior", R, (c["x0"] + 1.5, c["yf"] + 1.4, c["floors"][0] + 1.7), look=(c["x1"] - 4.0, c["yb"] - 1.0, c["floors"][0] + 2.0), lens=18.0, kind="interior", purpose="lamp-hung corridor")
    S.camera("Context", R, (c["x0"] - 14.0, c["yf"] - 40.0, c["zt"] + 10.0), look=((c["x0"] + c["x1"]) / 2, 3.0, c["floors"][0]), lens=24.0, kind="view",
             hide=("BACKDROP", "CAVESHELL"), purpose="the corridor with the host rock and buildings round it (nothing hidden but the far layers)")


REGIONS = {"WestFaceChamber": west_face_chamber, "WestStreets": west_streets, "WestStation": west_station, "GreenAtrium": green_atrium,
           "WestLowCorridor": west_low_corridor}
