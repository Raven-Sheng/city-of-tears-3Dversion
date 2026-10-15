"""Stage 3 structure: UpperBridge (windowed long bridge over the left well) and BridgeGatehouse."""
import math

import cot_kit as K
import cot_parts as P
import cot_shell as SH
from cot_geo import Geo, TAU, lerp, place, rng
from cot_s3 import X, Z


def baluster_column(h=3.6):
    """Fat turned baluster column of the bridge gallery (A: 04_Bridges/Bridges_middle.jpg)."""
    g = Geo().use("trim")
    prof = [(0.34, 0.0), (0.36, 0.12), (0.2, 0.24), (0.26, 0.4), (0.3, 0.75), (0.22, 1.05), (0.12, 1.25), (0.17, 1.38), (0.1, 1.5),
            (0.1, h - 0.9), (0.18, h - 0.8), (0.12, h - 0.66), (0.2, h - 0.5), (0.13, h - 0.36), (0.26, h - 0.16), (0.3, h)]
    g.revolve(prof, segs=10)
    return g


def upper_bridge(S):
    R = "UpperBridge"
    REF = "04_Bridges/Bridges_total.jpg; Bridges_left.jpg; Bridges_middle.jpg; Bridges_right.jpg; master A_upper_bridge"
    e = S.el(R, "Bridge")
    x0, x1 = X(e["x"][0]), X(e["x"][1])
    y0, y1 = -3.5, 3.5
    zd, zb = Z(e["deck"]), Z(e["band_to"]) - 0.1
    ztop = zd + 4.7                                            # top of the window gallery (re-measured on master A_upper_bridge: the
    # louvre roof starts 6.3 above the deck, not 3.9 as the stage 1 layout had it)
    bays = e["bays"]
    bw = (x1 - x0) / bays

    g = Geo()
    K.slab(g, x0, x1, y0 - 0.3, y1 + 0.3, zd, 0.8, "stone", lip=("front", "back"), trim="stone_far_trim")
    P.under_arcade(g, x0, x1, y0, y1, zd - 0.8, zb, bays)
    S.add(g, "Deck", R, "BridgeDeck", "A", REF)
    g = Geo()
    for yy, seed in ((y0 + 0.25, 1), (y1 - 0.25, 2)):
        SH.hanging_fringe(g, x0 + 4.0, x1 - 0.3, yy, zb + 0.3, 2.2, seed=seed)
    S.add(g, "DeckFringe", R, "BridgeFringe", "A", REF)

    # window gallery: baluster columns, leaded pointed windows, round arches with shell crests, thin roof (A)
    hgal = ztop - zd - 0.5
    col = S.kit(f"baluster_{hgal:.1f}", lambda: baluster_column(hgal))
    win = P.kit_window(S, "lancet", 1.6, hgal - 0.45, "glass_blue")
    g = Geo()
    for yy, rz in ((y0 + 0.3, 0.0), (y1 - 0.3, math.pi)):
        for k in range(bays + 1):
            S.put(col, f"Col_{k:02d}_{0 if rz == 0 else 1}", R, "BalusterColumn", place(x0 + bw * k, yy, zd), "A", REF)
        for k in range(bays):
            S.put(win, f"Win_{k:02d}_{0 if rz == 0 else 1}", R, "WindowLancet", place(x0 + bw * (k + 0.5), yy, zd + 0.15, rz=rz), "A", REF)
        g.use("stone_far")
        K.arcade(g, x0, x1, zd + hgal - 0.3, zd + 6.0, yy - 0.2, yy + 0.2, [(x0 + bw * (k + 0.5), bw - 0.5, zd + hgal - 0.25, "round", None, zd + hgal - 0.3) for k in range(bays)])
        g.use("stone_far_trim")
        for k in range(bays + 1):
            g.ellipsoid((x0 + bw * k, yy - (0.25 if rz == 0 else -0.25), zd + hgal + 0.1), (0.42, 0.16, 0.3), segs=10, steps=6)
    K.slab(g, x0, x1, y0 - 0.2, y1 + 0.2, zd + 6.3, 0.3, "stone_far", lip=("front", "back"), trim="stone_far_trim", drops=False)
    S.add(g, "Gallery", R, "BridgeGallery", "A", REF, note="the far side of the gallery repeats the near side (C)")
    drop = S.kit("lampdrop_1.6", lambda: K.k_lamp_string(1, 1.6))
    drop2 = S.kit("lampstring_2.2", lambda: K.k_lamp_string(2, 2.2))
    for k in range(bays):
        if k % 2 == 0:
            S.put(drop if k % 4 == 0 else drop2, f"Lamp_{k:02d}", R, "LampString", place(x0 + bw * (k + 0.5), 0.6 * (1 if k % 4 == 0 else -1), zd + 6.0), "A", REF)

    # louvre roof over the east half (A), wing ornament where it starts (A), stalactites over the west half (B)
    lr = S.el(R, "LouvreRoof")
    lx0 = X(lr["map"][0])
    br_x0 = X(S.el("SoulSanctum", "BookRooms")["map"][0])     # the roof ends in the west wall of the sanctum's book rooms above the gatehouse
    P.louvre_roof(S, R, "LouvreRoof", lx0, min(x1, br_x0 + 0.3), zd + 6.3, zd + 9.4, y0 - 0.3, y1 + 0.3, bays=7, curve_end="W", ev="A", ref="04_Bridges/Bridges_right.jpg; master A_upper_bridge",
                  note="heights re-measured on the master crop")
    g = Geo()
    import cot_assets as A
    A.add_corbel_wing(g, place(lx0 - 0.2, y0 - 0.2, zd + 8.0, rz=math.pi), length=3.0, blades=6, key="louvre_frame", spread=0.7)
    A.add_corbel_wing(g, place(lx0 - 0.2, y1 + 0.2, zd + 8.0, rz=math.pi), length=3.0, blades=6, key="louvre_frame", spread=0.7)
    S.add(g, "WingOrnament", R, "WingOrnament", "A", "04_Bridges/Bridges_middle.jpg (feathered ornament at the roof end)")
    g = Geo()
    K.stalactite_field(g, x0, lx0 - 1.0, -6.0, 8.0, lambda x, y: zd + 8.3, 110, seed=3, lmin=1.0, lmax=3.6)
    S.add(g, "Stalactites", R, "Stalactites", "B", "04_Bridges/Bridges_left.jpg shows a stalactite ceiling over the west half; extent is completion", layer="CEILING", smooth=50)
    # jars at the west landing (A: Bridges_left.jpg)
    jar = [S.kit(f"hivejar_{v}", lambda v=v: SH.k_hive_jar(v)) for v in range(3)]
    for k in range(5):
        S.put(jar[k % 3], f"Jar_{k}", R, "HiveJar", place(x0 + 1.0 + 0.9 * k, 1.8 - 0.5 * (k % 2), zd), "A", "04_Bridges/Bridges_left.jpg")

    for k, (f, kind, dy) in enumerate(((0.3, "husk_sentry", -0.8), (0.55, "lance_sentry", 0.8), (0.78, "husk_sentry_low", -0.6))):
        P.creature(S, R, kind, f"Deck_{k}", lerp(x0, x1, f), dy, zd + 0.01, rz=(math.pi / 2 if k % 2 else -math.pi / 2))
    P.creature(S, R, "winged_sentry", "Air_0", lerp(x0, x1, 0.12), -1.2, zd + 0.4, rz=-math.pi / 2)
    S.cam_auto(R, (x0, x1, y0, y1, zb - 2.0, zd + 11.0), ref="master A_upper_bridge", views=("front", "closed", "oblique", "back"), front_hide=())
    S.camera("Along", R, (x0 + 3.0, -0.8, zd + 1.7), look=(x1, 0.4, zd + 1.9), lens=22.0, kind="interior", purpose="walking along the deck, compare Bridges_middle.jpg", ref=REF)
    S.camera("Underside", R, (-104.0, -22.0, 86.0), look=(-98.0, 0.0, 106.0), lens=28.0, kind="view", purpose="underside: arches, pendants, fringe, deck thickness")
    S.camera("EastEnd", R, (-92.0, -26.0, 116.0), look=(-76.0, 0.0, 110.0), lens=28.0, kind="view", purpose="louvre roof, wing ornament and the joint with the gatehouse")


def bridge_gatehouse(S):
    R = "BridgeGatehouse"
    REF = "master B3_sanctum (no local screenshot)"
    e = S.el(R, "Room")
    st = dict(P.STYLES["sanctum"], bay=4.8, back=("tall", "niche", "tall"), partition=0, lamp="orb", inner=False)
    info = P.stack(S, R, e, st, skip_bays={(0, 2), (0, 3)})         # the observed tall window stands across these two bays
    # the great pointed window fills the room's height between the two middle bays (A: master B3 enlarged, map x 2813-2923)
    wx0, wx1 = X(2813), X(2923)
    wx = (wx0 + wx1) / 2
    zf, zt = info["floors"][0], info["zt"]
    win = S.kit("gatehouse_window", lambda: K.k_window_lancet(wx1 - wx0 - 0.6, zt - zf - 0.4, "glass_white", tracery=True, web=True))
    S.put(win, "TallWindow", R, "WindowTall", place(wx, info["yb"] - 0.75, zf + 0.1), "A", REF)
    # a screen of pointed arches hangs across the upper part of the room, broken by the window (A: master B3 enlarged)
    g = Geo().use(st["wall"])
    crown, spring = Z(1917), Z(1917) - 1.9
    xs0, xs1 = info["x0"] + 0.6, info["x1"] - 0.6
    for a, b in ((xs0, wx0 - 0.3), (wx1 + 0.3, xs1)):
        nb = max(1, int(round((b - a) / 3.6)))
        bw = (b - a) / nb
        ops = [(a + bw * (k + 0.5), bw - 0.5, spring, "pointed", crown - spring, spring - 0.3) for k in range(nb)]
        K.arcade(g, a, b, spring - 0.3, zt, info["yb"] - 1.9, info["yb"] - 1.6, ops)
        g.use(st["trim"])
        for cxk, w, sp, kind, rise, sill in ops:
            K.arch_trim(g, cxk, w, sp, sp, kind, rise, y=info["yb"] - 1.95, r=0.07)
        g.use(st["wall"])
    SH.hanging_fringe(g, xs0, wx0 - 0.3, info["yb"] - 1.75, spring - 0.3, 1.2, seed=3)
    SH.hanging_fringe(g, wx1 + 0.3, xs1, info["yb"] - 1.75, spring - 0.3, 1.2, seed=4)
    S.add(g, "ArchScreen", R, "ArchScreen", "A", REF, note="pointed arch screen under the ceiling; its depth position is completion")
    # a soul warrior stands in the gatehouse on the master (A: master B3 enlarged); a soul twister keeps it company (C)
    P.creature(S, R, "soul_warrior", "Warrior", X(2867), info["yf"] + 3.2, zf + 0.01, rz=0.2)
    P.populate(S, R, "Gate", info, ["soul_twister", "mistake_0"], 2, seed=7, avoid=[(0, X(2867) - 2.2, X(2867) + 2.2, info["yf"], info["yb"])])
    S.cam_auto(R, (info["x0"], info["x1"], info["yf"], info["yb"], info["bottom"] - 1.0, info["zt"] + 1.5), ref=REF, views=("front", "closed", "oblique"))
    S.camera("Interior", R, (info["x0"] + 1.4, info["yf"] + 1.4, info["floors"][0] + 1.7), look=(info["x1"] - 3.0, info["yb"] - 1.0, info["floors"][0] + 2.6), lens=18.0,
             kind="interior", purpose="gatehouse with the cold white windows; the ways up to the sanctum and down to the central block are not confirmed and not built")


REGIONS = {"UpperBridge": upper_bridge, "BridgeGatehouse": bridge_gatehouse}
