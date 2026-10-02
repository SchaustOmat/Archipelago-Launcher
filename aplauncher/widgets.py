"""Animated widgets for the launcher: buttons, status pill, tab bar, game cards, toggle, progress bar, toasts.

Everything moves through anim.engine, which ticks at the monitor's refresh rate. Widgets keep their canvas items
and only change colours/coordinates per frame instead of redrawing from scratch.
"""
import math
import tkinter as tk
import tkinter.font as tkfont

from . import anim, theme
from .anim import mix

lerp_color = mix  # old name


def ease(t: float) -> float:
    return anim.out_cubic(t)


def rr_points(x1, y1, x2, y2, r):
    r = max(0.0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
            x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


def rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    return canvas.create_polygon(rr_points(x1, y1, x2, y2, r), smooth=True, **kw)


def later(widget, ms, fn):
    """Run fn after ms on the animation clock (dies with the widget)."""
    anim.Tween(widget, 1, lambda t: None, done=fn, delay=ms)


def make_glow(canvas, n, bg):
    """n filled rounded rects behind a shape, stacked outermost first; index 0 is the innermost ring."""
    items = [rounded_rect(canvas, 0, 0, 1, 1, 10, fill=bg, outline="") for _ in range(n)]
    return items[::-1]


def paint_glow(canvas, rings, box, r, bg, glow, amount, strengths, step=1.0):
    """Soft glow: each ring is a slightly larger, fainter copy of the shape (filled, so no gaps in the edge)."""
    x1, y1, x2, y2 = box
    hidden = amount <= 0.004
    for i, (item, k) in enumerate(zip(rings, strengths)):
        if hidden:
            canvas.itemconfigure(item, state="hidden")
            continue
        o = round((i + 1) * step)
        canvas.coords(item, *rr_points(round(x1) - o, round(y1) - o, round(x2) + o, round(y2) + o, r + o))
        # Inner rings sit on top of outer ones, so each colour is the total brightness at that distance.
        canvas.itemconfigure(item, state="normal", fill=mix(bg, glow, amount * sum(strengths[i:])))


class _Painter:
    """Coalesces several animated values into one repaint per frame."""

    def _init_painter(self):
        self._dirty = False

    def _v(self, _=None):
        if not self._dirty:
            self._dirty = True
            self.after_idle(self._flush)

    def _flush(self):
        self._dirty = False
        try:
            self._paint()
        except tk.TclError:
            pass


class RoundButton(tk.Canvas, _Painter):
    G = 4  # room for the glow around the button
    KINDS = {  # base, hover, text, glow
        "primary": (theme.ACCENT, theme.ACCENT_HI, "#ffffff", theme.GLOW),
        "secondary": (theme.BUTTON, theme.BUTTON_HI, theme.FG, theme.ACCENT),
        "danger": ("#4a1d3a", "#6e2a52", "#ffd2e1", theme.ERR),
        "ghost": (theme.PANEL, theme.BUTTON, theme.FG, theme.BORDER),
    }
    RINGS = (0.28, 0.2, 0.14)

    def __init__(self, master, text, command=None, kind="secondary", bg=theme.PANEL, height=36, padx=18,
                 size=10, width=None):
        self.font = tkfont.Font(family="Segoe UI Semibold", size=size)
        self.text, self.command, self.kind, self.enabled = text, command, kind, True
        self.padx, self.fixed_width, self.bg = padx, width, bg
        super().__init__(master, height=height + 2 * self.G, width=self._width(), bg=bg, highlightthickness=0,
                         bd=0, cursor="hand2")
        self._init_painter()
        base = self.KINDS[kind][0]
        self.rings = make_glow(self, len(self.RINGS), bg)
        self.body = rounded_rect(self, 0, 0, 1, 1, 10, fill=base, outline="")
        self.shine = self.create_line(0, 0, 1, 0, fill=base)
        self.label = self.create_text(0, 0, text=text, font=self.font)
        self.h = anim.Value(self, 0, self._v, ms=170)                      # hover
        self.p = anim.Value(self, 0, self._v, ms=90)                       # pressed
        self.e = anim.Value(self, 1, self._v, ms=220)                      # enabled
        self.f = anim.Value(self, 0, self._v, ms=520)                      # click flash
        self.a = anim.Value(self, 1, self._v, ms=380, ease=anim.out_back)  # appear
        self.bind("<Enter>", lambda e: self.enabled and self.h.to(1))
        self.bind("<Leave>", lambda e: (self.h.to(0), self.p.to(0)))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Configure>", lambda e: self._paint())
        self._paint()

    def _width(self):
        return (self.fixed_width or self.font.measure(self.text) + 2 * self.padx) + 2 * self.G

    def _paint(self):
        w, h, G = int(self.cget("width")), int(self.cget("height")), self.G
        base, hover, fg, glow = self.KINDS[self.kind]
        hv, p, e, f, a = self.h.value, self.p.value, self.e.value, self.f.value, self.a.value
        vis = max(0.0, min(1.0, a))
        fill = mix(base, hover, hv)
        fill = mix(fill, "#000000", 0.22 * p)
        fill = mix(fill, "#ffffff", 0.18 * f)
        fill = mix(mix(self.bg, theme.BUTTON, 0.45), fill, e)
        fill = mix(self.bg, fill, vis)
        inset = 1.6 * p + (1 - a) * 6  # a overshoots a bit → the button pops slightly larger, then settles
        x1, y1, x2, y2 = G + inset, G + inset, w - G - inset, h - G - inset
        r = 10
        self.coords(self.body, *rr_points(x1, y1, x2, y2, r))
        self.itemconfigure(self.body, fill=fill)
        paint_glow(self, self.rings, (x1, y1, x2, y2), r, self.bg, glow, (hv * 0.6 + f * 0.8) * e * vis, self.RINGS)
        shine = fill if self.kind == "ghost" else mix(fill, "#ffffff", (0.10 + 0.10 * hv) * e * vis)
        self.itemconfigure(self.shine, fill=shine)
        self.coords(self.shine, x1 + r, y1 + 1, x2 - r, y1 + 1)
        self.coords(self.label, w / 2, h / 2 + 0.7 * p)
        self.itemconfigure(self.label, fill=mix(self.bg, mix(theme.DISABLED, fg, e), vis))

    def _press(self, _):
        if self.enabled:
            self.p.to(1, 70)

    def _release(self, e):
        if not self.enabled:
            return
        self.p.to(0, 180)
        if 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height() and self.command:
            self.f.set(1)
            self.f.to(0)
            self.command()

    def appear(self, delay=0):
        """Pop in when the button is shown (used when the visible button set changes)."""
        self.a.set(0)
        if delay:
            later(self, delay, lambda: self.a.to(1))
        else:
            self.a.to(1)

    def configure(self, cnf=None, **kw):
        changed = False
        if "state" in kw:
            self.enabled = kw.pop("state") != "disabled"
            super().configure(cursor="hand2" if self.enabled else "arrow")
            self.e.to(1 if self.enabled else 0)
            if not self.enabled:
                self.h.to(0)
        if "text" in kw:
            self.text = kw.pop("text")
            super().configure(width=self._width())
            self.itemconfigure(self.label, text=self.text)
            changed = True
        if "command" in kw:
            self.command = kw.pop("command")
        if cnf or kw:
            super().configure(cnf, **kw)
        if changed:
            self._paint()

    config = configure


class StatusPill(tk.Canvas, _Painter):
    STATES = {  # dot colour, pulses
        "offline": (theme.MUTED, False),
        "busy": (theme.WARN, True),
        "lobby": (theme.WARN, True),
        "connected": (theme.OK, True),
        "error": (theme.ERR, False),
    }
    H = 32

    def __init__(self, master, bg=theme.BG):
        self.font = tkfont.Font(family="Segoe UI Semibold", size=10)
        self.bg = bg
        super().__init__(master, height=self.H, width=self._width_for("Offline"), bg=bg, highlightthickness=0, bd=0)
        self._init_painter()
        self.state, self.text = "offline", "Offline"
        self.c0 = self.c1 = theme.MUTED
        self.frame = rounded_rect(self, 0, 0, 1, 1, 15, fill=theme.PANEL, outline=theme.BORDER)
        self.halo = self.create_oval(0, 0, 0, 0, fill="", outline="", state="hidden")
        self.ring = self.create_oval(0, 0, 0, 0, fill="", outline="", width=2, state="hidden")
        self.dot = self.create_oval(13, self.H / 2 - 5, 23, self.H / 2 + 5, fill=theme.MUTED, outline="")
        self.label = self.create_text(32, self.H / 2, text=self.text, anchor="w", fill=theme.FG, font=self.font)
        self.cv = anim.Value(self, 1, self._v, ms=450)
        self.width_v = anim.Value(self, self._width_for(self.text), self._set_width, ms=320, ease=anim.out_quint)
        self.tv = 1.0  # text visibility while cross-fading
        self.pulse = anim.Loop(self, self._pulse, start=False, fps=60, ambient=True)
        self._paint()

    def _width_for(self, text):
        return self.font.measure(text) + 48

    def _set_width(self, w):
        super().configure(width=int(w))
        self._v()

    def _color(self):
        return mix(self.c0, self.c1, self.cv.value)

    def set(self, state, text):
        if (state, text) == (self.state, self.text):
            return
        new_color, pulses = self.STATES.get(state, self.STATES["offline"])
        if state != self.state:
            self.c0, self.c1 = self._color(), new_color
            self.cv.set(0)
            self.cv.to(1)
        self.state = state
        if pulses:
            self.pulse.start()
        else:
            self.pulse.cancel()
            self.itemconfigure(self.halo, state="hidden")
            self.itemconfigure(self.ring, state="hidden")
        if text != self.text:
            self.text = text

            def fade(t):
                if t >= 0.5 and self.itemcget(self.label, "text") != self.text:
                    self.itemconfigure(self.label, text=self.text)
                    self.width_v.to(self._width_for(self.text))
                self.tv = abs(1 - 2 * t)
                self._v()
            anim.Tween(self, 300, fade, ease=anim.linear)

    def _paint(self):
        w, h = int(self.cget("width")), self.H
        self.coords(self.frame, *rr_points(1, 1, w - 1, h - 1, 15))
        self.itemconfigure(self.dot, fill=self._color())
        self.itemconfigure(self.label, fill=mix(theme.PANEL, theme.FG, self.tv))

    def _pulse(self, t):
        c, cy = self._color(), self.H / 2
        g = 0.5 + 0.5 * math.sin(t * 2 * math.pi / 1.6)
        r = 7 + 2.5 * g
        self.coords(self.halo, 18 - r, cy - r, 18 + r, cy + r)
        self.itemconfigure(self.halo, state="normal", fill=mix(theme.PANEL, c, 0.12 + 0.18 * g))
        ph = (t % 1.8) / 1.8  # radar ping
        rr = 5 + 7 * anim.out_cubic(ph)
        self.coords(self.ring, 18 - rr, cy - rr, 18 + rr, cy + rr)
        self.itemconfigure(self.ring, state="normal", outline=mix(c, theme.PANEL, anim.out_cubic(ph)))
        self.tag_raise(self.dot)


class TabBar(tk.Canvas):
    """Text tabs with a glowing underline that springs to the selected tab (the leading edge moves first)."""
    H = 46

    def __init__(self, master, tabs, on_select, bg=theme.BG):
        self.font = tkfont.Font(family="Segoe UI Semibold", size=11)
        super().__init__(master, height=self.H, bg=bg, highlightthickness=0, bd=0)
        self.bg, self.tabs, self.on_select = bg, tabs, on_select
        self.items, self.boxes, self.pills, self.hv, self.sv = {}, {}, {}, {}, {}
        x = 4
        for key, label in tabs:
            pill = rounded_rect(self, 0, 0, 1, 1, 10, fill=bg, outline="", tags=("tab", key))
            item = self.create_text(x + 16, 21, text=label, anchor="w", font=self.font, fill=theme.MUTED,
                                    tags=("tab", key))
            x1, _, x2, _ = self.bbox(item)
            self.items[key], self.boxes[key], self.pills[key] = item, (x1 - 16, x2 + 16), pill
            self.coords(pill, *rr_points(x1 - 10, 5, x2 + 10, 37, 10))
            self.hv[key] = anim.Value(self, 0, lambda v, k=key: self._paint_tab(k), ms=180)
            self.sv[key] = anim.Value(self, 0, lambda v, k=key: self._paint_tab(k), ms=260)
            self.tag_bind(key, "<Button-1>", lambda e, k=key: self.select(k))
            self.tag_bind(key, "<Enter>", lambda e, k=key: self.hv[k].to(1))
            self.tag_bind(key, "<Leave>", lambda e, k=key: self.hv[k].to(0))
            x = x2 + 16
        y = self.H - 1
        self.create_line(0, y, 4000, y, fill=theme.BORDER)
        self.glow2 = self.create_rectangle(0, 0, 0, 0, fill=mix(bg, theme.ACCENT, 0.10), outline="")
        self.glow1 = self.create_rectangle(0, 0, 0, 0, fill=mix(bg, theme.ACCENT, 0.24), outline="")
        self.bar = self.create_rectangle(0, 0, 0, 0, fill=theme.ACCENT_HI, outline="")
        self.spring = anim.Spring(self, [0, 0], self._bar, stiffness=300, damping=0.7)
        self.current = None
        self.configure(cursor="hand2")

    def _paint_tab(self, key):
        h, s = self.hv[key].value, self.sv[key].value
        self.itemconfigure(self.items[key], fill=mix(theme.MUTED, theme.FG, max(0.75 * h, s)))
        self.itemconfigure(self.pills[key], fill=mix(self.bg, theme.PANEL, h * (1 - 0.6 * s) + 0.35 * s))

    def _bar(self, x1, x2):
        y = self.H - 5
        if x2 - x1 < 1:
            x2 = x1 + 1
        self.coords(self.bar, x1, y, x2, y + 3)
        self.coords(self.glow1, x1 - 3, y - 2, x2 + 3, y + 4)
        self.coords(self.glow2, x1 - 8, y - 4, x2 + 8, y + 4)

    def select(self, key, animate=True):
        if self.current == key:
            return
        for k in self.items:
            self.sv[k].to(1 if k == key else 0)
        x1, x2 = self.boxes[key]
        goal = [x1 + 10, x2 - 10]
        if self.current is None or not animate:
            if animate:  # first appearance: the underline grows out of the tab's centre
                mid = (goal[0] + goal[1]) / 2
                self.spring.set([mid, mid])
                self.spring.to(goal, stiffness=[200, 200])
            else:
                self.spring.set(goal)
                for k in self.items:
                    self.sv[k].set(1 if k == key else 0)
        else:
            right = goal[0] > self.spring.x[0]
            fast, slow = 560, 190
            self.spring.to(goal, stiffness=[slow, fast] if right else [fast, slow])
        self.current = key
        self.on_select(key)


class GameCard(tk.Canvas, _Painter):
    """Selectable card with icon, title and subtitle; glows when selected and lifts on hover."""
    H, G = 88, 4
    RINGS = (0.22, 0.16, 0.1)

    def __init__(self, master, icon, title, subtitle, on_click, bg=theme.PANEL):
        super().__init__(master, height=self.H, width=170, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self._init_painter()
        self.bg, self.on_click = bg, on_click
        self.rings = make_glow(self, len(self.RINGS), bg)
        self.body = rounded_rect(self, 0, 0, 1, 1, 12, fill=theme.FIELD, outline=theme.BORDER, width=2)
        self.icon = self.create_text(0, 0, text=icon, anchor="w", font=("Segoe UI Emoji", 19), fill=theme.MUTED)
        self.title = self.create_text(0, 0, text=title, anchor="w", font=("Segoe UI Semibold", 11), fill=theme.FG)
        self.sub = self.create_text(0, 0, text=subtitle, anchor="w", font=("Segoe UI", 9), fill=theme.MUTED)
        self.check = self.create_oval(0, 0, 0, 0, fill=theme.ACCENT, outline="", state="hidden")
        self.tick = self.create_line(0, 0, 0, 0, 0, 0, fill="#ffffff", width=2, capstyle="round",
                                     joinstyle="round", state="hidden")
        self.h = anim.Value(self, 0, self._v, ms=200)
        self.s = anim.Value(self, 0, self._v, ms=420, ease=anim.out_quint)
        self.c = anim.Value(self, 0, self._v, ms=420, ease=anim.out_back)  # check mark pop
        self.p = anim.Value(self, 0, self._v, ms=90)
        self.selected = False
        self.bind("<Enter>", lambda e: self.h.to(1))
        self.bind("<Leave>", lambda e: (self.h.to(0), self.p.to(0)))
        self.bind("<ButtonPress-1>", lambda e: self.p.to(1, 70))
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Configure>", lambda e: self._paint())

    def _release(self, e):
        self.p.to(0, 200)
        if 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            self.on_click()

    def _paint(self):
        w, H, G = self.winfo_width(), self.H, self.G
        if w < 20:
            return
        h, s, p, c = self.h.value, self.s.value, self.p.value, self.c.value
        lift = 1.5 * h - 1.2 * p
        inset = 1.5 * p
        x1, y1, x2, y2 = G + inset, G + inset, w - G - inset, H - G - inset
        fill = mix(theme.FIELD, theme.BUTTON, max(0.5 * h, 0.8 * s))
        fill = mix(fill, theme.BUTTON_HI, 0.35 * h * s)
        border = mix(mix(theme.BORDER, theme.ACCENT, s), theme.ACCENT_HI, 0.45 * h)
        self.coords(self.body, *rr_points(x1, y1, x2, y2, 12))
        self.itemconfigure(self.body, fill=fill, outline=border)
        paint_glow(self, self.rings, (x1, y1, x2, y2), 12, self.bg, theme.GLOW, 0.9 * s + 0.45 * h, self.RINGS)
        tx = x1 + 16
        self.coords(self.icon, tx, H / 2 - 16 - lift)
        self.itemconfigure(self.icon, fill=mix(theme.MUTED, theme.GLOW, max(s, 0.6 * h)))
        self.coords(self.title, tx, H / 2 + 6 - lift)
        self.coords(self.sub, tx, H / 2 + 24 - lift)
        self.itemconfigure(self.sub, fill=mix(theme.MUTED, theme.FG, 0.4 * s))
        r = 9 * max(0.0, c)
        if r < 0.8:
            self.itemconfigure(self.check, state="hidden")
            self.itemconfigure(self.tick, state="hidden")
        else:
            cx, cy = x2 - 18, y1 + 18
            self.coords(self.check, cx - r, cy - r, cx + r, cy + r)
            k = r / 9
            self.coords(self.tick, cx - 4 * k, cy, cx - 1 * k, cy + 3 * k, cx + 4.5 * k, cy - 3.5 * k)
            self.itemconfigure(self.check, state="normal")
            self.itemconfigure(self.tick, state="normal" if r > 5 else "hidden")

    def set_selected(self, on):
        if on != self.selected:
            self.selected = on
            self.s.to(1 if on else 0)
            self.c.to(1 if on else 0, 420 if on else 200)


class Toggle(tk.Canvas, _Painter):
    """Switch with a sliding, slightly overshooting knob. Bound to a BooleanVar like a Checkbutton."""

    def __init__(self, master, text, variable, command=None, bg=theme.PANEL):
        self.font = tkfont.Font(family="Segoe UI", size=10)
        self.var, self.command, self.bg = variable, command, bg
        super().__init__(master, height=26, width=54 + self.font.measure(text), bg=bg, highlightthickness=0, bd=0,
                         cursor="hand2")
        self._init_painter()
        self.track = rounded_rect(self, 2, 4, 44, 22, 9, fill=theme.FIELD, outline=theme.BORDER)
        self.knob = self.create_oval(0, 0, 0, 0, fill=theme.MUTED, outline="")
        self.create_text(52, 13, text=text, anchor="w", font=self.font, fill=theme.FG)
        on = 1 if variable.get() else 0
        self.v = anim.Value(self, on, self._v, ms=380, ease=anim.out_back)
        self.c = anim.Value(self, on, self._v, ms=260)
        self.h = anim.Value(self, 0, self._v, ms=160)
        self.trace = variable.trace_add("write", lambda *a: self._sync())
        self.bind("<Enter>", lambda e: self.h.to(1))
        self.bind("<Leave>", lambda e: self.h.to(0))
        self.bind("<ButtonRelease-1>", self._click)
        self.bind("<Destroy>", lambda e: self._untrace(), add="+")
        self._paint()

    def _untrace(self):
        try:
            self.var.trace_remove("write", self.trace)
        except (tk.TclError, ValueError):
            pass

    def _sync(self):
        on = 1 if self.var.get() else 0
        self.v.to(on)
        self.c.to(on)

    def _click(self, e):
        if 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            self.var.set(not self.var.get())
            if self.command:
                self.command()

    def _paint(self):
        t, c, h = self.v.value, self.c.value, self.h.value
        self.itemconfigure(self.track, fill=mix(theme.FIELD, theme.ACCENT, c),
                           outline=mix(mix(theme.BORDER, theme.ACCENT_HI, c), theme.ACCENT_HI, 0.5 * h))
        x, r = anim.lerp(13, 33, t), 6.5 + 0.8 * h
        self.coords(self.knob, x - r, 13 - r, x + r, 13 + r)
        self.itemconfigure(self.knob, fill=mix(theme.MUTED, "#ffffff", c))


class GlowProgress(tk.Canvas, _Painter):
    """Thin progress bar: the fill glides to new values with a light sweeping over it; indeterminate = gliding
    segment."""
    H = 8

    def __init__(self, master, bg=theme.BG):
        super().__init__(master, height=self.H, width=200, bg=bg, highlightthickness=0, bd=0)
        self._init_painter()
        self.track = rounded_rect(self, 0, 0, 1, 1, 4, fill=theme.PANEL, outline="")
        self.fill = rounded_rect(self, 0, 0, 1, 1, 4, fill=theme.ACCENT, outline="", state="hidden")
        self.shine = self.create_rectangle(0, 0, 0, 0, fill=theme.ACCENT_HI, outline="", state="hidden")
        self.value = anim.Value(self, 0, self._v, ms=420, ease=anim.out_quint)
        self.mode = "det"
        self.t = 0.0
        self.loop = anim.Loop(self, self._tick, start=False)
        self.bind("<Configure>", lambda e: self._paint())

    def set(self, frac):
        self.mode = "det"
        self.value.to(max(0.0, min(1.0, frac)))
        self.loop.start()

    def indeterminate(self):
        self.mode = "indet"
        self.loop.start()

    def reset(self):
        self.mode = "det"
        self.loop.cancel()
        self.value.set(0)

    def _tick(self, t):
        self.t = t
        self._paint()

    def _paint(self):
        w, H = self.winfo_width(), self.H
        if w < 10:
            return
        self.coords(self.track, *rr_points(0, 0, w, H, 4))
        if self.mode == "indet":
            ph = (self.t / 1.1) % 2
            ph = anim.in_out_sine(ph if ph <= 1 else 2 - ph)
            seg = w * 0.28
            x1 = ph * (w - seg)
            x2 = x1 + seg
            color = mix(theme.ACCENT, theme.ACCENT_HI, 0.5 + 0.5 * math.sin(self.t * 4))
        else:
            x1, x2 = 0, w * self.value.value
            color = theme.ACCENT
        if x2 - x1 < 2:
            self.itemconfigure(self.fill, state="hidden")
            self.itemconfigure(self.shine, state="hidden")
            return
        self.coords(self.fill, *rr_points(x1, 0, x2, H, 4))
        self.itemconfigure(self.fill, state="normal", fill=color)
        band = 70  # light sweeping across the filled part
        c = x1 - band / 2 + (self.t * 260) % ((x2 - x1) + band + 200)
        b1, b2 = max(x1 + 4, c - band / 2), min(x2 - 4, c + band / 2)
        if self.mode == "det" and b2 > b1:
            self.coords(self.shine, b1, 2, b2, H - 2)
            self.itemconfigure(self.shine, state="normal", fill=mix(theme.ACCENT, theme.GLOW, 0.55))
        else:
            self.itemconfigure(self.shine, state="hidden")


class AuroraLine(tk.Canvas):
    """Thin purple light band that drifts slowly along the top of the window."""
    PERIOD = 640

    def __init__(self, master, height=3, bg=theme.BG):
        super().__init__(master, height=height, bg=bg, highlightthickness=0, bd=0)
        stops = [theme.DEEP, theme.ACCENT, theme.GLOW, theme.PINK, theme.GLOW, theme.ACCENT, theme.DEEP]
        P = self.PERIOD
        period = []
        for x in range(P):
            u = x / P * (len(stops) - 1)
            i = int(u)
            period.append(mix(stops[i], stops[min(i + 1, len(stops) - 1)], u - i))
        # One pre-rendered image that slides along: far cheaper for Tk than moving hundreds of rectangles.
        reps = self.winfo_screenwidth() // P + 2
        row = "{" + " ".join(period * reps) + "}"
        self.img = tk.PhotoImage(width=P * reps, height=height)
        self.img.put(" ".join([row] * height))
        self.item = self.create_image(0, 0, image=self.img, anchor="nw")
        self.off = 0
        anim.Loop(self, self._drift, fps=40, ambient=True)

    def _drift(self, t):
        off = -(int(t * 38) % self.PERIOD)  # whole pixels: only redraw when something visibly moves
        if off != self.off:
            self.coords(self.item, off, 0)
            self.off = off


class ShimmerTitle(tk.Canvas):
    """Title with a breathing diamond and a highlight that sweeps over the letters now and then."""

    def __init__(self, master, text, bg=theme.BG, size=18):
        self.font = tkfont.Font(family="Segoe UI Semibold", size=size)
        h = self.font.metrics("linespace") + 4
        dx = h * 0.9
        super().__init__(master, height=h, width=int(dx + self.font.measure(text) + 6), bg=bg, highlightthickness=0,
                         bd=0)
        self.bg, self.cy, self.dcx = bg, h / 2, h * 0.32
        self.diamond_glow = self.create_polygon(0, 0, 0, 0, fill="", outline="")
        self.diamond = self.create_polygon(0, 0, 0, 0, fill=theme.ACCENT, outline="")
        self.chars, x = [], dx
        for ch in text:
            item = self.create_text(x, self.cy, text=ch, anchor="w", font=self.font, fill=theme.FG)
            self.chars.append((item, x + self.font.measure(ch) / 2))
            x += self.font.measure(ch)
        self.width_px = x
        self.last = [None] * len(self.chars)
        self.dlast = None
        self.loop = anim.Loop(self, self._tick, fps=30, ambient=True)

    def _diamond(self, item, r):
        cx, cy = self.dcx, self.cy
        self.coords(item, cx, cy - r, cx + r, cy, cx, cy + r, cx - r, cy)

    def _tick(self, t):
        g = 0.5 + 0.5 * math.sin(t * 2 * math.pi / 2.4)
        state = (round(7 + 1.2 * g), round(10 + 2.5 * g), mix(theme.ACCENT, theme.GLOW, g),
                 mix(self.bg, theme.ACCENT, 0.18 + 0.12 * g))
        if state != self.dlast:  # only touch the canvas when a pixel or colour actually changes
            self.dlast = state
            self._diamond(self.diamond, state[0])
            self._diamond(self.diamond_glow, state[1])
            self.itemconfigure(self.diamond, fill=state[2])
            self.itemconfigure(self.diamond_glow, fill=state[3])
        ph = (t % 5.5) / 1.6  # the sweep takes 1.6 s, then a pause
        pos = -60 + anim.in_out_sine(ph) * (self.width_px + 120) if ph <= 1 else None
        self.loop.fps = None if pos is not None else 30  # full frame rate only while the light sweeps
        for i, (item, cx) in enumerate(self.chars):
            k = 0.0 if pos is None else max(0.0, 1 - abs(cx - pos) / 55)
            color = mix(theme.FG, theme.GLOW, anim.in_out_sine(k)) if k else theme.FG
            if color != self.last[i]:
                self.last[i] = color
                self.itemconfigure(item, fill=color)


class CardGlow:
    """The border of a card frame lights up on hover; flash() sends a short light pulse through it."""

    def __init__(self, frame, base=theme.BORDER, glow=theme.ACCENT):
        self.frame, self.base, self.glow = frame, base, glow
        self.h = anim.Value(frame, 0, self._paint, ms=240)
        self.f = anim.Value(frame, 0, self._paint, ms=900)
        frame.bind("<Enter>", lambda e: self.h.to(1), add="+")
        frame.bind("<Leave>", self._leave, add="+")

    def _leave(self, _):
        try:
            x, y = self.frame.winfo_pointerxy()
            w = self.frame.winfo_containing(x, y)
        except (tk.TclError, KeyError):
            w = None
        if w is not None and str(w).startswith(str(self.frame)):
            return  # moved onto a child widget, still inside the card
        self.h.to(0)

    def _paint(self, _=None):
        f = self.f.value
        color = mix(self.base, self.glow, 0.6 * self.h.value)
        if f > 0:
            color = mix(color, theme.GLOW, f)
        self.frame.configure(highlightbackground=color)

    def flash(self, delay=0):
        def go():
            self.f.set(1)
            self.f.to(0)
        if delay:
            later(self.frame, delay, go)
        else:
            go()


class Toast:
    """Message that springs in at the bottom of the window, glows briefly and slides away again."""

    def __init__(self, root):
        self.root = root
        self.label = None

    def show(self, text, color=theme.OK, ms=2200):
        if self.label:
            self.label.destroy()
        lbl = tk.Label(self.root, text=text, bg=theme.BUTTON, fg=color, font=("Segoe UI Semibold", 10),
                       padx=18, pady=9, highlightthickness=2, highlightbackground=theme.GLOW)
        self.label = lbl

        def place(y):
            lbl.place(relx=0.5, rely=1.0, y=round(y), anchor="s")

        def enter(t):
            place(anim.lerp(60, -22, t))
            lbl.configure(highlightbackground=mix(theme.GLOW, theme.ACCENT, max(0.0, min(1.0, t))))

        def leave():
            anim.Tween(lbl, 260, lambda t: place(anim.lerp(-22, 70, t)), ease=lambda t: t * t,
                       done=lbl.destroy, delay=ms)
        anim.Tween(lbl, 460, enter, ease=anim.out_back, done=leave)


def fade_in(win, ms=320):
    try:
        win.attributes("-alpha", 0.0)
    except tk.TclError:
        return

    def step(t):
        try:
            win.attributes("-alpha", t)
        except tk.TclError:
            pass
    anim.Tween(win, ms, step, ease=anim.out_cubic, delay=30)
