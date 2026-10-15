"""Stage 3 structure: SoulSanctum.

Layout decisions (level C, recorded in docs/decisions.md):
  * the part of the main body that hangs over the central well (X > -38.6) stands 30 units deeper (Y 18..56), so the well
    over the fountain plaza is open up to the cavern roof; a west bar keeps the original depth and ties it to the rest
  * a rear podium behind the central block and a rock corbel with arcing ribs carry the overhang
  * the link corridor level (map y 1474) is used as a floor in both the left wing and the main body (the stage 1 layout
    had the door 3.7 above the corridor floor)
"""
import math

import cot_assets as A
import cot_kit as K
import cot_furnish as FU
import cot_parts as P
import cot_shell as SH
from cot_geo import Geo, TAU, lerp, place, rng
from cot_s3 import X, Z

DY = 30.0
XS = X(3151)                                   # -38.6: east face of the central block, where the overhang begins
EAST_Y = (-12.0 + DY, 26.0 + DY)               # (18, 56)
REF_CORE = "01_Soul_Sanctuary/Soul_Sanctuary_core.jpg; master B3_sanctum"


def soul_sanctum(S):
    R = "SoulSanctum"
    st = dict(P.STYLES["sanctum"], back=("oval", "noble", "tall", "shelf_pale", "lotus"))
    me = S.el(R, "Main")
    mx0, mx1 = X(me["map"][0]), X(me["map"][2])
    floors_map = [1166, 1250, 1474, 1562, 1670, 1790, 1910]
    levels = {4: dict(back=("tall", "noble", "tall"), glass="glass_white", lamp="orb"), 5: dict(back=("oval", "noble", "lotus"), lamp="string"),
              6: dict(back=("lancet", "noble", "tall", "lancet"), lamp="string"), 0: dict(back=("oval", "noble", "shelf_pale")),
              3: dict(back=("shelf_pale", "noble", "oval", "lotus"))}

    # ---- main body, east wing over the well (A rooms; C depth position). Read from the master (B3 enlarged, 50-unit grid
    # crops in _work/stage03/grid/): the wing is not one grid. Under the dome runs one top storey; below it the core rooms
    # (map x 3151-3600) keep the stage 1 floors, a black spine (map x 3600-3650) parts them from the east rooms
    # (map x 3650-3888), which have their own, tighter floors, a double-height room at map y 1290-1575 and a lowest storey
    # that steps in to map x 3765. A black mass runs down the west side of the core (cells; bays 71.9 map units from 3160).
    elev = [3222, 3258, 1500, 1920]
    de = S.el(R, "Dome")
    dcx, drx = (de["map"][0] + de["map"][2]) / 2, (de["map"][2] - de["map"][0]) / 2
    dcy = (EAST_Y[0] + EAST_Y[1]) / 2
    top = dict(me, id="MainTop", map=[3151, me["map"][1], 3650, 1166], floors=[1166], doors=[],
               voids=[[dcx - 0.68 * drx, dcx + 0.68 * drx, 1075, 1090]])     # opening under the dome (D-361)
    ti = P.stack(S, R, top, st, y=EAST_Y, levels={0: levels[6]}, side_open=("L",), ext_faces=("N",), shaft_y=(dcy - 0.68 * 15.5, dcy + 0.68 * 15.5),
                 note="top storey under the dome and the louvre roofs (A)")
    core = dict(me, id="MainCore", map=[3151, 1166 + 7.5, 3600, me["map"][3]], floors=[f for f in floors_map if f > 1166], voids=[elev], doors=[])
    core_cells = [(i, 3151, 3218) for i in (0, 1, 2, 3, 4, 5)] + [(0, 3262, 3304), (2, 3440, 3600), (1, 3530, 3600), (0, 3540, 3600)]   # black masses; the glass column stays clear (D-374)
    ei = P.stack(S, R, core, st, y=EAST_Y, levels={i: v for i, v in levels.items() if i < 6}, side_open=("L",), shaft_y=(34.8, 39.2), roof=False,
                 ext_faces=("N",), cells=core_cells, note="core rooms of the east wing (A rooms; depth position C)")
    XR, XL = 3650, 3748
    east = dict(me, id="MainEast", map=[XR, 1118, me["map"][2], 1575], floors=[1180, 1240, 1290, 1575], voids=[], doors=[])
    ri = P.stack(S, R, east, st, y=EAST_Y, levels={0: dict(back=("tall", "oval"), glass="glass_white", lamp="orb"), 3: levels[6], 1: dict(back=("oval", "lotus"))},
                 ext_faces=("R", "N"), note="east rooms with their own floors; the double-height room is A (master B3 enlarged)")
    east_mid = dict(me, id="MainEastMid", map=[XR, 1575 + 7.5, XL, 1775], floors=[1650, 1710, 1775], voids=[], doors=[])
    rmi = P.stack(S, R, east_mid, st, y=EAST_Y, roof=False, ext_faces=("R", "N"), levels={1: dict(back=("noble", "oval", "noble"))},
                  note="the east rooms step in under the double-height room (A outline, master B3 enlarged; D-374)")
    g = Geo().use("wall_deep")                                   # black ledge under the step, ragged (A: master)
    g.box(X(XL), X(3800), EAST_Y[0] + 0.02, EAST_Y[1] - 0.02, Z(1610), ri["bottom"])
    SH.hanging_fringe(g, X(XL) + 0.1, X(3800) - 0.1, EAST_Y[0] - 0.1, Z(1610) - 0.2, 1.6, seed=24)
    S.add(g, "StepLedge", R, "SolidMass", "A", "master B3 enlarged: black mass under the east rooms' step")
    east_low = dict(me, id="MainEastLow", map=[XR, 1775 + 7.5, XL, 1850], floors=[1850], voids=[], doors=[])
    rli = P.stack(S, R, east_low, st, y=EAST_Y, roof=False, ext_faces=("R", "N"), note="lowest east room, stepped in as on the master (A outline)")
    fl = sorted(ei["floors"] + ti["floors"])
    zt = ti["zt"]
    g = Geo().use("wall_deep")                                   # the black spine between the core and the east rooms (A: black on the master)
    g.box(X(3600), X(XR), EAST_Y[0] + 0.02, EAST_Y[1] - 0.02, Z(1880), ti["bottom"])
    SH.hanging_fringe(g, X(3600) + 0.1, X(XR) - 0.1, EAST_Y[0] - 0.1, ti["bottom"] - 0.2, 1.4, seed=21)
    for zf in (Z(1474), Z(1670), Z(1790)):
        SH.hanging_fringe(g, X(3600) + 0.1, X(XR) - 0.1, EAST_Y[0] - 0.1, zf - 0.2, 1.6, seed=int(zf))
    SH.hanging_fringe(g, X(3600) + 0.1, X(XR) - 0.1, EAST_Y[0] + 0.3, Z(1880), 2.2, seed=22)
    S.add(g, "Spine", R, "SolidMass", "A", "master B3 enlarged: black band between the core rooms and the east rooms")
    g = Geo()                                                    # ragged fringe under the east rooms, which end higher than the core
    SH.hanging_fringe(g, X(XR) + 0.2, X(XL) - 0.2, EAST_Y[0] + 0.5, rli["bottom"], 3.0, seed=12)
    SH.hanging_fringe(g, X(XL) + 0.2, mx1 - 0.3, EAST_Y[0] + 0.5, ri["bottom"], 2.6, seed=13)
    SH.hanging_fringe(g, EAST_Y[0] + 0.5, EAST_Y[1] - 0.5, X(XL) - 0.4, rli["bottom"], 3.0, seed=14, axis="Y")
    SH.hanging_fringe(g, EAST_Y[0] + 0.5, EAST_Y[1] - 0.5, mx1 - 0.4, ri["bottom"], 2.6, seed=15, axis="Y")
    S.add(g, "StepFringe", R, "UndersideFringe", "A", "master B3_sanctum: fringe under the stepped east end")
    # ---- west bar at the original depth, running back to the wing (hinge)
    west = dict(me, id="MainWest", map=[me["map"][0], me["map"][1], 3151, me["map"][3]], floors=floors_map, voids=[],
                doors=[["L", 1474]] + [["R", f] for f in floors_map])
    west_levels = dict(levels)
    for i in (2, 3, 5):                                          # storeys drawn black on the master over the west bar
        west_levels[i] = dict(levels.get(i, {}), solid=True)
    wi = P.stack(S, R, west, dict(st, bay=4.9, partition=0, inner=False), y=(-12.0, EAST_Y[1]), levels=west_levels, door_y={"L": 1.0, "R": 37.0}, ext_faces=("R", "L", "N"),
                 cells=[(4, 3000, 3060)],
                 note="west bar keeps the stage 1 depth and continues back to the east wing")
    P.lift(S, R, S.el(R, "Elevator"), y=(34.8, 39.2), back="chevron", trim="trim_pale", ref="01_Soul_Sanctuary/Soul_Sanctuary_bottom1.jpg; Soul_Sanctuary_middle1.jpg")
    el_ = S.el(R, "Elevator")                                    # the master draws this run as a tall ribbed glass column (A; D-374)
    P.glass_pillar(S, R, "LiftGlass", (X(el_["map"][0]) + X(el_["map"][2])) / 2, 33.4, 1.15, Z(el_["map"][3]) + 0.2, Z(el_["map"][1]), "A", "master B3 enlarged",
                   note="glass column in front of the lift shaft through the core storeys; its depth position is completion")
    for k, py in enumerate((EAST_Y[0] + 6.0, EAST_Y[0] + 19.0, EAST_Y[1] - 6.0)):
        fe = S.el(R, "FacadeGlassA")
        P.glass_pillar(S, R, f"FacadeGlass_{k}", mx1 + 0.95, py, 0.87, ri["bottom"] + 0.3, Z(fe["map_y"][0]), "A" if k == 0 else "C",
                       "01_Soul_Sanctuary/Soul_Sanctuary_bottom2.jpg; Soul_Sanctuary_middle2.jpg", note="upper run, on the east face of the upper storeys")
        P.glass_pillar(S, R, f"FacadeGlassLow_{k}", X(XL) + 0.95, py, 0.8, Z(fe["map_y"][1]), Z(1610) - 0.3, "A" if k == 0 else "C",
                       "01_Soul_Sanctuary/Soul_Sanctuary_bottom2.jpg; master B3 enlarged", note="lower run, on the stepped-in east face")
    for k, py in enumerate((-9.0, 3.0, 14.5)):                 # the same glass columns on the bar's face over the well (C)
        P.glass_pillar(S, R, f"WestBarGlass_{k}", XS + 0.95, py, 0.87, fl[0] + 1.0, fl[4], "C", "repeat of the facade pillar on the face that now overlooks the well")

    # ---- lower bright hall hanging under the wing (A: Soul_Sanctuary_bottom.jpg)
    le = dict(S.el(R, "Lower"), map=[3200, 1930, 3590, 2283])
    li = P.stack(S, R, le, st, y=(20.0, 50.0), levels={0: dict(back=("tall", "oval", "tall"), glass="glass_white", lamp="orb"), 1: dict(back=("lotus", "oval"))},
                 ext_faces=("R", "L", "N"), cells=[(1, 3200, 3400)])
    g = Geo().use("wall_deep")                                   # east end of the upper storey: a black mass hanging over the well (A: master)
    g.box(li["x1"] + 0.02, X(3700), 20.0, 50.0, Z(2078) - 0.3, li["zt"])
    SH.hanging_fringe(g, li["x1"] + 0.2, X(3700) - 0.2, 19.8, Z(2078) - 0.4, 2.8, seed=26)
    SH.hanging_fringe(g, 20.2, 49.8, X(3700) - 0.2, Z(2078) - 0.4, 2.4, seed=27, axis="Y")
    S.add(g, "LowerEastMass", R, "SolidMass", "A", "master B3_sanctum: black mass east of the lower hall, ending above its floor")
    P.glass_pillar(S, R, "LowerGlass", li["x1"] + 0.9, 23.0, 0.85, li["floors"][0] + 0.4, li["floors"][1] - 0.6, "A", "01_Soul_Sanctuary/Soul_Sanctuary_bottom.jpg (ribbed glass at the right edge)")
    g = Geo()                                                    # oval ring hung in drapery over the hall (A: bottom.jpg)
    cxh = (li["x0"] + li["x1"]) / 2
    g.use("trim_pale")
    g.ring_arc((cxh, 35.0, li["floors"][0] + 8.4), 1.0, 0, TAU, 0.12, n=28, plane="XZ", segs=6, m=place(cxh, 35.0, li["floors"][0] + 8.4) @ place(s=(1.3, 1.0, 2.0)) @ place(-cxh, -35.0, -(li["floors"][0] + 8.4)))
    SH.hanging_fringe(g, li["x0"] + 1.0, li["x1"] - 1.0, 35.0, li["floors"][1] - 0.5, 2.6, seed=3)
    S.add(g, "Lower_OvalRing", R, "OvalRing", "A", "01_Soul_Sanctuary/Soul_Sanctuary_bottom.jpg")

    # ---- roofs: wide ribbed dome between spiked louvre roofs (A: core_upper.jpg, upper2.jpg)
    REF_TOP = "01_Soul_Sanctuary/Soul_Sanctuary_core_upper.jpg; Soul_Sanctuary_upper2.jpg; master B3_sanctum"
    de = S.el(R, "Dome")
    dx0, dx1 = X(de["map"][0]), X(de["map"][2])
    zr = zt + 0.5
    g = Geo()
    K.louvre_dome(g, (dx1 - dx0) / 2, 15.5, Z(de["map"][1]) - zt, ribs=14, m=place((dx0 + dx1) / 2, (EAST_Y[0] + EAST_Y[1]) / 2, zr), slat=0.26, cap_base=False)
    S.add(g, "Dome", R, "SanctumDome", "A", REF_TOP, note="depth of the dome is completion", smooth=35)
    P.louvre_band(S, R, "RoofLeft", mx0, dx0 - 0.2, -12.3, EAST_Y[1] + 0.3, zr, zr + 3.4, ev="A", ref=REF_TOP, note="band height read from core_upper.jpg")
    P.louvre_band(S, R, "RoofRight", dx1 + 0.2, X(3672), EAST_Y[0] - 0.3, EAST_Y[1] + 0.3, zr, zr + 3.4, ev="A", ref=REF_TOP)
    P.louvre_roof(S, R, "RoofRightLow", X(3672), mx1 + 0.4, zr - 2.4, zr + 1.0, EAST_Y[0] - 0.3, EAST_Y[1] + 0.3, bays=3, curve_end="E", ev="A",
                  ref="01_Soul_Sanctuary/Soul_Sanctuary_upper2.jpg")

    # ---- what carries the overhang: rear podium, rock corbel, arcing ribs (C)
    P.shell_block(S, R, "Podium", -50.6, -41.2, 21.6, EAST_Y[1], -2.0, fl[0] - 0.5, tier=8.0, seed=9,
                  windows=[("E", y, z, 2.4, 6.0) for y, z in ((44.0, 30.0), (50.0, 52.0), (42.0, 74.0), (49.0, 96.0))] + [("N", -45.0, z, 2.4, 6.0) for z in (24.0, 60.0, 92.0)],
                  ev="C", ref="support under the west bar behind the central block", note="not shown by any reference; a fringed tower mass that carries the sanctum (C)")
    g = Geo().use("wall_sanctum")
    g.box(mx0, XS, -9.0, 17.0, Z(1990) + 0.5, fl[0] - 0.5)
    S.add(g, "WestBar_Base", R, "WestBarBase", "C", "solid between the central block neck and the sanctum floor")
    g = Geo()
    K.rock(g, -40.2, li["x0"] - 0.2, 20.0, 52.0, 78.0, fl[0] - 0.6, seed=4, amp=1.2)
    K.rock(g, li["x0"] - 2.0, -16.0, 21.0, 49.0, li["bottom"] - 9.0, li["bottom"] - 0.2, seed=5, amp=1.3)
    K.rock(g, li["x1"] - 0.5, X(XL) - 0.5, 20.0, 54.0, rli["bottom"] - 6.0, rli["bottom"] - 0.1, seed=6, amp=1.0)
    S.add(g, "Corbel", R, "RockCorbel", "A", "master B3_sanctum: dark ragged mass under the right half of the sanctum",
          note="the dark underside is on the master; its form as a rock corbel springing from the podium is completion (C)", smooth=70)
    g = Geo()
    SH.hanging_fringe(g, li["x0"], li["x1"], 20.5, li["bottom"], 3.6, seed=7)
    SH.hanging_fringe(g, li["x0"], li["x1"], 49.5, li["bottom"], 3.6, seed=8)
    SH.hanging_fringe(g, li["x1"], X(3600), EAST_Y[0] + 0.5, fl[0] - 0.6, 4.2, seed=9)
    S.add(g, "UndersideFringe", R, "UndersideFringe", "A", "master B3_sanctum: ragged fringe under the overhang")
    # (the arcing corbel ribs of D-342 are left out: on the check images they read as stray poles across the lower bridge, D-361)

    # ---- left wing, arena, hall under it, book rooms, link corridor (A; depth and backs C)
    lw = dict(S.el(R, "LeftWing"), floors=[1142, 1298, 1474, 1574, 1670, 1802], doors=[["R", 1474]])
    lwi = P.stack(S, R, lw, dict(st, back=("chevron", "oval", "noble", "tall", "chevron")), door_y={"R": 1.0}, levels={5: dict(lamp="string")}, ext_faces=("R",),
                  cells=[(0, 2175, 2253), (2, 2409, 2487), (3, 2253, 2331), (5, 2409, 2487)])        # black parts between the rooms (master B3 enlarged, D-370)
    gt = S.el(R, "LeftGlassTower")
    P.glass_pillar(S, R, "LeftGlassTower", lwi["x1"] + 2.1, -7.6, 2.0, Z(gt["map_y"][1]), Z(gt["map_y"][0]), "A", "master B3_sanctum",
                   note="stands in front of the link corridor, whose floor is lower than the tower's top (depth position C)")
    ar = dict(S.el(R, "Arena"), map=[2580, 1082, 2880, 1274])     # the cave runs east to the pavilion (A: master B3_sanctum)
    ai = P.stack(S, R, ar, dict(st, wall="wall_deep", back=("niche",), lamp=None, partition=0, inner=False), decor=False, lamps=False, ext_faces=(), side_open=("L", "R"), roof=False)     # the cave sheet closes it (D-374)
    g = Geo()
    g.use("cushion")
    g.revolve([(3.0, 0.0), (3.2, 0.25), (3.2, 0.5), (0.05, 0.5)], segs=24, m=place((ai["x0"] + ai["x1"]) / 2, 3.0, ai["floors"][0]))
    K.stalactite_field(g, ai["x0"] + 1.0, ai["x1"] - 1.0, ai["yf"] + 1.0, ai["yb"] - 1.0, lambda x, y: ai["zt"] - 0.9, 18, seed=4, lmin=1.4, lmax=3.4, key="wall_green")
    S.add(g, "Arena_Dais", R, "ArenaDais", "A", "master B3_sanctum: cyan cave room with a pale dais (no local screenshot)", note="its entrance is not shown", smooth=45)
    # the arena is a cave on the master: uneven rock ceiling, rounded upper corners, a domed pavilion at its east end (D-370)
    g = Geo()
    zt_a, zf_a = ai["zt"], ai["floors"][0]
    K.rock_roof(g, ai["x0"] + 0.4, ai["x1"] - 0.4, ai["yf"] + 0.8, ai["yb"] - 0.4, lambda x: zt_a - 1.1 - 0.6 * math.sin((x - ai["x0"]) * 0.45), zt_a + 0.2, step=0.9, amp=0.6,
                seed=71, key="mass_black")                         # behind the face of the cave sheet below; the old corner fillets are replaced by that sheet (D-383)
    px_ = ai["x1"] - 3.6
    g.use("trim_pale")
    for dx, dy in ((-1.5, -1.3), (1.5, -1.3), (-1.5, 1.3), (1.5, 1.3)):
        g.tube([(px_ + dx, 4.0 + dy, zf_a), (px_ + dx, 4.0 + dy, zf_a + 2.8)], 0.09, segs=6)
    K.louvre_dome(g, 1.9, 1.7, 1.7, ribs=10, m=place(px_, 4.0, zf_a + 2.8), slat=0.2)
    S.add(g, "Arena_Cave", R, "ArenaCave", "A", "master B3_sanctum: the cyan room is a cave with a domed pavilion at its east end",
          note="ceiling form and pavilion size are completion", smooth=45)
    # the cave outline (A: master B3_sanctum): an oval cave on a flat floor, one sheet whose face comes forward outside it
    acx, aa = (ai["x0"] + ai["x1"]) / 2, (ai["x1"] - ai["x0"]) / 2 - 0.2
    azc, ab = zf_a + (zt_a - zf_a) * 0.45, (zt_a - zf_a) * 0.62

    def a_dist(x, z):
        de = (1.0 - (abs((x - acx) / aa) ** 3 + abs((z - azc) / ab) ** 3) ** (1.0 / 3.0)) * min(aa, ab)
        k = 0.8
        return -k * math.log(math.exp(-max(-20.0, de) / k) + math.exp(-max(-20.0, z - zf_a + 1.0) / k))

    def a_y(x, z):
        t = max(0.0, min(1.0, a_dist(x, z) / 1.2))
        return lerp(ai["yf"] + 0.6, ai["yb"] - 0.3, t * t * (3.0 - 2.0 * t))     # behind the cyan face inside the outline

    g = Geo()
    K.rock_sheet(g, ai["x0"] + 0.05, ai["x1"] - 0.05, zf_a - 0.6, zt_a - 0.05, a_y, ai["yb"] - 0.05, step=0.35, key="mass_black")
    g.use("wall_green")                                          # the cyan cave face, seen only inside the outline (the black sheet covers the rest)
    g.box(ai["x0"] + 0.3, ai["x1"] - 0.3, ai["yb"] - 0.62, ai["yb"] - 0.5, zf_a, zt_a - 0.3)
    S.add(g, "Arena_CaveSheet", R, "ArenaCave", "A", "master B3_sanctum: oval cyan cave", note="the outline is read from the master; depth is completion", smooth=50)
    P.pad_field(S, R, "Arena_Pads", ai["x0"] + 1.0, ai["x1"] - 1.0, ai["floors"][0] + 0.6, ai["zt"] - 1.0, ai["yb"] - 0.8, 30, seed=5, facing="front", size=(0.6, 1.2), ev="A",
                ref="master B3_sanctum", keep=lambda a_, b_: b_ < zf_a + 2.0 or a_ < ai["x0"] + 3.0 or b_ > zt_a - 2.6)
    P.stack(S, R, S.el(R, "HallUnderArena"), dict(st, back=("oval", "lotus"), lamp="string", partition=0, inner=False), ext_faces=())
    P.stack(S, R, S.el(R, "BookRooms"), dict(st, back=("shelf_pale", "oval", "shelf_pale"), partition=0), ext_faces=())
    lc = S.el(R, "LinkCorridor")
    P.stack(S, R, lc, dict(st, back=("oval",), partition=0, inner=False, lamp="string", bay=4.2), door_y={"L": 1.0, "R": 1.0}, ext_faces=())

    # ---- floating shell blocks, scrap heaps (A)
    blk2 = S.kit("shell_block_2", lambda: SH.k_shell_block(2))
    blk1 = S.kit("shell_block_1", lambda: SH.k_shell_block(1))
    heap = [S.kit(f"heap_{v}", lambda v=v: SH.k_heap(v)) for v in range(2)]
    spots = [(-22.0, 40.0, fl[4] + 3.4, blk2), (-12.0, 36.0, fl[4] + 6.2, blk1), (-27.0, 44.0, fl[4] + 8.6, blk2), (-2.0, 42.0, fl[4] + 4.4, blk2),
             (cxh - 5.0, 34.0, li["floors"][0] + 3.0, blk2), (cxh + 4.5, 37.0, li["floors"][0] + 5.2, blk2), (cxh, 31.0, li["floors"][0] + 1.6, blk2),
             (lwi["x0"] + 6.0, 4.0, lwi["floors"][2] + 3.2, blk2), (lwi["x0"] + 14.0, 6.0, lwi["floors"][4] + 2.6, blk1)]
    for k, (bx, by, bz, kit) in enumerate(spots):
        S.put(kit, f"ShellBlock_{k}", R, "ShellBlock", place(bx, by, bz), "A", "01_Soul_Sanctuary/Soul_Sanctuary_bottom.jpg; Soul_Sanctuary_core.jpg", note="hovering platform, as in the game")
    rand = rng(3)
    for k in range(14):
        info = (ei, ri, ti, rmi, ei)[k % 5] if k < 10 else li
        pool = info["room"]["storeys"]
        for _ in range(40):
            i, zf, top = pool[int(rand(0, len(pool)))]
            hx, hy, s = rand(info["room"]["x0"], info["room"]["x1"]), rand(info["room"]["yf"], info["room"]["yb"]), rand(0.7, 1.2)
            if info["room"]["free"](i, hx, hy, 1.2 * s):
                S.put(heap[k % 2], f"Heap_{k}", R, "ScrapHeap", place(hx, hy, zf, rz=k * 0.9, s=s), "A", "01_Soul_Sanctuary/Soul_Sanctuary_bottom.jpg")
                break

    # ---- creatures (D-347): soul warriors (user request; A: master B3 enlarged), soul twisters (A), soul blobs (C)
    P.populate(S, R, "EastWarrior", ei, ["soul_warrior"], 1, seed=31, storeys={4})
    P.populate(S, R, "East", ei, ["soul_twister", "mistake_0", "mistake_1", "soul_twister", "husk_sentry"], 6, seed=3)
    P.populate(S, R, "EastRooms", ri, ["soul_twister", "mistake_1", "husk_sentry", "soul_warrior"], 4, seed=8)
    P.populate(S, R, "EastLow", rli, ["mistake_0"], 1, seed=9)
    P.populate(S, R, "EastMid", rmi, ["soul_warrior", "mistake_1"], 2, seed=12)
    P.populate(S, R, "Top", ti, ["soul_twister", "husk_sentry"], 2, seed=10)
    P.populate(S, R, "West", wi, ["mistake_0", "soul_twister"], 3, seed=4)
    P.populate(S, R, "LowerWarrior", li, ["soul_warrior"], 1, seed=51, storeys={0})
    P.populate(S, R, "Lower", li, ["soul_twister", "mistake_1"], 3, seed=5)
    P.populate(S, R, "LeftWing", lwi, ["soul_twister", "mistake_0", "husk_sentry"], 5, seed=6)
    # floating segmented platforms in the tall halls (A: master B3 enlarged)
    for k, (inf, st_i, mxp, fy, dz, n) in enumerate(((ei, 4, 3378, 0.35, 3.6, 3), (ei, 4, 3484, 0.55, 5.0, 2), (ri, 0, 3780, 0.3, 6.5, 2), (ri, 0, 3720, 0.6, 11.0, 2),
                                                      (ti, 0, 3330, 0.4, 3.4, 2), (ti, 0, 3560, 0.5, 2.9, 3))):
        zf = next(z for j, z, top in inf["storeys"] if j == st_i)
        S.put(S.kit(f"FU_pill_{n}", lambda n=n: FU.k_pill_platform(n)), f"PillPlatform_{k}", R, "PillPlatform",
              place(X(mxp), lerp(EAST_Y[0] + 2.0, EAST_Y[1] - 2.0, fy), zf + dz), "A", "master B3 enlarged (Soul Sanctum)",
              note="floating platform; its place in depth is completion")

    # ---- cameras
    S.cam_front("MainSection", R, (3000, 990, 3900, 2300), y=EAST_Y[0] - 2.0, ref=REF_CORE, purpose="section through the east wing and lower hall, comparable with master B3_sanctum")
    S.cam_front("WestSection", R, (2150, 970, 3160, 1900), y=-13.5, ref="master B3_sanctum", purpose="left wing, arena, book rooms, corridor and west bar")
    S.cam_auto(R, (lwi["x0"], mx1, -12.0, EAST_Y[1], li["bottom"] - 10.0, zt + 7.0), ref="master B3_sanctum", views=("closed", "oblique", "obliqueR", "back"))
    S.camera("GreatHall", R, (X(3250), EAST_Y[0] + 3.0, fl[4] + 2.0), look=(X(3560), EAST_Y[1] - 1.0, fl[4] + 7.0), lens=18.0, kind="interior",
             purpose="great hall with the tall cold white windows, compare Soul_Sanctuary_core.jpg", ref=REF_CORE)
    S.camera("DomeHall", R, (XS + 4.0, EAST_Y[0] + 3.0, fl[6] + 1.8), look=((dx0 + dx1) / 2, EAST_Y[1] - 4.0, fl[6] + 3.2), lens=18.0, kind="interior",
             purpose="top hall under the dome, compare Soul_Sanctuary_core_upper.jpg", ref="01_Soul_Sanctuary/Soul_Sanctuary_core_upper.jpg")
    S.camera("LowerHall", R, (li["x0"] + 2.0, 22.5, li["floors"][0] + 2.0), look=(li["x1"] - 3.0, 46.0, li["floors"][0] + 5.5), lens=18.0, kind="interior",
             purpose="lower bright hall, compare Soul_Sanctuary_bottom.jpg", ref="01_Soul_Sanctuary/Soul_Sanctuary_bottom.jpg")
    S.camera("LeftWing", R, (lwi["x0"] + 1.6, lwi["yf"] + 1.6, lwi["floors"][4] + 1.8), look=(lwi["x1"] - 2.0, lwi["yb"] - 3.0, lwi["floors"][4] + 3.6), lens=18.0, kind="interior",
             purpose="left wing storey, compare Soul_Sanctuary_left.jpg", ref="01_Soul_Sanctuary/Soul_Sanctuary_left.jpg")
    S.camera("Roof", R, (-2.0, -30.0, zt + 22.0), look=((dx0 + dx1) / 2, 37.0, zt + 2.0), lens=30.0, kind="view", hide=("CEILING", "CAVESHELL", "BACKDROP"), purpose="dome and louvre roofs from above")
    S.camera("FromPlaza", R, (12.0, -60.0, 20.0), look=(-15.0, 30.0, 110.0), lens=22.0, kind="view", purpose="the sanctum seen from the plaza quay looking up the open well")
    S.camera("EastFace", R, (31.0, -12.0, 150.0), look=(11.0, 37.0, 140.0), lens=20.0, kind="side", hide=("CAVESHELL", "BACKDROP"), purpose="east face with the glass columns over the rain cavity")
    S.camera("Underside", R, (-8.0, -6.0, 52.0), look=(-26.0, 36.0, 92.0), lens=18.0, kind="view", purpose="podium, corbel, ribs and the underside of the lower hall")


REGIONS = {"SoulSanctum": soul_sanctum}
