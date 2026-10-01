"""In-game HUD: a click-through panel glued to the top right of the game window.

It shows where the player is, what is still reachable right there, dungeon help, and where to go
next when nothing is left here. It only appears while the game window is in front.
"""
import ctypes
import ctypes.wintypes as wt
import os
import tkinter as tk
from collections import Counter
from pathlib import Path

from . import places, theme

user32 = ctypes.windll.user32
GWL_EXSTYLE = -20
WS_EX_LAYERED, WS_EX_TRANSPARENT = 0x00080000, 0x00000020
WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE = 0x00000080, 0x08000000
GAME_TITLES = {"soh": ("Ship of Harkinian",), "sm64": ("Super Mario 64",)}
WIDTH = 360
MAX_HERE = 7

SM64_LOCATION_FILE = Path(os.environ.get("APPDATA", Path.home())) / "sm64ex" / "aplauncher_location.txt"


def find_window(prefixes) -> int | None:
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n:
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, buf, n + 1)
                if buf.value.startswith(prefixes):
                    found.append(hwnd)
                    return False
        return True
    user32.EnumWindows(cb, 0)
    return found[0] if found else None


def client_rect(hwnd):
    r = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    pt = wt.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y, r.right, r.bottom


class LocationSource:
    """Current place of the player: SoH via Sail scene events, Mario via the file our sm64ex patch writes."""

    def __init__(self, game, sail):
        self.game, self.sail = game, sail
        self._sm64_mtime, self._sm64_course = None, None

    def current(self):
        if self.game == "soh":
            if self.sail is None or self.sail.scene is None:
                return None
            return places.oot_place(self.sail.scene)
        if self.game == "sm64":
            try:
                st = SM64_LOCATION_FILE.stat()
                if st.st_mtime != self._sm64_mtime:
                    self._sm64_mtime = st.st_mtime
                    parts = SM64_LOCATION_FILE.read_text().split()
                    self._sm64_course = int(parts[1])
            except (OSError, ValueError, IndexError):
                return None
            return places.sm64_place(self._sm64_course) if self._sm64_course is not None else None
        return None


def guidance(snapshot, place):
    """Text pieces for the current place: (title, here-list, tips, next-hint)."""
    locs = (snapshot or {}).get("in_logic", [])
    if place is None:
        title, here, tips = "📍 Ort unbekannt", [], []
    else:
        name, prefixes, tips, _ = place
        title = f"📍 {name}"
        here = [l for l in locs if places.matches(l, prefixes)] if prefixes else []
    here.sort(key=lambda l: (not l.get("hinted"), l["name"]))
    nxt = ""
    if not here and locs:
        top = Counter(places.place_name(l) for l in locs).most_common(3)
        nxt = "Hier ist nichts mehr erreichbar. Nächste Ziele: " + ", ".join(f"{n} ({c})" for n, c in top)
    elif not locs and snapshot and snapshot.get("status") == "ok":
        nxt = "Gerade nichts erreichbar – du brauchst erst neue Items."
    return title, here, tips, nxt


class GameHud:
    def __init__(self, root, game, location: LocationSource, get_snapshot):
        self.game, self.location, self.get_snapshot = game, location, get_snapshot
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.88)
        self.win.configure(bg=theme.BG, highlightthickness=1, highlightbackground=theme.ACCENT)
        self.win.withdraw()
        self.frame = tk.Frame(self.win, bg=theme.BG, padx=12, pady=8)
        self.frame.pack(fill="both", expand=True)
        self.l_title = tk.Label(self.frame, bg=theme.BG, fg=theme.ACCENT_HI, font=("Segoe UI Semibold", 12),
                                anchor="w", justify="left")
        self.l_title.pack(fill="x")
        self.l_goal = tk.Label(self.frame, bg=theme.BG, fg=theme.MUTED, font=("Segoe UI", 9), anchor="w",
                               justify="left", wraplength=WIDTH - 24)
        self.l_goal.pack(fill="x")
        self.l_here = tk.Label(self.frame, bg=theme.BG, fg=theme.FG, font=("Segoe UI", 10), anchor="w",
                               justify="left", wraplength=WIDTH - 24)
        self.l_here.pack(fill="x", pady=(6, 0))
        self.l_tips = tk.Label(self.frame, bg=theme.BG, fg=theme.WARN, font=("Segoe UI", 9), anchor="w",
                               justify="left", wraplength=WIDTH - 24)
        self.l_tips.pack(fill="x", pady=(6, 0))
        self.styled = False
        self.last_key = None
        self.enabled = True
        self.job = self.win.after(500, self._tick)

    def _click_through(self):
        hwnd = user32.GetParent(self.win.winfo_id()) or self.win.winfo_id()
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                              style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
        self.styled = True

    def set_enabled(self, on):
        self.enabled = on
        if not on:
            self.win.withdraw()

    def destroy(self):
        if self.job:
            self.win.after_cancel(self.job)
        self.win.destroy()

    def _tick(self):
        self.job = self.win.after(400, self._tick)
        hwnd = find_window(GAME_TITLES.get(self.game, ("\0",))) if self.enabled else None
        if not hwnd or user32.IsIconic(hwnd) or user32.GetForegroundWindow() != hwnd:
            if self.win.state() != "withdrawn":
                self.win.withdraw()
            return
        snap = self.get_snapshot()
        place = self.location.current()
        key = (snap.get("ts") if snap else None, place[0] if place else None)
        if key != self.last_key:
            self.last_key = key
            self._render(snap, place)
        x, y, w, h = client_rect(hwnd)
        self.win.update_idletasks()
        height = self.win.winfo_reqheight()
        # Right edge, below the in-game button display (OoT's A/B/C icons sit in the top right corner).
        top = y + int(h * 0.22)
        self.win.geometry(f"{WIDTH}x{height}+{x + max(0, w - WIDTH - 14)}+{top}")
        if self.win.state() == "withdrawn":
            self.win.deiconify()
            if not self.styled:
                self.win.update_idletasks()
                self._click_through()
        self.win.lift()  # stay above the (also topmost) overlay window

    def _render(self, snap, place):
        title, here, tips, nxt = guidance(snap, place)
        self.l_title.configure(text=title)
        goal = ""
        if snap and snap.get("status") == "ok":
            from . import goals
            open_steps = [s for s in goals.steps_for(snap) if not s.done]
            if snap.get("beaten"):
                goal = "✅ Go-Mode – du kannst dein Ziel erreichen!"
            elif open_steps:
                s = open_steps[0]
                prog = f" {min(s.have, s.need)}/{s.need}" if s.have is not None and s.need else ""
                goal = f"🎯 {s.label}{prog}"
        self.l_goal.configure(text=goal)
        if here:
            lines = [("★ " if l.get("hinted") else "• ") + l["name"] for l in here[:MAX_HERE]]
            if len(here) > MAX_HERE:
                lines.append(f"… und {len(here) - MAX_HERE} weitere")
            self.l_here.configure(text=f"Hier erreichbar ({len(here)}):\n" + "\n".join(lines), fg=theme.FG)
        else:
            self.l_here.configure(text=nxt or "Warte auf Daten …", fg=theme.MUTED)
        self.l_tips.configure(text="\n".join("💡 " + t for t in tips))
        if tips:
            self.l_tips.pack(fill="x", pady=(6, 0))
        else:
            self.l_tips.pack_forget()
