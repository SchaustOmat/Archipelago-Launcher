"""Overlay window: where you are, what is reachable there, goal progress, everything reachable, recent items.

The logic comes from the bridge (Universal Tracker inside Archipelago), which writes a JSON snapshot
that this window polls. It also drives the click-through in-game HUD (hud.py).
"""
import json
import os
import subprocess
import tkinter as tk
from collections import defaultdict
from pathlib import Path
from tkinter import ttk

from . import goals, hud, places, theme, widgets
from .config import Paths

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
POLL_MS = 1000


class Overlay:
    def __init__(self, root: tk.Tk, paths: Paths, address: str, slot: str, password: str, yaml_dir: Path | None,
                 game: str, sail=None, on_close=None):
        self.paths, self.slot, self.game = paths, slot, game
        self.on_close = on_close
        self.out = paths.root / "overlay" / f"state_{slot}.json"
        self.out.parent.mkdir(parents=True, exist_ok=True)
        self.out.unlink(missing_ok=True)
        self.last_ts = None
        self.snapshot: dict = {}
        self.open_regions: set[str] = set()
        self.location = hud.LocationSource(game, sail)
        self.last_place = None
        self.proc = self._start_bridge(address, slot, password, yaml_dir)

        self.win = tk.Toplevel(root)
        self.win.title(f"Overlay – {slot}")
        self.win.configure(bg=theme.BG)
        self.win.attributes("-topmost", True)
        w, h = 420, 720
        self.win.geometry(f"{w}x{h}+{self.win.winfo_screenwidth() - w - 30}+50")
        self.win.minsize(340, 420)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        theme.dark_titlebar(self.win)
        self._build()
        widgets.fade_in(self.win, 200)
        self.hud = hud.GameHud(root, game, self.location, lambda: self.snapshot)
        self.win.after(300, self._poll)

    # ----- bridge process -----
    def _start_bridge(self, address, slot, password, yaml_dir):
        args = [str(self.paths.ap / "ArchipelagoLauncher.exe"), "APLauncher Bridge", "--",
                "--connect", address, "--name", slot, "--out", str(self.out), "--parent-pid", str(os.getpid())]
        if password:
            args += ["--password", password]
        if yaml_dir:
            args += ["--yaml-dir", str(yaml_dir)]
        return subprocess.Popen(args, cwd=self.paths.ap, creationflags=NO_WINDOW)

    def close(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
        self.hud.destroy()
        self.win.destroy()
        if self.on_close:
            self.on_close()

    # ----- layout -----
    def _card(self, parent, title, expand=False):
        outer = tk.Frame(parent, bg=theme.PANEL, highlightthickness=1, highlightbackground=theme.BORDER)
        outer.pack(fill="both" if expand else "x", expand=expand, pady=(0, 8))
        inner = tk.Frame(outer, bg=theme.PANEL, padx=10, pady=8)
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text=title, bg=theme.PANEL, fg=theme.ACCENT_HI, font=("Segoe UI Semibold", 10),
                 anchor="w").pack(fill="x")
        return inner

    def _build(self):
        top = tk.Frame(self.win, bg=theme.BG, padx=10, pady=8)
        top.pack(fill="both", expand=True)

        head = tk.Frame(top, bg=theme.BG)
        head.pack(fill="x", pady=(0, 6))
        self.l_title = tk.Label(head, text=self.slot, bg=theme.BG, fg=theme.FG, font=("Segoe UI Semibold", 13),
                                anchor="w")
        self.l_title.pack(side="left")
        self.pill = widgets.StatusPill(head)
        self.pill.pack(side="right")
        self.pill.set("busy", "Berechne …")

        opts = tk.Frame(top, bg=theme.BG)
        opts.pack(fill="x", pady=(0, 6))
        self.v_top = tk.BooleanVar(value=True)
        self.v_hud = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Immer oben", variable=self.v_top,
                        command=lambda: self.win.attributes("-topmost", self.v_top.get())).pack(side="left")
        ttk.Checkbutton(opts, text="HUD im Spiel", variable=self.v_hud,
                        command=lambda: self.hud.set_enabled(self.v_hud.get())).pack(side="left", padx=12)
        self.l_status = tk.Label(top, text="", bg=theme.BG, fg=theme.MUTED, font=("Segoe UI", 9), anchor="w",
                                 justify="left", wraplength=390)
        self.l_status.pack(fill="x")

        here = self._card(top, "📍 Hier")
        self.l_place = tk.Label(here, text="Ort unbekannt – Spiel starten", bg=theme.PANEL, fg=theme.FG,
                                font=("Segoe UI Semibold", 11), anchor="w")
        self.l_place.pack(fill="x")
        self.l_here = tk.Label(here, text="", bg=theme.PANEL, fg=theme.FG, font=("Segoe UI", 9), anchor="w",
                               justify="left", wraplength=380)
        self.l_here.pack(fill="x", pady=(4, 0))
        self.l_tips = tk.Label(here, text="", bg=theme.PANEL, fg=theme.WARN, font=("Segoe UI", 9), anchor="w",
                               justify="left", wraplength=380)
        self.l_tips.pack(fill="x", pady=(4, 0))

        gf = self._card(top, "🎯 Ziel")
        self.goal_frame = tk.Frame(gf, bg=theme.PANEL)
        self.goal_frame.pack(fill="x")

        nf = self._card(top, "🧭 Alles Erreichbare", expand=True)
        box = tk.Frame(nf, bg=theme.PANEL)
        box.pack(fill="both", expand=True, pady=(4, 0))
        self.tree = ttk.Treeview(box, show="tree", selectmode="none")
        sb = ttk.Scrollbar(box, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("region", font=("Segoe UI Semibold", 10), foreground=theme.FG)
        self.tree.tag_configure("current", font=("Segoe UI Semibold", 10), foreground=theme.OK)
        self.tree.tag_configure("hint", foreground=theme.WARN)
        self.tree.tag_configure("loc", foreground=theme.MUTED)
        self.tree.bind("<<TreeviewOpen>>", lambda e: self._remember_open(True))
        self.tree.bind("<<TreeviewClose>>", lambda e: self._remember_open(False))

        rf = self._card(top, "📦 Zuletzt erhalten")
        self.recv = tk.Text(rf, height=4, wrap="none", state="disabled", font=("Segoe UI", 9))
        theme.style_text(self.recv)
        self.recv.pack(fill="x", pady=(4, 0))

        self.l_foot = tk.Label(top, text="", bg=theme.BG, fg=theme.MUTED, font=("Segoe UI", 9), anchor="w")
        self.l_foot.pack(fill="x")

    def _remember_open(self, opened):
        item = self.tree.focus()
        region = self.tree.item(item, "text").split("  (")[0].lstrip("★📍 ") if item else None
        if region:
            (self.open_regions.add if opened else self.open_regions.discard)(region)

    # ----- data -----
    def _poll(self):
        if not self.win.winfo_exists():
            return
        try:
            snap = json.loads(self.out.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            snap = None
        place = self.location.current()
        place_key = place[0] if place else None
        if snap and snap.get("ts") != self.last_ts:
            self.last_ts = snap.get("ts")
            if snap.get("status") == "ok":
                self.snapshot = snap
            self._render(snap, place)
        elif place_key != self.last_place and self.snapshot:
            self._render(self.snapshot, place)
        self.last_place = place_key
        if self.proc.poll() is not None and (not snap or snap.get("status") != "error"):
            self.pill.set("error", "Tracker aus")
            self.l_status.configure(text="Logik-Tracker wurde beendet. Overlay schließen und neu öffnen.",
                                    fg=theme.ERR)
        self.win.after(POLL_MS, self._poll)

    def _render(self, snap, place):
        status = snap.get("status")
        if status == "starting":
            self.pill.set("busy", "Berechne …")
            return
        if status == "error":
            err = (snap.get("error") or "").strip().splitlines()
            self.pill.set("error", "Fehler")
            self.l_status.configure(text="Fehler im Logik-Tracker: " + (err[-1] if err else "?"), fg=theme.ERR)
            return
        self.l_title.configure(text=f"{snap.get('slot_name', self.slot)}")
        if snap.get("beaten"):
            self.pill.set("connected", "Go-Mode!")
            self.l_status.configure(text="✅ Du kannst dein Ziel jetzt erreichen!", fg=theme.OK)
        else:
            self.pill.set("connected", "Live")
            self.l_status.configure(text=snap.get("game", ""), fg=theme.MUTED)
        self._render_here(snap, place)
        self._render_goals(goals.steps_for(snap))
        self._render_reachable(snap.get("in_logic", []), place)
        self._render_received(snap.get("received", []))
        extra = f" · {snap['glitched']} nur mit Tricks" if snap.get("glitched") else ""
        self.l_foot.configure(text=f"Gefunden {snap.get('checked', 0)}/{snap.get('total', 0)} · "
                                   f"erreichbar {len(snap.get('in_logic', []))}{extra}")

    def _render_here(self, snap, place):
        title, here, tips, nxt = hud.guidance(snap, place)
        self.l_place.configure(text=title.replace("📍 ", "") if place else "Ort unbekannt – Spiel starten")
        if here:
            lines = [("★ " if l.get("hinted") else "• ") + l["name"] for l in here[:10]]
            if len(here) > 10:
                lines.append(f"… und {len(here) - 10} weitere")
            self.l_here.configure(text="\n".join(lines), fg=theme.FG)
        else:
            self.l_here.configure(text=nxt, fg=theme.MUTED)
        self.l_tips.configure(text="\n".join("💡 " + t for t in tips))

    def _render_goals(self, steps):
        for w in self.goal_frame.winfo_children():
            w.destroy()
        for s in steps:
            row = tk.Frame(self.goal_frame, bg=theme.PANEL)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=("✓ " if s.done else "• ") + s.label, bg=theme.PANEL,
                     fg=theme.OK if s.done else theme.FG, anchor="w", font=("Segoe UI", 10)).pack(
                side="left", fill="x", expand=True)
            if s.need is not None and s.have is not None:
                tk.Label(row, text=f"{min(s.have, s.need)}/{s.need}", bg=theme.PANEL,
                         fg=theme.OK if s.done else theme.ACCENT_HI, font=("Segoe UI Semibold", 10)).pack(side="right")
            elif s.need is not None:
                tk.Label(row, text=f"?/{s.need}", bg=theme.PANEL, fg=theme.MUTED).pack(side="right")
            if s.need and s.have is not None and not s.done:
                ttk.Progressbar(self.goal_frame, maximum=s.need, value=min(s.have, s.need),
                                style="Thin.Horizontal.TProgressbar").pack(fill="x", padx=(14, 0), pady=(0, 2))
            if s.hint and not s.done:
                tk.Label(self.goal_frame, text=s.hint, bg=theme.PANEL, fg=theme.MUTED, anchor="w", justify="left",
                         wraplength=360, font=("Segoe UI", 9)).pack(fill="x", padx=(14, 0))

    def _render_reachable(self, locs, place):
        groups = defaultdict(list)
        for l in locs:
            groups[places.place_name(l)].append(l)
        current = place[0] if place else None
        # Where you are first, then places with hinted spots, then the ones with the most checks.
        order = sorted(groups.items(), key=lambda kv: (kv[0] != current, not any(l["hinted"] for l in kv[1]),
                                                       -len(kv[1]), kv[0]))
        y = self.tree.yview()[0]
        self.tree.delete(*self.tree.get_children())
        if not order:
            self.tree.insert("", "end", text="Nichts erreichbar – du brauchst erst neue Items.", tags=("loc",))
        for name, items in order:
            is_here = name == current
            mark = "📍 " if is_here else ("★ " if any(l["hinted"] for l in items) else "")
            parent = self.tree.insert("", "end", text=f"{mark}{name}  ({len(items)})",
                                      tags=("current" if is_here else "region",),
                                      open=name in self.open_regions or is_here)
            for l in sorted(items, key=lambda l: (not l["hinted"], l["name"])):
                self.tree.insert(parent, "end", text=("★ " if l["hinted"] else "   ") + l["name"],
                                 tags=("hint" if l["hinted"] else "loc",))
        self.tree.yview_moveto(y)

    def _render_received(self, received):
        self.recv.configure(state="normal")
        self.recv.delete("1.0", "end")
        for r in reversed(received[-6:]):
            src = "" if r["from"] == self.slot else f"  ← {r['from']}"
            self.recv.insert("end", f"{r['item']}{src}\n")
        self.recv.configure(state="disabled")
