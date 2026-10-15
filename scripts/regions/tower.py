"""Stage 3 structure: TowerBlock (the tower building from the banner hall to the telescope room), TopCavern
(pebble roof, walls and spires of the upper rain cavity) and GroundCorridorEast."""
import math

import cot_assets as A
import cot_kit as K
import cot_furnish as FU
import cot_parts as P
import cot_shell as SH
from cot_geo import fbm, Geo, TAU, lerp, place, rng
from cot_s3 import X, Z

GZ = 0.867
BRIDGE_Y = (-19.5, -12.5)


def tower_block(S):
    R = "TowerBlock"
    st = dict(P.STYLES["tower"])
    T = lambda n: f"08_Tower/Tower_step{n}.jpg"

    # ---- base: banner hall and the five-window storey (A: step1)
    base = dict(S.el(R, "Base"), floors=[3404, 3587])
    bx0 = X(base["map"][0])
    bi = P.stack(S, R, base, st, levels={0: dict(back=("blind", "lancet"), lamp="string"), 1: dict(back=("lancet",), glass="glass_blue")}, door_y={"L": 1.0, "R": 1.0},
                 keep_clear=[(1, bx0 + 12.3, bx0 + 24.7, 10.2, 13.8), (0, X(4568) - 5.2, X(4568) + 5.2, 4.2, 9.8)],     # (0, ...): the banner dais
                 ext_faces=("L", "N"))
    for eid in ("BaseShaftL", "BaseShaftR"):
        P.lift(S, R, S.el(R, eid), back="chevron", ref=T(1))
    ban = S.kit("banner_xl", lambda: K.k_banner(2.1, 7.6))      # the banners fill most of the hall height on Tower_step1.jpg
    xs = [bi["x0"] + 9.0 + 4.2 * k for k in range(7)]
    for k, bx in enumerate(xs):
        S.put(ban, f"Banner_{k}", R, "Banner", place(bx, 3.0 + 6.0 * (k % 2), bi["floors"][1] - 0.6), "A", T(1))
    S.put(S.kit("FU_dais_tower", lambda: FU.k_dais(9.0, 4.2, 1.1, "cushion", "trim")), "BannerDais", R, "Dais",
          place((bi["x0"] + bi["x1"]) / 2, 7.0, bi["floors"][0] + 0.01), "A", T(1), note="raised platform in the middle of the banner hall (A); its depth is completion")
    g = Geo().use("cushion")                                    # pale segmented dais under the five windows
    for k in range(4):
        g.ellipsoid((bi["x0"] + 14.0 + 3.0 * k, 12.0, bi["floors"][1] + 0.2), (1.45, 1.6, 0.24), segs=12, steps=5, e=0.5)
    S.add(g, "Dais", R, "PaleDais", "A", T(1))
    g = Geo().use("stone_dark")
    g.box(bi["x0"], bi["x1"], bi["yf"], bi["yb"], -2.7, bi["bottom"])
    S.add(g, "Foundation", R, "Foundation", "C", "foundation down to the well bed")
    # ---- link shaft and the black mass above the base (A shaft; C mass)
    P.lift(S, R, S.el(R, "LinkShaft"), back="chevron", car=None, closed=True, ref="master B2_rc_block_lower")
    ma = S.el(R, "MassA")
    g = Geo().use("wall_deep")                                  # a flat black block, as the master draws it (D-364)
    mx0_, mx1_, mz0_, mz1_ = X(ma["map"][0]), X(ma["map"][2]), Z(ma["map"][3]) + 0.5, Z(ma["map"][1])
    g.box(mx0_, mx1_, -9.0, 17.0, mz0_, mz1_)
    for zz in (mz1_, lerp(mz0_, mz1_, 0.5)):
        SH.hanging_fringe(g, mx0_ + 0.3, mx1_ - 0.3, -9.1, zz - 0.1, 1.6, seed=int(zz))
    S.add(g, "MassA", R, "SolidMass", "C", ma["ref"], note="black on the master; solid between the base and the rooms (C)")
    # ---- rooms with the tall three-window chamber (A: step2)
    rooms = dict(S.el(R, "Rooms"))
    rooms["voids"] = list(rooms["voids"]) + [[4521, 4647, 2850, 2870, 1]]
    ri = P.stack(S, R, rooms, st, levels={0: dict(back=("lancet", "portrait", "niche")), 1: dict(back=("portrait", "web"))}, ext_faces=("L", "N"),
                 cells=[(1, 4273, 4400), (2, 4720, 4867), (0, 4273, 4330)],       # black between the rooms (master B2_rc_block_lower, D-377)
                 skip_bays={(0, k) for k in range(20) if 52.0 < 36.8 + 4.4 * (k + 0.5) < 62.0} | {(1, k) for k in range(20) if 52.0 < 36.8 + 4.4 * (k + 0.5) < 62.0})
    ww = S.el(R, "WhiteWindow")
    wx0, wx1, wz0, wz1 = X(ww["map"][0]), X(ww["map"][2]), Z(ww["map"][3]), Z(ww["map"][1])
    tall = P.kit_window(S, "tall", 2.2, wz1 - wz0 - 0.4, "glass_white")
    for k in range(3):
        S.put(tall, f"WhiteWindow_{k}", R, "WindowTall", place(lerp(wx0 + 1.4, wx1 - 1.4, k / 2), ri["yb"] - 0.75, wz0 + 0.1), "A", T(2))
    blk = S.kit("shell_block_2", lambda: SH.k_shell_block(2))
    S.put(blk, "WhiteRoom_Block", R, "ShellBlock", place((wx0 + wx1) / 2, 8.0, wz0 + 4.0), "A", T(2))
    # ---- corridor of portraits and its west arm to the bridge (A: step3)
    cor = S.el(R, "Corridor")
    ci = P.stack(S, R, cor, st, levels={0: dict(solid=True), 1: dict(back=("noble", "portrait", "lancet"), lamp="round"), 2: dict(back=("web", "lancet", "noble"))},
                 door_y={"L": -6.6}, ext_faces=("N",), cells=[(0, 4700, 4780), (2, 4450, 4520)])
    cw = S.el(R, "CorridorWest")
    P.stack(S, R, cw, dict(st, bay=4.0, partition=0, inner=False, back=("portrait", "drape")), y=(BRIDGE_Y[0] - 0.5, -4.0), door_y={"L": -16.0, "R": -6.6}, ext_faces=("N",),
            note="moved forward with the lower bridge so that the corridor still receives it (C)")
    P.lift(S, R, S.el(R, "MidShaft"), back="chevron", ref=T(3))
    # ---- upper block with its black middle, the chandelier hall, floor 5 (A: step4, step5)
    up = S.el(R, "Upper")
    P.stack(S, R, up, st, levels={1: dict(solid=True), 0: dict(back=("noble", "lancet", "portrait")), 2: dict(back=("lancet", "niche", "noble"))}, ext_faces=("L", "N"),
            cells=[(0, 4285, 4546), (0, 4588, 4700), (2, 4720, 4790)])      # the storey over the corridor is mostly black on the master (D-377)
    hf = S.el(R, "HallFloors")
    hi = P.stack(S, R, hf, dict(st, partition=0), keep_clear=[(1, 39.0, 65.0, 9.5, 11.5)], levels={1: dict(back=("drape", "web", "drape"), lamp=None), 0: dict(back=("web", "niche", "web"), glass="glass_blue")},
                 ext_faces=("N",))
    hz = hi["floors"][1]
    chand = S.kit("chandelier_l", lambda: K.k_chandelier(2.4, 14))
    for k, (cx, cy, dz) in enumerate(((44.0, 4.0, 2.0), (50.0, 9.0, 5.0), (56.0, 3.0, 3.2), (62.0, 8.0, 1.6), (47.0, -3.0, 4.4), (59.0, -2.0, 2.6))):
        g = Geo()
        K.chain(g, cx, cy, hi["zt"] - dz, hi["zt"])
        S.add(g, f"Chandelier_Chain_{k}", R, "ChandelierChain", "A", T(4))
        S.put(chand, f"Chandelier_{k}", R, "Chandelier", place(cx, cy, hi["zt"] - dz), "A", T(4))
    g = Geo().use("trim")                                       # ribbed half dome on the back wall behind the chandeliers
    mx_, my_ = (hi["x0"] + hi["x1"]) / 2 + 2.0, hi["yb"] - 0.7
    for k in range(9):
        a = math.pi * k / 8
        g.tube([(mx_ + 9.0 * math.cos(a) * t, my_, hz + 9.0 + 6.0 * math.sin(a) * t) for t in (0.08, 0.5, 1.0)], 0.1, segs=5, ref=(0, 1, 0))
    g.tube([(mx_ + 9.0 * math.cos(math.pi * i / 16), my_, hz + 9.0 + 6.0 * math.sin(math.pi * i / 16)) for i in range(17)], 0.16, segs=6, ref=(0, 1, 0))
    S.add(g, "HallDomeRibs", R, "HallDome", "A", T(4), note="radial ribs of the hall's dome, modelled as relief on the back wall")
    seat = S.kit("seat", lambda: K.k_seat())
    for k in range(8):
        S.put(seat, f"Seat_{k}", R, "Seat", place(40.0 + 3.4 * k, 10.5, hz), "A", T(4))
    gf, gg = Geo(), Geo()                                       # leaf windows on the black west face (A: master B2 upper)
    for k, (yy, zz) in enumerate(((-4.0, 126.0), (5.0, 121.0), (11.0, 129.0), (0.0, 112.0))):
        A.add_leaf_window(gf, gg, place(hi["x0"] - 0.5, yy, zz, rz=-math.pi / 2), 2.4, 6.0, index=k, glass_key="glass")
    S.add(gf, "WestLeafFrames", R, "LeafWindows", "A", "master B2_rc_block_upper", note="depth positions are completion")
    S.add(gg, "WestLeafGlass", R, "LeafWindows", "A", "master B2_rc_block_upper")
    f5 = S.el(R, "Floor5")
    fi = P.stack(S, R, f5, st, levels={0: dict(back=("web", "portrait", "drape", "lancet"))}, ext_faces=("L", "N"))
    wc = S.el(R, "WestCanopy")
    P.louvre_roof(S, R, "WestCanopy", X(wc["map"][0]), min(X(wc["map"][2]) + 4.0, X(S.el(R, "SpireBase")["map"][0]) + 0.3), fi["zt"] + 0.5, fi["zt"] + 3.5,
                  fi["yf"] - 0.4, fi["yb"] + 0.4, bays=2, curve_end="W", ev="A",
                  ref="master B2_rc_block_upper")
    # ---- spire base with glass columns, louvre roofs and the domed kiosk (A: step6)
    sb = S.el(R, "SpireBase")
    si = P.stack(S, R, sb, dict(st, glass="glass_blue"), levels={0: dict(back=("web",), lamp="round")}, ext_faces=("N",))
    for k, gx in enumerate((si["x0"] - 0.85, si["x1"] + 0.85)):
        P.glass_pillar(S, R, f"SpireBaseGlass_{k}", gx, si["yf"] + 1.5, 0.8, si["floors"][0] + 0.4, si["zt"], "A", T(6))
    sh = S.el(R, "SpireShaft")
    shx0, shx1 = X(sh["map"][0]), X(sh["map"][2])
    zr = si["zt"] + 0.5
    P.louvre_roof(S, R, "SpireBaseRoofW", si["x0"] - 0.3, shx0 - 1.6, zr, zr + 3.2, si["yf"] - 0.3, si["yb"] + 0.3, bays=3, curve_end="W", ev="A", ref=T(6))
    P.louvre_roof(S, R, "SpireBaseRoofE", X(4652) + 0.4, si["x1"] + 0.3, zr, zr + 3.2, si["yf"] - 0.3, si["yb"] + 0.3, bays=1, curve_end="E", ev="A", ref=T(6))
    bp = S.el(R, "BasePavilion")
    kx0, kx1 = X(bp["map"][0]), X(bp["map"][2])
    g = Geo()
    g.use("louvre_core")
    g.box(kx0 + 0.2, kx1 - 0.2, -2.8, 2.8, zr + 3.2, zr + 5.6)
    g.use("louvre_frame")
    for sx in (kx0, kx1):
        for sy in (-3.0, 3.0):
            g.box(sx - 0.22, sx + 0.22, sy - 0.22, sy + 0.22, zr + 3.2, zr + 5.9)
    g.box(kx0 - 0.3, kx1 + 0.3, -3.3, 3.3, zr + 5.6, zr + 5.9)
    K.louvre_dome(g, (kx1 - kx0) / 2 + 0.2, 3.2, 2.3, ribs=8, m=place((kx0 + kx1) / 2, 0.0, zr + 5.9))
    g.use("iron")
    for i in range(14):
        a = TAU * i / 14
        px, py = (kx0 + kx1) / 2 + ((kx1 - kx0) / 2 + 0.3) * math.cos(a), 3.3 * math.sin(a)
        g.spike((px, py, zr + 5.9), (px, py, zr + 6.9), 0.05, segs=5, bulb=0.9)
    S.add(g, "BasePavilion", R, "DomedKiosk", "A", T(6), smooth=35)
    kwin = P.kit_window(S, "lancet", 1.2, 2.1, "glass_blue")
    for j, dx in enumerate((-1.5, 0.0, 1.5)):
        S.put(kwin, f"BasePavilion_Win_{j}", R, "WindowLancet", place((kx0 + kx1) / 2 + dx, -3.25, zr + 3.3), "A", T(6))
    # ---- the spire: glass column, herringbone shaft, black body, small chamber (A: step7, step8)
    P.lift(S, R, sh, back="chevron", car=None, closed=True, y=(-2.2, 2.2), ref=f"{T(7)}; {T(8)}", stops=(Z(sh["map"][3]), Z(sh["map"][1]) - 4.7))
    sg = S.el(R, "SpireGlass")
    P.glass_pillar(S, R, "SpireGlass", shx0 - 1.0, 0.0, 0.93, Z(sg["map_y"][1]), Z(sg["map_y"][0]), "A", T(7))
    bx0, bx1 = X(4446), X(4652)
    sc = S.el(R, "SmallChamber")
    cz0, cz1 = Z(sc["map"][3]), Z(sc["map"][1])
    g = Geo().use("wall_deep")                                  # the spire body is black on the master and in Tower_step7.jpg: a flat block (D-364)
    g.box(bx0, bx1, -5.0, 7.0, zr, cz0 - 0.3)
    for zz in (lerp(zr, cz0, 0.33), lerp(zr, cz0, 0.66), cz0 - 0.4):
        SH.hanging_fringe(g, bx0 + 0.3, bx1 - 0.3, -5.1, zz, 1.4, seed=int(zz))
    S.add(g, "SpireBody", R, "SolidMass", "C", "black right of the shaft on master and in Tower_step7.jpg", note="solid tower body (C)")
    P.stack(S, R, sc, dict(st, bay=3.0, partition=0, inner=False, back=("drape", "portrait")), ext_faces=("N",))
    g = Geo().use("house_wall")
    g.box(bx0, X(sc["map"][0]), -5.0, 7.0, cz0 - 0.5, cz1)
    g.box(X(sc["map"][2]), bx1, -5.0, 7.0, cz0 - 0.5, cz1)
    g.box(bx0, bx1, -5.0, 7.0, cz1, Z(398))
    S.add(g, "SpireBodyTop", R, "SpireBody", "C", "black round the small chamber on the master")
    # ---- top room with the telescope (A: step9)
    tr = S.el(R, "TopRoom")
    trx0 = X(tr["map"][0])
    ti = P.stack(S, R, tr, dict(st, glass="glass_blue", partition=0), keep_clear=[(0, trx0, trx0 + 7.0, -9.0, 9.0), (0, trx0 + 8.0, trx0 + 30.0, 3.4, 10.6)], levels={0: dict(back=("drape", "web", "portrait", "web"), lamp=None)}, ext_faces=("L", "R", "N"))
    tz = ti["floors"][0]
    g = Geo()
    K.telescope(g, m=place(ti["x0"] + 1.4, 0.0, tz, s=1.0))
    S.add(g, "Telescope", R, "Telescope", "A", T(9), note="points west out over the rain cavity")
    cst = S.kit("candle_stand", lambda: K.k_candle_stand(3, 1.7))
    cs1 = S.kit("candle_stand1", lambda: K.k_candle_stand(1, 2.0))
    for k in range(9):
        S.put(cst if k % 2 else cs1, f"Candle_{k}", R, "CandleStand", place(ti["x0"] + 9.0 + 2.4 * k, 4.6 + 2.6 * (k % 3), tz, rz=k * 0.7), "A", T(9))
    g = Geo()
    g.use("glass_blue")
    g.box(54.0, 57.6, ti["yb"] - 0.72, ti["yb"] - 0.62, tz + 1.4, tz + 3.6)
    g.use("trim")
    for a, b in (((53.9, tz + 1.3), (57.7, tz + 1.3)), ((53.9, tz + 3.7), (57.7, tz + 3.7))):
        g.tube([(a[0], ti["yb"] - 0.74, a[1]), (b[0], ti["yb"] - 0.74, b[1])], 0.09, segs=5)
    for xx in (53.9, 57.7):
        g.tube([(xx, ti["yb"] - 0.74, tz + 1.3), (xx, ti["yb"] - 0.74, tz + 3.7)], 0.09, segs=5)
    SH.hanging_fringe(g, ti["x0"] + 0.5, ti["x1"] - 0.5, ti["yf"] + 0.4, ti["bottom"], 3.2, seed=4)
    SH.hanging_fringe(g, ti["x0"] + 0.5, ti["x1"] - 0.5, ti["yb"] - 0.4, ti["bottom"], 3.2, seed=5)
    S.add(g, "TopRoom_PaintingAndFringe", R, "TopRoomDetails", "A", T(9))
    tw = S.el(R, "TopRoofWest")
    P.louvre_roof(S, R, "TopRoofWest", ti["x0"] - 0.4, X(tw["map"][2]), ti["zt"] + 0.5, ti["zt"] + 3.3, ti["yf"] - 0.4, ti["yb"] + 0.4, bays=4, curve_end="W", ev="A", ref=T(9))
    te = S.el(R, "TopRoofEast")
    g = Geo()
    K.louvre_dome(g, (X(te["map"][2]) - X(te["map"][0])) / 2 + 0.6, 9.0, 3.6, ribs=10, spikes=False, m=place((X(te["map"][0]) + X(te["map"][2])) / 2, 1.5, ti["zt"] + 0.5), slat=0.3)
    S.add(g, "TopRoofEast", R, "TopDome", "A", T(9), note="dark rounded roof over the east half; its depth is completion", smooth=40)

    # ---- creatures (D-347): many residents in the banner hall and the portrait corridor; a lancer and a winged sentry
    # in the corridor (A: Tower_step1.jpg, Tower_step3.jpg)
    P.populate(S, R, "Base", bi, ["resident_0", "resident_1", "resident_2"], 9, seed=8)
    P.populate(S, R, "Rooms", ri, ["resident_0", "resident_2"], 3, seed=9)
    P.populate(S, R, "Corridor", ci, ["resident_0", "resident_1", "resident_2", "resident_1", "lance_sentry", "winged_sentry"], 8, seed=10)
    P.populate(S, R, "Hall", hi, ["resident_1", "resident_2"], 4, seed=11)
    P.populate(S, R, "Floor5", fi, ["resident_0", "husk_sentry"], 2, seed=12)
    P.populate(S, R, "Top", ti, ["resident_2"], 1, seed=13)

    # ---- cameras
    S.cam_front("LowerSection", R, (3990, 1990, 4880, 3610), y=bi["yf"] - 2.5, ref="master B2_rc_block_lower", purpose="base to corridor, comparable with master B2_rc_block_lower")
    S.cam_front("UpperSection", R, (4080, 200, 4900, 2010), y=-12.0, ref="master B2_rc_block_upper", purpose="hall to top room, comparable with master B2_rc_block_upper")
    S.cam_auto(R, (bi["x0"] - 16.0, bi["x1"], -20.0, 19.0, -1.0, ti["zt"] + 4.0), ref="master B2", views=("closed", "oblique", "obliqueR", "back"))
    S.camera("BannerHall", R, (bi["x0"] + 1.6, bi["yf"] + 1.6, GZ + 1.8), look=(bi["x1"] - 6.0, bi["yb"] - 1.0, GZ + 5.0), lens=18.0, kind="interior", purpose="banner hall, compare Tower_step1.jpg", ref=T(1))
    S.camera("WhiteRoom", R, (wx0 - 6.0, ri["yf"] + 1.6, wz0 + 1.8), look=((wx0 + wx1) / 2, ri["yb"], wz0 + 6.0), lens=18.0, kind="interior", purpose="tall chamber with three white windows, compare Tower_step2.jpg", ref=T(2))
    S.camera("Corridor", R, (ci["x0"] + 1.6, ci["yf"] + 1.6, ci["floors"][1] + 1.7), look=(ci["x1"] - 4.0, ci["yb"] - 1.0, ci["floors"][1] + 2.0), lens=18.0, kind="interior", purpose="portrait corridor, compare Tower_step3.jpg", ref=T(3))
    S.camera("ChandelierHall", R, (hi["x0"] + 2.0, hi["yf"] + 2.0, hz + 2.0), look=(hi["x1"] - 8.0, hi["yb"] - 1.0, hz + 8.0), lens=18.0, kind="interior", purpose="chandelier hall, compare Tower_step4.jpg", ref=T(4))
    S.camera("SpireBase", R, (si["x0"] - 14.0, -22.0, zr + 3.0), look=((si["x0"] + si["x1"]) / 2, 2.0, zr + 1.0), lens=28.0, kind="view", hide=("CAVESHELL", "BACKDROP"), purpose="spire base roofs, kiosk and glass columns, compare Tower_step6.jpg", ref=T(6))
    S.camera("SpireUp", R, (30.0, -18.0, zr + 6.0), look=(46.0, 0.0, zr + 60.0), lens=20.0, kind="view", hide=("CAVESHELL", "BACKDROP"), purpose="up the spire: glass column, shaft, body, top room")
    S.camera("TopRoom", R, (ti["x0"] + 6.0, ti["yf"] + 1.6, tz + 1.7), look=(ti["x1"] - 6.0, ti["yb"] - 1.0, tz + 2.4), lens=18.0, kind="interior", purpose="top room with candles and painting, compare Tower_step9.jpg", ref=T(9))
    S.camera("Telescope", R, (ti["x0"] - 9.0, -9.0, tz + 3.0), look=(ti["x0"] + 3.0, 0.5, tz + 1.8), lens=28.0, kind="view", hide=("CAVESHELL", "BACKDROP"), purpose="telescope at the west end of the top room")


# ============================================================================ TopCavern
def top_cavern(S):
    R = "TopCavern"
    REF = "master B7"
    cw, ce, ww, ew = S.el(R, "CeilingWest"), S.el(R, "CeilingEast"), S.el(R, "WestWall"), S.el(R, "EastWall")
    P.rock(S, R, "CeilingWest", X(cw["map"][0]), X(cw["map"][2]), -40.0, 96.0, Z(cw["map"][3]), Z(cw["map"][1]), ev="A", ref=cw["ref"], layer="CEILING", amp=2.2, cell=6.0)
    P.rock(S, R, "CeilingEast", X(ce["map"][0]), X(ce["map"][2]), -40.0, 96.0, Z(ce["map"][3]), Z(ce["map"][1]), ev="A", ref=ce["ref"], layer="CEILING", amp=1.6, cell=6.0)
    # the cavity walls are rock like the host masses under them, so they hide and show together in the check views
    P.rock(S, R, "WestWall", X(ww["map"][0]), X(2860), -12.0, 96.0, Z(ww["map"][3]), Z(ww["map"][1]), ev="A", ref=REF, layer="ROCK", amp=2.0, cell=5.0,
           note="inner face moved out to the master's west wall line; the sheet below draws the bulge")
    P.rock(S, R, "EastWall", X(ew["map"][0]), X(ew["map"][2]), -12.0, 96.0, Z(ew["map"][3]), 150.0, ev="A", ref=ew["ref"], layer="ROCK", amp=2.0, cell=6.0)
    P.rock(S, R, "EastWallUpper", X(4962), X(ew["map"][2]), -12.0, 96.0, 150.0, Z(ew["map"][1]), ev="A", ref=ew["ref"], layer="ROCK", amp=1.6, cell=6.0,
           note="above the tower block the east wall stands back; the sheet draws its bulge (master B7)")
    peb = [S.kit(f"pebbles_{v}", lambda v=v: K.k_pebbles(v, 4, 4, 1.5)) for v in range(3)]

    # ---- the cavity outline (A: master B7 traced on TopCavern_ElevSection__pair; D-373): a rounded pebble cave
    def tab(pts, v):
        if v <= pts[0][0]:
            return pts[0][1]
        for (a, pa), (b, pb) in zip(pts, pts[1:]):
            if a <= v <= b:
                return lerp(pa, pb, (v - a) / (b - a))
        return pts[-1][1]

    LW = [(175.0, 2500), (177.0, 2877), (190.6, 2840), (207.0, 2914), (219.0, 3040), (232.0, 3100)]
    xstep = X(cw["map"][2])

    def top(x):                                                 # roof underside (two rock masses), lumpy
        zc = Z(cw["map"][3]) if x < xstep else Z(ce["map"][3])
        return zc + 0.6 + 0.8 * fbm(x * 0.08, 2.2, 0.4, 2)

    def lw(z):
        return X(tab(LW, z)) + 0.8 * fbm(z * 0.1, 1.3, 0.7, 2)

    RW = [(150.0, 4878), (166.0, 4900), (182.0, 4950), (200.0, 4935), (215.0, 4890), (232.0, 4860)]

    def rw(z):
        return X(tab(RW, z)) + 0.8 * fbm(z * 0.1, 5.3, 0.2, 2) if z > 150.0 else X(ew["map"][2]) + 60.0

    def dist(x, z):
        k = 5.0
        ds = (top(x) - z, x - lw(z), rw(z) - x, z - 80.0)
        return -k * math.log(sum(math.exp(-max(-20.0, d) / k) for d in ds))

    Y_OUT, T = -41.0, 2.5

    def sheet_y(x, z):
        t = max(0.0, min(1.0, dist(x, z) / T))
        return lerp(Y_OUT, 97.0 + 1.5 * fbm(x * 0.05, z * 0.05, 3.1, 2), t * t * (3.0 - 2.0 * t))

    def bisect(f, a, b):
        fa = f(a)
        for _ in range(26):
            m = (a + b) / 2
            fm = f(m)
            if (fm < 0) == (fa < 0):
                a, fa = m, fm
            else:
                b = m
        return (a + b) / 2

    sx0, sx1 = X(cw["map"][0]), X(ce["map"][2])
    g = Geo()
    K.rock_sheet(g, sx0, sx1, 86.0, Z(cw["map"][1]), sheet_y, 104.0, step=0.8, key="pebble")
    S.add(g, "CaveSheet", R, "CaveWall", "A", REF, layer="ROCK", smooth=50,
          note="one rock sheet: its face comes forward where the cave ends (rounded outline of master B7); depth is completion")
    n = 0
    # pebbles: a band round the outline on the face the elevation sees, the side walls, the roof (A on the master; every stone is C)
    xx = sx0
    while xx < sx1:
        zz = 142.0
        while zz < Z(cw["map"][1]):
            if -9.0 < dist(xx, zz) < 0.3:
                S.put(peb[n % 3], f"Pebbles_Front_{n:04d}", R, "PebbleFace", place(xx - 3.0, Y_OUT - 0.5, zz - 3.0), "A", REF, layer="ROCK",
                      note="pebble band round the cave outline; stones are completion")
                n += 1
            zz += 5.6
        xx += 5.6
    for face, side, rz in (("WestWall", -1, math.pi / 2), ("EastWall", 1, -math.pi / 2)):
        ya = -38.0
        while ya < 90.0:
            zb = 176.0 if side < 0 else 152.0
            while zb < Z(cw["map"][3]) - 3.0:
                xw = lw(zb) if side < 0 else rw(zb)
                if dist(xw - side * 2.0, zb) > 1.0:
                    xs = bisect(lambda x: sheet_y(x, zb) - ya, xw - 4.0, xw + 4.0)
                    m = place(xs - side * 0.3, ya + (6.0 if rz > 0 else 0.0), zb, rz=rz)
                    S.put(peb[n % 3], f"Pebbles_{face}_{n:04d}", R, "PebbleFace", m, "A", REF, layer="ROCK", note="pebbled cavern face; stones are completion")
                    n += 1
                zb += 4.8
            ya += 6.0
    xa = sx0 + 1.0
    while xa < sx1 - 1.0:
        ya = -38.0
        while ya < 60.0:
            zt = top(xa)
            if lw(zt - 3.0) + 2.0 < xa < rw(zt - 3.0) - 2.0:
                zs = bisect(lambda z: sheet_y(xa, z) - ya, zt - T - 4.0, zt + 1.0)
                S.put(peb[n % 3], f"Pebbles_Roof_{n:04d}", R, "PebbleFace", place(xa, ya, zs + 0.4, rx=math.pi / 2), "A", REF, layer="CEILING",
                      note="pebbled cavern roof; stones are completion")
                n += 1
            ya += 4.8
        xa += 6.0
    g = Geo()
    K.stalactite_field(g, X(cw["map"][0]) + 2.0, X(cw["map"][2]) - 2.0, -30.0, 60.0, lambda x, y: Z(cw["map"][3]) + 0.5, 150, seed=2, lmin=2.0, lmax=7.0, key="pebble")
    S.add(g, "RoofStalactites", R, "Stalactites", "A", REF, layer="CEILING", smooth=50)
    # The cavity stays open (A: the master draws only faint forms in it). The two spires seen above the sanctum roof
    # line stand on that roof at its back edge (B); the faint tall form at the east end is a far tower against the
    # back wall of the cavern, standing on its floor (C). Nothing hangs in the air.
    zr = Z(1082) + 0.5                                           # sanctum roof slab (see sanctum.py)
    for eid, sx_off, zb in (("SpireA", 0.0, zr + 0.02), ("SpireB", 0.75, zr + 1.0)):
        e = S.el(R, eid)
        cx, r = (X(e["map"][0]) + X(e["map"][2])) / 2 + sx_off, (X(e["map"][2]) - X(e["map"][0])) / 2 * 0.85
        z1 = Z(e["map"][1])
        cy = 54.4
        g = Geo().use("stone_far_trim")
        g.revolve([(r * 1.15, zb), (r * 1.15, zb + 1.4), (r * 0.95, zb + 1.8), (r * 0.8, zb + 3.2), (r * 0.62, lerp(zb, z1, 0.5)),
                   (r * 0.3, lerp(zb, z1, 0.85)), (0.04, z1)], segs=14, m=place(cx, cy, 0))
        for k in range(3):
            zz = lerp(zb + 1.8, z1, 0.15 + 0.22 * k)
            g.ring_arc((cx, cy, zz), r * (0.95 - 0.2 * k), 0, TAU, 0.1, n=14, plane="XY", segs=4)
        S.add(g, eid, R, "RoofSpire", "B", e["ref"], note="spire on the back edge of the sanctum roof; the master shows it above the roof line, its depth is completion")
    e = S.el(R, "BackTowerC")
    tx0, tx1, tz1 = X(e["map"][0]), X(e["map"][2]), Z(e["map"][1])
    P.tower(S, R, "BackTowerC", (tx0 + tx1) / 2, 90.0, -4.0, tz1, (tx1 - tx0) / 2 * 0.85, windows=e["windows"] + 4, roof=e["roof"], seed=46, leaf=(3.0, 7.6), tier=9.0,
            ry_scale=0.8, far=True, ev="C", ref=e["ref"], layer="BACKDROP", note="far tower against the cavern back wall, standing on the cavern floor")
    # FrontTowerA of the layout is not built here: the stage 2 sample replaced it with its own viewer-side tower
    # (COT_FrontTower_C, build_plaza.py), which stays in the structure file
    S.cam_auto(R, (X(ww["map"][0]), X(ew["map"][2]), -42.5, 80.0, 90.0, 232.0), ref=REF, views=("front",), front_hide=("FRONT",))   # stands in front of the roof rock (front at y -41)
    S.camera("CavityUp", R, (-8.0, -30.0, 184.0), look=(22.0, 50.0, 214.0), lens=18.0, kind="view", hide=("CAVESHELL",), purpose="inside the rain cavity: pebble roof, rounded walls and the spire")
    S.camera("FromSpireTop", R, (38.0, -4.0, 216.0), look=(-30.0, 40.0, 170.0), lens=24.0, kind="view", hide=("CAVESHELL",), purpose="from the telescope room over the sanctum roofs")


# ============================================================================ GroundCorridorEast
def ground_corridor_east(S):
    R = "GroundCorridorEast"
    REF = "master C8 (no local screenshot)"
    st = dict(P.STYLES["corridor"], bay=4.4, fringe=True, back=("blind", "niche", "lancet"), lamp="string")
    up = dict(S.el(R, "Upper"), floors=[3587])
    ui = P.stack(S, R, up, st, door_y={"L": 1.0, "R": 0.4}, ext_faces=())
    lo = S.el(R, "Lower")
    li = P.stack(S, R, lo, st, door_y={"R": -2.8}, ext_faces=())
    g = Geo()
    # braces drawn under the lower corridor (A) and the steps that join the two levels and the east ground (C)
    g.use("stone_far_trim")
    for k in range(6):
        bx = li["x0"] + 2.0 + (li["x1"] - li["x0"] - 4.0) * k / 5
        g.tube([(bx - 1.5, li["yf"] - 0.2, li["bottom"] - 2.6), (bx, li["yf"] - 0.2, li["bottom"])], 0.16, segs=6)
        g.tube([(bx + 1.5, li["yf"] - 0.2, li["bottom"] - 2.6), (bx, li["yf"] - 0.2, li["bottom"])], 0.16, segs=6)
    P.stairs(g, li["x0"] - 2.4, li["x0"] + 3.0, -1.5, 3.5, ui["floors"][0], li["floors"][0], step=0.45, key="stone")
    g.use("stone")
    g.box(li["x0"] - 3.2, li["x0"] + 0.6, -5.0, 7.0, li["floors"][0] - 0.5, ui["floors"][0] - 0.5)
    S.add(g, "BracesAndSteps", R, "CorridorBraces", "A", REF, note="braces are on the master; the steps between the two corridors are completion (C)")
    sett = S.kit("FU_settee_f", lambda: FU.k_settee())          # a row of sofas in the upper corridor (A: master C8)
    for k in range(5):
        S.put(sett, f"Sofa_{k}", R, "Furniture", place(lerp(ui["x0"] + 3.5, ui["x1"] - 3.5, k / 4), ui["yb"] - 2.0, ui["floors"][0] + 0.01), "A", REF,
              note="sofas along the back wall as on the master; exact count is completion")
    g = Geo().use("stone_far_trim")                              # cross-shaped posts in the lower corridor (A: master C8)
    for k in range(4):
        px = lerp(li["x0"] + 4.0, li["x1"] - 4.0, k / 3)
        g.box(px - 0.18, px + 0.18, 2.0, 2.36, li["floors"][0], li["floors"][0] + 2.8)
        g.box(px - 0.8, px + 0.8, 2.0, 2.36, li["floors"][0] + 1.9, li["floors"][0] + 2.25)
        g.ellipsoid((px, 2.18, li["floors"][0] + 0.25), (0.9, 0.7, 0.35), segs=12, steps=6)
    S.add(g, "CrossPosts", R, "CrossPost", "A", REF, note="cross-shaped posts with round bases as on the master; their depth is completion")
    P.populate(S, R, "Upper", ui, ["resident_0", "resident_1", "husk_sentry"], 3, seed=14, avoid=[(0, ui["x0"], ui["x1"], ui["yb"] - 2.4, ui["yb"])])
    P.populate(S, R, "Lower", li, ["husk_sentry_low"], 1, seed=15)
    S.cam_auto(R, (ui["x0"], li["x1"] + 2.4, -5.0, 7.0, li["bottom"] - 3.0, ui["zt"] + 1.0), ref=REF, views=("front", "closed", "oblique"))
    S.camera("Interior", R, (ui["x0"] + 1.5, ui["yf"] + 1.2, ui["floors"][0] + 1.6), look=(ui["x1"] - 4.0, ui["yb"] - 0.8, ui["floors"][0] + 1.8), lens=18.0, kind="interior", purpose="upper low corridor")
    S.camera("Context", R, (ui["x0"] - 14.0, ui["yf"] - 38.0, ui["zt"] + 8.0), look=((ui["x0"] + li["x1"]) / 2, 3.0, li["floors"][0]), lens=24.0, kind="view",
             hide=("BACKDROP", "CAVESHELL"), purpose="both corridors with the ground, rock and buildings round them (nothing hidden but the far layers)")


REGIONS = {"TowerBlock": tower_block, "TopCavern": top_cavern, "GroundCorridorEast": ground_corridor_east}
