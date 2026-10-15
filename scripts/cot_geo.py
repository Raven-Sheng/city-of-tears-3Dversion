"""Geometry helpers for City of Tears stage 2+ assets (Blender 5.2, background-safe).

Everything here builds real, closed, editable geometry:
  * Geo        - bmesh accumulator with material slots (meshes: stone, shells, statue, glass)
  * IronCurves - bevelled curve object builder (ironwork with a true round section, tapered spikes)
Coordinates follow the project convention: X right, Y depth (away from the viewer), Z up.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector, noise
from mathutils.geometry import tessellate_polygon

TAU = math.tau


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def spow(v, e):
    return math.copysign(abs(v) ** e, v)


def rng(seed):
    """Small deterministic generator (independent of Python's global random state)."""
    state = [seed & 0x7FFFFFFF or 1]

    def nxt(a=0.0, b=1.0):
        state[0] = (state[0] * 1103515245 + 12345) & 0x7FFFFFFF
        return a + (b - a) * (state[0] / 0x7FFFFFFF)
    return nxt


def rot_z(angle):
    return Matrix.Rotation(angle, 4, "Z")


def place(x=0.0, y=0.0, z=0.0, rz=0.0, s=1.0, rx=0.0, ry=0.0):
    m = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(ry, 4, "Y") @ Matrix.Rotation(rx, 4, "X")
    if isinstance(s, (tuple, list)):
        m = m @ Matrix.Diagonal((s[0], s[1], s[2], 1.0))
    elif s != 1.0:
        m = m @ Matrix.Scale(s, 4)
    return m


class Geo:
    """Accumulates closed solids into one mesh; faces remember the current material key."""

    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.keys = []
        self.mi = 0

    # ------------------------------------------------------------------ materials
    def use(self, key):
        if key not in self.keys:
            self.keys.append(key)
        self.mi = self.keys.index(key)
        return self

    # ------------------------------------------------------------------ primitives
    def _v(self, p, m):
        p = Vector(p)
        return self.bm.verts.new(m @ p if m is not None else p)

    def _f(self, verts, uvs=None):
        if len(set(verts)) < 3:
            return None
        try:
            face = self.bm.faces.new(verts)
        except ValueError:
            return None
        face.material_index = self.mi
        face.smooth = True
        if uvs is not None:
            for loop, uv in zip(face.loops, uvs):
                loop[self.uv].uv = uv
        return face

    def grid(self, rows, close_u=False, cap_start=False, cap_end=False, m=None, uvs=None):
        """Quads between consecutive rows (each row: equal number of points). close_u closes each row."""
        loops = [[self._v(p, m) for p in row] for row in rows]
        n = len(loops[0])
        last = n if close_u else n - 1
        for r, (a, b) in enumerate(zip(loops, loops[1:])):
            for i in range(last):
                j = (i + 1) % n
                uv = None
                if uvs is not None:
                    uv = (uvs[r][i], uvs[r][j], uvs[r + 1][j], uvs[r + 1][i])
                self._f((a[i], a[j], b[j], b[i]), uv)
        if cap_start and n > 2:
            self._cap(loops[0], True)
        if cap_end and n > 2:
            self._cap(loops[-1], False)
        return loops

    def _cap(self, loop, flip):
        centre = Vector((0, 0, 0))
        for v in loop:
            centre += v.co
        c = self.bm.verts.new(centre / len(loop))
        n = len(loop)
        for i in range(n):
            j = (i + 1) % n
            self._f((loop[j], loop[i], c) if flip else (loop[i], loop[j], c))

    def box(self, x0, x1, y0, y1, z0, z1, m=None):
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        z0, z1 = sorted((z0, z1))
        v = [self._v(p, m) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                      (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
        for a, b, c, d in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            f = self._f((v[a], v[b], v[c], v[d]))
            if f is not None:
                f.smooth = False

    def prism(self, pts_xz, y0, y1, m=None, smooth=False, half_fn=None):
        """Extrude an XZ polygon along Y (concave allowed). Caps are tessellated with mathutils, which is
        reliable for concave outlines (the bmesh n-gon triangulation filled concavities on one side)."""
        if half_fn is not None:                 # depth varies over the outline: half_fn(x, z) -> half thickness
            yc = (y0 + y1) / 2
            front = [self._v((x, yc - half_fn(x, z), z), m) for x, z in pts_xz]
            back = [self._v((x, yc + half_fn(x, z), z), m) for x, z in pts_xz]
        else:
            front = [self._v((x, y0, z), m) for x, z in pts_xz]
            back = [self._v((x, y1, z), m) for x, z in pts_xz]
        n = len(front)
        for i in range(n):
            j = (i + 1) % n
            f = self._f((front[i], front[j], back[j], back[i]))
            if f is not None:
                f.smooth = smooth
        tris = tessellate_polygon([[Vector((x, z, 0.0)) for x, z in pts_xz]])
        for a, b, c in tris:
            for loop, flip in ((front, False), (back, True)):
                f = self._f((loop[a], loop[c], loop[b]) if flip else (loop[a], loop[b], loop[c]))
                if f is not None:
                    f.smooth = False

    def revolve(self, profile, segs=24, m=None, mod=None, cap_bottom=True, cap_top=True, sx=1.0, sy=1.0):
        """Revolve (r, z) profile around Z. mod(theta, k) -> radius multiplier (k = profile index)."""
        rows = []
        for k, (r, z) in enumerate(profile):
            row = []
            for i in range(segs):
                th = TAU * i / segs
                rr = r * (mod(th, k) if mod else 1.0)
                row.append((rr * math.cos(th) * sx, rr * math.sin(th) * sy, z))
            rows.append(row)
        return self.grid(rows, close_u=True, cap_start=cap_bottom, cap_end=cap_top, m=m)

    def ellipsoid(self, c, r, segs=14, steps=8, m=None, e=1.0):
        """(Super)ellipsoid; e < 1 gives rounded-box stones."""
        cx, cy, cz = c
        rx, ry, rz = r
        rows = []
        for k in range(steps + 1):
            a = -math.pi / 2 + math.pi * k / steps
            ca, sa = spow(math.cos(a), e), spow(math.sin(a), e)
            if k in (0, steps):
                ca = 0.02
            rows.append([(cx + rx * ca * spow(math.cos(TAU * i / segs), e),
                          cy + ry * ca * spow(math.sin(TAU * i / segs), e), cz + rz * sa) for i in range(segs)])
        return self.grid(rows, close_u=True, cap_start=True, cap_end=True, m=m)

    def tube(self, path, ra, rb=None, segs=8, ref=None, m=None, cap=True, twist=0.0):
        """Sweep an ellipse along a path. ra: radius along the reference normal, rb: along the binormal.

        ra / rb may be numbers or per-point lists. ref fixes the normal direction (default: auto).
        """
        pts = [Vector(p) for p in path]
        n = len(pts)
        if n < 2:
            return None
        ra = ra if isinstance(ra, (list, tuple)) else [ra] * n
        rb = ra if rb is None else (rb if isinstance(rb, (list, tuple)) else [rb] * n)
        tangents = []
        for i in range(n):
            t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
            tangents.append(t.normalized() if t.length > 1e-9 else Vector((0, 0, 1)))
        if ref is None:
            ref = Vector((0, 1, 0)) if abs(tangents[0].y) < 0.9 else Vector((1, 0, 0))
        ref = Vector(ref)
        normal = (ref - tangents[0] * ref.dot(tangents[0])).normalized()
        rows = []
        for i in range(n):
            t = tangents[i]
            normal = normal - t * normal.dot(t)
            if normal.length < 1e-6:
                normal = t.orthogonal()
            normal.normalize()
            binormal = t.cross(normal)
            row = []
            for k in range(segs):
                a = TAU * k / segs + twist
                row.append(pts[i] + normal * (math.cos(a) * max(ra[i], 1e-4)) + binormal * (math.sin(a) * max(rb[i], 1e-4)))
            rows.append(row)
        return self.grid(rows, close_u=True, cap_start=cap, cap_end=cap, m=m)

    def lens(self, centre_fn, width_fn, thick_fn, nu=14, nv=10, m=None, cup=0.0, crease=0.0, edge=0.55, uv=False):
        """Leaf / petal solid. centre_fn(u) -> (x, z) centre line in the local XZ plane, growing along +X.

        Cross-sections lie across Y. cup lifts the edges, crease sinks the middle, edge < 1 sharpens the rim.
        """
        rows, uvs = [], []
        for i in range(nu + 1):
            u = i / nu
            x, z = centre_fn(u)
            x2, z2 = centre_fn(min(1.0, u + 1e-3))
            x1, z1 = centre_fn(max(0.0, u - 1e-3))
            tx, tz = x2 - x1, z2 - z1
            length = math.hypot(tx, tz) or 1.0
            nx, nz = -tz / length, tx / length
            w = max(width_fn(u), 1e-4)
            t = max(thick_fn(u), 1e-4)
            row, uvrow = [], []
            for k in range(nv):
                a = TAU * k / nv
                yy = math.cos(a)
                off = spow(math.sin(a), edge) * t * 0.5
                off += cup * w * yy * yy - crease * w * (1.0 - abs(yy)) ** 2
                row.append((x + nx * off, w * yy, z + nz * off))
                uvrow.append((0.5 + 0.5 * yy, u))
            rows.append(row)
            uvs.append(uvrow)
        return self.grid(rows, close_u=True, cap_start=True, cap_end=True, m=m, uvs=uvs if uv else None)

    def fluted(self, z0, z1, r_fn, folds=12, depth_fn=None, nz=12, per_fold=6, m=None, bend_fn=None,
               sx=1.0, sy=1.0, phase=0.0, sharp=0.55):
        """Pleated cloak body: radius r_fn(t) with inward cusps (folds). bend_fn(t) -> (dx, dy) offset."""
        segs = folds * per_fold
        rows = []
        for i in range(nz + 1):
            t = i / nz
            r = r_fn(t)
            d = depth_fn(t) if depth_fn else 0.18
            ox, oy = bend_fn(t) if bend_fn else (0.0, 0.0)
            row = []
            for k in range(segs):
                th = TAU * k / segs
                ph = (k / per_fold + phase) % 1.0
                ridge = abs(math.sin(math.pi * ph)) ** sharp
                rr = r * (1.0 - d + d * ridge)
                row.append((ox + rr * math.cos(th) * sx, oy + rr * math.sin(th) * sy, lerp(z0, z1, t)))
            rows.append(row)
        return self.grid(rows, close_u=True, cap_start=True, cap_end=True, m=m)

    def ring_arc(self, centre, radius, a0, a1, r, n=16, plane="XZ", segs=6, m=None, taper=False):
        cx, cy, cz = centre
        path, radii = [], []
        for i in range(n + 1):
            a = lerp(a0, a1, i / n)
            if plane == "XZ":
                path.append((cx + radius * math.cos(a), cy, cz + radius * math.sin(a)))
            elif plane == "XY":
                path.append((cx + radius * math.cos(a), cy + radius * math.sin(a), cz))
            else:
                path.append((cx, cy + radius * math.cos(a), cz + radius * math.sin(a)))
            radii.append(r * (math.sin(math.pi * i / n) ** 0.5 * 0.85 + 0.15) if taper else r)
        closed = abs(abs(a1 - a0) - TAU) < 1e-6
        if closed:
            path, radii = path[:-1], radii[:-1]
            pts = [Vector(p) for p in path]
            ref = Vector((0, 1, 0)) if plane == "XZ" else (Vector((0, 0, 1)) if plane == "XY" else Vector((1, 0, 0)))
            rows = []
            k = len(pts)
            for i in range(k):
                t = (pts[(i + 1) % k] - pts[i - 1]).normalized()
                b = t.cross(ref)
                rows.append([pts[i] + ref * (math.cos(TAU * s / segs) * r) + b * (math.sin(TAU * s / segs) * r)
                             for s in range(segs)])
            rows.append(rows[0])
            return self.grid(rows, close_u=True, m=m)
        ref = (0, 1, 0) if plane == "XZ" else ((0, 0, 1) if plane == "XY" else (1, 0, 0))
        return self.tube(path, radii, segs=segs, ref=ref, m=m)

    def spike(self, base, tip, r, segs=6, m=None, bulb=0.0):
        """Tapered spike from base to tip, optional bulb near the base (turned finial)."""
        base, tip = Vector(base), Vector(tip)
        path, radii = [], []
        for i in range(7):
            t = i / 6
            path.append(base.lerp(tip, t))
            rr = r * (1.0 - t) ** 0.8
            if bulb:
                rr += r * bulb * math.exp(-((t - 0.18) / 0.09) ** 2)
            radii.append(max(rr, 0.002))
        return self.tube(path, radii, segs=segs, m=m)

    # ------------------------------------------------------------------ output
    def empty(self):
        return len(self.bm.verts) == 0

    def to_object(self, name, coll, materials, props=None, smooth_angle=42.0):
        if self.empty():
            self.bm.free()
            return None
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts[:], dist=1e-5)
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces[:])
        mesh = bpy.data.meshes.new(name + "_mesh")
        self.bm.to_mesh(mesh)
        self.bm.free()
        for key in self.keys:
            mesh.materials.append(materials(key) if callable(materials) else materials[key])
        try:
            mesh.set_sharp_from_angle(angle=math.radians(smooth_angle))
        except Exception:
            pass
        obj = bpy.data.objects.new(name, mesh)
        for k, v in (props or {}).items():
            obj[k] = v
        coll.objects.link(obj)
        return obj


# ---------------------------------------------------------------------- 2D helpers for ironwork (XZ plane)
def spiral_pts(cx, cz, r0, turns, a0, ccw=True, r1=0.02, n=None):
    n = n or max(10, int(turns * 16))
    out = []
    for i in range(n + 1):
        t = i / n
        a = a0 + (TAU * turns * t) * (1 if ccw else -1)
        r = r0 * (1 - t) + r1 * t
        out.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return out


def arc_pts(cx, cz, r, a0, a1, n=12, rz=None):
    rz = r if rz is None else rz
    return [(cx + r * math.cos(lerp(a0, a1, i / n)), cz + rz * math.sin(lerp(a0, a1, i / n))) for i in range(n + 1)]


def bez(p0, p1, p2, p3, n=12):
    out = []
    for i in range(n + 1):
        t = i / n
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t * t
        d = t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


class IronCurves:
    """Collects splines for one bevelled curve object. Points are (x, z) in the local XZ plane or (x, y, z)."""

    def __init__(self):
        self.splines = []

    def add(self, pts, r=1.0, cyclic=False, smooth=True, mirror_x=None, taper=None):
        """r: radius scale (number or per-point list). taper='end'|'both'|'start' fades the radius."""
        pts3 = [Vector((p[0], 0.0, p[1])) if len(p) == 2 else Vector(p) for p in pts]
        n = len(pts3)
        radii = list(r) if isinstance(r, (list, tuple)) else [r] * n
        if taper:
            for i in range(n):
                t = i / max(1, n - 1)
                if taper == "end":
                    radii[i] *= max(0.08, 1 - t ** 1.5)
                elif taper == "start":
                    radii[i] *= max(0.08, 1 - (1 - t) ** 1.5)
                elif taper == "both":
                    radii[i] *= max(0.12, math.sin(math.pi * t) ** 0.6)
        self.splines.append((pts3, radii, cyclic, smooth))
        if mirror_x is not None:
            self.splines.append(([Vector((2 * mirror_x - p.x, p.y, p.z)) for p in pts3], list(radii), cyclic, smooth))
        return self

    def spike(self, x, z0, z1, r=1.6, bulb=True, y=0.0):
        """Vertical finial: turned bulb then a long tapered point."""
        h = z1 - z0
        pts = [(x, y, z0), (x, y, z0 + h * 0.10), (x, y, z0 + h * 0.20), (x, y, z0 + h * 0.30), (x, y, z0 + h * 0.6), (x, y, z1)]
        rad = [r * 0.6, r * (1.5 if bulb else 0.9), r * 0.55, r * 0.95, r * 0.45, 0.05]
        self.splines.append(([Vector(p) for p in pts], rad, False, True))
        return self

    def transformed(self, m):
        out = IronCurves()
        for pts, radii, cyc, sm in self.splines:
            out.splines.append(([m @ p for p in pts], list(radii), cyc, sm))
        return out

    def extend(self, other, m=None):
        for pts, radii, cyc, sm in other.splines:
            self.splines.append(([m @ p for p in pts] if m is not None else list(pts), list(radii), cyc, sm))
        return self

    def to_object(self, name, coll, material, bevel=0.03, props=None, resolution=2, bevel_res=2):
        curve = bpy.data.curves.new(name + "_curve", "CURVE")
        curve.dimensions = "3D"
        curve.bevel_depth = bevel
        curve.bevel_resolution = bevel_res
        curve.resolution_u = resolution
        curve.use_fill_caps = True
        for pts, radii, cyclic, smooth in self.splines:
            if smooth and len(pts) > 2:
                sp = curve.splines.new("BEZIER")
                sp.bezier_points.add(len(pts) - 1)
                for bp, p, r in zip(sp.bezier_points, pts, radii):
                    bp.co = p
                    bp.radius = r
                    bp.handle_left_type = bp.handle_right_type = "AUTO"
            else:
                sp = curve.splines.new("POLY")
                sp.points.add(len(pts) - 1)
                for pp, p, r in zip(sp.points, pts, radii):
                    pp.co = (p.x, p.y, p.z, 1.0)
                    pp.radius = r
            sp.use_cyclic_u = cyclic
        curve.materials.append(material)
        obj = bpy.data.objects.new(name, curve)
        for k, v in (props or {}).items():
            obj[k] = v
        coll.objects.link(obj)
        return obj


def instance(obj, name, coll, m, props=None):
    """Linked duplicate (shares mesh/curve data) placed with matrix m."""
    dup = bpy.data.objects.new(name, obj.data)
    dup.matrix_world = m
    for k in obj.keys():
        dup[k] = obj[k]
    for k, v in (props or {}).items():
        dup[k] = v
    coll.objects.link(dup)
    return dup


def fbm(x, y, z, octaves=3):
    v, amp, f = 0.0, 1.0, 1.0
    for _ in range(octaves):
        v += amp * noise.noise(Vector((x * f, y * f, z * f)))
        amp *= 0.5
        f *= 2.0
    return v


def catmull(points, per=6):
    """Catmull-Rom interpolation through 2D or 3D points; returns tuples."""
    pts = [tuple(p) for p in points]
    if len(pts) < 3:
        return pts
    ext = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(per):
            t = k / per
            out.append(tuple(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t ** 3)
                             for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(pts[-1])
    return out


def resample(values, n):
    """Linear resample of a list of numbers to n entries."""
    if len(values) == n:
        return list(values)
    out = []
    for i in range(n):
        f = i / (n - 1) * (len(values) - 1)
        a = int(math.floor(f))
        b = min(a + 1, len(values) - 1)
        out.append(lerp(values[a], values[b], f - a))
    return out
