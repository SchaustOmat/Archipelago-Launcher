"""Tkinter window tying install, lobby, server and games together."""
import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
import tempfile
import uuid
import webbrowser
import winsound
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from . import apclient, backup, config, dialogs, games, host, i18n, lobby, overlay, roms, sail, theme, updates, widgets
from .i18n import _
from .config import GAMES, NO_GAME, Paths
from .install import InstallError, Installer

POLL_MS = 100
LOBBY_POLL_S = 2


class App:
    def __init__(self):
        self.s = config.load_settings()
        self.s.setdefault("cid", uuid.uuid4().hex)
        i18n.set_lang(self.s.get("lang"))
        self.q = queue.Queue()
        self.busy = False
        self.mode = None            # None | "host" | "client"
        self.lobby: lobby.Lobby | None = None
        self.server: host.Server | None = None
        self.watcher: apclient.APWatcher | None = None
        self.client_poll_stop = threading.Event()

        self.root = tk.Tk()
        self.root.title(f"{config.APP_NAME} {config.APP_VERSION}")
        self.root.geometry("1040x760")
        self.root.minsize(900, 660)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        theme.apply(self.root)
        try:  # default= applies the icon to every window (overlay, dialogs) too
            self.root.iconbitmap(default=str(config.bundle_dir() / "assets" / "icon.ico"))
        except tk.TclError:
            pass
        theme.dark_titlebar(self.root)
        self.ap_connected = False
        self.friend_address = ""
        self.overlay: overlay.Overlay | None = None
        self.hint_dialog: dialogs.HintDialog | None = None
        self.vpn_found = []         # [(name, ip)] of VPN adapters (Radmin, Hamachi, ...)
        self.update_info = None
        # SoH reports scene changes here (Sail); the overlay/HUD use it to know where Link is.
        self.sail = sail.SailServer()
        self.sail.start()
        self.session_zip = None
        self._build()
        self._load_fields()
        widgets.fade_in(self.root)
        self.root.after(POLL_MS, self._drain)
        self._check_update()

    # ================= layout =================
    def _card(self, parent, title=None, **pack):
        outer = tk.Frame(parent, bg=theme.PANEL, highlightthickness=1, highlightbackground=theme.BORDER)
        outer.pack(fill=pack.pop("fill", "x"), expand=pack.pop("expand", False), pady=pack.pop("pady", (0, 10)),
                   **pack)
        inner = ttk.Frame(outer, style="Card.TFrame", padding=(14, 10, 14, 12))
        inner.pack(fill="both", expand=True)
        if title:
            tk.Label(inner, text=title, bg=theme.PANEL, fg=theme.ACCENT_HI,
                     font=("Segoe UI Semibold", 11)).pack(anchor="w", pady=(0, 8))
        return inner

    def _field(self, parent, label, var, width=28, show=None):
        box = ttk.Frame(parent, style="Card.TFrame")
        ttk.Label(box, text=label, style="CardMuted.TLabel").pack(anchor="w")
        e = ttk.Entry(box, textvariable=var, width=width, show=show)
        e.pack(fill="x", pady=(2, 0))
        return box, e

    def _build(self):
        self.toast = widgets.Toast(self.root)

        head = ttk.Frame(self.root, padding=(18, 14, 18, 0))
        head.pack(fill="x")
        titles = ttk.Frame(head)
        titles.pack(side="left")
        tk.Label(titles, text="◆ Archipelago Launcher", bg=theme.BG, fg=theme.FG,
                 font=("Segoe UI Semibold", 18)).pack(anchor="w")
        tk.Label(titles, text="Super Mario 64 · Ocarina of Time   ·   " + _("Version {v}").format(v=config.APP_VERSION),
                 bg=theme.BG, fg=theme.MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        self.pill = widgets.StatusPill(head)
        self.pill.pack(side="right", pady=6)
        # Shown only when a newer release exists (see _check_update).
        self.b_update = widgets.RoundButton(head, "⬆  Update", self.install_update, "primary", bg=theme.BG,
                                            height=32)

        self.tabs = widgets.TabBar(self.root, [("play", _("🎮  Spielen")), ("setup", _("⚙  Einrichtung")),
                                              ("net", _("🌐  Netzwerk")), ("log", _("📜  Log"))], self._show_tab)
        self.tabs.pack(fill="x", padx=14, pady=(8, 0))

        body = ttk.Frame(self.root, padding=(18, 12, 18, 6))
        body.pack(fill="both", expand=True)
        self.pages = {k: ttk.Frame(body) for k in ("play", "setup", "net", "log")}
        for page in self.pages.values():
            page.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._build_play(self.pages["play"])
        self._build_setup(self.pages["setup"])
        self._build_net(self.pages["net"])
        self._build_log(self.pages["log"])

        # Progress bar only appears while something runs.
        self.foot = ttk.Frame(self.root, padding=(18, 0, 18, 10))
        self.pb = ttk.Progressbar(self.foot, mode="determinate", maximum=1.0, style="Thin.Horizontal.TProgressbar")
        self.pb.pack(side="left", fill="x", expand=True)
        self.l_prog = tk.Label(self.foot, text="", bg=theme.BG, fg=theme.MUTED, font=("Segoe UI", 9),
                               width=46, anchor="e")
        self.l_prog.pack(side="left", padx=(10, 0))

    def _show_tab(self, key):
        self.pages[key].tkraise()

    def _build_play(self, page):
        conn = self._card(page, _("Verbindung"))
        row = ttk.Frame(conn, style="Card.TFrame")
        row.pack(fill="x")
        self.v_addr, self.v_pw = tk.StringVar(), tk.StringVar()
        box = self._field(row, _("Server-Adresse (vom Host)"), self.v_addr, width=34)[0]
        box.pack(side="left", padx=(0, 12))
        box = self._field(row, _("Passwort (optional)"), self.v_pw, width=16, show="•")[0]
        box.pack(side="left")

        self.actions = ttk.Frame(conn, style="Card.TFrame")
        self.actions.pack(fill="x", pady=(12, 0))
        mk = lambda text, cmd, kind="secondary": widgets.RoundButton(self.actions, text, cmd, kind)
        self.b_host = mk(_("🖥  Server hosten"), self.host_start, "primary")
        self.b_join = mk(_("🔗  Beitreten"), self.client_join, "primary")
        self.b_resume = mk(_("💾  Spielstand fortsetzen"), self.host_resume)
        self.b_gen = mk(_("🚀  Multiworld starten"), self.host_generate, "primary")
        self.b_play = widgets.RoundButton(self.actions, _("▶  Spielen"), self.play, "primary", height=40, size=11)
        self.b_overlay = mk("🗺  Overlay", self.toggle_overlay)
        self.b_hint = mk("💡  Hint", self.open_hints)
        self.b_stats = mk(_("📊  Statistik"), lambda: dialogs.show_stats(self.root, self.paths))
        self.b_stop = mk(_("Beenden"), self.stop_all, "danger")

        info = ttk.Frame(conn, style="Card.TFrame")
        info.pack(fill="x", pady=(10, 0))
        self.l_state = ttk.Label(info, text=_("Nicht verbunden."), style="Card.TLabel")
        self.l_state.pack(side="left")
        self.l_addr = tk.Label(info, text="", bg=theme.PANEL, fg=theme.OK, cursor="hand2",
                               font=("Segoe UI Semibold", 10))
        self.l_addr.pack(side="right")
        self.l_addr.bind("<Button-1>", lambda e: self.copy_address())

        pc = self._card(page, _("Spieler"), fill="both", expand=True)
        cols = ("name", "game", "status", "progress")
        self.tree = ttk.Treeview(pc, columns=cols, show="headings", height=5)
        for c, t, w in zip(cols, (_("Name"), _("Spiel"), _("Status"), _("Fortschritt")), (170, 260, 150, 140)):
            self.tree.heading(c, text=t, anchor="w")
            self.tree.column(c, width=w, anchor="w")
        self.tree.tag_configure("me", font=("Segoe UI Semibold", 10), foreground=theme.ACCENT_HI)
        self.tree.pack(fill="both", expand=True)

        feed = self._card(page, "Live", pady=(0, 0))
        self.feed = tk.Text(feed, height=5, wrap="word", state="disabled", font=("Segoe UI", 9), padx=8, pady=4)
        theme.style_text(self.feed)
        self.feed.pack(fill="x")

    def _build_setup(self, page):
        top = ttk.Frame(page)
        top.pack(fill="x")
        who = self._card(top, _("Du"), side="left", fill="y", pady=(0, 10), padx=(0, 10))
        self.v_name = tk.StringVar()
        self._field(who, _("Spielername (max. 16 Zeichen)"), self.v_name, width=22)[0].pack(anchor="w")
        ttk.Label(who, text="Sprache / Language", style="CardMuted.TLabel").pack(anchor="w", pady=(8, 0))
        self.v_lang = tk.StringVar(value=i18n.LANGS[i18n.lang()])
        lang_box = ttk.Combobox(who, textvariable=self.v_lang, values=list(i18n.LANGS.values()), state="readonly",
                                width=20)
        lang_box.pack(anchor="w", pady=(2, 0))
        lang_box.bind("<<ComboboxSelected>>", lambda e: self.change_language())

        gc = self._card(top, _("Spiel"), side="left", fill="x", expand=True)
        cards = ttk.Frame(gc, style="Card.TFrame")
        cards.pack(fill="x")
        self.game_labels = {**{k: g["label"] for k, g in GAMES.items()}, NO_GAME: _("Kein Spiel (nur hosten)")}
        self.v_game = tk.StringVar()
        self.game_cards = {}
        for key, icon, title, sub in (("sm64", "⭐", "Super Mario 64", "sm64ex · 60 FPS"),
                                      ("soh", "🗡", "Ocarina of Time", "Ship of Harkinian"),
                                      (NO_GAME, "🖥", _("Nur hosten"), _("kein eigenes Spiel"))):
            card = widgets.GameCard(cards, icon, title, sub, lambda k=key: self._select_game(k))
            card.pack(side="left", padx=(0, 10), fill="x", expand=True)
            self.game_cards[key] = card

        rc = self._card(page, "ROM")
        row = ttk.Frame(rc, style="Card.TFrame")
        row.pack(fill="x")
        self.v_rom = tk.StringVar()
        self.e_rom = ttk.Entry(row, textvariable=self.v_rom)
        self.e_rom.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.b_rom = widgets.RoundButton(row, _("Durchsuchen …"), self.pick_rom, height=32)
        self.b_rom.pack(side="left")
        self.l_rom = tk.Label(rc, text="", bg=theme.PANEL, fg=theme.MUTED, font=("Segoe UI", 9))
        self.l_rom.pack(anchor="w", pady=(6, 0))

        ic = self._card(page, _("Installation"))
        row = ttk.Frame(ic, style="Card.TFrame")
        row.pack(fill="x")
        self.b_install = widgets.RoundButton(row, _("⬇  Installieren / Prüfen"), self.install, "primary")
        self.b_install.pack(side="left")
        self.l_inst = tk.Label(row, text="", bg=theme.PANEL, font=("Segoe UI Semibold", 10))
        self.l_inst.pack(side="left", padx=14)
        self.v_root = tk.StringVar()
        widgets.RoundButton(row, _("Ändern …"), self.pick_root, "ghost", height=32).pack(side="right")
        ttk.Entry(row, textvariable=self.v_root, width=24).pack(side="right", padx=8)
        ttk.Label(row, text=_("Ordner:"), style="CardMuted.TLabel").pack(side="right")

        oc = self._card(page, _("Optionen"))
        row = ttk.Frame(oc, style="Card.TFrame")
        row.pack(fill="x")
        widgets.RoundButton(row, _("📝  YAML bearbeiten"), self.edit_yaml, height=32).pack(side="left", padx=(0, 8))
        widgets.RoundButton(row, "🧩  Options Creator", self.options_creator, height=32).pack(side="left", padx=(0, 8))
        widgets.RoundButton(row, "🗄  Backups", lambda: dialogs.show_backups(self.root, self.paths, self._log),
                            height=32).pack(side="left", padx=(0, 8))
        widgets.RoundButton(row, _("📂  Ordner öffnen"), lambda: self._open(self.paths.root), "ghost",
                            height=32).pack(side="left")
        self.v_sounds = tk.BooleanVar()
        ttk.Checkbutton(row, text=_("🔔 Ton bei wichtigen Items"), variable=self.v_sounds, style="Card.TCheckbutton",
                        command=self._save_fields).pack(side="right")
        self.game_opts = ttk.Frame(oc, style="Card.TFrame")
        self.game_opts.pack(fill="x", pady=(10, 0))
        self.b_mods = widgets.RoundButton(self.game_opts, _("🎨  SoH Mods / Texturen"), self.open_soh_mods, height=32)

    def _build_net(self, page):
        ac = self._card(page, _("Adresse für Freunde"))
        self.l_addr_net = tk.Label(ac, text="", bg=theme.PANEL, fg=theme.OK, font=("Segoe UI Semibold", 12),
                                   cursor="hand2")
        self.l_addr_net.pack(anchor="w")
        self.l_addr_net.bind("<Button-1>", lambda e: self.copy_address())
        ttk.Label(ac, text=_("Wird beim Hosten angezeigt. Anklicken kopiert sie. Eigene Adresse (z. B. "
                             "playit-Adresse) hier festlegen. Leer = automatisch: Radmin/Hamachi-Adresse, falls "
                             "vorhanden, sonst Internet-IP:"),
                  style="CardMuted.TLabel", wraplength=860).pack(anchor="w", pady=(6, 4))
        row = ttk.Frame(ac, style="Card.TFrame")
        row.pack(fill="x")
        self.v_public = tk.StringVar()
        ttk.Entry(row, textvariable=self.v_public, width=34).pack(side="left")
        widgets.RoundButton(row, _("Speichern"), self.save_public_address, height=32).pack(side="left", padx=8)
        self.vpn_box = ttk.Frame(row, style="Card.TFrame")
        self.vpn_box.pack(side="left")

        pc = self._card(page, _("Erreichbarkeit"))
        row = ttk.Frame(pc, style="Card.TFrame")
        row.pack(fill="x")
        self.v_port = tk.StringVar()
        self._field(row, _("Port"), self.v_port, width=8)[0].pack(side="left", padx=(0, 12))
        widgets.RoundButton(row, _("📡  Port testen"), self.port_test, height=32).pack(side="left", anchor="s")
        widgets.RoundButton(row, _("🌍  playit.gg einrichten"), self.playit, height=32).pack(side="left", padx=8,
                                                                                       anchor="s")
        ttk.Label(pc, text=_("Ohne Portfreigabe im Router: alle nutzen Radmin VPN / Hamachi (Host-Adresse aus "
                             "dem VPN-Programm) oder der Host richtet playit.gg ein."),
                  style="CardMuted.TLabel", wraplength=860).pack(anchor="w", pady=(10, 0))

    def _build_log(self, page):
        lc = self._card(page, None, fill="both", expand=True, pady=(0, 0))
        self.log_box = tk.Text(lc, wrap="word", state="disabled", font=("Consolas", 10), padx=8, pady=6)
        theme.style_text(self.log_box)
        sb = ttk.Scrollbar(lc, command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_box.pack(fill="both", expand=True)

    # ================= settings / fields =================
    @property
    def paths(self) -> Paths:
        return Paths(self.v_root.get().strip() or config.DEFAULT_ROOT)

    @property
    def game(self) -> str:
        return self.v_game.get() or NO_GAME

    @property
    def port(self) -> int:
        try:
            return int(self.v_port.get())
        except ValueError:
            return config.DEFAULT_PORT

    def _load_fields(self):
        self.v_name.set(self.s["name"])
        self.v_game.set(self.s["game"] if self.s["game"] in self.game_labels else "sm64")
        self.v_root.set(self.s["root"])
        self.v_addr.set(self.s["address"])
        self.v_pw.set(self.s["password"])
        self.v_port.set(str(self.s.get("port", config.DEFAULT_PORT)))
        self.v_public.set(self.s.get("public_address", ""))
        self.v_sounds.set(self.s.get("sounds", True))
        self._set_friend_address("")
        self._game_changed()
        self._refresh_buttons()
        self._detect_vpn()
        # First start or missing install: open the setup tab, otherwise go straight to playing.
        self.tabs.select("play" if self.v_name.get() and self._installed() else "setup", animate=False)

    def _save_fields(self):
        if self.game in GAMES:
            self.s["roms"][self.game] = self.v_rom.get().strip()
        self.s.update(name=self.v_name.get().strip(), game=self.game, root=self.v_root.get().strip(),
                      address=self.v_addr.get().strip(), password=self.v_pw.get(), port=self.port,
                      sounds=self.v_sounds.get())
        config.save_settings(self.s)

    def _select_game(self, key):
        if self.game in GAMES:
            self.s["roms"][self.game] = self.v_rom.get().strip()
        self.v_game.set(key)
        self._game_changed()
        self._save_fields()

    def _game_changed(self):
        g = self.game
        for key, card in self.game_cards.items():
            card.set_selected(key == g)
        state = "normal" if g in GAMES else "disabled"
        self.e_rom.configure(state=state)
        self.b_rom.configure(state=state)
        self.v_rom.set(self.s["roms"].get(g, "") if g in GAMES else "")
        self.b_mods.pack_forget()
        if g == "soh":
            self.b_mods.pack(anchor="w")
        self._check_rom()
        self._update_install_label()
        self._refresh_buttons()

    def _check_rom(self):
        g = self.game
        if g not in GAMES:
            self.l_rom.configure(text=_("Keine ROM nötig."), foreground=theme.MUTED)
            return
        path = self.v_rom.get().strip()
        if not path:
            self.l_rom.configure(text=_("Bitte die eigene ROM auswählen (.z64/.n64/.v64)."), foreground=theme.MUTED)
            return
        ok, text = roms.describe(g, path)
        self.l_rom.configure(text=("✓ " if ok else "✗ ") + text, foreground=theme.OK if ok else theme.ERR)

    def _installer(self):
        return Installer(self.paths, self.log_threadsafe, self.progress_threadsafe)

    def _installed(self) -> bool:
        i = self._installer()
        if not i.archipelago_ok():
            return False
        if self.game == "sm64":
            return i.sm64_region_built() is not None
        if self.game == "soh":
            return i.soh_ok()
        return True

    def _update_install_label(self):
        ok = self._installed()
        self.l_inst.configure(text=_("✓ installiert") if ok else _("● noch nicht installiert"),
                              foreground=theme.OK if ok else theme.WARN)

    def _refresh_buttons(self):
        """Only the buttons that make sense right now are shown."""
        connected = self.ap_connected
        lobby_open = self.mode == "host" and self.lobby is not None and self.lobby.state == "lobby"
        if self.mode is None:
            visible = [self.b_host, self.b_join, self.b_resume, self.b_stats]
            pill = ("busy", _("Arbeitet …")) if self.busy else ("offline", _("Offline"))
        elif lobby_open:
            visible = [self.b_gen, self.b_stop]
            pill = ("lobby", _("Lobby · {n} Spieler").format(n=len(self.lobby.players)))
        elif connected:
            visible = ([self.b_play, self.b_overlay, self.b_hint] if self.game in GAMES else []) + [self.b_stats,
                                                                                                 self.b_stop]
            pill = ("connected", _("Verbunden"))
        else:
            visible = [self.b_stop]
            pill = ("busy", _("Lobby") if self.mode == "client" else _("Startet …"))
        if [w for w in self.actions.pack_slaves()] != visible:
            for w in self.actions.pack_slaves():
                w.pack_forget()
            for w in visible:
                w.pack(side="right" if w is self.b_stop else "left", padx=(0, 8))
        for b in (self.b_host, self.b_join, self.b_resume, self.b_gen):
            b.configure(state="disabled" if self.busy else "normal")
        self.b_install.configure(state="disabled" if self.busy else "normal")
        self.pill.set(*pill)

    # ================= thread-safe plumbing =================
    def log_threadsafe(self, text):
        self.q.put(("log", text))

    def progress_threadsafe(self, frac, text):
        self.q.put(("progress", (frac, text)))

    def call(self, fn, *a):
        self.q.put(("call", (fn, a)))

    def _drain(self):
        try:
            while True:
                kind, data = self.q.get_nowait()
                if kind == "log":
                    self._log(data)
                elif kind == "progress":
                    frac, text = data
                    if (frac is not None or text) and not self.foot.winfo_ismapped():
                        self.foot.pack(fill="x", side="bottom")
                    elif frac is None and not text:
                        self.foot.pack_forget()
                    if frac is None:
                        self.pb.configure(mode="indeterminate")
                        self.pb.start(15) if text else self.pb.stop()
                        if not text:
                            self.pb.configure(mode="determinate", value=0)
                    else:
                        self.pb.stop()
                        self.pb.configure(mode="determinate", value=frac)
                    self.l_prog.configure(text=text)
                elif kind == "call":
                    fn, a = data
                    fn(*a)
        except queue.Empty:
            pass
        self.root.after(POLL_MS, self._drain)

    def _log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        if int(self.log_box.index("end-1c").split(".")[0]) > 5000:
            self.log_box.delete("1.0", "1000.0")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def background(self, fn, done=None):
        """Run fn in a worker thread; errors land in a message box."""
        self.busy = True
        self._refresh_buttons()

        def work():
            err = None
            try:
                fn()
            except Exception as e:  # shown to the user, not swallowed
                err = e
            self.call(self._finish, err, done)
        threading.Thread(target=work, daemon=True).start()

    def _finish(self, err, done):
        self.busy = False
        self.progress_threadsafe(None, "")
        if err:
            self._log(_("FEHLER: {error}").format(error=err))
            messagebox.showerror(_("Fehler"), str(err))
        elif done:
            done()
        self._update_install_label()
        self._refresh_buttons()

    def set_state(self, text):
        self.l_state.configure(text=text)

    def _feed(self, text):
        self.feed.configure(state="normal")
        self.feed.insert("end", text + "\n")
        if int(self.feed.index("end-1c").split(".")[0]) > 300:
            self.feed.delete("1.0", "100.0")
        self.feed.see("end")
        self.feed.configure(state="disabled")

    # ================= setup =================
    def pick_rom(self):
        path = filedialog.askopenfilename(title=_("ROM auswählen"),
                                          filetypes=[("N64 ROM", "*.z64 *.n64 *.v64"), (_("Alle Dateien"), "*.*")])
        if path:
            self.v_rom.set(path)
            self._check_rom()
            self._save_fields()

    def pick_root(self):
        path = filedialog.askdirectory(title=_("Installationsordner (ohne Leerzeichen)"))
        if path:
            if " " in path:
                messagebox.showerror(_("Ordner"), _("Der Ordner darf keine Leerzeichen enthalten (wegen MSYS2/make)."))
                return
            self.v_root.set(os.path.normpath(path))
            self._save_fields()
            self._update_install_label()

    def install(self):
        self._save_fields()
        g, rom = self.game, self.v_rom.get().strip()
        if g in GAMES:
            ok, text = roms.describe(g, rom)
            if not ok:
                messagebox.showerror(_("ROM"), text)
                return
        inst = self._installer()

        def work():
            inst.p.root.mkdir(parents=True, exist_ok=True)
            inst.install_archipelago()
            inst.ensure_templates()
            if g == "sm64":
                inst.install_sm64(rom)
            elif g == "soh":
                inst.install_soh(rom)
            self.log_threadsafe(_("Installation abgeschlossen."))
        self.background(work)

    def edit_yaml(self):
        g = self.game
        if g not in GAMES:
            messagebox.showinfo(_("Optionen"), _("Ohne eigenes Spiel gibt es keine Optionen."))
            return
        path = self.paths.yaml_for(g)
        if not path.is_file():
            messagebox.showinfo(_("Optionen"), _("Bitte erst 'Installieren / Prüfen' ausführen."))
            return
        os.startfile(path)

    def options_creator(self):
        exe = self.paths.ap / "ArchipelagoOptionsCreator.exe"
        if not exe.is_file():
            messagebox.showinfo("Options Creator", _("Bitte erst 'Installieren / Prüfen' ausführen."))
            return
        subprocess.Popen([str(exe)], cwd=self.paths.ap)
        self._log(_("Options Creator gestartet. Die fertige YAML als {path} speichern.").format(
            path=self.paths.yaml_for(self.game)))

    def open_soh_mods(self):
        """SoH loads texture packs (.o2r/.otr) from the mods folder next to soh.exe."""
        if not self.paths.soh_exe.is_file():
            messagebox.showinfo("SoH Mods", _("Ship of Harkinian ist noch nicht installiert. "
                                              "Erst OoT wählen und 'Installieren / Prüfen'."))
            return
        self._open(self.paths.soh / "mods")
        self._log(_("Texturpakete (.o2r/.otr) in den mods-Ordner legen. In SoH unter "
                    "Einstellungen → Mods bzw. 'Alternative Assets' (Taste Tab) aktivieren."))

    def _open(self, path):
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)

    def _my_yaml(self) -> str | None:
        path = self.paths.yaml_for(self.game)
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    def _ready_to_play(self) -> str | None:
        """Error text if this player can't take part yet."""
        err = lobby.validate_name(self.v_name.get())
        if err:
            return err
        if self.game in GAMES:
            if not self._installed():
                return _("Dein Spiel ist noch nicht installiert. Erst 'Installieren / Prüfen'.")
            if self._my_yaml() is None:
                return _("Options-YAML fehlt. Erst 'Installieren / Prüfen'.")
        return None

    # ================= hosting =================
    def _free_port(self) -> bool:
        """Offer to stop a leftover Archipelago server that still holds our port."""
        if self.server and self.server.running():
            return True
        pid = host.server_pid_on_port(self.port)
        if pid is None:
            return True
        if not messagebox.askyesno(_("Server läuft noch"),
                                   _("Auf Port {port} läuft noch ein Archipelago-Server (z. B. von einem "
                                     "geschlossenen Launcher). Mitspieler sind evtl. noch damit verbunden.\n\n"
                                     "Beenden? Der Spielstand ist gespeichert und kann fortgesetzt werden.").format(
                                       port=self.port)):
            return False
        host.kill_pid(pid)
        try:
            host.wait_port_free(self.port)
        except host.HostError as e:
            messagebox.showerror(_("Port"), str(e))
            return False
        self._log(_("Alten Archipelago-Server beendet."))
        return True

    def host_start(self):
        self._save_fields()
        if not self._free_port():
            return
        if not self._installer().archipelago_ok():
            messagebox.showerror(_("Host"), _("Archipelago ist noch nicht installiert. Erst 'Installieren / Prüfen'."))
            return
        plays = self.game in GAMES
        if plays:
            err = self._ready_to_play()
            if err:
                messagebox.showerror(_("Host"), err)
                return
        try:
            self.lobby = lobby.Lobby(self.port, self.v_pw.get())
            self.lobby.start()
        except OSError as e:
            self.lobby = None
            messagebox.showerror(_("Host"), _("Port {port} kann nicht geöffnet werden: {error}").format(port=self.port, error=e))
            return
        self.lobby.on_change = lambda: self.call(self._host_lobby_changed)
        if plays:
            self.lobby.add_player(self.v_name.get().strip(), self.game, self._my_yaml(), local=True)
        self.mode = "host"
        self.v_addr.set(f"localhost:{self.port}")
        self._log(_("Lobby offen auf Port {port}. Freunde tragen deine Adresse ein und klicken 'Beitreten'.").format(
            port=self.port))
        self.set_state(_("Lobby offen – warte auf Spieler. Dann 'Multiworld starten'."))
        self._show_public_address()
        self._host_lobby_changed()
        self._host_lobby_tick()

    def _show_public_address(self):
        if self.s.get("public_address"):
            self._set_friend_address(self.s["public_address"])
            return
        vpn = self._preferred_vpn()
        if vpn:
            # Everyone on the same VPN reaches the host there, no port forwarding needed.
            self._set_friend_address(f"{vpn[1]}:{self.port}")
            self._log(_("{vpn} erkannt: Freunde im selben {vpn}-Netzwerk nutzen {address}. "
                        "Andere Adresse im Netzwerk-Tab festlegen.").format(vpn=vpn[0], address=f"{vpn[1]}:{self.port}"))
            return

        def work():
            ip = host.public_ip()
            # A VPN found in the meantime wins (it already set the address).
            self.call(lambda: self.vpn_found or self._set_friend_address(f"{ip}:{self.port}" if ip else ""))
        threading.Thread(target=work, daemon=True).start()

    def _set_friend_address(self, address):
        self.friend_address = address
        self.l_addr.configure(text=_("📋  Für Freunde: {address}").format(address=address) if address else "")
        self.l_addr_net.configure(text=f"📋  {address}" if address else _("– erst beim Hosten –"),
                                  fg=theme.OK if address else theme.MUTED)

    def copy_address(self):
        if not self.friend_address:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.friend_address)
        self.toast.show(_("✓ Adresse kopiert: {address}").format(address=self.friend_address))

    def save_public_address(self):
        self.s["public_address"] = self.v_public.get().strip()
        config.save_settings(self.s)
        if self.mode == "host":
            self._show_public_address()
        self.toast.show(_("✓ Gespeichert") if self.s["public_address"] else _("✓ Adresse wird wieder automatisch gewählt"))

    def _detect_vpn(self):
        """Offer the IPs of Radmin VPN / Hamachi / Tailscale / ZeroTier adapters as one-click addresses."""
        def work():
            try:
                out = subprocess.run(["ipconfig"], capture_output=True, text=True, encoding="cp850",
                                     errors="replace", timeout=10, creationflags=subprocess.CREATE_NO_WINDOW).stdout
            except (OSError, subprocess.TimeoutExpired):
                return
            found, adapter = [], ""
            for line in out.splitlines():
                if line and not line.startswith(" "):
                    adapter = line
                m = re.search(r"IPv4[^:]*:\s*([\d.]+)", line)
                if m:
                    for vpn in ("Radmin", "Hamachi", "Tailscale", "ZeroTier"):
                        if vpn.lower() in adapter.lower():
                            found.append((vpn, m.group(1)))
            self.call(self._show_vpn, found)
        threading.Thread(target=work, daemon=True).start()

    def _preferred_vpn(self):
        """Radmin first: that is what most Archipelago groups use."""
        return next(iter(sorted(self.vpn_found, key=lambda v: v[0] != "Radmin")), None)

    def _show_vpn(self, found):
        self.vpn_found = found
        if self.mode == "host" and not self.s.get("public_address") and found:
            self._show_public_address()  # VPN detection finished after hosting started
        for vpn, ip in found:
            addr = f"{ip}:{self.port}"
            widgets.RoundButton(self.vpn_box, f"{vpn}: {ip}", lambda a=addr: (self.v_public.set(a),
                                self.save_public_address()), "ghost", height=32).pack(side="left", padx=(0, 6))

    def _host_lobby_tick(self):
        if self.mode == "host" and self.lobby and self.lobby.state == "lobby":
            self._host_lobby_changed()  # refresh online/offline
            self.root.after(LOBBY_POLL_S * 1000, self._host_lobby_tick)

    def _host_lobby_changed(self):
        if self.lobby:
            self._show_lobby_players(self.lobby.snapshot())
        self._refresh_buttons()

    def _show_lobby_players(self, snap):
        self.tree.delete(*self.tree.get_children())
        me = self.v_name.get().strip()
        for p in snap["players"]:
            status = (_("bereit") if p["ready"] else _("beigetreten")) if p["online"] else _("offline")
            self.tree.insert("", "end", values=(p["name"], GAMES[p["game"]]["label"], status, "-"),
                             tags=("me",) if p["name"] == me else ())

    def host_generate(self):
        lob = self.lobby
        yamls = lob.yamls()
        if not yamls:
            messagebox.showerror(_("Host"), _("Noch keine Spieler in der Lobby."))
            return
        if not messagebox.askyesno("Multiworld", _("Multiworld mit {n} Spieler(n) erstellen und Server starten?\n"
                                                   "Danach kann niemand mehr beitreten.").format(n=len(yamls))):
            return
        lob.set_state("generating", _("Multiworld wird erstellt ..."))
        self.set_state(_("Multiworld wird generiert ..."))
        paths, port, pw = self.paths, self.port, self.v_pw.get()
        result = {}

        def work():
            try:
                result["zip"] = host.generate(paths, yamls, self.log_threadsafe)
            except Exception:
                lob.set_state("lobby", "")
                self.call(self._host_lobby_tick)
                raise
            lob.set_state("starting", _("Server startet ..."))
            import time
            time.sleep(LOBBY_POLL_S + 1.5)  # let clients see "starting" before the lobby goes away
            lob.stop()
            self._start_server(paths, result["zip"], port, pw)
        self.background(work, done=lambda: self._host_running(result["zip"]))

    def host_resume(self):
        self._save_fields()
        if not self._free_port():
            return
        sessions = host.list_sessions(self.paths)
        if not sessions:
            messagebox.showinfo(_("Fortsetzen"), _("Keine gespeicherten Multiworlds gefunden."))
            return
        def go(z):
            self.mode = "host"
            paths, port, pw = self.paths, self.port, self.v_pw.get()
            self.v_addr.set(f"localhost:{port}")
            self._show_public_address()

            def work():
                backup.create(paths, "vor dem Fortsetzen", z)
                self._start_server(paths, z, port, pw)
            self.background(work, done=lambda: self._host_running(z))
        dialogs.pick_session(self.root, sessions, go)

    def _start_server(self, paths, zip_path, port, pw):
        self.server = host.Server(paths, zip_path, port, pw, self.log_threadsafe)
        self.server.start()
        self.log_threadsafe(_("Archipelago-Server gestartet."))

    def _host_running(self, zip_path):
        self.lobby = None
        self.session_zip = zip_path
        self.set_state(_("Server läuft. Alle können jetzt '▶ Spielen' drücken."))
        names = host.session_players(zip_path)
        me = self.v_name.get().strip()
        slot = me if me in names else (names[0] if names else me)
        self._start_watcher(f"localhost:{self.port}", slot)
        self._refresh_buttons()

    # ================= joining =================
    def client_join(self):
        self._save_fields()
        err = self._ready_to_play()
        if not err and self.game not in GAMES:
            err = _("Zum Beitreten bitte ein Spiel auswählen.")
        if err:
            messagebox.showerror(_("Beitreten"), err)
            return
        addr, name, pw = self.v_addr.get().strip(), self.v_name.get().strip(), self.v_pw.get()
        g, yaml_text, cid = self.game, self._my_yaml(), self.s["cid"]
        result = {}

        def work():
            try:
                result["snap"] = lobby.join(addr, name, g, yaml_text, cid, pw)
            except lobby.LobbyError as e:
                if e.unreachable:
                    raise RuntimeError(_(
                        "Der Host ist unter {address} nicht erreichbar.\n\n"
                        "• Stimmt die Adresse (mit :Port)?\n"
                        "• Hat der Host 'Server hosten' geklickt?\n"
                        "• Beim Host fehlt evtl. die Portfreigabe im Router – dann playit.gg nutzen "
                        "und dessen Adresse eintragen.").format(address=addr))
                # Something answered but it is not a lobby: probably the game already runs there.
                result["error"] = str(e)
        self.background(work, done=lambda: self._joined(result, addr, name))

    def _joined(self, result, addr, name):
        self.mode = "client"
        if "snap" in result:
            self._log(_("Lobby beigetreten als {name}.").format(name=name))
            self.set_state(_("In der Lobby – warte, bis der Host die Multiworld startet."))
            self._show_lobby_players(result["snap"])
            self.client_poll_stop.clear()
            threading.Thread(target=self._client_poll, args=(addr, name), daemon=True).start()
        else:
            self._log(_("Beim Host ist keine Lobby offen – dort läuft vermutlich schon eine Multiworld. "
                        "Verbinde mit dem laufenden Spiel ..."))
            self._start_watcher(addr, name)
        self._refresh_buttons()

    def _client_poll(self, addr, name):
        import time
        seen_starting = False
        failures = 0
        while not self.client_poll_stop.is_set():
            try:
                snap = lobby.get_state(addr, name)
                failures = 0
                self.call(self._show_lobby_players, snap)
                if snap["state"] in ("generating", "starting"):
                    seen_starting = True
                    self.call(self.set_state, snap.get("message") or _("Multiworld wird erstellt ..."))
                elif snap["state"] == "lobby":
                    self.call(self.set_state, _("In der Lobby – warte, bis der Host die Multiworld startet."))
            except lobby.LobbyError as e:
                failures += 1
                if seen_starting or failures >= 3:
                    # Lobby is gone: the Archipelago server should be up now.
                    self.call(self._start_watcher, addr, name)
                    return
                self.call(self.set_state, _("Lobby nicht erreichbar: {error}").format(error=e))
            time.sleep(LOBBY_POLL_S)

    # ================= in game =================
    def _start_watcher(self, addr, slot):
        if self.watcher:
            self.watcher.stop()
        self.set_state(_("Verbinde mit dem Archipelago-Server ..."))
        self.watcher = apclient.APWatcher(addr, slot, self.v_pw.get(),
                                          lambda k, d: self.call(self._watch_event, k, d))
        self.watcher.start()

    def _watch_event(self, kind, data):
        if kind == "log":
            self._log(data)
            self._feed(data)
        elif kind == "players":
            self.tree.delete(*self.tree.get_children())
            for r in data:
                self.tree.insert("", "end", values=(r["name"], r["game"], r["status"], r["progress"]),
                                 tags=("me",) if r["me"] else ())
        elif kind == "state":
            self.ap_connected = data["connected"]
            if data["connected"]:
                self.set_state(_("Verbunden. Server läuft – '▶ Spielen' drücken."))
            else:
                self.set_state(data["text"])
            self._refresh_buttons()
        elif kind == "error":
            self.set_state(_("Fehler: {error}").format(error=data))
            messagebox.showerror("Archipelago", data)
        elif kind == "hints":
            if self.hint_dialog:
                self.hint_dialog.update_points(data["points"], data["cost"])
        elif kind == "received" and data["progression"]:
            self._notify(_("⭐ {item} von {sender}").format(item=data["item"], sender=data["sender"]))
        elif kind == "goal":
            self._notify(_("🏆 {name} hat das Ziel erreicht!").format(name=data))

    def _notify(self, text):
        """Important event: toast in the launcher, line in the in-game HUD, optional sound."""
        self.toast.show(text, ms=4000)
        if self.overlay:
            self.overlay.hud.notify(text)
        if self.v_sounds.get():
            winsound.MessageBeep(winsound.MB_ICONASTERISK)

    def open_hints(self):
        if self.hint_dialog:
            self.hint_dialog.win.lift()
            return
        if not (self.watcher and self.ap_connected):
            return
        if not self.watcher.my_item_names():
            messagebox.showinfo("Hint", _("Die Item-Liste ist noch nicht geladen. Gleich nochmal versuchen."))
            return
        self.hint_dialog = dialogs.HintDialog(self.root, self.watcher, self._hints_closed)

    def _hints_closed(self):
        self.hint_dialog = None

    def play(self):
        self._save_fields()
        err = self._ready_to_play()
        if err:
            messagebox.showerror(_("Spiel starten"), err)
            return
        addr = f"localhost:{self.port}" if self.mode == "host" else self.v_addr.get().strip()
        name, pw = self.v_name.get().strip(), self.v_pw.get()
        try:
            if backup.create(self.paths, "vor dem Spielstart", self.session_zip):
                self._log(_("Spielstände gesichert (Einrichtung → Backups)."))
        except OSError as e:
            self._log(_("Backup fehlgeschlagen: {error}").format(error=e))
        try:
            if self.game == "sm64":
                region = self._installer().sm64_region_built()
                games.launch_sm64(self.paths, region, addr, name, pw)
                self._log(_("Super Mario 64 gestartet (verbindet sich automatisch)."))
            elif self.game == "soh":
                games.launch_soh(self.paths, addr, name, pw)
                self._log(_("Ship of Harkinian gestartet. Im Dateiauswahl-Menü 'Archipelago' wählen; "
                            "Server, Name und Passwort sind schon eingetragen."))
        except (games.GameError, OSError) as e:
            messagebox.showerror(_("Spiel starten"), str(e))

    # ================= overlay =================
    def toggle_overlay(self):
        if self.overlay:
            self.overlay.close()
            return
        name, pw = self.v_name.get().strip(), self.v_pw.get()
        addr = f"localhost:{self.port}" if self.mode == "host" else self.v_addr.get().strip()
        # Games without built-in tracker support (Mario 64) rebuild their logic from the player's YAML.
        if self.session_zip:
            yaml_dir = self.session_zip.parent / "players"
        else:
            yaml_dir = self.paths.root / "overlay" / "yaml"
            yaml_dir.mkdir(parents=True, exist_ok=True)
            for old in yaml_dir.glob("*.yaml"):
                old.unlink()
            text = self._my_yaml()
            if text:
                (yaml_dir / "me.yaml").write_text(host.set_yaml_name(text, name), encoding="utf-8")
        inst = self._installer()
        if not inst.archipelago_ok():
            messagebox.showinfo("Overlay", _("Bitte einmal 'Installieren / Prüfen' klicken (Overlay-Logik fehlt noch)."))
            return
        inst.write_bridge_world()
        self.overlay = overlay.Overlay(self.root, self.paths, addr, name, pw, yaml_dir, self.game,
                                       sail=self.sail, on_close=self._overlay_closed)
        self._log(_("Overlay geöffnet. Im Spiel erscheint oben rechts das HUD mit dem, was hier noch offen ist."))

    def _overlay_closed(self):
        self.overlay = None

    # ================= network helpers =================
    def port_test(self):
        port = self.port
        temp = None
        if self.lobby is None and not (self.server and self.server.running()):
            try:  # something must listen for the outside check to succeed
                temp = lobby.Lobby(port)
                temp.start()
            except OSError:
                temp = None
        self._log(_("Teste, ob Port {port} aus dem Internet erreichbar ist ...").format(port=port))

        def work():
            ok = host.port_reachable(port)
            if temp:
                temp.stop()
            if ok is None:
                msg = _("Port-Test konnte nicht durchgeführt werden (Testdienst nicht erreichbar).")
            elif ok:
                msg = _("✓ Port {port} ist von außen erreichbar. Freunde können direkt beitreten.").format(port=port)
            else:
                msg = _("✗ Port {port} ist von außen NICHT erreichbar.\n"
                        "Lösung: Im Router Port {port} (TCP) auf diesen PC weiterleiten und in der Windows-Firewall "
                        "erlauben – oder playit.gg benutzen.").format(port=port)
            self.call(self._log, msg)
            self.call(self.toast.show, msg.splitlines()[0], theme.OK if ok else theme.WARN, 4000)
            if not ok:
                self.call(messagebox.showinfo, _("Port-Test"), msg)
        threading.Thread(target=work, daemon=True).start()

    # ----- playit.gg -----
    @staticmethod
    def _playit_cli():
        base = os.environ.get("ProgramFiles", r"C:\Program Files")
        return Path(base) / "playit_gg" / "bin" / "playit.exe"

    def _playit_status(self) -> dict:
        try:
            out = subprocess.run([str(self._playit_cli()), "status"], capture_output=True, text=True, timeout=15,
                                 creationflags=subprocess.CREATE_NO_WINDOW).stdout
        except (OSError, subprocess.TimeoutExpired):
            return {}
        return {k.strip().lower(): v.strip() for k, _, v in (l.partition(":") for l in out.splitlines()) if v}

    def playit(self):
        cli = self._playit_cli()
        if not cli.is_file():
            if not messagebox.askyesno("playit.gg", _("playit.gg ist noch nicht installiert.\n\n"
                                                      "Jetzt das offizielle Installationspaket laden (ca. 6 MB) und "
                                                      "installieren? Windows fragt dabei nach Admin-Rechten.")):
                return

            def work():
                msi = self._installer().download(config.PLAYIT_MSI_URL, "playit-windows-x86_64-signed.msi")
                self.log_threadsafe(_("Installiere playit.gg ..."))
                subprocess.run(["msiexec", "/i", str(msi)], check=False)
                if not cli.is_file():
                    raise RuntimeError(_("playit.gg wurde nicht installiert (abgebrochen?)."))
            self.background(work, done=self.playit)
            return

        status = self._playit_status()
        if status.get("phase") != "running":
            subprocess.run([str(cli), "start"], capture_output=True, timeout=30,
                           creationflags=subprocess.CREATE_NO_WINDOW)
            tray = cli.parent / "playitd-tray.exe"
            if tray.is_file():
                subprocess.Popen([str(tray)])
            status = self._playit_status()
        if status.get("secret configured") != "true":
            subprocess.Popen([str(cli), "setup"], creationflags=subprocess.CREATE_NEW_CONSOLE)
            messagebox.showinfo("playit.gg",
                                _("Einmalige Einrichtung: Im neuen Fenster den Link öffnen, kostenlos anmelden und "
                                  "den Agent bestätigen. Danach hier nochmal auf 'playit.gg' klicken."))
            return
        webbrowser.open(config.PLAYIT_TUNNELS_URL)
        current = self.s.get("public_address", "")
        addr = simpledialog.askstring(
            "playit.gg – Tunnel",
            _("Auf der geöffneten playit-Seite (einmalig):\n"
              "  1. 'Add Tunnel' / 'Create Tunnel'\n"
              "  2. Typ: TCP (kein Spiel auswählen)\n"
              "  3. Local Address 127.0.0.1, Local Port {port}\n"
            "  4. Speichern\n\n"
              "Dann die Tunnel-Adresse (z. B. abc.gl.at.ply.gg:12345) hier einfügen.\n"
              "Leer lassen = wieder deine eigene IP verwenden.").format(port=self.port),
            initialvalue=current, parent=self.root)
        if addr is None:
            return
        self.s["public_address"] = addr.strip()
        self.v_public.set(addr.strip())
        config.save_settings(self.s)
        if self.mode == "host":
            self._show_public_address()
        self._log(_("Adresse für Freunde: {address}").format(address=addr.strip()) if addr.strip()
                  else _("Adresse für Freunde: eigene IP"))

    # ================= updates =================
    def _check_update(self):
        def work():
            info = updates.latest()
            if info:
                self.call(self._show_update, info)
        threading.Thread(target=work, daemon=True).start()

    def _show_update(self, info):
        self.update_info = info
        self.b_update.configure(text=_("⬆  Update {version}").format(version=info["version"]))
        self.b_update.pack(side="right", padx=(0, 10), pady=6)
        self._log(_("Neue Version {version} verfügbar: {url}").format(version=info["version"], url=info["url"]))

    def install_update(self):
        info = self.update_info
        text = updates.notes_for(info["notes"], i18n.lang())
        notes = f"\n\n{text[:700]}" if text else ""
        # Private builds (own icon etc.) are built by hand; they only point to the release page.
        if not (config.is_public_build() and info["setup_url"]):
            if messagebox.askyesno("Update", _("Version {version} ist verfügbar.").format(version=info["version"])
                                   + notes + "\n\n" + _("Release-Seite im Browser öffnen?")):
                webbrowser.open(info["url"])
            return
        if self.server and self.server.running():
            messagebox.showinfo("Update", _("Erst den Server beenden – das Update schließt den Launcher."))
            return
        if not messagebox.askyesno("Update", _("Version {version} jetzt herunterladen und installieren?").format(
                                       version=info["version"]) + notes + "\n\n"
                                   + _("Der Launcher wird dafür geschlossen. Spiele und Spielstände bleiben erhalten.")):
            return
        dest = Path(tempfile.gettempdir()) / info["setup_name"]

        def work():
            self.log_threadsafe(_("Lade {name} herunter ...").format(name=info["setup_name"]))
            updates.download(info["setup_url"], dest,
                             lambda f: self.progress_threadsafe(f, f"Update {int(f * 100)} %"))

        def run():
            # The setup starts the new launcher at the end; it must not inherit this exe's PyInstaller state.
            subprocess.Popen([str(dest)], env={**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"})
            self.on_close(ask=False)
        self.background(work, done=run)

    # ================= teardown =================
    def stop_all(self):
        if self.mode == "host" and self.server and self.server.running():
            if not messagebox.askyesno(_("Beenden"), _("Server wirklich beenden? Der Spielstand bleibt gespeichert "
                                                        "und kann mit 'Spielstand fortsetzen' weitergespielt werden.")):
                return
        self._teardown()
        self.set_state(_("Nicht verbunden."))
        self.tree.delete(*self.tree.get_children())
        self._refresh_buttons()

    def _teardown(self):
        self.client_poll_stop.set()
        if self.overlay:
            self.overlay.close()
        if self.hint_dialog:
            self.hint_dialog.close()
        self.session_zip = None
        self.ap_connected = False
        self._set_friend_address("")
        if self.mode == "client" and self.v_addr.get().strip():
            addr, name, pw = self.v_addr.get().strip(), self.v_name.get().strip(), self.v_pw.get()
            threading.Thread(target=lobby.leave, args=(addr, name, pw), daemon=True).start()
        if self.watcher:
            self.watcher.stop()
            self.watcher = None
        if self.lobby:
            self.lobby.stop()
            self.lobby = None
        if self.server:
            self.server.stop()
            self.server = None
        self.mode = None

    def change_language(self):
        lang = next(k for k, v in i18n.LANGS.items() if v == self.v_lang.get())
        if lang == i18n.lang():
            return
        self.s["lang"] = lang
        self._save_fields()
        # Messages in the language just picked, since that is the one the user reads.
        de = lang == "de"
        if self.mode is not None:
            messagebox.showinfo("Sprache" if de else "Language",
                                "Die Sprache wechselt beim nächsten Start des Launchers." if de else
                                "The language changes the next time the launcher starts.")
            return
        if messagebox.askyesno("Sprache" if de else "Language",
                               "Launcher jetzt neu starten?" if de else "Restart the launcher now?"):
            self.on_close(ask=False)
            args = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, sys.argv[0]]
            # Without this the new exe would reuse this one's unpacked temp folder, which is deleted on exit
            # ("Failed to import encodings module").
            subprocess.Popen(args, env={**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"})

    def on_close(self, ask=True):
        if ask and self.server and self.server.running():
            if not messagebox.askyesno(_("Beenden"), _("Der Server läuft noch. Beenden? (Spielstand bleibt gespeichert)")):
                return
        self._save_fields()
        self._teardown()
        self.sail.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    App().run()
