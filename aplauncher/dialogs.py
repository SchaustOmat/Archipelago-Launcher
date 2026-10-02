"""Small modal windows of the launcher: resume a multiworld, hints, statistics, save backups."""
import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from . import backup, host, i18n, stats, theme, widgets
from .i18n import _


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


def pick_session(root, paths, on_pick, log=None):
    """Saved multiworlds with exact creation and last-played times, last played first.
    on_pick(zip_path) starts the chosen one; delete moves one to the recycle bin."""
    sessions = []
    win = modal(root, _("Spielstand fortsetzen"), 820, 460)
    _heading(win, _("Welche Multiworld möchtest du fortsetzen?"),
             _("Sortiert nach „zuletzt gespielt“. Doppelklick oder Enter startet den Server mit diesem Spielstand.\n"
               "Löschen verschiebt den Spielstand in den Papierkorb."))
    row = tk.Frame(win, bg=theme.BG)
    row.pack(side="bottom", fill="x", padx=14, pady=(0, 12))
    cols = ("created", "played", "players")
    tree = ttk.Treeview(win, columns=cols, show="headings", selectmode="browse", height=8)
    for c, t, w in zip(cols, (_("Erstellt"), _("Zuletzt gespielt"), _("Spieler")), (210, 210, 340)):
        tree.heading(c, text=t, anchor="w")
        tree.column(c, width=w, anchor="w", stretch=c == "players")
    tree.pack(fill="both", expand=True, padx=14, pady=10)

    def refresh(select=0):
        sessions[:] = host.list_sessions(paths)
        tree.delete(*tree.get_children())
        for i, z in enumerate(sessions):
            played = datetime.fromtimestamp(host.last_played(z))
            tree.insert("", "end", iid=str(i), values=(i18n.exact(host.created(z)), i18n.exact(played),
                                                       ", ".join(host.session_players(z)) or "–"))
        if sessions:
            iid = str(min(select, len(sessions) - 1))
            tree.selection_set(iid)
            tree.focus(iid)

    def chosen():
        sel = tree.selection()
        return sessions[int(sel[0])] if sel else None

    def go():
        z = chosen()
        if z:
            win.destroy()
            on_pick(z)

    def delete():
        z = chosen()
        if not z:
            return
        if not messagebox.askyesno(_("Spielstand löschen"),
                                   _("Spielstand vom {date} löschen?\nSpieler: {players}\n\n"
                                     "Er kommt in den Papierkorb und lässt sich dort wiederherstellen.").format(
                                       date=i18n.exact(host.created(z)),
                                       players=", ".join(host.session_players(z)) or "–"), parent=win):
            return
        index = int(tree.selection()[0])
        try:
            host.delete_session(paths, z)
        except (host.HostError, OSError) as e:
            messagebox.showerror(_("Spielstand löschen"), str(e), parent=win)
            return
        if log:
            log(_("Spielstand vom {date} in den Papierkorb verschoben.").format(date=i18n.exact(host.created(z))))
        refresh(index)
        if not sessions:
            win.destroy()

    widgets.RoundButton(row, _("▶  Diesen Spielstand starten"), go, "primary", bg=theme.BG).pack(side="left")
    widgets.RoundButton(row, _("🗑  Löschen"), delete, "danger", bg=theme.BG).pack(side="right")
    tree.bind("<Double-Button-1>", lambda e: go())
    tree.bind("<Delete>", lambda e: delete())
    win.bind("<Return>", lambda e: go())
    refresh()
    win.lift()
    win.grab_set()
    tree.focus_set()


class HintDialog:
    """Pick one of your own game's items and ask the server where it is (!hint)."""

    def __init__(self, root, watcher, on_close):
        self.watcher, self.on_close = watcher, on_close
        self.win = modal(root, "Hint", 520, 520)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.win.bind("<Escape>", lambda e: self.close())
        _heading(self.win, _("Wo ist mein Item?"),
                 _("Ein Hint verrät, in welcher Welt und an welchem Ort ein Item von dir liegt.\n"
                   "Die Antwort erscheint im Live-Feed und im Log."))
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
        widgets.RoundButton(row, _("💡  Hint holen"), self.hint, "primary", bg=theme.BG).pack(side="left", padx=4)
        widgets.RoundButton(row, _("📜  Meine Hints anzeigen"), lambda: self.watcher.say("!hint"),
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
            self.l_points.configure(text=_("Hint-Punkte: {points}  ·  ein Hint kostet {cost}").format(
                                             points=points, cost=cost)
                                         + ("" if enough else "  –  " + _("noch zu wenig (mehr Checks machen)")),
                                    fg=theme.OK if enough else theme.WARN)
        else:
            self.l_points.configure(text=_("Hint-Punkte: {points}  ·  Hints sind kostenlos").format(points=points),
                                    fg=theme.OK)

    def hint(self):
        sel = self.lb.curselection()
        if not sel:
            return
        item = self.shown[sel[0]]
        self.watcher.say(f"!hint {item}")
        self.win.after(10, lambda: messagebox.showinfo("Hint", _("Hint für „{item}“ angefragt.\n"
                                                                 "Die Antwort steht gleich im Live-Feed.").format(item=item),
                                                       parent=self.win))

    def close(self):
        self.win.destroy()
        self.on_close()


def show_stats(root, paths):
    runs = stats.list_runs(paths.sessions)
    if not runs:
        messagebox.showinfo(_("Statistik"), _("Noch keine Statistik. Sie erscheint, sobald du eine Multiworld "
                                              "hostest oder mit einer verbunden bist."))
        return
    win = modal(root, _("Statistik"), 720, 560)
    _heading(win, _("Statistik"), _("Items und Checks: kompletter Spielstand. Spielzeit und Durststrecke: nur, "
                                    "solange dein Launcher verbunden war."))
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
    win = modal(root, _("Spielstand-Backups"), 640, 420)
    _heading(win, _("Spielstand-Backups"),
             _("Vor jedem Spielstart werden SoH-, Mario-64- und Server-Spielstände gesichert (die letzten "
               "{n}).\nWiederherstellen geht nur, wenn Spiel und Server beendet sind.").format(n=backup.KEEP))
    items = []
    lb = _listbox(win, [])

    def refresh():
        items[:] = backup.list_backups(paths)
        lb.delete(0, "end")
        for b in items:
            lb.insert("end", f"  {i18n.date(b['time'])}    –    {_(b['reason'])}  "
                             + _("({n} Dateien)").format(n=len(b["files"])))
        if items:
            lb.selection_set(0)

    def now():
        if backup.create(paths, "von Hand", force=True):
            log(_("Backup erstellt."))
        else:
            messagebox.showinfo("Backup", _("Keine Spielstände gefunden."), parent=win)
        refresh()

    def restore():
        sel = lb.curselection()
        if not sel:
            return
        b = items[sel[0]]
        if not messagebox.askyesno(_("Wiederherstellen"), _("Spielstände vom {date} zurückspielen?\n"
                                                             "Der aktuelle Stand wird vorher selbst gesichert.").format(
                                       date=i18n.date(b["time"])), parent=win):
            return
        try:
            backup.restore(paths, b)
        except (backup.BackupError, OSError) as e:
            messagebox.showerror(_("Wiederherstellen"), str(e), parent=win)
            return
        log(_("Backup vom {date} wiederhergestellt.").format(date=i18n.date(b["time"])))
        messagebox.showinfo(_("Wiederherstellen"), _("Fertig."), parent=win)
        refresh()

    row = tk.Frame(win, bg=theme.BG)
    row.pack(pady=(0, 12))
    widgets.RoundButton(row, _("↩  Wiederherstellen"), restore, "primary", bg=theme.BG).pack(side="left", padx=4)
    widgets.RoundButton(row, _("💾  Jetzt sichern"), now, bg=theme.BG).pack(side="left", padx=4)
    widgets.RoundButton(row, _("📂  Ordner"), lambda: os.startfile(paths.root / "backups")
                        if (paths.root / "backups").is_dir() else None, "ghost", bg=theme.BG).pack(side="left", padx=4)
    refresh()
