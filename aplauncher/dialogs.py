"""Small modal windows of the launcher: resume a multiworld, hints, statistics, save backups."""
import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from . import backup, host, stats, theme, widgets


def modal(root, title, w, h) -> tk.Toplevel:
    """Dark window centred over the launcher. Tied to it, so it can never end up hidden behind it."""
    win = tk.Toplevel(root)
    win.title(title)
    win.configure(bg=theme.BG)
    win.transient(root)
    root.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() - w) // 2
    y = root.winfo_rooty() + (root.winfo_height() - h) // 3
    win.geometry(f"{w}x{h}+{x}+{y}")
    theme.dark_titlebar(win)
    win.bind("<Escape>", lambda e: win.destroy())
    widgets.fade_in(win, 180)
    return win


def _heading(win, title, sub=""):
    tk.Label(win, text=title, bg=theme.BG, fg=theme.FG, font=("Segoe UI Semibold", 11)).pack(anchor="w", padx=14,
                                                                                              pady=(12, 0))
    if sub:
        tk.Label(win, text=sub, bg=theme.BG, fg=theme.MUTED, font=("Segoe UI", 9), justify="left").pack(anchor="w",
                                                                                                         padx=14)


def _listbox(win, rows):
    lb = tk.Listbox(win, font=("Segoe UI", 11), activestyle="none", exportselection=False)
    theme.style_text(lb)
    lb.pack(fill="both", expand=True, padx=14, pady=10)
    for r in rows:
        lb.insert("end", "  " + r)
    if rows:
        lb.selection_set(0)
        lb.activate(0)
    return lb


def _session_row(zip_path) -> str:
    played = datetime.fromtimestamp(host.last_played(zip_path))
    stamp = zip_path.parent.name  # created: YYYY-MM-DD_HH-MM-SS
    created = f"{stamp[8:10]}.{stamp[5:7]}." if len(stamp) >= 10 else "?"
    return (f"{played.strftime('%d.%m.%Y  %H:%M')}    –    {', '.join(host.session_players(zip_path))}"
            f"    (erstellt {created})")


def pick_session(root, sessions, on_pick):
    """List of saved multiworlds, last played first; on_pick(zip_path) for the chosen one."""
    win = modal(root, "Spielstand fortsetzen", 680, 340)
    _heading(win, "Welche Multiworld möchtest du fortsetzen?",
             "Sortiert nach „zuletzt gespielt“. Doppelklick oder Enter startet den Server mit diesem Spielstand.")
    lb = _listbox(win, [_session_row(z) for z in sessions])

    def go():
        sel = lb.curselection()
        if sel:
            win.destroy()
            on_pick(sessions[sel[0]])
    widgets.RoundButton(win, "▶  Diesen Spielstand starten", go, "primary", bg=theme.BG).pack(pady=(0, 12))
    lb.bind("<Double-Button-1>", lambda e: go())
    win.bind("<Return>", lambda e: go())
    win.lift()
    win.grab_set()
    lb.focus_set()


class HintDialog:
    """Pick one of your own game's items and ask the server where it is (!hint)."""

    def __init__(self, root, watcher, on_close):
        self.watcher, self.on_close = watcher, on_close
        self.win = modal(root, "Hint", 520, 520)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.win.bind("<Escape>", lambda e: self.close())
        _heading(self.win, "Wo ist mein Item?",
                 "Ein Hint verrät, in welcher Welt und an welchem Ort ein Item von dir liegt.\n"
                 "Die Antwort erscheint im Live-Feed und im Log.")
        self.l_points = tk.Label(self.win, bg=theme.BG, fg=theme.ACCENT_HI, font=("Segoe UI Semibold", 10))
        self.l_points.pack(anchor="w", padx=14, pady=(8, 0))
        self.v_filter = tk.StringVar()
        e = ttk.Entry(self.win, textvariable=self.v_filter)
        e.pack(fill="x", padx=14, pady=(8, 0))
        self.items = watcher.my_item_names()
        self.lb = _listbox(self.win, [])
        self.v_filter.trace_add("write", lambda *a: self._filter())
        self._filter()
        row = tk.Frame(self.win, bg=theme.BG)
        row.pack(pady=(0, 12))
        widgets.RoundButton(row, "💡  Hint holen", self.hint, "primary", bg=theme.BG).pack(side="left", padx=4)
        widgets.RoundButton(row, "📜  Meine Hints anzeigen", lambda: self.watcher.say("!hint"),
                            bg=theme.BG).pack(side="left", padx=4)
        self.lb.bind("<Double-Button-1>", lambda e: self.hint())
        self.win.bind("<Return>", lambda e: self.hint())
        self.update_points(watcher.hint_points, watcher.hint_cost)
        e.focus_set()

    def _filter(self):
        text = self.v_filter.get().strip().lower()
        self.shown = [i for i in self.items if text in i.lower()]
        self.lb.delete(0, "end")
        for i in self.shown:
            self.lb.insert("end", "  " + i)
        if self.shown:
            self.lb.selection_set(0)

    def update_points(self, points, cost):
        if cost:
            enough = points >= cost
            self.l_points.configure(text=f"Hint-Punkte: {points}  ·  ein Hint kostet {cost}"
                                         + ("" if enough else "  –  noch zu wenig (mehr Checks machen)"),
                                    fg=theme.OK if enough else theme.WARN)
        else:
            self.l_points.configure(text=f"Hint-Punkte: {points}  ·  Hints sind kostenlos", fg=theme.OK)

    def hint(self):
        sel = self.lb.curselection()
        if not sel:
            return
        item = self.shown[sel[0]]
        self.watcher.say(f"!hint {item}")
        self.win.after(10, lambda: messagebox.showinfo("Hint", f"Hint für „{item}“ angefragt.\n"
                                                               "Die Antwort steht gleich im Live-Feed.",
                                                       parent=self.win))

    def close(self):
        self.win.destroy()
        self.on_close()


def show_stats(root, paths):
    runs = stats.list_runs(paths.sessions)
    if not runs:
        messagebox.showinfo("Statistik", "Noch keine Statistik. Sie erscheint, sobald du eine Multiworld "
                                         "hostest oder mit einer verbunden bist.")
        return
    win = modal(root, "Statistik", 720, 560)
    _heading(win, "Statistik", "Items und Checks: kompletter Spielstand. Spielzeit und Durststrecke: nur, "
                               "solange dein Launcher verbunden war.")
    titles = [stats.run_title(r) for r in runs]
    v = tk.StringVar(value=titles[0])
    box = ttk.Combobox(win, textvariable=v, values=titles, state="readonly")
    box.pack(fill="x", padx=14, pady=(8, 0))
    text = tk.Text(win, wrap="word", font=("Segoe UI", 10), padx=10, pady=8)
    theme.style_text(text)
    text.pack(fill="both", expand=True, padx=14, pady=10)

    def show(*_):
        text.configure(state="normal")
        text.delete("1.0", "end")
        text.insert("end", stats.report(runs[titles.index(v.get())]))
        text.configure(state="disabled")
    box.bind("<<ComboboxSelected>>", show)
    show()


def show_backups(root, paths, log):
    win = modal(root, "Spielstand-Backups", 640, 420)
    _heading(win, "Spielstand-Backups",
             "Vor jedem Spielstart werden SoH-, Mario-64- und Server-Spielstände gesichert (die letzten "
             f"{backup.KEEP}).\nWiederherstellen geht nur, wenn Spiel und Server beendet sind.")
    items = []
    lb = _listbox(win, [])

    def refresh():
        items[:] = backup.list_backups(paths)
        lb.delete(0, "end")
        for b in items:
            lb.insert("end", f"  {b['time'].strftime('%d.%m.%Y  %H:%M')}    –    {b['reason']}  "
                             f"({len(b['files'])} Dateien)")
        if items:
            lb.selection_set(0)

    def now():
        if backup.create(paths, "von Hand", force=True):
            log("Backup erstellt.")
        else:
            messagebox.showinfo("Backup", "Keine Spielstände gefunden.", parent=win)
        refresh()

    def restore():
        sel = lb.curselection()
        if not sel:
            return
        b = items[sel[0]]
        if not messagebox.askyesno("Wiederherstellen", f"Spielstände vom {b['time'].strftime('%d.%m.%Y %H:%M')} "
                                   "zurückspielen?\nDer aktuelle Stand wird vorher selbst gesichert.", parent=win):
            return
        try:
            backup.restore(paths, b)
        except (backup.BackupError, OSError) as e:
            messagebox.showerror("Wiederherstellen", str(e), parent=win)
            return
        log(f"Backup vom {b['time'].strftime('%d.%m.%Y %H:%M')} wiederhergestellt.")
        messagebox.showinfo("Wiederherstellen", "Fertig.", parent=win)
        refresh()

    row = tk.Frame(win, bg=theme.BG)
    row.pack(pady=(0, 12))
    widgets.RoundButton(row, "↩  Wiederherstellen", restore, "primary", bg=theme.BG).pack(side="left", padx=4)
    widgets.RoundButton(row, "💾  Jetzt sichern", now, bg=theme.BG).pack(side="left", padx=4)
    widgets.RoundButton(row, "📂  Ordner", lambda: os.startfile(paths.root / "backups")
                        if (paths.root / "backups").is_dir() else None, "ghost", bg=theme.BG).pack(side="left", padx=4)
    refresh()
