"""Vorschau: animierter Launcher-Prototyp. Nur zum Ausprobieren, nicht Teil des Launchers.

Start:   py -3.14 preview\\fancy_launcher.py            (Bildrate = Monitorfrequenz)
         py -3.14 preview\\fancy_launcher.py --fps 165
Tasten:  1-4 Tabs, F Bildraten-Anzeige, Q Effekte hoch/niedrig, F11 Vollbild, Esc Vollbild aus

Alles ist auf einem einzigen Canvas gezeichnet und wird jedes Bild neu positioniert. Bewegungen laufen über
Federn (Spring) mit echter Zeit (dt), dadurch sehen sie bei 60, 144 oder 165 Hz gleich aus, nur flüssiger.
Die Daten (Mitspieler, Funde, Log, Ping) sind ausgedacht.
"""
import colorsys
import ctypes
import math
import random
import sys
import time
import tkinter as tk
import tkinter.font as tkfont

BG = "#0c0716"
PANEL = "#181029"
PANEL_HI = "#241943"
BORDER = "#31255a"
FG = "#f1ecff"
MUTED = "#9a8cc4"
ACCENT = "#8b5cf6"
ACCENT_HI = "#b79bff"
PINK = "#f472b6"
CYAN = "#5eead4"
GOLD = "#fcd34d"
GREEN = "#5ee0a0"
RUN = "#10b981"
RED = "#ff6b86"
WHITE = "#ffffff"

GAMES = [
    dict(name="Super Mario 64", sub="sm64ex · 60 FPS · eigene ROM", col=GOLD, done=64, total=120),
    dict(name="Ocarina of Time", sub="Ship of Harkinian · AP 1.4.2", col=GREEN, done=112, total=216),
]
PLAYERS = [
    dict(name="Nova", game=0, prog=0.62, hue=0.78),
    dict(name="Kiwi", game=1, prog=0.48, hue=0.42),
    dict(name="Pixel", game=0, prog=0.31, hue=0.12),
    dict(name="Mondlicht", game=1, prog=0.77, hue=0.92),
]
ITEMS = [["Power-Stern", "Flügelkappe", "Schlüssel 1", "Metallkappe", "Kanone", "Tarnkappe"],
         ["Hookshot", "Bomben-Tasche", "Herzteil", "Feuerpfeile", "Eisenstiefel", "Bumerang"]]
STEPS = [
    ("Archipelago", "Silent-Install · Server, Client, Generator"),
    ("Ship of Harkinian", "SoH-Zip + oot.o2r aus eigener ROM"),
    ("MSYS2", "Build-Umgebung für sm64ex"),
    ("sm64ex", "Archipelago-Build aus eigener ROM · 60 FPS"),
    ("Universal Tracker", "tracker.apworld + Brücken-apworld"),
]


# ---------------------------------------------------------------- helpers

def rgb(c):
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def hexc(r, g, b):
    return "#%02x%02x%02x" % (max(0, min(255, int(r))), max(0, min(255, int(g))), max(0, min(255, int(b))))


_MIX = {}


def mix(a, b, t):
    """Farbe zwischen a und b, in 64 Stufen gecacht: schneller, und die Farbe ändert sich seltener."""
    q = 0 if t <= 0 else 64 if t >= 1 else int(t * 64 + 0.5)
    key = (a, b, q)
    col = _MIX.get(key)
    if col is None:
        if len(_MIX) > 50000:
            _MIX.clear()
        f = q / 64
        ra, ga, ba = rgb(a)
        rb, gb, bb = rgb(b)
        col = _MIX[key] = hexc(ra + (rb - ra) * f, ga + (gb - ga) * f, ba + (bb - ba) * f)
    return col


def hsv(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return hexc(r * 255, g * 255, b * 255)


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def rrect(x1, y1, x2, y2, r):
    r = max(0.0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
            x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


def pick_font(root, names):
    families = set(tkfont.families(root))
    return next((n for n in names if n in families), "Helvetica")


class Spring:
    """Gedämpfte Feder: value läuft zu target, mit Schwung (wenig Dämpfung = Überschwingen)."""

    def __init__(self, value=0.0, k=170.0, d=20.0):
        self.v = self.target = float(value)
        self.vel = 0.0
        self.k, self.d = k, d

    def to(self, target):
        self.target = float(target)
        return self

    def snap(self, value):
        self.v = self.target = float(value)
        self.vel = 0.0

    def step(self, dt):
        n = max(1, math.ceil(dt / 0.004))
        h = dt / n
        for _ in range(n):
            self.vel += (self.k * (self.target - self.v) - self.d * self.vel) * h
            self.v += self.vel * h
        return self.v


class Gfx:
    """Canvas-Aufrufe nur, wenn sich wirklich etwas ändert (spart Tcl-Aufrufe bei 165 Bildern/s)."""

    def __init__(self, canvas):
        self.c = canvas
        self._call, self._w = canvas.tk.call, canvas._w
        self._xy, self._kw = {}, {}

    def xy(self, item, pts):
        key = tuple(map(round, pts))  # Tk zeichnet sowieso auf ganze Pixel
        if self._xy.get(item) != key:
            self._xy[item] = key
            self._call(self._w, "coords", item, *key)

    def cfg(self, item, **kw):
        old = self._kw.setdefault(item, {})
        args = []
        for k, v in kw.items():
            if old.get(k) != v:
                old[k] = v
                args += ("-" + k, v)
        if args:
            self._call(self._w, "itemconfigure", item, *args)

    def forget_state(self, items):
        for item in items:
            self._kw.get(item, {}).pop("state", None)

    def delete(self, item):
        self.c.delete(item)
        self._xy.pop(item, None)
        self._kw.pop(item, None)


def win_setup():
    """Windows: 1-ms-Timer (sonst ist after() auf ~64 Hz begrenzt) und scharfe Darstellung bei Skalierung."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def monitor_hz(default=165):
    if sys.platform == "win32":
        try:
            user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
            hdc = user32.GetDC(0)
            hz = gdi32.GetDeviceCaps(hdc, 116)  # VREFRESH
            user32.ReleaseDC(0, hdc)
            if hz > 1:
                return hz
        except Exception:
            pass
    return default


def dark_titlebar(root):
    if sys.platform != "win32":
        return
    try:
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass


# ---------------------------------------------------------------- background

class Aurora:
    """Drei weiche Farbwolken. Ringe werden ebenenweise über alle Wolken gestapelt, damit sie ineinanderfließen."""
    COLORS = [ACCENT, PINK, CYAN]
    RINGS = 18

    def __init__(self, app):
        self.app = app
        self.blobs = [dict(col=col, phase=random.uniform(0, 6.28), speed=0.06 + 0.025 * i, items=[])
                      for i, col in enumerate(self.COLORS)]
        for _ in range(self.RINGS):
            for b in self.blobs:
                b["items"].append(app.c.create_oval(0, 0, 0, 0, fill=BG, outline=""))

    def update(self, dt, t):
        app, g = self.app, self.app.g
        W, H = app.W, app.H
        px = (app.mx - W / 2) * 0.03 if app.mouse_in else 0
        py = (app.my - H / 2) * 0.03 if app.mouse_in else 0
        run = app.run.v
        rings = self.RINGS if app.quality else self.RINGS // 2
        for i, b in enumerate(self.blobs):
            s, ph = b["speed"], b["phase"]
            cx = W * (0.15 + 0.7 * (0.5 + 0.5 * math.sin(t * s * 1.3 + ph))) - px * (1 + i * 0.5)
            cy = H * (0.2 + 0.6 * (0.5 + 0.5 * math.cos(t * s + ph * 1.7))) - py * (1 + i * 0.5)
            R = max(W, H) * (0.34 + 0.05 * math.sin(t * 0.5 + i))
            col = mix(b["col"], RUN, run * 0.7)
            inten = 0.15 + 0.04 * math.sin(t * 0.8 + i * 2.1)
            for j, item in enumerate(b["items"]):
                if j >= rings:
                    g.xy(item, (0, 0, 0, 0))
                    continue
                f = (j + 1) / rings
                r = R * (1 - f * 0.86)
                g.xy(item, (cx - r, cy - r * 0.8, cx + r, cy + r * 0.8))
                g.cfg(item, fill=mix(BG, col, inten * f ** 1.3))


class Stars:
    """Glitzernde Partikel mit Parallaxe; weichen der Maus aus und verbinden sich mit ihr."""
    N = 80

    def __init__(self, app):
        self.app = app
        self.p = []
        for _ in range(self.N):
            z = random.uniform(0.25, 1.0)
            self.p.append(dict(x=random.random(), y=random.random(), z=z, ox=0.0, oy=0.0,
                               tw=random.uniform(1.0, 3.5), ph=random.uniform(0, 6.28),
                               col=random.choice([FG, ACCENT_HI, CYAN, PINK, FG]),
                               item=app.c.create_oval(0, 0, 0, 0, fill=BG, outline="")))
        self.lines = [app.c.create_line(0, 0, 0, 0, fill=BG, width=1) for _ in range(9)]

    def update(self, dt, t):
        app, g, k = self.app, self.app.g, self.app.k
        W, H = app.W, app.H
        mx, my, inside = app.mx, app.my, app.mouse_in
        count = self.N if app.quality else self.N // 3
        R = 150 * k
        near = []
        decay = math.exp(-2.5 * dt)
        speed = 0.012 + 0.05 * app.run.v
        for i, p in enumerate(self.p):
            if i >= count:
                g.xy(p["item"], (0, 0, 0, 0))
                continue
            z = p["z"]
            p["y"] -= speed * z * dt
            if p["y"] < -0.02:
                p["y"] += 1.04
                p["x"] = random.random()
            x = p["x"] * W + ((W / 2 - mx) * 0.04 * z if inside else 0)
            y = p["y"] * H + ((H / 2 - my) * 0.04 * z if inside else 0)
            if inside:
                dx, dy = x + p["ox"] - mx, y + p["oy"] - my
                d = math.hypot(dx, dy) or 1
                if d < R:
                    push = (1 - d / R) * 900 * k * z * dt
                    p["ox"] += dx / d * push
                    p["oy"] += dy / d * push
                    near.append((d, x + p["ox"], y + p["oy"]))
            p["ox"] *= decay
            p["oy"] *= decay
            x, y = x + p["ox"], y + p["oy"]
            tw = 0.5 + 0.5 * math.sin(t * p["tw"] + p["ph"])
            r = (0.8 + 1.8 * z) * k * (0.8 + 0.4 * tw)
            g.xy(p["item"], (x - r, y - r, x + r, y + r))
            g.cfg(p["item"], fill=mix(BG, p["col"], (0.25 + 0.75 * tw) * (0.35 + 0.65 * z)))
        near.sort()
        for i, line in enumerate(self.lines):
            if i < len(near):
                d, x, y = near[i]
                g.xy(line, (mx, my, x, y))
                g.cfg(line, fill=mix(BG, ACCENT_HI, 0.55 * (1 - d / R)))
            else:
                g.xy(line, (0, 0, 0, 0))


# ---------------------------------------------------------------- header, tabs, overlays

class Title:
    TEXT = "ARCHIPELAGO"

    def __init__(self, app):
        self.app = app
        c = app.c
        self.offs = [app.f_title.measure(self.TEXT[:i]) for i in range(len(self.TEXT))]
        self.width = app.f_title.measure(self.TEXT)
        self.drop = [Spring(-70 * app.k, 160, 13) for _ in self.TEXT]
        self.delay = [0.15 + i * 0.045 for i in range(len(self.TEXT))]
        self.amp = Spring(1, 120, 14)
        self.shadow = [c.create_text(0, 0, text=ch, font=app.f_title, fill=BG, anchor="w") for ch in self.TEXT]
        self.main = [c.create_text(0, 0, text=ch, font=app.f_title, fill=BG, anchor="w") for ch in self.TEXT]
        self.sub = c.create_text(0, 0, text="L A U N C H E R   ·   V O R S C H A U", font=app.f_small,
                                 fill=MUTED, anchor="w")
        self.line = c.create_line(0, 0, 0, 0, fill=ACCENT, width=2 * app.k, capstyle="round")

    def update(self, dt, t):
        app, g, k = self.app, self.app.g, self.app.k
        x0, y0 = 30 * k, 50 * k
        hovered = app.hover == "title"
        self.amp.to(2.6 if hovered else 1).step(dt)
        app.hit(x0, y0 - 28 * k, x0 + self.width, y0 + 28 * k, "title")
        for i in range(len(self.TEXT)):
            s = self.drop[i]
            if t > self.delay[i]:
                s.to(0)
            dy = s.step(dt) + math.sin(t * 2.2 - i * 0.5) * 2.5 * k * self.amp.v
            x = x0 + self.offs[i]
            col = hsv(0.76 + 0.09 * math.sin(t * 0.9 - i * 0.38), 0.42 + 0.1 * (self.amp.v - 1), 1.0)
            vis = clamp(1 + s.v / (70 * k))
            g.xy(self.shadow[i], (x + 1.5 * k, y0 + dy + 4 * k))
            g.cfg(self.shadow[i], fill=mix(BG, mix(ACCENT, PINK, 0.5 + 0.5 * math.sin(t + i)), 0.55 * vis))
            g.xy(self.main[i], (x, y0 + dy))
            g.cfg(self.main[i], fill=mix(BG, col, vis))
        g.xy(self.sub, (x0 + 2 * k, y0 + 36 * k))
        g.cfg(self.sub, fill=mix(BG, MUTED, clamp((t - 0.7) * 2)))
        grow = ease_out((t - 0.6) * 1.2)
        wob = 0.5 + 0.5 * math.sin(t * 1.4)
        g.xy(self.line, (x0 + 2 * k, y0 + 54 * k, x0 + 2 * k + (90 + 60 * wob) * k * grow, y0 + 54 * k))
        g.cfg(self.line, fill=mix(ACCENT, PINK, wob))


class Tabs:
    NAMES = ["Spielen", "Einrichtung", "Netzwerk", "Log"]

    def __init__(self, app):
        self.app = app
        c, k = app.c, app.k
        self.widths = [app.f_tab.measure(n) + 40 * k for n in self.NAMES]
        self.active = 0
        self.left = Spring(0, 260, 26)
        self.right = Spring(self.widths[0], 260, 26)
        self.page = Spring(0, 120, 19)
        self.hov = [Spring(0, 300, 26) for _ in self.NAMES]
        self.enter = Spring(-40 * k, 140, 15)
        self.track = c.create_polygon(rrect(0, 0, 1, 1, 1), smooth=True, fill=PANEL, outline=BORDER)
        self.glow = c.create_polygon(rrect(0, 0, 1, 1, 1), smooth=True, fill=BG, outline="")
        self.pill = c.create_polygon(rrect(0, 0, 1, 1, 1), smooth=True, fill=ACCENT, outline="")
        self.hl = c.create_polygon(rrect(0, 0, 1, 1, 1), smooth=True, fill=ACCENT_HI, outline="")
        self.texts = [c.create_text(0, 0, text=n, font=app.f_tab, fill=MUTED) for n in self.NAMES]

    def select(self, i):
        if i == self.active:
            return
        # Flüssiger Indikator: die vordere Kante zieht schneller als die hintere
        fwd = i > self.active
        self.left.k, self.right.k = (150, 420) if fwd else (420, 150)
        self.left.d, self.right.d = 2 * math.sqrt(self.left.k) * 0.8, 2 * math.sqrt(self.right.k) * 0.8
        self.active = i
        self.page.to(i)

    def update(self, dt, t):
        app, g, k = self.app, self.app.g, self.app.k
        if t > 0.35:
            self.enter.to(0)
        ey = self.enter.step(dt)
        x0, y, h = 30 * k, 128 * k + ey, 40 * k
        xs, x = [], x0
        for w in self.widths:
            xs.append(x)
            x += w + 4 * k
        self.left.to(xs[self.active] - x0)
        self.right.to(xs[self.active] - x0 + self.widths[self.active])
        lx, rx = x0 + self.left.step(dt), x0 + self.right.step(dt)
        self.page.step(dt)
        pad = 5 * k
        g.xy(self.track, rrect(x0 - pad, y - h / 2 - pad, x - 4 * k + pad, y + h / 2 + pad, h / 2 + pad))
        pulse = 0.5 + 0.5 * math.sin(t * 2.5)
        gl = 3 * k + 2 * k * pulse
        g.xy(self.glow, rrect(lx - gl, y - h / 2 - gl, rx + gl, y + h / 2 + gl, h / 2 + gl))
        g.cfg(self.glow, fill=mix(PANEL, ACCENT, 0.3 + 0.1 * pulse))
        g.xy(self.pill, rrect(lx, y - h / 2, rx, y + h / 2, h / 2))
        g.xy(self.hl, rrect(lx + 6 * k, y - h / 2 + 3 * k, rx - 6 * k, y - 2 * k, h / 4))
        g.cfg(self.hl, fill=mix(ACCENT, ACCENT_HI, 0.35))
        for i, item in enumerate(self.texts):
            hv = self.hov[i].to(1 if app.hover == ("tab", i) else 0).step(dt)
            cx = xs[i] + self.widths[i] / 2
            g.xy(item, (cx, y - hv * 1.5 * k))
            if i == self.active:
                g.cfg(item, fill=WHITE)
            else:
                g.cfg(item, fill=mix(MUTED, FG, hv))
            app.hit(xs[i], y - h / 2, xs[i] + self.widths[i], y + h / 2, ("tab", i),
                    click=lambda i=i: self.select(i))


class FpsMeter:
    N = 90

    def __init__(self, app):
        self.app = app
        c = app.c
        self.on = True
        self.times = [1 / app.fps] * self.N
        self.frames, self.acc, self.fps = 0, 0.0, float(app.fps)
        self.bg = c.create_polygon(rrect(0, 0, 1, 1, 1), smooth=True, fill=PANEL, outline=BORDER)
        self.target = c.create_line(0, 0, 0, 0, fill=BORDER, dash=(2, 3))
        self.graph = c.create_line(0, 0, 0, 0, fill=GREEN, width=1.5 * app.k)
        self.text = c.create_text(0, 0, text="", font=app.f_mono, fill=GREEN, anchor="ne")
        self.text2 = c.create_text(0, 0, text="", font=app.f_tiny, fill=MUTED, anchor="ne")

    def update(self, dt, t):
        app, g, k = self.app, self.app.g, self.app.k
        self.times.append(dt)
        del self.times[0]
        self.frames += 1
        self.acc += dt
        if self.acc >= 0.5:
            self.fps = self.frames / self.acc
            self.frames, self.acc = 0, 0.0
        items = (self.bg, self.target, self.graph, self.text, self.text2)
        if not self.on:
            for it in items:
                g.cfg(it, state="hidden")
            return
        for it in items:
            g.cfg(it, state="normal")
        x2, y1 = app.W - 22 * k, 20 * k
        w, h = 170 * k, 64 * k
        x1 = x2 - w
        g.xy(self.bg, rrect(x1, y1, x2, y1 + h, 12 * k))
        ratio = self.fps / app.fps
        col = GREEN if ratio > 0.9 else GOLD if ratio > 0.6 else RED
        g.cfg(self.text, text=f"{self.fps:5.0f} FPS", fill=col)
        g.xy(self.text, (x2 - 12 * k, y1 + 8 * k))
        g.cfg(self.text2, text=f"Ziel {app.fps} Hz · {'hoch' if app.quality else 'niedrig'}")
        g.xy(self.text2, (x2 - 12 * k, y1 + 28 * k))
        gx1, gx2, gy1, gy2 = x1 + 12 * k, x2 - 12 * k, y1 + 44 * k, y1 + h - 8 * k
        top = 2.5 / app.fps  # Graph geht bis 2,5x der Zielzeit
        ty = gy2 - (1 / app.fps) / top * (gy2 - gy1)
        g.xy(self.target, (gx1, ty, gx2, ty))
        pts = []
        for i, ft in enumerate(self.times):
            pts += [gx1 + (gx2 - gx1) * i / (self.N - 1), gy2 - clamp(ft / top) * (gy2 - gy1)]
        g.xy(self.graph, pts)
        g.cfg(self.graph, fill=col)


class Toasts:
    LIFE = 4.2

    def __init__(self, app):
        self.app = app
        self.list = []

    def push(self, text, col, icon="★"):
        app, c, k = self.app, self.app.c, self.app.k
        w = app.f_body.measure(text) + 76 * k
        ts = dict(text=text, col=col, w=w, born=app.t, x=Spring(1, 210, 19), y=Spring(-1, 190, 21),
                  items=[c.create_polygon(rrect(0, 0, 1, 1, 1), smooth=True, fill="#05030a", outline=""),
                         c.create_polygon(rrect(0, 0, 1, 1, 1), smooth=True, fill=PANEL_HI, outline=col),
                         c.create_oval(0, 0, 0, 0, fill=col, outline=""),
                         c.create_text(0, 0, text=icon, font=app.f_body, fill=BG),
                         c.create_text(0, 0, text=text, font=app.f_body, fill=FG, anchor="w"),
                         c.create_line(0, 0, 0, 0, fill=col, width=2 * k, capstyle="round")])
        ts["x"].to(0)
        self.list.append(ts)
        if len([s for s in self.list if s["x"].target == 0]) > 4:
            next(s for s in self.list if s["x"].target == 0)["x"].to(1.15)

    def update(self, dt, t):
        app, g, k = self.app, self.app.g, self.app.k
        th, gap = 48 * k, 10 * k
        slot = 0
        for ts in reversed(self.list):
            age = t - ts["born"]
            if age > self.LIFE and ts["x"].target == 0:
                ts["x"].to(1.15)
            ts["y"].to(slot)
            if ts["x"].target == 0:
                slot += 1
            xs, ys = ts["x"].step(dt), ts["y"].step(dt)
            w = ts["w"]
            x1 = app.W - 26 * k - w + xs * (w + 40 * k)
            y2 = app.H - 26 * k - ys * (th + gap)
            y1 = y2 - th
            sh, body, dot, icon, text, bar = ts["items"]
            g.xy(sh, rrect(x1 + 3 * k, y1 + 6 * k, x1 + w + 3 * k, y2 + 6 * k, 14 * k))
            g.xy(body, rrect(x1, y1, x1 + w, y2, 14 * k))
            cx, cy = x1 + 26 * k, (y1 + y2) / 2
            pulse = 1 + 0.12 * math.sin(age * 9) * max(0, 1 - age)
            r = 13 * k * pulse
            g.xy(dot, (cx - r, cy - r, cx + r, cy + r))
            g.xy(icon, (cx, cy))
            g.xy(text, (x1 + 50 * k, cy))
            left = clamp(1 - age / self.LIFE)
            g.xy(bar, (x1 + 16 * k, y2 - 4 * k, x1 + 16 * k + (w - 32 * k) * left, y2 - 4 * k))
            app.hit(x1, y1, x1 + w, y2, ("toast", id(ts)), click=lambda ts=ts: ts["x"].to(1.15))
            if app.hover == ("toast", id(ts)):
                ts["born"] = min(ts["born"] + dt, t)  # beim Drüberfahren bleibt der Toast stehen
        for ts in [s for s in self.list if s["x"].target > 1 and s["x"].v > 1.05]:
            for it in ts["items"]:
                g.delete(it)
            self.list.remove(ts)


class Bursts:
    def __init__(self, app):
        self.app = app
        self.parts, self.rings = [], []

    def burst(self, x, y, cols, n=46):
        c, k = self.app.c, self.app.k
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(150, 620) * k
            self.parts.append(dict(x=x, y=y, vx=math.cos(a) * s, vy=math.sin(a) * s - 180 * k, age=0.0,
                                   life=random.uniform(0.6, 1.3), r=random.uniform(2, 4.5) * k,
                                   col=random.choice(cols), item=c.create_oval(0, 0, 0, 0, fill=BG, outline="")))
        for i in range(2):
            self.rings.append(dict(x=x, y=y, age=-i * 0.12, col=cols[0],
                                   item=c.create_oval(0, 0, 0, 0, outline=BG, width=3 * k)))

    def update(self, dt, t):
        g, k = self.app.g, self.app.k
        drag = math.exp(-2.2 * dt)
        for p in list(self.parts):
            p["age"] += dt
            if p["age"] >= p["life"]:
                g.delete(p["item"])
                self.parts.remove(p)
                continue
            p["vy"] += 900 * k * dt
            p["vx"] *= drag
            p["vy"] *= drag
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            f = p["age"] / p["life"]
            r = p["r"] * (1 - f * 0.7)
            g.xy(p["item"], (p["x"] - r, p["y"] - r, p["x"] + r, p["y"] + r))
            g.cfg(p["item"], fill=mix(WHITE, p["col"], f * 3) if f < 0.33 else mix(p["col"], BG, (f - 0.33) * 1.5))
        for ring in list(self.rings):
            ring["age"] += dt
            f = ring["age"] / 0.7
            if f >= 1:
                g.delete(ring["item"])
                self.rings.remove(ring)
                continue
            r = 20 * k + 160 * k * ease_out(max(0, f))
            g.xy(ring["item"], (ring["x"] - r, ring["y"] - r, ring["x"] + r, ring["y"] + r))
            g.cfg(ring["item"], outline=mix(ring["col"], BG, max(0, f)) if f > 0 else BG)


class Button:
    """Kleiner animierter Knopf (Hover-Glühen, Drück-Feder)."""

    def __init__(self, page, text, key, command, col=ACCENT):
        self.page, self.key, self.command, self.col = page, key, command, col
        app = page.app
        self.font = app.f_btn_s
        self.w = self.font.measure(text) + 44 * app.k
        self.h = 38 * app.k
        self.hov, self.prs = Spring(0, 300, 24), Spring(0, 500, 26)
        self.glow = page.mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=BG, outline="")
        self.body = page.mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=col, outline="")
        self.text = page.mk("text", 0, 0, text=text, font=self.font, fill=WHITE)

    def update(self, dt, t, cx, cy, base=PANEL):
        app, g, k = self.page.app, self.page.app.g, self.page.app.k
        hv = self.hov.to(1 if app.hover == self.key else 0).step(dt)
        pr = self.prs.to(1 if app.pressed == self.key and app.hover == self.key else 0).step(dt)
        s = 1 + 0.05 * hv - 0.07 * pr
        w, h = self.w * s, self.h * s
        x1, y1, x2, y2 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
        gl = 6 * k * hv
        g.xy(self.glow, rrect(x1 - gl, y1 - gl, x2 + gl, y2 + gl, h / 2 + gl))
        g.cfg(self.glow, fill=mix(base, self.col, 0.35 * hv))
        g.xy(self.body, rrect(x1, y1, x2, y2, h / 2))
        g.cfg(self.body, fill=mix(self.col, WHITE, 0.15 * hv))
        g.xy(self.text, (cx, cy))
        app.hit(x1, y1, x2, y2, self.key, click=self.command)


# ---------------------------------------------------------------- pages

class Page:
    def __init__(self, app, index):
        self.app, self.index = app, index
        self.tag = f"page{index}"
        self.shown = None

    def mk(self, kind, *args, **kw):
        kw["tags"] = (self.tag,)
        kw["state"] = "normal" if self.shown else "hidden"
        return getattr(self.app.c, "create_" + kind)(*args, **kw)

    def set_shown(self, on):
        if on == self.shown:
            return
        self.shown = on
        self.app.c.itemconfigure(self.tag, state="normal" if on else "hidden")
        self.app.g.forget_state(self.app.c.find_withtag(self.tag))
        if on:
            self.enter()

    def enter(self):
        pass

    def sim(self, dt, t):
        pass

    def draw(self, dt, t, x1, y1, x2, y2):
        pass


class Card:
    def __init__(self, page, gi):
        self.page, self.gi, self.key = page, gi, ("card", gi)
        game = GAMES[gi]
        col = game["col"]
        mk = page.mk
        self.hov = Spring(0, 260, 20)
        self.sel = Spring(0, 200, 20)
        self.prog = Spring(0, 70, 15)
        self.flash = Spring(0, 60, 14)
        self.enter = Spring(0, 130, 15)
        self.spin_speed = Spring(0.9, 40, 12)
        self.spin = gi * 1.3
        self.glow = [mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill="", outline="") for _ in range(4)]
        self.shadow = mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill="#06030b", outline="")
        self.body = mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=PANEL, outline=BORDER)
        self.halo = [mk("oval", 0, 0, 0, 0, fill=PANEL, outline="") for _ in range(5)]
        self.icon = mk("polygon", 0, 0, 0, 0, 0, 0, fill=col, outline="")
        self.icon2 = mk("polygon", 0, 0, 0, 0, 0, 0, fill=col, outline="")
        self.orbit = [mk("oval", 0, 0, 0, 0, fill=col, outline="") for _ in range(4)]
        self.title = mk("text", 0, 0, text=game["name"], font=page.app.f_h, fill=FG, anchor="n")
        self.subt = mk("text", 0, 0, text=game["sub"], font=page.app.f_small, fill=MUTED, anchor="n")
        self.label = mk("text", 0, 0, text="", font=page.app.f_small, fill=MUTED, anchor="sw")
        self.pct = mk("text", 0, 0, text="", font=page.app.f_small_b, fill=col, anchor="se")
        self.track = mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=BG, outline="")
        self.bar = mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=col, outline="")
        self.bar_hl = mk("oval", 0, 0, 0, 0, fill=WHITE, outline="")

    def shape(self, cx, cy, R, ang, inner):
        """Stern (SM64) oder Edelstein (OoT), gedreht um die senkrechte Achse (Breite * cos)."""
        sx = math.cos(ang)
        sx = math.copysign(max(abs(sx), 0.08), sx)
        pts = []
        if self.gi == 0:
            for i in range(10):
                a = -math.pi / 2 + i * math.pi / 5
                r = R * (1 if i % 2 == 0 else 0.46) * inner
                pts += [cx + math.cos(a) * r * sx, cy + math.sin(a) * r]
        else:
            for i in range(6):
                a = -math.pi / 2 + i * math.pi / 3
                r = R * inner
                pts += [cx + math.cos(a) * r * 0.78 * sx, cy + math.sin(a) * r * 1.1]
        return pts, sx

    def update(self, dt, t, x1, y1, x2, y2, selected):
        app, g, k = self.page.app, self.page.app.g, self.page.app.k
        game = GAMES[self.gi]
        col = game["col"]
        h = self.hov.to(1 if app.hover == self.key else 0).step(dt)
        s = self.sel.to(1 if selected else 0).step(dt)
        fl = self.flash.step(dt)
        ey = self.enter.step(dt)
        prog = self.prog.to(game["done"] / game["total"]).step(dt)
        lift, grow = h * 9 * k, h * 4 * k
        X1, Y1, X2, Y2 = x1 - grow, y1 - grow - lift + ey, x2 + grow, y2 + grow - lift + ey
        r = 20 * k
        pulse = 0.5 + 0.5 * math.sin(t * 3)
        for i, item in enumerate(self.glow):  # weicher Schein, äußerste Schicht zuerst
            d = (4 - i) * (4 + 1.5 * pulse) * k * s
            g.xy(item, rrect(X1 - d, Y1 - d, X2 + d, Y2 + d, r + d))
            g.cfg(item, fill=mix(BG, mix(ACCENT, col, 0.25), s * (0.12 + i * 0.12)) if s > 0.02 else "")
        g.xy(self.shadow, rrect(X1 + 5 * k, Y1 + 8 * k + lift, X2 + 5 * k, Y2 + 8 * k + lift * 1.4, r))
        fill = mix(mix(PANEL, PANEL_HI, h * 0.8), col, fl * 0.18)
        g.xy(self.body, rrect(X1, Y1, X2, Y2, r))
        g.cfg(self.body, fill=fill, outline=mix(mix(BORDER, col, h * 0.6), ACCENT_HI, s))
        cw, ch = X2 - X1, Y2 - Y1
        cx, cy = (X1 + X2) / 2, Y1 + ch * 0.33
        R = min(cw, ch) * 0.15 * (1 + 0.08 * h + 0.15 * fl)
        for i, item in enumerate(self.halo):
            rr = R * (2.3 - i * 0.32) * (1 + 0.05 * math.sin(t * 2.4 + i))
            g.xy(item, (cx - rr, cy - rr, cx + rr, cy + rr))
            g.cfg(item, fill=mix(fill, col, 0.05 + i * 0.045 + h * 0.05 + fl * 0.1))
        self.spin_speed.to(0.9 + h * 5).step(dt)
        self.spin += self.spin_speed.v * dt
        bob = math.sin(t * 2) * 3 * k
        pts, sx = self.shape(cx, cy + bob, R, self.spin, 1.0)
        g.xy(self.icon, pts)
        light = 0.5 + 0.5 * sx
        g.cfg(self.icon, fill=mix(mix(col, "#000000", 0.35), col, light))
        pts = self.shape(cx, cy + bob, R, self.spin, 0.5)[0]
        g.xy(self.icon2, pts)
        g.cfg(self.icon2, fill=mix(col, WHITE, 0.25 + 0.35 * light))
        for j, item in enumerate(self.orbit):
            a = t * (1.6 + h * 2) + self.gi * 2 - j * 0.2
            ox, oy = math.cos(a) * R * 1.9, math.sin(a) * R * 0.5
            rr = (3.2 - j * 0.6) * k
            g.xy(item, (cx + ox - rr, cy + bob + oy - rr, cx + ox + rr, cy + bob + oy + rr))
            g.cfg(item, fill=mix(fill, mix(col, WHITE, 0.4), 1 - j * 0.22))
        g.xy(self.title, (cx, Y1 + ch * 0.6))
        g.xy(self.subt, (cx, Y1 + ch * 0.6 + 28 * k))
        tx1, tx2, ty = X1 + 22 * k, X2 - 22 * k, Y2 - 24 * k
        g.xy(self.label, (tx1, ty - 8 * k))
        g.cfg(self.label, text=f"{round(prog * game['total'])} / {game['total']} Checks")
        g.xy(self.pct, (tx2, ty - 8 * k))
        g.cfg(self.pct, text=f"{prog * 100:.0f} %")
        g.xy(self.track, rrect(tx1, ty, tx2, ty + 8 * k, 4 * k))
        g.cfg(self.track, fill=mix(fill, "#000000", 0.35))
        bx = tx1 + max(8 * k, (tx2 - tx1) * prog)
        g.xy(self.bar, rrect(tx1, ty, bx, ty + 8 * k, 4 * k))
        g.cfg(self.bar, fill=mix(col, WHITE, fl * 0.5))
        sh = (t * 0.45 + self.gi * 0.5) % 1.0  # Lichtpunkt läuft über den Balken
        hx = tx1 + (bx - tx1) * sh
        g.xy(self.bar_hl, (hx - 5 * k, ty + 2 * k, hx + 5 * k, ty + 6 * k))
        g.cfg(self.bar_hl, fill=mix(col, WHITE, 0.7 * math.sin(sh * math.pi)))
        app.hit(X1, Y1, X2, Y2, self.key, click=lambda: self.page.select(self.gi))


class PlayButton:
    def __init__(self, page):
        self.page = page
        mk, k = page.mk, page.app.k
        self.hov, self.prs = Spring(0, 260, 20), Spring(0, 500, 24)
        self.enter = Spring(0, 120, 13)
        self.center = (0.0, 0.0)
        self.rings = [mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill="", outline=BG, width=2 * k)
                      for _ in range(3)]
        self.glow = mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=BG, outline="")
        self.body = mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=ACCENT, outline="")
        self.hl = mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=ACCENT_HI, outline="")
        self.shine = mk("polygon", 0, 0, 0, 0, 0, 0, fill=WHITE, outline="")
        self.text = mk("text", 0, 0, text="", font=page.app.f_btn, fill=WHITE)
        self.dot_halo = mk("oval", 0, 0, 0, 0, fill="", outline=BG, width=1.5 * k)
        self.dot = mk("oval", 0, 0, 0, 0, fill=MUTED, outline="")
        self.status = mk("text", 0, 0, text="", font=page.app.f_small, fill=MUTED, anchor="w")

    def update(self, dt, t, cx, cy, w, h):
        app, g, k = self.page.app, self.page.app.g, self.page.app.k
        hv = self.hov.to(1 if app.hover == "play" else 0).step(dt)
        pr = self.prs.to(1 if app.pressed == "play" and app.hover == "play" else 0).step(dt)
        rn = app.run.v
        cy += self.enter.step(dt)
        self.center = (cx, cy)
        s = 1 + 0.045 * hv - 0.06 * pr
        bw, bh = w * s, h * s
        x1, y1, x2, y2 = cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2
        r = bh / 2
        base = mix(mix(ACCENT, "#9d74ff", hv), RUN, rn)
        for i, item in enumerate(self.rings):
            ph = (t * (0.45 + 0.35 * rn) + i / 3) % 1.0
            d = ease_out(ph) * (26 + 14 * hv) * k
            g.xy(item, rrect(x1 - d, y1 - d, x2 + d, y2 + d, r + d))
            g.cfg(item, outline=mix(base, BG, 0.25 + 0.75 * ph))
        gp = 0.5 + 0.5 * math.sin(t * 2.2)
        gl = (7 + 4 * gp + 6 * hv) * k
        g.xy(self.glow, rrect(x1 - gl, y1 - gl, x2 + gl, y2 + gl, r + gl))
        g.cfg(self.glow, fill=mix(BG, base, 0.28 + 0.12 * gp + 0.12 * hv))
        g.xy(self.body, rrect(x1, y1, x2, y2, r))
        g.cfg(self.body, fill=base)
        g.xy(self.hl, rrect(x1 + 5 * k, y1 + 4 * k, x2 - 5 * k, cy - 1 * k, r * 0.6))
        g.cfg(self.hl, fill=mix(base, WHITE, 0.13 + 0.05 * hv))
        p = (t % 3.4) / 1.1
        if p < 1:
            sx = x1 - 50 * k + (bw + 100 * k) * ease_out(p)
            lo, hi = x1 + r * 0.7, x2 - r * 0.7
            sw, sl = 26 * k, 22 * k
            pts = [clamp(sx, lo, hi), y1, clamp(sx + sw, lo, hi), y1,
                   clamp(sx + sw - sl, lo, hi), y2, clamp(sx - sl, lo, hi), y2]
            g.xy(self.shine, pts)
            g.cfg(self.shine, fill=mix(base, WHITE, 0.28 * math.sin(p * math.pi)), state="normal")
        else:
            g.cfg(self.shine, state="hidden")
        g.cfg(self.text, text="■   STOPPEN" if app.running else "▶   SPIELEN")
        g.xy(self.text, (cx, cy))
        app.hit(x1, y1, x2, y2, "play", click=app.toggle_run)
        # Statuszeile mit pulsierendem Punkt
        status = (f"Server läuft · {len(PLAYERS)} Spieler verbunden · Port 38281" if app.running
                  else "Bereit · Port 38281 frei · 2 Spiele installiert")
        tw = app.f_small.measure(status)
        sx, sy = cx - tw / 2 + 8 * k, y2 + 32 * k
        dr = 4 * k
        g.xy(self.dot, (sx - 16 * k - dr, sy - dr, sx - 16 * k + dr, sy + dr))
        g.cfg(self.dot, fill=mix(MUTED, GREEN, rn))
        ph = (t * 0.9) % 1.0
        hr = dr + ph * 10 * k * rn
        g.xy(self.dot_halo, (sx - 16 * k - hr, sy - hr, sx - 16 * k + hr, sy + hr))
        g.cfg(self.dot_halo, outline=mix(GREEN, BG, 0.3 + 0.7 * ph) if rn > 0.05 else "")
        g.xy(self.status, (sx, sy))
        g.cfg(self.status, text=status, fill=mix(MUTED, FG, rn * 0.7))


class PlayerRow:
    def __init__(self, page, pi):
        self.page, self.pi, self.key = page, pi, ("player", pi)
        p = PLAYERS[pi]
        mk = page.mk
        self.col = hsv(p["hue"], 0.5, 1.0)
        self.hov, self.prog, self.flash = Spring(0, 260, 24), Spring(0, 60, 14), Spring(0, 50, 12)
        self.enter = Spring(0, 140, 16)
        self.bg = mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=PANEL, outline="")
        self.av_ring = mk("oval", 0, 0, 0, 0, fill="", outline=self.col, width=2 * page.app.k)
        self.av = mk("oval", 0, 0, 0, 0, fill=mix(PANEL, self.col, 0.35), outline="")
        self.av_t = mk("text", 0, 0, text=p["name"][0], font=page.app.f_h, fill=WHITE)
        self.name = mk("text", 0, 0, text=p["name"], font=page.app.f_body_b, fill=FG, anchor="w")
        self.game = mk("text", 0, 0, text=GAMES[p["game"]]["name"], font=page.app.f_small, fill=MUTED, anchor="w")
        self.pct = mk("text", 0, 0, text="", font=page.app.f_small_b, fill=self.col, anchor="e")
        self.track = mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=BG, outline="")
        self.bar = mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=self.col, outline="")

    def update(self, dt, t, x1, y1, x2, y2):
        app, g, k = self.page.app, self.page.app.g, self.page.app.k
        p = PLAYERS[self.pi]
        hv = self.hov.to(1 if app.hover == self.key else 0).step(dt)
        fl = self.flash.step(dt)
        e = self.enter.step(dt)
        prog = self.prog.to(p["prog"]).step(dt)
        x1 += e
        x2 += e
        vis = clamp(1 - e / (60 * k))
        base = mix(PANEL, PANEL_HI, hv * 0.9 + fl * 0.4)
        g.xy(self.bg, rrect(x1, y1, x2, y2, 14 * k))
        g.cfg(self.bg, fill=mix(PANEL, mix(base, self.col, fl * 0.15), vis))
        cy = (y1 + y2) / 2
        ax = x1 + 30 * k
        ar = 17 * k * (1 + 0.08 * hv)
        g.xy(self.av, (ax - ar, cy - ar, ax + ar, cy + ar))
        g.cfg(self.av, fill=mix(PANEL, self.col, 0.35 * vis))
        rr = ar + (3 + 2 * math.sin(t * 3 + self.pi)) * k * (0.4 + hv + (1 if app.running else 0) * 0.4)
        g.xy(self.av_ring, (ax - rr, cy - rr, ax + rr, cy + rr))
        g.cfg(self.av_ring, outline=mix(PANEL, self.col, (0.3 + 0.5 * hv + 0.3 * fl) * vis))
        g.xy(self.av_t, (ax, cy))
        g.cfg(self.av_t, fill=mix(PANEL, WHITE, vis))
        g.xy(self.name, (x1 + 60 * k, cy - 10 * k))
        g.cfg(self.name, fill=mix(PANEL, FG, vis))
        g.xy(self.game, (x1 + 60 * k, cy + 10 * k))
        g.cfg(self.game, fill=mix(PANEL, MUTED, vis))
        bx1, bx2 = x2 - 150 * k, x2 - 16 * k
        g.xy(self.pct, (bx2, cy - 9 * k))
        g.cfg(self.pct, text=f"{prog * 100:.1f} %", fill=mix(PANEL, mix(self.col, WHITE, fl), vis))
        g.xy(self.track, rrect(bx1, cy + 4 * k, bx2, cy + 10 * k, 3 * k))
        g.cfg(self.track, fill=mix(PANEL, "#000000", 0.4 * vis))
        g.xy(self.bar, rrect(bx1, cy + 4 * k, bx1 + max(6 * k, (bx2 - bx1) * prog), cy + 10 * k, 3 * k))
        g.cfg(self.bar, fill=mix(PANEL, mix(self.col, WHITE, fl * 0.6), vis))
        app.hit(x1, y1, x2, y2, self.key)


class PlayPage(Page):
    def __init__(self, app):
        super().__init__(app, 0)
        k = app.k
        self.selected = 0
        self.cards = [Card(self, 0), Card(self, 1)]
        self.button = PlayButton(self)
        self.panel = self.mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=PANEL, outline=BORDER)
        self.p_title = self.mk("text", 0, 0, text="Mitspieler", font=app.f_h, fill=FG, anchor="w")
        self.p_pill = self.mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=BG, outline="")
        self.p_count = self.mk("text", 0, 0, text="", font=app.f_tiny_b, fill=GREEN)
        self.rows = [PlayerRow(self, i) for i in range(len(PLAYERS))]
        self.ring_track = self.mk("oval", 0, 0, 0, 0, outline=BG, width=10 * k)
        self.ring = self.mk("arc", 0, 0, 0, 0, style="arc", start=90, extent=0, outline=ACCENT_HI, width=10 * k)
        self.ring_spark = self.mk("arc", 0, 0, 0, 0, style="arc", start=90, extent=10, outline=WHITE, width=10 * k)
        self.ring_pct = self.mk("text", 0, 0, text="", font=app.f_big, fill=FG)
        self.ring_lbl = self.mk("text", 0, 0, text="Multiworld gesamt", font=app.f_small, fill=MUTED)
        self.total = Spring(0, 50, 13)
        self.panel_enter = Spring(0, 120, 15)

    def select(self, gi):
        self.selected = gi
        self.cards[gi].flash.snap(1)
        self.cards[gi].flash.to(0)

    def enter(self):
        k = self.app.k
        for i, c in enumerate(self.cards):
            c.enter.snap(70 * k + i * 30 * k)
            c.enter.to(0)
        self.button.enter.snap(60 * k)
        self.button.enter.to(0)
        self.panel_enter.snap(80 * k)
        self.panel_enter.to(0)
        for i, row in enumerate(self.rows):
            row.enter.snap(120 * k + i * 45 * k)
            row.enter.to(0)

    def draw(self, dt, t, x1, y1, x2, y2):
        app, g, k = self.app, self.app.g, self.app.k
        gap = 22 * k
        cw = x2 - x1
        left_w = (cw - gap) * 0.62
        lx2 = x1 + left_w
        card_w = (left_w - gap) / 2
        card_h = min(330 * k, (y2 - y1) * 0.64)
        for i, card in enumerate(self.cards):
            cx1 = x1 + i * (card_w + gap)
            card.update(dt, t, cx1, y1, cx1 + card_w, y1 + card_h, self.selected == i)
        by = y1 + card_h + (y2 - y1 - card_h) * 0.42
        self.button.update(dt, t, (x1 + lx2) / 2, by, min(320 * k, left_w * 0.7), 66 * k)
        # Mitspieler-Panel
        px1, px2 = lx2 + gap, x2
        pe = self.panel_enter.step(dt)
        py1, py2 = y1 + pe, y2 + pe
        g.xy(self.panel, rrect(px1, py1, px2, py2, 20 * k))
        g.cfg(self.panel, outline=mix(BORDER, ACCENT, 0.3 + 0.3 * math.sin(t * 1.5)))
        g.xy(self.p_title, (px1 + 22 * k, py1 + 30 * k))
        online = f"● {len(PLAYERS)} ONLINE" if app.running else "○ OFFLINE"
        g.cfg(self.p_count, text=online, fill=mix(MUTED, GREEN, app.run.v))
        pw = app.f_tiny_b.measure(online) + 20 * k
        g.xy(self.p_pill, rrect(px2 - 20 * k - pw, py1 + 18 * k, px2 - 20 * k, py1 + 42 * k, 12 * k))
        g.cfg(self.p_pill, fill=mix(PANEL_HI, RUN, app.run.v * 0.35))
        g.xy(self.p_count, (px2 - 20 * k - pw / 2, py1 + 30 * k))
        ry = py1 + 58 * k
        rh = 58 * k
        for row in self.rows:
            row.update(dt, t, px1 + 12 * k, ry, px2 - 12 * k, ry + rh)
            ry += rh + 6 * k
        # Fortschrittsring
        total = sum(p["prog"] for p in PLAYERS) / len(PLAYERS)
        tv = self.total.to(total).step(dt)
        space = py2 - ry
        rad = min(space * 0.36, (px2 - px1) * 0.22)
        show = rad > 22 * k
        for it in (self.ring_track, self.ring, self.ring_spark, self.ring_pct, self.ring_lbl):
            g.cfg(it, state="normal" if show else "hidden")
        if show:
            rcx, rcy = (px1 + px2) / 2, ry + space * 0.46
            box = (rcx - rad, rcy - rad, rcx + rad, rcy + rad)
            for it in (self.ring_track, self.ring, self.ring_spark):
                g.xy(it, box)
            g.cfg(self.ring_track, outline=mix(PANEL, "#000000", 0.35))
            g.cfg(self.ring, extent=-359.9 * clamp(tv), outline=mix(ACCENT_HI, PINK, 0.5 + 0.5 * math.sin(t)))
            sp = (t * 0.6) % 1.0 * clamp(tv)
            g.cfg(self.ring_spark, start=90 - 360 * sp, extent=-12,
                  outline=mix(ACCENT_HI, WHITE, 0.6 * math.sin(math.pi * (t * 0.6 % 1.0))))
            g.xy(self.ring_pct, (rcx, rcy - 6 * k))
            g.cfg(self.ring_pct, text=f"{tv * 100:.0f}%")
            g.xy(self.ring_lbl, (rcx, rcy + rad + 20 * k))


class SetupPage(Page):
    def __init__(self, app):
        super().__init__(app, 1)
        k = app.k
        self.t0 = 0.0
        self.rows = []
        for i, (name, detail) in enumerate(STEPS):
            mk = self.mk
            self.rows.append(dict(
                hov=Spring(0, 260, 24), pop=Spring(0, 320, 12), enter=Spring(0, 140, 16), done_at=None,
                bg=mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=PANEL, outline=BORDER),
                track=mk("oval", 0, 0, 0, 0, outline=BG, width=3 * k),
                arc=mk("arc", 0, 0, 0, 0, style="arc", start=90, extent=0, outline=ACCENT_HI, width=3 * k),
                disc=mk("oval", 0, 0, 0, 0, fill=GREEN, outline=""),
                check=mk("line", 0, 0, 0, 0, fill=BG, width=3.2 * k, capstyle="round", joinstyle="round"),
                name=mk("text", 0, 0, text=name, font=app.f_body_b, fill=FG, anchor="w"),
                detail=mk("text", 0, 0, text=detail, font=app.f_small, fill=MUTED, anchor="w"),
                state=mk("text", 0, 0, text="", font=app.f_small_b, fill=MUTED, anchor="e")))
        self.head = self.mk("text", 0, 0, text="Einrichtung", font=app.f_h2, fill=FG, anchor="w")
        self.sub = self.mk("text", 0, 0, text="", font=app.f_small, fill=MUTED, anchor="w")
        self.track = self.mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=PANEL, outline="")
        self.bar = self.mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=ACCENT, outline="")
        self.prog = Spring(0, 90, 16)
        self.button = Button(self, "↻  Erneut prüfen", "recheck", self.enter)

    def enter(self):
        k = self.app.k
        self.t0 = self.app.t
        for i, row in enumerate(self.rows):
            row["start"] = 0.25 + i * 0.55
            row["dur"] = random.uniform(0.5, 1.0)
            row["done_at"] = None
            row["pop"].snap(0)
            row["enter"].snap(90 * k + i * 30 * k)
            row["enter"].to(0)

    def draw(self, dt, t, x1, y1, x2, y2):
        app, g, k = self.app, self.app.g, self.app.k
        w = min(760 * k, x2 - x1)
        cx = (x1 + x2) / 2
        lx1, lx2 = cx - w / 2, cx + w / 2
        el = t - self.t0
        done = 0
        for row in self.rows:
            if row["done_at"] is None and el > row["start"] + row["dur"]:
                row["done_at"] = t
                row["pop"].to(1)
            done += row["done_at"] is not None
        g.xy(self.head, (lx1, y1 + 14 * k))
        g.xy(self.sub, (lx1, y1 + 42 * k))
        g.cfg(self.sub, text=f"{done} von {len(self.rows)} Komponenten bereit"
              + ("  ·  alles startklar ✓" if done == len(self.rows) else ""),
              fill=GREEN if done == len(self.rows) else MUTED)
        pv = self.prog.to(done / len(self.rows)).step(dt)
        g.xy(self.track, rrect(lx1, y1 + 62 * k, lx2, y1 + 68 * k, 3 * k))
        g.xy(self.bar, rrect(lx1, y1 + 62 * k, lx1 + max(6 * k, w * pv), y1 + 68 * k, 3 * k))
        g.cfg(self.bar, fill=mix(ACCENT, GREEN, pv ** 3))
        ry = y1 + 88 * k
        rh = min(64 * k, (y2 - ry - 70 * k) / len(self.rows) - 8 * k)
        for i, row in enumerate(self.rows):
            key = ("step", i)
            hv = row["hov"].to(1 if app.hover == key else 0).step(dt)
            e = row["enter"].step(dt)
            vis = clamp(1 - e / (90 * k))
            ra, rb = ry, ry + rh
            g.xy(row["bg"], rrect(lx1 + e, ra, lx2 + e, rb, 14 * k))
            g.cfg(row["bg"], fill=mix(BG, mix(PANEL, PANEL_HI, hv), vis), outline=mix(BG, BORDER, vis))
            ccx, ccy, cr = lx1 + e + 32 * k, (ra + rb) / 2, 13 * k
            box = (ccx - cr, ccy - cr, ccx + cr, ccy + cr)
            g.xy(row["track"], box)
            g.cfg(row["track"], outline=mix(BG, BORDER, vis))
            busy = el > row["start"] and row["done_at"] is None
            if row["done_at"] is None:
                if busy:
                    f = clamp((el - row["start"]) / row["dur"])
                    g.xy(row["arc"], box)
                    g.cfg(row["arc"], start=90 - t * 420, extent=-(40 + 280 * f), outline=ACCENT_HI, state="normal")
                    state, scol = "Prüfe …", ACCENT_HI
                else:
                    g.cfg(row["arc"], state="hidden")
                    state, scol = "Wartet", MUTED
                g.cfg(row["disc"], state="hidden")
                g.cfg(row["check"], state="hidden")
            else:
                g.cfg(row["arc"], state="hidden")
                pop = row["pop"].step(dt)
                rr = cr * max(0.0, pop)
                g.xy(row["disc"], (ccx - rr, ccy - rr, ccx + rr, ccy + rr))
                g.cfg(row["disc"], state="normal", fill=GREEN)
                # Häkchen wird gezeichnet statt eingeblendet
                a = (ccx - 6 * k, ccy + 0.5 * k)
                b = (ccx - 1.5 * k, ccy + 5 * k)
                c = (ccx + 6.5 * k, ccy - 5 * k)
                f = clamp((t - row["done_at"] - 0.08) / 0.22)
                if f <= 0:
                    g.cfg(row["check"], state="hidden")
                else:
                    if f < 0.4:
                        q = f / 0.4
                        pts = (a[0], a[1], a[0] + (b[0] - a[0]) * q, a[1] + (b[1] - a[1]) * q)
                    else:
                        q = (f - 0.4) / 0.6
                        pts = (a[0], a[1], b[0], b[1], b[0] + (c[0] - b[0]) * q, b[1] + (c[1] - b[1]) * q)
                    g.xy(row["check"], pts)
                    g.cfg(row["check"], state="normal")
                state, scol = "Fertig", GREEN
            g.xy(row["name"], (lx1 + e + 62 * k, ccy - 9 * k))
            g.cfg(row["name"], fill=mix(BG, FG, vis))
            g.xy(row["detail"], (lx1 + e + 62 * k, ccy + 11 * k))
            g.cfg(row["detail"], fill=mix(BG, MUTED, vis))
            g.xy(row["state"], (lx2 + e - 20 * k, ccy))
            g.cfg(row["state"], text=state, fill=mix(BG, scol, vis))
            app.hit(lx1, ra, lx2, rb, key)
            ry = rb + 8 * k
        self.button.update(dt, t, cx, min(y2 - 24 * k, ry + 36 * k))


class NetPage(Page):
    TRAIL = 16
    N = 90

    def __init__(self, app):
        super().__init__(app, 2)
        k = app.k
        mk = self.mk
        self.disc = mk("oval", 0, 0, 0, 0, fill="#0a1220", outline="")
        self.trail = [mk("arc", 0, 0, 0, 0, style="pieslice", start=0, extent=4, fill=BG, outline="")
                      for _ in range(self.TRAIL)]
        self.circles = [mk("oval", 0, 0, 0, 0, outline=BG, width=1) for _ in range(4)]
        self.cross = [mk("line", 0, 0, 0, 0, fill=BG) for _ in range(2)]
        self.sweep = mk("line", 0, 0, 0, 0, fill=CYAN, width=2 * k)
        self.blips = [dict(a=random.uniform(0, 360), d=random.uniform(0.2, 0.92), name=p["name"],
                           item=mk("oval", 0, 0, 0, 0, fill=BG, outline=""),
                           lbl=mk("text", 0, 0, text=p["name"], font=app.f_tiny, fill=BG, anchor="w"))
                      for p in PLAYERS]
        self.center = mk("oval", 0, 0, 0, 0, fill=CYAN, outline="")
        self.radar_lbl = mk("text", 0, 0, text="Lobby · 38281", font=app.f_small_b, fill=CYAN)
        self.status = []
        for title, val in (("Server", "online"), ("Lobby (HTTP)", "38281"), ("Port-Test", "offen")):
            self.status.append(dict(
                bg=mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=PANEL, outline=BORDER),
                dot=mk("oval", 0, 0, 0, 0, fill=GREEN, outline=""),
                t=mk("text", 0, 0, text=title, font=app.f_small, fill=MUTED, anchor="w"),
                v=mk("text", 0, 0, text=val, font=app.f_h, fill=FG, anchor="w")))
        self.g_bg = mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=PANEL, outline=BORDER)
        self.g_title = mk("text", 0, 0, text="Ping", font=app.f_small, fill=MUTED, anchor="w")
        self.g_val = mk("text", 0, 0, text="", font=app.f_h, fill=CYAN, anchor="e")
        self.g_area = mk("polygon", 0, 0, 0, 0, 0, 0, fill=mix(PANEL, CYAN, 0.12), outline="")
        self.g_line = mk("line", 0, 0, 0, 0, fill=CYAN, width=2 * k, smooth=True)
        self.g_dot = mk("oval", 0, 0, 0, 0, fill=WHITE, outline="")
        self.e_bg = mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill=PANEL, outline=BORDER)
        self.e_title = mk("text", 0, 0, text="Datenverkehr", font=app.f_small, fill=MUTED, anchor="w")
        self.bars = [dict(s=Spring(0.2, 220, 18), item=mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True,
                                                         fill=CYAN, outline="")) for _ in range(24)]
        self.samples = [19 + 5 * math.sin(i * 0.056) + random.gauss(0, 1.6) for i in range(-self.N, 0)]
        self.last_sample = 0.0
        self.last_eq = 0.0
        self.ping = Spring(20, 80, 16)

    def sim(self, dt, t):
        while t - self.last_sample > 0.08:
            self.last_sample += 0.08
            v = 19 + 5 * math.sin(self.last_sample * 0.7) + random.gauss(0, 1.6)
            if random.random() < 0.02:
                v += random.uniform(12, 30)
            self.samples.append(max(4.0, v))
            del self.samples[0]
        if t - self.last_eq > 0.11:
            self.last_eq = t
            act = 0.35 + 0.65 * self.app.run.v
            for i, b in enumerate(self.bars):
                b["s"].to(clamp(random.random() ** 1.6 * act + 0.06 * math.sin(t * 3 + i * 0.4) + 0.08))

    def draw(self, dt, t, x1, y1, x2, y2):
        app, g, k = self.app, self.app.g, self.app.k
        gap = 22 * k
        lw = min((x2 - x1) * 0.45, y2 - y1)
        R = lw / 2 - 10 * k
        cx, cy = x1 + lw / 2, (y1 + y2) / 2
        g.xy(self.disc, (cx - R, cy - R, cx + R, cy + R))
        ang = (t * 100) % 360
        for i, item in enumerate(self.trail):
            g.xy(item, (cx - R, cy - R, cx + R, cy + R))
            g.cfg(item, start=ang - (i + 1) * 4.2, extent=4.4, fill=mix("#0a1220", CYAN, 0.32 * (1 - i / self.TRAIL) ** 1.5))
        for i, item in enumerate(self.circles):
            r = R * (i + 1) / 4
            g.xy(item, (cx - r, cy - r, cx + r, cy + r))
            g.cfg(item, outline=mix("#0a1220", CYAN, 0.22 if i == 3 else 0.12))
        g.xy(self.cross[0], (cx - R, cy, cx + R, cy))
        g.xy(self.cross[1], (cx, cy - R, cx, cy + R))
        for item in self.cross:
            g.cfg(item, fill=mix("#0a1220", CYAN, 0.12))
        rad = math.radians(ang)
        g.xy(self.sweep, (cx, cy, cx + math.cos(rad) * R, cy - math.sin(rad) * R))
        for b in self.blips:
            behind = (ang - b["a"]) % 360
            br = clamp(1 - behind / 300) ** 1.4
            if behind > 340 and random.random() < 0.02:  # Spieler "bewegen" sich ab und zu
                b["d"] = clamp(b["d"] + random.uniform(-0.15, 0.15), 0.2, 0.92)
            a = math.radians(b["a"])
            bx, by = cx + math.cos(a) * R * b["d"], cy - math.sin(a) * R * b["d"]
            r = (3 + 4 * br) * k
            g.xy(b["item"], (bx - r, by - r, bx + r, by + r))
            g.cfg(b["item"], fill=mix("#0a1220", mix(GREEN, WHITE, br * 0.5), 0.25 + 0.75 * br))
            g.xy(b["lbl"], (bx + 10 * k, by))
            g.cfg(b["lbl"], fill=mix("#0a1220", GREEN, br))
        pr = (4 + 1.5 * math.sin(t * 4)) * k
        g.xy(self.center, (cx - pr, cy - pr, cx + pr, cy + pr))
        g.xy(self.radar_lbl, (cx, cy + R - 14 * k))
        # rechte Spalte
        rx1 = x1 + lw + gap
        sh = 64 * k
        sgap = 11 * k
        sw = (x2 - rx1 - 2 * sgap) / 3
        for i, s in enumerate(self.status):
            sx1 = rx1 + i * (sw + sgap)
            g.xy(s["bg"], rrect(sx1, y1, sx1 + sw, y1 + sh, 14 * k))
            ph = 0.5 + 0.5 * math.sin(t * 3 + i)
            dr = (4 + ph) * k
            g.xy(s["dot"], (sx1 + 18 * k - dr, y1 + 22 * k - dr, sx1 + 18 * k + dr, y1 + 22 * k + dr))
            g.cfg(s["dot"], fill=mix(RUN, GREEN, ph))
            g.xy(s["t"], (sx1 + 30 * k, y1 + 22 * k))
            g.xy(s["v"], (sx1 + 16 * k, y1 + 45 * k))
        gy1 = y1 + sh + gap
        gy2 = gy1 + (y2 - gy1 - gap) * 0.55
        g.xy(self.g_bg, rrect(rx1, gy1, x2, gy2, 16 * k))
        g.xy(self.g_title, (rx1 + 18 * k, gy1 + 20 * k))
        cur = self.ping.to(self.samples[-1]).step(dt)
        g.xy(self.g_val, (x2 - 18 * k, gy1 + 22 * k))
        g.cfg(self.g_val, text=f"{cur:.0f} ms", fill=GOLD if cur > 35 else CYAN)
        ax1, ax2, ay1, ay2 = rx1 + 16 * k, x2 - 16 * k, gy1 + 44 * k, gy2 - 14 * k
        step = (ax2 - ax1) / (self.N - 2)
        frac = (t - self.last_sample) / 0.08
        lo, hi = 0.0, max(60.0, max(self.samples) * 1.1)
        pts = []
        for i, v in enumerate(self.samples):
            x = max(ax1, ax1 + (i - frac) * step)
            pts += [x, ay2 - (v - lo) / (hi - lo) * (ay2 - ay1)]
        g.xy(self.g_line, pts)
        g.xy(self.g_area, pts + [pts[-2], ay2, ax1, ay2])
        lx, ly = pts[-2], pts[-1]
        dr = 4 * k
        g.xy(self.g_dot, (lx - dr, ly - dr, lx + dr, ly + dr))
        ey1, ey2 = gy2 + gap, y2
        g.xy(self.e_bg, rrect(rx1, ey1, x2, ey2, 16 * k))
        g.xy(self.e_title, (rx1 + 18 * k, ey1 + 20 * k))
        bx1, bx2, by1, by2 = rx1 + 18 * k, x2 - 18 * k, ey1 + 40 * k, ey2 - 14 * k
        n = len(self.bars)
        bw = (bx2 - bx1) / n
        for i, b in enumerate(self.bars):
            v = clamp(b["s"].step(dt), 0.03, 1.0)
            bx = bx1 + i * bw
            top = by2 - (by2 - by1) * v
            g.xy(b["item"], rrect(bx + 2 * k, top, bx + bw - 2 * k, by2, 3 * k))
            g.cfg(b["item"], fill=mix(mix(PANEL, CYAN, 0.35), mix(CYAN, ACCENT_HI, i / n), v))


class LogPage(Page):
    COLORS = {"Server": ACCENT_HI, "Fund": GREEN, "Hinweis": GOLD, "Chat": CYAN, "Info": MUTED}

    def __init__(self, app):
        super().__init__(app, 3)
        self.panel = self.mk("polygon", rrect(0, 0, 1, 1, 1), smooth=True, fill="#0a0613", outline=BORDER)
        self.head = self.mk("text", 0, 0, text="Live-Log", font=app.f_h2, fill=FG, anchor="w")
        self.caret = self.mk("rectangle", 0, 0, 0, 0, fill=ACCENT_HI, outline="")
        self.lines = []
        self.scroll = Spring(0, 160, 22)
        self.next_at = 0.5

    def add(self, kind, text):
        self.lines.append(dict(time=time.strftime("%H:%M:%S"), kind=kind, text=text, born=self.app.t, items=None))
        self.scroll.snap(self.scroll.v + 1)
        self.scroll.to(0)
        while len(self.lines) > 60:
            old = self.lines.pop(0)
            for it in old["items"] or ():
                self.app.g.delete(it)

    def sim(self, dt, t):
        if t > self.next_at:
            self.next_at = t + random.uniform(0.7, 1.8)
            p = random.choice(PLAYERS)
            kind, text = random.choice([
                ("Info", f"{p['name']} hat sich mit der Lobby synchronisiert"),
                ("Chat", f"{p['name']}: hat jemand schon den Wassertempel?"),
                ("Hinweis", f"{p['name']}s {random.choice(ITEMS[p['game']])} liegt in der Welt von "
                            f"{random.choice(PLAYERS)['name']}"),
                ("Server", f"Speichere Multiworld … ok ({random.randint(40, 90)} ms)"),
            ])
            self.add(kind, text)

    def draw(self, dt, t, x1, y1, x2, y2):
        app, g, k = self.app, self.app.g, self.app.k
        g.xy(self.panel, rrect(x1, y1, x2, y2, 18 * k))
        g.xy(self.head, (x1 + 22 * k, y1 + 28 * k))
        sc = self.scroll.step(dt)
        lh = 24 * k
        top, bottom = y1 + 58 * k, y2 - 30 * k
        n = len(self.lines)
        caret_set = False
        for i, line in enumerate(self.lines):
            y = bottom - (n - 1 - i) * lh + sc * lh
            if y < top - lh:
                if line["items"]:
                    for it in line["items"]:
                        g.delete(it)
                    line["items"] = None
                continue
            if line["items"] is None:
                line["items"] = (self.mk("text", 0, 0, text=line["time"], font=app.f_mono, fill=BG, anchor="w"),
                                 self.mk("text", 0, 0, text=f"[{line['kind']}]", font=app.f_mono, fill=BG, anchor="w"),
                                 self.mk("text", 0, 0, text="", font=app.f_mono, fill=BG, anchor="w"))
            ti, ki, xi = line["items"]
            fade = clamp((y - top) / (lh * 2.5)) * clamp(1 - (y - bottom) / lh)
            col = self.COLORS[line["kind"]]
            age = t - line["born"]
            typed = line["text"][:int(age * 110)]
            g.xy(ti, (x1 + 22 * k, y))
            g.cfg(ti, fill=mix("#0a0613", BORDER, fade * 1.6))
            g.xy(ki, (x1 + 100 * k, y))
            g.cfg(ki, fill=mix("#0a0613", col, fade))
            g.xy(xi, (x1 + 190 * k, y))
            g.cfg(xi, text=typed, fill=mix("#0a0613", mix(WHITE, FG, clamp(age * 2)), fade))
            if i == n - 1:
                cx = x1 + 190 * k + app.f_mono.measure(typed) + 3 * k
                on = (t * 2.2) % 1 < 0.6
                g.xy(self.caret, (cx, y - 8 * k, cx + 8 * k, y + 8 * k))
                g.cfg(self.caret, state="normal" if on else "hidden")
                caret_set = True
        if not caret_set:
            g.cfg(self.caret, state="hidden")


# ---------------------------------------------------------------- app

class App:
    def __init__(self, fps):
        win_setup()
        self.root = root = tk.Tk()
        root.title("Archipelago Launcher · Vorschau")
        self.k = k = max(1.0, root.winfo_fpixels("1i") / 96.0)
        root.geometry(f"{int(1200 * k)}x{int(760 * k)}")
        root.minsize(int(980 * k), int(640 * k))
        root.configure(bg=BG)
        self.fps = fps
        self.quality = True
        sans = pick_font(root, ["Segoe UI", "Inter", "DejaVu Sans"])
        semi = pick_font(root, ["Segoe UI Semibold", "Segoe UI", "DejaVu Sans"])
        black = pick_font(root, ["Segoe UI Black", "Segoe UI", "DejaVu Sans"])
        mono = pick_font(root, ["Cascadia Mono", "Consolas", "DejaVu Sans Mono"])
        self.f_title = tkfont.Font(family=black, size=30, weight="bold")
        self.f_big = tkfont.Font(family=black, size=22, weight="bold")
        self.f_h2 = tkfont.Font(family=semi, size=17, weight="bold")
        self.f_h = tkfont.Font(family=semi, size=13, weight="bold")
        self.f_tab = tkfont.Font(family=semi, size=11, weight="bold")
        self.f_btn = tkfont.Font(family=black, size=15, weight="bold")
        self.f_btn_s = tkfont.Font(family=semi, size=10, weight="bold")
        self.f_body = tkfont.Font(family=sans, size=10)
        self.f_body_b = tkfont.Font(family=semi, size=11, weight="bold")
        self.f_small = tkfont.Font(family=sans, size=9)
        self.f_small_b = tkfont.Font(family=semi, size=9, weight="bold")
        self.f_tiny = tkfont.Font(family=sans, size=8)
        self.f_tiny_b = tkfont.Font(family=semi, size=8, weight="bold")
        self.f_mono = tkfont.Font(family=mono, size=10)

        self.c = tk.Canvas(root, bg=BG, highlightthickness=0, bd=0)
        self.c.pack(fill="both", expand=True)
        self.g = Gfx(self.c)
        self.W, self.H = int(1200 * k), int(760 * k)
        self.mx = self.my = -9999.0
        self.mouse_in = False
        self.hits, self.hover, self.hover_click, self.pressed, self.cursor = [], None, None, None, ""
        self.t = 0.0
        self.running = False
        self.run = Spring(0, 40, 11)
        self.next_event = 3.0

        self.aurora = Aurora(self)
        self.stars = Stars(self)
        self.pages = [PlayPage(self), SetupPage(self), NetPage(self), LogPage(self)]
        self.title = Title(self)
        self.tabs = Tabs(self)
        self.bursts = Bursts(self)
        self.toasts = Toasts(self)
        self.meter = FpsMeter(self)

        self.c.bind("<Configure>", self.on_resize)
        self.c.bind("<Motion>", self.on_motion)
        self.c.bind("<Leave>", lambda e: setattr(self, "mouse_in", False))
        self.c.bind("<ButtonPress-1>", self.on_press)
        self.c.bind("<ButtonRelease-1>", self.on_release)
        for i in range(4):
            root.bind(str(i + 1), lambda e, i=i: self.tabs.select(i))
        root.bind("<f>", lambda e: setattr(self.meter, "on", not self.meter.on))
        root.bind("<q>", lambda e: setattr(self, "quality", not self.quality))
        root.bind("<F11>", lambda e: root.attributes("-fullscreen", not root.attributes("-fullscreen")))
        root.bind("<Escape>", lambda e: root.attributes("-fullscreen", False))
        root.after(30, lambda: dark_titlebar(root))

        self.frame_dt = 1.0 / fps
        self.last = self.next_t = time.perf_counter()
        self.loop()

    # --- input
    def on_resize(self, e):
        self.W, self.H = e.width, e.height

    def on_motion(self, e):
        self.mx, self.my, self.mouse_in = e.x, e.y, True

    def on_press(self, e):
        self.on_motion(e)
        self.resolve_hover()
        self.pressed = self.hover

    def on_release(self, e):
        self.on_motion(e)
        self.resolve_hover()
        if self.pressed is not None and self.pressed == self.hover and self.hover_click:
            self.hover_click()
        self.pressed = None

    def hit(self, x1, y1, x2, y2, key, click=None):
        self.hits.append((x1, y1, x2, y2, key, click))

    def resolve_hover(self):
        key = click = None
        if self.mouse_in:
            for x1, y1, x2, y2, hk, hc in reversed(self.hits):
                if x1 <= self.mx <= x2 and y1 <= self.my <= y2:
                    key, click = hk, hc
                    break
        self.hover, self.hover_click = key, click
        cursor = "hand2" if click else ""
        if cursor != self.cursor:
            self.cursor = cursor
            self.c.configure(cursor=cursor)

    # --- simulation
    def toggle_run(self):
        self.running = not self.running
        self.run.to(1 if self.running else 0)
        cx, cy = self.pages[0].button.center
        if self.running:
            self.bursts.burst(cx, cy, [RUN, GREEN, CYAN, WHITE, GOLD])
            self.toasts.push("Multiworld gestartet · Server läuft auf Port 38281", RUN, "▶")
            self.pages[3].add("Server", "Multiworld gestartet, Lobby auf 38281")
            self.next_event = self.t + 1.2
        else:
            self.bursts.burst(cx, cy, [ACCENT, ACCENT_HI, PINK], n=24)
            self.toasts.push("Server gestoppt · Spielstand gesichert", ACCENT, "■")
            self.pages[3].add("Server", "Server gestoppt, Spielstand gesichert")

    def random_event(self):
        pi = random.randrange(len(PLAYERS))
        p = PLAYERS[pi]
        item = random.choice(ITEMS[p["game"]])
        p["prog"] = min(1.0, p["prog"] + random.uniform(0.008, 0.03))
        game = GAMES[p["game"]]
        game["done"] = min(game["total"], game["done"] + random.randint(1, 3))
        page = self.pages[0]
        page.rows[pi].flash.snap(1)
        page.rows[pi].flash.to(0)
        page.cards[p["game"]].flash.snap(0.6)
        page.cards[p["game"]].flash.to(0)
        col = hsv(p["hue"], 0.5, 1.0)
        self.toasts.push(f"{p['name']} hat {item} gefunden", col, "★" if p["game"] == 0 else "◆")
        self.pages[3].add("Fund", f"{p['name']} hat {item} gefunden ({game['name']})")

    # --- frame loop
    def loop(self):
        now = time.perf_counter()
        dt = min(now - self.last, 0.05)
        self.last = now
        self.frame(dt)
        self.c.update_idletasks()  # jetzt zeichnen, damit die Zeitmessung echt ist
        self.next_t += self.frame_dt
        now = time.perf_counter()
        if self.next_t < now - self.frame_dt:
            self.next_t = now
        self.root.after(max(0, int((self.next_t - now) * 1000)), self.loop)

    def frame(self, dt):
        self.t += dt
        t = self.t
        self.hits = []
        self.run.step(dt)
        if self.running and t > self.next_event:
            self.next_event = t + random.uniform(2.2, 4.5)
            self.random_event()
        self.aurora.update(dt, t)
        self.stars.update(dt, t)
        k = self.k
        x1, y1, x2, y2 = 30 * k, 176 * k, self.W - 30 * k, self.H - 30 * k
        pos = self.tabs.page.v
        for page in self.pages:
            page.sim(dt, t)
            ox = (page.index - pos) * self.W
            visible = abs(ox) < self.W - 1
            page.set_shown(visible)
            if visible:
                page.draw(dt, t, x1 + ox, y1, x2 + ox, y2)
        self.title.update(dt, t)
        self.tabs.update(dt, t)
        self.bursts.update(dt, t)
        self.toasts.update(dt, t)
        self.meter.update(dt, t)
        self.resolve_hover()


def main():
    fps = monitor_hz()
    if "--fps" in sys.argv:
        fps = int(sys.argv[sys.argv.index("--fps") + 1])
    app = App(max(30, fps))
    app.root.mainloop()


if __name__ == "__main__":
    main()
