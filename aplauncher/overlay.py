"""Always-on-top overlay: goal progress, what is reachable now, recently received items.

The logic comes from the bridge (Universal Tracker inside Archipelago), which writes a JSON
snapshot that this window polls.
"""
import json
import os
import subprocess
import tkinter as tk
from collections import defaultdict
from pathlib import Path
from tkinter import ttk

from . import goals, theme
from .config import Paths

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
POLL_MS = 1000


class Overlay:
    def __init__(self, root: tk.Tk, paths: Paths, address: str, slot: str, password: str, yaml_dir: Path | None,
                 on_close=None):
        self.paths, self.slot = paths, slot
        self.on_close = on_close
        self.out = paths.root / "overlay" / f"state_{slot}.json"
        self.out.parent.mkdir(parents=True, exist_ok=True)
        self.out.unlink(missing_ok=True)
        self.last_ts = None
        self.open_regions: set[str] = set()
        self.proc = self._start_bridge(address, slot, password, yaml_dir)

        self.win = tk.Toplevel(root)
        self.win.title(f"Overlay – {slot}")
        self.win.configure(bg=theme.BG)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.97)
        w, h = 400, 640
        self.win.geometry(f"{w}x{h}+{self.win.winfo_screenwidth() - w - 30}+60")
        self.win.minsize(320, 360)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        theme.dark_titlebar(self.win)
        self._build()
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
        self.win.destroy()
        if self.on_close:
            self.on_close()

    # ----- layout -----
    def _build(self):
        top = ttk.Frame(self.win, padding=8)
        top.pack(fill="both", expand=True)

        head = ttk.Frame(top)
        head.pack(fill="x")
        self.l_title = ttk.Label(head, text=self.slot, style="State.TLabel")
        self.l_title.pack(side="left")
        self.v_top = tk.BooleanVar(value=True)
        ttk.Checkbutton(head, text="Immer oben", variable=self.v_top,
                        command=lambda: self.win.attributes("-topmost", self.v_top.get())).pack(side="right")
        self.l_status = ttk.Label(top, text="Starte Logik-Tracker ...", style="Muted.TLabel", wraplength=370)
        self.l_status.pack(fill="x", pady=(2, 6))

        gf = ttk.LabelFrame(top, text="🎯 Ziel", padding=6)
        gf.pack(fill="x")
        self.goal_frame = ttk.Frame(gf)
        self.goal_frame.pack(fill="x")

        nf = ttk.LabelFrame(top, text="📍 Jetzt erreichbar", padding=4)
        nf.pack(fill="both", expand=True, pady=(8, 0))
        self.tree = ttk.Treeview(nf, show="tree", selectmode="none")
        sb = ttk.Scrollbar(nf, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("region", font=("Segoe UI", 10, "bold"), foreground=theme.FG)
        self.tree.tag_configure("hint", foreground=theme.WARN)
        self.tree.tag_configure("loc", foreground=theme.MUTED)
        self.tree.bind("<<TreeviewOpen>>", lambda e: self._remember_open(True))
        self.tree.bind("<<TreeviewClose>>", lambda e: self._remember_open(False))

        rf = ttk.LabelFrame(top, text="📦 Zuletzt erhalten", padding=4)
        rf.pack(fill="x", pady=(8, 0))
        self.recv = tk.Text(rf, height=5, wrap="none", state="disabled", font=("Segoe UI", 9))
        theme.style_text(self.recv)
        self.recv.pack(fill="x")

        self.l_foot = ttk.Label(top, text="", style="Muted.TLabel")
        self.l_foot.pack(fill="x", pady=(6, 0))

    def _remember_open(self, opened):
        item = self.tree.focus()
        region = self.tree.item(item, "text").split("  (")[0] if item else None
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
        if snap and snap.get("ts") != self.last_ts:
            self.last_ts = snap.get("ts")
            self._render(snap)
        if self.proc.poll() is not None and (not snap or snap.get("status") != "error"):
            self.l_status.configure(text="Logik-Tracker wurde beendet. Overlay schließen und neu öffnen.",
                                    foreground=theme.ERR)
        self.win.after(POLL_MS, self._poll)

    def _render(self, snap):
        status = snap.get("status")
        if status == "starting":
            self.l_status.configure(text="Berechne Spiellogik ...", foreground=theme.MUTED)
            return
        if status == "error":
            err = (snap.get("error") or "").strip().splitlines()
            self.l_status.configure(text="Fehler im Logik-Tracker: " + (err[-1] if err else "?"), foreground=theme.ERR)
            return
        self.l_title.configure(text=f"{snap.get('slot_name', self.slot)} – {snap.get('game', '')}")
        if snap.get("beaten"):
            self.l_status.configure(text="✅ Go-Mode: Du kannst dein Ziel jetzt erreichen!", foreground=theme.OK)
        else:
            self.l_status.configure(text="Live – aktualisiert sich bei jedem Fund.", foreground=theme.MUTED)
        self._render_goals(goals.steps_for(snap))
        self._render_reachable(snap.get("in_logic", []))
        self._render_received(snap.get("received", []))
        extra = f" · {snap['glitched']} nur mit Tricks" if snap.get("glitched") else ""
        self.l_foot.configure(text=f"Gefunden {snap.get('checked', 0)}/{snap.get('total', 0)} · "
                                   f"erreichbar {len(snap.get('in_logic', []))}{extra}")

    def _render_goals(self, steps):
        for w in self.goal_frame.winfo_children():
            w.destroy()
        for s in steps:
            row = ttk.Frame(self.goal_frame)
            row.pack(fill="x", pady=1)
            mark = "✓" if s.done else "•"
            color = theme.OK if s.done else theme.FG
            tk.Label(row, text=f"{mark} {s.label}", bg=theme.BG, fg=color, anchor="w",
                     font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True)
            if s.need is not None and s.have is not None:
                tk.Label(row, text=f"{min(s.have, s.need)}/{s.need}", bg=theme.BG,
                         fg=theme.OK if s.done else theme.ACCENT_HI, font=("Segoe UI", 10, "bold")).pack(side="right")
            elif s.need is not None:
                tk.Label(row, text=f"?/{s.need}", bg=theme.BG, fg=theme.MUTED).pack(side="right")
            if s.need and s.have is not None and not s.done:
                bar = ttk.Progressbar(self.goal_frame, maximum=s.need, value=min(s.have, s.need))
                bar.pack(fill="x", padx=(14, 0))
            if s.hint and not s.done:
                tk.Label(self.goal_frame, text=s.hint, bg=theme.BG, fg=theme.MUTED, anchor="w", justify="left",
                         wraplength=350, font=("Segoe UI", 9)).pack(fill="x", padx=(14, 0))

    def _render_reachable(self, locs):
        by_region = defaultdict(list)
        for l in locs:
            by_region[l.get("region") or "Sonstiges"].append(l)
        # Regions with hinted spots first, then the ones with the most checks.
        order = sorted(by_region.items(), key=lambda kv: (-any(l["hinted"] for l in kv[1]), -len(kv[1]), kv[0]))
        y = self.tree.yview()[0]
        self.tree.delete(*self.tree.get_children())
        if not order:
            self.tree.insert("", "end", text="Nichts erreichbar – du brauchst erst neue Items.", tags=("loc",))
        for region, items in order:
            star = "★ " if any(l["hinted"] for l in items) else ""
            parent = self.tree.insert("", "end", text=f"{star}{region}  ({len(items)})", tags=("region",),
                                      open=region in self.open_regions)
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
