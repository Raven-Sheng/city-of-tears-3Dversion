"""Furniture, noble portraits and the per-storey furnishing of room stacks (user decision D-348).

Evidence (D-349): oval portraits of masked nobles in robes, dressers with ornaments, stairs and drapes
(A: 08_Tower/Tower_step3.jpg); book stacks, chests, lidded urns, tables with vases (A: 11_Lower_City/Lower_City_middle.jpg);
crowned display cabinets, glass soul-orb lamps, floating segmented platforms (A: master B3 enlarged, 01_Soul_Sanctuary);
settees and stools (A: 06_Right_City/Right_City_peak.jpg). Where each piece stands in a room is completion (C).
All builders face -Y (into the room from the back wall) and stand on z = 0.
"""
import math

import cot_kit as K
from cot_geo import Geo, TAU, lerp, place, rng


# ---------------------------------------------------------------------------- portraits
def k_noble_portrait(v=0, w=1.0, h=1.4, frame="trim_purple"):
    """Framed portrait of a masked bug noble in a robe (A: Tower_step3.jpg oval portraits). Hangs on the wall: origin at
    the bottom of the frame on the wall plane, painting faces -Y."""
    g = Geo()
    oval = v % 2 == 0
    cz = h / 2
    g.use("paint")
    if oval:
        g.ellipsoid((0, -0.02, cz), (w * 0.46, 0.03, h * 0.46), segs=24, steps=10)
    else:
        g.box(-w * 0.44, w * 0.44, -0.05, 0.0, h * 0.05, h * 0.95)
    g.use("creature_cloak" if v % 3 == 0 else ("cloth_purple" if v % 3 == 1 else "cloth_blue"))
    g.ellipsoid((0, -0.07, h * 0.24), (w * 0.34, 0.05, h * 0.2), segs=16, steps=8)        # robed shoulders
    g.use("creature_pale")
    g.ellipsoid((0, -0.09, h * 0.52), (w * 0.17, 0.05, h * 0.17), segs=14, steps=8)       # mask
    g.use("creature_dark")
    for sx in (-1, 1):
        g.ellipsoid((sx * w * 0.065, -0.135, h * 0.53), (w * 0.045, 0.012, h * 0.06), segs=8, steps=5)
    g.use("creature_pale")
    if v % 4 == 0:                                        # horns
        for sx in (-1, 1):
            g.spike((sx * w * 0.08, -0.09, h * 0.66), (sx * w * 0.2, -0.09, h * 0.84), w * 0.04, segs=5)
    elif v % 4 == 1:                                      # tall hat
        g.use("creature_dark")
        g.box(-w * 0.12, w * 0.12, -0.12, -0.07, h * 0.66, h * 0.85)
        g.box(-w * 0.2, w * 0.2, -0.13, -0.07, h * 0.65, h * 0.68)
    elif v % 4 == 2:                                      # crown points
        for k in range(5):
            x = (k - 2) * w * 0.06
            g.spike((x, -0.09, h * 0.66), (x, -0.09, h * 0.76 + 0.02 * (2 - abs(k - 2))), w * 0.025, segs=4)
    else:                                                 # veil
        g.use("cloth_purple")
        g.ellipsoid((0, -0.06, h * 0.6), (w * 0.24, 0.035, h * 0.22), segs=12, steps=6)
        g.use("creature_pale")
        g.ellipsoid((0, -0.1, h * 0.52), (w * 0.15, 0.04, h * 0.15), segs=12, steps=6)
    g.use(frame)
    if oval:
        g.ring_arc((0, -0.03, 0), 1.0, 0, TAU, 0.05 / max(w, 0.2), n=28, plane="XZ", segs=5, m=place(0, 0, cz, s=(w * 0.5, 1.0, h * 0.5)))
        g.ellipsoid((0, -0.06, h * 1.0), (w * 0.12, 0.05, h * 0.05), segs=8, steps=5)    # crest
        g.ellipsoid((0, -0.06, 0.0), (w * 0.08, 0.04, h * 0.04), segs=8, steps=5)
    else:
        for a, b in (((-w / 2, 0.0), (w / 2, 0.0)), ((-w / 2, h), (w / 2, h)), ((-w / 2, 0.0), (-w / 2, h)), ((w / 2, 0.0), (w / 2, h))):
            g.tube([(a[0], -0.04, a[1]), (b[0], -0.04, b[1])], 0.05, segs=5)
        g.ellipsoid((0, -0.07, h + 0.04), (w * 0.16, 0.05, 0.08), segs=8, steps=5)
    return g


# ---------------------------------------------------------------------------- furniture
def k_dresser(v=0, wood="wood", trim="trim_purple"):
    """Chest of drawers with curved legs and ornaments on top (A: Tower_step3.jpg)."""
    g = Geo()
    w, d, h = (1.4, 1.1, 1.7)[v % 3], 0.55, (1.05, 1.25, 0.95)[v % 3]
    g.use(wood)
    g.box(-w / 2, w / 2, -d / 2, d / 2, 0.18, h)
    g.box(-w / 2 - 0.05, w / 2 + 0.05, -d / 2 - 0.05, d / 2 + 0.03, h, h + 0.06)
    g.use(trim)
    rows = 3 if h > 1.0 else 2
    for r in range(rows):
        z0 = 0.24 + (h - 0.3) * r / rows
        z1 = 0.24 + (h - 0.3) * (r + 1) / rows - 0.05
        g.box(-w / 2 + 0.06, w / 2 - 0.06, -d / 2 - 0.02, -d / 2, z0, z1)
        g.ellipsoid((0, -d / 2 - 0.04, (z0 + z1) / 2), (0.05, 0.03, 0.05), segs=6, steps=4)
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.tube([(sx * (w / 2 - 0.06), sy * (d / 2 - 0.06), 0.2), (sx * (w / 2 - 0.02), sy * (d / 2 - 0.02), 0.0)], 0.04, segs=5)
    top = h + 0.06
    if v % 3 == 0:                                        # urn and a candle
        g.use("pot")
        g.revolve([(0.1, top), (0.14, top + 0.1), (0.1, top + 0.3), (0.05, top + 0.36)], segs=10, m=place(-w * 0.25, 0, 0))
        g.use("candle")
        g.tube([(w * 0.25, 0, top), (w * 0.25, 0, top + 0.25)], 0.03, segs=6)
    elif v % 3 == 1:                                      # row of spiky ornaments
        g.use(trim)
        for k in range(5):
            x = lerp(-w * 0.4, w * 0.4, k / 4)
            g.spike((x, 0, top), (x, 0, top + 0.2 + 0.1 * (k % 2)), 0.05, segs=5, bulb=1.0)
    else:                                                 # mirror on top
        g.use("mirror")
        g.ellipsoid((0, d / 2 - 0.1, top + 0.45), (w * 0.3, 0.03, 0.4), segs=16, steps=8)
        g.use(trim)
        g.tube([(w * 0.31 * math.cos(TAU * i / 24), d / 2 - 0.13, top + 0.45 + 0.41 * math.sin(TAU * i / 24)) for i in range(25)], 0.04, segs=4, ref=(0, 1, 0))
    return g


def k_cabinet(v=0, wood="wood", trim="trim_pale", crown=True):
    """Tall display cabinet / bookcase with a crowned top, shelves of books and curios (A: master B3 enlarged)."""
    g = Geo()
    w, d, h = (1.5, 1.2)[v % 2], 0.5, (2.4, 2.1)[v % 2]
    g.use(wood)
    g.box(-w / 2, w / 2, d / 2 - 0.06, d / 2, 0.0, h)                    # back
    for sx in (-1, 1):
        g.box(min(sx * w / 2, sx * (w / 2 - 0.07)), max(sx * w / 2, sx * (w / 2 - 0.07)), -d / 2, d / 2, 0.0, h)
    rand = rng(v * 17 + 3)
    n_sh = 4 if h > 2.2 else 3
    for k in range(n_sh + 1):
        z = 0.12 + (h - 0.2) * k / n_sh
        g.use(wood)
        g.box(-w / 2 + 0.07, w / 2 - 0.07, -d / 2, d / 2 - 0.06, z - 0.04, z)
        if k == n_sh:
            break
        x = -w / 2 + 0.1
        while x < w / 2 - 0.15:                           # books and curios
            bw = rand(0.05, 0.12)
            bh = rand(0.22, 0.38) * (h - 0.2) / n_sh / 0.5
            g.use(("cloth_blue", "cloth_purple", "trim_pale", "pot")[int(rand(0, 4))])
            if rand() < 0.15:
                g.ellipsoid((x + 0.08, 0.0, z + 0.1), (0.08, 0.08, 0.1), segs=8, steps=5)
                x += 0.2
            else:
                g.box(x, x + bw, -d / 2 + 0.08, d / 2 - 0.12, z, z + min(bh, (h - 0.2) / n_sh - 0.08))
                x += bw + 0.01
    if crown:
        g.use(trim)
        g.box(-w / 2 - 0.05, w / 2 + 0.05, -d / 2 - 0.05, d / 2, h, h + 0.08)
        for k in range(7):
            x = lerp(-w * 0.45, w * 0.45, k / 6)
            g.spike((x, -d / 2 + 0.05, h + 0.08), (x, -d / 2 + 0.05, h + 0.2 + 0.18 * (1 - abs(k - 3) / 3)), 0.04, segs=5)
    return g


def k_table(v=0, wood="wood", trim="trim_purple"):
    """Table with things on it: round pedestal table with a vase (v even) or a long table with cups (v odd)."""
    g = Geo()
    if v % 2 == 0:
        g.use(wood)
        g.revolve([(0.55, 0.78), (0.58, 0.82), (0.55, 0.86), (0.0, 0.86)], segs=20)
        g.revolve([(0.08, 0.0), (0.06, 0.78)], segs=8)
        g.revolve([(0.32, 0.0), (0.3, 0.06), (0.08, 0.1)], segs=12)
        g.use("pot")
        g.revolve([(0.08, 0.86), (0.13, 0.98), (0.07, 1.15), (0.1, 1.22)], segs=10)
    else:
        g.use(wood)
        g.box(-0.9, 0.9, -0.4, 0.4, 0.76, 0.84)
        for sx in (-1, 1):
            for sy in (-1, 1):
                g.tube([(sx * 0.8, sy * 0.32, 0.76), (sx * 0.84, sy * 0.35, 0.0)], 0.04, segs=5)
        g.use(trim)
        for k in range(4):
            x = -0.6 + 0.4 * k
            g.revolve([(0.04, 0.84), (0.06, 0.88), (0.05, 0.94)], segs=8, m=place(x, -0.15 + 0.3 * (k % 2), 0))
    return g


def k_chair(wood="wood", seat="cushion"):
    """Plain high-backed chair."""
    g = Geo()
    g.use(seat)
    g.box(-0.24, 0.24, -0.24, 0.24, 0.42, 0.5)
    g.use(wood)
    g.box(-0.24, 0.24, 0.2, 0.26, 0.5, 1.15)
    g.ellipsoid((0, 0.23, 1.18), (0.18, 0.04, 0.08), segs=8, steps=4)
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.tube([(sx * 0.2, sy * 0.2, 0.42), (sx * 0.22, sy * 0.22, 0.0)], 0.03, segs=4)
    return g


def k_trunk(v=0):
    """Chest with a domed lid and straps (A: Lower_City_middle.jpg)."""
    g = Geo()
    w = (1.0, 0.8)[v % 2]
    g.use("wood")
    g.box(-w / 2, w / 2, -0.3, 0.3, 0.0, 0.5)
    g.prism([(-w / 2, 0.5)] + [(w / 2 * math.cos(math.pi * i / 10), 0.5 + 0.22 * math.sin(math.pi * i / 10)) for i in range(11)][::-1] + [(w / 2, 0.5)], -0.3, 0.3)
    g.use("iron")
    for x in (-w * 0.3, w * 0.3):
        g.tube([(x, -0.31, 0.0), (x, -0.31, 0.5)] + [(x, -0.31 + 0.31 * (1 - math.cos(math.pi * i / 6)), 0.5 + 0.22 * math.sin(math.pi * i / 6)) for i in range(1, 7)],
               0.025, segs=4)
    return g


def k_book_stack(v=0):
    """Stacks of books and papers (A: Lower_City_middle.jpg)."""
    g = Geo()
    rand = rng(v * 31 + 7)
    for s in range(3 if v % 2 == 0 else 2):
        x = (s - 1) * 0.45
        z = 0.0
        for k in range(int(rand(4, 9))):
            g.use(("cloth_blue", "cloth_purple", "trim_pale", "wood")[int(rand(0, 4))])
            w, d, hh = rand(0.32, 0.45), rand(0.24, 0.32), rand(0.06, 0.12)
            a = rand(-0.3, 0.3)
            g.box(-w / 2, w / 2, -d / 2, d / 2, 0.0, hh, m=place(x, 0, z, rz=a))
            z += hh
    return g


def k_orb_lamp(h=1.4):
    """Glass soul orb on a slender stand (A: Soul_Sanctuary core / master B3 enlarged)."""
    g = Geo()
    g.use("trim_pale")
    g.revolve([(0.22, 0.0), (0.24, 0.06), (0.06, 0.14), (0.04, h - 0.25), (0.12, h - 0.18), (0.16, h - 0.12)], segs=10)
    g.use("lamp_white")
    g.ellipsoid((0, 0, h + 0.12), (0.24, 0.24, 0.24), segs=14, steps=8)
    g.use("trim_pale")
    g.ring_arc((0, 0, h + 0.12), 0.25, 0, TAU, 0.025, n=16, plane="XY", segs=4)
    return g


def k_lectern():
    """Reading desk with an open book and a small orb (sanctum)."""
    g = Geo()
    g.use("trim_pale")
    g.revolve([(0.3, 0.0), (0.28, 0.06), (0.08, 0.14), (0.07, 0.95)], segs=10)
    g.use("wood")
    g.box(-0.4, 0.4, -0.25, 0.25, 0.95, 1.02, m=place(0, 0, 0, rx=0.35))
    g.use("trim_pale")
    g.box(-0.32, 0.32, -0.18, 0.18, 1.02, 1.06, m=place(0, 0, 0, rx=0.35))
    g.use("lamp_white")
    g.ellipsoid((0.3, 0.12, 1.2), (0.08, 0.08, 0.08), segs=8, steps=5)
    return g


def k_pill_platform(n=2):
    """Floating segmented platform of pale capsules (A: master B3 enlarged, Soul Sanctum). Origin at its top."""
    g = Geo()
    w = 0.95
    for k in range(n):
        x = (k - (n - 1) / 2) * w
        g.use("trim_pale")
        g.ellipsoid((x, 0, -0.38), (w * 0.5, 0.5, 0.38), segs=14, steps=8, e=0.55)
        g.use("wall_sanctum")
        g.box(x - w * 0.35, x + w * 0.35, -0.52, -0.46, -0.6, -0.15)
    return g


def k_rug(w=2.2, d=1.4, key="cloth_purple", trim="trim_purple"):
    g = Geo()
    g.use(key)
    g.ellipsoid((0, 0, 0.03), (w / 2, d / 2, 0.025), segs=24, steps=3)
    g.use(trim)
    g.ring_arc((0, 0, 0.02), 1.0, 0, TAU, 0.025, n=28, plane="XY", segs=4, m=place(0, 0, 0, s=(w / 2 * 0.92, d / 2 * 0.92, 1.0)))
    return g


def k_settee():
    """Tufted settee with a high shell back (A: Right_City_peak.jpg)."""
    g = Geo()
    g.use("cushion")
    g.ellipsoid((0, 0, 0.5), (1.1, 0.5, 0.3), segs=14, steps=6, e=0.6)
    for k in range(3):
        g.ellipsoid((-0.7 + 0.7 * k, 0.42, 1.1), (0.34, 0.18, 0.55), segs=8, steps=6)
    g.use("trim_purple")
    g.box(-1.1, 1.1, -0.42, 0.52, 0.0, 0.28)
    return g


def k_bench_plain(w=1.8):
    g = Geo().use("wood")
    g.box(-w / 2, w / 2, -0.22, 0.22, 0.42, 0.5)
    for sx in (-1, 1):
        g.box(sx * (w / 2 - 0.12) - 0.05, sx * (w / 2 - 0.12) + 0.05, -0.2, 0.2, 0.0, 0.42)
    return g


def k_tall_case(w=1.8, h=3.6, trim="trim_pale", v=0):
    """Tall bookcase with a crowned top for high rooms (A: crowned cabinets on master B3 enlarged; height is completion)."""
    g = Geo()
    d = 0.55
    g.use("wood")
    g.box(-w / 2, w / 2, d / 2 - 0.06, d / 2, 0.0, h)
    for sx in (-1, 1):
        g.box(min(sx * w / 2, sx * (w / 2 - 0.08)), max(sx * w / 2, sx * (w / 2 - 0.08)), -d / 2, d / 2, 0.0, h)
    rand = rng(v * 23 + int(h * 10))
    n_sh = max(4, int(h / 0.62))
    for k in range(n_sh + 1):
        z = 0.12 + (h - 0.2) * k / n_sh
        g.use("wood")
        g.box(-w / 2 + 0.08, w / 2 - 0.08, -d / 2, d / 2 - 0.06, z - 0.04, z)
        if k == n_sh:
            break
        x = -w / 2 + 0.11
        while x < w / 2 - 0.16:
            bw = rand(0.05, 0.12)
            g.use(("cloth_blue", "cloth_purple", "trim_pale", "pot", "wood")[int(rand(0, 5))])
            if rand() < 0.12:
                g.ellipsoid((x + 0.08, 0.0, z + 0.1), (0.08, 0.08, 0.1), segs=8, steps=5)
                x += 0.2
            else:
                g.box(x, x + bw, -d / 2 + 0.08, d / 2 - 0.12, z, z + rand(0.6, 0.95) * ((h - 0.2) / n_sh - 0.06))
                x += bw + 0.01
    g.use(trim)
    g.box(-w / 2 - 0.06, w / 2 + 0.06, -d / 2 - 0.06, d / 2, h, h + 0.1)
    g.prism([(-w / 2, h + 0.1), (w / 2, h + 0.1), (0.0, h + 0.1 + w * 0.32)], -d / 2 - 0.02, -d / 2 + 0.06)
    for k in range(5):
        x = lerp(-w * 0.42, w * 0.42, k / 4)
        g.spike((x, -d / 2 + 0.02, h + 0.1), (x, -d / 2 + 0.02, h + 0.3 + 0.12 * (2 - abs(k - 2))), 0.04, segs=5)
    return g


def k_oval_case(h=3.2):
    """Tall oval glass display case on a plinth, a soul orb inside (A: tall oval cabinets of Soul_Sanctuary_core.jpg)."""
    g = Geo()
    g.use("trim_pale")
    g.revolve([(0.62, 0.0), (0.66, 0.1), (0.56, 0.22), (0.5, 0.3)], segs=16)
    zc, rz_ = 0.3 + (h - 0.3) / 2, (h - 0.3) / 2
    g.use("glass_white")
    g.ellipsoid((0, 0, zc), (0.46, 0.36, rz_), segs=18, steps=10)
    g.use("trim_pale")
    g.ring_arc((0, 0, 0), 1.0, 0, TAU, 0.05, n=32, plane="XZ", segs=5, m=place(0, -0.02, zc, s=(0.48, 1.0, rz_ * 1.02)))
    g.ring_arc((0, 0, 0), 1.0, 0, TAU, 0.05, n=32, plane="XZ", segs=5, m=place(0, 0, zc, rz=math.pi / 2, s=(0.38, 1.0, rz_ * 1.02)))
    g.spike((0, 0, h - 0.02), (0, 0, h + 0.35), 0.06, segs=6, bulb=1.0)
    g.use("lamp_white")
    g.ellipsoid((0, 0, 0.3 + (h - 0.3) * 0.42), (0.17, 0.17, 0.17), segs=12, steps=6)
    return g


def k_scroll_pile(v=0):
    """Heap of rolled scrolls (A: Soul_Sanctuary_core.jpg)."""
    g = Geo()
    rand = rng(v * 41 + 5)
    for r in range(3):
        n = 5 - r
        for k in range(n):
            x = (k - (n - 1) / 2) * 0.17 + rand(-0.03, 0.03)
            z = 0.08 + r * 0.14
            g.use(("trim_pale", "cloth_blue", "trim_pale")[k % 3])
            g.tube([(x, -0.38 + rand(-0.05, 0.05), z), (x + rand(-0.08, 0.08), 0.38 + rand(-0.05, 0.05), z)], 0.075, segs=8)
    return g


def k_orb_cluster(v=0):
    """Cluster of soul orbs on stands of different heights (A: clusters of glowing orbs, master B3 enlarged)."""
    g = Geo()
    g.use("trim_pale")
    g.revolve([(0.62, 0.0), (0.6, 0.08), (0.2, 0.14)], segs=16)
    for k, (dx, dy, h) in enumerate(((0.0, 0.0, 2.1), (0.36, 0.2, 1.5), (-0.34, 0.18, 1.7), (0.1, -0.36, 1.2), (-0.25, -0.3, 0.95))[: 3 + v % 3]):
        g.use("trim_pale")
        g.tube([(0, 0, 0.12), (dx, dy, h - 0.2)], 0.03, segs=5)
        g.use("lamp_white")
        g.ellipsoid((dx, dy, h), (0.2, 0.2, 0.2), segs=12, steps=6)
    return g


def k_dais(w=6.0, d=3.0, h=0.9, key="cushion", trim="trim"):
    """Raised platform with two steps along its front (A: raised dais of Tower_step1.jpg)."""
    g = Geo()
    g.use(key)
    g.box(-w / 2, w / 2, -d / 2, d / 2, 0.0, h)
    g.use(trim)
    g.box(-w / 2 - 0.05, w / 2 + 0.05, -d / 2 - 0.05, d / 2 + 0.05, h - 0.08, h)
    for k, z in enumerate((h * 0.33, h * 0.66)):
        dd = 0.35 * (2 - k)
        g.use(key)
        g.box(-w / 2 + 0.6, w / 2 - 0.6, -d / 2 - dd, -d / 2, 0.0, z)
    return g


# groups: (kit key, builder, dx, dy, rz) laid out round the group centre, facing -Y
def _groups():
    def dining(wood_trim, rug_key, rug_trim, tag):
        out = [(f"rug_{rug_key}_34", lambda: k_rug(3.4, 2.6, rug_key, rug_trim), 0.0, 0.0, 0.0),
               (f"table_1_{wood_trim}", lambda: k_table(1, "wood", wood_trim), 0.0, 0.0, 0.0)]
        for x in (-0.5, 0.5):
            out += [("chair", lambda: k_chair(), x, -0.68, math.pi), ("chair", lambda: k_chair(), x, 0.68, 0.0)]
        out += [("chair", lambda: k_chair(), -1.3, 0.0, math.pi / 2), ("chair", lambda: k_chair(), 1.3, 0.0, -math.pi / 2)]
        return (f"dining_{tag}", out, 3.4, 2.6, 1.25)
    study = ("study", [("rug_cloth_blue_30", lambda: k_rug(3.0, 2.2, "cloth_blue", "trim_pale"), 0.0, 0.0, 0.0), ("lectern", lambda: k_lectern(), 0.0, 0.35, 0.0),
                       ("books_0", lambda: k_book_stack(0), -1.05, -0.3, 0.3), ("books_1", lambda: k_book_stack(1), 1.0, 0.5, -0.4),
                       ("scrolls_0", lambda: k_scroll_pile(0), 0.85, -0.55, 1.2), ("orb_lamp", lambda: k_orb_lamp(1.4), -1.25, 0.75, 0.0)], 3.0, 2.2, 1.6)
    salon = ("salon", [("rug_cloth_purple_36", lambda: k_rug(3.6, 2.6, "cloth_purple", "trim_purple"), 0.0, 0.0, 0.0), ("settee_f", lambda: k_settee(), 0.0, 0.85, 0.0),
                       ("table_0p", lambda: k_table(0, "wood", "trim_purple"), 0.0, -0.25, 0.0), ("chair", lambda: k_chair(), -1.2, -0.7, math.pi - 0.6),
                       ("chair", lambda: k_chair(), 1.2, -0.7, math.pi + 0.6)], 3.6, 2.6, 1.6)
    rest = ("rest", [("bench_plain", lambda: k_bench_plain(), 0.0, 0.25, 0.0), ("trunk_0", lambda: k_trunk(0), 1.45, -0.25, 0.3),
                     ("books_0", lambda: k_book_stack(0), -1.35, -0.25, -0.2)], 3.6, 1.4, 0.9)
    orbs = ("orbs", [(f"orb_cluster_{v}", (lambda v=v: k_orb_cluster(v)), 0.0, 0.0, 0.0) for v in (1,)], 1.4, 1.4, 2.3)
    return {"sanctum": [study, orbs, dining("trim_pale", "cloth_blue", "trim_pale", "pale")],
            "blue": [dining("trim", "cloth_blue", "trim", "blue"), rest],
            "tower": [dining("trim", "cloth_purple", "trim", "tower"), study],
            "purple": [salon, dining("trim_purple", "cloth_purple", "trim_purple", "purple")],
            "jar": [dining("trim_purple", "cloth_purple", "trim_purple", "jar")],
            "street": [rest], "corridor": [rest], "green": [rest]}


# tall wall pieces for high rooms: (kit key prefix, builder of height h)
TALL = {"sanctum": [("tallcase_pale", lambda h: k_tall_case(1.9, h, "trim_pale"), 0.6), ("ovalcase", lambda h: k_oval_case(min(h, 3.6)), 1.45)],
        "blue": [("tallcase_blue", lambda h: k_tall_case(1.8, h, "trim"), 0.6)], "tower": [("tallcase_tower", lambda h: k_tall_case(1.8, h, "trim"), 0.6)],
        "purple": [("tallcase_purple", lambda h: k_tall_case(1.7, h, "trim_purple"), 0.6)]}     # (key, builder of height h, depth)
GROUPS = None


# ---------------------------------------------------------------------------- per-style sets
# each entry: (kit key, builder, footprint width, footprint depth, height, where) where = "wall" (against the back wall) or "floor"
def _sets():
    return {
        "blue": [("dresser_0", lambda: k_dresser(0, "wood", "trim"), 1.5, 0.6, 1.5, "wall"), ("cabinet_1_dark", lambda: k_cabinet(1, "wood", "trim", False), 1.2, 0.5, 2.1, "wall"),
                 ("table_1", lambda: k_table(1, "wood", "trim"), 1.9, 0.9, 0.95, "floor"), ("trunk_0", lambda: k_trunk(0), 1.0, 0.6, 0.75, "floor"),
                 ("books_0", lambda: k_book_stack(0), 1.4, 0.4, 0.9, "wall"), ("bench_plain", lambda: k_bench_plain(), 1.8, 0.5, 0.5, "floor")],
        "sanctum": [("cabinet_0_pale", lambda: k_cabinet(0, "wood", "trim_pale", True), 1.6, 0.55, 2.65, "wall"), ("orb_lamp", lambda: k_orb_lamp(1.4), 0.5, 0.5, 1.8, "floor"),
                    ("lectern", lambda: k_lectern(), 0.8, 0.6, 1.3, "floor"), ("table_0_pale", lambda: k_table(0, "wood", "trim_pale"), 1.2, 1.2, 1.25, "floor"),
                    ("books_1", lambda: k_book_stack(1), 1.0, 0.4, 0.8, "wall"), ("rug_pale", lambda: k_rug(2.4, 1.5, "cloth_blue", "trim_pale"), 2.4, 1.5, 0.05, "floor")],
        "tower": [("dresser_1", lambda: k_dresser(1, "wood", "trim"), 1.2, 0.6, 1.5, "wall"), ("dresser_2", lambda: k_dresser(2, "wood", "trim"), 1.8, 0.6, 1.9, "wall"),
                  ("table_0", lambda: k_table(0, "wood", "trim"), 1.2, 1.2, 1.25, "floor"), ("chair", lambda: k_chair(), 0.5, 0.5, 1.2, "floor"),
                  ("rug_purple", lambda: k_rug(), 2.2, 1.4, 0.05, "floor"), ("trunk_1", lambda: k_trunk(1), 0.8, 0.6, 0.75, "floor")],
        "purple": [("settee_f", lambda: k_settee(), 2.2, 1.0, 1.6, "wall"), ("dresser_1p", lambda: k_dresser(1, "wood", "trim_purple"), 1.2, 0.6, 1.5, "wall"),
                   ("table_0p", lambda: k_table(0, "wood", "trim_purple"), 1.2, 1.2, 1.25, "floor"), ("rug_purple", lambda: k_rug(), 2.2, 1.4, 0.05, "floor"),
                   ("chair", lambda: k_chair(), 0.5, 0.5, 1.2, "floor")],
        "street": [("trunk_0", lambda: k_trunk(0), 1.0, 0.6, 0.75, "floor"), ("books_0", lambda: k_book_stack(0), 1.4, 0.4, 0.9, "wall"),
                   ("bench_plain", lambda: k_bench_plain(), 1.8, 0.5, 0.5, "floor")],
        "corridor": [("trunk_1", lambda: k_trunk(1), 0.8, 0.6, 0.75, "floor"), ("books_1", lambda: k_book_stack(1), 1.0, 0.4, 0.8, "wall"),
                     ("bench_plain", lambda: k_bench_plain(), 1.8, 0.5, 0.5, "wall")],
        "jar": [("table_1p", lambda: k_table(1, "wood", "trim_purple"), 1.9, 0.9, 0.95, "floor"), ("chair", lambda: k_chair(), 0.5, 0.5, 1.2, "floor")],
        "green": [("trunk_0", lambda: k_trunk(0), 1.0, 0.6, 0.75, "floor"), ("bench_plain", lambda: k_bench_plain(), 1.8, 0.5, 0.5, "wall")],
    }


SETS = None


def furniture_set(name):
    global SETS
    if SETS is None:
        SETS = _sets()
    return SETS.get(name, [])


def furnish_storeys(S, rid, name, set_name, storeys, bay_x, bw, x0, x1, yf, yb, wall, blocked, door_bays, inner_rows, seed, ev, ref,
                    window_bays=None, density=0.75, clear=()):
    """Put furniture in each storey. clear: (storey, x0, x1, y0, y1) rectangles kept free (region-specific pieces). blocked(i, x) -> True where a bay is a shaft, a solid cell or kept clear.
    door_bays: {storey index: set of bay indices next to a door}. window_bays: {(i, k): (height limit, stand-off)} from
    what each back-wall bay carries. High rooms get tall cases on the back wall and furniture groups on the floor, one
    try per stretch of about 6 m between the arcade rows (D-354, D-361). Returns the footprints taken: (storey, x0, x1, y0, y1)."""
    global GROUPS
    items = furniture_set(set_name)
    occ = []
    if not items:
        return occ + list(clear)
    if GROUPS is None:
        GROUPS = _groups()
    groups = GROUPS.get(set_name, [])
    talls = TALL.get(set_name, [])
    rand = rng(seed * 7919 + 13)
    walls = [it for it in items if it[5] == "wall"]
    floors = [it for it in items if it[5] == "floor"]

    def hit(i, a, b, c, d):
        return any(j == i and a < xb and b > xa and c < yb_ and d > ya for j, xa, xb, ya, yb_ in list(clear) + occ)

    for i, zf, top in storeys:
        hgt = top - zf
        if hgt < 2.2:
            continue
        big = hgt >= 3.4 and bw >= 3.6
        for k, cx in enumerate(bay_x):
            if blocked(i, cx) or k in door_bays.get(i, ()):
                continue
            # against the back wall: below what the bay carries, standing off a window, portrait or panel
            wb = (window_bays or {}).get((i, k), 99.0) if isinstance(window_bays, dict) else (0.95 if window_bays and (i, k) in window_bays else 99.0)
            lim, push = wb if isinstance(wb, tuple) else (wb, 0.0)
            yw = yb - wall - 0.08 - push
            th = round(min(hgt - 1.3, 4.4) * 5) / 5
            if talls and hgt >= 4.6 and lim >= th and bw >= 2.6 and rand() < 0.6:
                key, build, fd = talls[int(rand(0, len(talls)))]
                fw = max(1.9, fd)
                fx = cx + rand(-0.2, 0.2) * (bw - fw) / 2
                if not hit(i, fx - fw / 2, fx + fw / 2, yw - fd, yw):
                    S.put(S.kit(f"FU_{key}_{th:.1f}", lambda build=build, th=th: build(th)), f"{name}_FurnT_{i}_{k:02d}", rid, "Furniture",
                          place(fx, yw - fd / 2, zf + 0.01), "C", ref, note="tall case of the region's set for a high room; placement is completion")
                    occ.append((i, fx - fw / 2, fx + fw / 2, yw - fd, yw))
            else:
                cand = [it for it in walls if it[4] < min(hgt - 1.7, lim) and it[2] < bw - 0.4]
                if cand and rand() < density:
                    key, build, fw, fd, fh, _ = cand[int(rand(0, len(cand)))]
                    fx = cx + rand(-0.3, 0.3) * (bw - fw) / 2
                    if not hit(i, fx - fw / 2, fx + fw / 2, yw - fd, yw):
                        S.put(S.kit("FU_" + key, build), f"{name}_FurnW_{i}_{k:02d}", rid, "Furniture", place(fx, yw - fd / 2, zf + 0.01),
                              "C", ref, note="furniture of the region's set; placement is completion")
                        occ.append((i, fx - fw / 2, fx + fw / 2, yw - fd, yw))
            # out on the floor, clear of the front walk and the inner arcade rows: bands between the rows, each cut
            # into stretches of about 6 m; one group (high rooms) or one piece per stretch
            y_lo, y_hi = yf + 1.9, yb - wall - 1.6
            if y_hi - y_lo < 1.2:
                continue
            cuts = sorted(r for r in inner_rows if y_lo < r < y_hi)
            bands = [(a + (0.5 if a != y_lo else 0.0), b - (0.5 if b != y_hi else 0.0)) for a, b in zip([y_lo] + cuts, cuts + [y_hi])]
            parts = []
            for a, b in bands:
                n = max(1, int((b - a) / 6.0))
                parts += [(a + (b - a) * q / n, a + (b - a) * (q + 1) / n) for q in range(n)]
            parts = [(a, b) for a, b in parts if b - a > 1.4]
            cand = [it for it in floors if it[4] < hgt - 1.2]
            for j, (b_lo, b_hi) in enumerate(parts):
                sfx = "" if j == 0 else f"_b{j}"
                if rand() >= density * 0.85:
                    continue
                gr = [gp for gp in groups if gp[3] + 0.4 < b_hi - b_lo and gp[2] + 0.4 < bw and gp[4] < hgt - 1.0] if big else []
                if gr and rand() < 0.7:
                    gkey, parts_g, fw, fd, fh = gr[int(rand(0, len(gr)))]
                    for _ in range(6):
                        yy = rand(b_lo + fd / 2, b_hi - fd / 2)
                        tx = cx + rand(-0.2, 0.2) * max(0.0, bw - fw)
                        if hit(i, tx - fw / 2 - 0.3, tx + fw / 2 + 0.3, yy - fd / 2 - 0.2, yy + fd / 2 + 0.2):
                            continue
                        if all(abs(yy - r) > fd / 2 + 0.45 for r in inner_rows):
                            rz0 = rand(-0.15, 0.15)
                            cz, sz = math.cos(rz0), math.sin(rz0)
                            for n_, (key, build, dx, dy, rz) in enumerate(parts_g):
                                S.put(S.kit("FU_" + key, build), f"{name}_FurnG_{i}_{k:02d}{sfx}_{n_}", rid, "Furniture",
                                      place(tx + dx * cz - dy * sz, yy + dx * sz + dy * cz, zf + 0.01, rz=rz + rz0), "C", ref,
                                      note=f"furniture group ({gkey}) of the region's set; placement is completion")
                            occ.append((i, tx - fw / 2 - 0.15, tx + fw / 2 + 0.15, yy - fd / 2 - 0.15, yy + fd / 2 + 0.15))
                            break
                    continue
                if not cand:
                    continue
                key, build, fw, fd, fh, _ = cand[int(rand(0, len(cand)))]
                if b_hi - b_lo < fd + 0.2:
                    continue
                for _ in range(6):
                    yy = rand(b_lo + fd / 2, b_hi - fd / 2)
                    tx = cx + rand(-0.25, 0.25) * max(0.0, bw - fw)
                    if hit(i, tx - fw / 2 - 0.8, tx + fw / 2 + 0.8, yy - fd / 2 - 0.2, yy + fd / 2 + 0.2):
                        continue
                    if all(abs(yy - r) > fd / 2 + 0.45 for r in inner_rows):
                        S.put(S.kit("FU_" + key, build), f"{name}_FurnF_{i}_{k:02d}{sfx}", rid, "Furniture",
                              place(tx, yy, zf + 0.01, rz=rand(-0.25, 0.25)), "C", ref, note="furniture of the region's set; placement is completion")
                        occ.append((i, tx - fw / 2 - 0.15, tx + fw / 2 + 0.15, yy - fd / 2 - 0.15, yy + fd / 2 + 0.15))
                        if key.startswith("table") and rand() < 0.6 and bw - fw > 1.6:             # chairs round a table
                            ch = S.kit("FU_chair", lambda: k_chair())
                            for sgn in (-1, 1):
                                S.put(ch, f"{name}_FurnC_{i}_{k:02d}{sfx}_{sgn + 1}", rid, "Furniture",
                                      place(tx + sgn * (fw / 2 + 0.35), yy, zf + 0.01, rz=-sgn * math.pi / 2), "C", ref)
                            occ.append((i, tx - fw / 2 - 0.7, tx + fw / 2 + 0.7, yy - 0.4, yy + 0.4))
                        break
    return occ + list(clear)


def side_cases(S, rid, name, set_name, storeys, x0, x1, yf, yb, wall, side_ok, ref):
    """Tall cases along the side walls of high, deep rooms (between the side portraits). side_ok(i, side, y, half) tells
    whether that stretch of side wall is free (no door, shaft, solid cell or open side). Returns footprints."""
    talls = TALL.get(set_name, [])
    occ = []
    if not talls:
        return occ
    for i, zf, top in storeys:
        hgt = top - zf
        if hgt < 4.2 or yb - yf < 9.0:
            continue
        th = round(min(hgt - 1.3, 4.4) * 5) / 5
        for side, sgn, rz in (("L", 1.0, math.pi / 2), ("R", -1.0, -math.pi / 2)):
            for j, f in enumerate((0.2, 0.92)):
                py = min(max(lerp(yf + 0.6, yb - wall, f), yf + 2.2), yb - wall - 1.5)     # clear of the front arcade and the back wall
                if j == 1 and py - lerp(yf + 0.6, yb - wall, 0.2) < 3.0:
                    continue
                if not side_ok(i, side, py, 1.2):
                    continue
                key, build, fd = talls[(i + j + (side == "R")) % len(talls)]
                px = (x0 + wall + 0.06 + fd / 2) if sgn > 0 else (x1 - wall - 0.06 - fd / 2)
                S.put(S.kit(f"FU_{key}_{th:.1f}", lambda build=build, th=th: build(th)), f"{name}_FurnS_{side}_{i}_{j}", rid, "Furniture",
                      place(px, py, zf + 0.01, rz=rz), "C", ref, note="tall case on the side wall of a high room: completion")
                occ.append((i, px - fd / 2 - 0.1, px + fd / 2 + 0.1, py - 1.05, py + 1.05))
    return occ
