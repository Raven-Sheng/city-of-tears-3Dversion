"""Stage 3 structural kit: pure geometry builders (no scene access).

Conventions: kit parts stand on z = 0 at the origin and face -Y (toward the viewer of the master map); depth
grows into +Y. `g` is a cot_geo.Geo; functions that return a Geo are meant for Session.kit() (shared datablocks).
Evidence for each part is noted in its docstring; depth, backs and hidden joints are level-C completion.
"""
import math

from cot_geo import Geo, IronCurves, TAU, bez, fbm, lerp, place, rng, spiral_pts
from mathutils import Vector


# ============================================================================ arches and walls
def arch_profile(w, kind="round", rise=None, n=10):
    """Arch soffit from the right springing (w/2, 0) over the crown to the left springing (-w/2, 0)."""
    hw = w / 2
    if kind == "pointed":
        r = rise if rise else 0.9 * w
        if r < hw * 1.02:                                 # depressed pointed arch: soft point, no vertical springing
            m = 2 * n
            return [(hw * (1 - 2 * i / m), r * (1 - abs(1 - 2 * i / m) ** 1.6)) for i in range(m + 1)]
        radius = (hw * hw + r * r) / (2 * hw)
        cx = hw - radius
        a1 = math.atan2(r, -cx)
        right = [(cx + radius * math.cos(a1 * i / n), radius * math.sin(a1 * i / n)) for i in range(n + 1)]
        return right + [(-x, z) for x, z in reversed(right[:-1])]
    if kind == "flat":
        r = rise if rise else 0.3 * w
        return [(hw * math.cos(math.pi * i / (2 * n)), r * math.sin(math.pi * i / (2 * n))) for i in range(2 * n + 1)]
    if kind == "cusp":                                   # trefoil: three round lobes meeting in two cusps (06_Right_City interiors)
        r = rise if rise else 0.62 * w
        m = 15
        pts = []
        for i in range(2 * m + 1):
            a = math.pi * i / (2 * m)
            lobe = 0.74 + 0.26 * abs(math.sin(3 * a)) ** 0.5
            if i in (0, 2 * m):
                pts.append((hw * math.cos(a), 0.0))
            else:
                pts.append((hw * math.cos(a) * lobe, r * math.sin(a) * lobe))
        return pts
    return [(hw * math.cos(math.pi * i / (2 * n)), hw * math.sin(math.pi * i / (2 * n))) for i in range(2 * n + 1)]


def arch_rise(w, kind="round", rise=None):
    if kind == "pointed":
        return rise if rise else 0.9 * w
    if kind == "flat":
        return rise if rise else 0.3 * w
    if kind == "cusp":
        return (rise if rise else 0.62 * w)
    return w / 2


def arcade(g, x0, x1, z0, z1, y0, y1, openings, m=None):
    """Wall slab in the local XZ plane pierced by arched openings: (cx, width, spring z, kind, rise, sill z or None)."""
    ops = sorted(openings)
    if not ops:
        g.box(x0, x1, y0, y1, z0, z1, m=m)
        return
    edges = [x0] + [((a[0] + a[1] / 2) + (b[0] - b[1] / 2)) / 2 for a, b in zip(ops, ops[1:])] + [x1]
    for (xa, xb), (cx, w, spring, kind, rise, sill) in zip(zip(edges, edges[1:]), ops):
        sill = z0 if sill is None else sill
        if sill > z0 + 1e-4:
            g.box(xa, xb, y0, y1, z0, sill, m=m)
        hw = w / 2
        spring = max(spring, sill + 0.05)
        pts = [(xa, sill), (xa, z1), (xb, z1), (xb, sill), (cx + hw, sill)]
        pts += [(cx + px, spring + pz) for px, pz in arch_profile(w, kind, rise)]
        pts += [(cx - hw, sill)]
        g.prism(pts, y0, y1, m=m)


def arch_trim(g, cx, w, spring, base, kind="round", rise=None, y=0.0, r=0.09, m=None, segs=6):
    """Moulding round an opening: both jambs and the arch as one bead."""
    hw = w / 2
    path = [(cx + hw, y, base)] + [(cx + px, y, spring + pz) for px, pz in arch_profile(w, kind, rise)] + [(cx - hw, y, base)]
    g.tube(path, r, segs=segs, ref=(0, 1, 0), m=m)


def slab(g, x0, x1, y0, y1, z, t=0.5, key="floor", lip=("front",), trim="trim", m=None, drops=True):
    """Floor / platform slab with a rounded nosing and a row of pendant points on the exposed edges
    (A: every platform edge in the interior references carries a moulded, toothed fascia)."""
    if x1 - x0 < 1e-3 or y1 - y0 < 1e-3:
        return
    g.use(key)
    g.box(x0, x1, y0, y1, z - t, z, m=m)
    g.use(trim)
    edges = {"front": ((x0, y0), (x1, y0)), "back": ((x0, y1), (x1, y1)), "left": ((x0, y0), (x0, y1)), "right": ((x1, y0), (x1, y1))}
    for side in lip:
        (ax, ay), (bx, by) = edges[side]
        g.tube([(ax, ay, z - 0.11), (bx, by, z - 0.11)], 0.13, segs=6, m=m)
        g.tube([(ax, ay, z - t + 0.07), (bx, by, z - t + 0.07)], 0.085, segs=6, m=m)
        if drops:
            ln = math.hypot(bx - ax, by - ay)
            cnt = max(1, int(round(ln / 1.1)))
            for i in range(cnt):
                f = (i + 0.5) / cnt
                px, py = lerp(ax, bx, f), lerp(ay, by, f)
                g.spike((px, py, z - t + 0.02), (px, py, z - t - 0.3), 0.07, segs=4, m=m)


def corbel(g, x, y, z, size=0.5, key="trim", m=None, facing=-1):
    """Scroll bracket under a slab edge (pointing toward -Y when facing = -1)."""
    g.use(key)
    pts = [(0.0, 0.0), (size, 0.0), (size * 0.92, -size * 0.3), (size * 0.55, -size * 0.55), (size * 0.2, -size * 0.95), (0.0, -size * 1.2)]
    mm = place(x, y, z, rz=math.pi / 2 * (1 if facing < 0 else -1))
    g.prism(pts, -0.12, 0.12, m=(m @ mm) if m is not None else mm)


def rock(g, x0, x1, y0, y1, z0, z1, amp=None, seed=0, cell=2.4, key="rock", rounding=0.16, freq=0.17):
    """Rock mass: a box whose surface is displaced by continuous noise and whose corners are pulled in."""
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    g.use(key)
    c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    h = Vector(((x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2))
    if min(h) < 1e-3:
        return
    if amp is None:
        amp = min(2.6, 0.1 * max(h) * 2 + 0.5)
    amp = min(amp, 0.6 * min(h))
    n = [max(2, min(22, int(round(2 * hh / cell)))) for hh in h]

    def move(p):
        d = Vector(((p.x - c.x) / h.x, (p.y - c.y) / h.y, (p.z - c.z) / h.z))
        pull = 1.0 - rounding * max(0.0, (d.length - 1.0) / 0.732) ** 1.3
        q = c + Vector(((p.x - c.x) * pull, (p.y - c.y) * pull, (p.z - c.z) * pull))
        out = (q - c)
        out = out.normalized() if out.length > 1e-6 else Vector((0, 0, 1))
        nval = fbm(q.x * freq + seed * 1.7, q.y * freq - seed * 0.9, q.z * freq + seed * 0.3, 3)
        nval += 0.45 * fbm(q.x * freq * 3.1 - seed, q.y * freq * 3.1 + seed * 0.5, q.z * freq * 3.1, 2)
        nval += 0.2 * fbm(q.x * freq * 7.3 + seed * 0.7, q.y * freq * 7.3 - seed, q.z * freq * 7.3 + seed * 1.3, 2)
        return q + out * nval * amp

    lo, hi = (x0, y0, z0), (x1, y1, z1)
    for axis in range(3):
        u, v = [a for a in range(3) if a != axis]
        for side in (0, 1):
            rows = []
            for i in range(n[u] + 1):
                row = []
                for j in range(n[v] + 1):
                    p = [0.0, 0.0, 0.0]
                    p[axis] = hi[axis] if side else lo[axis]
                    p[u] = lo[u] + (hi[u] - lo[u]) * i / n[u]
                    p[v] = lo[v] + (hi[v] - lo[v]) * j / n[v]
                    row.append(move(Vector(p)))
                rows.append(row)
            g.grid(rows)


def stalactite(g, x, y, z, length, r, seed=0, key="rock"):
    g.use(key)
    rand = rng(seed + 3)
    lean = (rand(-0.08, 0.08) * length, rand(-0.08, 0.08) * length)
    prof = [(r, 0.0), (r * 0.72, -0.25 * length), (r * 0.4, -0.6 * length), (r * 0.16, -0.86 * length), (0.012, -length)]
    rows = []
    for k, (rr, dz) in enumerate(prof):
        f = k / (len(prof) - 1)
        rows.append([(x + lean[0] * f + rr * math.cos(TAU * i / 6 + seed), y + lean[1] * f + rr * math.sin(TAU * i / 6 + seed), z + dz) for i in range(6)])
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)


def rock_roof(g, x0, x1, y0, y1, z_fn, z_top, step=1.0, amp=0.6, seed=0, key="rock", freq=0.35):
    """Cave roof as one rock slab: its underside follows z_fn(x) with noise across x and y, its top is flat at z_top.
    One closed mesh, so a section seen from the front shows one roof line instead of the joints of many blocks."""
    g.use(key)
    nx = max(2, int(math.ceil((x1 - x0) / step)))
    ny = max(2, int(math.ceil((y1 - y0) / step)))
    rows = []
    for i in range(nx + 1):
        x = lerp(x0, x1, i / nx)
        ring = []
        for j in range(ny + 1):
            y = lerp(y0, y1, j / ny)
            n = fbm(x * freq + seed * 1.3, y * freq - seed * 0.7, seed * 0.31, 3)
            ring.append((x, y, min(z_top - 0.3, z_fn(x) + amp * n)))
        ring += [(x, y1, z_top), (x, y0, z_top)]
        rows.append(ring)
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)


def rock_sheet(g, x0, x1, z0, z1, y_fn, y_out, step=0.5, key="rock", front=False):
    """Cave wall as one closed rock slab seen from the front: its inner face lies at y_fn(x, z), its outer face is flat at
    y_out (a number, or a function of (x, z) for a rough face; behind it for a back wall, in front of it with front=True). A face that comes forward where the cave ends
    draws the cave's outline in a section, without the joints of separate wall blocks."""
    g.use(key)
    nx = max(2, int(math.ceil((x1 - x0) / step)))
    nz = max(2, int(math.ceil((z1 - z0) / step)))
    zs = [lerp(z0, z1, k / nz) for k in range(nz + 1)]
    if not front:
        zs = zs[::-1]
    rows = []
    for i in range(nx + 1):
        x = lerp(x0, x1, i / nx)
        ring = [(x, y_fn(x, z), z) for z in zs]
        if callable(y_out):                                     # a rough outer face as well
            ring += [(x, y_out(x, z), z) for z in zs[::-1]]
        else:
            ring += [(x, y_out, zs[-1]), (x, y_out, zs[0])]
        rows.append(ring)
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)


def stalactite_field(g, x0, x1, y0, y1, z_fn, count, seed=0, lmin=0.8, lmax=3.5, key="rock"):
    rand = rng(seed * 13 + 7)
    for i in range(count):
        x, y = rand(x0, x1), rand(y0, y1)
        ln = lmin + (lmax - lmin) * rand() ** 2.0
        stalactite(g, x, y, z_fn(x, y) + 0.3, ln, 0.12 + 0.11 * ln, seed=seed * 101 + i, key=key)


def spike_rail(g, p0, p1, z, h=0.95, step=0.5, key="iron", heavy=4, spike=0.55):
    """Balcony railing of plain bars with spear points and heavier turned posts (A: 03_Left_City right_upper, 07_Interior)."""
    g.use(key)
    ax, ay = p0
    bx, by = p1
    length = math.hypot(bx - ax, by - ay)
    if length < 0.2:
        return
    n = max(1, int(round(length / step)))
    g.tube([(ax, ay, z + h), (bx, by, z + h)], 0.045, segs=5)
    g.tube([(ax, ay, z + 0.12), (bx, by, z + 0.12)], 0.04, segs=5)
    for i in range(n + 1):
        t = i / n
        x, y = lerp(ax, bx, t), lerp(ay, by, t)
        big = (i % heavy == 0) or i == n
        if big:
            g.revolve([(0.075, 0.0), (0.09, 0.06), (0.045, 0.16), (0.045, h - 0.1), (0.085, h - 0.04), (0.06, h + 0.05)], segs=6, m=place(x, y, z))
            g.spike((x, y, z + h + 0.04), (x, y, z + h + spike * 1.7), 0.06, segs=5, bulb=1.0)
        else:
            g.tube([(x, y, z + 0.12), (x, y, z + h)], 0.022, segs=4, cap=False)
            g.spike((x, y, z + h), (x, y, z + h + spike * 0.55), 0.03, segs=4)


def chain(g, x, y, z0, z1, r=0.035, key="chain", pitch=0.34):
    """Hanging chain as a beaded rod (links read at distance, cheap up close)."""
    g.use(key)
    n = max(2, int(abs(z1 - z0) / (pitch / 2)))
    path = [(x, y, lerp(z0, z1, i / n)) for i in range(n + 1)]
    radii = [r * (1.9 if i % 2 else 0.8) for i in range(n + 1)]
    g.tube(path, radii, segs=5, ref=(0, 1, 0))


def chevron_panel(g, x0, x1, y, z0, z1, pitch=0.85, key="trim", back="wall_deep", depth=0.1):
    """Herringbone wall of the lift shafts (A: 08_Tower step7 / step3, 01_Soul_Sanctuary bottom1, 06_Right_City step2)."""
    g.use(back)
    g.box(x0, x1, y, y + 0.14, z0, z1)
    g.use(key)
    cx, hw = (x0 + x1) / 2, (x1 - x0) / 2
    drop = min(0.55, hw * 0.55)
    th = math.atan2(drop, hw)
    ln = math.hypot(hw, drop)
    z = z0 + drop + 0.1
    while z < z1 - 0.1:
        g.box(0.0, ln, -depth, 0.0, -0.055, 0.055, m=place(cx, y, z, ry=th))
        g.box(0.0, ln, -depth, 0.0, -0.055, 0.055, m=place(cx, y, z, ry=math.pi - th))
        z += pitch
    g.tube([(cx, y - depth * 0.6, z0), (cx, y - depth * 0.6, z1)], 0.06, segs=5)


# ============================================================================ kit parts (return a Geo)
def k_column(h, r=0.15, key="trim"):
    """Slender shaft with a moulded foot and a segmented (noded) capital (A: arcades in 04_Bridges, 05_Streets, 11_Lower_City)."""
    g = Geo().use(key)
    prof = [(r * 2.3, 0.0), (r * 2.3, 0.09), (r * 1.5, 0.17), (r * 1.75, 0.3), (r * 1.1, 0.42), (r, 0.62),
            (r, h - 0.8), (r * 1.5, h - 0.72), (r * 1.08, h - 0.62), (r * 1.62, h - 0.5), (r * 1.12, h - 0.4),
            (r * 1.9, h - 0.22), (r * 2.4, h - 0.07), (r * 2.4, h)]
    g.revolve(prof, segs=10)
    return g


def k_window_lancet(w, h, glass="glass_blue", tracery=True, web=False, frame="window_frame"):
    """Pointed window with a mullion, two sub-lights and an oculus (A: 11_Lower_City middle / upper, 03_Left_City left_upper)."""
    g = Geo()
    hw = w / 2
    rise = min(0.95 * w, h * 0.45)
    spring = h - rise
    prof = arch_profile(w, "pointed", rise, n=8)
    g.use(glass)
    g.prism([(-hw, 0.0), (hw, 0.0)] + [(x, spring + z) for x, z in prof], 0.03, 0.09)
    g.use(frame)
    fr = 0.03 * w + 0.035
    g.tube([(hw, 0, 0)] + [(x, 0, spring + z) for x, z in prof] + [(-hw, 0, 0)], fr, segs=6, ref=(0, 1, 0))
    g.box(-hw - fr * 1.6, hw + fr * 1.6, -0.1, 0.16, -0.12, 0.0)
    thin = fr * 0.55
    if web:                                              # cobweb tracery (A: 06_Right_City step1, 08_Tower step6)
        for k in range(5):
            a = math.pi * (k + 1) / 6
            ex, ez = hw * 0.96 * math.cos(a), min(rise * 0.98, hw * 1.5 * math.sin(a))
            g.tube([(0, 0, spring * 0.55), (ex, 0, spring * 0.55 + ez + spring * 0.25)], thin, segs=4)
        for f in (0.35, 0.62, 0.86):
            g.tube([(hw * f * math.cos(math.pi * i / 10), 0, spring * 0.55 + hw * 1.3 * f * math.sin(math.pi * i / 10)) for i in range(11)], thin, segs=4, ref=(0, 1, 0))
        g.tube([(-hw, 0, spring * 0.55), (hw, 0, spring * 0.55)], thin, segs=4)
        g.tube([(0, 0, 0), (0, 0, spring * 0.55)], thin, segs=4)
    elif tracery:
        g.tube([(0, 0, 0), (0, 0, spring + rise * 0.3)], thin, segs=5)
        sub = arch_profile(hw, "pointed", rise * 0.5, n=5)
        for sx in (-1, 1):
            g.tube([(sx * hw / 2 + x, 0, spring - 0.05 + z) for x, z in sub], thin, segs=5, ref=(0, 1, 0))
        g.ring_arc((0, 0, spring + rise * 0.5), 0.15 * w, 0, TAU, thin, n=12, plane="XZ", segs=5)
        g.tube([(-hw, 0, spring * 0.5), (hw, 0, spring * 0.5)], thin, segs=4)
    g.spike((0, 0, h + fr * 0.5), (0, 0, h + 0.22 * w + 0.15), fr * 0.9, segs=5, bulb=0.9)
    return g


def k_window_tall(w, h, glass="glass_white", bars=2):
    """Tall plain lancet with horizontal bars (A: cold white windows in 01_Soul_Sanctuary bottom / core, 08_Tower step2)."""
    g = Geo()
    hw = w / 2
    rise = min(1.3 * w, h * 0.4)
    spring = h - rise
    prof = arch_profile(w, "pointed", rise, n=8)
    g.use(glass)
    g.prism([(-hw, 0.0), (hw, 0.0)] + [(x, spring + z) for x, z in prof], 0.03, 0.09)
    g.use("window_frame")
    fr = 0.03 * w + 0.05
    g.tube([(hw, 0, 0)] + [(x, 0, spring + z) for x, z in prof] + [(-hw, 0, 0)], fr, segs=6, ref=(0, 1, 0))
    for k in range(bars):
        z = spring * (k + 1) / (bars + 1)
        g.tube([(-hw, 0, z), (hw, 0, z)], fr * 0.5, segs=4)
    g.tube([(0, 0, 0), (0, 0, h - fr)], fr * 0.5, segs=4)
    return g


def k_oval(w, h, pane="mirror", ribs=4, beads=18, frame="trim_pale"):
    """Oval frame with a beaded rim and a ribbed pane (A: mirrors in 01_Soul_Sanctuary bottom1 / left / middle1; windows in 06_Right_City elevator)."""
    g = Geo()
    rx, rz = w / 2, h / 2
    g.use(pane)
    rows = []
    for k in range(5):
        a = -math.pi / 2 + math.pi * k / 4
        s = max(0.03, math.cos(a))
        rows.append([(rx * 0.96 * s * math.cos(TAU * i / 24), 0.06 + 0.05 * math.sin(a), rz + rz * 0.96 * s * math.sin(TAU * i / 24)) for i in range(24)])
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)
    g.use(frame)
    fr = 0.045 * w + 0.03
    for scale, rr in ((1.0, fr), (1.16, fr * 0.55)):
        pts = [(rx * scale * math.cos(TAU * i / 28), 0.0, rz + rz * (scale * 0.5 + 0.5 if scale > 1 else 1.0) * math.sin(TAU * i / 28)) for i in range(28)]
        rows = []
        for i in range(28):
            p = Vector(pts[i])
            t = (Vector(pts[(i + 1) % 28]) - Vector(pts[i - 1])).normalized()
            b = t.cross(Vector((0, 1, 0)))
            rows.append([p + Vector((0, 1, 0)) * (math.cos(TAU * s / 6) * rr) + b * (math.sin(TAU * s / 6) * rr) for s in range(6)])
        rows.append(rows[0])
        g.grid(rows, close_u=True)
    for i in range(beads):
        a = TAU * i / beads
        g.ellipsoid((rx * 1.08 * math.cos(a), 0.0, rz + rz * 1.04 * math.sin(a)), (fr * 0.75, fr * 0.75, fr * 0.75), segs=6, steps=4)
    thin = fr * 0.5
    g.tube([(0, 0.0, rz - rz * 0.92), (0, 0.0, rz + rz * 0.92)], thin, segs=4)
    for k in range(1, ribs + 1):                          # chevron ribs, the same grammar as the leaf windows
        t = k / (ribs + 1)
        zc = h * t
        half = rx * 0.9 * math.sqrt(max(0.0, 1 - ((zc - rz) / rz) ** 2))
        g.tube([(-half, 0.0, zc - 0.08 * h), (0, 0.0, zc + 0.03 * h), (half, 0.0, zc - 0.08 * h)], thin, segs=4)
    g.spike((0, 0, h + fr), (0, 0, h + 0.3 * w + 0.2), fr, segs=5, bulb=1.0)
    g.spike((0, 0, -fr), (0, 0, -0.18 * w - 0.12), fr * 0.9, segs=5, bulb=0.8)
    return g


def k_shelf_arch(w, h, seed=0, kind="round", back="wall_deep", frame="trim_purple"):
    """Arched bookcase niche (A: 06_Right_City step1 / step2 / step3, 13_Lighting/Lighting_04)."""
    g = Geo()
    hw = w / 2
    rise = arch_rise(w, kind)
    spring = h - rise
    prof = arch_profile(w, kind, None, n=8)
    g.use(back)
    g.prism([(-hw, 0.0), (hw, 0.0)] + [(x, spring + z) for x, z in prof], 0.1, 0.2)
    g.use(frame)
    g.tube([(hw, 0, 0)] + [(x, 0, spring + z) for x, z in prof] + [(-hw, 0, 0)], 0.09, segs=6, ref=(0, 1, 0))
    rand = rng(seed + 17)
    z = 0.12
    while z < spring - 0.05:
        g.use(frame)
        g.box(-hw + 0.06, hw - 0.06, -0.04, 0.14, z - 0.045, z)
        g.use("pot")
        x = -hw + 0.12
        while x < hw - 0.2:
            bw = rand(0.07, 0.15)
            if rand() > 0.18:
                g.box(x, x + bw, 0.0, 0.11, z, z + rand(0.28, 0.46))
            x += bw + 0.012
        z += 0.62
    return g


def k_portrait(w=0.9, h=1.3):
    """Small oval portrait (A: corridor in 08_Tower step3)."""
    g = Geo()
    g.use("mirror")
    g.ellipsoid((0, 0.06, 0), (w / 2 * 0.9, 0.04, h / 2 * 0.9), segs=14, steps=6)
    g.use("trim")
    g.ring_arc((0, 0, 0), 1.0, 0, TAU, 0.07, n=20, plane="XZ", segs=6, m=place(s=(w / 2, 1.0, h / 2)))
    g.spike((0, 0, h / 2), (0, 0, h / 2 + 0.3), 0.05, segs=5, bulb=1.0)
    return g


def k_car_spire(w=2.1, d=1.9):
    """Lift car: open cage under a steep spired roof with corner pinnacles (A: 03_Left_City left_bottom / left_middle, 08_Tower step3, 11_Lower_City upper)."""
    g = Geo()
    hw, hd = w / 2, d / 2
    g.use("trim")
    g.box(-hw, hw, -hd, hd, 0.0, 0.16)
    g.box(-hw * 1.06, hw * 1.06, -hd * 1.06, hd * 1.06, 2.42, 2.6)
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.revolve([(0.075, 0.16), (0.06, 0.3), (0.045, 0.5), (0.045, 2.2), (0.08, 2.3), (0.06, 2.42)], segs=6, m=place(sx * (hw - 0.09), sy * (hd - 0.09), 0))
            g.spike((sx * (hw - 0.05), sy * (hd - 0.05), 2.6), (sx * (hw - 0.05), sy * (hd - 0.05), 3.5), 0.07, segs=5, bulb=1.1)
    prof = arch_profile(w - 0.3, "pointed", 0.85, n=6)
    for sy in (-1, 1):
        g.tube([(x, sy * (hd - 0.09), 1.55 + z) for x, z in prof], 0.04, segs=5, ref=(0, 1, 0))
    prof = arch_profile(d - 0.3, "pointed", 0.85, n=6)
    for sx in (-1, 1):
        g.tube([(sx * (hw - 0.09), y, 1.55 + z) for y, z in prof], 0.04, segs=5, ref=(1, 0, 0))
    g.use("iron")
    for sx in (-1, 1):                                    # low side grilles
        g.tube([(sx * (hw - 0.09), -hd + 0.1, 0.85), (sx * (hw - 0.09), hd - 0.1, 0.85)], 0.03, segs=4)
        for k in range(1, 5):
            y = -hd + 2 * hd * k / 5
            g.tube([(sx * (hw - 0.09), y, 0.16), (sx * (hw - 0.09), y, 0.85)], 0.02, segs=4, cap=False)
    g.use("louvre")
    roof = [(hw * 1.12, 2.6), (hw * 1.0, 2.78), (hw * 0.7, 3.15), (hw * 0.42, 3.75), (hw * 0.2, 4.5), (0.06, 5.2)]
    g.revolve(roof, segs=8, sx=1.0, sy=hd / hw, m=place(rz=TAU / 16))
    g.use("iron")
    g.spike((0, 0, 5.15), (0, 0, 6.1), 0.07, segs=5, bulb=1.2)
    g.ring_arc((0, 0, 6.22), 0.14, 0, TAU, 0.03, n=12, plane="XZ", segs=5)
    g.use("lamp")
    g.ellipsoid((0, 0, 2.15), (0.13, 0.13, 0.16), segs=8, steps=6)
    return g


CAR_SPIRE_TOP = 6.36


def k_car_dome(r=1.45):
    """Round lift car under a ribbed dome, lattice arches on three sides (A: 06_Right_City/Right_City_elevator.jpg)."""
    g = Geo()
    g.use("trim_purple")
    g.revolve([(r * 1.08, 0.0), (r * 1.1, 0.14), (r * 0.98, 0.24)], segs=20)
    g.revolve([(r * 1.02, 2.5), (r * 1.1, 2.6), (r * 1.1, 2.74), (r * 1.0, 2.82)], segs=20)
    for k in range(6):
        a = TAU * (k + 0.5) / 6
        g.revolve([(0.085, 0.24), (0.05, 0.45), (0.05, 2.3), (0.09, 2.42), (0.07, 2.5)], segs=6, m=place(r * 0.92 * math.cos(a), r * 0.92 * math.sin(a), 0))
    g.use("iron")
    for k in range(6):                                    # lattice arch between each pair of posts
        a0, a1 = TAU * (k + 0.5) / 6, TAU * (k + 1.5) / 6
        pts = []
        for i in range(9):
            a = lerp(a0, a1, i / 8)
            pts.append((r * 0.92 * math.cos(a), r * 0.92 * math.sin(a), 1.75 + 0.62 * math.sin(math.pi * i / 8)))
        g.tube(pts, 0.035, segs=5, ref=(0, 0, 1))
        am = (a0 + a1) / 2
        if k % 2 == 0:
            for f in (-0.28, 0.0, 0.28):
                a = am + f * (a1 - a0)
                g.tube([(r * 0.92 * math.cos(a), r * 0.92 * math.sin(a), 0.24), (r * 0.92 * math.cos(a), r * 0.92 * math.sin(a), 1.9)], 0.02, segs=4, cap=False)
            g.tube([(r * 0.92 * math.cos(lerp(a0, a1, i / 6)), r * 0.92 * math.sin(lerp(a0, a1, i / 6)), 1.0) for i in range(7)], 0.025, segs=4, ref=(0, 0, 1))
    g.use("louvre")
    g.revolve([(r * 1.0, 2.82)] + [(r * math.cos(math.pi / 2 * i / 8), 2.82 + r * 0.92 * math.sin(math.pi / 2 * i / 8)) for i in range(1, 8)] + [(0.1, 2.82 + r * 0.92)], segs=24)
    g.use("trim_purple")
    for k in range(8):
        a = TAU * k / 8
        g.tube([(r * 1.01 * math.cos(math.pi / 2 * i / 8) * math.cos(a), r * 1.01 * math.cos(math.pi / 2 * i / 8) * math.sin(a), 2.82 + r * 0.93 * math.sin(math.pi / 2 * i / 8))
                for i in range(9)], 0.045, segs=5, ref=(0, 0, 1))
    g.use("iron")
    top = 2.82 + r * 0.92
    g.revolve([(0.16, top - 0.02), (0.2, top + 0.1), (0.08, top + 0.22), (0.12, top + 0.34), (0.03, top + 0.5)], segs=8)
    g.ring_arc((0, 0, top + 0.72), 0.22, 0, TAU, 0.04, n=14, plane="XZ", segs=5)
    g.use("lamp_pink")
    g.ellipsoid((0, 0, 2.2), (0.14, 0.14, 0.18), segs=8, steps=6)
    return g


CAR_DOME_TOP = 2.82 + 1.45 * 0.92 + 0.94


def louvre_dome(g, rx, ry, h, a0=0.0, a1=TAU, ribs=10, spikes=True, finial=True, m=None, slat=0.19, cap_base=True):
    """Louvred dome or half-dome hood with ribs and spear points (A: 05_Streets middle / right, 07_Interior bottom_left, 11_Lower_City upperbridge, 01_Soul_Sanctuary core_upper).

    Base on z = 0; a0..a1 measured from +X toward +Y. A partial dome is closed through its axis, so it is a solid.
    """
    closed = abs((a1 - a0) - TAU) < 1e-6
    segs = max(10, int(34 * (a1 - a0) / TAU))
    count = segs if closed else segs + 1

    def pt(a, phi, f=1.0):
        return (rx * f * math.cos(phi) * math.cos(a), ry * f * math.cos(phi) * math.sin(a), h * f * math.sin(phi))

    g.use("louvre_core")
    rows = []
    steps = 9
    for k in range(steps + 1):
        phi = math.pi / 2 * min(k / steps, 0.985)
        row = [pt(a0 + (a1 - a0) * i / segs, phi, 0.95) for i in range(count)]
        if not closed:
            row.append((0.0, 0.0, h * 0.95 * math.sin(phi)))
        rows.append(row)
    g.grid(rows, close_u=True, cap_start=cap_base, cap_end=True, m=m)
    g.use("louvre")
    n_sl = max(4, int(h / slat))
    for j in range(n_sl):
        phi = math.asin(min(0.97, (j + 0.5) / n_sl))
        dphi = 0.32 / n_sl * math.pi / 2
        ring = lambda ph, f: [pt(a0 + (a1 - a0) * i / segs, ph, f) for i in range(count)]
        g.grid([ring(phi - dphi, 0.95), ring(phi - dphi, 1.01), ring(phi + dphi, 1.0), ring(phi + dphi, 0.95), ring(phi - dphi, 0.95)], close_u=closed, m=m)
    g.use("louvre_frame")
    n_rib = ribs if closed else max(2, int(round(ribs * (a1 - a0) / TAU)) + 1)
    rib_angles = [a0 + (a1 - a0) * (k / n_rib if closed else k / (n_rib - 1)) for k in range(n_rib)]
    for a in rib_angles:
        g.tube([pt(a, math.pi / 2 * i / 10, 1.02) for i in range(11)], 0.075, segs=5, ref=(0, 0, 1), m=m)
    g.tube([pt(a0 + (a1 - a0) * i / segs, 0.0, 1.03) for i in range(count)] + ([pt(a0, 0.0, 1.03)] if closed else []), 0.1, segs=6, ref=(0, 0, 1), m=m)
    if spikes:
        g.use("iron")
        for k, a in enumerate(rib_angles):
            for phi, ln in ((math.radians(34), 0.55), (math.radians(62), 0.8)):
                base = Vector(pt(a, phi, 1.02))
                g.spike(base, base + Vector((0, 0, ln)), 0.045, segs=5, bulb=0.8, m=m)
    if finial:
        g.use("iron")
        g.revolve([(0.2, h * 0.97), (0.26, h + 0.08), (0.1, h + 0.2), (0.15, h + 0.33), (0.04, h + 0.5)], segs=8, m=m)
        g.spike((0, 0, h + 0.45), (0, 0, h + 1.5), 0.08, segs=5, bulb=0.9, m=m)


def k_lamp_string(drops=3, length=3.0, lamp="lamp"):
    """Hanging string of tear-drop lamps (A: 13_Lighting/Lighting_02, 11_Lower_City middle, 04_Bridges). Hangs down from z = 0."""
    g = Geo()
    g.use("chain")
    g.tube([(0, 0, 0), (0, 0, -length)], 0.018, segs=4)
    for k in range(drops):
        z = -length * (k + 1) / drops
        g.use("iron")
        g.revolve([(0.02, z + 0.32), (0.07, z + 0.27), (0.085, z + 0.21), (0.03, z + 0.2)], segs=8)
        g.use(lamp)
        g.revolve([(0.02, z + 0.2), (0.09, z + 0.13), (0.11, z + 0.05), (0.08, z - 0.03), (0.02, z - 0.07)], segs=10)
    return g


def k_wall_lamp(lamp="lamp", kind="globe"):
    """Wall bracket lamp: scroll arm and a hanging globe (A: wall lamps in 02_Marissa, 06_Right_City step1). Mounts on the wall at the origin, faces -Y."""
    g = Geo()
    g.use("iron")
    path = [(0, 0, 0.0), (0, -0.16, 0.12), (0, -0.36, 0.14), (0, -0.48, 0.02), (0, -0.5, -0.12)]
    g.tube(path, 0.03, segs=5, ref=(1, 0, 0))
    g.ring_arc((0, -0.2, -0.04), 0.12, 0, TAU * 0.8, 0.02, n=12, plane="YZ", segs=4)
    g.revolve([(0.02, 0.0), (0.07, -0.04), (0.09, -0.1), (0.03, -0.11)], segs=8, m=place(0, -0.5, -0.12))
    g.use(lamp)
    if kind == "heart":                                   # two lobes drawn together: the heart lamps of Marrisa_home.jpg
        for sx in (-1, 1):
            g.ellipsoid((sx * 0.07, -0.5, -0.34), (0.1, 0.1, 0.13), segs=8, steps=6)
        g.revolve([(0.12, -0.38), (0.06, -0.48), (0.01, -0.56)], segs=8, m=place(0, -0.5, 0))
    else:
        g.ellipsoid((0, -0.5, -0.36), (0.14, 0.14, 0.15), segs=10, steps=8)
    return g


def k_orb_post(h=3.4, orbs=3):
    """Lamp standard carrying caged glowing orbs (A: 01_Soul_Sanctuary bottom)."""
    g = Geo()
    g.use("trim_pale")
    g.revolve([(0.26, 0.0), (0.28, 0.08), (0.12, 0.2), (0.07, 0.5), (0.06, h - 0.3), (0.11, h - 0.2), (0.05, h)], segs=8)
    g.spike((0, 0, h), (0, 0, h + 0.7), 0.05, segs=5, bulb=1.0)
    pos = [(0.0, h - 0.75)] if orbs == 1 else [(-0.42, h - 0.9), (0.42, h - 0.9), (0.0, h - 0.15)][:orbs]
    for x, z in pos:
        if abs(x) > 1e-3:
            g.use("trim_pale")
            g.tube([(0, 0, z + 0.25), (x * 0.6, 0, z + 0.42), (x, 0, z + 0.28)], 0.025, segs=4, ref=(0, 1, 0))
        g.use("lamp_white")
        g.ellipsoid((x, 0, z), (0.2, 0.2, 0.2), segs=10, steps=8)
        g.use("trim_pale")
        g.ring_arc((x, 0, z), 0.215, 0, TAU, 0.018, n=14, plane="XZ", segs=4)
        g.ring_arc((x, 0, z), 0.215, 0, TAU, 0.018, n=14, plane="XY", segs=4)
    return g


def k_chandelier(r=1.3, arms=8, lamp="lamp_pink"):
    """Branched chandelier (A: 08_Tower step4 / step5, 06_Right_City peak). Hangs from z = 0; body about 1.6 below."""
    g = Geo()
    g.use("chain")
    g.tube([(0, 0, 0), (0, 0, -1.0)], 0.025, segs=4)
    g.use("iron")
    g.revolve([(0.03, -1.0), (0.12, -1.1), (0.2, -1.3), (0.1, -1.5), (0.16, -1.62), (0.02, -1.85)], segs=10)
    for k in range(arms):
        a = TAU * k / arms
        pts = [(0.12 * math.cos(a), 0.12 * math.sin(a), -1.45), (0.5 * r * math.cos(a), 0.5 * r * math.sin(a), -1.7),
               (0.9 * r * math.cos(a), 0.9 * r * math.sin(a), -1.55), (r * math.cos(a), r * math.sin(a), -1.3)]
        g.tube(pts, 0.022, segs=4, ref=(0, 0, 1))
        g.use(lamp)
        g.ellipsoid((r * math.cos(a), r * math.sin(a), -1.2), (0.09, 0.09, 0.12), segs=8, steps=6)
        g.use("iron")
    return g


def k_banner(w=1.1, h=3.6, cloth="cloth_blue"):
    """Hanging pennant with a shell-and-wings emblem and a forked hem (A: 08_Tower step1, 05_Streets station, 06_Right_City station). Hangs from z = 0."""
    g = Geo()
    hw = w / 2
    g.use(cloth)
    g.prism([(-hw, 0.0), (hw, 0.0), (hw, -h + 0.55), (hw * 0.45, -h + 0.15), (0.0, -h + 0.55), (-hw * 0.45, -h + 0.15), (-hw, -h + 0.55)], -0.03, 0.03)
    g.use("trim")
    g.tube([(-hw - 0.14, 0, 0.04), (hw + 0.14, 0, 0.04)], 0.045, segs=6)
    for sx in (-1, 1):
        g.ellipsoid((sx * (hw + 0.16), 0, 0.04), (0.07, 0.07, 0.07), segs=6, steps=4)
    zc = -h * 0.36
    g.ring_arc((0, -0.035, zc), 1.0, 0, TAU, 0.03, n=14, plane="XZ", segs=4, m=place(s=(0.16, 1.0, 0.24)))
    for sx in (-1, 1):
        for k in range(3):
            g.tube([(sx * 0.14, -0.035, zc + 0.12 - 0.12 * k), (sx * (0.3 + 0.05 * k), -0.035, zc + 0.3 - 0.14 * k), (sx * hw * 0.85, -0.035, zc + 0.18 - 0.2 * k)],
                   0.022, segs=4, ref=(0, 1, 0))
    g.tube([(0, -0.035, zc - 0.24), (0, -0.035, -h + 0.8)], 0.02, segs=4)
    return g


def k_jar(variant=0):
    """Lidded pot / urn (A: 05_Streets left, 03_Left_City left_middle, 06_Right_City elevator_upper)."""
    g = Geo().use("pot")
    if variant == 0:
        prof = [(0.2, 0.0), (0.32, 0.1), (0.38, 0.34), (0.33, 0.58), (0.2, 0.7), (0.24, 0.78), (0.2, 0.82), (0.08, 0.9), (0.1, 0.98), (0.02, 1.02)]
    elif variant == 1:
        prof = [(0.26, 0.0), (0.4, 0.14), (0.42, 0.4), (0.3, 0.6), (0.32, 0.68), (0.12, 0.76), (0.02, 0.8)]
    else:
        prof = [(0.16, 0.0), (0.24, 0.12), (0.27, 0.5), (0.22, 0.9), (0.14, 1.06), (0.17, 1.14), (0.06, 1.2), (0.02, 1.3)]
    g.revolve(prof, segs=12)
    g.use("trim")
    g.ring_arc((0, 0, prof[2][1]), prof[2][0] + 0.01, 0, TAU, 0.025, n=14, plane="XY", segs=4)
    return g


def k_snail(R=0.8, seed=0):
    """Coiled snail shell lying on the ground (A: 05_Streets left / middle, 07_Interior bottom_right, 11_Lower_City bottom)."""
    g = Geo().use("shell")
    path, radii = [], []
    n = 46
    for i in range(n + 1):
        t = i / n
        a = math.pi * 0.5 - t * TAU * 2.4
        rad = R * (0.06 + 0.94 * t ** 1.5) * 0.62
        path.append((rad * math.cos(a), 0.22 * R * (1 - t), R * 0.62 + rad * math.sin(a)))
        radii.append(R * (0.07 + 0.36 * t ** 1.25))
    g.tube(path, radii, segs=10, ref=(0, 1, 0))
    g.use("trim")
    for k in range(7):
        i = int(n * (0.45 + 0.08 * k))
        if i < n:
            p, p2 = Vector(path[i]), Vector(path[i + 1])
            t = (p2 - p).normalized()
            b = t.cross(Vector((0, 1, 0)))
            rr = radii[i] * 1.04
            g.tube([p + Vector((0, 1, 0)) * (math.cos(TAU * s / 10) * rr) + b * (math.sin(TAU * s / 10) * rr) for s in range(11)], 0.022, segs=4, ref=tuple(t))
    return g


def k_bench(w=2.4):
    """Iron bench with scrolled ends and a fan back (A: 05_Streets station, 06_Right_City station, 11_Lower_City upperbridge)."""
    g = Geo()
    hw = w / 2
    g.use("iron")
    g.box(-hw, hw, -0.3, 0.3, 0.5, 0.58)
    for sx in (-1, 1):
        for sy in (-0.24, 0.24):
            g.tube([(sx * (hw - 0.1), sy, 0.0), (sx * (hw - 0.1), sy, 0.5)], 0.04, segs=5)
        g.ring_arc((sx * (hw + 0.02), 0.0, 0.72), 0.2, -math.pi / 2, math.pi * 1.1, 0.035, n=14, plane="YZ", segs=5)
        g.tube([(sx * hw, -0.3, 0.52), (sx * hw, 0.3, 0.52)], 0.04, segs=5)
    for k in range(9):
        x = -hw + 0.2 + (w - 0.4) * k / 8
        top = 1.25 + 0.3 * math.sin(math.pi * k / 8)
        g.tube([(x, 0.28, 0.58), (x * 1.04, 0.34, top)], 0.022, segs=4, cap=False)
    g.tube([(-hw + 0.2 + (w - 0.4) * k / 8 * 1.0, 0.34, 1.25 + 0.3 * math.sin(math.pi * k / 8)) for k in range(9)], 0.035, segs=5, ref=(0, 1, 0))
    g.spike((0, 0.34, 1.55), (0, 0.34, 2.0), 0.04, segs=5, bulb=1.0)
    return g


def k_bell():
    """Station bell on a scrolled bracket post (A: 05_Streets station, 06_Right_City station)."""
    g = Geo()
    g.use("iron")
    g.revolve([(0.16, 0.0), (0.18, 0.06), (0.06, 0.16), (0.045, 2.2)], segs=8)
    g.tube([(0, 0, 2.2), (0.12, 0, 2.5), (0.42, 0, 2.6), (0.6, 0, 2.42)], 0.035, segs=5, ref=(0, 1, 0))
    g.ring_arc((0.26, 0, 2.3), 0.16, 0, TAU * 0.85, 0.022, n=12, plane="XZ", segs=4)
    g.spike((0, 0, 2.2), (0, 0, 2.75), 0.04, segs=5, bulb=1.0)
    g.use("trim")
    g.revolve([(0.03, 2.4), (0.08, 2.34), (0.13, 2.2), (0.16, 2.02), (0.2, 1.94), (0.17, 1.92), (0.0, 1.98)], segs=10, m=place(0.6, 0, 0))
    return g


def k_cluster(seed=0, n=9, R=0.75):
    """Spotted round cluster (A: 09_Bench all, 07_Interior centre / middle_bottom, 04_Bridges left). Grows out of the origin toward +Z."""
    g = Geo()
    rand = rng(seed * 37 + 5)
    g.use("cluster")
    g.ellipsoid((0, 0, R * 0.25), (R * 0.85, R * 0.85, R * 0.6), segs=10, steps=6)
    balls = []
    for k in range(n):
        a = TAU * (k * 0.618 + rand(0, 0.2))
        el = math.radians(rand(8, 78))
        rr = R * rand(0.3, 0.44)
        c = Vector((R * 0.72 * math.cos(el) * math.cos(a), R * 0.72 * math.cos(el) * math.sin(a), R * 0.3 + R * 0.62 * math.sin(el)))
        balls.append((c, rr))
        g.ellipsoid(tuple(c), (rr, rr, rr * 0.92), segs=8, steps=6)
    g.use("cluster_spot")
    for c, rr in balls:
        out = c.normalized()
        side = out.orthogonal().normalized()
        up = out.cross(side)
        for j in range(4):
            a = TAU * j / 4 + rand(0, 1.0)
            d = (out * 0.8 + (side * math.cos(a) + up * math.sin(a)) * rand(0.25, 0.6)).normalized()
            p = c + d * rr * 0.93
            g.ellipsoid(tuple(p), (rr * 0.2, rr * 0.2, rr * 0.2), segs=6, steps=4)
    return g


def k_lobes(seed=0, n=5, R=1.6):
    """Pile of large smooth dark lobes (A: big rounded rock lobes in 05_Streets middle, 07_Interior middle_left)."""
    g = Geo().use("lobe")
    rand = rng(seed * 53 + 11)
    for k in range(n):
        a = TAU * rand()
        d = R * rand(0.0, 0.7)
        rr = R * rand(0.38, 0.62)
        g.ellipsoid((d * math.cos(a), d * math.sin(a) * 0.7, rr * rand(0.5, 1.4)), (rr, rr * rand(0.8, 1.0), rr * rand(0.9, 1.3)), segs=12, steps=8)
    return g


def k_pebbles(seed=0, nx=4, nz=4, size=1.5):
    """Patch of rounded boulders standing proud of a rock face (A: cobbled cavern rim in master B7; C: every stone). Local XZ plane, faces -Y."""
    g = Geo().use("pebble")
    rand = rng(seed * 71 + 3)
    for i in range(nx):
        for j in range(nz):
            x = (i + 0.5 + rand(-0.25, 0.25) + (0.5 if j % 2 else 0.0)) * size
            z = (j + 0.5 + rand(-0.2, 0.2)) * size * 0.8
            g.ellipsoid((x, rand(-0.1, 0.25), z), (size * rand(0.5, 0.66), size * rand(0.32, 0.5), size * rand(0.4, 0.52)), segs=8, steps=5, e=0.75)
    return g


def k_candle_stand(n=3, h=1.5):
    """Candelabrum (A: 08_Tower step9)."""
    g = Geo()
    g.use("iron")
    g.revolve([(0.18, 0.0), (0.2, 0.05), (0.05, 0.14), (0.035, h)], segs=8)
    xs = [0.0] if n == 1 else [(-0.3 + 0.6 * k / (n - 1)) for k in range(n)]
    for x in xs:
        if abs(x) > 1e-3:
            g.tube([(0, 0, h - 0.25), (x * 0.6, 0, h - 0.3), (x, 0, h - 0.08)], 0.022, segs=4, ref=(0, 1, 0))
        g.revolve([(0.02, h - 0.1), (0.07, h - 0.04), (0.05, h)], segs=6, m=place(x, 0, 0))
    g.use("candle")
    for x in xs:
        g.revolve([(0.03, h), (0.03, h + 0.32), (0.012, h + 0.42)], segs=6, m=place(x, 0, 0))
    return g


def k_seat():
    """Round cushioned stool / pouffe (A: 06_Right_City peak)."""
    g = Geo()
    g.use("cushion")
    g.ellipsoid((0, 0, 0.42), (0.62, 0.62, 0.3), segs=14, steps=8, e=0.8)
    g.use("trim_purple")
    g.revolve([(0.5, 0.0), (0.56, 0.08), (0.46, 0.22)], segs=14)
    return g


def k_shelf_stack(seed=0):
    """Stack of boxes and bundles (A: Marrisa_home.jpg right, crates in 06_Right_City elevator_upper)."""
    g = Geo()
    rand = rng(seed + 29)
    z = 0.0
    w = 1.1
    for k in range(4):
        g.use("wood" if k % 2 == 0 else "cloth_purple")
        d = w * rand(0.7, 0.9)
        hh = rand(0.28, 0.42)
        ox = rand(-0.1, 0.1)
        g.ellipsoid((ox, 0, z + hh / 2), (w / 2, d / 2, hh / 2), segs=10, steps=6, e=0.35)
        z += hh * 0.96
        w *= rand(0.82, 0.95)
    return g


def drape(g, x0, x1, y, z_top, z_bot, folds=6, amp=0.16, thick=0.07, key="cloth_purple", gather=None, nz=10, hem=0.3, seed=0, axis="X", nx=None):
    """Curtain with real folds and thickness. gather = (z, factor): tied in toward its middle at height z.

    axis "X": spans x0..x1 at depth y; axis "Y": spans y from x0..x1 at x = y (for side curtains).
    """
    g.use(key)
    rand = rng(seed + 41)
    nx = nx or max(8, folds * 6)
    hems = [hem * (0.3 + 0.7 * abs(math.sin(math.pi * folds * i / nx + 0.7))) * (0.6 + 0.4 * rand()) for i in range(nx + 1)]
    cx = (x0 + x1) / 2
    rows = []
    for j in range(nz + 1):
        v = j / nz
        z_base = lerp(z_top, z_bot, v)
        squeeze, a_scale = 1.0, 0.35 + 0.65 * v
        if gather:
            gz, gf = gather
            d = abs(z_base - gz) / max(0.5, (z_top - z_bot) * 0.3)
            squeeze = 1.0 - (1.0 - gf) * math.exp(-d * d)
        front, back = [], []
        for i in range(nx + 1):
            u = i / nx
            x = cx + (lerp(x0, x1, u) - cx) * squeeze
            wave = amp * a_scale * math.sin(TAU * folds * u * 0.5 + seed) / max(0.4, squeeze)
            z = z_base - (hems[i] * v if j == nz else 0.0)
            if axis == "X":
                front.append((x, y + wave - thick / 2, z))
                back.append((x, y + wave + thick / 2, z))
            else:
                front.append((y + wave - thick / 2, x, z))
                back.append((y + wave + thick / 2, x, z))
        rows.append(front + list(reversed(back)))
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)


def swag(g, x0, x1, y, z, sag=0.8, depth=0.9, thick=0.06, key="cloth_purple", folds=5):
    """Draped valance between two points (A: bunting over the stage in Marissa.jpg, drapes in 06_Right_City peak)."""
    g.use(key)
    n = 14
    rows = []
    for j in range(folds + 1):
        v = j / folds
        front, back = [], []
        for i in range(n + 1):
            u = i / n
            x = lerp(x0, x1, u)
            dz = sag * (0.25 + 0.75 * v) * math.sin(math.pi * u) + depth * v * (0.35 + 0.65 * math.sin(math.pi * u))
            yy = y - 0.12 * math.sin(math.pi * v) * math.sin(math.pi * u)
            front.append((x, yy - thick / 2, z - dz))
            back.append((x, yy + thick / 2, z - dz))
        rows.append(front + list(reversed(back)))
    g.grid(rows, close_u=True, cap_start=True, cap_end=True)


def pattern_relief(g, x0, x1, z0, z1, y, cell=1.1, key="pattern", depth=0.05, kind="damask"):
    """Raised repeating wall pattern, separate from the wall behind it (A: wallpaper in 02_Marissa both images)."""
    g.use(key)
    nx = max(1, int(round((x1 - x0) / cell)))
    nz = max(1, int(round((z1 - z0) / (cell * 1.25))))
    cw, chh = (x1 - x0) / nx, (z1 - z0) / nz
    for i in range(nx):
        for j in range(nz):
            cx = x0 + cw * (i + 0.5 + (0.5 if j % 2 else 0.0))
            if cx > x1 - cw * 0.3:
                continue
            cz = z0 + chh * (j + 0.5)
            m = place(cx, y, cz)
            if kind == "damask":                          # pointed quatrefoil motif
                pts = []
                for k in range(16):
                    a = TAU * k / 16
                    rr = (0.42 if k % 4 == 0 else (0.2 if k % 2 else 0.3))
                    pts.append((cw * rr * math.cos(a), chh * rr * 1.05 * math.sin(a)))
                g.prism(pts, -depth, 0.0, m=m)
            else:                                         # diamond lattice
                g.prism([(cw * 0.42, 0), (0, chh * 0.46), (-cw * 0.42, 0), (0, -chh * 0.46)], -depth, 0.0, m=m)


def winged_shell_relief(g, w, h, m=None, key="relief", dark="wall_deep"):
    """Great winged-shell emblem (A: 06_Right_City/Right_City_elevator_upper.jpg, master B1): an upright banded shell with a
    middle seam between two wings of long overlapping feathers that spread sideways almost to the columns, a short crest of
    blades on top and a pendant under it. Faces -Y; origin at the middle of the bottom edge."""
    g.use(dark)
    g.box(-w / 2, w / 2, 0.0, 0.25, 0.0, h, m=m)
    cz = h * 0.55
    bw = w * 0.12
    bh = bw * 1.55
    by = w * 0.07

    def blade(bx, bz, ang, length, width, y0, sx, rib=True):
        dx, dz = math.cos(ang), math.sin(ang)
        # keep the tip inside the panel
        if dx > 0.05:
            length = min(length, (w * 0.49 - bx) / dx)
        if dz > 0.05:
            length = min(length, (h * 0.985 - bz) / dz)
        elif dz < -0.05:
            length = min(length, (bz - h * 0.02) / -dz)
        up, lo = [], []
        for i in range(13):
            t = i / 12
            half = width * (math.sin(math.pi * min(1.0, t) ** 0.7) ** 0.8 * 0.96 + 0.03)
            ax, az = bx + dx * length * t, bz + dz * length * t
            up.append((ax - dz * half, az + dx * half))
            lo.append((ax + dz * half, az - dx * half))
        pts = up + lo[::-1][1:-1]
        pts = [(sx * px, pz) for px, pz in pts]
        if sx > 0:
            pts = pts[::-1]
        g.prism(pts, y0, y0 + 0.12, m=m)
        if rib:
            g.use(dark)
            g.tube([(sx * (bx + dx * length * t), y0 - 0.01, bz + dz * length * t) for t in (0.05, 0.5, 0.9)], 0.014 * w ** 0.5, segs=4, ref=(0, 1, 0), m=m)
            g.use(key)

    g.use(key)
    # three overlapping rows of feathers per wing: the front row is the longest and spreads almost level (A)
    # broad feathers overlapping like roof tiles: within a row each lower feather lies in front of the one above it,
    # and the lowest row lies in front of the others, so the wing reads as a layered fan, not as rays
    rows = ((5, -0.6, 0.25, -14.0, 22.0, 0.45, 0.13, -0.44),
            (5, 0.0, 0.8, 14.0, 46.0, 0.41, 0.12, -0.3),
            (4, 0.55, 1.05, 40.0, 74.0, 0.31, 0.1, -0.17))
    for n, f0, f1, a0, a1, ln, wd, y0 in rows:
        for k in range(n):
            f = k / (n - 1)
            bz = cz + bh * lerp(f0, f1, f)
            bx = bw * 0.7 * math.sqrt(max(0.05, 1 - ((bz - cz) / (bh * 1.08)) ** 2))
            for sx in (-1, 1):
                blade(bx, bz, math.radians(lerp(a0, a1, f)), w * ln * (1.0 - 0.15 * f), w * wd, y0 + 0.025 * k, sx)
    for k in range(5):                                    # crest of short blades on top of the shell
        ang = math.radians(70 + 10 * k)
        blade(0.0, cz + bh * 0.85, ang, w * (0.13 - 0.02 * abs(k - 2)), w * 0.035, -0.05, 1, rib=False)
    for k in range(3):                                    # pendant under the shell
        ang = math.radians(-90 + 22 * (k - 1))
        blade(0.0, cz - bh * 0.9, ang, h * (0.16 - 0.03 * abs(k - 1)), w * 0.04, -0.1, 1, rib=False)
    g.ellipsoid((0, -0.13, cz - bh - h * 0.17), (w * 0.03, w * 0.03, w * 0.04), segs=8, steps=5, m=m)
    for sx in (-1, 1):                                    # two scrolls curling out under the pendant
        g.ring_arc((sx * w * 0.055, -0.08, cz - bh - h * 0.06), w * 0.035, 0.0, TAU * 0.75, 0.012 * w ** 0.5 + 0.015, n=12, plane="XZ", segs=4, m=m)
    g.ellipsoid((0, -0.3, cz), (bw, by, bh), segs=20, steps=14, m=m)
    g.use(dark)                                           # bands and the middle seam of the shell
    for fz in (-0.5, -0.12, 0.26, 0.62):
        z = cz + bh * fz
        q = math.sqrt(max(0.0, 1 - fz * fz))
        g.tube([(bw * q * math.cos(math.pi * i / 12), -0.3 - by * q * math.sin(math.pi * i / 12) - 0.006, z) for i in range(13)], 0.014 * w ** 0.5, segs=4, ref=(0, 0, 1), m=m)
    g.tube([(0, -0.3 - by * math.sqrt(max(0.0, 1 - (i / 8 - 1) ** 2)) - 0.006, cz + bh * (i / 8 - 1)) for i in range(17)], 0.014 * w ** 0.5, segs=4, ref=(1, 0, 0), m=m)


def face_relief(g, w, h, m=None, key="relief"):
    """Giant mask-face relief filling a back wall (A: master D1 only; no close screenshot, so features are a restrained completion - B/C)."""
    g.use(key)
    rows = []
    for k in range(11):
        a = -math.pi / 2 + math.pi * k / 10
        s = max(0.03, math.cos(a))
        zf = math.sin(a)
        wide = 1.0 - 0.22 * max(0.0, -zf)                 # narrower chin
        rows.append([(w / 2 * s * wide * math.cos(TAU * i / 28), -0.16 * w * (s ** 0.7) * max(0.0, -math.sin(TAU * i / 28)) , h / 2 + h / 2 * zf) for i in range(28)])
    g.grid(rows, close_u=True, cap_start=True, cap_end=True, m=m)
    g.use("wall_deep")
    for sx in (-1, 1):                                    # eye sockets
        g.ellipsoid((sx * w * 0.2, -0.13 * w, h * 0.5), (w * 0.11, 0.05 * w, h * 0.13), segs=12, steps=6, m=m)
    g.use(key)
    for sx in (-1, 1):                                    # horns / crest strokes above the brow
        g.tube([(sx * w * 0.22, -0.1 * w, h * 0.86), (sx * w * 0.32, -0.08 * w, h * 1.02), (sx * w * 0.3, -0.05 * w, h * 1.16)], [0.05 * w, 0.035 * w, 0.01 * w], segs=6, ref=(0, 1, 0), m=m)
    for k in range(5):                                    # brow / cheek ridges
        z = h * (0.2 + 0.12 * k)
        half = w * 0.4 * math.sqrt(max(0.05, 1 - ((z - h / 2) / (h / 2)) ** 2))
        g.tube([(-half, -0.04 * w, z), (0, -0.19 * w, z - 0.03 * h), (half, -0.04 * w, z)], 0.012 * w, segs=4, ref=(0, 1, 0), m=m)


def telescope(g, m=None, length=4.6):
    """Long brass telescope on a geared stand (A: 08_Tower/Tower_step9.jpg, master B2)."""
    g.use("iron")
    g.revolve([(0.5, 0.0), (0.55, 0.1), (0.16, 0.3), (0.1, 1.4), (0.2, 1.5), (0.12, 1.62)], segs=10, m=m)
    for k in range(3):
        a = TAU * k / 3
        g.tube([(0.1 * math.cos(a), 0.1 * math.sin(a), 0.5), (0.7 * math.cos(a), 0.7 * math.sin(a), 0.0)], 0.04, segs=5, m=m)
    g.ring_arc((0, 0, 1.55), 0.42, 0, TAU, 0.035, n=18, plane="XZ", segs=5, m=m)
    g.use("trim")
    tilt = place(0, 0, 1.62, ry=math.radians(-104)) if m is None else m @ place(0, 0, 1.62, ry=math.radians(-104))
    # barrel points toward -X and slightly down
    prof = [(0.16, -1.0), (0.2, -0.9), (0.2, 0.0), (0.24, 0.05), (0.24, 0.3), (0.17, 0.36), (0.17, length * 0.55), (0.21, length * 0.57), (0.21, length * 0.62),
            (0.14, length * 0.66), (0.14, length - 1.0), (0.2, length - 0.94), (0.24, length - 0.7), (0.26, length - 0.62)]
    g.revolve(prof, segs=12, m=tilt)
