"""Stage 3 structure: LeftWell (left rain well with its west block, lift, iron frames and shell towers) and
SouthwestCave (the cluster cave with the shell hut)."""
import math

import cot_assets as A
import cot_kit as K
import cot_parts as P
import cot_shell as SH
from cot_geo import Geo, IronCurves, TAU, fbm, lerp, place, rng
from cot_s3 import X, Z

GROUND = Z(3581)          # 1.27: quay level of the west wells
WATER = Z(3608)           # -0.53
BED = Z(3625)             # -1.67


# ============================================================================ LeftWell
def left_well(S):
    R = "LeftWell"
    REF_T = "03_Left_City/Left_City_total.jpg; master A_left_well_lower"
    REF_LB = "03_Left_City/Left_City_left_bottom.jpg"
    REF_M = "03_Left_City/Left_City_middle.jpg; 15_Background/Background_01.jpg"

    # ---- west block: blue lancet interiors over a black fringed underside (A)
    wb = P.stack(S, R, S.el(R, "WestBlock"), "blue", ext_faces=("R", "N"))
    wl = P.stack(S, R, S.el(R, "WestBlockLower"), "blue", ext_faces=("R", "N"), levels={0: dict(back=("niche", "lancet"))})
    P.lift(S, R, S.el(R, "WestBlockShaft"), back="chevron", ref="master B5")
    for k, py in enumerate((wb["yf"] + 1.2, 3.5, wb["yb"] - 1.2)):
        evk = "A" if k == 0 else "C"
        P.glass_pillar(S, R, f"GlassPillarUpper_{k}", wb["x1"] + 0.8, py, 0.8, Z(3100), Z(2440), evk, "03_Left_City/Left_City_left_upper.jpg")
        P.glass_pillar(S, R, f"GlassPillarLower_{k}", wl["x1"] + 0.75, py, 0.72, Z(3243), Z(3135), evk, "master A_left_well_lower")
    g = Geo()
    SH.hanging_fringe(g, wl["x0"] + 0.5, wl["x1"] - 0.3, wl["yf"] + 0.3, wl["bottom"], 2.6, seed=3)
    SH.hanging_fringe(g, wl["x0"] + 0.5, wl["x1"] - 0.3, wl["yb"] - 0.3, wl["bottom"], 2.2, seed=4)
    SH.hanging_fringe(g, wl["yf"] + 0.3, wl["yb"] - 0.3, wl["x1"] - 0.3, wl["bottom"], 2.4, seed=5, axis="Y")
    S.add(g, "WestBlock_UnderFringe", R, "UndersideFringe", "A", REF_T)

    # ---- the open lift: iron frame of pointed arches, spired car on chains (A: left_bottom / left_middle)
    le = S.el(R, "Elevator")
    lx0, lx1, lzt = X(le["map"][0]) - 0.25, X(le["map"][2]) + 0.25, Z(le["map"][1])
    tiers = [GROUND + 3.4 + 4.3 * k for k in range(5) if GROUND + 3.4 + 4.3 * k < lzt - 1.0]
    P.scaffold(S, R, "LiftFrame", [(x, y, GROUND, lzt) for x in (lx0, lx1) for y in (-1.6, 1.6)],
               [(lx0, y, lx1, y, tiers, None, None, 0.3) for y in (-1.6, 1.6)] + [(x, -1.6, x, 1.6, tiers[::2], None, None, 0.3) for x in (lx0, lx1)],
               "A", REF_LB, note="open frame of the exterior lift; depth is completion")
    cx = (lx0 + lx1) / 2
    S.put(S.kit("car_spire", lambda: K.k_car_spire()), "Lift_Car", R, "LiftCarSpire", place(cx, 0.0, GROUND + 0.12), "A", REF_LB)
    g = Geo()
    for dx in (-0.35, 0.35):
        K.chain(g, cx + dx, 0.0, GROUND + 5.2, lzt)
    g.use("iron")
    g.tube([(cx - 0.35, 0, GROUND + 5.25), (cx, 0, GROUND + 6.3), (cx + 0.35, 0, GROUND + 5.25)], 0.03, segs=4, ref=(0, 1, 0))
    S.add(g, "Lift_Chains", R, "LiftChain", "A", REF_LB)

    # ---- ground: west quay, rubble wall, piers, water, ring posts, lamps
    g = Geo()
    g.use("stone_dark")
    g.box(X(1300), X(1520), -9.0, 14.0, Z(3640), GROUND - 0.3)
    A.add_cobbles(g, X(1300), X(1520), -9.0, 14.0, GROUND, size=(1.0, 0.8), seed=11, key="cobble", height=0.3)
    A.add_stone_course(g, X(1300), X(1520), -9.3, -8.9, BED, GROUND - 0.25, block=1.0, seed=12, key="stone")
    A.add_stone_course(g, X(1520) - 0.2, X(1520) + 0.2, -9.0, 14.0, BED, GROUND - 0.25, block=0.5, seed=13, key="stone")
    S.add(g, "GroundWest", R, "QuayWest", "A", REF_LB, smooth=35)
    g = Geo()
    rand = rng(21)
    z = GROUND
    while z < wl["bottom"] - 0.6:                              # broken rubble wall behind the lift
        x = X(1300) + rand(0.0, 0.5)
        while x < lx0 - 0.9:
            w = rand(0.9, 1.5)
            if rand() > 0.22:
                g.use("stone")
                g.ellipsoid((x + w / 2, 4.2 + rand(-0.2, 0.2), z + 0.3), (w * 0.5, 0.9, 0.31), segs=8, steps=5, e=0.45)
            x += w
        z += 0.6
    g.use("stone_dark")
    g.box(X(1300), lx0 - 1.0, 4.6, 14.0, GROUND, wl["bottom"])
    S.add(g, "LiftWall", R, "RubbleWall", "A", "03_Left_City/Left_City_left_middle.jpg", note="rubble courses behind the lift; extent in depth is completion", smooth=35)
    P.rock(S, R, "Bed", X(1520), X(2700), -14.0, 40.0, Z(3680), BED, ev="C", ref="well floor under the water line", layer=None, amp=0.5)
    P.water(S, R, "Water", X(1520), X(2700), -14.0, 40.0, WATER, "A", "03_Left_City/Left_City_middle_bottom.jpg")
    piers = [(X(a), X(b), Z(t)) for a, b, t in S.el(R, "Piers")["items"]]
    g = Geo()
    for i, (xa, xb, zt) in enumerate(piers):
        P.stone_pier(g, xa, xb, -2.5, 2.5, BED, zt, seed=30 + i)
    S.add(g, "Piers", R, "StonePiers", "A", "master A_left_well_lower; 03_Left_City/Left_City_left_bottom.jpg", smooth=35)
    lamps = [(X(1335), 1.0, GROUND), ((piers[0][0] + piers[0][1]) / 2, 0.0, piers[0][2]), ((piers[2][0] + piers[2][1]) / 2, 0.0, piers[2][2]),
             (piers[4][0] + 2.0, 0.0, piers[4][2]), (piers[4][1] - 2.0, 0.0, piers[4][2])]
    for i, (x, y, z) in enumerate(lamps):
        P.lamp(S, R, f"Lamp_{i}", x, y, z, ev="A", ref=REF_T)
    rand = rng(41)
    P.ring_posts(S, R, "RingPost", [(rand(X(1540), X(2680)), rand(-9.0, -3.5), -2.4, rand(0.7, 0.95)) for _ in range(26)])

    # ---- stone arcade wall with a railing and lamps (A: middle_bottom)
    aw = S.el(R, "ArcadeWall")
    ax0, ax1, top = X(aw["map"][0]), X(aw["map"][2]), Z(aw["map"][1])
    objs = A.build_viaduct(S.coll(R), S.mat, "ArcadeWall", ax0, ax1, -1.75, 1.75, BED + 0.5, top, [ax0 + (ax1 - ax0) * (k + 0.5) / 3 for k in range(3)],
                           arch_w=2.3, spring=WATER + 2.4, props=None)
    S.adopt(objs, R, "ArcadeWall", "A", "03_Left_City/Left_City_middle_bottom.jpg")
    for j, yy in enumerate((-1.95, 1.95)):
        P.railing(S, R, f"ArcadeWall_Rail_{j}", (ax0, yy), (ax1, yy), top, ref="03_Left_City/Left_City_middle_bottom.jpg")
    P.lamp(S, R, "Lamp_Arcade", (ax0 + ax1) / 2, 0.0, top, ev="A", ref="03_Left_City/Left_City_middle_bottom.jpg")

    # ---- iron frames with walkways (A)
    def xs_of(eid):
        e = S.el(R, eid)
        n = e["posts"]
        return [X(e["map"][0]) + (X(e["map"][2]) - X(e["map"][0])) * i / (n - 1) for i in range(n)], [Z(t) for t in e["tiers"]], Z(e["map"][3])

    xa, ta, _ = xs_of("ScaffoldA")
    P.iron_frame(S, R, "ScaffoldA", xa, -1.5, 1.5, top, ta, ev="A", ref=REF_M)
    xb, tb, _ = xs_of("ScaffoldB")
    P.iron_frame(S, R, "ScaffoldB", xb, 2.6, 5.6, BED, tb, extra_tiers=[tb[0] - 5.0, tb[0] - 10.0], ev="A", ref=REF_M, note="stands one layer behind frame A (C)")
    xc, tc, _ = xs_of("ScaffoldC")
    P.iron_frame(S, R, "ScaffoldC", xc, 2.6, 5.6, tb[0], tc, extra_tiers=[tc[0] - 4.2], ev="A", ref=REF_M)
    xd, td, _ = xs_of("ScaffoldD")
    P.iron_frame(S, R, "ScaffoldD", xd, -1.5, 1.5, BED, td, ev="A", ref="15_Background/Background_02.jpg; 03_Left_City/Left_City_middle.jpg")
    xe, te, _ = xs_of("ScaffoldE")
    P.iron_frame(S, R, "ScaffoldE", xe, -1.5, 1.5, piers[0][2], te, ev="A", ref=REF_LB)

    # ---- floating stone platforms (A low / B high)
    for eid, ev in (("FloatingLow", "A"), ("FloatingHigh", "B")):
        g = Geo()
        rand = rng(51 if ev == "A" else 52)
        for i, (mx, my) in enumerate(S.el(R, eid)["items"]):
            SH.float_slab(g, X(mx), rand(-2.2, 2.8), Z(my), w=rand(1.8, 2.6), d=1.5, seed=i, spear=(i % 3 == 0))
        S.add(g, eid, R, "FloatingPlatform", ev, S.el(R, eid)["ref"], note="depth positions are completion", smooth=35)

    # ---- shell towers on the east side of the well, with louvre roofs / hoods and the high balcony (A)
    REF_ST = "03_Left_City/Left_City_right_bottom.jpg; Left_City_right_middle.jpg; master B3_central_lower"
    P.tower(S, R, "ShellTowerLower", X(2425.5), 2.0, -1.5, Z(2678), 8.1, windows=14, roof="flat", seed=21, leaf=(2.8, 7.2), ev="A", ref=REF_ST)
    P.tower(S, R, "ShellTowerUpper", X(2529), 2.0, Z(2641), Z(2200), 7.8, windows=9, roof="dome", seed=22, leaf=(2.8, 7.0), ev="A", ref="master B3_central_lower")
    P.louvre_roof(S, R, "ShellTowerLower_Roof", X(2290), X(2550), Z(2678), Z(2641), -6.5, 10.5, bays=3, curve_end="W", ev="A", ref="master B3_central_lower",
                  note="louvre roof on the lower shell tower; depth is completion")
    for k, (mx, my, rr) in enumerate(((2440, 2439, 2.6), (2330, 2948, 2.8))):   # louvred hoods on slim turrets against the towers
        hx, hz = X(mx), Z(my)
        g = Geo()
        K.louvre_dome(g, rr, rr, rr * 0.9, ribs=8, m=place(hx, -4.6, hz))
        g.use("louvre_frame")
        g.revolve([(rr * 0.5, hz - 9.0), (rr * 0.42, hz - 8.6), (rr * 0.36, hz - 1.2), (rr * 0.7, hz - 0.6), (rr * 1.0, hz - 0.2), (rr * 1.04, hz)], segs=16, m=place(hx, -4.6, 0))
        A.add_corbel_wing(g, place(hx, -5.0, hz - 9.0, rz=-math.pi / 2), length=1.6, blades=4, key="louvre_frame")
        S.add(g, f"TowerHood_{k}", R, "LouvreHood", "A", "master B3_central_lower", note="depth position is completion", smooth=35)
    hb = S.el(R, "HighBalcony")
    bz = Z(hb["map"][1])
    g = Geo()
    BX, EX = X(2547) - 0.4, -64.7                               # west face of the central block's dark band; end of the facade's first bay
    K.slab(g, X(hb["map"][0]), BX, -12.6, -6.0, bz, 0.7, "stone", lip=("front", "left"), trim="stone_far_trim")
    K.slab(g, BX, EX, -12.6, -10.25, bz, 0.7, "stone", lip=("front",), trim="stone_far_trim")
    for xk in (X(hb["map"][0]) + 0.8, -90.0, -84.0):
        K.corbel(g, xk, -6.4, bz - 0.7, size=2.6, key="stone_far_trim", facing=1)
    for xk in (-77.0, -72.0, -66.5):
        K.corbel(g, xk, -10.4, bz - 0.7, size=1.8, key="stone_far_trim", facing=1)
    SH.hanging_fringe(g, X(hb["map"][0]) + 0.3, EX - 0.3, -12.3, bz - 0.7, 1.6, seed=9)
    S.add(g, "HighBalcony", R, "HighBalcony", "A", "03_Left_City/Left_City_right_upper.jpg; Left_City_right_middle.jpg",
          note="runs in front of the shell tower and the dark band to the first bay of the central block's facade, whose floor is level with it (B)")
    P.spike_rail(S, R, "HighBalcony_Rail", [((X(hb["map"][0]), -12.4), (EX - 0.1, -12.4)), ((X(hb["map"][0]), -12.4), (X(hb["map"][0]), -9.8)), ((EX - 0.1, -12.4), (EX - 0.1, -10.4))], z=bz, ev="A",
                 ref="03_Left_City/Left_City_right_upper.jpg")

    # ---- spotted cluster masses (A): the column by the lift and the rock under the upper bridge
    REF_C = "03_Left_City/Left_City_left_bottom.jpg; Left_City_left_middle.jpg"
    wbl = S.el(R, "WestBlockLower")                        # the column carries the west block: it stops under its lowest floor slab
    cz1 = Z(max(wbl.get("floors", [wbl["map"][3]]))) - 0.5
    P.rock(S, R, "ClusterColumn", -148.6, -140.0, 0.5, 6.5, 0.0, cz1 - 1.0, ev="A", ref=REF_C, layer=None, amp=1.4)
    P.pad_field(S, R, "ClusterColumn_Pad", -149.5, -139.0, 0.5, cz1 - 0.6, 0.4, 130, seed=3, facing="front", size=(0.5, 1.0), ev="A", ref=REF_C)
    sr = S.el(R, "SpottedRock")
    sx0, sx1, sz0, sz1 = X(sr["map"][0]), X(sr["map"][2]), Z(sr["map"][3]), Z(sr["map"][1])
    P.rock(S, R, "SpottedRock", sx0, sx1, -6.0, 12.0, sz0, sz1, ev="A", ref=sr["ref"], layer=None, amp=1.6)
    P.pad_field(S, R, "SpottedRock_PadF", sx0 - 0.5, sx1 + 0.5, sz0 - 1.0, sz1, -6.2, 150, seed=5, facing="front", size=(0.6, 1.2), ev="A", ref=sr["ref"])
    P.pad_field(S, R, "SpottedRock_PadE", -6.0, 12.0, sz0, sz1, sx1 + 0.2, 110, seed=6, facing="east", size=(0.6, 1.2), ev="C", ref=sr["ref"])
    bc = S.el("GreenAtrium", "BottomCorridor")                # its east end abuts the rock's west face: no pads into that room
    bz0, bz1 = Z(bc["map"][3]) - 0.6, Z(bc["map"][1]) + 0.6
    P.pad_field(S, R, "SpottedRock_PadW", -6.0, 12.0, sz0, sz1, sx0 - 0.2, 110, seed=7, facing="west", size=(0.6, 1.2), ev="C", ref=sr["ref"],
                keep=lambda a, b: not (bz0 < b < bz1))

    # ---- towers behind and in front of the well (B / C)
    for eid, seed in (("BackTowerA", 31), ("BackTowerB", 32), ("BackTowerC", 33), ("BackTowerD", 34), ("FrontTowerA", 35), ("FrontTowerB", 36)):
        e = S.el(R, eid)
        tx0, tx1, tz1, tz0 = X(e["map"][0]), X(e["map"][2]), Z(e["map"][1]), Z(e["map"][3])
        r = (tx1 - tx0) / 2
        P.tower(S, R, eid, (tx0 + tx1) / 2, e["yc"], tz0 - 4.0, tz1, r, windows=e["windows"], roof=e["roof"], seed=seed, leaf=(3.2, 8.0), tier=8.5,
                ry_scale=e["ry"] / r, far=True, ev=e["ev"], ref=e["ref"], layer="BACKDROP")

    # ---- cameras
    box = (X(1300), X(2700), -13.0, 16.0, -2.0, Z(1990))
    P.populate(S, R, "WestBlock", wb, ["resident_0", "resident_1", "husk_sentry"], 5, seed=19)
    P.populate(S, R, "WestBlockLower", wl, ["resident_2", "husk_sentry_low"], 2, seed=20)
    for k, (wx, wy, wz) in enumerate(((-122.0, -6.0, 30.0), (-104.0, -4.0, 47.0))):          # winged sentries over the well (C)
        P.creature(S, R, "winged_sentry", f"Air_{k}", wx, wy, wz, rz=-0.6 + 1.2 * k)
    S.cam_auto(R, box, ref="master A_left_well_lower; B5; B3_central_lower", views=("front", "oblique", "obliqueR", "back", "side"))
    S.cam_front("LowerSection", R, (1300, 3050, 2700, 3660), y=-13.0, hide=("FRONT", "BACKDROP"), ref="03_Left_City/Left_City_total.jpg; master A_left_well_lower", purpose="lower well, same frame as master A_left_well_lower")
    S.camera("BalconyEntry", R, (-76.0, -11.4, bz + 1.7), look=(-60.0, -11.2, bz + 1.4), lens=20.0, kind="view", purpose="east end of the high balcony: past the dark band into the first bay of the central block")
    S.camera("GroundWest", R, (-128.0, -15.0, 4.0), look=(-149.0, 1.0, 7.5), lens=24.0, kind="view", purpose="lift, quay and cluster column, compare Left_City_left_bottom.jpg", ref=REF_LB)
    S.camera("Frames", R, (-112.0, -22.0, 14.0), look=(-124.0, 2.0, 12.0), lens=28.0, kind="view", purpose="iron frames, walkways and floating platforms, compare Left_City_middle.jpg", ref=REF_M)
    S.camera("Balcony", R, (-104.0, -24.0, 24.0), look=(-84.0, -6.0, 22.0), lens=28.0, kind="view", purpose="high balcony and shell towers, compare Left_City_right_upper.jpg",
             ref="03_Left_City/Left_City_right_upper.jpg")
    S.camera("LookUp", R, (-124.0, -28.0, 4.0), look=(-108.0, 10.0, 60.0), lens=18.0, kind="view", purpose="up the well from the water")
    S.camera("Interior_WestBlock", R, (wb["x0"] + 1.6, wb["yf"] + 1.5, wb["floors"][2] + 1.8), look=(wb["x1"] - 1.0, wb["yb"] - 1.0, wb["floors"][2] + 2.4), lens=18.0, kind="interior",
             purpose="west block interior, compare Left_City_left_upper.jpg", ref="03_Left_City/Left_City_left_upper.jpg")
    S.camera("WalkOnFrame", R, (xa[0] + 0.5, 0.0, ta[0] + 1.7), look=(xa[-1], 0.6, ta[0] + 1.5), lens=24.0, kind="view", purpose="standing on the iron walkway")


# ============================================================================ SouthwestCave
def southwest_cave(S):
    R = "SouthwestCave"
    REF = "09_Bench/Bench_left.jpg; Bench_middle.jpg; Bench_right.jpg; Bench_top.jpg; master B4"
    x0, x1 = X(120), X(1300)
    y0, y1 = -9.0, 14.0
    zc = [(X(120), 27.9), (X(520), 28.4), (X(700), 24.3), (X(900), 20.6), (X(1300), 19.9)]      # ceiling underside along X (A: master B4)

    def ceil_base(x):
        for (xa, za), (xb, zb) in zip(zc, zc[1:]):
            if xa <= x <= xb:
                return lerp(za, zb, (x - xa) / (xb - xa))
        return zc[-1][1]

    # the master draws the ceiling as a lumpy line of pad clusters, not as straight runs (A outline; the wobble is C)
    rand_c = rng(91)
    zc2 = [(lerp(x0, x1, k / 30), ceil_base(lerp(x0, x1, k / 30)) + (rand_c(-1.4, 0.8) if 0 < k < 30 else 0.0)) for k in range(31)]

    def ceil_z(x):
        if x <= zc2[0][0]:
            return zc2[0][1]
        for (xa, za), (xb, zb) in zip(zc2, zc2[1:]):
            if xa <= x <= xb:
                return lerp(za, zb, (x - xa) / (xb - xa))
        return zc2[-1][1]

    # ---- rock shell of the cave
    P.rock(S, R, "Floor", x0, x1, y0, y1, Z(3680), BED, ev="C", ref="cave floor under the water line", layer=None, amp=0.4)
    P.water(S, R, "Water", X(440), x1, y0, y1 + 4.0, WATER, "A", "09_Bench/Bench_middle.jpg")
    wbl = S.el("LeftWell", "WestBlockLower")
    wx0, wz0 = X(wbl["map"][0]), Z(max(wbl.get("floors", [wbl["map"][3]]))) - 0.5          # outer face and slab underside of the left well's west block
    # ---- the cave's outline (A: master B4 traced on SouthwestCave_Section__pair): the left wall bulges out, the corners
    # are round, the right wall comes down to the passage. Back and front walls are one rock sheet each (D-372).
    def tab(pts, v):
        if v <= pts[0][0]:
            return pts[0][1]
        for (a, pa), (b, pb) in zip(pts, pts[1:]):
            if a <= v <= b:
                return lerp(pa, pb, (v - a) / (b - a))
        return pts[-1][1]

    LW = [(-6.0, 215), (3.0, 215), (5.3, 205), (7.0, 186), (11.0, 177), (16.5, 176), (22.0, 184), (25.5, 201), (30.0, 232)]
    xr = X(1236)

    def lw(z):                                                  # west wall line (map x by height)
        return X(tab(LW, z)) + 0.5 * fbm(z * 0.3, 1.7, 0.2, 2)

    def rw(z):                                                  # east wall: down to 7.5 m, open below to the passage
        if z <= 6.5:
            return x1 + 30.0
        return lerp(x1 + 30.0, xr, min(1.0, z - 6.5)) + 0.4 * fbm(z * 0.3, 4.1, 0.6, 2)

    def dist(x, z):                                             # soft distance inside the outline: round corners (k)
        k = 2.2
        ds = (ceil_z(x) + 1.0 - z, x - lw(z), rw(z) - x, z - (BED - 1.0))
        return -k * math.log(sum(math.exp(-max(-20.0, d) / k) for d in ds))

    y_out = y0 + 0.9                                           # outside the outline the back sheet comes forward

    def y_in(x, z):                                             # uneven back of the cave, also in plan (C)
        return 15.0 + 2.0 * math.sin(x * 0.13 + 0.6) + 0.6 * fbm(x * 0.25, z * 0.25, 3.3, 3)

    def sheet_y(x, z):
        t = max(0.0, min(1.0, dist(x, z) / 1.6))
        return lerp(y_out, y_in(x, z), t * t * (3.0 - 2.0 * t))

    def front_y(x, z):                                          # inner face of the viewer-side wall; meets the back sheet at both ends
        yy = y0 - 0.3 + 0.8 * math.sin(x * 0.11 + 2.0) + 0.4 * fbm(x * 0.25, z * 0.25, 7.1, 3)
        yy = max(yy, y0 + 1.1 - max(0.0, x - lw(z) - 0.5))
        return max(yy, y0 + 1.1 - max(0.0, rw(z) - 0.5 - x))

    def solve_x(y, z, xa, xb):                                  # where the back sheet passes depth y (side walls)
        fa = sheet_y(xa, z) - y
        for _ in range(24):
            xm = (xa + xb) / 2
            fm = sheet_y(xm, z) - y
            if (fm < 0) == (fa < 0):
                xa, fa = xm, fm
            else:
                xb = xm
        return (xa + xb) / 2

    sx0, sx1 = x0 - 3.0, wx0 - 1.2                              # the sheets stop short of the west block of the left well
    g = Geo()
    K.rock_sheet(g, sx0, sx1, BED - 2.0, 6.0, sheet_y, y1 + 6.0, step=0.5)
    S.add(g, "BackWall", R, "CaveWall", "A", "master B4 outline", layer=None, smooth=50,
          note="lower back wall: uneven plan (C); one rock sheet with the upper part (D-372)")
    g = Geo()
    K.rock_sheet(g, sx0, sx1, 6.0, 34.0, sheet_y, y1 + 6.0, step=0.5)
    S.add(g, "BackWallUpper", R, "CaveWall", "A", "master B4 outline", layer="ROCK", smooth=50,
          note="the inner face comes forward where the cave ends, drawing the cloud-shaped outline in the section; depth is completion")
    g = Geo()
    def front_out(x, z):                                        # outside face: a rounded rock mass, thin toward its edges
        e = min(x - sx0, sx1 - x, z - BED + 2.0, 34.0 - z) / 7.0
        e = max(0.0, min(1.0, e))
        return front_y(x, z) - 0.6 - 5.4 * e * e * (3.0 - 2.0 * e) + 0.9 * fbm(x * 0.2, z * 0.2, 5.5, 2)
    K.rock_sheet(g, sx0, sx1, BED - 2.0, 34.0, front_y, front_out, step=0.5, front=True)
    S.add(g, "FrontWall", R, "CaveWall", "C", "viewer-side closure of the cave (completion)", layer="FRONT", smooth=50)
    g = Geo()
    K.rock_roof(g, x0 - 1.0, x1 + 1.0, y0 - 2.0, y1 + 2.0, ceil_z, 34.0, step=1.0, amp=0.5, seed=61)
    S.add(g, "Ceiling", R, "Ceiling", "A", "master B4 cave outline", layer="CEILING", smooth=50, note="one rock roof along the wobbled roof line (wobble C)")
    P.rock(S, R, "EastEnd", sx1 - 1.6, sx1 + 0.6, 8.0, y1 + 6.0, BED - 1.0, 8.5, ev="C", ref="back of the east passage (completion)", layer=None, amp=1.0)
    P.rock(S, R, "EastLintel", X(1240), wx0 - 1.2, y0 - 2.0, y1 + 2.0, 7.5, 21.0, ev="A", ref="master B4: the cave closes down to the passage at its east end", layer=None, amp=1.2)
    P.rock(S, R, "EastLintelLow", wx0 - 2.0, x1 + 4.0, y0 - 2.0, y1 + 2.0, 7.5, wz0 - 0.9, ev="A", ref="master B4", layer=None, amp=0.8,
           note="under the west block of the left well: the lintel stops below its lowest floor")
    # west bank with its low pocket and the stepped ledges up the west wall (A: master B4, Bench_left.jpg)
    bx1 = X(440)
    # the bank stops 1.2 short of the viewer-side wall: a rock face with a crevice in front, not a block cut by the wall (C)
    P.rock(S, R, "WestBank_Top", x0, bx1, y0 + 1.2, y1, 3.6, Z(3500), ev="A", ref="09_Bench/Bench_left.jpg; master B4", layer=None, amp=0.7)
    P.rock(S, R, "WestBank_Rear", x0, bx1, 4.0, y1, BED, 3.7, ev="A", ref="master B4", layer=None, amp=0.5)
    P.rock(S, R, "WestBank_End", x0, x0 + 4.5, y0 + 1.2, 4.2, BED, 3.7, ev="A", ref="master B4", layer=None, amp=0.5)
    P.rock(S, R, "WestBank_Toe", bx1 - 4.0, bx1 + 1.5, y0 + 1.2, 4.2, BED, 3.7, ev="A", ref="master B4: the pocket under the bank opens toward the water between two rock toes", layer=None, amp=0.6)
    P.rock(S, R, "WestStep_1", x0, x0 + 8.0, -4.0, 8.0, Z(3500), 10.4, ev="A", ref="master B4 stepped ledges", layer=None, amp=1.3)
    P.rock(S, R, "WestStep_2", x0, x0 + 4.6, -4.0, 8.0, 10.4, 13.4, ev="A", ref="master B4 stepped ledges", layer=None, amp=0.9)
    hl = S.el(R, "HutLedge")
    lx0, lx1, lz0, lz1 = X(hl["map"][0]), X(hl["map"][2]), Z(hl["map"][3]), Z(hl["map"][1])
    P.rock(S, R, "HutLedge", X(178), lx1, -4.5, 9.0, lz0 - 1.2, lz1, ev="A", ref="09_Bench/Bench_top.jpg", layer=None, amp=1.1,
           note="runs into the west wall as the master shows (B)")

    # ---- the shell hut (A: Bench_top.jpg)
    hx = (X(383) + X(446)) / 2
    g = Geo()
    SH.gourd_hut(g, m=place(hx, 2.0, lz1 - 0.15), h=Z(3266) - lz1 + 0.6, r=2.3)
    S.add(g, "Hut", R, "ShellHut", "A", "09_Bench/Bench_top.jpg", note="back of the hut is completion", smooth=50)

    # ---- spotted pads on every rock face, small ball clusters on the ledge
    # pads only in a band along the outline (A: master B4); the middle of the back wall stays bare rock
    rand_p = rng(95)
    for o in P.pad_field(S, R, "PadBack", x0 + 1.0, sx1, 0.5, 31.0, 0.0, 210, seed=1, facing="front", size=(1.2, 2.6), ev="A", ref=REF,
                         keep=lambda a_, b_: 1.0 < dist(a_, b_) < 4.8 and lw(b_) + 1.6 < a_ < rw(b_) - 1.6):
        o.location.y = sheet_y(o.location.x, o.location.z) - 0.3 - rand_p(0.0, 0.4)
    for o in P.pad_field(S, R, "PadFront", x0 + 1.0, sx1, 0.5, 31.0, 0.0, 150, seed=2, facing="back", size=(1.2, 2.6), ev="C", ref=REF, layer="FRONT",
                         keep=lambda a_, b_: b_ < ceil_z(a_) - 0.5 and lw(b_) + 1.0 < a_ < rw(b_) - 1.0, note="inner face of the viewer-side wall: completion"):
        o.location.y = front_y(o.location.x, o.location.z) + 0.3 + rand_p(0.0, 0.4)
    # pad lumps hanging from the ceiling (A: master B4 shows pad clusters bulging down from the roof line)
    for k, mx in enumerate((640, 790, 1010)):
        xc = X(mx)
        zc_ = ceil_z(xc)
        P.pad_field(S, R, f"PadLump{k}", xc - 3.6, xc + 3.6, zc_ - 4.6, zc_ + 0.6, 9.0, 46, seed=70 + k, facing="front", size=(1.0, 2.2), ev="A",
                    ref="master B4", jitter=7.0, keep=lambda a_, b_, xc=xc, zc_=zc_: ((a_ - xc) / 3.6) ** 2 + ((b_ - zc_) / 4.6) ** 2 < 1.0,
                    note="pad cluster hanging from the roof; its depth is completion")
    P.pad_field(S, R, "PadBankFront", x0, bx1 + 1.0, BED + 0.5, Z(3500), y0 + 1.6, 70, keep=lambda a_, b_: a_ > lw(b_) + 0.6, seed=78, facing="front", size=(0.9, 2.0), ev="A",
                ref="master B4 (the lower-left pocket and bank are lined with clusters); 09_Bench/Bench_left.jpg")
    P.pad_field(S, R, "PadSteps", x0, x0 + 8.0, Z(3500), 13.4, -4.4, 40, seed=79, facing="front", size=(0.8, 1.7), ev="A", ref="master B4; 09_Bench/Bench_left.jpg",
                keep=lambda a_, b_: (a_ < x0 + 4.6 or b_ < 10.4) and a_ > lw(b_) + 0.6)
    P.pad_field(S, R, "PadCeil", x0 + 1.0, x1, y0, y1, 0.0, 190, seed=3, facing="down", size=(1.2, 2.6), ev="A", ref=REF, layer="CEILING")
    for o in [o for o in S.coll(R, "CEILING").objects if o.name.startswith(f"S3_{R}_PadCeil")]:
        o.location.z = ceil_z(o.location.x) - 0.2
    for o in P.pad_field(S, R, "PadWest", y0 + 2.5, y1 - 2.5, 6.8, 27.0, 0.0, 60, seed=4, facing="east", size=(1.2, 2.4), ev="A", ref=REF,
                         keep=lambda a_, b_: b_ < ceil_z(lw(b_) + 2.0) - 0.5):
        z_ = o.location.z
        o.location.x = solve_x(o.location.y, z_, lw(z_) - 3.0, lw(z_) + 3.0) + 0.2
    P.pad_field(S, R, "PadLedge", lx0, lx1, -4.5, 9.0, lz0 - 1.3, 46, seed=5, facing="down", size=(1.0, 2.0), ev="A", ref="09_Bench/Bench_top.jpg")
    P.pad_field(S, R, "PadLedgeFront", lx0, lx1, lz0 - 1.0, lz1 - 0.2, -4.6, 24, seed=6, facing="front", size=(0.9, 1.6), ev="A", ref="09_Bench/Bench_top.jpg")
    for o in P.pad_field(S, R, "PadLintelW", y0 + 2.5, y1 - 2.5, 7.8, 19.0, 0.0, 40, seed=7, facing="west", size=(1.2, 2.2), ev="A", ref="09_Bench/Bench_right.jpg"):
        z_ = o.location.z
        o.location.x = solve_x(o.location.y, z_, xr - 3.0, xr + 3.0) - 0.2
    P.cluster_field(S, R, "LedgeClusters", lx0 + 0.5, lx1 - 0.5, -3.5, 8.0, lz1 - 0.15, 26, seed=8, facing="up", size=(0.35, 0.7), ev="A", ref="09_Bench/Bench_top.jpg",
                    keep=lambda a, b: abs(a - hx) > 2.8 or abs(b - 2.0) > 2.8)
    P.cluster_field(S, R, "BankClusters", x0 + 1.0, bx1, y0 + 1.0, y1 - 1.0, Z(3500) - 0.1, 30, seed=9, facing="up", size=(0.5, 1.1), ev="A", ref="09_Bench/Bench_left.jpg")

    # ---- piers, causeway, fences, lamps, spire posts, the long pole (A: Bench_middle / Bench_right)
    REF_M = "09_Bench/Bench_middle.jpg; master B4"
    piers = [(X(a), X(b), Z(t)) for a, b, t in S.el(R, "Piers")["items"]]
    g = Geo()
    for i, (xa, xb, zt) in enumerate(piers):                   # open brick frames (A: Bench_middle.jpg): slender legs, a deck on top,
        slim = xb - xa < 3.0                                    # rungs between the legs of the narrow ones, black between the wide ones
        hd, lg = (0.9, 0.55) if slim else (2.5, 0.8)
        SH.rubble_pier(g, xa, xa + lg, -hd, hd, BED, zt - 0.6, seed=70 + i, block=0.6)
        SH.rubble_pier(g, xb - lg, xb, -hd, hd, BED, zt - 0.6, seed=170 + i, block=0.6)
        P.stone_pier(g, xa - 0.05, xb + 0.05, -hd, hd, zt - (0.85 if slim else 1.3), zt, seed=270 + i, block=0.6)
        if slim:
            zr = BED + 1.4
            while zr < zt - 2.0:
                SH.rubble_pier(g, xa + lg - 0.1, xb - lg + 0.1, -hd + 0.15, hd - 0.15, zr, zr + 0.4, seed=370 + i * 13 + int(zr * 7), block=0.5)
                zr += 1.5
        else:
            g.use("wall_deep")
            g.box(xa + lg, xb - lg, -hd + 0.5, hd - 0.5, BED, zt - 1.3)
    ep = S.el(R, "EastPassage")
    P.stone_pier(g, X(ep["map"][0]), X(ep["map"][2]), -4.0, 6.0, BED, GROUND, seed=77, block=1.0)
    S.add(g, "Piers", R, "StonePiers", "A", REF_M, smooth=35)
    fence = S.kit("fence_web", lambda: (A.fence_web_curves(1.675), "iron", 0.026))
    spire = S.kit("spire_post", lambda: spire_post())
    seat = S.kit("stone_seat", lambda: stone_seat())
    wide, east = piers[2], piers[4]
    P.creature(S, R, "resident_1", "ByHut", hx + 3.4, 3.0, lz1 + 0.01, rz=-2.0)          # D-347 (C positions)
    P.creature(S, R, "husk_sentry", "EastPier", east[0] + 3.2, 0.6, east[2] + 0.01, rz=1.4)
    for k in range(3):
        S.put(fence, f"Fence_W_{k}", R, "FenceWeb", place(wide[0] + 0.5 + 1.7 * k, 2.2, wide[2]), "A", REF_M)
    for k in range(5):
        S.put(fence, f"Fence_E_{k}", R, "FenceWeb", place(east[0] + 1.0 + 1.7 * k, 2.2, east[2]), "A", REF_M)
    S.put(fence, "Fence_P1", R, "FenceWeb", place(piers[1][0] + 0.05, 0.0, piers[1][2]), "A", REF_M)
    g = Geo().use("iron")                                       # iron gates hung between the slender piers (A: Bench_middle.jpg)
    gi = 0
    for (xa, xb, za), (xc, xd, zc) in zip(piers, piers[1:]):
        if xc - xb > 6.0:
            continue
        zg = min(za, zc) - 2.1
        g.tube([(xb, 0.0, zg + 1.9), (xc, 0.0, zg + 1.9)], 0.06, segs=5)
        n_p = max(1, int(round((xc - xb) / 1.7)))
        for q in range(n_p):
            S.put(fence, f"Gate_{gi}", R, "FenceWeb", place(xb + (xc - xb) * (q + 0.5) / n_p - 0.84, 0.0, zg), "A", REF_M)
            gi += 1
    S.add(g, "GateBars", R, "IronBar", "A", REF_M)
    S.put(seat, "StoneSeat", R, "StoneSeat", place((wide[0] + wide[1]) / 2 - 0.6, 0.6, wide[2]), "A", REF_M,
          note="domed stone seat on the wide pier; not confirmed to be the bench (Bench_middle.jpg)")
    P.lamp(S, R, "Lamp_0", (wide[0] + wide[1]) / 2 + 1.9, 0.4, wide[2], ref=REF_M)
    P.lamp(S, R, "Lamp_1", east[0] + 2.0, 0.0, east[2], ref=REF_M)
    P.lamp(S, R, "Lamp_2", east[1] - 2.2, 0.0, east[2], ref=REF_M)
    for k, (px, pz) in enumerate(((piers[3][0] + 1.05, piers[3][2]), (east[0] + 5.4, east[2]), (piers[0][0] + 1.2, piers[0][2]))):
        S.put(spire, f"SpirePost_{k}", R, "SpirePost", place(px, -0.4, pz, s=1.0 if k < 2 else 0.6), "A", REF_M)
    pe = S.el(R, "Pole")
    g = Geo().use("iron")
    px = X(pe["map"][0])
    g.tube([(px, 0.5, BED), (px, 0.5, ceil_z(px) + 0.5)], 0.11, segs=6)
    for zz in (4.0, 9.0, 14.0):
        g.revolve([(0.11, zz), (0.2, zz + 0.1), (0.11, zz + 0.25)], segs=8, m=place(px, 0.5, 0))
    SH.float_slab(g, px - 1.7, 0.5, 6.4, w=2.0, d=1.4, seed=5)
    S.add(g, "Pole", R, "LongPole", "A", "09_Bench/Bench_right.jpg", smooth=35)
    rand = rng(81)
    P.ring_posts(S, R, "RingPost", [(rand(X(460), x1 - 2.0), rand(-7.5, -3.2), -2.4, rand(0.7, 0.95)) for _ in range(20)], ref=REF_M)
    g = Geo()                                                   # big dark shell mounds behind the piers
    rand = rng(83)
    for k, mx in enumerate((-202.0, -196.0, -190.5, -184.0, -178.0, -171.5, -167.0)):
        A.add_shell_dome(g, place(mx, rand(6.0, 10.5), BED + 0.4, rz=rand(0, 3.0)), rand(1.8, 2.8), rand(1.6, 2.2), rand(3.0, 5.2), bands=4, tilt=0.08)
    for k, mx in enumerate((-206.0, -188.0, -174.0)):
        A.add_shell_mound(g, place(mx, rand(4.5, 7.0), BED + 0.4, rz=rand(-0.4, 0.4)), rand(2.0, 2.8), 1.5, rand(2.0, 2.6), 4, slant=0.25)
    S.add(g, "ShellMounds", R, "ShellMounds", "A", "09_Bench/Bench_middle.jpg; Bench_top.jpg (lower right)", note="depth positions are completion")

    # ---- cameras: the cave is closed on all sides, so its own rock stays visible
    hide = ("BACKDROP", "CAVESHELL")
    S.cam_front("Section", R, (100, 3100, 1310, 3690), y=y0 + 0.4, hide=("FRONT",), ref=REF, purpose="section through the cave, same frame as master B4")
    S.camera("FromEast", R, (x1 - 6.0, -4.0, 5.2), look=(-205.0, 2.0, 9.0), lens=20.0, kind="interior", purpose="from the east end across the piers, compare Bench_middle.jpg", ref=REF_M)
    S.camera("Hut", R, (hx + 9.0, -6.0, lz1 + 1.6), look=(hx - 0.5, 2.0, lz1 + 2.6), lens=24.0, kind="interior", purpose="shell hut on its ledge, compare Bench_top.jpg", ref="09_Bench/Bench_top.jpg")
    S.camera("FromLedge", R, (lx0 + 2.5, 6.5, lz1 + 2.2), look=(-190.0, 0.0, 3.5), lens=18.0, kind="interior", purpose="from the ledge down over the water")
    S.camera("WestBank", R, (-204.0, -5.0, 3.6), look=(-232.0, 1.0, 7.0), lens=20.0, kind="interior", purpose="west bank, steps and pocket, compare Bench_left.jpg", ref="09_Bench/Bench_left.jpg")
    S.camera("Passage", R, (-172.0, 1.0, 3.2), look=(-150.0, 1.0, 3.6), lens=20.0, kind="view", purpose="east passage toward the left well (connection A)")
    S.camera("Outside", R, (-185.0, -95.0, 40.0), look=(-195.0, 0.0, 14.0), lens=24.0, hide=hide, kind="closed", purpose="cave closed by its viewer-side wall")
    S.camera("Top", R, (-202.0, 2.5, 80.0), look=(-202.0, 2.5, 0.0), ortho=90.0, hide=("CEILING", "ROCK", "CAVESHELL"), kind="top", purpose="plan of the cave with the ceiling removed")


def spire_post():
    """Lamp-less spired post standing on the piers (A: Bench_middle.jpg, Bench_right.jpg)."""
    g = Geo()
    g.use("iron")
    g.revolve([(0.32, 0.0), (0.34, 0.1), (0.2, 0.2), (0.16, 0.5), (0.2, 0.6), (0.14, 0.7), (0.13, 1.7), (0.24, 1.8), (0.26, 2.3), (0.2, 2.4), (0.3, 2.5), (0.12, 2.9)], segs=8)
    g.use("louvre")
    g.revolve([(0.36, 2.5), (0.3, 2.7), (0.16, 3.3), (0.06, 4.2), (0.015, 5.2)], segs=8)
    g.use("iron")
    for k in range(4):
        a = TAU * k / 4
        g.spike((0.27 * math.cos(a), 0.27 * math.sin(a), 2.5), (0.34 * math.cos(a), 0.34 * math.sin(a), 3.1), 0.04, segs=4)
    return g


def stone_seat():
    """Round-backed stone seat (A: Bench_middle.jpg; identity not confirmed)."""
    g = Geo()
    g.use("stone")
    g.revolve([(0.5, 0.0), (0.55, 0.12), (0.45, 0.3), (0.5, 0.55), (0.42, 0.62)], segs=12)
    rows = []
    for k in range(7):
        a = math.pi * k / 6
        rows.append([(0.55 * math.cos(a) * s, 0.28 + 0.12 * (j - 1), 0.6 + 1.0 * math.sin(a) * s) for s in (1.0, 0.72) for j in ((0, 2) if s == 1.0 else (2, 0))])
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)
    g.use("stone_dark")
    g.ellipsoid((0, 0.22, 1.05), (0.2, 0.06, 0.34), segs=8, steps=5)
    return g


REGIONS = {"LeftWell": left_well, "SouthwestCave": southwest_cave}
