"""Interface elements drawn as items on the scene canvas.

They copy the small interface of the clean widgets the shared App logic uses (configure(text=, state=,
foreground=), pack()/pack_forget(), set_selected(), set(), select()), so gui.App works unchanged on top of them.
Every element can build itself up (build()), which the intro and the tab change use."""
import math
import random
import tkinter as tk
from tkinter import font as tkfont

from PIL import Image, ImageTk

from .. import anim
from . import look

_fonts = {}


def measure(font, text):
    f = _fonts.get(font)
    if f is None:
        f = _fonts[font] = tkfont.Font(font=font)
    return f.measure(text)


def mix(a, b, t):
    return anim.mix(a, b, t)


# ======================================================================================================
class Elem:
    def __init__(self, scene, page=None):
        self.sc, self.c, self.page = scene, scene.c, page
        self.tag = f"e{id(self)}"
        self.fx = self.tag + "fx"       # temporary build items, never shown by sync()
        self.shown = True               # pack()/pack_forget() of the logic
        self.built = True               # False while the build-up has not reached this element
        self.x = self.y = 0
        self.w = self.h = 0
        scene.add(self)

    def visible(self):
        return self.shown and self.built and self.sc.page_visible(self.page)

    def sync(self):
        self.c.itemconfigure(self.tag, state="normal" if self.visible() else "hidden")

    def place(self, x, y, w=None, h=None):
        self.x, self.y = x, y
        if w is not None:
            self.w = w
        if h is not None:
            self.h = h
        self.draw()
        return self

    def draw(self):
        pass

    # Compatibility with the pack-based clean widgets.
    def pack(self, **_kw):
        if not self.shown:
            self.shown = True
            self.sync()

    def pack_forget(self):
        if self.shown:
            self.shown = False
            self.sync()

    def winfo_ismapped(self):
        return self.visible()

    def hide_for_build(self):
        self.built = False
        self.sync()

    def reveal(self):
        self.built = True
        self.sync()

    def build(self, tl, delay, quick=False):
        """Default: materialise out of pixel noise."""
        self.hide_for_build()
        if self.w and self.h:
            materialize(self.sc, tl, (self.x, self.y, self.x + self.w, self.y + self.h), delay,
                        220 if quick else 420, self.reveal)
        else:
            tl.at(delay, self.reveal)

    def bind(self, seq, fn):
        self.c.tag_bind(self.tag, seq, fn)

    def hand(self):
        self.bind("<Enter>", lambda e: self.c.configure(cursor="hand2"), )
        self.c.tag_bind(self.tag, "<Leave>", lambda e: self.c.configure(cursor=""), add="+")


def materialize(scene, tl, box, delay, ms, on_show, block=3):
    """Pixel noise appears over box, the element switches on underneath, the noise dissolves."""
    c = scene.c
    x1, y1, x2, y2 = (int(v) for v in box)
    w, h = max(2, x2 - x1), max(2, y2 - y1)
    field = Image.effect_noise((w // block + 1, h // block + 1), 110).resize(
        (w // block * block + block, h // block * block + block), Image.NEAREST).crop((0, 0, w, h))
    colors = []
    for _i in range(3):
        r = Image.effect_noise((w // block + 1, h // block + 1), 90).resize(field.size, Image.NEAREST).crop((0, 0, w, h))
        colors.append(Image.merge("RGB", (r.point(lambda v: min(255, v + 40)), r.point(lambda v: v // 2 + 20),
                                         r.point(lambda v: min(255, v + 90)))))
    state = {"item": None, "photo": None, "shown": False}

    def update(p):
        if p < 0.35:
            thr = 255 - int(p / 0.35 * 255)
        else:
            if not state["shown"]:
                state["shown"] = True
                on_show()
            thr = int((p - 0.35) / 0.65 * 255)
        if p >= 1:
            return
        alpha = field.point(lambda v, t=thr: 220 if v > t else 0)
        img = random.choice(colors).copy()
        img.putalpha(alpha)
        state["photo"] = ImageTk.PhotoImage(img)
        if state["item"] is None:
            state["item"] = c.create_image(x1, y1, image=state["photo"], anchor="nw", tags=("fx",))
        else:
            c.itemconfigure(state["item"], image=state["photo"])
        c.tag_raise(state["item"])

    def done():
        if not state["shown"]:
            on_show()
        if state["item"] is not None:
            c.delete(state["item"])
        state["photo"] = None
    tl.add(delay, ms, update, done=done)


# ======================================================================================================
class Text(Elem):
    def __init__(self, scene, page, text="", font=look.F_BODY, fill=look.FG, anchor="nw", width=0):
        super().__init__(scene, page)
        self.text, self.fill, self.font, self.anchor = text, fill, font, anchor
        self.id = self.c.create_text(0, 0, text=text, font=font, fill=fill, anchor=anchor, width=width,
                                     tags=(self.tag,))
        self.anim = None

    def draw(self):
        self.c.coords(self.id, self.x, self.y)

    def set_width(self, width):
        self.c.itemconfigure(self.id, width=width)

    def configure(self, text=None, foreground=None, fg=None, **_kw):
        if text is not None and text != self.text:
            self.text = text
            if not (self.anim and self.anim.active):
                self.c.itemconfigure(self.id, text=text)
        color = foreground or fg
        if color:
            self.fill = color
            self.c.itemconfigure(self.id, fill=color)

    config = configure

    def cget(self, key):
        return self.text if key == "text" else self.fill

    def text_width(self):
        return measure(self.font, self.text)

    def scramble_to(self, text, ms=420, delay=0):
        """New text decodes itself out of random glyphs."""
        self.text = text
        if self.anim:
            self.anim.cancel()
        self.anim = anim.Tween(self.c, ms, lambda p: self.c.itemconfigure(self.id, text=look.scramble(self.text, p)),
                               delay=delay)

    def build(self, tl, delay, quick=False):
        self.hide_for_build()
        ms = 260 if quick else max(320, min(800, 18 * len(self.text)))

        def update(p):
            if not self.built:
                self.reveal()
            self.c.itemconfigure(self.id, text=look.scramble(self.text, p))
        tl.add(delay, ms, update, done=lambda: self.c.itemconfigure(self.id, text=self.text))


# ======================================================================================================
KINDS = {
    "primary": dict(fill="#5426b8", hover="#7c4dff", line=look.GLOW, text="#ffffff"),
    "secondary": dict(fill="#1a1230", hover="#2b1e4e", line="#5a45a0", text=look.FG),
    "ghost": dict(fill="#0d0918", hover="#1d1436", line="#3e3168", text=look.MUTED),
    "danger": dict(fill="#34121f", hover="#5a1d33", line=look.ERR, text="#ffd6df"),
}


class Button(Elem):
    def __init__(self, scene, page, text, command=None, kind="secondary", height=32, size=10, padx=16):
        super().__init__(scene, page)
        self.command, self.kind = command, kind
        self.font = ("Bahnschrift SemiBold", size)
        self.padx, self.h = padx, height
        self.text = look.plain(text).upper()
        self.w = measure(self.font, self.text) + 2 * padx
        self.state = "normal"
        self.inside = False
        self.poly = self.c.create_polygon(0, 0, 0, 0, 0, 0, tags=(self.tag,), width=1)
        self.txt = self.c.create_text(0, 0, text=self.text, font=self.font, tags=(self.tag,))
        self.hov = anim.Value(self.c, 0, self._paint, ms=160)
        self.flash_v = 0.0
        self.bind("<Enter>", self._enter)
        self.c.tag_bind(self.tag, "<Leave>", self._leave)
        self.c.tag_bind(self.tag, "<ButtonPress-1>", self._press)
        self.c.tag_bind(self.tag, "<ButtonRelease-1>", self._release)
        self._paint(0)

    def draw(self):
        x, y = self.x, self.y
        self.c.coords(self.poly, *look.chamfer(x, y, self.w, self.h, 8))
        self.c.coords(self.txt, x + self.w / 2, y + self.h / 2)

    def _colors(self, h):
        k = KINDS[self.kind]
        if self.state == "disabled":
            return "#130d21", "#2a2142", look.theme.DISABLED
        fill = mix(k["fill"], k["hover"], h)
        if self.flash_v:
            fill = mix(fill, "#ffffff", self.flash_v)
        return fill, mix(k["line"], look.GLOW, h * 0.8), mix(k["text"], "#ffffff", h)

    def _paint(self, h=None):
        h = self.hov.value if h is None else h
        fill, line, text = self._colors(h)
        self.c.itemconfigure(self.poly, fill=fill, outline=line)
        self.c.itemconfigure(self.txt, fill=text)

    def _enter(self, _e):
        self.inside = True
        if self.state != "disabled":
            self.c.configure(cursor="hand2")
            self.hov.to(1)

    def _leave(self, _e):
        self.inside = False
        self.c.configure(cursor="")
        self.hov.to(0)

    def _press(self, _e):
        if self.state != "disabled":
            self.flash(0.35, 200)

    def _release(self, e):
        if self.state == "disabled" or not self.visible():
            return
        if self.x <= e.x <= self.x + self.w and self.y <= e.y <= self.y + self.h and self.command:
            self.sc.sound("click")
            self.command()

    def flash(self, amount=1.0, ms=300):
        def step(t):
            self.flash_v = amount * (1 - t)
            self._paint()
        anim.Tween(self.c, ms, step, ease=anim.out_cubic)

    def configure(self, state=None, text=None, **_kw):
        if state is not None and state != self.state:
            self.state = state
            if state == "disabled":
                self.hov.set(0)
            elif self.inside:
                self.hov.to(1)
            self._paint()
        if text is not None:
            self.text = look.plain(text).upper()
            self.w = measure(self.font, self.text) + 2 * self.padx
            self.c.itemconfigure(self.txt, text=self.text)
            self.draw()

    config = configure

    def cget(self, key):
        return self.state if key == "state" else self.text

    def appear(self, delay=0):
        """Newly shown button: quick bracket build."""
        from .scene import Timeline
        self.build(Timeline(self.c), delay, quick=True)

    def build(self, tl, delay, quick=False):
        """Corner brackets close in, a line sweeps across, the face flashes up."""
        self.hide_for_build()
        ms = 300 if quick else 560
        x, y, w, h = self.x, self.y, self.w, self.h
        L = 7
        corners = [((x, y), (1, 1)), ((x + w, y), (-1, 1)), ((x + w, y + h), (-1, -1)), ((x, y + h), (1, -1))]
        cx, cy = x + w / 2, y + h / 2
        items = {}

        def update(p):
            if "br" not in items:
                items["br"] = [self.c.create_line(0, 0, 0, 0, 0, 0, fill=look.GLOW, width=2, tags=(self.fx, "fx"))
                               for _c in corners]
                items["line"] = self.c.create_line(cx, cy, cx, cy, fill="#ffffff", width=2, tags=(self.fx, "fx"))
            if not (self.shown and self.sc.page_visible(self.page)):
                self.c.itemconfigure(self.fx, state="hidden")
                return
            self.c.itemconfigure(self.fx, state="normal")
            b = anim.out_cubic(min(1.0, p / 0.4))
            for item, ((px, py), (dx, dy)) in zip(items["br"], corners):
                qx, qy = cx + (px - cx) * (0.35 + 0.65 * b), cy + (py - cy) * (0.35 + 0.65 * b)
                self.c.coords(item, qx, qy + dy * L, qx, qy, qx + dx * L, qy)
            if 0.35 < p < 0.68:
                s = anim.out_cubic((p - 0.35) / 0.3)
                self.c.coords(items["line"], cx - w / 2 * s, cy, cx + w / 2 * s, cy)
            else:
                self.c.coords(items["line"], cx, cy, cx, cy)
            if p >= 0.62 and not self.built:
                self.reveal()
                self.c.itemconfigure(self.txt, text=look.scramble(self.text, 0))
            if self.built:
                q = (p - 0.62) / 0.38
                self.flash_v = max(0.0, 1 - q) * 0.9
                self._paint()
                self.c.itemconfigure(self.txt, text=look.scramble(self.text, min(1.0, q * 1.3)))
            self.c.tag_raise(self.fx)

        def done():
            self.c.delete(self.fx)
            self.flash_v = 0
            if not self.built:
                self.reveal()
            self.c.itemconfigure(self.txt, text=self.text)
            self._paint()
        tl.add(delay, ms, update, done=done)


# ======================================================================================================
class Toggle(Elem):
    def __init__(self, scene, page, text, variable, command=None):
        super().__init__(scene, page)
        self.var, self.command = variable, command
        self.text = text
        self.track = self.c.create_line(0, 0, 0, 0, width=16, capstyle="round", tags=(self.tag,))
        self.knob = self.c.create_oval(0, 0, 0, 0, width=0, tags=(self.tag,))
        self.txt = self.c.create_text(0, 0, text=text, font=look.F_BODY, fill=look.FG, anchor="w", tags=(self.tag,))
        self.w, self.h = 44 + measure(look.F_BODY, text), 20
        self.v = anim.Value(self.c, 1 if variable.get() else 0, lambda v: self.draw(), ms=200)
        self.trace = variable.trace_add("write", lambda *a: self.v.to(1 if self.var.get() else 0))
        self.bind("<Button-1>", self._click)
        self.hand()

    def _click(self, _e):
        if not self.visible():
            return
        self.var.set(not self.var.get())
        self.sc.sound("click")
        if self.command:
            self.command()

    def draw(self):
        x, y = self.x, self.y + self.h / 2
        v = self.v.value
        self.c.coords(self.track, x + 8, y, x + 26, y)
        self.c.itemconfigure(self.track, fill=mix("#241a3d", look.ACCENT, v))
        kx = x + 8 + 18 * v
        self.c.coords(self.knob, kx - 6, y - 6, kx + 6, y + 6)
        self.c.itemconfigure(self.knob, fill=mix(look.MUTED, "#ffffff", v))
        self.c.coords(self.txt, x + 42, y)


# ======================================================================================================
class Choice(Elem):
    """Selectable tile (game choice): plain glass, symbol and text, no pictures."""

    def __init__(self, scene, page, icon, title, sub, on_click):
        super().__init__(scene, page)
        self.on_click = on_click
        self.sel = anim.Value(self.c, 0, lambda v: self._paint(), ms=240)
        self.hov = anim.Value(self.c, 0, lambda v: self._paint(), ms=150)
        self.poly = self.c.create_polygon(0, 0, 0, 0, 0, 0, width=1, tags=(self.tag,))
        self.icon = self.c.create_text(0, 0, text=icon, font=("Segoe UI Symbol", 20), anchor="w", tags=(self.tag,))
        self.title = self.c.create_text(0, 0, text=title.upper(), font=("Bahnschrift SemiBold", 11), anchor="w",
                                        tags=(self.tag,))
        self.sub = self.c.create_text(0, 0, text=sub, font=look.F_SMALL, fill=look.MUTED, anchor="w", tags=(self.tag,))
        self.mark = self.c.create_text(0, 0, text="◆ " + "AKTIV", font=look.F_LABEL, anchor="ne", tags=(self.tag,))
        self.bind("<Enter>", lambda e: (self.hov.to(1), self.c.configure(cursor="hand2")))
        self.c.tag_bind(self.tag, "<Leave>", lambda e: (self.hov.to(0), self.c.configure(cursor="")))
        self.c.tag_bind(self.tag, "<ButtonRelease-1>", self._click)
        self._paint()

    def _click(self, _e):
        if self.visible():
            self.sc.sound("click")
            self.on_click()

    def set_mark_text(self, text):
        self.c.itemconfigure(self.mark, text="◆ " + text)

    def draw(self):
        x, y, w, h = self.x, self.y, self.w, self.h
        self.c.coords(self.poly, *look.chamfer(x, y, w, h, 12))
        self.c.coords(self.icon, x + 16, y + h / 2 - 2)
        self.c.coords(self.title, x + 56, y + h / 2 - 10)
        self.c.coords(self.sub, x + 56, y + h / 2 + 12)
        self.c.coords(self.mark, x + w - 10, y + 8)
        self._paint()

    def _paint(self):
        s, hv = self.sel.value, self.hov.value
        self.c.itemconfigure(self.poly, fill=mix(mix("#120b22", "#1d1338", hv), "#2c1a5c", s),
                             outline=mix(mix(look.WIRE, "#7a64c0", hv), look.GLOW, s))
        self.c.itemconfigure(self.icon, fill=mix(look.MUTED, look.GLOW, max(s, hv * 0.6)))
        self.c.itemconfigure(self.title, fill=mix(look.FG, "#ffffff", s))
        self.c.itemconfigure(self.mark, fill=mix("#1d1338", look.OK, s))

    def set_selected(self, on):
        self.sel.to(1 if on else 0)


# ======================================================================================================
PILL = {"offline": look.MUTED, "busy": look.WARN, "lobby": look.ACCENT_HI, "connected": look.OK}


class Pill(Elem):
    """Status pill, right-aligned at (x, y center)."""

    def __init__(self, scene, page=None):
        super().__init__(scene, page)
        self.state, self.text = "offline", "Offline"
        self.color = PILL["offline"]
        self.poly = self.c.create_polygon(0, 0, 0, 0, 0, 0, fill="#110b1f", width=1, tags=(self.tag,))
        self.dot = self.c.create_oval(0, 0, 0, 0, width=0, tags=(self.tag,))
        self.txt = self.c.create_text(0, 0, text=self.text.upper(), font=look.F_BUTTON, anchor="w", tags=(self.tag,))
        self.anim = None
        scene.hooks.append(self._pulse)

    def _size(self):
        return measure(look.F_BUTTON, self.text.upper()) + 44, 30

    def draw(self):
        w, h = self._size()
        self.w, self.h = w, h
        x1 = self.x - w
        y1 = self.y - h / 2
        self.c.coords(self.poly, *look.chamfer(x1, y1, w, h, 8))
        self.c.coords(self.dot, x1 + 14, self.y - 4, x1 + 22, self.y + 4)
        self.c.coords(self.txt, x1 + 30, self.y)
        self.c.itemconfigure(self.poly, outline=mix(look.WIRE, self.color, 0.6))
        self.c.itemconfigure(self.txt, fill=self.color)

    def set(self, state, text):
        if (state, text) == (self.state, self.text):
            return
        old = self.color
        self.state, self.text = state, text
        new = PILL.get(state, look.MUTED)
        self.draw()
        if self.anim:
            self.anim.cancel()

        def step(t):
            self.color = mix(old, new, t)
            self.c.itemconfigure(self.txt, text=look.scramble(self.text.upper(), t), fill=self.color)
            self.c.itemconfigure(self.poly, outline=mix(look.WIRE, self.color, 0.6))
        self.anim = anim.Tween(self.c, 360, step)

    def _pulse(self, now):
        if not self.visible():
            return
        a = 0.5 + 0.5 * math.sin(now * (6 if self.state == "busy" else 3))
        self.c.itemconfigure(self.dot, fill=mix("#2a1f45", self.color, 0.45 + 0.55 * a))

    def build(self, tl, delay, quick=False):
        self.hide_for_build()
        w, h = self._size()
        materialize(self.sc, tl, (self.x - w, self.y - h / 2, self.x, self.y + h / 2), delay, 420, self.reveal)


# ======================================================================================================
class Progress(Elem):
    def __init__(self, scene, page=None):
        super().__init__(scene, page)
        self.frac, self.indet = 0.0, False
        self.back = self.c.create_line(0, 0, 0, 0, fill="#21183a", width=4, tags=(self.tag,))
        self.bar = self.c.create_line(0, 0, 0, 0, fill=look.ACCENT_HI, width=4, tags=(self.tag,))
        self.tip = self.c.create_oval(0, 0, 0, 0, fill="#ffffff", width=0, tags=(self.tag,))
        self.v = anim.Value(self.c, 0, lambda v: self.draw(), ms=260)
        self.loop = None

    def draw(self, now=None):
        x, y, w = self.x, self.y, self.w
        self.c.coords(self.back, x, y, x + w, y)
        if self.indet:
            t = (now or 0) * 0.7 % 1.4 - 0.2
            a, b = max(0, t) * w, min(1, t + 0.25) * w
            self.c.coords(self.bar, x + a, y, x + max(a, b), y)
            tx = x + max(a, b)
        else:
            tx = x + w * self.v.value
            self.c.coords(self.bar, x, y, tx, y)
        self.c.coords(self.tip, tx - 3, y - 3, tx + 3, y + 3)

    def set(self, frac):
        self._stop()
        self.indet = False
        self.v.to(max(0.0, min(1.0, frac)))

    def indeterminate(self):
        if self.loop is None:
            self.indet = True
            self.loop = anim.Loop(self.c, lambda t: self.draw(t), fps=40)

    def reset(self):
        self._stop()
        self.indet = False
        self.v.set(0)

    def _stop(self):
        if self.loop:
            self.loop.cancel()
            self.loop = None


# ======================================================================================================
class Tabs(Elem):
    def __init__(self, scene, tabs, on_select):
        super().__init__(scene, None)
        self.on_select = on_select
        self.keys = [k for k, _t in tabs]
        self.labels = {k: look.plain(t).upper() for k, t in tabs}
        self.items = {k: self.c.create_text(0, 0, text=self.labels[k], font=look.F_TAB, fill=look.MUTED, anchor="w",
                                            tags=(self.tag,)) for k in self.keys}
        self.nums = {k: self.c.create_text(0, 0, text=f"0{i + 1}", font=look.F_LABEL, fill=look.WIRE, anchor="w",
                                           tags=(self.tag,)) for i, k in enumerate(self.keys)}
        self.under = self.c.create_rectangle(0, 0, 0, 0, fill=look.GLOW, width=0, tags=(self.tag,))
        self.rule = self.c.create_line(0, 0, 0, 0, fill="#2a2046", tags=(self.tag,))
        self.current = None
        self.pos = {}
        self.spring = anim.Spring(self.c, [0, 0], self._bar, stiffness=260, damping=0.78)
        for k, item in self.items.items():
            self.c.tag_bind(item, "<Button-1>", lambda e, k=k: self.select(k))
            self.c.tag_bind(self.nums[k], "<Button-1>", lambda e, k=k: self.select(k))
            self.c.tag_bind(item, "<Enter>", lambda e, k=k: self._hover(k, True))
            self.c.tag_bind(item, "<Leave>", lambda e, k=k: self._hover(k, False))

    def _hover(self, k, on):
        self.c.configure(cursor="hand2" if on else "")
        if k != self.current:
            self.c.itemconfigure(self.items[k], fill=look.FG if on else look.MUTED)

    def draw(self):
        x = self.x
        for k in self.keys:
            self.c.coords(self.nums[k], x, self.y)
            self.c.coords(self.items[k], x + 20, self.y)
            w = measure(look.F_TAB, self.labels[k])
            self.pos[k] = (x, x + 20 + w)
            x += 20 + w + 34
        self.c.coords(self.rule, self.x - 4, self.y + 18, self.w, self.y + 18)
        if self.current:
            a, b = self.pos[self.current]
            self.spring.set([a, b])

    def _bar(self, a, b):
        self.c.coords(self.under, a, self.y + 16, b, self.y + 19)

    def select(self, key, animate=True):
        if key == self.current:
            return
        self.current = key
        for k in self.keys:
            self.c.itemconfigure(self.items[k], fill="#ffffff" if k == key else look.MUTED)
            self.c.itemconfigure(self.nums[k], fill=look.GLOW if k == key else look.WIRE)
        if key in self.pos:
            if animate:
                self.spring.to(list(self.pos[key]))
            else:
                self.spring.set(list(self.pos[key]))
        self.on_select(key)

    def build(self, tl, delay, quick=False):
        self.hide_for_build()

        def update(p):
            if not self.built:
                self.reveal()
            for k in self.keys:
                self.c.itemconfigure(self.items[k], text=look.scramble(self.labels[k], p))
            a = anim.out_cubic(p)
            self.c.coords(self.rule, self.x - 4, self.y + 18, self.x - 4 + (self.w - self.x + 4) * a, self.y + 18)
        tl.add(delay, 600, update, done=self.draw)


# ======================================================================================================
class Panel(Elem):
    """Glass panel with a chamfered outline and a title; builds as wireframe → particles snap in → print fill."""

    def __init__(self, scene, page, title=None):
        super().__init__(scene, page)
        self.title = title.upper() if title else ""
        self.glass = None
        self.children = []
        self.outline = self.c.create_polygon(0, 0, 0, 0, 0, 0, fill="", outline=look.WIRE, tags=(self.tag,))
        self.cut1 = self.c.create_line(0, 0, 0, 0, fill=look.ACCENT_HI, width=2, tags=(self.tag,))
        self.cut2 = self.c.create_line(0, 0, 0, 0, fill=look.ACCENT_HI, width=2, tags=(self.tag,))
        self.ttl = self.c.create_text(0, 0, text=self.title, font=look.F_PANEL, fill=look.ACCENT_HI, anchor="w",
                                      tags=(self.tag,))
        self.bullet = self.c.create_rectangle(0, 0, 0, 0, fill=look.GLOW, width=0, tags=(self.tag,))
        self.c.tag_lower(self.tag, "all")
        self.c.tag_raise(self.tag, self.sc.bg)

    def add(self, elem):
        self.children.append(elem)
        return elem

    def draw(self):
        from .scene import Glass
        x, y, w, h = self.x, self.y, self.w, self.h
        old = self.glass
        self.glass = Glass(x, y, w, h)
        self.glass.reveal = old.reveal if old else (1.0 if self.built else 0.0)
        lst = self.sc.glasses.setdefault(self.page, [])
        if old in lst:
            lst[lst.index(old)] = self.glass
        else:
            lst.append(self.glass)
        self.c.coords(self.outline, *look.chamfer(x, y, w, h, 14))
        self.c.coords(self.cut1, x, y + 22, x, y + 14, x + 14, y, x + 22, y)
        self.c.coords(self.cut2, x + w, y + h - 22, x + w, y + h - 14, x + w - 14, y + h, x + w - 22, y + h)
        if self.title:
            self.c.coords(self.bullet, x + 18, y + 18, x + 24, y + 24)
            self.c.coords(self.ttl, x + 32, y + 21)
        else:
            self.c.coords(self.bullet, 0, 0, 0, 0)

    def reveal(self):
        super().reveal()
        if self.glass:
            self.glass.reveal = 1.0

    def hide_for_build(self):
        super().hide_for_build()
        if self.glass:
            self.glass.reveal = 0.0

    def build(self, tl, delay, quick=False):
        """Returns (fill start, fill duration) in ms so the content can follow the print edge."""
        self.hide_for_build()
        c, x, y, w, h = self.c, self.x, self.y, self.w, self.h
        pts = look.chamfer_points(x, y, w, h, 14)
        wire_at, wire_ms = (delay, 260) if quick else (delay + 260, 560)
        fill_at, fill_ms = (delay + 140, 320) if quick else (wire_at + wire_ms - 120, 640)
        fx = (self.fx, "fx")
        st = {}

        def wire(p):
            if "wire" not in st:
                st["wire"] = c.create_line(0, 0, 0, 0, fill=look.EDGE, width=1, tags=fx)
            c.coords(st["wire"], *look.path_part(pts, p))
        tl.add(wire_at, wire_ms, wire, ease=anim.in_out_sine)

        if not quick:
            # Particles fly in and lock onto the outline right when the growing wire reaches them.
            for i in range(14):
                f = (i + random.random() * 0.6) / 14
                arrive = wire_at + wire_ms * anim.in_out_sine(f)
                tx, ty = look.point_at(pts, f)
                ang = random.uniform(0, math.tau)
                dist = random.uniform(260, 620)
                sx, sy = tx + math.cos(ang) * dist, ty + math.sin(ang) * dist
                fly = random.randint(380, 620)
                self._particle(tl, max(0, arrive - fly), fly, (sx, sy), (tx, ty))

        def fill(p):
            if not self.built:
                self.built = True
                self.sync()
                if "wire" in st:
                    c.delete(st["wire"])
                c.itemconfigure(self.ttl, text="")
                st["edge"] = [c.create_line(0, 0, 0, 0, fill=mix(look.EDGE, look.VOID, 0.6), width=7, tags=fx),
                              c.create_line(0, 0, 0, 0, fill=look.EDGE, width=2, tags=fx),
                              c.create_rectangle(0, 0, 0, 0, fill="#ffffff", width=0, tags=fx)]
                self.glass.reveal = 0.0001
            self.glass.reveal = max(0.0001, p)
            ey = y + int(h * p) // 3 * 3
            glow, line, nozzle = st["edge"]
            c.coords(glow, x + 2, ey, x + w - 2, ey)
            c.coords(line, x + 2, ey, x + w - 2, ey)
            nx = x + 10 + (w - 30) * (0.5 + 0.5 * math.sin(p * math.pi * 7))
            c.coords(nozzle, nx, ey - 2, nx + 12, ey + 2)
            c.itemconfigure(self.ttl, text=look.scramble(self.title, min(1.0, p * 2.2)))
            c.itemconfigure(self.outline, outline=mix(look.EDGE, look.WIRE, p))
            c.tag_raise(self.fx)

        def fill_done():
            c.delete(self.fx)
            self.reveal()
            c.itemconfigure(self.ttl, text=self.title)
            c.itemconfigure(self.outline, outline=look.WIRE)
        tl.add(fill_at, fill_ms, fill, ease=anim.in_out_sine, done=fill_done)
        return fill_at, fill_ms

    def _particle(self, tl, start, ms, src, dst):
        c = self.c
        st = {}
        (sx, sy), (tx, ty) = src, dst
        # Curved path: control point off to the side.
        mx, my = (sx + tx) / 2 + random.uniform(-120, 120), (sy + ty) / 2 + random.uniform(-120, 120)

        def at(t):
            u = 1 - t
            return u * u * sx + 2 * u * t * mx + t * t * tx, u * u * sy + 2 * u * t * my + t * t * ty

        def update(p):
            if "dot" not in st:
                st["dot"] = c.create_line(sx, sy, sx, sy, fill=look.GLOW, width=2, capstyle="round",
                                          tags=(self.fx, "fx"))
            q = anim.in_out_cubic(p)
            ax, ay = at(q)
            bx, by = at(max(0.0, q - 0.08))
            c.coords(st["dot"], bx, by, ax, ay)

        def snap():
            c.delete(st.get("dot"))
            ring = c.create_oval(tx, ty, tx, ty, outline="#ffffff", width=1, tags=(self.fx, "fx"))

            def grow(p):
                r = 2 + 9 * p
                c.coords(ring, tx - r, ty - r, tx + r, ty + r)
                c.itemconfigure(ring, outline=mix("#ffffff", look.VOID, p))
            tl.add(0, 260, grow, ease=anim.out_cubic, done=lambda: c.delete(ring))
        tl.add(start, ms, update, done=snap)


# ======================================================================================================
class Embed(Elem):
    """A real tk widget in a canvas window. While building, a drawn copy stands in for it; at the end the copy is
    swapped for the real widget, which looks the same."""

    def __init__(self, scene, page, widget, kind="entry"):
        super().__init__(scene, page)
        self.widget, self.kind = widget, kind
        self.win = self.c.create_window(0, 0, window=widget, anchor="nw", tags=(self.tag,))

    def draw(self):
        self.c.coords(self.win, self.x, self.y)
        self.c.itemconfigure(self.win, width=self.w, height=self.h)

    def _copy(self):
        """Draw the stand-in (temporary items)."""
        c, x, y, w, h = self.c, self.x, self.y, self.w, self.h
        tags = (self.fx, "fx")
        c.create_rectangle(x, y, x + w - 1, y + h - 1, fill=look.FIELD, outline=look.WIRE, tags=tags)
        wdg = self.widget
        try:
            if self.kind in ("entry", "combo"):
                text = wdg.get()
                if str(wdg.cget("show")) if self.kind == "entry" else "":
                    text = "•" * len(text)
                c.create_text(x + 6, y + h / 2, text=text, anchor="w", font=look.F_BODY, fill=look.FG, tags=tags)
                if self.kind == "combo":
                    c.create_text(x + w - 12, y + h / 2, text="▾", font=look.F_BODY, fill=look.FG, tags=tags)
            elif self.kind == "tree":
                c.create_rectangle(x + 1, y + 1, x + w - 2, y + 26, fill="#160f26", width=0, tags=tags)
                cols = wdg["columns"]
                cx = x + 6
                for col in cols:
                    c.create_text(cx, y + 13, text=wdg.heading(col, "text"), anchor="w",
                                  font=("Segoe UI", 10, "bold"), fill=look.ACCENT_HI, tags=tags)
                    cx += int(wdg.column(col, "width"))
                for r, iid in enumerate(wdg.get_children()[: max(0, (h - 28) // 26)]):
                    cx = x + 6
                    for col, val in zip(cols, wdg.item(iid, "values")):
                        c.create_text(cx, y + 28 + 13 + r * 26, text=str(val), anchor="w", font=look.F_BODY,
                                      fill=look.FG, tags=tags)
                        cx += int(wdg.column(col, "width"))
            elif self.kind == "text":
                txt = getattr(wdg, "copy_source", wdg)
                lines = txt.get("1.0", "end-1c").splitlines()[-max(1, (h - 8) // 17):]
                c.create_text(x + 9, y + 6, text="\n".join(lines), anchor="nw", font=txt.cget("font"),
                              fill=look.FG, width=w - 20, tags=tags)
        except tk.TclError:
            pass
        if not self.visible_page():
            c.itemconfigure(self.fx, state="hidden")

    def visible_page(self):
        return self.shown and self.sc.page_visible(self.page)

    def build(self, tl, delay, quick=False):
        self.hide_for_build()

        def show_copy():
            if not self.built:
                self._copy()
        materialize(self.sc, tl, (self.x, self.y, self.x + self.w, self.y + self.h), delay,
                    220 if quick else 380, show_copy, block=4)

    def swap(self):
        """Copy out, real widget in (same pixels, so nothing visibly changes)."""
        self.c.delete(self.fx)
        self.reveal()
