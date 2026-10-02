"""One-off effects: logo with light ring, scan line, boot console, item banners."""
import math
import random

from .. import anim
from . import look
from .items import Elem, mix


class Emblem(Elem):
    """Hexagon emblem left of the title. Builds by drawing its lines while a light ring rolls outwards."""

    def __init__(self, scene, r=20):
        super().__init__(scene, None)
        self.r = r
        self.hexa = self.c.create_polygon(0, 0, 0, 0, 0, 0, fill="#140c26", outline=look.GLOW, width=2,
                                          tags=(self.tag,))
        self.inner = self.c.create_polygon(0, 0, 0, 0, 0, 0, fill=look.ACCENT, outline="", tags=(self.tag,))
        self.core = self.c.create_oval(0, 0, 0, 0, fill="#ffffff", width=0, tags=(self.tag,))
        self.w = self.h = 2 * r
        scene.hooks.append(self._breathe)

    def _hex(self, r, rot=0.0):
        cx, cy = self.x, self.y
        return [v for i in range(6) for v in (cx + r * math.cos(rot + i * math.pi / 3),
                                              cy + r * math.sin(rot + i * math.pi / 3))]

    def draw(self):
        cx, cy, r = self.x, self.y, self.r
        self.c.coords(self.hexa, *self._hex(r, math.pi / 6))
        self.c.coords(self.inner, cx, cy - r * 0.55, cx + r * 0.42, cy, cx, cy + r * 0.55, cx - r * 0.42, cy)
        self.c.coords(self.core, cx - 3, cy - 3, cx + 3, cy + 3)

    def _breathe(self, now):
        if self.visible():
            a = 0.5 + 0.5 * math.sin(now * 1.7)
            self.c.itemconfigure(self.inner, fill=mix(look.ACCENT, look.PINK, a * 0.6))

    def build(self, tl, delay, quick=False):
        self.hide_for_build()
        c, cx, cy, r = self.c, self.x, self.y, self.r
        pts = list(zip(*[iter(self._hex(r, math.pi / 6))] * 2))
        st = {}

        def lines(p):
            if "l" not in st:
                st["l"] = c.create_line(0, 0, 0, 0, fill=look.GLOW, width=2, tags=(self.fx, "fx"))
            c.coords(st["l"], *look.path_part(pts, p))

        def ring(p):
            if "ring" not in st:
                st["ring"] = [c.create_oval(0, 0, 0, 0, outline="#ffffff", width=3, tags=(self.fx, "fx")),
                              c.create_oval(0, 0, 0, 0, outline=look.GLOW, width=1, tags=(self.fx, "fx"))]
            for i, item in enumerate(st["ring"]):
                q = max(0.0, p - i * 0.12)
                rr = r * 0.4 + 110 * anim.out_cubic(q)
                c.coords(item, cx - rr, cy - rr, cx + rr, cy + rr)
                c.itemconfigure(item, outline=mix("#ffffff" if i == 0 else look.GLOW, look.VOID, q),
                                width=max(1, round(3 * (1 - q))))

        def flash(p):
            if not self.built:
                self.reveal()
            c.itemconfigure(self.hexa, fill=mix("#ffffff", "#140c26", p))
        tl.add(delay, 360, lines, ease=anim.out_cubic)
        tl.add(delay + 300, 900, ring)
        tl.add(delay + 330, 420, flash, done=lambda: c.delete(self.fx))


class ScanLine:
    """Bright horizontal line that wipes down and reveals the backdrop (scene.wipe)."""

    def __init__(self, scene):
        self.sc = scene
        c = scene.c
        self.items = [c.create_rectangle(0, 0, 0, 0, fill=mix(look.GLOW, look.VOID, 0.75), width=0, tags=("fx",)),
                      c.create_rectangle(0, 0, 0, 0, fill=look.GLOW, width=0, tags=("fx",)),
                      c.create_line(0, 0, 0, 0, fill="#ffffff", width=1, tags=("fx",))]

    def run(self, tl, delay, ms):
        c, sc = self.sc.c, self.sc
        sc.wipe = 0.0

        def step(p):
            sc.wipe = p
            y = sc.h * p
            glow, band, line = self.items
            c.coords(glow, 0, y - 26, sc.w, y + 4)
            c.coords(band, 0, y - 3, sc.w, y + 1)
            c.coords(line, 0, y, sc.w, y)
            for item in self.items:
                c.tag_raise(item)

        def done():
            sc.wipe = 1.0
            for item in self.items:
                c.delete(item)
        tl.add(delay, ms, step, ease=anim.in_out_sine, done=done)


class BootConsole:
    """System start lines with real checks; they type themselves out in the lower left during the build-up."""

    def __init__(self, scene, x, y):
        self.sc, self.c = scene, scene.c
        self.x, self.y = x, y
        self.lines = []
        self.closed = False
        self.plate = self.c.create_rectangle(0, 0, 0, 0, fill="#0a0613", outline=look.WIRE, stipple="gray75",
                                             tags=("boot",))
        self.head = self.c.create_text(x + 12, 0, text="SYS://BOOT", font=look.F_MONO, fill=look.ACCENT_HI, anchor="w",
                                       tags=("boot",))
        self._layout()

    def _layout(self):
        n = len(self.lines)
        top = self.y - 30 - n * 17
        self.c.coords(self.plate, self.x, top, self.x + 440, self.y)
        self.c.coords(self.head, self.x + 12, top + 13)
        for i, (status, text) in enumerate(self.lines):
            yy = top + 32 + i * 17
            self.c.coords(status, self.x + 12, yy)
            self.c.coords(text, self.x + 74, yy)
        self.c.tag_raise("boot")

    def line(self, status, text, color=look.OK):
        """status like 'OK' / '--' / 'FAIL'."""
        if self.closed:
            return
        tag = f"[{status:^4}]"
        s = self.c.create_text(0, 0, text=tag, font=look.F_MONO, fill=color, anchor="w", tags=("boot",))
        t = self.c.create_text(0, 0, text="", font=look.F_MONO, fill=look.FG, anchor="w", tags=("boot",))
        self.lines.append((s, t))
        self._layout()
        anim.Tween(self.c, 260, lambda p: self.c.itemconfigure(t, text=look.scramble(text, p)),
                   done=lambda: self.c.itemconfigure(t, text=text))

    def close(self, delay=0):
        if self.closed:
            return
        self.closed = True

        def step(p):
            for s, t in self.lines:
                self.c.itemconfigure(t, text=look.scramble(self.c.itemcget(t, "text"), 1 - p, 1.0))
            self.c.itemconfigure(self.plate, outline=mix(look.WIRE, look.VOID, p))
            self.c.move("boot", -12 * p * p, 0)
        anim.Tween(self.c, 360, step, done=lambda: self.c.delete("boot"), delay=delay)


class Banner:
    """Killstreak-style banner for important items: slides in at the top, the name decodes, a timer runs out."""
    W, H = 440, 74

    def __init__(self, scene, area=None):
        self.sc, self.c = scene, scene.c
        self.queue = []
        self.busy = False
        self.area = area  # () -> (x1, x2): free space in the header; centred in the window if None

    def show(self, kicker, title, sub):
        self.queue.append((kicker, title, sub))
        if not self.busy:
            self._next()

    def _next(self):
        if not self.queue:
            self.busy = False
            return
        self.busy = True
        kicker, title, sub = self.queue.pop(0)
        c, W, H = self.c, self.W, self.H
        tag = "banner"
        x1, x2 = self.area() if self.area else (0, self.sc.w)
        if x2 - x1 < W:
            x1, x2 = 0, self.sc.w
        x0 = (x1 + x2) / 2 - W / 2
        self.sc.boost(5200)
        self.sc.sound("banner")

        def shape(dy, dx=0.0):
            y = dy
            x = x0 + dx
            return [x + 18, y, x + W, y, x + W - 18, y + H, x, y + H]

        body = c.create_polygon(*shape(-100), fill="#150c28", outline=look.GLOW, width=2, tags=(tag,))
        stripe = c.create_polygon(0, 0, 0, 0, 0, 0, fill=look.ACCENT, tags=(tag,))
        chev = c.create_text(0, 0, text="❯❯❯", font=("Segoe UI Symbol", 14, "bold"), fill="#ffffff", tags=(tag,))
        k = c.create_text(0, 0, text=kicker.upper(), font=look.F_LABEL, fill=look.PINK, anchor="w", tags=(tag,))
        t = c.create_text(0, 0, text="", font=("Bahnschrift", 16, "bold"), fill="#ffffff", anchor="w", tags=(tag,))
        s = c.create_text(0, 0, text=sub, font=look.F_SMALL, fill=look.MUTED, anchor="w", tags=(tag,))
        timer = c.create_line(0, 0, 0, 0, fill=look.GLOW, width=2, tags=(tag,))
        ring = c.create_polygon(*shape(-100), fill="", outline="#ffffff", width=2, tags=(tag,))
        st = {"y": -100.0, "dx": 0.0}

        def put():
            y, dx = st["y"], st["dx"]
            x = x0 + dx
            c.coords(body, *shape(y, dx))
            c.coords(stripe, x + 18, y, x + 92, y, x + 74, y + H, x, y + H)
            c.coords(chev, x + 46, y + H / 2)
            c.coords(k, x + 100, y + 17)
            c.coords(t, x + 100, y + 38)
            c.coords(s, x + 100, y + 59)
            c.tag_raise(tag)

        def enter(p):
            st["y"] = -100 + 110 * p
            put()

        def landed():
            def flash(p):
                g = 10 * anim.out_cubic(p)
                y = st["y"]
                x0d = x0 + st["dx"]
                c.coords(ring, x0d + 18 - g, y - g, x0d + W + g, y - g, x0d + W - 18 + g, y + H + g, x0d - g, y + H + g)
                c.itemconfigure(ring, outline=mix("#ffffff", look.VOID, p))
                c.itemconfigure(body, fill=mix("#3b2370", "#150c28", p))
            anim.Tween(c, 420, flash, done=lambda: c.delete(ring))
            anim.Tween(c, 520, lambda p: c.itemconfigure(t, text=look.scramble(title, p)),
                       done=lambda: c.itemconfigure(t, text=title))

            def tick(p):
                y = st["y"] + H - 2
                x = x0 + 96
                c.coords(timer, x, y, x + (W - 130) * (1 - p), y)
            anim.Tween(c, 3800, tick, done=leave)

        def leave():
            def out(p):
                st["y"] = 10 - 120 * p * p
                st["dx"] = random.uniform(-10, 10) * p
                put()
            anim.Tween(c, 340, out, done=finish)

        def finish():
            c.delete(tag)
            self._next()
        anim.Tween(c, 460, enter, ease=anim.out_back, done=landed)


class Toast:
    """Short message at the bottom centre (same call as the clean Toast)."""

    def __init__(self, scene):
        self.sc, self.c = scene, scene.c
        self.n = 0

    def show(self, text, color=look.OK, ms=2200):
        c = self.c
        c.delete("toast")
        self.n += 1
        n = self.n
        w = min(self.sc.w - 60, 40 + len(text) * 7.4)
        cx = self.sc.w / 2
        plate = c.create_polygon(0, 0, 0, 0, 0, 0, fill="#160d2b", outline=color, width=1, tags=("toast",))
        txt = c.create_text(0, 0, text="", font=("Segoe UI Semibold", 10), fill=color, tags=("toast",))

        def put(y):
            c.coords(plate, *look.chamfer(cx - w / 2, y, w, 36, 10))
            c.coords(txt, cx, y + 18)
            c.tag_raise("toast")

        def enter(p):
            put(self.sc.h + 10 - 92 * p)
            c.itemconfigure(txt, text=look.scramble(text, min(1.0, p * 1.4)))

        def leave():
            if n == self.n:
                anim.Tween(c, 260, lambda p: put(self.sc.h - 82 + 100 * p * p),
                           done=lambda: n == self.n and c.delete("toast"))
        anim.Tween(c, 420, enter, ease=anim.out_back, done=lambda: c.after(ms, leave))

