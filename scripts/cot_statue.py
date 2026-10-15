"""Hero asset: the fountain memorial of the plaza (Blender-only route, stage 2).

Round 4 (2026-10-02): widths re-measured on the main reference. With the height unchanged the plinth, the lower
leaves and the upper dish were about a quarter too wide; they now span 8.7 / 7.4 / 5.5 play-plane units
(plinth base step, lower leaf tips, upper dish tips), as measured on a crop that shows the whole plinth.

Local frame: origin on the plaza ground under the fountain axis, front = -Y, Z up. Total height about 9.4.
What the references show (A) and what is completion (C) is listed in docs/art_direction.md; in short the
front silhouette, tiers and figure types are observed, everything on the back half is completion that
continues the same radial rules.
"""
import math

from cot_geo import Geo, TAU, catmull, lerp, place, resample, rng


def _plinth(g, hx=3.9, hy=3.4):
    g.use("stone")

    def ring(inset, z, corner=0.35, n=6):
        ax, ay = hx - inset, hy - inset
        pts = []
        for cx, cy, a0 in ((ax - corner, ay - corner, 0.0), (-ax + corner, ay - corner, math.pi / 2),
                           (-ax + corner, -ay + corner, math.pi), (ax - corner, -ay + corner, 1.5 * math.pi)):
            for k in range(n + 1):
                a = a0 + (math.pi / 2) * k / n
                pts.append((cx + corner * math.cos(a), cy + corner * math.sin(a), z))
        return pts

    profile = [(0.06, 0.0), (0.0, 0.05), (0.0, 0.24), (0.07, 0.30), (0.26, 0.31), (0.26, 0.48), (0.20, 0.50),
               (0.13, 0.55), (0.11, 0.61), (0.15, 0.67), (0.24, 0.70), (0.30, 0.71), (0.30, 0.78), (0.5, 0.80)]
    g.grid([ring(i, z) for i, z in profile], close_u=True, cap_start=True, cap_end=True)
    # capstone course: separate rounded blocks around the top edge
    r = rng(11)
    for side in range(4):
        length = (hx if side % 2 == 0 else hy) * 2 - 0.5
        count = 8 if side % 2 == 0 else 7
        w = length / count
        for i in range(count):
            t = -length / 2 + w * (i + 0.5)
            jitter = r(-0.015, 0.015)
            cx, cy = (t, -(hy - 0.52)) if side == 0 else ((hx - 0.52, t) if side == 1 else ((t, hy - 0.52) if side == 2 else (-(hx - 0.52), t)))
            rx, ry = (w * 0.49, 0.36) if side % 2 == 0 else (0.36, w * 0.49)
            g.ellipsoid((cx, cy, 0.86 + jitter), (rx, ry, 0.105), segs=10, steps=6, e=0.42)
    # plaque on the front (A) and a matching one on the back (C)
    for sign in (-1, 1):
        y = sign * (hy - 0.24)
        g.use("stone")
        rows = []
        for k in range(7):
            a = -math.pi / 2 + math.pi * k / 6
            rows.append([(0.72 * math.cos(TAU * i / 20) * (0.55 + 0.45 * math.cos(a)), y + sign * 0.07 * math.sin(a) + sign * 0.03,
                          0.44 + 0.2 * math.sin(TAU * i / 20) * (0.55 + 0.45 * math.cos(a))) for i in range(20)])
        g.grid(rows, close_u=True, cap_start=True, cap_end=True)
        oval = [(0.74 * math.cos(TAU * i / 28), y + sign * 0.07, 0.44 + 0.215 * math.sin(TAU * i / 28)) for i in range(29)]
        g.tube(oval, 0.035, segs=6, ref=(0, 1, 0), cap=False)
        g.spike((0, y + sign * 0.06, 0.62), (0, y + sign * 0.1, 0.84), 0.11, segs=4)
        g.spike((0, y + sign * 0.06, 0.26), (0, y + sign * 0.1, 0.06), 0.13, segs=4)
        for sx in (-1, 1):
            g.spike((sx * 0.72, y + sign * 0.06, 0.44), (sx * 0.95, y + sign * 0.06, 0.44), 0.07, segs=4)
    # mushroom bollards in front (A) and behind (C)
    for bx, by in ((-2.6, -(hy + 0.55)), (2.7, -(hy + 0.55)), (-2.6, hy + 0.55), (2.7, hy + 0.55)):
        g.revolve([(0.15, 0.0), (0.13, 0.05), (0.12, 0.36), (0.25, 0.39), (0.27, 0.45), (0.2, 0.52), (0.05, 0.55)], segs=12,
                  m=place(bx, by, 0.0))


def _rolled_shell(g, m, length, radius, ribs=5):
    def mod(th, k):
        return 1.0
    prof = []
    n = ribs * 6
    for i in range(n + 1):
        t = i / n
        env = max(0.0, 1 - (2 * t - 1) ** 2) ** 0.55
        rib = 0.84 + 0.16 * abs(math.sin(math.pi * t * ribs))
        prof.append((max(0.01, radius * env * rib), (t - 0.5) * length))
    g.revolve(prof, segs=12, m=m)


def _lower_basin(g):
    g.use("statue")
    g.revolve([(2.42, 0.78), (2.46, 0.95), (2.1, 1.4), (1.3, 1.85), (0.85, 2.1), (0.7, 2.2)], segs=40, cap_bottom=True, cap_top=True)
    # gravel
    r = rng(5)
    g.use("stone")
    for i in range(64):
        a = r(0, TAU)
        rr = r(3.25, 3.65)
        s = r(0.06, 0.12)
        g.ellipsoid((rr * math.cos(a), rr * math.sin(a), 0.82 + s * 0.4), (s, s * r(0.7, 1.2), s * 0.6), segs=6, steps=4)
    # rolled shells around the foot of the basin
    g.use("shell")
    count = 14
    for i in range(count):
        a = TAU * (i + 0.5) / count
        rad = 0.41 if i % 2 == 0 else 0.36
        m = place(3.1 * math.cos(a), 3.1 * math.sin(a), 0.84 + rad * 0.86, rz=a + math.pi / 2) @ place(rx=math.pi / 2)
        _rolled_shell(g, m, 1.3, rad)
    count = 10
    for i in range(count):
        a = TAU * i / count
        m = place(2.05 * math.cos(a), 2.05 * math.sin(a), 1.5, rz=a + math.pi / 2) @ place(rx=math.pi / 2)
        _rolled_shell(g, m, 1.15, 0.34, ribs=4)
    # petals
    g.use("petal")
    count = 10
    for i in range(count):
        a = -math.pi / 2 + TAU * i / count
        upper = i % 2 == 0
        lift = 0.13 if upper else 0.0

        def centre(u, lift=lift):
            return (0.8 + 3.13 * u, 2.2 + lift - 0.75 * u ** 0.9 + 0.5 * max(0.0, (u - 0.72) / 0.28) ** 2)

        def width(u):
            return 1.2 * math.sin(math.pi * u ** 0.72) ** 0.72

        def thick(u):
            return lerp(0.62, 0.3, u) * (1 - u ** 5) + 0.02

        g.lens(centre, width, thick, nu=18, nv=12, m=place(rz=a), cup=-0.14, crease=0.05, edge=0.6, uv=True)


def _column_and_upper_basin(g):
    g.use("statue")
    for i in range(13):
        a = TAU * i / 13
        g.ellipsoid((1.02 * math.cos(a), 1.02 * math.sin(a), 2.42), (0.22, 0.22, 0.2), segs=10, steps=6)
    for i in range(10):
        a = TAU * (i + 0.5) / 10
        g.ellipsoid((0.8 * math.cos(a), 0.8 * math.sin(a), 2.68), (0.2, 0.2, 0.18), segs=10, steps=6)
    # segmented column: overlapping carapace cups widening upward
    g.use("shell")
    z = 2.5
    for i in range(5):
        rr = 0.6 + 0.07 * i
        g.revolve([(rr * 0.72, z), (rr * 1.05, z + 0.03), (rr * 1.1, z + 0.10), (rr * 0.98, z + 0.24), (rr * 0.8, z + 0.3)],
                  segs=24)
        z += 0.235
    # upper dish: eight broad lobes. Each lobe is domed across its width and its tip droops, so the rim reads as a
    # row of rounded humps with a pointed lobe out to each side; nested crescent ridges underneath (A: close-up).
    count = 8
    cup = -0.15
    for i in range(count):
        a = -math.pi / 2 + TAU * i / count
        lift = 0.08 if i % 2 == 0 else 0.0

        def centre(u, lift=lift):
            return (0.45 + 2.52 * u, 3.05 + lift + 1.45 * u ** 0.8 - 0.3 * max(0.0, (u - 0.7) / 0.3) ** 2)

        def width(u):
            return 1.36 * (u ** 0.6) * max(0.0, 1 - u ** 6) ** 0.5

        def thick(u):
            return lerp(0.5, 0.3, u)

        g.use("petal")
        g.lens(centre, width, thick, nu=18, nv=16, m=place(rz=a), cup=cup, crease=0.0, edge=0.9, uv=True)
    # underside of the dish: a solid funnel of nested shell rims stepping out from the stem, scalloped so that every
    # lobe carries its own stack of crescents (A: close-up; rounds 1-3 had loose ridge bars here)
    g.use("shell")
    prof = []
    rings = 6
    for k in range(rings + 1):
        rk = 0.95 + 0.25 * k
        u = (rk - 0.45) / 2.52
        zk = 3.05 + 1.45 * u ** 0.8 - 0.3 * max(0.0, (u - 0.7) / 0.3) ** 2 - lerp(0.5, 0.3, u) * 0.5 - 0.08
        if k > 0:
            h = zk - prof[-1][1] - 0.02
            base_r, base_z = prof[-1]
            prof[-1:] = [(base_r, base_z), (base_r + 0.06, base_z + 0.45 * h), (base_r + 0.035, base_z + h)]
        prof.append((rk, zk))
    prof.append((prof[-1][0] - 0.25, prof[-1][1] + 0.12))
    g.revolve(prof, segs=64, mod=lambda th, k: 1.0 + 0.11 * math.cos(8 * (th + math.pi / 2)), cap_bottom=True, cap_top=False)
    g.use("statue")
    g.revolve([(0.0, 4.0), (1.8, 4.08), (2.58, 4.25), (2.46, 4.3), (0.0, 4.3)], segs=32, cap_bottom=False, cap_top=False)
    g.use("water_dish")                                       # water standing in the dish
    g.revolve([(0.02, 4.29), (2.48, 4.29), (2.48, 4.325), (0.02, 4.325)], segs=32)


FIG_BASE = 4.32


def _dreamer(g, x, y, out, top=6.8, low=6.1, r_bot=0.36, r_top=0.245, base=FIG_BASE):
    """Straight cloaked dreamer whose hood is cut on a slant: high on the outer side, low towards the centre.

    out: unit XY vector pointing away from the central figure. A: close-up reference (left and right figures).
    Slender: in the main reference the figure is about 0.5 wide at the shoulders and 0.7 at the hem for a height
    of 2.1 (play-plane units), i.e. a narrow bell rather than a column.
    """
    ox, oy = out
    folds, per_fold = 8, 6
    segs = folds * per_fold
    half_drop = (top - low) / 2 - 0.05
    z_mid = (top + low) / 2 - 0.06
    nz = 16
    rows = []
    for i in range(nz + 1):
        t = i / nz
        r = r_top + (r_bot - r_top) * (1 - t) ** 2.2 + 0.1 * math.exp(-(t / 0.07) ** 2)       # hem spreads onto the dish
        d = lerp(0.3, 0.06, t)
        row = []
        for k in range(segs):
            th = TAU * k / segs
            ridge = abs(math.sin(math.pi * (k / per_fold % 1.0))) ** 0.6
            rr = r * (1 - d + d * ridge)
            cut = z_mid + half_drop * (math.cos(th) * ox + math.sin(th) * oy)       # slanted cut height at this angle
            row.append((x + rr * math.cos(th), y + rr * math.sin(th), lerp(base, cut, t ** 0.9)))
        rows.append(row)
    # domed cap over the slanted cut
    nx, ny, nzn = -ox * half_drop, -oy * half_drop, r_top
    ln = math.sqrt(nx * nx + ny * ny + nzn * nzn)
    nx, ny, nzn = nx / ln, ny / ln, nzn / ln
    rim = rows[-1]
    for k in range(1, 6):
        sk = math.cos(math.pi / 2 * k / 5)
        up = 0.23 * math.sin(math.pi / 2 * k / 5)
        rows.append([(x + (px - x) * sk + nx * up, y + (py - y) * sk + ny * up, z_mid + (pz - z_mid) * sk + nzn * up)
                     for px, py, pz in rim])
    g.use("statue")
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)
    g.use("petal")                                            # lighter rim band of the hood
    band = [(px + (px - x) * 0.05, py + (py - y) * 0.05, pz + 0.01) for px, py, pz in rim[::2]]
    g.tube(band + band[:1], 0.022, 0.02, segs=6, ref=(0, 0, 1), cap=False)
    g.use("statue")


def _central_figure(g, base=FIG_BASE):
    """Central horned figure: pleated robe, draped mantle, tied bands and a one-piece lyre-shaped horned head."""
    g.use("statue")
    g.revolve([(0.76, base), (0.8, base + 0.07), (0.66, base + 0.18), (0.45, base + 0.22)], segs=24)
    for i in range(10):                                       # turned-out toe folds of the hem
        a = TAU * (i + 0.5) / 10

        def centre(u):
            return (0.5 + 0.34 * u, base + 0.14 - 0.08 * u + 0.2 * u ** 3)

        g.lens(centre, lambda u: 0.16 * math.sin(math.pi * u ** 0.6) ** 0.7, lambda u: 0.1 * (1 - u) + 0.02, nu=8, nv=8,
               m=place(s=(1.0, 0.86, 1.0)) @ place(rz=a), cup=0.2)

    def robe(t):
        return 0.37 + 0.3 * (1 - t) ** 1.6 + 0.13 * math.exp(-(t / 0.07) ** 2)

    g.fluted(base + 0.18, 6.55, robe, folds=13, depth_fn=lambda t: lerp(0.24, 0.1, t), nz=16, sy=0.86, sharp=0.6)

    def mantle(t):
        return 0.2 + 0.34 * (1 - t) ** 0.85

    # short cape: pleated, its hem hanging to a point at each side and cut up in a V at the front, where the two
    # lapel edges run down from the brooch (A: main reference and close-up)
    folds, per_fold, nzc = 8, 6, 12
    segs = folds * per_fold
    rows = []
    for i in range(nzc + 1):
        t = i / nzc
        d = lerp(0.24, 0.06, t)
        row = []
        for k in range(segs):
            th = TAU * k / segs
            side = abs(math.cos(th)) ** 2.5
            front = math.exp(-((th - 1.5 * math.pi) / 0.4) ** 2)
            z_hem = 6.22 - 0.34 * side + 0.2 * front
            ridge = abs(math.sin(math.pi * ((k / per_fold + 0.5) % 1.0))) ** 0.5
            rr = mantle(t) * (1 + 0.2 * side * (1 - t) ** 2) * (1 - d + d * ridge)
            row.append((rr * math.cos(th), rr * math.sin(th) * 0.9, lerp(z_hem, 7.24, t)))
        rows.append(row)
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)
    for sx in (-1, 1):
        g.tube([(0.0, -0.31, 6.96), (sx * 0.22, -0.4, 6.66), (sx * 0.45, -0.36, 6.32), (sx * 0.64, -0.16, 5.96)],
               [0.03, 0.045, 0.045, 0.02], segs=6, ref=(0, 1, 0))
    # bands crossing below the head, and a diamond brooch (A: close-up)
    for sx in (-1, 1):
        g.tube([(sx * -0.2, -0.2, 6.98), (sx * -0.07, -0.25, 7.14), (sx * 0.08, -0.2, 7.3), (sx * 0.17, -0.1, 7.44)],
               0.035, 0.075, segs=8, ref=(0, 1, 0))
    g.spike((0, -0.29, 6.96), (0, -0.31, 7.1), 0.07, segs=4)
    g.spike((0, -0.29, 6.96), (0, -0.31, 6.8), 0.07, segs=4)
    g.use("statue_head")
    # one-piece head: a single lyre-shaped plate. Two broad horn blades rise from the neck, meet in a rounded crotch
    # and carry two upward barbs on each inner edge (A: close-up reference). Built as one extruded outline.
    right = [(0.0, 7.2), (0.14, 7.24), (0.24, 7.42), (0.36, 7.68), (0.5, 7.95), (0.61, 8.25), (0.69, 8.55), (0.725, 8.85),
             (0.715, 9.08), (0.665, 9.27), (0.59, 9.4), (0.54, 9.47),                    # outer edge up to the tip
             (0.545, 9.3), (0.535, 9.12), (0.5, 8.95), (0.465, 8.84),                     # inner edge coming down
             (0.38, 8.9), (0.31, 9.02), (0.35, 8.82), (0.395, 8.66), (0.37, 8.5),         # upper barb
             (0.28, 8.54), (0.2, 8.66), (0.24, 8.46), (0.29, 8.3), (0.24, 8.14),          # lower barb
             (0.16, 8.02), (0.08, 7.95)]                                                  # into the crotch
    # smooth each run between sharp points: horn tip (11), upper barb tip (17), lower barb tip (22)
    runs = (right[0:12], right[11:18], right[17:23], right[22:] + [(0.0, 7.93)])
    half = []
    for run in runs:
        pts = catmull(run, per=4)
        half += pts if not half else pts[1:]
    outline = half + [(-px, pz) for px, pz in reversed(half[1:-1])]
    g.prism(outline, -0.09, 0.09, smooth=True, half_fn=lambda x, z: lerp(0.17, 0.035, min(1.0, max(0.0, (z - 7.2) / 2.2)) ** 0.8))


def build_statue(coll, materials, props):
    """Returns the list of created objects (plinth, basins, figures, rods)."""
    objs = []
    g = Geo()
    _plinth(g)
    objs.append(g.to_object("COT_Statue_Plinth", coll, materials, dict(props, cot_part="plinth")))

    g = Geo()
    _lower_basin(g)
    _column_and_upper_basin(g)
    objs.append(g.to_object("COT_Statue_Basins", coll, materials, dict(props, cot_part="basins")))

    g = Geo()
    _central_figure(g)
    # Standing places read from two views with different camera offsets (main reference and the user's close-up):
    # the left figure level with the centre, the right one towards the front, the third one behind on the left.
    # All three dreamers share one form, the slant-cut hood, with no face (user decision 2026-10-03: the third one
    # used to wear an egg mask with two eyes; the eyes and then the egg head were removed).
    for dx, dy in ((-1.8, -0.2), (1.6, -0.95), (-1.0, 1.2)):
        ln = math.hypot(dx, dy)
        _dreamer(g, dx, dy, (dx / ln, dy / ln))
    objs.append(g.to_object("COT_Statue_Figures", coll, materials, dict(props, cot_part="figures")))

    g = Geo()
    g.use("statue")                                           # thin rods between the dish and the lower petals
    for i in range(6):
        a = -math.pi / 2 + TAU * (i + 0.42) / 6
        rr = 2.15
        g.revolve([(0.055, 1.95), (0.045, 2.1), (0.045, 3.95), (0.07, 4.05)], segs=8, m=place(rr * math.cos(a), rr * math.sin(a), 0))
    objs.append(g.to_object("COT_Statue_Rods", coll, materials, dict(props, cot_part="rods")))
    return [o for o in objs if o is not None]
