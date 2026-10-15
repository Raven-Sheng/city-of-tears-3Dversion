"""Stage 3 kit, part 2: louvre bands, shell-fringe cladding, hanging fringe and lift slot panels (pure geometry)."""
import math

from cot_geo import Geo, TAU, fbm, lerp, place, rng
from mathutils import Vector


def louvre_band(g, x0, x1, y0, y1, zb, zt, posts=None, spikes=True, slat=0.17, sill=True, m=None):
    """Straight louvred roof band: dark core, slats on all four faces, posts, top rail and spear rows
    (A: flat louvre roofs in 04_Bridges right, 11_Lower_City upperbridge, 01_Soul_Sanctuary core_upper / upper2)."""
    g.use("louvre_core")
    g.box(x0 + 0.1, x1 - 0.1, y0 + 0.1, y1 - 0.1, zb, zt - 0.04, m=m)
    g.use("louvre")
    n_sl = max(4, int((zt - zb) / slat))
    for k in range(n_sl):
        z = zb + (k + 0.5) * (zt - zb) / n_sl
        for yy in (y0, y1):
            g.box(x0, x1, yy - 0.06, yy + 0.06, z - 0.055, z + 0.055, m=m)
        for xx in (x0, x1):
            g.box(xx - 0.06, xx + 0.06, y0, y1, z - 0.055, z + 0.055, m=m)
    g.use("louvre_frame")
    n = posts if posts else max(1, int(round((x1 - x0) / 3.3)))
    post_x = [x0 + (x1 - x0) * i / n for i in range(n + 1)]
    for yy in (y0 - 0.09, y1 + 0.09):
        for px in post_x:
            g.box(px - 0.09, px + 0.09, yy - 0.07, yy + 0.07, zb, zt + 0.12, m=m)
        g.box(x0, x1, yy - 0.08, yy + 0.08, zt, zt + 0.14, m=m)
    for xx in (x0 - 0.09, x1 + 0.09):
        g.box(xx - 0.08, xx + 0.08, y0, y1, zt, zt + 0.14, m=m)
    if sill:
        g.use("stone_dark")
        g.box(x0 - 0.3, x1 + 0.3, y0 - 0.32, y1 + 0.32, zb - 0.26, zb, m=m)
    if spikes:
        g.use("iron")
        for yy in (y0 - 0.09, y1 + 0.09):
            for px in post_x:
                g.spike((px, yy, zt + 0.12), (px, yy, zt + 1.3), 0.11, bulb=1.2, m=m)
            cnt = max(1, int((x1 - x0) / 0.55))
            for i in range(1, cnt):
                px = x0 + (x1 - x0) * i / cnt
                if min(abs(px - qx) for qx in post_x) > 0.22:
                    g.spike((px, yy, zt + 0.12), (px, yy, zt + 0.6), 0.05, segs=5, bulb=0.6, m=m)


def scallop_trim(g, x0, x1, y, z, step=0.95, drop=0.3, key="iron", m=None):
    """Row of small inverted arches with a point at each node (A: under every louvre roof in the references)."""
    g.use(key)
    n = max(1, int(round((x1 - x0) / step)))
    for i in range(n):
        xa, xb = x0 + (x1 - x0) * i / n, x0 + (x1 - x0) * (i + 1) / n
        mid, rad = (xa + xb) / 2, (xb - xa) / 2
        g.tube([(mid + rad * math.cos(math.pi + math.pi * j / 8), y, z - drop * math.sin(math.pi * j / 8)) for j in range(9)], 0.04, segs=5, ref=(0, 1, 0), m=m)
        g.spike((xa, y, z), (xa, y, z - drop * 0.9), 0.04, segs=4, m=m)


def _spow(v, e):
    return math.copysign(abs(v) ** e, v)


def fringe_tier_rect(g, cx, cy, hx, hy, z_top, z_bot, seed=0, e=0.3, ragged=0.34, key="fringe", top_in=0.95, flare=1.05):
    """Shell-fringe tier wrapped round a rounded rectangle (the black fringed building masses of the master map).

    Same construction and UV convention as cot_assets.add_fringe_tier (u = locks round the tier, v = 0 top .. 1 hem).
    """
    g.use(key)
    rand = rng(seed * 7919 + 13)
    h = z_top - z_bot
    per = 4 * (hx + hy)
    segs = int(max(40, min(260, per * 1.6)))
    hem = []
    for i in range(segs):
        v = fbm(i * 0.55 + seed * 3.1, seed * 1.7, 0.0, 3)
        tooth = (rand() ** 2.0) * 1.25 + (0.3 if i % 4 == 0 else 0.0)
        hem.append(h * ragged * (0.3 * v + tooth * 0.8))
    locks = max(8, round(per * 0.24))
    phase = seed * 1.37

    def pt(i, scale, z, grow=0.0):
        a = TAU * i / segs + math.pi / 2
        ca, sa = _spow(math.cos(a), e), _spow(math.sin(a), e)
        return (cx + (hx * scale + grow) * ca, cy + (hy * scale + grow) * sa, z)

    steps = 8
    bulge = min(0.5, 0.05 * h + 0.12)                     # absolute outward bulge of the tuft
    rows, uvs = [], []
    for k in range(steps + 1):
        t = k / steps
        shoulder = math.sin(math.pi / 2 * min(1.0, t / 0.38))
        scale = top_in + (flare - top_in) * shoulder
        grow = bulge * shoulder - (bulge + 0.1) * max(0.0, (t - 0.38) / 0.62) ** 1.5
        row, uvrow = [], []
        for i in range(segs):
            z = z_top - h * t ** 1.35
            if k == steps:
                z -= hem[i]
            elif k == steps - 1:
                z -= hem[i] * 0.5
            elif k == steps - 2:
                z -= hem[i] * 0.15
            lock = 0.2 * math.sin(locks * TAU * i / segs + phase) * min(1.0, t * 2.0)
            row.append(pt(i, scale, z, grow + lock))
            uvrow.append((locks * i / segs, t))
        rows.append(row)
        uvs.append(uvrow)
    inner = [pt(i, 0.92, lerp(z_top, z_bot, 0.55)) for i in range(segs)]
    top = [pt(i, top_in * 0.94, z_top) for i in range(segs)]
    dark = [(locks * i / segs, 1.0) for i in range(segs)]
    g.grid([top] + rows + [inner, top], close_u=True, uvs=[dark] + uvs + [dark, dark])


def shell_core(g, cx, cy, hx, hy, z0, z1, e=0.3, key="tower_core", scale=0.9):
    g.use(key)
    segs = 64
    ring = lambda z: [(cx + hx * scale * _spow(math.cos(TAU * i / segs), e), cy + hy * scale * _spow(math.sin(TAU * i / segs), e), z) for i in range(segs)]
    g.grid([ring(z0), ring(z1)], close_u=True, cap_start=True, cap_end=True)


def hanging_fringe(g, x0, x1, y, z_top, drop, seed=0, key="curtain", axis="X", n=None, thick=0.07):
    """Ragged hanging fringe with thickness (under ceilings, decks and overhangs; A: master map and most interiors)."""
    g.use(key)
    rand = rng(seed + 5)
    n = n or max(6, int(abs(x1 - x0) / 0.35))
    rows = []
    for i in range(n + 1):
        t = i / n
        p = lerp(x0, x1, t)
        zb = z_top - drop * (0.25 + 0.75 * rand() ** 1.6)
        if axis == "X":
            rows.append([(p, y - thick, z_top), (p, y + thick, z_top), (p, y + thick * 0.4, zb), (p, y - thick * 0.4, zb)])
        else:
            rows.append([(y - thick, p, z_top), (y + thick, p, z_top), (y + thick * 0.4, p, zb), (y - thick * 0.4, p, zb)])
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)


def slot_panel(g, cx, y, z, w=2.2, h=2.4, slots=4, key="trim", back="wall_deep"):
    """Panel of narrow round-headed slots that interrupts the lift shafts (A: 11_Lower_City middle / bottom)."""
    g.use(back)
    g.box(cx - w / 2, cx + w / 2, y, y + 0.12, z, z + h)
    g.use(key)
    sw = w / slots
    for k in range(slots):
        sx = cx - w / 2 + sw * (k + 0.5)
        hw = sw * 0.32
        zt, zb = z + h - 0.25 - hw, z + 0.25 + hw
        path = [(sx + hw * math.cos(TAU * i / 16), y - 0.03, (zt if i <= 8 else zb) + hw * math.sin(TAU * i / 16)) for i in range(17)]
        g.tube(path + [path[0]], 0.05, segs=5, ref=(0, 1, 0), cap=False)
    g.box(cx - w / 2 - 0.1, cx + w / 2 + 0.1, y - 0.1, y + 0.14, z - 0.12, z)
    g.box(cx - w / 2 - 0.1, cx + w / 2 + 0.1, y - 0.1, y + 0.14, z + h, z + h + 0.12)


def k_pad(seed=0, spots=13):
    """Spotted pad: a flattened cushion covered with pale spots, the unit of the cluster walls
    (A: 09_Bench all four, 07_Interior centre / middle_bottom, 03_Left_City left_bottom). Lies in the local XZ plane, faces -Y."""
    g = Geo()
    rand = rng(seed * 59 + 7)
    g.use("cluster")
    rx, rz = 1.0, rand(0.72, 0.9)
    g.ellipsoid((0, 0, 0), (rx, 0.24, rz), segs=14, steps=8, e=0.9)
    g.use("cluster_spot")
    placed = []
    tries = 0
    while len(placed) < spots and tries < 200:
        tries += 1
        u, v = rand(-0.78, 0.78), rand(-0.78, 0.78)
        if u * u + v * v > 0.62 or any((u - a) ** 2 + (v - b) ** 2 < 0.06 for a, b in placed):
            continue
        placed.append((u, v))
        y = -0.24 * math.sqrt(max(0.0, 1 - u * u - v * v)) * 0.98
        r = rand(0.08, 0.13)
        g.ellipsoid((u * rx, y, v * rz), (r, 0.03, r), segs=6, steps=4)
    return g


def float_slab(g, x, y, z, w=2.0, d=1.5, seed=0, spear=False, key="stone", iron="iron"):
    """Small floating stone platform with iron lace under it and, on some, a spear rod standing on it
    (A: 03_Left_City middle / middle_upper, master A_left_well_lower)."""
    rand = rng(seed + 3)
    g.use(key)
    n = max(2, int(round(w / 0.62)))
    for i in range(n):
        cx = x - w / 2 + w * (i + 0.5) / n
        g.ellipsoid((cx, y, z - 0.17), (w / n * 0.52, d / 2, 0.19), segs=8, steps=5, e=0.5)
    g.use(iron)
    g.tube([(x - w / 2, y - d / 2, z - 0.36), (x + w / 2, y - d / 2, z - 0.36)], 0.035, segs=4)
    g.tube([(x - w / 2, y + d / 2, z - 0.36), (x + w / 2, y + d / 2, z - 0.36)], 0.035, segs=4)
    for sx in (-1, 1):
        for yy in (y - d / 2, y + d / 2):
            g.tube([(x + sx * w / 2, yy, z - 0.36), (x + sx * w * 0.3, yy, z - 0.62), (x + sx * w * 0.08, yy, z - 0.5), (x, yy, z - 0.86)], 0.028, segs=4, ref=(0, 1, 0))
    g.spike((x, y, z - 0.4), (x, y, z - 1.35), 0.07, segs=5, bulb=1.1)
    if spear:
        g.tube([(x, y, z), (x, y, z + 2.2)], 0.035, segs=5)
        g.ellipsoid((x, y, z + 2.25), (0.09, 0.09, 0.16), segs=6, steps=5)
        g.spike((x, y, z + 2.3), (x, y, z + 3.2), 0.06, segs=5, bulb=1.0)


def iron_walk(g, x0, x1, y0, y1, z, key="iron", plate="iron_plate"):
    """Iron walkway: thin deck, edge beams and lace under the edges (A: 03_Left_City middle, Background_01)."""
    g.use(plate)
    g.box(x0, x1, y0, y1, z - 0.1, z)
    g.use(key)
    for yy in (y0, y1):
        g.tube([(x0, yy, z - 0.05), (x1, yy, z - 0.05)], 0.06, segs=5)
        g.tube([(x0, yy, z - 0.42), (x1, yy, z - 0.42)], 0.03, segs=4)
        scallop_trim(g, x0, x1, yy, z - 0.42, step=1.3, drop=0.34, key=key)
        n = max(1, int(round((x1 - x0) / 1.3)))
        for i in range(n + 1):
            px = x0 + (x1 - x0) * i / n
            g.tube([(px, yy, z - 0.42), (px, yy, z - 0.05)], 0.02, segs=4, cap=False)
    for xx in (x0, x1):
        g.tube([(xx, y0, z - 0.05), (xx, y1, z - 0.05)], 0.06, segs=5)


def gourd_hut(g, m=None, h=6.0, r=2.1):
    """Shell hut with a twisted chimney and a glowing door (A: 09_Bench/Bench_top.jpg). Door faces -Y."""
    g.use("shell")
    prof = [(r * 0.78, 0.0), (r * 0.98, h * 0.1), (r * 1.04, h * 0.22), (r * 0.95, h * 0.34), (r * 0.7, h * 0.45), (r * 0.42, h * 0.53), (r * 0.34, h * 0.57)]

    def mod(th, k):
        return 1.0 + 0.045 * math.sin(3 * th + k * 0.9)

    g.revolve(prof, segs=24, m=m, mod=mod, cap_top=True)
    g.use("trim")
    for k in range(4):                                    # swirling lap lines of the shell
        z = h * (0.08 + 0.1 * k)
        rr = r * (1.01 - 0.05 * k * k * 0.3)
        g.tube([(rr * math.cos(a) * 1.01, rr * math.sin(a) * 1.01, z + 0.25 * math.sin(a * 0.5 + k)) for a in [TAU * i / 28 for i in range(29)]], 0.05, segs=4, ref=(0, 0, 1), m=m, cap=False)
    g.use("shell")
    path = [(0.0, 0.0, h * 0.5), (0.1, 0.0, h * 0.62), (0.34, 0.05, h * 0.74), (0.26, 0.1, h * 0.86), (0.0, 0.05, h * 0.95), (-0.12, 0.0, h * 1.03)]
    g.tube(path, [r * 0.34, r * 0.24, r * 0.17, r * 0.13, r * 0.11, r * 0.13], segs=10, ref=(0, 1, 0), m=m)
    g.use("lamp_warm")
    g.ellipsoid((r * 0.18, -r * 0.93, h * 0.17), (r * 0.26, r * 0.1, h * 0.16), segs=12, steps=8, m=m)
    g.use("trim")
    g.tube([(r * 0.18 + r * 0.28 * math.cos(TAU * i / 20), -r * 0.99, h * 0.17 + h * 0.17 * math.sin(TAU * i / 20)) for i in range(21)], 0.06, segs=5, ref=(0, 1, 0), m=m, cap=False)


def block_course(g, length, z0, z1, thick=0.5, block=0.85, seed=0, m=None, key="stone", course_h=0.52, e=0.42):
    """Courses of rounded blocks along local +X from the origin (a wall face of the given thickness, centred on y = 0)."""
    g.use(key)
    rand = rng(seed + 101)
    n_course = max(1, int(round((z1 - z0) / course_h)))
    ch = (z1 - z0) / n_course
    for c in range(n_course):
        zc = z0 + ch * (c + 0.5)
        n = max(1, int(round(length / block)))
        cuts = [0.0] + sorted(length * (i + rand(-0.22, 0.22)) / n for i in range(1, n)) + [length]
        if c % 2 == 1 and n > 1:
            cuts = [0.0] + [min(length - 0.2, v + length / n * 0.35) for v in cuts[1:-1]] + [length]
        for a, b in zip(cuts, cuts[1:]):
            g.ellipsoid(((a + b) / 2, rand(-0.04, 0.04), zc), ((b - a) / 2 * 1.02, thick / 2, ch / 2 * 1.04), segs=10, steps=6, e=e, m=m)


def rubble_pier(g, x0, x1, y0, y1, z0, z1, seed=0, block=0.85, key="stone", core="stone_dark"):
    """Free-standing pier: a dark core faced on all four sides with courses of rounded blocks."""
    g.use(core)
    g.box(x0 + 0.2, x1 - 0.2, y0 + 0.2, y1 - 0.2, z0, z1 - 0.05)
    block_course(g, x1 - x0, z0, z1, 0.5, block, seed, place(x0, y0 + 0.15, 0), key)
    block_course(g, x1 - x0, z0, z1, 0.5, block, seed + 1, place(x0, y1 - 0.15, 0), key)
    block_course(g, y1 - y0, z0, z1, 0.5, block, seed + 2, place(x0 + 0.15, y0, 0, rz=math.pi / 2), key)
    block_course(g, y1 - y0, z0, z1, 0.5, block, seed + 3, place(x1 - 0.15, y0, 0, rz=math.pi / 2), key)


def arch_ring(g, w, kind="round", band=0.28, y0=-0.15, y1=0.15, m=None, rise=None, n=10):
    """Solid arch ring (voussoir band) spanning w, springing on z = 0."""
    import cot_kit as K
    inner = K.arch_profile(w, kind, rise, n)
    outer = K.arch_profile(w + 2 * band, kind, (rise + band) if rise else None, n)
    g.prism(list(outer) + list(reversed(inner)), y0, y1, m=m)


def k_aedicule(w=2.6, h=4.3, key="stone_far_trim", pendant=True):
    """Round arch on two slender columns with a shell crest and a hanging ornament: the unit of the street arcades
    (A: 05_Streets left / middle / right)."""
    g = Geo().use(key)
    spring = h - w / 2 - 0.3
    r = 0.11
    for sx in (-1, 1):
        prof = [(r * 2.2, 0.0), (r * 2.2, 0.1), (r * 1.4, 0.2), (r, 0.4), (r, spring - 0.5), (r * 1.6, spring - 0.42), (r * 1.1, spring - 0.3), (r * 1.9, spring - 0.14), (r * 2.3, spring)]
        g.revolve(prof, segs=8, m=place(sx * w / 2, 0, 0))
    arch_ring(g, w - 0.2, "round", 0.24, -0.14, 0.14, m=place(0, 0, spring))
    g.ellipsoid((0, 0, spring + w / 2 + 0.22), (0.34, 0.16, 0.24), segs=10, steps=6)       # shell crest
    for k in range(3):
        g.ring_arc((0, -0.02, spring + w / 2 + 0.14 + 0.1 * k), 0.3 - 0.06 * k, 0, TAU, 0.025, n=10, plane="XY", segs=4)
    if pendant:
        g.use("iron")
        top = spring + (w - 0.2) / 2
        g.tube([(0, 0, top), (0, 0, top - 0.5)], 0.02, segs=4)
        g.revolve([(0.02, top - 0.5), (0.1, top - 0.62), (0.13, top - 0.82), (0.06, top - 1.0), (0.1, top - 1.1), (0.01, top - 1.4)], segs=8)
    return g


def k_hive_jar(v=0):
    """Ribbed beehive jar (A: rows of jars in 05_Streets, 07_Interior, 06_Right_City elevator_upper)."""
    g = Geo().use("pot")
    s = (1.0, 0.8, 1.25)[v % 3]
    w = (1.0, 1.15, 0.85)[v % 3]
    prof = [(0.3, 0.0), (0.38, 0.08), (0.35, 0.17), (0.41, 0.28), (0.37, 0.38), (0.42, 0.5), (0.36, 0.6), (0.38, 0.7), (0.28, 0.8), (0.3, 0.88), (0.13, 0.96), (0.02, 1.0)]
    g.revolve([(r * w * s, z * s) for r, z in prof], segs=12)
    return g


def k_rune_tablet(w=0.75, h=2.4, seed=0):
    """Hanging tablet with glowing glyphs (A: 05_Streets station, 06_Right_City station). Hangs from z = 0, faces -Y."""
    g = Geo()
    rand = rng(seed + 61)
    g.use("stone_dark")
    g.ellipsoid((0, 0, -0.25 - h / 2), (w / 2, 0.07, h / 2), segs=10, steps=8, e=0.35)
    g.use("iron")
    g.tube([(0, 0, 0), (0, 0, -0.25)], 0.02, segs=4)
    g.use("glass_blue")
    z = -0.5
    while z > -0.1 - h:
        for sx in (-0.17, 0.17):
            kind = int(rand(0, 3))
            if kind == 0:
                g.ellipsoid((sx, -0.07, z), (0.07, 0.02, 0.12), segs=6, steps=4)
            elif kind == 1:
                g.box(sx - 0.1, sx + 0.1, -0.09, -0.06, z - 0.035, z + 0.035)
            else:
                g.ring_arc((sx, -0.075, z), 0.08, 0, TAU, 0.022, n=8, plane="XZ", segs=4)
        z -= 0.3
    return g


def k_medallion(r=1.7):
    """Round wheel emblem with a beetle at its hub (A: 07_Interior centre / middle_upper). Lies in the XZ plane."""
    g = Geo().use("trim")
    g.ring_arc((0, 0, 0), r, 0, TAU, 0.09, n=32, plane="XZ", segs=6)
    g.ring_arc((0, 0, 0), r * 0.78, 0, TAU, 0.05, n=28, plane="XZ", segs=5)
    g.ring_arc((0, 0, 0), r * 0.34, 0, TAU, 0.05, n=18, plane="XZ", segs=5)
    for k in range(8):
        a = TAU * k / 8
        g.tube([(r * 0.34 * math.cos(a), 0, r * 0.34 * math.sin(a)), (r * math.cos(a), 0, r * math.sin(a))], 0.035, segs=4)
    g.ellipsoid((0, -0.06, 0), (r * 0.16, 0.08, r * 0.24), segs=10, steps=6)
    for sx in (-1, 1):
        for k in range(3):
            g.tube([(sx * r * 0.12, -0.06, r * (0.1 - 0.1 * k)), (sx * r * 0.3, -0.06, r * (0.2 - 0.14 * k))], 0.025, segs=4)
    return g


def hang_platform(g, x, y, z, z_top, w=2.4, d=2.0, cable=1.0, key="stone_dark", iron="iron"):
    """Dark slab hung on two cables with a lace bracket under it (A: 07_Interior all, master A_green_shaft)."""
    g.use(key)
    g.ellipsoid((x, y, z - 0.16), (w / 2, d / 2, 0.17), segs=12, steps=5, e=0.4)
    g.use(iron)
    for sx in (-1, 1):
        g.tube([(x + sx * cable, y, z - 0.1), (x + sx * cable, y, z_top)], 0.022, segs=4, cap=False)
        g.tube([(x + sx * w * 0.42, y, z - 0.34), (x + sx * w * 0.2, y, z - 0.52), (x, y, z - 0.42)], 0.028, segs=4, ref=(0, 1, 0))
    g.spike((x, y, z - 0.36), (x, y, z - 0.95), 0.06, segs=5, bulb=1.0)


def tunnel_arch(g, w, h, depth=10.0, m=None, key="stone_far", trim="stone_far_trim", dark="tower_core"):
    """Great station portal: stepped concentric arches leading into a dark tunnel (A: 05_Streets station, 06_Right_City station).
    Opening faces -Y, origin at the middle of the sill."""
    import cot_kit as K
    spring = h - w / 2
    for k in range(4):
        s = 1.0 - 0.07 * k
        g.use(trim if k % 2 == 0 else key)
        yk = 0.55 * k
        for sx in (-1, 1):
            g.box(sx * w / 2 * s - (0.0 if sx > 0 else 0.3), sx * w / 2 * s + (0.3 if sx > 0 else 0.0), yk, yk + 0.55, 0.0, spring * s, m=m)
        arch_ring(g, w * s, "round", 0.3, yk, yk + 0.55, m=(m @ place(0, 0, spring * s)) if m is not None else place(0, 0, spring * s))
    s = 1.0 - 0.07 * 3
    g.use(dark)                                             # tunnel walls, vault and a closed end (the line beyond is not built)
    hw = w / 2 * s
    g.box(-hw - 0.3, -hw, 2.2, depth, 0.0, spring * s, m=m)
    g.box(hw, hw + 0.3, 2.2, depth, 0.0, spring * s, m=m)
    rows = []
    for i in range(13):
        a = math.pi * i / 12
        rows.append([(hw * math.cos(a), 2.2, spring * s + hw * math.sin(a)), (hw * math.cos(a), depth, spring * s + hw * math.sin(a)),
                     ((hw + 0.3) * math.cos(a), depth, spring * s + (hw + 0.3) * math.sin(a)), ((hw + 0.3) * math.cos(a), 2.2, spring * s + (hw + 0.3) * math.sin(a))])
    g.grid(rows, close_u=True, cap_start=True, cap_end=True, m=m)
    g.prism([(-hw, 0.0), (hw, 0.0), (hw, spring * s)] + [(hw * math.cos(math.pi * i / 12), spring * s + hw * math.sin(math.pi * i / 12)) for i in range(1, 12)] + [(-hw, spring * s)],
            depth - 0.3, depth, m=m)
    g.use("iron")                                           # gate tracery across the mouth
    for k in range(-2, 3):
        x = hw * 0.36 * k
        top = spring * s + math.sqrt(max(0.0, hw * hw - x * x)) - 0.05
        g.tube([(x, 2.0, 0.0), (x, 2.0, top)], 0.035, segs=4, m=m, cap=False)
    g.tube([(hw * 0.9 * math.cos(math.pi * i / 10), 2.0, spring * s * 0.55 + hw * 0.5 * math.sin(math.pi * i / 10)) for i in range(11)], 0.03, segs=4, ref=(0, 1, 0), m=m)


def mask_relief(g, w, h, m=None, key="relief"):
    """Great calm mask face on a wall: smooth oval, brow, closed eyes, nose ridge, with a mantle spreading below
    (A: master D1 - only a small blurred image exists, so the features are kept few and plain; B). Faces -Y, base at z = 0."""
    g.use(key)
    rows = []
    for k in range(13):
        a = -math.pi / 2 + math.pi * k / 12
        s = max(0.03, math.cos(a))
        zf = math.sin(a)
        wide = 1.0 - 0.2 * max(0.0, -zf) ** 1.5
        rows.append([(w / 2 * s * wide * math.cos(TAU * i / 32), -0.2 * w * (s ** 0.8) * max(0.0, -math.sin(TAU * i / 32)), h * 0.5 + h * 0.5 * zf) for i in range(32)])
    g.grid(rows, close_u=True, cap_start=True, cap_end=True, m=m)
    y_at = lambda x, z: -0.2 * w * max(0.0, 1 - (x / (w / 2)) ** 2 - ((z - h * 0.5) / (h * 0.5)) ** 2) ** 0.45 - 0.03
    for sx in (-1, 1):
        ex = sx * w * 0.2
        g.tube([(ex - w * 0.13, y_at(ex - w * 0.13, h * 0.56), h * 0.56), (ex, y_at(ex, h * 0.52), h * 0.525), (ex + w * 0.13, y_at(ex + w * 0.13, h * 0.56), h * 0.56)], 0.012 * w, segs=5, ref=(0, 1, 0), m=m)
        g.tube([(sx * w * 0.06, y_at(sx * w * 0.06, h * 0.66), h * 0.66), (ex, y_at(ex, h * 0.7), h * 0.7), (sx * w * 0.36, y_at(sx * w * 0.36, h * 0.64), h * 0.64)], 0.018 * w, segs=5, ref=(0, 1, 0), m=m)
    g.tube([(0, y_at(0, h * 0.66) - 0.01 * w, h * 0.66), (0, y_at(0, h * 0.5) - 0.045 * w, h * 0.46), (0, y_at(0, h * 0.4) - 0.02 * w, h * 0.4)], [0.012 * w, 0.03 * w, 0.02 * w], segs=6, ref=(1, 0, 0), m=m)
    g.tube([(-w * 0.08, y_at(-w * 0.08, h * 0.28), h * 0.28), (0, y_at(0, h * 0.27), h * 0.272), (w * 0.08, y_at(w * 0.08, h * 0.28), h * 0.28)], 0.01 * w, segs=5, ref=(0, 1, 0), m=m)
    for k in range(3):                                      # bands of a head-dress over the brow
        zz = h * (0.84 + 0.05 * k)
        half = w * 0.5 * math.sqrt(max(0.02, 1 - ((zz - h * 0.5) / (h * 0.5)) ** 2)) + 0.08 * w * k
        g.tube([(-half, -0.03 * w, zz - 0.04 * h * k), (0, -0.12 * w + 0.03 * w * k, zz + 0.05 * h), (half, -0.03 * w, zz - 0.04 * h * k)], 0.018 * w, segs=5, ref=(0, 1, 0), m=m)
    for sx in (-1, 1):                                      # mantle folds falling from the jaw to the floor
        for k in range(4):
            g.tube([(sx * w * (0.22 + 0.05 * k), -0.06 * w, h * 0.12), (sx * w * (0.4 + 0.14 * k), -0.05 * w, h * (0.02 - 0.03 * k)), (sx * w * (0.62 + 0.2 * k), -0.03 * w, -h * (0.14 + 0.02 * k))],
                   [0.05 * w, 0.045 * w, 0.015 * w], segs=6, ref=(0, 1, 0), m=m)


def shell_mask(g, w, h, wing=2.6, m=None, key="relief", dark="wall_deep"):
    """Great shell mask on a wall (A: master D1 - an upright shell face divided by horizontal bands with a seam down the
    upper middle, a wide brim on top and folded wings spreading level from its sides; no human features). Faces -Y,
    origin at the middle of the bottom (chin)."""
    hw = w / 2
    prof = ((0.0, 0.42), (0.08, 0.7), (0.2, 0.87), (0.4, 0.97), (0.62, 1.0), (0.8, 0.96), (0.9, 0.84), (0.97, 0.6), (1.0, 0.3))

    def half(z):
        t = max(0.0, min(1.0, z / h))
        for (t0, f0), (t1, f1) in zip(prof, prof[1:]):
            if t <= t1:
                return hw * lerp(f0, f1, (t - t0) / max(1e-6, t1 - t0))
        return hw * prof[-1][1]

    depth = 0.32 * w

    def front_y(x, z):
        q = max(0.0, 1 - (x / max(0.05, half(z))) ** 2)
        return -depth * q ** 0.6 * (0.55 + 0.45 * math.sin(math.pi * min(1.0, z / h) ** 0.8))

    g.use(key)
    rows = []
    for k in range(15):
        z = h * k / 14
        hz = half(z)
        row = []
        for i in range(25):                               # front arc from right to left, then back across the wall plane
            x = hz * math.cos(math.pi * i / 24)
            row.append((x, front_y(x, z), z))
        for i in range(1, 6):
            row.append((lerp(-hz, hz, i / 6), 0.0, z))
        rows.append(row)
    g.grid(rows, close_u=True, cap_start=True, cap_end=True, m=m)
    g.use(dark)                                           # bands and the seam
    for t in (0.34, 0.6):
        z = h * t
        hz = half(z)
        g.tube([(hz * math.cos(math.pi * i / 16), front_y(hz * math.cos(math.pi * i / 16), z) - 0.02, z) for i in range(17)], 0.05, segs=4, ref=(0, 0, 1), m=m)
    g.tube([(0, front_y(0, z) - 0.025, z) for z in [h * (0.5 + 0.5 * i / 8) for i in range(9)]], 0.06, segs=4, ref=(1, 0, 0), m=m)
    g.use(key)                                            # raised band round the crown of the helmet
    zb = h * 0.8
    hb = half(zb)
    g.tube([(hb * 1.04 * math.cos(math.pi * i / 16), front_y(hb * 0.97 * math.cos(math.pi * i / 16), zb) - 0.1, zb) for i in range(17)], 0.12, segs=6, ref=(0, 0, 1), m=m)
    # folded wings: three broad curved blades a side, spreading level and drooping a little at the tips
    for sx in (-1, 1):
        for k, (zt, zd, ln, wd, yy) in enumerate(((0.8, 0.64, wing, 1.35, -0.12), (0.62, 0.46, wing * 0.97, 1.2, -0.2), (0.45, 0.3, wing * 0.86, 1.05, -0.28))):
            p0 = (hw * 0.45, h * zt)
            p2 = (hw + ln, h * zd)
            p1 = ((p0[0] + p2[0]) / 2, max(p0[1], p2[1]) + h * 0.06)
            up, lo = [], []
            for i in range(15):
                t = i / 14
                cx = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
                cz = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
                wdt = wd * (math.sin(math.pi * min(1.0, 0.18 + 0.82 * t) ** 0.6) * 0.8 + 0.2) * (1.0 - 0.3 * t)
                up.append((cx, cz + wdt / 2))
                lo.append((cx, cz - wdt / 2))
            pts = up + lo[::-1]
            pts = [(sx * px, pz) for px, pz in pts]
            if sx < 0:
                pts = pts[::-1]
            g.prism(pts, yy, yy + 0.16, m=m)
            g.use(dark)
            g.tube([(sx * px, yy - 0.02, pz) for px, pz in [((up[i][0] + lo[i][0]) / 2, (up[i][1] + lo[i][1]) / 2) for i in (1, 6, 13)]], 0.025, segs=4, ref=(0, 1, 0), m=m)
            g.use(key)


def k_shell_block(n=2):
    """Floating dark block with toothed bands, single or in a row (A: 01_Soul_Sanctuary bottom / core - the hovering platforms)."""
    g = Geo()
    for k in range(n):
        x = (k - (n - 1) / 2) * 1.0
        g.use("wall_deep")
        g.ellipsoid((x, 0, 0), (0.52, 0.5, 0.6), segs=12, steps=8, e=0.3)
        g.use("trim_pale")
        for z in (-0.3, 0.0, 0.3):
            g.ring_arc((x, 0, z), 1.0, 0, TAU, 0.035, n=16, plane="XY", segs=4, m=place(x, 0, z) @ place(s=(0.53, 0.51, 1.0)) @ place(-x, 0, -z))
        g.spike((x - 0.2, -0.5, 0.12), (x - 0.2, -0.5, -0.12), 0.07, segs=4)
        g.spike((x + 0.2, -0.5, 0.12), (x + 0.2, -0.5, -0.12), 0.07, segs=4)
    return g


def k_heap(seed=0, r=1.6, n=26):
    """Low heap of husks and shell scraps on the floor (A: 01_Soul_Sanctuary bottom / core)."""
    g = Geo()
    rand = rng(seed * 17 + 9)
    g.use("shell")
    g.ellipsoid((0, 0, 0.0), (r, r * 0.8, 0.5), segs=14, steps=6)
    for k in range(n):
        a, d = TAU * rand(), r * rand(0.0, 0.9)
        z = 0.5 * math.sqrt(max(0.0, 1 - (d / r) ** 2)) + rand(-0.05, 0.1)
        rr = rand(0.12, 0.26)
        g.use("shell" if k % 3 else "trim_pale")
        g.ellipsoid((d * math.cos(a), d * math.sin(a) * 0.8, z), (rr, rr * rand(0.7, 1.0), rr * rand(0.5, 0.9)), segs=8, steps=5)
    return g
