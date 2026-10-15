"""Stage 5 v008 camera rig: smooth time-parameterised spline paths for camera, look target and lens.

Pure Python + mathutils so it runs inside Blender (builder, worker, audit) identically.
Each sequence holds keys {t, pos, look, lens?, roll?}. Position and look use non-uniform
Catmull-Rom (cubic Hermite with tangents from neighbours, time-parameterised), giving C1
continuous position and velocity. End tangents can be 'hold' (zero velocity, used only at
the film start/end) or 'flow' (keep the velocity, used where a sequence hands over to the
next one through a dissolve or a matched cut). An optional per-sequence time-warp remaps
sequence time to path time with smooth speed changes.
"""
import math
from mathutils import Vector, Matrix, Quaternion


def _hermite(p0, m0, p1, m1, u, dt):
    u2 = u * u; u3 = u2 * u
    h00 = 2 * u3 - 3 * u2 + 1; h10 = u3 - 2 * u2 + u
    h01 = -2 * u3 + 3 * u2; h11 = u3 - u2
    return p0 * h00 + m0 * (h10 * dt) + p1 * h01 + m1 * (h11 * dt)


class Track:
    """Time-parameterised cubic Hermite spline through (t, value) samples."""

    def __init__(self, times, values, start='flow', end='flow', start_vel=None, end_vel=None):
        assert len(times) == len(values) >= 2
        assert all(times[i] < times[i + 1] for i in range(len(times) - 1)), times
        self.t = list(times)
        self.v = [Vector((float(x), 0.0)) if isinstance(x, (int, float)) else (Vector((float(x[0]), 0.0)) if len(x) == 1 else Vector(x)) for x in values]
        n = len(self.t)
        m = []
        for i in range(n):
            if 0 < i < n - 1:
                # Non-uniform Catmull-Rom / finite-difference tangent (weighted by interval lengths).
                d0 = (self.v[i] - self.v[i - 1]) / (self.t[i] - self.t[i - 1])
                d1 = (self.v[i + 1] - self.v[i]) / (self.t[i + 1] - self.t[i])
                w0 = self.t[i + 1] - self.t[i]; w1 = self.t[i] - self.t[i - 1]
                m.append((d0 * w0 + d1 * w1) / (w0 + w1))
            else:
                m.append(None)
        z = self.v[0] * 0
        first = (self.v[1] - self.v[0]) / (self.t[1] - self.t[0])
        last = (self.v[-1] - self.v[-2]) / (self.t[-1] - self.t[-2])
        if n == 2:
            m[0] = z if start == 'hold' else first
            m[1] = z if end == 'hold' else last
        else:
            # 'flow' end: natural-spline style end tangent so the path keeps moving smoothly.
            m[0] = z if start == 'hold' else (first * 1.5 - m[1] * 0.5)
            m[-1] = z if end == 'hold' else (last * 1.5 - m[-2] * 0.5)
        if start_vel is not None: m[0] = Vector(start_vel)
        if end_vel is not None: m[-1] = Vector(end_vel)
        self.m = m

    def at(self, t):
        ts = self.t
        if t <= ts[0]:
            return self.v[0] + self.m[0] * (t - ts[0])
        if t >= ts[-1]:
            return self.v[-1] + self.m[-1] * (t - ts[-1])
        i = max(j for j in range(len(ts) - 1) if ts[j] <= t)
        dt = ts[i + 1] - ts[i]
        return _hermite(self.v[i], self.m[i], self.v[i + 1], self.m[i + 1], (t - ts[i]) / dt, dt)


def _noise(t, seed, freqs=(0.11, 0.23, 0.37)):
    """Smooth deterministic float noise in [-1, 1] (sum of incommensurate sines)."""
    v = 0.0; a = 0.0
    for k, f in enumerate(freqs):
        w = 1.0 / (k + 1)
        v += w * math.sin(2 * math.pi * f * t + seed * (1.7 + k * 2.3))
        a += w
    return v / a


class TimeWarp:
    """Change dwell time without changing the original spatial spline.

    Map path time to screen time by integrating a nonnegative speed window:
    quintic ramps, a constant middle, then a quintic ramp out. The inverse is
    monotone, with continuous speed and acceleration at the window edges.
    """
    def __init__(self, windows):
        self.windows = windows
        for w in windows:
            length = w['path_end'] - w['path_start']
            fraction = w.get('ramp_fraction', .15)
            assert length > 0 and 0 < fraction <= .5
            assert 1 + min(w['seconds_delta'], 0) / (length * (1 - fraction)) > 0
        assert all(windows[i]['path_end'] <= windows[i + 1]['path_start'] for i in range(len(windows) - 1))

    @staticmethod
    def _integral(u):
        # Integral from 0 to u of 10u^3 - 15u^4 + 6u^5.
        return 2.5 * u**4 - 3 * u**5 + u**6

    def screen_time(self, path_time):
        result = path_time
        for w in self.windows:
            length = w['path_end'] - w['path_start']
            x = path_time - w['path_start']
            ramp = length * w.get('ramp_fraction', .15)
            area = length - ramp
            if x <= 0: progress = 0
            elif x >= length: progress = 1
            elif x < ramp: progress = ramp * self._integral(x / ramp) / area
            elif x <= length - ramp: progress = (x - ramp / 2) / area
            else: progress = 1 - ramp * self._integral((length - x) / ramp) / area
            result += w['seconds_delta'] * progress
        return result

    def path_time(self, screen_time):
        if not self.windows: return screen_time
        lo = self.windows[0]['path_start']; hi = self.windows[-1]['path_end']
        if screen_time <= self.screen_time(lo): return screen_time
        if screen_time >= self.screen_time(hi):
            return screen_time - sum(w['seconds_delta'] for w in self.windows)
        for _ in range(42):
            mid = (lo + hi) / 2
            if self.screen_time(mid) < screen_time: lo = mid
            else: hi = mid
        return (lo + hi) / 2


class Sequence:
    def __init__(self, spec, fps=24):
        self.spec = spec
        self.fps = fps
        keys = spec['keys']
        times = [k['t'] for k in keys]
        start = spec.get('start', 'flow'); end = spec.get('end', 'flow')
        self.pos = Track(times, [k['pos'] for k in keys], start, end)
        # Look is interpolated as a direction (plus a focus distance), not as a point: a moving
        # look point can swing close to the camera and cause whip pans; directions keep the turn
        # rate proportional to the angle between consecutive keys.
        dirs = [(Vector(k['look']) - Vector(k['pos'])) for k in keys]
        self.dist = Track(times, [(d.length,) for d in dirs], start, end)
        self.dir = Track(times, [d.normalized() for d in dirs], start, end)
        lens_keys = [(k['t'], k['lens']) for k in keys if 'lens' in k]
        if len(lens_keys) < 2:
            lens_keys = [(times[0], lens_keys[0][1] if lens_keys else spec.get('lens', 24)), (times[-1], lens_keys[0][1] if lens_keys else spec.get('lens', 24))]
        self.lens = Track([a for a, b in lens_keys], [(b,) for a, b in lens_keys], 'hold', 'hold')
        roll_keys = [(k['t'], k['roll']) for k in keys if 'roll' in k]
        self.roll = Track([a for a, b in roll_keys], [(b,) for a, b in roll_keys], 'hold', 'hold') if len(roll_keys) >= 2 else None
        self.bank = spec.get('bank', 0.35)        # degrees of roll per (unit lateral accel / speed)
        self.bank_max = spec.get('bank_max', 2.0)
        self.float_amp = spec.get('float', 0.06)  # position float in H
        self.float_rot = spec.get('float_rot', 0.15)  # degrees
        self.seed = spec.get('seed', 1)
        self.duration = spec['seconds']
        self.t0 = times[0]
        self.time_warp = TimeWarp(spec.get('time_warp', []))

    def _bank(self, t):
        h = 1.0 / self.fps
        p0 = self.pos.at(t - h); p1 = self.pos.at(t); p2 = self.pos.at(t + h)
        v = (p2 - p0) / (2 * h); a = (p2 - 2 * p1 + p0) / (h * h)
        horiz = Vector((v.x, v.y, 0))
        if horiz.length < 0.3:
            return 0.0
        side = Vector((-horiz.y, horiz.x, 0)).normalized()  # left of travel direction
        lat = a.dot(side)  # H/s^2, positive when turning left
        # Positive roll about the camera's local +Z (pointing back at the viewer) tilts the camera's top
        # to the left, i.e. banks left: bank into the turn like a flying camera.
        return max(-self.bank_max, min(self.bank_max, self.bank * lat))

    def sample(self, t):
        """Return (location, rotation quaternion, lens, look point) at sequence time t (seconds)."""
        t = self.time_warp.path_time(t)
        p = self.pos.at(t)
        d0 = self.dir.at(t).normalized()
        look = p + d0 * max(self.dist.at(t)[0], 1.0)
        fa = self.float_amp
        if fa:
            p = p + Vector((_noise(t, self.seed), _noise(t, self.seed + 11), _noise(t, self.seed + 23) * 0.7)) * fa
        d = (look - p).normalized()
        q = d.to_track_quat('-Z', 'Y')
        roll = self._bank(t)
        if self.roll is not None:
            roll += self.roll.at(t)[0]
        fr = self.float_rot
        yaw = _noise(t, self.seed + 31) * fr; pitch = _noise(t, self.seed + 41) * fr * 0.8
        q = q @ Quaternion((0, 1, 0), math.radians(yaw)) @ Quaternion((1, 0, 0), math.radians(pitch)) @ Quaternion((0, 0, 1), math.radians(roll))
        return p, q, self.lens.at(t)[0], look

    def frames(self):
        n = round(self.duration * self.fps)
        return n


def matrix(p, q):
    m = q.to_matrix().to_4x4(); m.translation = p
    return m
