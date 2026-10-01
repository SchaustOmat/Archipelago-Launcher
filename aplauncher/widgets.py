"""Animated widgets for the launcher: rounded buttons, status pill, tab bar, game cards, toasts."""
import math
import tkinter as tk
import tkinter.font as tkfont

from . import theme

FRAME_MS = 16


def lerp_color(a: str, b: str, t: float) -> str:
    a, b = a.lstrip("#"), b.lstrip("#")
    ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


def ease(t: float) -> float:
    return 1 - (1 - t) ** 3


def rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
           x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


class Tween:
    """Animates a colour from its current value to a target over a few frames."""

    def __init__(self, widget, setter, start: str):
        self.widget, self.setter, self.value = widget, setter, start
        self.job = None

    def to(self, target: str, ms=140):
        if self.job:
            self.widget.after_cancel(self.job)
        start, steps = self.value, max(1, ms // FRAME_MS)

        def step(i=1):
            self.value = lerp_color(start, target, ease(i / steps))
            self.setter(self.value)
            self.job = self.widget.after(FRAME_MS, step, i + 1) if i < steps else None
        step()


class RoundButton(tk.Canvas):
    KINDS = {  # base, hover, text
        "primary": (theme.ACCENT, theme.ACCENT_HI, "#ffffff"),
        "secondary": (theme.BUTTON, theme.BUTTON_HI, theme.FG),
        "danger": ("#4a1d3a", "#6e2a52", "#ffd2e1"),
        "ghost": (theme.PANEL, theme.BUTTON, theme.FG),
    }

    def __init__(self, master, text, command=None, kind="secondary", bg=theme.PANEL, height=36, padx=18,
                 size=10, width=None):
        self.font = tkfont.Font(family="Segoe UI Semibold", size=size)
        self.text, self.command, self.kind, self.enabled = text, command, kind, True
        self.padx, self.fixed_width = padx, width
        super().__init__(master, height=height, width=self._width(), bg=bg, highlightthickness=0, bd=0,
                         cursor="hand2")
        base = self.KINDS[kind][0]
        self.tween = Tween(self, self._paint, base)
        self.hover = False
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Configure>", lambda e: self._paint(self.tween.value))
        self._paint(base)

    def _width(self):
        return self.fixed_width or self.font.measure(self.text) + 2 * self.padx

    def _paint(self, fill):
        self.delete("all")
        w, h = int(self.cget("width")), int(self.cget("height"))
        rounded_rect(self, 1, 1, w - 1, h - 1, 10, fill=fill, outline="")
        fg = self.KINDS[self.kind][2] if self.enabled else theme.DISABLED
        self.create_text(w / 2, h / 2, text=self.text, fill=fg, font=self.font)

    def _target(self):
        base, hover, _ = self.KINDS[self.kind]
        if not self.enabled:
            return theme.PANEL if self.kind != "ghost" else theme.PANEL
        return hover if self.hover else base

    def _set_hover(self, on):
        self.hover = on
        self.tween.to(self._target())

    def _press(self, _):
        if self.enabled:
            self.tween.to(lerp_color(self.KINDS[self.kind][0], "#000000", 0.25), ms=60)

    def _release(self, e):
        if not self.enabled:
            return
        self.tween.to(self._target(), ms=120)
        if 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height() and self.command:
            self.command()

    def configure(self, cnf=None, **kw):
        changed = False
        if "state" in kw:
            self.enabled = kw.pop("state") != "disabled"
            super().configure(cursor="hand2" if self.enabled else "arrow")
            changed = True
        if "text" in kw:
            self.text = kw.pop("text")
            super().configure(width=self._width())
            changed = True
        if "command" in kw:
            self.command = kw.pop("command")
        if cnf or kw:
            super().configure(cnf, **kw)
        if changed:
            self.tween.to(self._target(), ms=100)
            self._paint(self.tween.value)

    config = configure


class StatusPill(tk.Canvas):
    STATES = {  # dot colour, pulses
        "offline": (theme.MUTED, False),
        "busy": (theme.WARN, True),
        "lobby": (theme.WARN, True),
        "connected": (theme.OK, True),
        "error": (theme.ERR, False),
    }

    def __init__(self, master, bg=theme.BG):
        self.font = tkfont.Font(family="Segoe UI Semibold", size=10)
        super().__init__(master, height=32, width=160, bg=bg, highlightthickness=0, bd=0)
        self.state, self.text, self.phase = "offline", "Offline", 0.0
        self._draw()
        self._pulse()

    def set(self, state, text):
        if (state, text) != (self.state, self.text):
            self.state, self.text = state, text
            self.configure(width=self.font.measure(text) + 48)
            self._draw()

    def _draw(self):
        self.delete("all")
        w, h = int(self.cget("width")), int(self.cget("height"))
        rounded_rect(self, 1, 1, w - 1, h - 1, 15, fill=theme.PANEL, outline=theme.BORDER)
        color, pulses = self.STATES.get(self.state, self.STATES["offline"])
        if pulses:
            glow = 0.5 + 0.5 * math.sin(self.phase)
            r = 7 + 3 * glow
            self.create_oval(18 - r, h / 2 - r, 18 + r, h / 2 + r, outline="",
                             fill=lerp_color(theme.PANEL, color, 0.35 * (1 - glow) + 0.1))
        self.create_oval(13, h / 2 - 5, 23, h / 2 + 5, fill=color, outline="")
        self.create_text(32, h / 2, text=self.text, anchor="w", fill=theme.FG, font=self.font)

    def _pulse(self):
        if self.STATES.get(self.state, (None, False))[1]:
            self.phase += 0.12
            self._draw()
        self.after(40, self._pulse)


class TabBar(tk.Canvas):
    """Text tabs with an underline that glides to the selected tab."""

    def __init__(self, master, tabs, on_select, bg=theme.BG):
        self.font = tkfont.Font(family="Segoe UI Semibold", size=11)
        super().__init__(master, height=42, bg=bg, highlightthickness=0, bd=0)
        self.tabs, self.on_select = tabs, on_select
        self.items, self.boxes = {}, {}
        x = 4
        for key, label in tabs:
            item = self.create_text(x + 14, 20, text=label, anchor="w", font=self.font, fill=theme.MUTED,
                                    tags=("tab", key))
            x1, _, x2, _ = self.bbox(item)
            self.items[key], self.boxes[key] = item, (x1 - 14, x2 + 14)
            self.tag_bind(key, "<Button-1>", lambda e, k=key: self.select(k))
            self.tag_bind(key, "<Enter>", lambda e, k=key: self._hover(k, True))
            self.tag_bind(key, "<Leave>", lambda e, k=key: self._hover(k, False))
            x = x2 + 14
        self.create_line(0, 41, 4000, 41, fill=theme.BORDER)
        self.bar = self.create_rectangle(0, 37, 0, 40, fill=theme.ACCENT, outline="")
        self.current, self.job = None, None
        self.configure(cursor="hand2")

    def _hover(self, key, on):
        if key != self.current:
            self.itemconfigure(self.items[key], fill=theme.FG if on else theme.MUTED)

    def select(self, key, animate=True):
        if self.current == key:
            return
        for k, item in self.items.items():
            self.itemconfigure(item, fill=theme.FG if k == key else theme.MUTED)
        x1, x2 = self.boxes[key]
        if self.job:
            self.after_cancel(self.job)
        sx1, _, sx2, _ = self.coords(self.bar)
        steps = 12 if animate and self.current else 1

        def step(i=1):
            t = ease(i / steps)
            self.coords(self.bar, sx1 + (x1 + 8 - sx1) * t, 37, sx2 + (x2 - 8 - sx2) * t, 40)
            self.job = self.after(FRAME_MS, step, i + 1) if i < steps else None
        step()
        self.current = key
        self.on_select(key)


class GameCard(tk.Frame):
    """Selectable card with icon, title and subtitle."""

    def __init__(self, master, icon, title, subtitle, on_click):
        super().__init__(master, bg=theme.FIELD, highlightthickness=2, highlightbackground=theme.BORDER,
                         cursor="hand2", padx=14, pady=10)
        self.selected = False
        self.labels = [
            tk.Label(self, text=icon, bg=theme.FIELD, fg=theme.FG, font=("Segoe UI Emoji", 20)),
            tk.Label(self, text=title, bg=theme.FIELD, fg=theme.FG, font=("Segoe UI Semibold", 11)),
            tk.Label(self, text=subtitle, bg=theme.FIELD, fg=theme.MUTED, font=("Segoe UI", 9)),
        ]
        for lbl in self.labels:
            lbl.pack(anchor="w")
        self.tween = Tween(self, self._paint, theme.FIELD)
        for w in (self, *self.labels):
            w.bind("<Button-1>", lambda e: on_click())
            w.bind("<Enter>", lambda e: self.tween.to(theme.BUTTON if not self.selected else theme.BUTTON_HI))
            w.bind("<Leave>", lambda e: self.tween.to(self._base()))

    def _base(self):
        return theme.BUTTON if self.selected else theme.FIELD

    def _paint(self, color):
        self.configure(bg=color)
        for lbl in self.labels:
            lbl.configure(bg=color)

    def set_selected(self, on):
        self.selected = on
        self.configure(highlightbackground=theme.ACCENT if on else theme.BORDER)
        self.tween.to(self._base())


class Toast:
    """Small message that slides in at the bottom of the window and disappears again."""

    def __init__(self, root):
        self.root = root
        self.label = None

    def show(self, text, color=theme.OK, ms=2200):
        if self.label:
            self.label.destroy()
        lbl = tk.Label(self.root, text=text, bg=theme.BUTTON, fg=color, font=("Segoe UI Semibold", 10),
                       padx=16, pady=8, highlightthickness=1, highlightbackground=theme.ACCENT)
        self.label = lbl
        steps = 12

        def slide(i, start, end, after=None):
            if not lbl.winfo_exists():
                return
            y = start + (end - start) * ease(i / steps)
            lbl.place(relx=0.5, rely=1.0, y=y, anchor="s")
            if i < steps:
                self.root.after(FRAME_MS, slide, i + 1, start, end, after)
            elif after:
                after()

        def leave():
            self.root.after(ms, slide, 1, -46, 60, lbl.destroy)
        slide(1, 60, -46, leave)


def fade_in(win, ms=260):
    steps = max(1, ms // FRAME_MS)
    try:
        win.attributes("-alpha", 0.0)
    except tk.TclError:
        return

    def step(i=1):
        win.attributes("-alpha", ease(i / steps))
        if i < steps:
            win.after(FRAME_MS, step, i + 1)
    win.after(30, step)
