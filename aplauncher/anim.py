"""Frame-clock animation engine for tkinter.

All animations share one timer that ticks at the monitor's refresh rate. Every animation computes its state
from the real time that has passed, so a late frame never slows an animation down, it only skips ahead.
When nothing animates the timer stops and the launcher costs no CPU.
"""
import atexit
import ctypes
import math
import time
import tkinter as tk


def refresh_rate() -> int:
    """Refresh rate of the primary monitor in Hz (60 if Windows does not say)."""
    try:
        user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
        hdc = user32.GetDC(0)
        hz = gdi32.GetDeviceCaps(hdc, 116)  # VREFRESH
        user32.ReleaseDC(0, hdc)
        return hz if 30 <= hz <= 500 else 60
    except (AttributeError, OSError):
        return 60


def _fine_timer():
    """Windows timers tick every 15.6 ms by default, too coarse for 60+ fps."""
    try:
        winmm = ctypes.windll.winmm
        winmm.timeBeginPeriod(1)
        atexit.register(winmm.timeEndPeriod, 1)
    except (AttributeError, OSError):
        pass


# ----- easing -----
def linear(t):
    return t


def out_cubic(t):
    return 1 - (1 - t) ** 3


def out_quint(t):
    return 1 - (1 - t) ** 5


def in_out_cubic(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def in_out_sine(t):
    return -(math.cos(math.pi * t) - 1) / 2


def out_back(t, s=1.70158):
    t -= 1
    return 1 + (s + 1) * t ** 3 + s * t ** 2


def lerp(a, b, t):
    return a + (b - a) * t


_rgb_cache = {}


def _rgb(c):
    v = _rgb_cache.get(c)
    if v is None:
        h = c.lstrip("#")
        v = _rgb_cache[c] = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return v


def mix(a: str, b: str, t: float) -> str:
    """Colour between a and b (t=0 → a, t=1 → b)."""
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    ca, cb = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))


class Engine:
    def __init__(self):
        self.hz = refresh_rate()
        self.period = 1.0 / self.hz
        self.items = []
        self.root = None
        self.job = None
        self.next = 0.0
        _fine_timer()

    def add(self, item):
        if self.root is None:
            self.root = item.widget._root()
        self.items.append(item)
        if self.job is None:
            self.next = time.perf_counter()
            self.job = self.root.after(1, self._tick)

    def _tick(self):
        now = time.perf_counter()
        for item in list(self.items):
            alive = False
            try:
                alive = item.widget.winfo_exists() and item.step(now)
            except tk.TclError:
                pass
            if not alive and item in self.items:
                self.items.remove(item)
                item.active = False
        if not self.items:
            self.job = None
            return
        # Full refresh rate while anything real moves; slow ambient loops alone get a lower rate.
        caps = [i.cap for i in self.items]
        period = self.period if None in caps else max(self.period, 1.0 / max(caps))
        # Keep a steady cadence: aim at the next frame boundary, skip frames we already missed.
        self.next += period
        if self.next < now:
            self.next = now + period
        delay = max(1, int((self.next - time.perf_counter()) * 1000 + 0.5))
        try:
            self.job = self.root.after(delay, self._tick)
        except tk.TclError:
            self.job = None


engine = Engine()


class _Item:
    active = False
    cap = None  # max frames per second this item needs; None = the monitor's refresh rate

    def __init__(self, widget):
        self.widget = widget

    def start(self):
        if not self.active:
            self.active = True
            engine.add(self)
        return self

    def cancel(self):
        if self.active and self in engine.items:
            engine.items.remove(self)
        self.active = False


class Tween(_Item):
    """Runs update(eased t) for ms milliseconds, then done()."""

    def __init__(self, widget, ms, update, ease=out_cubic, done=None, delay=0):
        super().__init__(widget)
        self.ms, self.update, self.ease, self.done = max(1, ms), update, ease, done
        self.t0 = time.perf_counter() + delay / 1000
        self.start()

    def step(self, now):
        if now < self.t0:
            return True
        t = min(1.0, (now - self.t0) * 1000 / self.ms)
        self.update(self.ease(t))
        if t >= 1:
            self.active = False
            if self.done:
                self.done()
            return False
        return True


class Value(_Item):
    """A number that glides to whatever target it gets, also when retargeted mid-flight."""

    def __init__(self, widget, value, update, ms=180, ease=out_cubic):
        super().__init__(widget)
        self.value = self.target = float(value)
        self.update, self.ms, self.ease = update, ms, ease
        self.from_ = self.value
        self.t0 = 0.0
        self.dur = ms

    def to(self, target, ms=None):
        target = float(target)
        if target == self.target and (self.active or self.value == target):
            return
        self.from_, self.target = self.value, target
        self.dur = max(1, self.ms if ms is None else ms)
        self.t0 = time.perf_counter()
        self.start()

    def set(self, value):
        self.cancel()
        self.value = self.target = float(value)
        self.update(self.value)

    def step(self, now):
        t = min(1.0, (now - self.t0) * 1000 / self.dur)
        self.value = lerp(self.from_, self.target, self.ease(t))
        self.update(self.value)
        return t < 1


class Spring(_Item):
    """Damped spring: values overshoot a little and settle, which reads as 'physical' motion."""

    def __init__(self, widget, values, update, stiffness=320.0, damping=0.72):
        super().__init__(widget)
        self.x = [float(v) for v in values]
        self.v = [0.0] * len(self.x)
        self.goal = list(self.x)
        self.k = [stiffness] * len(self.x) if not isinstance(stiffness, (list, tuple)) else list(stiffness)
        self.zeta = damping
        self.update = update
        self.last = 0.0

    def to(self, goal, stiffness=None):
        self.goal = [float(g) for g in goal]
        if stiffness is not None:
            self.k = list(stiffness) if isinstance(stiffness, (list, tuple)) else [stiffness] * len(self.x)
        if not self.active:
            self.last = time.perf_counter()
        self.start()

    def set(self, values):
        self.cancel()
        self.x = [float(v) for v in values]
        self.goal = list(self.x)
        self.v = [0.0] * len(self.x)
        self.update(*self.x)

    def step(self, now):
        dt = min(now - self.last, 1 / 20)
        self.last = now
        n = max(1, int(dt / 0.004))  # small fixed sub-steps keep the spring stable at any frame rate
        h = dt / n
        settled = True
        for i in range(len(self.x)):
            k = self.k[i]
            c = 2 * math.sqrt(k) * self.zeta
            x, v, g = self.x[i], self.v[i], self.goal[i]
            for _ in range(n):
                v += (-k * (x - g) - c * v) * h
                x += v * h
            if abs(x - g) < 0.05 and abs(v) < 0.5:
                x, v = g, 0.0
            else:
                settled = False
            self.x[i], self.v[i] = x, v
        self.update(*self.x)
        return not settled


class Loop(_Item):
    """Endless animation: fn(seconds since start). Pauses while the window is minimised.

    fps limits how often an ambient loop needs a frame. Ambient loops also pause while the launcher does not
    have the focus (e.g. while playing), so decoration costs nothing in the background."""
    PAUSED_FPS = 4

    def __init__(self, widget, fn, start=True, fps=None, ambient=False):
        super().__init__(widget)
        self.fn, self.fps, self.ambient = fn, fps, ambient
        self.t0 = time.perf_counter()
        self.hidden, self.checked = False, 0.0
        if start:
            self.start()

    @property
    def cap(self):
        return self.PAUSED_FPS if self.hidden else self.fps

    def step(self, now):
        if now - self.checked > 0.25:  # asking Tk every frame costs more than the check is worth
            self.checked = now
            try:
                w = self.widget
                self.hidden = (w.winfo_toplevel().state() == "iconic" or not w.winfo_viewable()
                               or (self.ambient and w.focus_displayof() is None))
            except (tk.TclError, KeyError):
                return False
        if not self.hidden:
            self.fn(now - self.t0)
        return True
