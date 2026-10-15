"""Stage 3 structure: the east city - EastWell, EastTower, EastPeakHall, EastStack, EastQuarter, EastStation,
EastRainGap, EastJarHouse and EastUndercroft."""
import math

import cot_assets as A
import cot_kit as K
import cot_parts as P
import cot_shell as SH
from cot_geo import Geo, TAU, lerp, place, rng, spiral_pts
from cot_s3 import X, Z
from regions.west import hive_jars, sign_lamp

EG = Z(3640)                                                # ground of the east well (lower than the plaza)


# ---------------------------------------------------------------------------- kit parts of the east city
def k_spire_niche(w=2.4, h=5.6, glass="glass_pink"):
    """Gabled door niche between two pinnacles, lit pink inside (A: 06_Right_City/Right_City_west.jpg)."""
    g = Geo()
    hw = w / 2
    spring = h * 0.34
    rise = h * 0.36
    g.use("stone_far_trim")
    g.box(-hw - 0.75, hw + 0.75, -0.3, 0.3, -0.02, 0.16)
    for sx in (-1, 1):
        g.box(sx * (hw + 0.2) - 0.2, sx * (hw + 0.2) + 0.2, -0.26, 0.26, 0.0, spring)
        g.box(sx * (hw + 0.62) - 0.12, sx * (hw + 0.62) + 0.12, -0.18, 0.18, 0.0, spring * 0.95)
    # steep gable with the pointed opening cut out of it
    out = [(hw + 0.42, spring), (0.0, h - 0.5), (-hw - 0.42, spring)]
    out += [(px, spring + pz) for px, pz in reversed(K.arch_profile(w, "pointed", rise))]
    g.prism(out, -0.26, 0.26)
    g.use("wall_deep")
    g.prism([(-hw, 0.0), (hw, 0.0)] + [(px, spring + pz) for px, pz in K.arch_profile(w, "pointed", rise)], 0.1, 0.24)
    g.use(glass)
    iw = w * 0.52
    g.prism([(-iw / 2, 0.3), (iw / 2, 0.3)] + [(px, spring * 0.9 + pz) for px, pz in K.arch_profile(iw, "pointed", rise * 0.7)], 0.0, 0.1)
    g.use("stone_far_trim")
    for k in range(3):                                      # chevron ribs over the pane
        zz = spring * 0.5 + 0.6 * k
        g.tube([(-iw / 2, -0.03, zz), (0, -0.03, zz + 0.36), (iw / 2, -0.03, zz)], 0.04, segs=4, ref=(0, 1, 0))
    g.tube([(hw + 0.42, -0.28, spring), (0.0, -0.28, h - 0.5), (-hw - 0.42, -0.28, spring)], 0.07, segs=5, ref=(0, 1, 0))
    g.use("iron")
    g.spike((0, 0, h - 0.6), (0, 0, h + 1.0), 0.09, segs=6, bulb=1.1)
    for sx in (-1, 1):
        g.spike((sx * (hw + 0.62), 0, spring * 0.95), (sx * (hw + 0.62), 0, spring * 0.95 + 1.7), 0.08, segs=6, bulb=1.0)
    return g


def k_pill_panel(w=2.9, h=6.0):
    """Round-ended filigree panel of the east tower's back wall (A: Right_City_elevator_upper.jpg lower edge; master B1)."""
    g = Geo()
    hw = w / 2
    zc0, zc1 = hw, h - hw
    out = [(hw * math.cos(math.pi * i / 12), zc1 + hw * math.sin(math.pi * i / 12)) for i in range(13)]
    out += [(hw * math.cos(math.pi + math.pi * i / 12), zc0 + hw * math.sin(math.pi + math.pi * i / 12)) for i in range(13)]
    g.use("pattern_blue")
    g.prism(out, -0.06, 0.1)
    g.use("trim")
    g.tube([(px, -0.08, pz) for px, pz in out + out[:1]], 0.11, segs=6, ref=(0, 1, 0))
    g.use("iron")
    g.tube([(0, -0.1, 0.3), (0, -0.1, h - 0.3)], 0.04, segs=4)
    for zz, r in ((h * 0.3, hw * 0.42), (h * 0.62, hw * 0.3)):
        g.ring_arc((0, -0.1, zz), 1.0, 0, TAU, 0.035 / max(r, 0.2), n=14, plane="XZ", segs=4, m=place(s=(r, 1.0, r * 1.5)))
        for sx in (-1, 1):
            g.tube([(sx * r * 0.9, -0.1, zz), (sx * hw * 0.7, -0.1, zz + r * 0.9), (sx * hw * 0.86, -0.1, zz + r * 0.2)], 0.03, segs=4, ref=(0, 1, 0))
            g.tube([(sx * r * 0.9, -0.1, zz - r * 0.3), (sx * hw * 0.66, -0.1, zz - r * 1.1), (sx * hw * 0.84, -0.1, zz - r * 0.5)], 0.03, segs=4, ref=(0, 1, 0))
    for k in range(4):
        zz = h * 0.76 + 0.3 * k
        half = hw * 0.5 * (1 - k / 5)
        g.tube([(-half, -0.1, zz), (0, -0.1, zz + 0.2), (half, -0.1, zz)], 0.025, segs=4, ref=(0, 1, 0))
    return g


def k_arch_niche(w=3.3, h=6.2):
    """Carved round-headed niche with an iron screen and a winged-bug emblem (A: the two niches under the relief in
    Right_City_elevator_upper.jpg; the master shows two per row in the lower part of the tower). Faces -Y, base at z = 0."""
    g = Geo()
    hw = w / 2
    spring = h - hw
    g.use("wall_deep")
    g.prism([(-hw, 0.0), (hw, 0.0)] + [(px, spring + pz) for px, pz in K.arch_profile(w, "round")], -0.02, 0.12)
    g.use("trim")
    SH.arch_ring(g, w, "round", 0.26, -0.22, 0.02, m=place(0, 0, spring))
    for sx in (-1, 1):
        g.box(sx * (hw + 0.13) - 0.13, sx * (hw + 0.13) + 0.13, -0.22, 0.02, 0.0, spring)
        g.revolve([(0.2, spring - 0.25), (0.26, spring - 0.1), (0.22, spring)], segs=8, m=place(sx * (hw + 0.13), -0.1, 0))
    g.box(-hw - 0.4, hw + 0.4, -0.26, 0.04, -0.05, 0.2)
    g.use("iron")
    g.tube([(0, -0.08, 0.2), (0, -0.08, h - 0.2)], 0.04, segs=4)
    for zz, r in ((h * 0.22, hw * 0.55), (h * 0.66, hw * 0.45)):
        for sx in (-1, 1):
            g.tube([(px * sx, -0.08, zz + pz) for px, pz in spiral_pts(r * 0.5, 0.0, r * 0.5, 1.2, math.pi / 2, ccw=sx > 0)], 0.03, segs=4, ref=(0, 1, 0))
            g.tube([(sx * 0.05, -0.08, zz + r * 0.9), (sx * hw * 0.8, -0.08, zz + r * 1.4), (sx * hw * 0.85, -0.08, zz + r * 0.4)], 0.03, segs=4, ref=(0, 1, 0))
    g.use("relief")                                       # winged-bug emblem in the middle of the screen
    ez = h * 0.44
    g.ellipsoid((0, -0.12, ez), (0.28, 0.12, 0.42), segs=10, steps=8)
    for sx in (-1, 1):
        for k in range(2):
            g.ellipsoid((sx * (0.45 + 0.1 * k), -0.1, ez + 0.15 - 0.3 * k), (0.32, 0.06, 0.13), segs=8, steps=5)
    return g


def k_bound_column(h=6.0, r=0.2):
    """Fluted shaft bound with cords and carrying a scarab-shell ornament (A: Right_City_elevator_upper.jpg)."""
    g = Geo()
    g.use("trim")
    g.revolve([(r, 0.0), (r, h)], segs=10, mod=lambda a, z: 1.0 + 0.12 * math.cos(5 * a))
    for zz in (0.5, 0.72, 0.94, h * 0.5 - 0.1, h * 0.5 + 0.12, h - 0.9, h - 0.68):
        g.ring_arc((0, 0, zz), r * 1.22, 0, TAU, 0.07, n=10, plane="XY", segs=4)
    zs = h * 0.74
    g.use("relief")
    g.ellipsoid((0, -r * 0.9, zs), (r * 1.5, r * 0.9, r * 2.3), segs=10, steps=7)
    for sx in (-1, 1):
        for k in range(3):
            a = math.radians(24 + 26 * k)
            g.ellipsoid((sx * r * (1.3 + 0.9 * math.cos(a)), -r * 0.7, zs + r * (0.4 + 1.5 * math.sin(a))), (r * 1.0, r * 0.3, r * 0.42), segs=8, steps=5)
    g.use("wall_deep")
    for dz in (-0.7, 0.0, 0.7):
        g.tube([(-r * 1.4, -r * 1.75, zs + r * dz), (0, -r * 1.86, zs + r * dz + 0.02), (r * 1.4, -r * 1.75, zs + r * dz)], 0.016, segs=4, ref=(0, 0, 1))
    return g


def k_bowl(v=0):
    """Glass specimen bowl on a foot (A: master C4 rows of round vessels; details are completion)."""
    g = Geo()
    s = (1.0, 0.8, 1.25)[v % 3]
    g.use("trim_purple")
    g.revolve([(0.34 * s, 0.0), (0.36 * s, 0.07), (0.16 * s, 0.14), (0.14 * s, 0.24), (0.3 * s, 0.3)], segs=12)
    g.use("jar_glass")
    g.ellipsoid((0, 0, 0.3 + 0.5 * s), (0.56 * s, 0.56 * s, 0.5 * s), segs=14, steps=9)
    g.use("trim_purple")
    g.revolve([(0.2 * s, 0.3 + 0.96 * s), (0.26 * s, 0.3 + 1.0 * s), (0.2 * s, 0.3 + 1.06 * s), (0.05 * s, 0.3 + 1.12 * s), (0.03 * s, 0.3 + 1.24 * s)], segs=10)
    return g


def k_urn():
    """Dark lidded urn on a stand (A: master C4)."""
    g = Geo().use("pot")
    g.revolve([(0.3, 0.0), (0.34, 0.08), (0.1, 0.2), (0.09, 0.7), (0.3, 0.86), (0.6, 1.3), (0.62, 1.62), (0.42, 1.9), (0.2, 1.98), (0.24, 2.06), (0.06, 2.16), (0.02, 2.3)], segs=14)
    return g


def k_hook_lamp(lamp="lamp"):
    """Wall lamp on a curled hook (A: master C4)."""
    g = Geo().use("trim_purple")
    g.tube([(0, 0, 0), (0, -0.5, 0.1), (0, -0.78, -0.12), (0, -0.7, -0.42), (0, -0.52, -0.5)], 0.035, segs=5, ref=(1, 0, 0))
    g.use(lamp)
    g.ellipsoid((0, -0.52, -0.66), (0.17, 0.17, 0.17), segs=10, steps=6)
    return g


def k_sofa():
    """Tufted settee with a high shell back (A: Right_City_peak.jpg, step2.jpg)."""
    g = Geo()
    g.use("cushion")
    g.ellipsoid((0, 0, 0.5), (1.3, 0.6, 0.34), segs=14, steps=6, e=0.6)
    for k in range(4):
        g.ellipsoid((-0.9 + 0.6 * k, 0.5, 1.2), (0.36, 0.2, 0.62), segs=8, steps=6)
    g.use("trim_purple")
    g.box(-1.3, 1.3, -0.5, 0.62, 0.0, 0.3)
    for sx in (-1, 1):
        g.revolve([(0.12, 0.0), (0.1, 0.9), (0.18, 1.0), (0.05, 1.2)], segs=8, m=place(sx * 1.34, 0.5, 0))
        g.tube([(sx * 1.34, 0.5, 0.9), (sx * 1.4, 0.0, 0.84), (sx * 1.3, -0.5, 0.6)], 0.06, segs=5, ref=(0, 0, 1))
    return g


def hook_lamps(S, R, name, items, ref, lamp="lamp"):
    kit = S.kit(f"hooklamp_{lamp}", lambda: k_hook_lamp(lamp))
    return [S.put(kit, f"{name}_{i:02d}", R, "HookLamp", place(x, y, z), "A", ref) for i, (x, y, z) in enumerate(items)]


def tier_balcony(S, R, name, x0, x1, y0, y1, z, niches=(), banners=(), rails=(), ref="", surf=None):
    """Stone balcony tier on round under-arches, with gabled niches, spear rails and hanging pennants."""
    g = Geo()
    K.slab(g, x0, x1, y0, y1, z, 0.5, "stone", lip=("front",), trim="stone_far_trim")
    bays = max(2, int(round((x1 - x0) / 2.6)))
    P.under_arcade(g, x0 + 0.4, x1 - 0.4, y0 + 0.1, y1, z - 0.5, z - 1.7, bays, key="stone", trim="stone_far_trim")
    for xe in (x0, x1):
        A.add_corbel_wing(g, place(xe, y0 + 0.5, z - 0.5, rz=math.pi if xe == x0 else 0.0), length=1.3, blades=4, key="stone_far_trim")
    g.use("iron")
    for xe in (x0 + 0.2, x1 - 0.2):
        g.spike((xe, y0 + 0.2, z), (xe, y0 + 0.2, z + 1.9), 0.07, segs=6, bulb=1.0)
    for xa, xb in rails:
        K.spike_rail(g, (xa, y0 + 0.2), (xb, y0 + 0.2), z, h=0.95)
    S.add(g, name, R, "TierBalcony", "A", ref, note="depth of the balcony is completion", smooth=35)
    niche = S.kit("spire_niche", lambda: k_spire_niche())
    for k, nx in enumerate(niches):
        ny = (surf(nx) if surf else y1) - 1.7
        S.put(niche, f"{name}_Niche_{k}", R, "SpireNiche", place(nx, ny, z), "A", ref)
    ban = S.kit("banner_long", lambda: K.k_banner(1.2, 4.6))
    for k, bx in enumerate(banners):
        S.put(ban, f"{name}_Banner_{k}", R, "Banner", place(bx, y0 + 0.7, z - 0.55), "A", ref)


def backdrop_towers(S, R, ids, seed0, dy=0.0):
    for i, eid in enumerate(ids):
        e = S.el(R, eid)
        tx0, tx1, tz1, tz0 = X(e["map"][0]), X(e["map"][2]), Z(e["map"][1]), Z(e["map"][3])
        r = (tx1 - tx0) / 2
        P.tower(S, R, eid, (tx0 + tx1) / 2, e["yc"] + (dy if e["yc"] > 0 else 0.0), tz0 - 4.0, tz1, r, windows=e["windows"], roof=e["roof"], seed=seed0 + i, leaf=(3.2, 8.0), tier=8.5,
                ry_scale=e["ry"] / r, far=True, ev=e["ev"], ref=e["ref"], layer="BACKDROP", note="depth is completion")


FRINGE_HANG = 5.6      # the lowest fringe tier of P.tower hangs this far below the base it is given (measured)


def fit_above(objs, seat):
    """Squeeze a built tower vertically (about its top) so that nothing of it hangs below seat: its fringe must not
    reach into the building it stands on."""
    from mathutils import Matrix, Vector
    objs = [o for o in objs if o is not None]
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    zmin, ztop = min(p.z for p in pts), max(p.z for p in pts)
    if zmin >= seat - 1e-3 or ztop - zmin < 1e-3:
        return
    f = (ztop - seat) / (ztop - zmin)
    m = Matrix.Translation((0, 0, ztop)) @ Matrix.Diagonal((1.0, 1.0, f, 1.0)) @ Matrix.Translation((0, 0, -ztop))
    for o in objs:
        o.matrix_world = m @ o.matrix_world


def layout_tower(S, R, eid, seed, z0=None, leaf=(2.8, 7.2), tier=8.0, dx=0.0, r_scale=1.0, seat=None, **kw):
    e = S.el(R, eid)
    tx0, tx1, tz1, tz0 = X(e["map"][0]), X(e["map"][2]), Z(e["map"][1]), Z(e["map"][3])
    r = (tx1 - tx0) / 2 * r_scale
    objs = P.tower(S, R, eid, (tx0 + tx1) / 2 + dx, e["yc"], tz0 if z0 is None else z0, tz1, r, windows=int(e["windows"] * 1.6), roof=e["roof"], seed=seed, leaf=leaf,
                   tier=tier, ry_scale=e["ry"] / r, ev=e["ev"], ref=e["ref"], arc=(-math.pi * 1.12, math.pi * 0.12), **kw)
    if seat is not None:
        fit_above(objs, seat)
    return (tx0 + tx1) / 2 + dx, r, e["yc"], e["ry"], tz0, tz1


def tower_foot(S, R, name, cx, cy, r, ry, z_seat, z_top, ref):
    """Plain round foot under a shell tower whose fringe must stay clear of the building it stands on."""
    g = Geo().use("tower_core")
    g.revolve([(r * 0.8, z_seat), (r * 0.84, z_seat + 0.4), (r * 0.84, z_top)], segs=20, m=place(cx, cy, 0), sy=ry / r)
    g.use("stone_far_trim")
    g.revolve([(r * 0.92, z_seat), (r * 0.95, z_seat + 0.25), (r * 0.86, z_seat + 0.5)], segs=20, m=place(cx, cy, 0), sy=ry / r)
    S.add(g, name, R, "TowerFoot", "C", ref, note="plain foot that carries the tower above the roof it stands on")


# ============================================================================ EastWell
def east_well(S):
    R = "EastWell"
    REF = "06_Right_City/Right_City_west.jpg; master C3"
    gr = S.el(R, "Ground")
    gx0, gx1 = X(gr["map"][0]), X(gr["map"][2])
    sb = S.el(R, "SmallBridge")
    bx0, bx1, bz = X(sb["x"][0]), X(sb["x"][1]), Z(sb["deck"])
    # ---- ground: quay each side of a channel that the small bridge crosses (A bridge; channel depth is C)
    ZB, ZL, BAL = Z(gr["map"][3]), Z(3664), Z(3587)             # ground underside, lower corridor floor, upper corridor floor
    YB0, YB1 = -1.2, 2.0                                        # depth of the balcony strip
    g = Geo().use("stone")
    g.box(bx1, gx1, -14.0, 44.0, ZB, EG - 0.24)
    g.box(gx0, bx0, -14.0, -5.2, ZB, EG - 0.24)                 # front apron of the west end
    g.box(gx0, bx0, 10.6, 44.0, ZB, EG - 0.24)
    g.box(bx0, bx1, 6.0, 44.0, ZB, EG - 0.24)
    g.use("stone_dark")
    g.box(bx0, bx1, -14.0, 6.0, Z(gr["map"][3]), Z(sb["band_to"]) - 0.6)
    A.add_cobbles(g, bx1, gx1, -14.0, 20.0, EG, size=(0.8, 0.62), seed=71, key="cobble", height=0.26)
    A.add_cobbles(g, gx0, bx0, -14.0, -5.2, EG, size=(0.8, 0.62), seed=72, key="cobble", height=0.26)
    A.add_cobbles(g, gx0, bx0, 10.6, 20.0, EG, size=(0.8, 0.62), seed=73, key="cobble", height=0.26)
    g.use("stone")
    g.box(bx1, gx1, 20.0, 44.0, EG - 0.24, EG)
    g.box(gx0, bx0, 20.0, 44.0, EG - 0.24, EG)
    g.box(bx0, bx1, 6.0, 44.0, EG - 0.24, EG)
    S.add(g, "Ground", R, "Ground", "A", REF, note="quay and cobbles observed; the channel under the small bridge and all depths are completion", smooth=35)
    # west end (A: master C8 shows the upper corridor coming out on a railed platform, a stepped mass under its east end and
    # the lower gallery ending beside it; B/C: how the flights are arranged in depth)
    xc = X(5414)                                                # east end of the upper corridor
    g = Geo().use("stone")
    g.box(xc, gx0, YB0, YB1, Z(3608) + 0.45, BAL)               # balcony slab over the lower corridor's roof
    P.stone_pier(g, gx0, 117.0, YB0, YB1, ZB, BAL, seed=5)
    P.stairs(g, 117.0, 121.6, YB0 + 0.2, YB1 - 0.6, BAL, bz, step=0.42, key="stone")
    g.use("stone")
    g.box(117.0, bx0, YB0, YB1, ZB, bz)
    g.box(gx0, gx0 + 1.2, -5.2, YB0, ZB, ZL)                    # landing of the lower corridor
    g.box(gx0 + 1.2, bx0, -5.2, YB0, ZB, ZL)
    P.stairs(g, gx0 + 1.2, bx0, -5.2, -2.7, ZL, bz, step=0.36, key="stone")
    P.stone_pier(g, bx0, bx0 + 2.0, -5.2, sb["y"][0], ZB, bz, seed=8)       # rubble pier where that flight meets the bridge
    S.add(g, "WestEnd", R, "WestEndStairs", "B", "master C8; 10_Elevator/Elevator_bottom.jpg",
          note="platform level with the upper corridor and a stepped mass at its east end are on the master; the arrangement of the two flights in depth is completion", smooth=35)
    g = Geo()
    P.stone_pier(g, gx0 - 0.1, bx0, YB1, 10.6, ZB, Z(3580), seed=6)
    S.add(g, "WestFlankBase", R, "TowerBasePier", "A", "master C8: masonry under the west flank tower", smooth=35)
    P.spike_rail(S, R, "WestEnd_Rail", [((xc, YB0 + 0.12), (117.0, YB0 + 0.12))], z=BAL, ev="A", ref="master C8")
    P.lamp(S, R, "BalconyLamp", xc + 1.6, YB1 - 0.5, BAL, ev="A", ref="master C8")
    P.water(S, R, "ChannelWater", bx0, bx1, -14.0, 6.0, Z(sb["band_to"]) - 0.1, ev="C", ref="dark below the small bridge on Right_City_west.jpg; water is completion")
    g = Geo()
    K.slab(g, bx0 - 0.2, bx1 + 0.2, sb["y"][0], sb["y"][1], bz, 0.5, "stone", lip=("front", "back"), trim="stone_far_trim")
    P.under_arcade(g, bx0, bx1, sb["y"][0] + 0.1, sb["y"][1] - 0.1, bz - 0.5, Z(sb["band_to"]), sb["bays"], key="stone", trim="stone_far_trim")
    S.add(g, "SmallBridge", R, "SmallBridge", "A", sb["ref"], smooth=35)
    P.spike_rail(S, R, "SmallBridge_Rail", [((bx0 + 2.0, sb["y"][0] + 0.15), (bx1, sb["y"][0] + 0.15)), ((bx0, sb["y"][1] - 0.15), (bx1, sb["y"][1] - 0.15))], z=bz, ev="A", ref=sb["ref"])
    for k in range(4):
        P.lamp(S, R, f"BridgeLamp_{k}", lerp(bx0 + 1.4, bx1 - 1.4, k / 3), sb["y"][1] - 0.6, bz, ev="A", ref=REF)
    P.ring_posts(S, R, "ChannelPost", [(lerp(bx0 + 1.0, bx1 - 1.0, k / 5), -6.0 - 1.5 * (k % 2), Z(sb["band_to"]) - 0.6) for k in range(6)], ev="C", ref="mooring posts as in the central well; completion")

    # ---- the towers of the well (A)
    ucx, ur, uyc, ury, _, uz1 = layout_tower(S, R, "UmbrellaTower", 61, z0=EG - 1.0, leaf=(3.0, 7.6), tier=8.5)
    layout_tower(S, R, "LeftTower", 62, z0=EG - 1.0)
    rcx, rr, ryc, rry, rz0, _ = layout_tower(S, R, "RightTower", 63, z0=EG - 1.0, r_scale=0.93, dx=-0.6, note="master draws it above the top balcony; carried down to the ground behind the balconies as Right_City_west.jpg shows fringe tiers there (B)")
    layout_tower(S, R, "WestFlank", 64, leaf=(2.0, 5.0), tier=6.0)
    layout_tower(S, R, "UpperColumnTower", 65)

    def surf_u(x):
        t = max(-0.98, min(0.98, (x - ucx) / ur))
        return uyc - ury * math.sqrt(1 - t * t)

    def surf_r(x):
        t = max(-0.98, min(0.98, (x - rcx) / rr))
        return ryc - rry * math.sqrt(1 - t * t)

    # ---- balcony tiers in front of the towers (A: Right_City_west.jpg)
    ta, tb = S.el(R, "TiersA")["items"], S.el(R, "TiersB")["items"]
    spec_a = (((0.3, 0.72), (0.12, 0.5, 0.9), ((0.0, 0.2), (0.8, 1.0))), ((0.5,), (0.85,), ((0.0, 0.3),)), ((0.45,), (0.1,), ((0.6, 1.0),)))
    for k, ((mx0, mx1, my), (nf, bf, rf)) in enumerate(zip(ta, spec_a)):
        x0, x1 = X(mx0), X(mx1)
        tier_balcony(S, R, f"TierA_{k}", x0, x1, -2.2, 7.0, Z(my), niches=[lerp(x0, x1, f) for f in nf], banners=[lerp(x0, x1, f) for f in bf],
                     rails=[(lerp(x0, x1, a), lerp(x0, x1, b)) for a, b in rf], ref=REF, surf=surf_u)
    spec_b = (((0.3, 0.78), (0.1, 0.55), ((0.0, 0.25),)), ((0.62,), (0.25, 0.5, 0.86), ((0.0, 0.5),)), ((0.6,), (0.2,), ((0.0, 0.45),)))
    for k, ((mx0, mx1, my), (nf, bf, rf)) in enumerate(zip(tb, spec_b)):
        x0, x1 = X(mx0), X(mx1)
        tier_balcony(S, R, f"TierB_{k}", x0, x1, -2.2, 9.0, Z(my), niches=[lerp(x0, x1, f) for f in nf], banners=[lerp(x0, x1, f) for f in bf],
                     rails=[(lerp(x0, x1, a), lerp(x0, x1, b)) for a, b in rf], ref=REF, surf=surf_r)
    # ground-level niches and banners under the lowest tiers (A)
    niche = S.kit("spire_niche", lambda: k_spire_niche())
    for k, nx in enumerate((140.0, 144.6, 149.6, 161.5, 166.0)):
        S.put(niche, f"GroundNiche_{k}", R, "SpireNiche", place(nx, (surf_u(nx) if nx < 156 else surf_r(nx)) - 1.7, EG), "A", REF)
    # small stepping slabs between the tiers (A: three little ledges between the two groups)
    g = Geo()
    for k, (sx, sz) in enumerate(((155.6, 1.6), (156.4, 8.8), (155.2, 12.8), (135.2, 7.0), (134.6, 2.6))):
        SH.float_slab(g, sx, 0.5, sz, w=1.8, d=1.6, seed=k)
    S.add(g, "Ledges", R, "FloatingPlatform", "A", REF, note="depth positions are completion", smooth=35)
    for k, lx in enumerate((137.5, 171.0)):
        P.lamp(S, R, f"QuayLamp_{k}", lx, -3.0, EG, ev="A", ref=REF)

    # ---- rock roofs (A) and backdrop towers (B / C)
    for eid, amp in (("Ceiling", 1.8), ("UpperColumnCeiling", 1.2)):
        e = S.el(R, eid)
        cx0, cx1, cz0, cz1 = X(e["map"][0]), X(e["map"][2]), Z(e["map"][3]), Z(e["map"][1])
        P.rock(S, R, eid, cx0, cx1, e["y"][0], e["y"][1], cz0, cz1, ev="A", ref=e["ref"], layer="CEILING", amp=amp, cell=4.0)
        g = Geo()
        K.stalactite_field(g, cx0 + 1.0, cx1 - 1.0, e["y"][0] + 2.0, 40.0, lambda x, y, cz0=cz0: cz0 + 0.4, 60, seed=len(eid), lmin=1.0, lmax=4.2)
        SH.hanging_fringe(g, cx0 + 0.5, cx1 - 0.5, e["y"][0] + 0.4, cz0 + 0.3, 2.4, seed=len(eid) + 3)
        S.add(g, eid + "_Stalactites", R, "Stalactites", "A", e["ref"], layer="CEILING", smooth=50)
    backdrop_towers(S, R, ("BackTower", "BackTowerB", "BackTowerC", "FrontTowerA", "FrontTowerB"), 66)

    # ---- cameras
    for k, (kind, mx, my, dy) in enumerate((("husk_sentry", (5774 + 6032) / 2 + 30, 3553, 0.6), ("lance_sentry", (5840 + 5978) / 2, 3466, 0.8),
                                            ("husk_sentry_low", (6125 + 6302) / 2, 3520, 0.4), ("resident_1", (6098 + 6275) / 2, 3424, 0.9))):
        P.creature(S, R, kind, f"Tier_{k}", X(mx), dy, Z(my) + 0.01, rz=0.5 - 0.3 * k)
    for k, (kind, cx_, cy_) in enumerate((("resident_0", bx1 + 6.0, -8.0), ("resident_2", bx1 + 13.0, -6.5), ("husk_sentry", gx1 - 8.0, -9.0))):
        P.creature(S, R, kind, f"Quay_{k}", cx_, cy_, EG + 0.01, rz=0.6 * (k - 1))
    P.creature(S, R, "winged_sentry", "Air_0", 150.0, -6.0, 26.0, rz=0.5)
    S.cam_auto(R, (gx0, gx1, -14.0, 22.0, EG - 3.0, Z(2560)), ref="master B1, C3", views=("front", "oblique", "obliqueR", "back"))
    S.cam_front("GroundSection", R, (5450, 3250, 6330, 3680), y=-14.0, hide=("FRONT", "BACKDROP"), ref="master C3_east_ground_left", purpose="ground and balcony tiers, same frame as master C3")
    S.camera("REF_West", R, (152.0, -34.0, 6.5), look=(152.0, 6.0, 7.5), lens=30.0, kind="ref", hide=("CAVESHELL", "BACKDROP"), purpose="balcony tiers, compare Right_City_west.jpg", ref=REF)
    S.camera("LookUp", R, (150.0, -30.0, 1.0), look=(148.0, 10.0, 45.0), lens=18.0, kind="view", hide=("CAVESHELL",), purpose="up the well from the quay")
    S.camera("WestEnd", R, (127.0, -13.0, 3.4), look=(116.0, -0.5, -1.6), lens=24.0, kind="view", hide=("CAVESHELL",), purpose="west end: corridor doors, railed platform, both flights and the bridge head, compare master C8", ref="master C8")
    S.camera("BridgeEnd", R, (bx0 - 3.0, -7.0, bz + 2.0), look=(bx1 + 6.0, 2.0, bz + 3.0), lens=24.0, kind="view", hide=("CAVESHELL",), purpose="small bridge, lamps and the west flank", ref=sb["ref"])


# ============================================================================ EastTower
def east_tower(S):
    R = "EastTower"
    REF = "06_Right_City/Right_City_elevator_upper.jpg; Right_City_elevator.jpg; master B1"
    sh = S.el(R, "Shaft")
    x0, x1, zb, zt = X(sh["map"][0]), X(sh["map"][2]), Z(sh["map"][3]), Z(sh["map"][1])
    y0, y1 = sh["y"]
    cx = (x0 + x1) / 2
    t = 0.5
    hall_z = Z(2634)
    # ---- walls: back (A) and sides, an east door to the dome hall (B), the viewer-side wall (C)
    g = Geo().use("wall_deep")
    g.box(x0, x1, y1 - t, y1, zb - 0.6, zt)
    g.box(x0, x0 + t, y0, y1 - t, zb - 0.6, zt)
    K.arcade(g, y0, y1 - t, zb - 0.6, hall_z + 6.0, 0.0, t, [(0.0, 2.8, hall_z + 2.6, "pointed", 1.6, hall_z)], m=place(x1, 0, 0, rz=math.pi / 2))
    g.box(x1 - t, x1, y0, y1 - t, hall_z + 6.0, zt)
    K.slab(g, x0 + t, x1 - t, y0 + t, y1 - t, zb, 0.6, "floor", lip=())
    g.use("stone_far")
    for zz in [zb + 13.0 * k for k in range(1, 7) if zb + 13.0 * k < zt - 2.0]:
        for (ax, bx, ay, by) in ((x0 - 0.22, x0, y0, y1), (x1, x1 + 0.22, y0, y1), (x0 - 0.22, x1 + 0.22, y1, y1 + 0.22)):
            g.box(ax, bx, ay, by, zz - 0.25, zz + 0.25)
    for px in (x0, x1):
        for py in (y0, y1):
            g.box(px - 0.4, px + 0.4, py - 0.4, py + 0.4, zb - 0.6, zt)
    # outer faces of the tallest landmark of the east city: pilasters, a fringe at every band, leaf windows (C, D-365)
    nb_ = max(2, int((x1 - x0) / 2.8))
    for k in range(1, nb_):
        xx = lerp(x0, x1, k / nb_)
        g.box(xx - 0.16, xx + 0.16, y1, y1 + 0.32, zb - 0.6, zt)
    ns_ = max(2, int((y1 - y0) / 2.8))
    for k in range(1, ns_):
        yy = lerp(y0, y1, k / ns_)
        g.box(x0 - 0.32, x0, yy - 0.16, yy + 0.16, zb - 0.6, zt)
        g.box(x1, x1 + 0.32, yy - 0.16, yy + 0.16, hall_z + 6.0, zt)
    bands_ = [zb + 13.0 * k for k in range(1, 7) if zb + 13.0 * k < zt - 2.0]
    for zz in bands_:
        SH.hanging_fringe(g, x0 + 0.1, x1 - 0.1, y1 + 0.42, zz - 0.25, 1.6, seed=int(zz * 3))
        SH.hanging_fringe(g, y0 + 0.2, y1 - 0.2, x0 - 0.42, zz - 0.25, 1.6, seed=int(zz * 5), axis="Y")
    S.add(g, "Shaft_Walls", R, "TowerShaft", "A", REF, note="plan depth and the outer faces are completion")
    gf, gg = Geo(), Geo()
    for j, (za, zbb) in enumerate(zip([zb] + bands_, bands_ + [zt])):
        if zbb - za < 9.0 or j % 2:
            continue
        A.add_leaf_window(gf, gg, place((x0 + x1) / 2, y1 + 0.35, (za + zbb) / 2 - 3.0, rz=math.pi), 2.2, 6.0, index=j, glass_key="glass")
        A.add_leaf_window(gf, gg, place(x0 - 0.35, (y0 + y1) / 2, (za + zbb) / 2 - 3.0, rz=-math.pi / 2), 2.0, 5.4, index=j + 5, glass_key="glass")
    S.add(gf, "Shaft_LeafFrames", R, "LeafWindows", "C", REF, note="leaf windows on the outer faces: completion")
    S.add(gg, "Shaft_LeafGlass", R, "LeafWindows", "C", REF)
    g = Geo().use("wall_deep")
    ops = [(cx + dx, 2.4, zz + 2.0, "round", None, zz - 2.2) for zz in (Z(1800), Z(2086), Z(2344), Z(2626), Z(2758)) for dx in (-3.6, 0.0, 3.6)]
    for zlo, zhi, row in ((zb - 0.6, Z(2700), ops[12:15]), (Z(2700), Z(2560), ops[9:12]), (Z(2560), Z(2230), ops[6:9]), (Z(2230), Z(1960), ops[3:6]), (Z(1960), zt, ops[0:3])):
        K.arcade(g, x0 + 0.4, x1 - 0.4, zlo, zhi, y0, y0 + t, row)
    S.add(g, "Shaft_Front", R, "TowerShaft", "C", REF, note="viewer-side wall with round-ended openings: completion", layer="FRONT")
    # ---- cap (A: rounded top on the master)
    g = Geo().use("louvre_core")
    hw, hd = (x1 - x0) / 2 + 0.2, (y1 - y0) / 2 + 0.2
    g.revolve([(1.0, 0.0)] + [(math.cos(math.pi / 2 * i / 8), 3.6 * math.sin(math.pi / 2 * i / 8)) for i in range(1, 8)] + [(0.02, 3.6)], segs=20, m=place(cx, (y0 + y1) / 2, zt), sx=hw, sy=hd)
    g.use("louvre_frame")
    for k in range(8):
        a = TAU * k / 8 + TAU / 16
        g.tube([(cx + hw * 1.01 * math.cos(math.pi / 2 * i / 8) * math.cos(a), (y0 + y1) / 2 + hd * 1.01 * math.cos(math.pi / 2 * i / 8) * math.sin(a), zt + 3.62 * math.sin(math.pi / 2 * i / 8))
                for i in range(9)], 0.09, segs=5, ref=(0, 0, 1))
    g.box(x0 - 0.3, x1 + 0.3, y0 - 0.3, y1 + 0.3, zt - 0.3, zt + 0.1)
    g.use("iron")
    g.spike((cx, (y0 + y1) / 2, zt + 3.5), (cx, (y0 + y1) / 2, zt + 6.0), 0.12, segs=6, bulb=1.2)
    S.add(g, "Cap", R, "TowerCap", "A", S.el(R, "Cap")["ref"], smooth=40)
    # ---- back wall: winged-shell reliefs alternating with rows of round-ended filigree panels (A)
    def relief_geo():
        gg = Geo()
        K.winged_shell_relief(gg, 10.4, 8.6)
        return gg

    rel = S.kit("winged_relief", relief_geo, smooth=50)
    for k, my in enumerate((1958, 2212, 2472)):
        S.put(rel, f"Relief_{k}", R, "WingedShellRelief", place(cx, y1 - t - 0.26, Z(my) - 4.3), "A", REF,
              note="relief observed once in the screenshot and repeated up the tower on the master")
    pill = S.kit("pill_panel", lambda: k_pill_panel(2.9, 6.0))
    pill_z = (Z(1800), Z(2086), Z(2344), Z(2626), Z(2758))
    niche = S.kit("arch_niche", lambda: k_arch_niche(3.3, 6.2))
    for k, zz in enumerate(pill_z):
        if k >= 3:                                         # lower rows: two carved arch niches (A: screenshot and master B1)
            for j, dx in enumerate((-2.0, 2.0)):
                S.put(niche, f"Niche_{k}_{j}", R, "ArchNiche", place(cx + dx, y1 - t - 0.1, zz - 3.1), "A", REF)
        else:
            for j, dx in enumerate((-3.6, 0.0, 3.6)):
                S.put(pill, f"Pill_{k}_{j}", R, "FiligreePanel", place(cx + dx, y1 - t - 0.12, zz - 3.0), "A", REF)
        for j, (px, rz) in enumerate(((x0 - 0.1, -math.pi / 2), (x1 + 0.1, math.pi / 2))):       # the same panels on the outer side faces (C)
            for dy in (-2.4, 2.4):
                if abs(zz - hall_z - 3.0) < 6.0 and px > cx and dy < 0:
                    continue
                S.put(pill, f"PillSide_{k}_{j}_{int(dy > 0)}", R, "FiligreePanel", place(px, dy, zz - 3.0, rz=rz), "C", REF, note="outer faces: completion")
        S.put(pill, f"PillBack_{k}", R, "FiligreePanel", place(cx, y1 + 0.1, zz - 3.0, rz=math.pi), "C", REF, note="outer faces: completion")
    # ---- bound columns in pairs down both sides (A)
    col = S.kit("bound_column_6", lambda: k_bound_column(6.0, 0.2))
    n = int((zt - zb) // 6.0)
    for i in range(n):
        for j, (px, py) in enumerate(((x0 + 0.95, y1 - 1.1), (x0 + 1.55, y1 - 1.1), (x1 - 0.95, y1 - 1.1), (x1 - 1.55, y1 - 1.1))):
            S.put(col, f"BoundColumn_{j}_{i:02d}", R, "BoundColumn", place(px, py, zb + 6.0 * i), "A", REF)
    # ---- timber staging with jars (A), ledge and link to the dome hall (B)
    wp = S.el(R, "WoodPlatform")
    wx0, wx1, wz = X(wp["map"][0]) + 0.1, X(wp["map"][2]) + 0.6, Z(wp["map"][1])
    g = Geo().use("wood")
    g.box(wx0, wx1, -2.0, 2.4, wz - 0.2, wz)
    for px in (wx0 + 0.15, wx1 - 0.15):
        for py in (-1.8, 2.2):
            g.box(px - 0.07, px + 0.07, py - 0.07, py + 0.07, wz, wz + 5.4)
    for zz in (wz + 2.6, wz + 5.2):
        g.tube([(wx0 + 0.15, -1.8, zz), (wx1 - 0.15, -1.8, zz)], 0.06, segs=5)
        g.tube([(wx0 + 0.15, 2.2, zz), (wx1 - 0.15, 2.2, zz)], 0.06, segs=5)
        g.tube([(wx1 - 0.15, -1.8, zz), (wx1 - 0.15, 2.2, zz)], 0.06, segs=5)
    g.tube([(wx0 + 0.15, -1.8, wz + 0.2), (wx1 - 0.15, -1.8, wz + 2.6)], 0.05, segs=5)
    g.box(wx0 + 2.0, wx0 + 3.2, -0.4, 0.4, wz + 0.5, wz + 0.58)
    g.box(wx0 + 2.5, wx0 + 2.7, -0.1, 0.1, wz, wz + 0.5)
    SH.hanging_fringe(g, wx0, wx1, -1.9, wz - 0.2, 2.2, seed=7)
    SH.hanging_fringe(g, wx0, wx1, 2.3, wz - 0.2, 2.2, seed=8)
    S.add(g, "WoodPlatform", R, "TimberStaging", "A", wp["ref"], smooth=35)
    hive_jars(S, R, "Jars", [(wx0 + 0.9, 0.2, wz), (wx0 + 1.5, -0.4, wz)], wp["ref"])
    # ---- creatures (D-347): a lance sentry on the staging, a sentry on the shaft floor, a flying sentry in the shaft (C)
    P.creature(S, R, "lance_sentry", "Staging", wx0 + 4.2, 0.6, wz + 0.01, rz=-math.pi / 2)
    P.creature(S, R, "husk_sentry", "Floor", cx - 1.6, (y0 + y1) / 2, zb + 0.01, rz=0.4)
    P.creature(S, R, "winged_sentry", "Air", cx + 1.2, (y0 + y1) / 2 - 1.0, lerp(zb, hall_z, 0.5), rz=2.6)
    g = Geo()
    K.slab(g, x1 - 3.6, x1 + 1.9, -2.2, 2.2, hall_z, 0.5, "stone", lip=("front", "back"), trim="stone_far_trim")
    K.corbel(g, x1 - 3.4, -2.0, hall_z - 0.5, size=1.6, key="stone_far_trim", facing=-1)
    K.corbel(g, x1 - 3.4, 2.0, hall_z - 0.5, size=1.6, key="stone_far_trim", facing=-1)
    K.spike_rail(g, (x1 - 3.5, -2.0), (x1 - 3.5, 2.0), hall_z)
    S.add(g, "HallLedge", R, "TowerLedge", "B", "master C5: the dome hall's west door meets the tower; the ledge is completion", smooth=35)
    # ---- domed car on its long chain (A)
    zc = Z(sh["car"]) + 0.0
    S.put(S.kit("car_dome", lambda: K.k_car_dome()), "Car", R, "LiftCarDome", place(cx, 0.0, zb + 0.02), "A", REF)
    g = Geo()
    K.chain(g, cx, 0.0, zb + K.CAR_DOME_TOP - 0.1, zt)
    S.add(g, "Chain", R, "LiftChain", "A", REF)
    # ---- below the tower: glass columns either side of a rain strip, stem tower, canopy (A; stem depth C)
    for eid in ("LowerGlassL", "LowerGlassR"):
        e = S.el(R, eid)
        P.glass_pillar(S, R, eid, X(e["x"]), -3.6, e["r"] / 15.0 + 0.2, Z(e["map_y"][1]), Z(e["map_y"][0]), "A", e["ref"])
    tower_foot(S, R, "Stem_Foot", cx, 3.0, 5.2, 5.2, Z(3340) + 0.5, Z(3340) + 0.6 + FRINGE_HANG, "foot of the stem on the quarter roof")
    stem = P.tower(S, R, "Stem", cx, 3.0, Z(3340) + 0.6 + FRINGE_HANG, zb - 0.6, 5.2, windows=6, roof="flat", seed=77, leaf=(2.4, 6.0), tier=7.0, ev="B",
            ref="master B1: leaf windows in the rain strip under the tower", note="the tower's support below the shaft; its form is completion")
    fit_above(stem, Z(3340) + 0.6)
    g = Geo().use("stone_far")
    g.box(x0 - 0.4, x1 + 0.4, y0 - 0.4, y1 + 0.4, zb - 1.6, zb - 0.6)
    SH.hanging_fringe(g, x0, x1, y0 - 0.3, zb - 1.6, 2.6, seed=3)
    SH.hanging_fringe(g, x0, x1, y1 + 0.3, zb - 1.6, 2.6, seed=4)
    S.add(g, "ShaftBase", R, "TowerBase", "C", "base slab of the shaft")
    lc = S.el(R, "LowerCanopy")
    P.louvre_roof(S, R, "LowerCanopy", X(lc["map"][0]), X(lc["map"][2]), Z(lc["map"][3]), Z(lc["map"][1]) + 1.6, lc["y"][0], lc["y"][1], bays=2, curve_end="W", ev="A", ref=lc["ref"])
    # ---- cameras
    S.cam_auto(R, (x0 - 2.0, x1 + 2.0, y0, y1, Z(3160), zt + 6.0), ref="master B1", views=("oblique", "back"))
    for key, hd in (("Section", ("FRONT", "BACKDROP", "CAVESHELL")), ("Closed", ("BACKDROP", "CAVESHELL"))):
        S.cam_front(f"Elev{key}", R, (6230, 1576, 6560, 2380), y=y0 - 3.0, hide=hd, ref="master B1",
                    purpose="upper half of the tower, comparable with master B1 (section)" if key == "Section" else "upper half of the tower with its viewer-side wall")
        S.cam_front(f"Elev{key}Low", R, (6230, 2360, 6560, 3160), y=y0 - 3.0, hide=hd, ref="master B1",
                    purpose="lower half of the tower and the glass columns under it")
    S.camera("REF_Upper", R, (cx, -19.0, Z(2472) - 1.0), look=(cx, y1, Z(2472) - 1.0), lens=30.0, kind="ref", hide=("FRONT", "CAVESHELL", "BACKDROP"),
             purpose="relief, staging and panels, compare Right_City_elevator_upper.jpg", ref=REF)
    S.camera("ShaftUp", R, (cx, y0 + 0.9, Z(2626) - 1.0), look=(cx, y1, Z(2344) - 1.0), lens=20.0, kind="interior", purpose="up the shaft: panels, relief and bound columns")
    S.camera("Car", R, (cx - 4.0, y0 + 1.2, zb + 2.2), look=(cx + 0.6, 1.0, zb + 2.0), lens=18.0, kind="interior", purpose="domed car, compare Right_City_elevator.jpg", ref=REF)


# ============================================================================ EastPeakHall
def east_peak_hall(S):
    R = "EastPeakHall"
    REF = "06_Right_City/Right_City_peak.jpg; master C5"
    e = dict(S.el(R, "Hall"), voids=[[6740, 6764, 2600, 2650]])        # floor opening over the stack's right lift (B)
    st = dict(P.STYLES["purple"], partition=0, inner=False, bay=4.25, back=("shelf", "drape", "shelf", "drape"), lamp=None)
    hi = P.stack(S, R, e, st, roof=False, door_y={"L": 0.0}, ext_faces=("R", "N"), furnish=False)        # the hall has its own settees, stools and drapes
    x0, x1, yf, yb, zf, zt = hi["x0"], hi["x1"], hi["yf"], hi["yb"], hi["floors"][0], hi["zt"]
    de = S.el(R, "Dome")
    dx0, dx1 = X(de["map"][0]), X(de["map"][2])
    dcx, dcy, rx, ry = (dx0 + dx1) / 2, de["yc"], (dx1 - dx0) / 2, de["ry"]
    dome_h = Z(de["map"][1]) - zt
    # ---- roof slab with an oval opening under the dome (A)
    g = Geo().use("floor")
    for xa, xb, ya, yc in ((x0 - 0.3, dx0, yf - 0.45, yb + 0.3), (dx1, x1 + 0.3, yf - 0.45, yb + 0.3), (dx0, dx1, yf - 0.45, dcy - ry), (dx0, dx1, dcy + ry, yb + 0.3)):
        g.box(xa, xb, ya, yc, zt, zt + 0.5)
    rows = []
    for i in range(49):
        a = TAU * i / 48
        c, s = math.cos(a), math.sin(a)
        f = 1.0 / max(abs(c), abs(s))
        ix, iy = dcx + rx * 0.97 * c, dcy + ry * 0.97 * s
        ox, oy = dcx + rx * c * f, dcy + ry * s * f
        rows.append([(ix, iy, zt + 0.5), (ox, oy, zt + 0.5), (ox, oy, zt), (ix, iy, zt)])
    g.grid(rows, close_u=True)
    g.use("trim_purple")
    g.tube([(dcx + rx * 0.97 * math.cos(TAU * i / 48), dcy + ry * 0.97 * math.sin(TAU * i / 48), zt) for i in range(49)], 0.16, segs=6, ref=(0, 0, 1))
    S.add(g, "Roof", R, "HallRoof", "A", REF, note="oval opening under the dome; its depth is completion")
    g = Geo()
    K.louvre_dome(g, rx, ry, dome_h, ribs=14, m=place(dcx, dcy, zt + 0.5), slat=0.26, cap_base=False)
    g.use("iron")
    g.spike((dcx, dcy, zt + 0.5 + dome_h), (dcx, dcy, zt + 0.5 + dome_h + 4.6), 0.2, segs=8, bulb=1.2)
    S.add(g, "Dome", R, "HallDome", "A", de["ref"], note="depth of the dome is completion", smooth=35)
    g = Geo().use("wall_purple")                               # pale lining of the dome seen from the hall (C)
    rows = []
    for k in range(10):
        phi = math.pi / 2 * min(k / 9, 0.97)
        rows.append([(dcx + rx * 0.93 * math.cos(phi) * math.cos(TAU * i / 40), dcy + ry * 0.93 * math.cos(phi) * math.sin(TAU * i / 40), zt + 0.5 + dome_h * 0.92 * math.sin(phi))
                     for i in range(40)])
    g.grid(rows, close_u=True, cap_start=False, cap_end=True)
    S.add(g, "DomeLining", R, "HallDome", "C", REF, note="inner face of the dome as seen from the hall; the lining itself is completion")
    g = Geo().use("trim_purple")                               # ribs and tracery seen inside the dome
    for k in range(14):
        a = TAU * k / 14
        g.tube([(dcx + rx * 0.9 * math.cos(math.pi / 2 * i / 8) * math.cos(a), dcy + ry * 0.9 * math.cos(math.pi / 2 * i / 8) * math.sin(a), zt + 0.5 + dome_h * 0.89 * math.sin(math.pi / 2 * i / 8))
                for i in range(9)], 0.09, segs=5, ref=(0, 0, 1))
    S.add(g, "DomeRibs", R, "HallDome", "A", REF)
    for eid, end in (("RoofL", "W"), ("RoofR", "E")):
        c = S.el(R, eid)
        P.louvre_roof(S, R, eid, X(c["map"][0]) - (0.3 if end == "W" else 0.0), X(c["map"][2]) + (0.3 if end == "E" else 0.0), zt + 0.5, Z(c["map"][1]) + 0.5, c["y"][0], c["y"][1],
                      bays=3, curve_end=end, ev="A", ref=c["ref"])
    g = Geo().use("iron")
    g.spike((x1 - 0.6, yf + 1.0, zt + 2.4), (x1 - 0.6, yf + 1.0, zt + 9.0), 0.3, segs=8, bulb=0.0)
    S.add(g, "EastSpire", R, "RoofSpire", "A", REF)
    # ---- drapes, lamp strings, settees, stools, cobbled floor edge (A)
    g = Geo()
    for k, dx in enumerate((dx0 - 0.4, dx0 + 3.2, dx1 - 3.2, dx1 + 0.4)):
        K.drape(g, dx - 1.5, dx + 1.5, yb - 3.2, zt - 0.1, zf + 0.25, folds=6, amp=0.2, key="cloth_purple", gather=(zf + 2.6, 0.42), seed=k)
    for k, (xa, xb) in enumerate(((x0 + 1.0, dx0 - 1.0), (dx1 + 1.0, x1 - 1.0))):
        K.drape(g, xa, xa + 2.4, yb - 4.4, zt - 0.1, zf + 0.25, folds=5, amp=0.2, key="cloth_purple", gather=(zf + 2.4, 0.4), seed=10 + k)
        K.drape(g, xb - 2.4, xb, yb - 4.4, zt - 0.1, zf + 0.25, folds=5, amp=0.2, key="cloth_purple", gather=(zf + 2.4, 0.4), seed=20 + k)
    for k in range(6):
        xa = lerp(dx0, dx1, k / 6)
        K.swag(g, xa, xa + (dx1 - dx0) / 6, yb - 3.6, zt - 0.2, sag=0.8, depth=0.7, key="cloth_purple")
    S.add(g, "Drapes", R, "Drapes", "A", REF, smooth=60)
    string = S.kit("lampstring_pink_3", lambda: K.k_lamp_string(3, 2.4, "lamp_pink"))
    drop = S.kit("lampstring_pink_1", lambda: K.k_lamp_string(1, 1.8, "lamp_pink"))
    for k, (lx, ly, dz) in enumerate(((dcx - 6.0, 2.0, 0.0), (dcx - 2.4, 7.0, 0.6), (dcx + 2.0, 1.0, 0.2), (dcx + 6.0, 6.0, 0.4), (x0 + 5.0, 3.0, 0.0), (x1 - 5.0, 3.0, 0.0))):
        S.put(string if k % 2 == 0 else drop, f"LampString_{k}", R, "LampString", place(lx, ly, zt - dz), "A", REF)
    sofa = S.kit("sofa", lambda: k_sofa())
    for k, sx_ in enumerate((dcx - 5.6, dcx + 5.6, x0 + 6.0, x1 - 6.0)):
        S.put(sofa, f"Sofa_{k}", R, "Settee", place(sx_, yb - 5.6, zf), "A", REF)
    seat = S.kit("seat", lambda: K.k_seat())
    for k in range(7):
        S.put(seat, f"Stool_{k}", R, "Seat", place(dcx - 4.0 + 1.35 * k, yb - 7.4 + 0.5 * (k % 2), zf, s=0.8), "A", REF)
    for k, (sx_, sy_, rz) in enumerate(((dcx - 7.0, 3.0, 0.5), (dcx + 7.0, 2.0, -0.5), (x0 + 4.0, -3.0, 1.2), (x1 - 4.0, -3.0, -1.2))):
        S.put(sofa, f"SofaMid_{k}", R, "Settee", place(sx_, sy_, zf, rz=rz), "C", REF, note="furniture across the depth of the hall: completion")
    cst = S.kit("candle_stand", lambda: K.k_candle_stand(3, 1.7))
    for k in range(8):
        S.put(cst if k % 2 else seat, f"MidProp_{k}", R, "CandleStand" if k % 2 else "Seat", place(dcx - 9.0 + 2.6 * k, -2.0 + 3.4 * (k % 3), zf, rz=k), "C", REF,
              note="furniture across the depth of the hall: completion")
    g = Geo()
    A.add_cobbles(g, x0 + 0.6, x1 - 0.6, yf - 0.2, yf + 1.3, zf, size=(0.62, 0.5), seed=31, key="cushion", height=0.18)
    S.add(g, "FloorEdge", R, "PinkCobbleEdge", "A", REF, smooth=35)
    g = Geo()
    lx0, lx1 = X(6740), X(6764)
    K.spike_rail(g, (lx0 - 0.2, -2.4), (lx1 + 0.2, -2.4), zf)
    K.spike_rail(g, (lx0 - 0.2, 2.4), (lx1 + 0.2, 2.4), zf)
    K.spike_rail(g, (lx1 + 0.2, -2.4), (lx1 + 0.2, 2.4), zf)
    S.add(g, "LiftOpening_Rail", R, "SpikeRail", "C", "rail round the lift opening in the hall floor: completion")
    g = Geo()
    K.slab(g, x0 - 2.0, x0 + 0.2, -2.2, 2.2, zf, 0.5, "floor", lip=("front", "back"), trim="trim_purple")
    S.add(g, "WestLink", R, "HallLink", "B", "master C5: hall floor continues to the tower; the opening is not shown")
    # ---- cave roof over the hall, the east rock, spires behind (A)
    cc = S.el(R, "CaveCeiling")
    cz0 = Z(cc["map"][3])
    P.rock(S, R, "CaveCeiling", X(cc["map"][0]), X(cc["map"][2]), cc["y"][0], cc["y"][1], cz0, Z(cc["map"][1]), ev="A", ref=cc["ref"], layer="CEILING", amp=1.8, cell=4.0)
    g = Geo()
    K.stalactite_field(g, X(cc["map"][0]) + 1.0, X(cc["map"][2]) - 1.0, -8.0, 40.0, lambda x, y: cz0 + 0.4, 90, seed=12, lmin=1.2, lmax=5.0)
    SH.hanging_fringe(g, X(cc["map"][0]) + 0.5, X(cc["map"][2]) - 0.5, cc["y"][0] + 0.5, cz0 + 0.3, 3.0, seed=6)
    S.add(g, "CaveCeiling_Stalactites", R, "Stalactites", "A", cc["ref"], layer="CEILING", smooth=50)
    er = S.el(R, "EastRock")
    P.rock(S, R, "EastRock", X(er["map"][0]), X(er["map"][2]), er["y"][0], er["y"][1], Z(er["map"][3]), Z(er["map"][1]), ev="A", ref=er["ref"], layer="ROCK", amp=1.2)
    for eid in ("SpireA", "SpireB"):
        sp = S.el(R, eid)
        scx, r = (X(sp["map"][0]) + X(sp["map"][2])) / 2, (X(sp["map"][2]) - X(sp["map"][0])) / 2
        z0, z1 = Z(sp["map"][3]), Z(sp["map"][1])
        g = Geo().use("tower_far")
        g.revolve([(r * 1.6, zt), (r * 1.4, z0), (r * 1.0, z0 + (z1 - z0) * 0.3), (r * 0.45, z0 + (z1 - z0) * 0.7), (0.05, z1)], segs=12, m=place(scx, sp["yc"] + 6.0, 0))
        S.add(g, eid, R, "DistantSpire", sp["ev"], sp["ref"], layer="BACKDROP", note="depth is completion")
    # ---- cameras
    for k, (kind, cx_, cy_) in enumerate((("resident_0", dcx - 2.0, -5.2), ("resident_2", dcx + 3.0, -6.0), ("resident_1", x0 + 8.0, -6.2), ("husk_sentry", x1 - 8.0, -5.0),
                                          ("resident_0", dcx + 9.5, -5.5))):
        P.creature(S, R, kind, f"Hall_{k}", cx_, cy_, zf + 0.01, rz=0.5 * (k - 2))
    S.cam_auto(R, (x0 - 2.0, x1 + 2.0, yf, yb, zf - 2.0, cz0 + 2.0), ref="master C5", views=("front", "closed", "oblique", "back"))
    S.camera("REF_Peak", R, (dcx, yf - 14.0, zf + 2.6), look=(dcx, yb, zf + 3.2), lens=24.0, kind="ref", hide=("FRONT", "CAVESHELL", "BACKDROP"), purpose="hall under the dome, compare Right_City_peak.jpg", ref=REF)
    S.camera("Interior", R, (x0 + 2.0, yf + 2.0, zf + 1.7), look=(dcx + 4.0, yb - 3.0, zf + 3.4), lens=18.0, kind="interior", purpose="inside the hall towards the dome")
    S.camera("LiftOpening", R, (lx0 - 7.0, -5.0, zf + 2.4), look=(lx0 + 0.8, 0.0, zf - 0.6), lens=20.0, kind="interior", purpose="railed opening over the stack's right lift (connection to the purple stack)")
    S.camera("Roofs", R, (dcx - 16.0, yf - 16.0, zt + 9.0), look=(dcx, dcy, zt + 1.0), lens=26.0, kind="view", hide=("CAVESHELL", "CEILING"), purpose="dome, louvre roofs and spires from above")


# ============================================================================ EastStack
def east_stack(S):
    R = "EastStack"
    REF = "06_Right_City/Right_City_step1.jpg; step2.jpg; step3.jpg; master B1"
    e = dict(S.el(R, "Stack"))
    e["voids"] = [list(v) for v in e["voids"]]
    e["voids"][1][2] = 2630                                     # the right lift's void runs through the roof into the dome hall
    # floor lines read from the master (B1 enlarged, _work/stage03/grid/eaststack_grid.png): storeys of uneven height, and
    # black solid parts between the rooms (cells, bays of 64.5 map units from 6540) (D-362)
    e["floors"] = [2720, 2805, 2910, 2985, 3080, 3140, 3192]
    cells = [(0, 6669, 6733), (2, 6604, 6669), (4, 6669, 6733), (6, 6604, 6669)]
    st = dict(P.STYLES["purple"], back=("chevron", "web", "noble", "drape", "shelf"), furniture="tower")      # own set, not the plaza house's
    lv = {i: dict(back=(("web", "drape", "noble", "chevron", "shelf") if i % 2 else ("chevron", "shelf", "noble", "web", "drape")), lamp="round") for i in range(9)}
    info = P.stack(S, R, e, st, levels=lv, ext_faces=("L", "R", "N"), cells=cells)
    x0, x1, yf, yb = info["x0"], info["x1"], info["yf"], info["yb"]
    stops = tuple(info["floors"])
    LOW = 3328                                                  # the left lift stops on the roof of the quarter's centre (master B1: it does not enter the room)
    for eid in ("ShaftL", "ShaftR"):
        s = dict(S.el(R, eid))
        if eid == "ShaftR":
            s["map"] = [s["map"][0], 2634, s["map"][2], s["map"][3]]      # up to the hall floor
        else:
            s["map"] = [s["map"][0], s["map"][1], s["map"][2], LOW]
        P.lift(S, R, s, back="chevron", trim="trim_purple", closed=False, stops=stops, ref=s["ref"])
    sl = S.el(R, "ShaftL")
    sx0, sx1 = X(sl["map"][0]), X(sl["map"][2])
    g = Geo().use("wall_deep")                                  # the left shaft runs on down through the black mass to the quarter (A shaft, C casing)
    zc0, zc1 = Z(LOW), info["bottom"]
    for xa, xb, ya, yb_ in ((sx0 - 0.3, sx0, -2.5, 2.5), (sx1, sx1 + 0.3, -2.5, 2.5), (sx0 - 0.3, sx1 + 0.3, 2.2, 2.5), (sx0 - 0.3, sx1 + 0.3, -2.5, -2.2)):
        g.box(xa, xb, ya, yb_, zc0, zc1)
    S.add(g, "ShaftL_Casing", R, "ShaftCasing", "C", "enclosure of the lift shaft between the stack and the quarter")
    # black mass under the stack (A black on the master; fringed form is C)
    g = Geo().use("wall_deep")                                  # a plain black mass, as the master draws it (D-362)
    g.box(x0 + 2.6, x1, yf + 1.0, yb, Z(3336) + 0.5, info["bottom"])
    for zz in (info["bottom"] - 0.1, lerp(Z(3336), info["bottom"], 0.5)):
        SH.hanging_fringe(g, x0 + 2.8, x1 - 0.2, yf + 0.9, zz, 1.8, seed=int(zz * 3))
    S.add(g, "Podium", R, "SolidMass", "C", "black on master B1 between the stack and the quarter", note="support of the stack; its depth is completion")
    for eid in ("GlassL", "GlassR"):
        p = S.el(R, eid)
        px = x0 - 0.9 if eid == "GlassL" else x1 + 0.9
        P.glass_pillar(S, R, eid, px, yf + 1.6, p["r"] / 15.0 + 0.15, Z(p["map_y"][1]), Z(p["map_y"][0]), "A", p["ref"])
    bc = S.el(R, "BottomCanopy")
    P.louvre_roof(S, R, "BottomCanopy", X(bc["map"][0]), X(bc["map"][2]), Z(bc["map"][3]), Z(bc["map"][1]) + 1.2, bc["y"][0], bc["y"][1], bays=1, curve_end="E", ev="A", ref=bc["ref"])
    # furniture seen in the rooms (A)
    P.populate(S, R, "Stack", info, ["resident_0", "resident_1", "resident_2", "husk_sentry"], 8, seed=21)
    S.cam_auto(R, (x0 - 2.0, x1 + 2.0, yf, yb, Z(3336), info["zt"] + 1.0), ref="master B1", views=("front", "closed", "oblique", "back"))
    zr = info["floors"][3]
    S.camera("REF_Step2", R, ((x0 + x1) / 2 + 1.0, yf - 12.0, zr + 2.4), look=((x0 + x1) / 2 + 1.0, yb, zr + 2.4), lens=26.0, kind="ref", hide=("FRONT", "CAVESHELL", "BACKDROP"),
             purpose="rooms, shaft and glass column, compare Right_City_step2.jpg", ref=REF)
    S.camera("Interior", R, (x0 + 3.4, yf + 1.4, zr + 1.7), look=(x1 - 3.0, yb - 1.0, zr + 2.2), lens=18.0, kind="interior", purpose="one storey of the stack")


# ============================================================================ EastQuarter
def east_quarter(S):
    R = "EastQuarter"
    REF = "06_Right_City/Right_City_middle.jpg; master C2"
    st = dict(ext="stone_far", fringe=True, wall="stone_far", floor="stone", trim="stone_far_trim", front="round", bay=3.3, back=("blind", "noble", "lancet", "niche"),
              glass="glass_blue", lamp="string", partition=0, rail=True, inner=False, furniture="blue", side_portraits=True, ceiling="beams")
    ce = S.el(R, "Center")
    we, ea = S.el(R, "West"), dict(S.el(R, "East"))
    ea["doors"] = list(ea["doors"]) + [["R", 3636]]
    # black solid parts of the wings (master C2 / B1 enlarged; bays of about 45 and 42 map units) (D-362)
    wi = P.stack(S, R, we, st, side_open=("R",), ext_faces=("L", "N"), door_y={"L": 0.0}, cells=[(0, 6329, 6374), (2, 6465, 6511)])
    ei = P.stack(S, R, ea, st, side_open=("L",), ext_faces=("R", "N"), door_y={"R": 0.0}, cells=[(1, 6709, 6751), (3, 6625, 6667)])
    # the centre is an open rain court (A: Right_City_middle.jpg, master B1): only its top storey is a room; below it
    # stone balconies with iron lace hang across the front of the court, which stays open to the back (D-362)
    cfl = sorted(Z(f) for f in ce["floors"])                    # court ground, balconies, top room floor
    ce_top = dict(ce, map=[ce["map"][0], ce["map"][1], ce["map"][2], min(ce["floors"])], floors=[min(ce["floors"])])
    ci = P.stack(S, R, ce_top, dict(st, bay=3.1, back=("tall",), lamp=None, furniture=None, side_portraits=False), side_open=("L", "R"), ext_faces=("N",),
                 levels={0: dict(back=("tall",), glass="glass_blue")})
    ci = dict(ci, floors=cfl)
    cx0, cx1, cyf, cyb = ci["x0"] + 0.2, ci["x1"] - 0.2, ci["yf"], ci["yb"]
    g = Geo()
    K.slab(g, cx0, cx1, cyf, cyb, cfl[0], 0.6, "stone", lip=("front",), trim="stone_far_trim")          # court floor
    for zb in cfl[1:-1]:
        K.slab(g, cx0, cx1, cyf - 0.2, cyf + 3.4, zb, 0.45, "stone", lip=("front", "back"), trim="stone_far_trim")
        g.use("iron")
        for xx in (cx0 + 0.6, (cx0 + cx1) / 2, cx1 - 0.6):          # brackets under the balcony
            g.tube([(xx, cyf + 3.2, zb - 0.45), (xx, cyf + 0.8, zb - 2.2)], 0.07, segs=5)
            g.tube([(xx, cyf + 0.8, zb - 2.2), (xx, cyf + 0.4, zb - 0.45)], 0.06, segs=5)
    S.add(g, "CourtBalconies", R, "CourtBalconies", "A", REF, note="balconies across the open court; their depth is completion")
    for k, zb in enumerate(cfl[1:-1]):
        P.railing(S, R, f"CourtRailBack_{k}", (cx0, cyf + 3.35), (cx1, cyf + 3.35), zb, ev="A", ref=REF)
    g = Geo().use("iron")                                       # chains from the top room's floor down to the balcony corners
    for zb in cfl[1:-1]:
        for xx in (cx0 + 0.3, cx1 - 0.3):
            K.chain(g, xx, cyf + 3.2, zb + 0.05, cfl[-1] - 0.5)
    S.add(g, "CourtChains", R, "Chains", "C", REF)
    # the centre court is open to both wings (A: no wall between them on Right_City_middle.jpg). Floors of different
    # height meet at the boundary: boundary piers (A) and short flights between the levels (C)
    g = Geo()
    for side, info, xb in (("L", wi, ci["x0"]), ("R", ei, ci["x1"])):
        sgn = 1 if side == "L" else -1                            # +x points into the centre for the west boundary
        for k, yy in enumerate((ci["yf"] + 0.3, ci["yf"] + 3.4)):
            g.use("stone_far_trim")
            g.box(xb - 0.22, xb + 0.22, yy - 0.22, yy + 0.22, wi["bottom"], wi["zt"])
            for zz in sorted(set(ci["floors"] + info["floors"])):
                g.box(xb - 0.32, xb + 0.32, yy - 0.32, yy + 0.32, zz - 0.5, zz + 0.12)
        for j, zc in enumerate(ci["floors"]):
            zs = min(info["floors"], key=lambda v: abs(v - zc))
            dz = zs - zc
            if not 0.25 < abs(dz) < 3.0:
                continue
            run = abs(dz) * 1.25
            ya, yb_ = (cyf + 0.5, cyf + 3.0)
            inward = sgn if dz > 0 else -sgn                      # the flight lies on the lower floor's side
            x_far = xb + inward * run
            z_far, z_near = min(zc, zs), max(zc, zs)              # it climbs towards the boundary
            if x_far < xb:
                P.stairs(g, x_far, xb, ya, yb_, z_far, z_near, step=0.4, key="stone")
            else:
                P.stairs(g, xb, x_far, ya, yb_, z_near, z_far, step=0.4, key="stone")
    S.add(g, "BoundaryAndSteps", R, "LevelSteps", "C", "the centre and wing floors differ in height on the master; boundary piers observed, the short flights are completion")
    # rune tablets hanging in the open centre and under the side ceilings, jars on the floors (A)
    tab = [S.kit(f"rune_{v}", lambda v=v: SH.k_rune_tablet(0.75, 2.2 + 0.3 * v, v)) for v in range(3)]
    n = 0
    for info in (wi, ei):
        for i, zf, top in info["storeys"]:
            if top - zf < 3.2:
                continue
            for k, bxc in enumerate(info["bay_x"]):
                if any(a - 0.2 < bxc < b + 0.2 for a, b in info["cells"].get(i, ())):
                    continue
                S.put(tab[n % 3], f"Tablet_{n:03d}", R, "RuneTablet", place(bxc, info["yb"] - 1.6 - 1.2 * (k % 2), top - 0.2), "A", REF)
                n += 1
    g = Geo().use("iron")                                       # clusters of tablets of different drops in the open court (A: Right_City_middle.jpg)
    rand = rng(64)
    for c, (fx, fy) in enumerate(((0.3, 0.45), (0.7, 0.6), (0.5, 0.82))):
        for j in range(4 + c % 2):
            px = lerp(cx0 + 0.8, cx1 - 0.8, fx) + rand(-0.6, 0.6)
            py = lerp(cyf + 4.0, cyb - 1.0, fy) + rand(-0.8, 0.8)
            drop = rand(0.5, 3.6)
            zt_ = cfl[-1] - 0.6 - drop
            K.chain(g, px, py, zt_, cfl[-1] - 0.5)
            S.put(tab[(c + j) % 3], f"Tablet_{n:03d}", R, "RuneTablet", place(px, py, zt_, rz=rand(-0.5, 0.5)), "A", REF)
            n += 1
    S.add(g, "TabletChains", R, "Chains", "C", REF)
    jars = []
    for info in (wi, ei):
        for i, zf, top in info["storeys"]:
            for k in range(5):
                jx = info["x0"] + 1.6 + 0.95 * k + 1.4 * (i % 2)
                if any(a - 0.5 < jx < b + 0.5 for a, b in info["cells"].get(i, ())):
                    continue
                jars.append((jx, info["yb"] - 2.0 - 0.5 * (k % 2), zf))
    hive_jars(S, R, "Jars", jars, REF)
    lace = [((cx0 + 0.3, cyf - 0.05), (cx1 - 0.3, cyf - 0.05), zb) for zb in cfl[1:-1]]
    for k, (p0, p1, zz) in enumerate(lace):
        P.railing(S, R, f"LaceRail_{k}", p0, p1, zz, ev="A", ref=REF, layer="FRONT")
    S.put(S.kit("signlamp_w", lambda: sign_lamp()), "SignLamp", R, "SignLamp", place(ei["x0"] + 2.0, ei["yf"] + 2.0, ei["floors"][2]), "A", REF)
    back = lambda info: [(i, info["x0"], info["x1"], info["yb"] - 3.4, info["yb"]) for i, zf, top in info["storeys"]]     # jars and tablets stand at the back
    P.populate(S, R, "West", wi, ["resident_0", "resident_1", "husk_sentry"], 3, seed=22, avoid=back(wi))
    P.populate(S, R, "East", ei, ["resident_2", "resident_1", "husk_sentry_low"], 3, seed=23, avoid=back(ei))
    P.populate(S, R, "Centre", ci, ["resident_0"], 1, seed=24)
    S.cam_auto(R, (wi["x0"], ei["x1"], -9.0, 17.0, wi["zb"] - 1.0, wi["zt"] + 2.0), ref="master C2", views=("front", "closed", "oblique", "back"))
    S.cam_front("GroundSection", R, (6280, 3300, 7060, 3660), y=-10.0, ref="master C2_east_ground_mid", purpose="quarter and station, same frame as master C2")
    zr = ci["floors"][2]
    S.camera("REF_Middle", R, ((ci["x0"] + ci["x1"]) / 2, -22.0, zr + 1.0), look=((ci["x0"] + ci["x1"]) / 2, 10.0, zr + 1.0), lens=30.0, kind="ref", hide=("FRONT", "CAVESHELL", "BACKDROP"),
             purpose="centre balconies and side rooms, compare Right_City_middle.jpg", ref=REF)
    S.camera("Interior", R, (wi["x0"] + 1.6, wi["yf"] + 1.4, wi["floors"][1] + 1.7), look=(ci["x1"], wi["yb"] - 2.0, wi["floors"][1] + 2.0), lens=18.0, kind="interior", purpose="west rooms towards the centre")


# ============================================================================ EastStation
def east_station(S):
    R = "EastStation"
    REF = "06_Right_City/Right_City_station.jpg; master C2"
    e = S.el(R, "Hall")
    st = dict(P.STYLES["street"], bay=3.8, fringe=True)
    info = P.stack(S, R, e, st, decor=False, lamps=False, ext_faces=("N",), door_y={"L": 0.0, "R": 0.0})
    x0, x1, yf, yb, zf, zt = info["x0"], info["x1"], info["yf"], info["yb"], info["floors"][0], info["zt"]
    # back wall bays: round arches with chevron doors, tablets, hanging lamps (A)
    tab = [S.kit(f"rune_{v}", lambda v=v: SH.k_rune_tablet(0.75, 2.2 + 0.3 * v, v)) for v in range(3)]
    for k, cx in enumerate(info["bay_x"]):
        g = Geo().use("stone_far_trim")
        w = info["bw"] - 1.0
        kind, rise, spring = P.fit_arch("round", w, zt - zf, 0.4, 1.4)
        K.arch_trim(g, cx, w, zf + spring, zf, kind, rise, y=yb - 0.7, r=0.14)
        if k % 2 == 0:
            K.chevron_panel(g, cx - w / 2 + 0.3, cx + w / 2 - 0.3, yb - 0.62, zf, zf + spring, pitch=0.6, key="stone_far_trim")
        S.add(g, f"Niche_{k}", R, "StationNiche", "A", REF)
        for j, dx in enumerate((-0.6, 0.6)):
            if (k + j) % 3:
                S.put(tab[(k + j) % 3], f"Tablet_{k}_{j}", R, "RuneTablet", place(cx + dx, yb - 0.9, zt - 0.3), "A", REF)
    drop = S.kit("lampdrop_1.2", lambda: K.k_lamp_string(1, 1.2))
    for k, cx in enumerate(info["bay_x"][::2]):
        S.put(drop, f"Lamp_{k}", R, "LampString", place(cx + 1.0, 2.0, zt), "A", REF)
    S.put(S.kit("bench", lambda: K.k_bench()), "Bench", R, "Bench", place(x0 + 5.0, 4.0, zf), "A", REF)
    S.put(S.kit("bell", lambda: K.k_bell()), "Bell", R, "StationBell", place(x1 - 4.2, 3.0, zf), "A", REF)
    S.put(S.kit("signlamp_w", lambda: sign_lamp()), "SignLamp", R, "SignLamp", place(x1 - 1.6, 4.6, zf), "A", REF)
    rf = S.el(R, "Roof")
    P.louvre_roof(S, R, "Roof", x0 - 0.3, X(rf["map"][2]) + 2.0, zt + 0.5, Z(rf["map"][1]) + 0.5, rf["y"][0], rf["y"][1], bays=4, curve_end="E", ev="A", ref=rf["ref"])
    # ---- east porch with the tunnel portal (A portal; the line beyond is not built)
    ta = S.el(R, "TunnelArch")
    tx0, tx1 = X(ta["map"][0]), X(ta["map"][2]) + 2.6
    g = Geo()
    K.slab(g, tx0, tx1, yf, -0.2, zf - 0.6, 0.5, "stone", lip=("front",), trim="stone_far_trim")
    P.stairs(g, tx0, tx0 + 1.6, -2.0, 2.0, zf, zf - 0.6, step=0.2, key="stone")
    g.use("stone_far")
    g.box(tx0, tx1, -0.8, -0.2, zf - 0.6, zt + 2.0)
    g.box(tx1 - 0.5, tx1, yf, -0.8, zf - 0.6, zt + 2.0)
    S.add(g, "Porch", R, "StationPorch", "A", REF, note="porch floor and steps observed; walls behind the portal are completion")
    g = Geo()
    SH.tunnel_arch(g, tx1 - tx0 - 1.4, zt - zf + 2.0, depth=9.0, m=place((tx0 + tx1) / 2 - 0.2, -1.4, zf - 0.6))
    hw_ = (tx1 - tx0 - 1.4) / 2 * 0.79 - 0.1                    # a deep tunnel with a flight of steps up into it (A: Right_City_station.jpg; D-365)
    g.use("stone")
    for q in range(4):                                          # steps rise along +Y into the tunnel
        g.box((tx0 + tx1) / 2 - 0.2 - hw_, (tx0 + tx1) / 2 - 0.2 + hw_, 1.0 + 0.9 * q, 9.0 - 1.4, zf - 0.6, zf - 0.6 + 0.3 * (q + 1))
    S.add(g, "TunnelArch", R, "StationPortal", "A", REF, note="portal at the foot of the rain-gap tower with steps up into a deep tunnel; the line beyond 9 m is not built", smooth=40)
    pl = S.el(R, "Plinth")
    P.host(S, R, "Plinth", (X(pl["map"][0]), tx0, yf, yb, Z(pl["map"][3]), zf - 0.5), ("front", "back"), ev="C", ref=pl["ref"], layer=None, a=0.4)
    P.host(S, R, "PorchPlinth", (tx0, tx1, yf, -0.2, Z(pl["map"][3]), zf - 1.1), ("front",), ev="C", ref=pl["ref"], layer=None, a=0.4,
           note="under the porch only: the rain-gap tower stands behind it")
    for k, (kind, cx_, cy_) in enumerate((("resident_0", x0 + 8.0, 0.5), ("resident_2", x0 + 11.0, 1.5), ("husk_sentry", x1 - 6.0, 0.0))):
        P.creature(S, R, kind, f"Waiting_{k}", cx_, cy_, zf + 0.01, rz=0.4 * (k - 1))
    S.cam_auto(R, (x0, tx1, yf, yb, Z(pl["map"][3]), zt + 5.0), ref="master C2", views=("front", "closed", "oblique", "back"))
    S.camera("REF_Station", R, ((x0 + tx1) / 2 + 1.0, yf - 16.0, zf + 3.4), look=((x0 + tx1) / 2 + 1.0, yb, zf + 3.6), lens=24.0, kind="ref", hide=("FRONT", "CAVESHELL", "BACKDROP"),
             purpose="station hall, roof and portal, compare Right_City_station.jpg", ref=REF)
    S.camera("Interior", R, (x0 + 1.5, yf + 1.4, zf + 1.7), look=(x1 - 2.0, yb - 1.0, zf + 2.0), lens=18.0, kind="interior", purpose="station hall")


# ============================================================================ EastRainGap
def east_rain_gap(S):
    R = "EastRainGap"
    tz_base = Z(S.el(R, "Tower")["map"][3])
    tcx, tr, tyc, try_, tz0, tz1 = layout_tower(S, R, "Tower", 81, z0=tz_base + 0.7 + FRINGE_HANG, leaf=(2.6, 6.6), tier=7.5, dx=1.0, r_scale=0.92, seat=tz_base + 0.6,
                                                 note="lowest fringe kept above the undercroft roof")
    tower_foot(S, R, "Tower_Foot", tcx, tyc, tr, try_, tz_base + 0.5, tz_base + 0.8 + FRINGE_HANG, "plain foot of the tower on the undercroft roof")
    # long sloping roof rising from the tower top to the jar house wall, spears along its edges (A: master C4 enlarged)
    br = S.el(R, "BigRoof")
    rx0, rx1 = X(6936), X(7190)                                 # from west of the tower (map 6936) to the jar house's west wall
    ry0, ry1 = br["y"][0] - 1.0, br["y"][1]
    # upper edge read on the master (map 6940 / 3077 to 7172 / 3010): it rises faster towards the east end (upswept) (D-362)
    top = lambda x: lerp(Z(3078), Z(3008), ((x - rx0) / (rx1 - rx0)) ** 1.35)
    g = Geo().use("louvre_core")
    n = 24
    upper = [(lerp(rx0, rx1, i / n), top(lerp(rx0, rx1, i / n))) for i in range(n + 1)]
    lower = [(x, z - lerp(3.2, 2.2, i / n)) for i, (x, z) in enumerate(upper)]     # a thick roof, 3.2 m at the low end
    g.prism(upper + lower[::-1], ry0, ry1)
    g.use("louvre")                                              # slats on the front face of the thick edge
    for k in range(5):
        f = (k + 0.5) / 5
        g.tube([(x, ry0 - 0.05, lerp(z, zl, f)) for (x, z), (_, zl) in zip(upper[::2], lower[::2])], 0.06, segs=4, ref=(0, 1, 0))
    g.use("louvre")                                              # slats laid along the slope
    for k in range(12):
        yy = lerp(ry0 + 0.4, ry1 - 0.4, k / 11)
        g.tube([(x, yy, z + 0.06) for x, z in upper[::2]], 0.07, segs=4, ref=(0, 1, 0))
    g.use("louvre_frame")
    for yy in (ry0 - 0.05, ry1 + 0.05):
        g.tube([(x, yy, z + 0.02) for x, z in upper], 0.12, segs=5, ref=(0, 1, 0))
    g.use("iron")
    for i in range(int((rx1 - rx0) / 1.25) + 1):
        x = rx0 + 0.4 + 1.25 * i
        if x > rx1 - 0.3:
            break
        for yy in (ry0, ry1):
            g.spike((x, yy, top(x)), (x, yy, top(x) + 1.8), 0.1, segs=6, bulb=1.0)
    A.add_corbel_wing(g, place(rx0 + 0.2, ry0 + 0.6, top(rx0) - 1.6, rz=math.pi), length=1.8, blades=5, key="louvre_frame")
    S.add(g, "BigRoof", R, "BigRoof", "A", br["ref"], note="long sloping spiked roof resting on the tower top and the jar house wall; its depth is completion", smooth=30)
    sc = S.el(R, "SmallCanopy")
    P.louvre_roof(S, R, "SmallCanopy", X(sc["map"][0]), X(sc["map"][2]), Z(sc["map"][3]), Z(sc["map"][1]), sc["y"][0] - 1.5, sc["y"][1] + 0.5, bays=2, curve_end="W", ev="A", ref=sc["ref"])
    g = Geo().use("louvre_frame")
    for px in (X(sc["map"][0]) + 0.6, X(sc["map"][2]) - 0.4):
        g.box(px - 0.16, px + 0.16, sc["y"][0] - 1.3, sc["y"][0] - 0.9, tz0, Z(sc["map"][3]))
    S.add(g, "SmallCanopy_Posts", R, "CanopyPosts", "C", sc["ref"], note="supports of the small canopy: completion")
    backdrop_towers(S, R, ("BackTower", "BackTowerB"), 82)
    P.creature(S, R, "winged_sentry", "UnderRoof", lerp(rx0, rx1, 0.3), -9.0, top(lerp(rx0, rx1, 0.3)) - 6.0, rz=-1.2)     # in front of the tower and canopy
    S.cam_auto(R, (X(6830), X(7230), -6.0, 18.0, tz0 - 1.0, Z(2960)), ref="master C4", views=("front", "oblique", "back"), hide=("ROCK", "CEILING", "CAVESHELL"))


# ============================================================================ EastJarHouse
def east_jar_house(S):
    R = "EastJarHouse"
    REF = "master C4 (no local screenshot)"
    st = dict(P.STYLES["jar"], partition=0, inner=False)
    bowls = [S.kit(f"bowl_{v}", lambda v=v: k_bowl(v)) for v in range(3)]
    urn = S.kit("urn", lambda: k_urn())
    infos = {}
    # read from the master (C4 enlarged, 50-unit grid): the middle block has a narrower top storey (rooms map x 7250-7460,
    # black at both ends) and a black band over its lowest room (map y 3062-3105); the base has a narrower upper row
    # (map x ~7265-7485) over three rooms (map x 7240-7320, 7330-7440, 7445-7510)
    elems = {"CageRoom": S.el(R, "CageRoom"), "Top": S.el(R, "Top"),
             "Mid": dict(S.el(R, "Mid"), floors=[2918, 2984, 3062, 3105, 3161]),
             "Base": dict(S.el(R, "Base"), map=[7241, 3420 + 7.5, 7511, 3518], floors=[3514]),
             "BaseUpper": dict(S.el(R, "Base"), id="BaseUpper", map=[7290, 3374, 7462, 3420], floors=[3420])}
    extra = {"Mid": dict(cells=[(4, 7190, 7253), (4, 7469, 7532), (3, 7190, 7300), (3, 7460, 7532), (2, 7190, 7244), (0, 7190, 7244)]),   # widths differ (D-380)
             "Base": dict(roof=False)}
    for eid in ("CageRoom", "Top", "Mid", "Base", "BaseUpper"):
        lv = None
        if eid != "CageRoom":
            lv = {i: dict(back=(("jars", "quilt", "quilt", "niche") if i % 2 else ("quilt", "niche", "jars", "quilt"))) for i in range(1, 6)}
        if eid == "Mid":
            lv[1] = dict(solid=True)
        stl = dict(st, bay=3.6 if eid != "CageRoom" else 2.6, back=("quilt", "jars", "niche", "quilt", "jars") if eid != "CageRoom" else ("quilt",))
        if eid == "Base":
            stl.update(partition=2, front="pointed")              # three rooms under pointed arches (A: master C4)
        if eid == "BaseUpper":
            stl.update(front="pointed", bay=3.3)
        infos[eid] = P.stack(S, R, elems[eid], stl, levels=lv, ext_faces=("L", "R", "N"), **extra.get(eid, {}))
    # the base is a hall with three pointed arch niches, the middle one tallest (A: master C4; D-380)
    bi_ = infos["Base"]
    g = Geo()
    i0, zf0, top0 = bi_["storeys"][0]
    w3 = (bi_["x1"] - bi_["x0"]) / 3
    for k in range(3):
        cx = bi_["x0"] + w3 * (k + 0.5)
        w = w3 - (1.4 if k != 1 else 0.9)
        spring = zf0 + (top0 - zf0) * (0.42 if k != 1 else 0.5)
        rise = (top0 - zf0) * (0.3 if k != 1 else 0.4)
        pts = [(cx + w / 2, zf0 + 0.02)] + [(cx + px, spring + pz) for px, pz in K.arch_profile(w, "pointed", rise)] + [(cx - w / 2, zf0 + 0.02)]
        g.use("mass_black")
        g.prism(pts, bi_["yb"] - 1.0, bi_["yb"] - 0.9)          # in front of the jar shelves on the back wall
        g.use("trim_purple")
        K.arch_trim(g, cx, w + 0.3, spring, zf0, "pointed", rise=rise + 0.15, y=bi_["yb"] - 1.06, r=0.13)
    S.add(g, "BaseArches", R, "ArchNiche", "A", REF, note="three pointed niches on the base hall's back wall; their depth is completion")
    # thick black floor bands under the upper jar-room floors (A: master C4 draws the floors as broad black bands)
    g = Geo().use("wall_deep")
    for eid in ("Mid", "Top"):
        inf = infos[eid]
        for i, zf, top in inf["storeys"][1:] if eid == "Mid" else inf["storeys"]:
            zb_ = zf - 0.5
            g.box(inf["x0"] + 0.6, inf["x1"] - 0.6, inf["yf"] + 0.4, inf["yb"] - 0.6, zb_ - 0.9, zb_)
            SH.hanging_fringe(g, inf["x0"] + 0.7, inf["x1"] - 0.7, inf["yf"] + 0.35, zb_ - 0.85, 0.7, seed=int(zf * 7))
            g.use("wall_deep")
    S.add(g, "FloorBands", R, "SolidMass", "A", REF, note="black bands under the floors as on the master; their depth is completion")
    n = 0
    lamps = []
    for eid in ("Top", "Mid", "Base"):
        info = infos[eid]
        for i, zf, top in info["storeys"]:
            if top - zf < 2.4:
                continue
            for k, bxc in enumerate(info["bay_x"]):
                if 241.4 < bxc < 244.8 and eid != "Top":
                    continue
                if any(a - 0.2 < bxc < b + 0.2 for a, b in info["cells"].get(i, ())):
                    continue                                 # black cell: no room there
                if (k + i) % 4 == 3:
                    S.put(urn, f"Urn_{n:03d}", R, "Urn", place(bxc, 3.0 + 1.5 * (k % 2), zf), "A", REF)
                else:
                    S.put(bowls[n % 3], f"Bowl_{n:03d}", R, "SpecimenBowl", place(bxc + 0.5 * ((n % 3) - 1), 4.0 + 2.0 * (k % 2), zf, rz=n), "A", REF)
                n += 1
                if k % 3 == i % 3:
                    lamps.append((bxc - 1.2, info["yb"] - 0.7, zf + min(top - zf - 0.5, 3.0)))
    hook_lamps(S, R, "HookLamp", lamps, REF)
    # the wire emblem of the cage room (A outline only; form is completion)
    ci = infos["CageRoom"]
    ccx, ccz = (ci["x0"] + ci["x1"]) / 2, ci["floors"][0] + 2.0
    g = Geo().use("trim_purple")
    for k in range(6):
        g.ring_arc((ccx, 3.0, ccz), 1.25, 0, TAU, 0.03, n=20, plane="XZ", segs=4, m=place(ccx, 3.0, ccz, rz=math.pi * k / 6) @ place(-ccx, -3.0, -ccz))
    g.ring_arc((ccx, 3.0, ccz), 1.25, 0, TAU, 0.04, n=20, plane="XY", segs=4)
    g.use("lamp")
    for k in range(5):
        a = TAU * k / 5
        g.ellipsoid((ccx + 0.7 * math.cos(a), 3.0 + 0.5 * math.sin(a * 2), ccz + 0.7 * math.sin(a)), (0.1, 0.1, 0.1), segs=8, steps=5)
    S.add(g, "CageEmblem", R, "CageEmblem", "B", REF, note="round wire emblem with lights read from the master; its construction is completion")
    # neck, quilted shaft, stub (A outline; quilting from the purple pads on the master)
    nk = S.el(R, "Neck")
    g = Geo().use("wall_deep")                               # black on the master
    g.box(X(nk["map"][0]), X(nk["map"][2]), nk["y"][0], nk["y"][1], Z(nk["map"][3]), Z(nk["map"][1]))
    SH.hanging_fringe(g, X(nk["map"][0]) + 0.3, X(nk["map"][2]) - 0.3, nk["y"][0] - 0.1, Z(nk["map"][3]) + 0.2, 1.2, seed=5)
    S.add(g, "Neck", R, "Neck", "C", nk["ref"])
    for eid in ("Shaft", "Stub"):
        s = S.el(R, eid)
        li = P.lift(S, R, s, back="plain", car=None, closed=True, trim="trim_purple", ref=s["ref"])
        g = Geo()
        K.pattern_relief(g, li["x0"] + 0.3, li["x1"] - 0.3, li["zb"] + 0.2, li["zt"] - 0.2, li["yb"] - 0.2, cell=1.1, key="pattern", depth=0.06, kind="diamond")
        S.add(g, eid + "_Quilting", R, "QuiltedWall", "A", s["ref"])
    hook_lamps(S, R, "ShaftLamp", [(X(7394) - 0.4, 1.9, Z(my)) for my in (3200, 3260, 3320)], REF)
    mi, bi = infos["Mid"], infos["Base"]
    g = Geo().use("wall_deep")                               # black on the master round the narrow shaft: solid dark mass with ragged edges
    bu = infos["BaseUpper"]                                     # the masses stand on the narrower upper row of the base
    for k, (xa, xb) in enumerate(((max(mi["x0"], bu["x0"]) + 0.4, X(7358) - 0.6), (X(7394) + 0.6, min(mi["x1"], bu["x1"]) - 0.4))):
        g.box(xa, xb, -6.5, 12.5, bu["zt"] + 0.55, mi["bottom"] - 0.05)
        SH.hanging_fringe(g, xa + 0.2, xb - 0.2, -6.6, mi["bottom"] - 0.1, 2.2, seed=40 + k)
        SH.hanging_fringe(g, xa + 0.2, xb - 0.2, -6.6, lerp(bu["zt"], mi["bottom"], 0.5), 1.6, seed=44 + k)
        g.use("wall_deep")
    S.add(g, "BlackMass", R, "SolidMass", "C", "black on master C4 round the narrow shaft", note="solid between the middle block and the base; its depth is completion")
    for eid, n in (("Mid", 3), ("Top", 1)):
        info = infos[eid]
        P.populate(S, R, eid, info, ["resident_0", "resident_2"], n, seed=25 + n, avoid=[(i, info["x0"], info["x1"], 2.2, info["yb"]) for i, zf, top in info["storeys"]])
    S.cam_auto(R, (X(7079), X(7532), -8.0, 14.0, Z(3558), Z(2636) + 1.0), ref="master C4", views=("front", "closed", "oblique", "back"))
    S.camera("Context", R, (X(7000), -70.0, Z(3300)), look=(X(7300), 3.0, Z(3050)), lens=26.0, kind="view", hide=("BACKDROP", "CAVESHELL"),
             purpose="the jar house with the rock and buildings round it (nothing hidden but the far layers)")
    S.cam_front("Section", R, (6980, 2600, 7560, 3660), y=-10.0, ref="master C4_east_right_block", purpose="jar house and rain gap, same frame as master C4")
    zr = mi["floors"][2]                                        # a jar room (storey 1 is the black band)
    S.camera("Interior", R, (X(7250) + 1.0, mi["yf"] + 1.4, zr + 1.6), look=(mi["x1"] - 3.0, mi["yb"] - 1.5, zr + 1.4), lens=18.0, kind="interior", purpose="a jar room")     # clear of the black end bay (D-383)


# ============================================================================ EastUndercroft
def east_undercroft(S):
    R = "EastUndercroft"
    REF = "master C2, C4 (no local screenshot)"
    e = S.el(R, "Gallery")
    st = dict(P.STYLES["corridor"], bay=4.6, fringe=True, back=("blind", "niche", "blind", "lancet"), lamp="string", wall="stone_far", floor="stone", trim="stone_far_trim")
    info = P.stack(S, R, e, st, ext_faces=("R",), door_y={"L": 0.0})
    x0, x1, yf, yb, zf, zt = info["x0"], info["x1"], info["yf"], info["yb"], info["floors"][0], info["zt"]
    g = Geo().use("iron_scaffold")                              # big braces crossing in front of the gallery, from below its floor (A: master C2, C4)
    for k, bx in enumerate(info["edge_x"][1:-1]):
        if k % 2 == 0:
            g.tube([(bx - 4.6, yf - 0.9, zf - 3.0), (bx + 4.6, yf - 0.9, zt + 0.4)], 0.16, segs=6)
            g.tube([(bx + 4.6, yf - 0.9, zf - 3.0), (bx - 4.6, yf - 0.9, zt + 0.4)], 0.16, segs=6)
            g.ellipsoid((bx, yf - 0.9, lerp(zf - 3.0, zt + 0.4, 0.5)), (0.3, 0.3, 0.3), segs=8, steps=5)
    S.add(g, "Braces", R, "GalleryBraces", "A", REF, layer="FRONT")
    g = Geo()                                                    # uneven ceiling: rock lumps and a long ragged fringe (A: master C2)
    rand = rng(91)
    for k in range(9):
        px = lerp(x0 + 2.0, x1 - 2.0, k / 8) + rand(-1.0, 1.0)
        K.rock(g, px - 2.4, px + 2.4, yf + 0.6, yb - 0.8, zt - rand(0.6, 1.6), zt + 0.4, seed=200 + k, amp=0.4, key="wall_deep")
    SH.hanging_fringe(g, x0 + 0.5, x1 - 0.5, yf + 0.5, zt - 0.2, 1.4, seed=93)
    S.add(g, "CeilingLumps", R, "CeilingRock", "C", REF, note="uneven ceiling read from the master; form is completion")
    g = Geo()
    for k in range(5):
        px = lerp(x0 + 6.0, x1 - 8.0, k / 4)
        SH.float_slab(g, px, 2.0 + 1.5 * (k % 2), zf + 1.5 + 0.5 * (k % 3), w=2.6, d=1.8, seed=k + 30)
    P.stairs(g, x0 - 0.4, x0 + 1.4, -1.3, 1.3, zf + 0.6, zf, step=0.2, key="stone")
    S.add(g, "Ledges", R, "FloatingPlatform", "A", REF, note="ledges observed on the master; depth is completion", smooth=35)
    P.populate(S, R, "Gallery", info, ["husk_sentry", "heavy_sentry"], 2, seed=27, avoid=[(0, x0, x1, 0.9, yb)])
    S.cam_auto(R, (x0, x1, yf, yb, zf - 2.0, zt + 1.0), ref="master C2, C4", views=("front", "closed", "oblique"))
    S.camera("Interior", R, (x0 + 1.6, yf + 1.4, zf + 1.6), look=(x0 + 30.0, yb - 1.0, zf + 2.2), lens=18.0, kind="interior", purpose="low gallery under the station")
    S.camera("Context", R, (x0 - 12.0, yf - 40.0, zf + 9.0), look=((x0 + x1) / 2, yb, zf + 2.0), lens=24.0, kind="view", hide=("BACKDROP", "CAVESHELL"),
             purpose="the gallery with the ground, rock and buildings round it (nothing hidden but the far layers)")


REGIONS = {"EastWell": east_well, "EastTower": east_tower, "EastPeakHall": east_peak_hall, "EastStack": east_stack, "EastQuarter": east_quarter,
           "EastStation": east_station, "EastRainGap": east_rain_gap, "EastJarHouse": east_jar_house, "EastUndercroft": east_undercroft}
