"""Stage 3 structure: central well group - CentralWell, FountainPlaza, CentralBlock, LowerBridge, PlazaEastHouse.

Layout corrections made here (all level C, see docs/decisions.md D-301..):
  * the lower bridge runs along the viewer-side edge of the well (Y -19.5..-12.5) so the well over the plaza is open
  * the east-shore overhang no longer covers the plaza (it keeps to X > 12.5, plus a front piece under the bench room)
  * the stage 2 placeholder solids for the ground gallery and the east house are carved out and replaced by rooms
"""
import math

import bpy

import cot_assets as A
import cot_kit as K
import cot_parts as P
import cot_shell as SH
from cot_geo import Geo, IronCurves, TAU, lerp, place, rng
from cot_s3 import X, Z

GZ = 0.867                       # plaza paving level (stage 2)
BRIDGE_Y = (-19.5, -12.5)
X_BW, X_BE = X(3151), X(4030)    # lower bridge ends: central block east face, tower block corridor


# ============================================================================ CentralWell
def central_well(S):
    R = "CentralWell"
    P.rock(S, R, "Bed", X(3151), X(4270), -16, 44, Z(3680), Z(3625) - 0.3, ev="C", ref="well floor under the water line", layer=None, amp=0.5)
    P.water(S, R, "WaterBack", -78.0, 40.0, 16.0, 100.0, -0.45, ev="C", ref="water behind the plaza: towers of the well stand in it (completion)")
    P.water(S, R, "WaterWest", -38.6, -20.0, 6.5, 16.0, -0.45, ev="C", ref="as above")
    # east-shore overhang: black rock mass under the tower-block corridor (A: master B6), kept clear of the plaza (C)
    g = Geo()
    K.rock(g, 12.5, 36.2, -4.0, 16.0, Z(2860) - 0.3, Z(2704), seed=11, amp=1.1)
    # the slab seen from the well (A: master B6 outline): underside dropping in steps from the west tip, serrated (D-379)
    prof = [(0.0, 58.0), (3.0, 52.5), (9.0, 49.2), (13.0, 49.0), (20.0, 50.0), (28.0, 49.6), (37.0, 50.2)]

    def under(x):
        for (xa, za), (xb, zb) in zip(prof, prof[1:]):
            if xa <= x <= xb:
                z = lerp(za, zb, (x - xa) / (xb - xa))
                break
        else:
            z = prof[-1][1]
        return z + 0.9 * abs(((x * 0.42) % 2.0) - 1.0)
    K.rock_roof(g, 0.2, 12.9, -22.0, -9.0, under, 59.6, step=0.8, amp=0.7, seed=13)
    K.rock_roof(g, 12.5, 36.2, -22.0, -4.0, under, 64.4, step=0.8, amp=0.7, seed=12)
    K.stalactite_field(g, 26.5, 35.6, -3.6, 15.4, lambda x, y: Z(2860) + 0.4, 26, seed=12, lmin=1.2, lmax=4.6)     # jagged underside (A: master B6), clear of the house tower
    K.stalactite_field(g, 1.5, 35.8, -21.4, -9.6, lambda x, y: under(x) + 0.5, 46, seed=13, lmin=1.6, lmax=6.5)
    S.add(g, "Overhang", R, "Overhang", "A", "master B6 dark overhang below the bridge end",
          note="X/Z outline observed; plan shape changed so that the well over the plaza is open (C); points under it are A", smooth=70)
    g = Geo()
    SH.hanging_fringe(g, 12.6, 36.0, -4.2, Z(2860) - 0.3, 3.2, seed=3)
    SH.hanging_fringe(g, -22.0, 16.0, 12.5, Z(2860) + 1.0, 3.6, seed=4, axis="Y")
    SH.hanging_fringe(g, 0.4, 12.8, -9.2, 53.3, 2.4, seed=5)
    SH.hanging_fringe(g, -21.8, -9.2, 0.4, 53.5, 2.4, seed=6, axis="Y")
    S.add(g, "OverhangFringe", R, "OverhangFringe", "A", "master B6: ragged fringe under the overhang")
    # flying sentries in the open well (D-347; C: the master shows sentries of the city, their places here are completion)
    P.creature(S, R, "winged_sentry", "Air_0", -9.0, 24.0, 30.0, rz=0.8)
    P.creature(S, R, "winged_sentry", "Air_1", 6.0, 30.0, 47.0, rz=-2.2)
    box = (X(3151), X(4149), -22.0, 60.0, -1.0, 76.0)
    S.cam_auto(R, box, ref="master B6", views=("front", "oblique", "back"))
    # the stage 2 main reference camera (config/plaza.json): evidence for D-344, the free-standing tower as the statue image shows it
    S.camera("REF_StatueMain", R, (8.5, -36.0, 2.2), rot=(90.0, 0.0, 0.0), lens=28.6, shift=(0.0, 0.1874), kind="ref", hide=(),
             ref="11_Lower_City/Lower_City_statue.jpg", purpose="the stage 2 main reference view with the stage 3 city round it (D-344)")
    S.camera("LookUp", R, (2.0, -30.0, 4.0), look=(-8.0, 20.0, 60.0), lens=18.0, kind="view", hide=(),
             purpose="from the plaza straight up the well: the opening above the statue must be clear to the cavern roof")
    S.camera("BridgeFromPlaza", R, (8.0, 14.0, 10.0), look=(-8.0, -16.0, 55.0), lens=22.0, kind="view", purpose="lower bridge seen from behind the statue")
    S.camera("FromFreeTower", R, (-30.0, 12.0, 30.0), look=(8.0, -8.0, 22.0), lens=24.0, kind="view", hide=("BACKDROP",), purpose="across the well toward the east shore")


def fountain_plaza(S):
    """The plaza itself is the stage 2 sample (kept as is). Stage 3 only adds check cameras from the well side."""
    R = "FountainPlaza"
    S.camera("TopDown", R, (0.0, 4.0, 60.0), look=(0.0, 4.0, 0.0), ortho=64.0, hide=("CEILING",), kind="top", purpose="plan of the plaza with its new neighbours")
    P.creature(S, R, "resident_1", "Plaza_0", -8.5, 0.5, GZ + 0.01, rz=0.6, note="on the paving in front of the statue (C)")
    P.creature(S, R, "resident_2", "Plaza_1", -4.0, 7.5, GZ + 0.01, rz=-0.9, note="on the paving in front of the statue (C)")
    S.camera("FromWestGallery", R, (-14.0, -4.4, 3.0), look=(2.0, 1.0, 4.0), lens=24.0, kind="view", purpose="plaza seen from inside the ground gallery end (connection A)")
    S.camera("FromEastHouseDoor", R, (11.2, 1.5, 2.6), look=(0.0, 0.5, 4.0), lens=24.0, kind="view", purpose="plaza seen from the east house door (connection A)")
    S.camera("HighFront", R, (-6.0, -52.0, 30.0), look=(0.0, 4.0, 12.0), lens=35.0, kind="oblique", purpose="plaza within the open well")


# ============================================================================ CentralBlock
def central_block(S):
    R = "CentralBlock"
    REF_MID = "11_Lower_City/Lower_City_middle.jpg; 11_Lower_City/Lower_City_upper.jpg; master B3_central_lower"
    e = dict(S.el(R, "Stack"))
    e["y"] = [e["y"][0], 15.0]                                # back wall at Y 15: the well's free-standing tower (stage 2) stands from Y 15.5
    # three column groups on their own floors (master B3_central_lower enlarged); 2710..2821 stays the black band
    # black masses over several storeys and thin storeys drawn black (thick floors), D-375
    groups = {"L": (2687, 2843, [2263, 2350, 2497, 2605, 2710, 2821, 2885, 3055, 3130, 3250, 3320, 3451],
                    [(8, 2687, 2770), (1, 2770, 2843), (2, 2770, 2843), (3, 2770, 2843), (5, 2687, 2843), (9, 2687, 2770), (10, 2687, 2770)]),
              "M": (2843, 2966, [2263, 2440, 2605, 2710, 2821, 2885, 3000, 3109, 3208, 3320, 3451],
                    [(1, 2900, 2966), (3, 2843, 2900), (4, 2843, 2900), (8, 2900, 2966), (9, 2900, 2966)]),
              "R": (3018, 3151, [2263, 2330, 2440, 2540, 2615, 2710, 2821, 3019, 3109, 3208, 3320, 3451],
                    [(7, 3018, 3085), (1, 3085, 3151), (2, 3085, 3151), (3, 3018, 3085), (9, 3018, 3085), (10, 3018, 3151)])}
    infos = {}
    for gk, (ga, gb, gfl, gcells) in groups.items():
        ge = dict(e, id=f"Stack{gk}" if gk != "L" else "Stack", map=[ga, e["map"][1], gb, e["map"][3]], floors=gfl,
                  doors=[["R", 3451]] if gk == "R" else [], voids=[[2775, 2815, 3440, 3470]] if gk == "L" else [])
        solid_i = sorted(gfl, reverse=True).index(2710)
        lv = {0: dict(back=("lancet", "noble"), lamp="string"), solid_i: dict(solid=True), solid_i + 1: dict(back=("lancet", "niche", "noble", "lancet"))}
        kc = []
        if gk == "M":
            kc = [(sorted(gfl, reverse=True).index(2885), X(2935) - 1.6, X(2935) + 1.6, 4.6, 7.4)]
        if gk == "R":
            kc = [(0, -51.0, -38.0, -10.0, 15.0)]
        infos[gk] = P.stack(S, R, ge, "blue", levels=lv, skip_bays={(0, 0), (0, 1)} if gk == "R" else None, ext_faces=("R", "N") if gk == "R" else ("N",),
                            rail_skip={(1, 0)} if gk == "L" else (), cells=gcells, keep_clear=kc,
                            note=f"{gk} column group of the central block on its own floors (A outline; depth C)")
    iL, iM, iR = infos["L"], infos["M"], infos["R"]
    info = dict(iL, x1=iR["x1"], floors=iM["floors"])
    x0, x1, yf, yb = iL["x0"], iR["x1"], iL["yf"], iL["yb"]
    g = Geo().use("wall_deep")                                  # dark spine round the herringbone lift (A: black on the master)
    zsb, zst = iL["bottom"], iL["zt"] + 0.5
    for xa, xb in ((X(2966), X(2970)), (X(3010), X(3018))):
        g.box(xa, xb, yf + 0.3, yb, zsb, zst)
    for za, zb_ in ((Z(2272), zst), (Z(2740), Z(2524)), (zsb, Z(3325))):
        g.box(X(2970), X(3010), 2.6, yb, za, zb_) if za < zb_ else None
    SH.hanging_fringe(g, X(2966), X(3018), yf + 0.2, Z(2524) - 0.2, 1.2, seed=31)
    S.add(g, "Spine", R, "SolidMass", "A", REF_MID, note="black spine between the middle and right rooms, round the lift")

    # ---- lifts (A): shafts with slot panels at the floors they pass, spired cars on chains
    fl = info["floors"]
    for eid in ("ShaftUpper", "ShaftLower"):
        se = S.el(R, eid)
        zt, zb = Z(se["map"][1]), Z(se["map"][3])
        panels = [zf - 0.5 - 2.5 for zf in fl if zb + 3.0 < zf < zt + 0.5]
        P.lift(S, R, se, back="plain", panels=panels, ref=REF_MID)
    P.lift(S, R, S.el(R, "GroundShaft"), back="plain", panels=[Z(3497) + 0.1], ref="11_Lower_City/Lower_City_bottom.jpg")

    # ---- shop at the east end of the lowest storey (A: 13_Lighting/Lighting_03.jpg, master C6)
    z0 = fl[0]
    REF_SHOP = "13_Lighting/Lighting_03.jpg; master B3_central_lower"
    g = Geo()
    g.use("wall_purple")
    g.box(-47.6, -39.2, yb - 0.75, yb - 0.6, z0, z0 + 6.4)                 # purple wall lining behind the shelves
    g.use("cushion")
    g.revolve([(1.9, 0.0), (2.05, 0.2), (2.0, 1.0), (2.15, 1.12), (2.15, 1.26), (0.02, 1.26)], segs=20, sx=1.0, sy=0.5, m=place(-43.4, yb - 4.2, z0))
    g.use("trim_purple")
    g.ring_arc((-43.4, yb - 4.2, z0 + 1.2), 1.0, 0, TAU, 0.07, n=24, plane="XY", segs=5, m=None)
    S.add(g, "Shop_Counter", R, "ShopCounter", "A", REF_SHOP, note="counter position in depth is completion")
    for k, sx in enumerate((-45.9, -43.3, -40.9)):
        S.put(S.kit("shelf_2.2_3.4_trim_purple_s", lambda: K.k_shelf_arch(2.2, 3.4, seed=5, kind="pointed")), f"Shop_Shelf_{k}", R, "ShelfArch",
              place(sx, yb - 0.82, z0 + 0.1), "A", REF_SHOP)
    S.put(S.kit("walllamp_pink", lambda: K.k_wall_lamp("lamp_pink")), "Shop_Lamp_0", R, "WallLamp", place(-47.0, yb - 0.8, z0 + 4.4), "A", REF_SHOP)
    S.put(S.kit("signlamp", lambda: sign_lamp()), "Shop_SignLamp", R, "SignLamp", place(-49.5, 2.5, z0), "A", REF_SHOP)
    # ribbed glass pillars and the quarter-round louvre canopy on the well face (A at the front corner; repeats along the depth are C)
    ye = min(yb, 13.0)                                    # east-face fittings stop short of the well's free-standing tower (Y 15.5+)
    for k, py in enumerate((yf + 1.2, 2.0, ye - 1.2)):
        evk = "A" if k == 0 else "C"
        P.glass_pillar(S, R, f"ShopGlassPillar_{k}", x1 + 0.75, py, 0.72, z0 + 0.3, z0 + 4.6, evk, REF_SHOP)
        P.glass_pillar(S, R, f"GlassPillar_{k}", x1 + 0.75, py, 0.8, Z(2990), Z(2640), evk, "11_Lower_City/Lower_City_upper.jpg; master B3_central_lower")
    # the canopies start at the east wall and project at least their quarter-round radius (height), so no part reaches into the rooms
    P.louvre_roof(S, R, "ShopCanopy", x1 + 0.35, x1 + 0.35 + 3.2 + 0.3, z0 + 5.0, z0 + 8.2, yf - 0.4, ye, bays=1, curve_end="E", ev="A",
                  ref="13_Lighting/Lighting_03.jpg; 11_Lower_City/Lower_City_middle.jpg", note="runs the depth of the facade (C)")
    P.louvre_roof(S, R, "MidCanopy", x1 + 0.35, x1 + 0.35 + 2.8 + 0.3, Z(2640) + 0.4, Z(2640) + 3.2, yf - 0.4, ye, bays=1, curve_end="E", ev="A",
                  ref="11_Lower_City/Lower_City_middle.jpg (louvre eave above the glass pillar)", note="runs the depth of the facade (C)")
    g = Geo()
    A.add_corbel_wing(g, place(x1 + 0.2, yf + 0.5, z0 - 0.1), length=1.6, blades=5, key="louvre_frame")
    A.add_corbel_wing(g, place(x1 + 0.2, ye - 0.5, z0 - 0.1), length=1.6, blades=5, key="louvre_frame")
    S.add(g, "EastCorbels", R, "CorbelWing", "A", "11_Lower_City/Lower_City_middle.jpg: feathered brackets at the facade edge")
    # heap of orange finds on the fifth storey (A: Lower_City_upper.jpg, master (2935, 2871))
    g = Geo().use("lamp_warm")
    rand = rng(77)
    for k in range(14):
        g.ellipsoid((X(2935) + rand(-0.9, 0.9), 6.0 + rand(-0.7, 0.7), fl[5] + 0.12 + rand(0, 0.3)), (rand(0.14, 0.24), rand(0.14, 0.24), rand(0.1, 0.16)), segs=8, steps=5)
    S.add(g, "OrangeHeap", R, "OrangeHeap", "A", "11_Lower_City/Lower_City_upper.jpg", note="what the objects are is not identified")

    # ---- dark band between the interiors and the shell towers of the left well (C: black on the master)
    # the left well's shell towers stand partly in this strip: below Z 57 the band starts east of the lower tower, above it
    # it stands behind the upper tower (Y > 12), so the towers stay free-standing
    zs = 57.0
    P.shell_block(S, R, "DarkBand", -76.0, X(2687) - 0.7, yf + 0.5, yb - 0.5, Z(3461), zs, tier=7.5, seed=5,
                  windows=[("S", -73.1, z, 2.2, 5.6) for z in (24.0, 44.0)] + [("N", -73.1, 30.0, 2.2, 5.6)],
                  ev="C", ref="black band on master between the shell towers and the interiors", note="treated as a fringed building mass; windows are completion")
    P.shell_block(S, R, "DarkBandUpper", X(2547), X(2687) - 0.7, 12.4, yb - 0.5, zs, Z(2200), tier=7.5, seed=6,
                  windows=[("N", X(2617), z, 2.2, 5.6) for z in (64.0, 80.0)],
                  ev="C", ref="black band on master between the shell towers and the interiors", note="behind the upper shell tower; windows are completion")

    # ---- neck between the main stack and the bridge gatehouse (B)
    P.stack(S, R, S.el(R, "Neck"), "blue")

    # ---- ground level: undercroft hall under the stack and the gallery wing toward the plaza
    REF_G = "11_Lower_City/Lower_City_bottom.jpg; master C6"
    carved = P.carve_s2_box("COT_WestGallery_Bay", (-69.3, -4.0, -0.4, -19.0, 6.0, 6.0))
    ceil = Z(3497)
    under = P.wel("Undercroft", x0, x1, GZ, ceil, [GZ], doors=[("L", GZ), ("R", GZ)], voids=[(X(2775), X(2815), GZ - 1, ceil + 1)], ev="A", ref=REF_G)
    style = dict(P.STYLES["street"], back=("blind",), lamp=None, bay=4.2, fringe=True)
    ui = P.stack(S, R, under, style, y=(yf, yb), door_y={"R": 1.25, "L": 1.25}, front_rail=False, ext_faces=("N",), furnish=False,
                 keep_clear=[(0, -69.0, -20.0, 2.0, 18.5), (0, -66.5, -63.0, -5.0, -3.0), (0, -53.5, -50.5, -4.0, -2.0), (0, -34.5, -31.5, -2.5, -0.5),
                             (0, -56.5, -53.5, 5.0, 8.0)])
    wing = P.wel("GalleryWing", x1, -19.0, GZ, 5.52, [GZ], ev="A", ref=REF_G)
    P.stack(S, R, wing, dict(style, bay=3.9), y=(-4.0, 6.5), side_open=("L", "R"), rear=True, furnish=False)
    g = Geo()
    g.use("stone_dark")
    g.box(x0, x1, yf, yb, -2.7, GZ - 0.5)                                  # foundations down to the well bed
    g.box(x1, -19.0, -4.9, 6.5, -2.7, GZ - 0.5)
    g.use("stone")
    g.box(x0, x1, yf, yb, ceil + 0.5, Z(3461) - 0.5)                         # plinth between the hall and the lowest rooms
    S.add(g, "Ground_Masonry", R, "UndercroftMasonry", "A", REF_G, note="depth of the hall and the second arcade row are completion")
    snail = [S.kit(f"snail_{v}", lambda v=v: K.k_snail(0.75 + 0.2 * v, v)) for v in range(2)]
    P.scatter(S, R, snail[0], "Snail", "SnailShell", [(-66.0, 5.5, GZ, 0.4, 1.0), (-55.5, 7.0, GZ, 2.6, 1.2), (-45.0, 6.0, GZ, 0.2, 1.0), (-28.0, 3.2, GZ, 3.4, 0.9)], "A", REF_G)
    P.scatter(S, R, snail[1], "SnailB", "SnailShell", [(-58.8, 15.0, GZ, 1.2, 1.0), (-42.0, 15.5, GZ, 2.0, 1.1)], "A", REF_G)
    jars = [S.kit(f"jar_{v}", lambda v=v: K.k_jar(v)) for v in range(3)]
    rand = rng(5)
    for v in range(3):
        P.scatter(S, R, jars[v], f"Jar{v}", "Jar", [(rand(-67.5, -40.0), rand(4.0, 17.5), GZ, rand(0, 6), rand(0.8, 1.2)) for _ in range(5)] +
                  [(rand(-36.5, -21.0), rand(2.5, 5.6), GZ, rand(0, 6), rand(0.8, 1.1)) for _ in range(2)], "A", REF_G)
    lampk = S.kit("signlamp", lambda: sign_lamp())
    P.scatter(S, R, lampk, "GroundSignLamp", "SignLamp", [(-64.8, -4.0, GZ), (-52.0, -3.0, GZ, 0.3), (-33.0, -1.5, GZ)], "A", REF_G)
    g = Geo()                                                               # round emblem standing in a shaft of light
    g.use("glass_pink")
    g.ellipsoid((0, 0, 1.15), (0.85, 0.08, 0.85), segs=20, steps=6)
    g.use("trim")
    g.ring_arc((0, 0, 1.15), 0.9, 0, TAU, 0.07, n=24, plane="XZ", segs=6)
    g.revolve([(0.5, 0.0), (0.55, 0.1), (0.2, 0.22), (0.14, 0.3)], segs=10)
    for sx in (-1, 1):
        for k in range(3):
            g.tube([(sx * 0.08, -0.1, 1.2 - 0.1 * k), (sx * (0.34 + 0.06 * k), -0.1, 1.45 - 0.18 * k), (sx * 0.72, -0.1, 1.28 - 0.26 * k)], 0.03, segs=4, ref=(0, 1, 0))
    g.tube([(0, -0.1, 0.7), (0, -0.1, 1.5)], 0.06, segs=5)
    S.add(g, "Emblem", R, "EmblemDisc", "A", REF_G, note="pink-white round emblem under a light shaft; meaning not identified").location = (-55.0, 6.4, GZ)

    # ---- flat louvre roof over the gallery wing with the walkway on it (A: Lighting_03, master C6)
    REF_W = "13_Lighting/Lighting_03.jpg; master C6"
    P.louvre_band(S, R, "WalkwayRoof", x1 + 0.1, -19.3, -4.0, 6.5, 6.28, 9.3, spikes=False, ev="A", ref=REF_W, note="continues the stage 2 louvre eave westward; depth is completion")
    g = Geo()
    K.slab(g, x1, -19.3, -4.3, 6.8, Z(3451), 0.6, "stone", lip=("front", "back", "right"))
    S.add(g, "Walkway", R, "Walkway", "A", REF_W)
    P.spike_rail(S, R, "WalkwayRail", [((x1 + 0.2, -4.1), (-19.5, -4.1)), ((x1 + 0.2, 6.6), (-19.5, 6.6)), ((-19.5, -4.1), (-19.5, 6.6))], z=Z(3451), ev="A", ref=REF_W)

    # ---- creatures (D-347): sentries and residents (A: Lower_City_middle.jpg)
    for gk, n_ in (("L", 5), ("M", 4), ("R", 4)):
        P.populate(S, R, f"Block{gk}", infos[gk], ["husk_sentry", "lance_sentry", "heavy_sentry", "resident_0", "resident_1", "resident_2"], n_, seed=1 + ord(gk))
    P.populate(S, R, "Undercroft", ui, ["resident_0", "resident_2", "husk_sentry"], 4, seed=2)

    # ---- cameras
    # no west side view: the left well's shell towers stand against that side and hide it from every direction
    S.cam_auto(R, (X(2547), -19.0, yf - 1.0, yb + 1.0, -1.0, Z(1990)), ref="master B3_central_lower", views=("front", "closed", "oblique", "back"))
    S.camera("Interior_Storey2", R, (-58.3, -8.6, fl[2] + 1.8), look=(-52.0, 13.0, fl[2] + 2.2), lens=20.0, kind="interior", purpose="lancet-window storey from inside")
    S.camera("Interior_Storey6", R, (-58.3, -8.6, fl[5] + 1.7), look=(-52.0, 13.0, fl[5] + 1.9), lens=20.0, kind="interior", purpose="storey with the heap of orange finds and the lift")
    S.camera("Interior_Shop", R, (-45.6, 1.5, z0 + 1.8), look=(-43.4, 11.5, z0 + 1.4), lens=20.0, kind="interior", purpose="shop corner, compare 13_Lighting/Lighting_03.jpg",
             ref="13_Lighting/Lighting_03.jpg")
    S.camera("Interior_Undercroft", R, (-67.0, -6.0, GZ + 1.8), look=(-44.0, 14.0, GZ + 2.4), lens=20.0, kind="interior", purpose="ground hall, compare 11_Lower_City/Lower_City_bottom.jpg",
             ref="11_Lower_City/Lower_City_bottom.jpg")
    S.camera("EastFace", R, (-8.0, -30.0, 30.0), look=(-38.0, 4.0, 34.0), lens=28.0, kind="side", purpose="well face: glass pillars, canopies, walkway")
    S.camera("Walkway", R, (-22.0, 1.0, Z(3451) + 1.7), look=(-40.0, 1.5, Z(3451) + 2.0), lens=24.0, kind="view", purpose="walkway toward the shop door")
    return carved


def sign_lamp():
    """Round patterned lamp on a post (A: 11_Lower_City bottom, 13_Lighting/Lighting_03 left)."""
    g = Geo()
    g.use("iron")
    g.revolve([(0.2, 0.0), (0.22, 0.06), (0.07, 0.16), (0.045, 1.5), (0.09, 1.58), (0.05, 1.66)], segs=8)
    g.ring_arc((0, 0, 2.2), 0.56, 0, TAU, 0.05, n=22, plane="XZ", segs=5)
    g.spike((0, 0, 2.76), (0, 0, 3.3), 0.05, segs=5, bulb=1.1)
    g.spike((0, 0, 1.64), (0, 0, 1.4), 0.05, segs=5)
    g.use("lamp_pink")
    g.ellipsoid((0, 0, 2.2), (0.5, 0.16, 0.5), segs=16, steps=8)
    return g


# ============================================================================ LowerBridge
def lower_bridge(S):
    R = "LowerBridge"
    REF = "11_Lower_City/Lower_City_upperbridge.jpg; master B6"
    y0, y1 = BRIDGE_Y
    yc = (y0 + y1) / 2
    zd, zb_arc = Z(2618), Z(2652) - 0.2
    zrb, zrt, zpt = Z(2565), Z(2515), Z(2488)
    bench_x0, bench_x1 = X(3734), X(3896)
    NOTE = "moved to the viewer-side edge of the well so that the plaza is open to the rain (C); X/Z as on the master"

    g = Geo()
    K.slab(g, X_BW, X_BE, y0 - 0.3, y1 + 0.3, zd, 0.8, "stone", lip=("front", "back"), trim="stone_far_trim")
    P.under_arcade(g, X_BW, bench_x0, y0, y1, zd - 0.8, zb_arc, 13)
    P.under_arcade(g, bench_x0, bench_x1, y0, y1, zd - 0.8, zb_arc, 4, pendants=False)
    P.under_arcade(g, bench_x1, X_BE, y0, y1, zd - 0.8, zb_arc, 3)
    S.add(g, "Deck", R, "BridgeDeck", "A", REF, note=NOTE)
    g = Geo()
    for yy, seed in ((y0 + 0.25, 1), (y1 - 0.25, 2)):
        SH.hanging_fringe(g, X_BW + 0.3, bench_x0 - 0.2, yy, zb_arc + 0.3, 1.9, seed=seed)
    S.add(g, "DeckFringe", R, "BridgeFringe", "A", REF)

    bays = 20
    bw = (X_BE - X_BW) / bays
    col = P.kit_column(S, zrb - zd, 0.12, "trim")
    for k in range(bays + 1):
        xe = X_BW + bw * k
        for j, yy in enumerate((y0 + 0.3, y1 - 0.3)):
            S.put(col, f"Col_{k:02d}_{j}", R, "Column", place(xe, yy, zd), "A", REF)
    P.spike_rail(S, R, "Rail", [((X_BW, y0 + 0.3), (X_BE, y0 + 0.3)), ((X_BW, y1 - 0.3), (X_BE, y1 - 0.3))], z=zd, ev="A", ref=REF, h=0.9)

    # louvre roof band between the three domed pavilions
    pav = [X(3383), X(3563), X(3738)]
    hw = 110 / 15.0 / 2
    cuts = [X_BW] + [v for p in pav for v in (p - hw, p + hw)] + [X_BE]
    for k in range(0, len(cuts), 2):
        P.louvre_band(S, R, f"Roof_{k // 2}", cuts[k], cuts[k + 1], y0 - 0.15, y1 + 0.15, zrb, zrt, ev="A", ref=REF, note=NOTE)
    win = P.kit_window(S, "lancet", 1.5, zrt - zrb - 0.5, "glass_blue")
    for k, px in enumerate(pav):
        g = Geo()
        g.use("louvre_core")
        g.box(px - hw + 0.2, px + hw - 0.2, y0 + 0.1, y1 - 0.1, zrb, zrt)
        g.use("louvre_frame")
        for sx in (-1, 1):
            for yy in (y0 - 0.2, y1 + 0.2):
                g.box(px + sx * hw - 0.22, px + sx * hw + 0.22, yy - 0.22, yy + 0.22, zrb - 0.2, zrt + 0.3)
        g.box(px - hw - 0.25, px + hw + 0.25, y0 - 0.45, y1 + 0.45, zrt, zrt + 0.3)
        g.use("stone_dark")
        g.box(px - hw - 0.2, px + hw + 0.2, y0 - 0.4, y1 + 0.4, zrb - 0.26, zrb)
        K.louvre_dome(g, hw + 0.1, (y1 - y0) / 2 + 0.3, zpt - zrt + 0.5, ribs=10, m=place(px, yc, zrt + 0.3))
        g.use("iron")
        for i in range(22):                                   # crown of spears round the foot of the dome
            a = TAU * i / 22
            bx, by = px + (hw + 0.2) * math.cos(a), yc + ((y1 - y0) / 2 + 0.4) * math.sin(a)
            g.spike((bx, by, zrt + 0.3), (bx, by, zrt + (1.5 if i % 2 == 0 else 0.9)), 0.06, segs=5, bulb=0.9)
        for yy in (y0 - 0.2, y1 + 0.2):
            K.drape(g, px - hw + 0.4, px + hw - 0.4, yy - (0.1 if yy < yc else -0.1), zrt - 0.05, zrb + 0.9, folds=7, amp=0.07, thick=0.05, key="curtain", hem=0.9, seed=k)
        S.add(g, f"Pavilion_{k}", R, "BridgePavilion", "A", REF, note=NOTE, smooth=35)
        for j, dx in enumerate((-1.75, 0.0, 1.75)):
            for i, (yy, rz) in enumerate(((y0 - 0.34, 0.0), (y1 + 0.34, math.pi))):
                S.put(win, f"PavWin_{k}_{j}_{i}", R, "WindowLancet", place(px + dx, yy, zrb + 0.25, rz=rz), "A", REF)
    # hanging lamps: three-globe clusters and single drops (A)
    cluster = S.kit("globe3", lambda: globe_cluster())
    drop = S.kit("lampdrop_1.6", lambda: K.k_lamp_string(1, 1.6))
    for k in range(bays):
        cx = X_BW + bw * (k + 0.5)
        if k % 3 == 1:
            S.put(cluster, f"Cluster_{k:02d}", R, "GlobeCluster", place(cx, yc, zrb - 0.3), "A", REF)
        elif k % 3 == 2:
            S.put(drop, f"Drop_{k:02d}", R, "LampString", place(cx, yc + 1.2, zrb - 0.3), "A", REF)

    # bench room hanging under the east end (A: upperbridge.jpg lower right, master B6)
    REF_B = "11_Lower_City/Lower_City_upperbridge.jpg lower right; master B6"
    be = P.wel("BenchRoom", bench_x0, bench_x1, Z(2700), zb_arc, [Z(2700)], doors=[("L", Z(2700))], ev="A", ref=REF_B)
    st = dict(P.STYLES["blue"], glass="glass_pink", bay=3.5, partition=0, back=("lancet", "niche", "lancet"), lamp="string")
    P.stack(S, R, be, st, y=(y0 - 2.0, y1 + 2.0), roof=False, note=NOTE)
    S.put(S.kit("bench", lambda: K.k_bench()), "Bench", R, "Bench", place(bench_x1 - 2.6, y1 + 0.6, Z(2700)), "A", REF_B)
    P.glass_pillar(S, R, "BenchGlassPillar", bench_x0 - 0.2, y0 - 1.2, 0.6, Z(2700) - 0.2, zb_arc, "A", REF_B)
    g = Geo()
    P.stairs(g, bench_x0 - 3.2, bench_x0, y1 + 0.6, y1 + 1.9, Z(2700), zd, step=0.45, key="stone", solid=False)
    S.add(g, "BenchStair", R, "BenchStair", "C", REF_B, note="how the bench room is reached is not shown; a short stair from the deck is completion")

    # bridgeheads: covered landings that turn the bridge into the two buildings (C)
    zs = Z(2605)                                              # central block storey floor
    g = Geo()
    K.slab(g, X_BW - 7.4, X_BW, y0 - 0.3, -10.0, zd, 0.8, "stone", lip=("front", "left"), trim="stone_far_trim")
    g.use("stone")
    for i in range(2):                                        # two steps up to the storey floor
        g.box(X_BW - 6.6, X_BW - 0.6, -11.2 + 0.6 * i, -10.0, zd, zd + (zs - zd) * (i + 1) / 2)
    for sx in (X_BW - 6.6, X_BW - 0.8):
        K.corbel(g, sx, -10.0, zd - 0.8, size=2.6, key="stone_far_trim")
        K.corbel(g, sx, -13.0, zd - 0.8, size=2.0, key="stone_far_trim")
    S.add(g, "HeadWest", R, "BridgeheadWest", "C", REF, note="landing on the front of the central block where the moved bridge arrives")
    colh = P.kit_column(S, zrb - zd, 0.12, "trim")
    for k, (cx, cy) in enumerate(((X_BW - 7.0, y0), (X_BW - 7.0, -15.0), (X_BW - 7.0, -10.6), (X_BW - 3.6, y0))):
        S.put(colh, f"HeadWest_Col_{k}", R, "Column", place(cx, cy, zd), "C", REF)
    P.louvre_roof(S, R, "HeadWestRoof", X_BW - 8.2, X_BW, zrb, zrt, y0 - 0.15, -10.2, bays=2, curve_end="W", ev="C", ref=REF, note="completion: roof over the west landing")
    P.spike_rail(S, R, "HeadWestRail", [((X_BW - 7.1, y0 + 0.2), (X_BW, y0 + 0.2)), ((X_BW - 7.1, y0 + 0.2), (X_BW - 7.1, -10.4))], z=zd, ev="C", ref=REF, h=0.9)

    for k, (f, kind) in enumerate(((0.07, "resident_0"), (0.19, "husk_sentry"), (0.31, "resident_1"), (0.45, "resident_2"), (0.58, "resident_0"),
                                   (0.72, "husk_sentry_low"), (0.86, "resident_1"))):          # walkers on the bridge (A: notes on Tower_step3, the long corridor)
        P.creature(S, R, kind, f"Deck_{k}", lerp(X_BW, X_BE, f), yc + (1.2 if k % 2 else -1.2), zd + 0.01, rz=(math.pi / 2 if k % 2 else -math.pi / 2))
    S.cam_auto(R, (X_BW - 8.0, X_BE, y0 - 2.0, y1 + 2.0, Z(2704) - 1.0, zpt + 2.0), ref="master B6", views=("front", "closed", "oblique", "back"), front_hide=())
    S.camera("Along", R, (X_BW + 3.0, yc - 1.4, zd + 1.7), look=(X_BE, yc + 0.6, zd + 2.0), lens=24.0, kind="interior", purpose="walking along the deck, compare Lower_City_upperbridge.jpg", ref=REF)
    S.camera("Underside", R, (-14.0, 8.0, 30.0), look=(-6.0, -16.0, 64.0), lens=28.0, kind="view", purpose="bridge underside: arches, pendants, fringe, deck thickness")
    S.camera("BenchRoom", R, (bench_x0 + 0.9, y0 - 1.2, Z(2700) + 1.5), look=(bench_x1 - 1.0, y1 + 1.5, Z(2700) + 1.4), lens=18.0, kind="interior", purpose="bench room interior")
    S.camera("HeadWest", R, (X_BW + 9.0, y0 - 9.0, zd + 5.0), look=(X_BW - 4.0, -13.0, zd + 2.0), lens=28.0, kind="view", purpose="west bridgehead on the central block front")


def globe_cluster():
    """Three small globes on a common hanger (A: 11_Lower_City upperbridge / middle)."""
    g = Geo()
    g.use("chain")
    g.tube([(0, 0, 0), (0, 0, -0.5)], 0.02, segs=4)
    g.use("iron")
    g.tube([(-0.42, 0, -0.55), (-0.2, 0, -0.47), (0, 0, -0.5), (0.2, 0, -0.47), (0.42, 0, -0.55)], 0.022, segs=4, ref=(0, 1, 0))
    for x, z in ((-0.42, -0.72), (0.0, -0.84), (0.42, -0.72)):
        g.use("iron")
        g.revolve([(0.02, z + 0.2), (0.06, z + 0.16), (0.075, z + 0.12)], segs=6, m=place(x, 0, 0))
        g.use("lamp")
        g.ellipsoid((x, 0, z), (0.12, 0.12, 0.12), segs=8, steps=6)
    return g


# ============================================================================ PlazaEastHouse
def plaza_east_house(S):
    R = "PlazaEastHouse"
    REF = "11_Lower_City/Lower_City_statue.jpg right side; 13_Lighting/Lighting_04.jpg; master B6"
    HX, XE, HY0, HY1 = 10.4, 25.5, -1.6, 15.5
    TER = 9.94
    UP = 14.05                                                 # eave of the stage 2 louvre roofs
    c1 = P.carve_s2_box("COT_House_Body", (HX, HY0, -2.7, XE, HY1, TER - 0.6))
    c2 = P.carve_s2_box("COT_House_Body", (14.2, HY0, TER, XE, HY1, UP), tol=0.06)
    # The stage 2 tower on the house hangs its lowest fringe 2.7 below the roof; now that the upper storey is a room
    # (master B6 shows it lit), squeeze that tower slightly about its top so it stands on the roof (structure file only;
    # the original placement is kept on the objects, so rebuilding gives the same result)
    from mathutils import Matrix, Vector
    tw = [o for o in bpy.data.objects if o.get("cot_s2") and o.name.startswith("COT_EastTower_")]
    for o in tw:
        if "cot_s3_orig_matrix" not in o:
            o["cot_s3_orig_matrix"] = [v for row in o.matrix_world for v in row]
        o.matrix_world = Matrix([o["cot_s3_orig_matrix"][i * 4:(i + 1) * 4] for i in range(4)])
    if tw:
        pts = [o.matrix_world @ Vector(c) for o in tw for c in o.bound_box]
        zmin, ztop = min(p.z for p in pts), max(p.z for p in pts)
        if zmin < UP:
            f = (ztop - UP - 0.05) / (ztop - zmin)
            m = Matrix.Translation((0, 0, ztop)) @ Matrix.Diagonal((1.0, 1.0, f, 1.0)) @ Matrix.Translation((0, 0, -ztop))
            for o in tw:
                o.matrix_world = m @ o.matrix_world
                o["cot_s3_note"] = f"squeezed vertically by {f:.3f} about its top so its fringe stays above the upper room (stage 3)"
    purple = dict(P.STYLES["purple"], bay=3.7, partition=2, back=("shelf", "web", "shelf"))
    MID = 5.97
    lower = P.wel("House", HX, XE, GZ, TER - 0.6, [GZ, MID], doors=[("L", GZ), ("R", GZ)], ev="A", ref=REF)
    lo_i = P.stack(S, R, lower, purple, y=(HY0, HY1), front="solid", roof=False, door_y={"L": 1.5, "R": 1.0}, rear=True, ext_faces=("N",),
            note="interior floors follow master B6; the stage 2 placeholder solid was removed. No stair is shown by any reference")
    upper = P.wel("HouseUpper", 14.2, XE, TER, UP - 0.5, [TER], doors=[("L", TER)], ev="A", ref=REF)
    up_i = P.stack(S, R, upper, purple, y=(HY0, HY1), front="solid", roof=True, door_y={"L": 0.4}, rear=True, ext_faces=("N", "R"))
    g = Geo().use("stone_dark")
    g.box(HX, XE, HY0, HY1, -2.7, GZ - 0.5)
    S.add(g, "Foundation", R, "HouseFoundation", "C", REF)
    # pink cobbled floor tops and a railed floor opening (A: Lighting_04.jpg)
    g = Geo().use("cushion")
    rand = rng(31)
    for zf, (xa, xb) in ((MID, (11.2, 24.7)),):
        x = xa
        while x < xb:
            w = rand(0.5, 0.8)
            for yy in (HY0 + 0.75, HY0 + 1.3):
                g.ellipsoid((x + w / 2, yy, zf + 0.02), (w * 0.5, 0.3, 0.1), segs=8, steps=4, e=0.6)
            x += w
    S.add(g, "FloorCobbles", R, "PinkFloorCobbles", "A", "13_Lighting/Lighting_04.jpg", note="only the front rows are modelled; the rest is the slab")
    # east corridor toward the tower block (A: master B2_rc_block_lower)
    ce = dict(S.el(R, "CorridorEast"))
    ce["floors"] = [3600 - GZ * 15.0]
    P.stack(S, R, ce, dict(P.STYLES["purple"], bay=3.4, partition=0, back=("web", "niche")), y=(-5.0, 7.0), door_y={"L": 1.0, "R": 1.0})
    g = Geo().use("stone_dark")
    g.box(X(4112), X(4269), -5.0, 7.0, -2.7, GZ - 0.5)
    S.add(g, "CorridorFoundation", R, "HouseFoundation", "C", REF)

    P.populate(S, R, "House", lo_i, ["resident_0", "resident_1", "resident_2"], 4, seed=3)
    P.populate(S, R, "HouseUpper", up_i, ["resident_1"], 1, seed=4)
    # twisted columns along the middle of the rooms and iron railings at the floor edges (A: 13_Lighting/Lighting_04.jpg) (D-369)
    def twisted(h):
        g = Geo().use("trim_purple")
        g.revolve([(0.32, 0.0), (0.34, 0.12), (0.2, 0.26), (0.16, 0.4)], segs=12)
        for st_ in range(3):
            g.tube([(0.14 * math.cos(st_ * TAU / 3 + t * 0.6), 0.14 * math.sin(st_ * TAU / 3 + t * 0.6), 0.4 + (h - 0.9) * t / 24) for t in range(25)], 0.09, segs=6)
        g.revolve([(0.16, h - 0.5), (0.3, h - 0.3), (0.38, h - 0.12), (0.38, h)], segs=12)
        return g
    for info_, nm in ((lo_i, "Lower"), (up_i, "Upper")):
        for i, zf, top in info_["storeys"]:
            hgt_ = round(top - zf, 1)
            col = S.kit(f"twisted_{hgt_:.1f}", lambda h=hgt_: twisted(h))
            for k, cx_ in enumerate(info_["edge_x"][1:-1]):
                S.put(col, f"Twisted_{nm}_{i}_{k}", R, "TwistedColumn", place(cx_, (HY0 + HY1) / 2 - 1.5, zf), "A", "13_Lighting/Lighting_04.jpg",
                      note="twisted columns as in Lighting_04.jpg; their place in depth is completion")
            if i > 0 or nm == "Upper":
                P.railing(S, R, f"Railing_{nm}_{i}", (info_["x0"] + 0.8, HY0 + 1.2), (info_["x1"] - 0.8, HY0 + 1.2), zf, ev="A", ref="13_Lighting/Lighting_04.jpg")
    S.cam_auto(R, (HX - 2.0, X(4269), HY0, HY1, -1.0, 19.0), ref="master B6", views=("oblique", "back", "side"))
    for name, yy, purpose in (("Section", HY0 + 0.8, "section just inside the south wall, comparable with master B6 and Lighting_04.jpg"),):
        cam = S.camera(name, R, ((HX + X(4269)) / 2, yy, 8.0), ortho=30.0, rot=(90.0, 0.0, 0.0), kind="ref", purpose=purpose, ref=REF, res=(1920, 1300))
        cam.data.clip_start = 0.05
    S.camera("Interior_Ground", R, (11.6, 0.2, GZ + 1.7), look=(24.0, 13.0, GZ + 2.2), lens=18.0, kind="interior", purpose="ground floor room")
    S.camera("Interior_Mid", R, (11.6, 0.2, MID + 1.6), look=(24.0, 13.5, MID + 1.6), lens=18.0, kind="interior", purpose="middle floor, compare Lighting_04.jpg", ref="13_Lighting/Lighting_04.jpg")
    S.camera("Interior_Upper", R, (15.2, 0.0, TER + 1.6), look=(24.5, 13.5, TER + 1.8), lens=18.0, kind="interior", purpose="top room under the louvre roof")
    return c1, c2


REGIONS = {"CentralWell": central_well, "FountainPlaza": fountain_plaza, "CentralBlock": central_block, "LowerBridge": lower_bridge,
           "PlazaEastHouse": plaza_east_house}
