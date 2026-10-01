"""Tkinter window tying install, lobby, server and games together."""
import os
import queue
import re
import subprocess
import threading
import tkinter as tk
import uuid
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from . import apclient, config, games, host, lobby, overlay, roms, theme, widgets
from .config import GAMES, NO_GAME, Paths
from .install import InstallError, Installer

POLL_MS = 100
LOBBY_POLL_S = 2


class App:
    def __init__(self):
        self.s = config.load_settings()
        self.s.setdefault("cid", uuid.uuid4().hex)
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
        theme.dark_titlebar(self.root)
        self.ap_connected = False
        self.friend_address = ""
        self.overlay: overlay.Overlay | None = None
        self.session_zip = None
        self._build()
        self._load_fields()
        widgets.fade_in(self.root)
        self.root.after(POLL_MS, self._drain)

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
        tk.Label(titles, text=f"Super Mario 64 · Ocarina of Time   ·   Version {config.APP_VERSION}",
                 bg=theme.BG, fg=theme.MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        self.pill = widgets.StatusPill(head)
        self.pill.pack(side="right", pady=6)

        self.tabs = widgets.TabBar(self.root, [("play", "🎮  Spielen"), ("setup", "⚙  Einrichtung"),
                                              ("net", "🌐  Netzwerk"), ("log", "📜  Log")], self._show_tab)
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
        conn = self._card(page, "Verbindung")
        row = ttk.Frame(conn, style="Card.TFrame")
        row.pack(fill="x")
        self.v_addr, self.v_pw = tk.StringVar(), tk.StringVar()
        box, _ = self._field(row, "Server-Adresse (vom Host)", self.v_addr, width=34)
        box.pack(side="left", padx=(0, 12))
        box, _ = self._field(row, "Passwort (optional)", self.v_pw, width=16, show="•")
        box.pack(side="left")

        self.actions = ttk.Frame(conn, style="Card.TFrame")
        self.actions.pack(fill="x", pady=(12, 0))
        mk = lambda text, cmd, kind="secondary": widgets.RoundButton(self.actions, text, cmd, kind)
        self.b_host = mk("🖥  Server hosten", self.host_start, "primary")
        self.b_join = mk("🔗  Beitreten", self.client_join, "primary")
        self.b_resume = mk("💾  Spielstand fortsetzen", self.host_resume)
        self.b_gen = mk("🚀  Multiworld starten", self.host_generate, "primary")
        self.b_play = widgets.RoundButton(self.actions, "▶  Spielen", self.play, "primary", height=40, size=11)
        self.b_overlay = mk("🗺  Overlay", self.toggle_overlay)
        self.b_stop = mk("Beenden", self.stop_all, "danger")

        info = ttk.Frame(conn, style="Card.TFrame")
        info.pack(fill="x", pady=(10, 0))
        self.l_state = ttk.Label(info, text="Nicht verbunden.", style="Card.TLabel")
        self.l_state.pack(side="left")
        self.l_addr = tk.Label(info, text="", bg=theme.PANEL, fg=theme.OK, cursor="hand2",
                               font=("Segoe UI Semibold", 10))
        self.l_addr.pack(side="right")
        self.l_addr.bind("<Button-1>", lambda e: self.copy_address())

        pc = self._card(page, "Spieler", fill="both", expand=True)
        cols = ("name", "game", "status", "progress")
        self.tree = ttk.Treeview(pc, columns=cols, show="headings", height=5)
        for c, t, w in zip(cols, ("Name", "Spiel", "Status", "Fortschritt"), (170, 260, 150, 140)):
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
        who = self._card(top, "Du", side="left", fill="y", pady=(0, 10), padx=(0, 10))
        self.v_name = tk.StringVar()
        box, _ = self._field(who, "Spielername (max. 16 Zeichen)", self.v_name, width=22)
        box.pack(anchor="w")

        gc = self._card(top, "Spiel", side="left", fill="x", expand=True)
        cards = ttk.Frame(gc, style="Card.TFrame")
        cards.pack(fill="x")
        self.game_labels = {**{k: g["label"] for k, g in GAMES.items()}, NO_GAME: "Kein Spiel (nur hosten)"}
        self.v_game = tk.StringVar()
        self.game_cards = {}
        for key, icon, title, sub in (("sm64", "⭐", "Super Mario 64", "sm64ex · 60 FPS"),
                                      ("soh", "🗡", "Ocarina of Time", "Ship of Harkinian"),
                                      (NO_GAME, "🖥", "Nur hosten", "kein eigenes Spiel")):
            card = widgets.GameCard(cards, icon, title, sub, lambda k=key: self._select_game(k))
            card.pack(side="left", padx=(0, 10), fill="x", expand=True)
            self.game_cards[key] = card

        rc = self._card(page, "ROM")
        row = ttk.Frame(rc, style="Card.TFrame")
        row.pack(fill="x")
        self.v_rom = tk.StringVar()
        self.e_rom = ttk.Entry(row, textvariable=self.v_rom)
        self.e_rom.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.b_rom = widgets.RoundButton(row, "Durchsuchen …", self.pick_rom, height=32)
        self.b_rom.pack(side="left")
        self.l_rom = tk.Label(rc, text="", bg=theme.PANEL, fg=theme.MUTED, font=("Segoe UI", 9))
        self.l_rom.pack(anchor="w", pady=(6, 0))

        ic = self._card(page, "Installation")
        row = ttk.Frame(ic, style="Card.TFrame")
        row.pack(fill="x")
        self.b_install = widgets.RoundButton(row, "⬇  Installieren / Prüfen", self.install, "primary")
        self.b_install.pack(side="left")
        self.l_inst = tk.Label(row, text="", bg=theme.PANEL, font=("Segoe UI Semibold", 10))
        self.l_inst.pack(side="left", padx=14)
        self.v_root = tk.StringVar()
        widgets.RoundButton(row, "Ändern …", self.pick_root, "ghost", height=32).pack(side="right")
        ttk.Entry(row, textvariable=self.v_root, width=24).pack(side="right", padx=8)
        ttk.Label(row, text="Ordner:", style="CardMuted.TLabel").pack(side="right")

        oc = self._card(page, "Optionen")
        row = ttk.Frame(oc, style="Card.TFrame")
        row.pack(fill="x")
        widgets.RoundButton(row, "📝  YAML bearbeiten", self.edit_yaml, height=32).pack(side="left", padx=(0, 8))
        widgets.RoundButton(row, "🧩  Options Creator", self.options_creator, height=32).pack(side="left", padx=(0, 8))
        widgets.RoundButton(row, "📂  Ordner öffnen", lambda: self._open(self.paths.root), "ghost",
                            height=32).pack(side="left")
        self.game_opts = ttk.Frame(oc, style="Card.TFrame")
        self.game_opts.pack(fill="x", pady=(10, 0))
        self.v_invert = tk.BooleanVar()
        self.c_invert = ttk.Checkbutton(self.game_opts, text="Kamera links/rechts tauschen (Mario 64)",
                                        variable=self.v_invert, command=self._save_fields, style="Card.TCheckbutton")
        self.b_mods = widgets.RoundButton(self.game_opts, "🎨  SoH Mods / Texturen", self.open_soh_mods, height=32)

    def _build_net(self, page):
        ac = self._card(page, "Adresse für Freunde")
        self.l_addr_net = tk.Label(ac, text="", bg=theme.PANEL, fg=theme.OK, font=("Segoe UI Semibold", 12),
                                   cursor="hand2")
        self.l_addr_net.pack(anchor="w")
        self.l_addr_net.bind("<Button-1>", lambda e: self.copy_address())
        ttk.Label(ac, text="Wird beim Hosten angezeigt. Anklicken kopiert sie. Eigene Adresse (z. B. Radmin-, "
                           "Hamachi- oder playit-Adresse) hier festlegen, leer = Internet-IP:",
                  style="CardMuted.TLabel", wraplength=860).pack(anchor="w", pady=(6, 4))
        row = ttk.Frame(ac, style="Card.TFrame")
        row.pack(fill="x")
        self.v_public = tk.StringVar()
        ttk.Entry(row, textvariable=self.v_public, width=34).pack(side="left")
        widgets.RoundButton(row, "Speichern", self.save_public_address, height=32).pack(side="left", padx=8)
        self.vpn_box = ttk.Frame(row, style="Card.TFrame")
        self.vpn_box.pack(side="left")

        pc = self._card(page, "Erreichbarkeit")
        row = ttk.Frame(pc, style="Card.TFrame")
        row.pack(fill="x")
        self.v_port = tk.StringVar()
        box, _ = self._field(row, "Port", self.v_port, width=8)
        box.pack(side="left", padx=(0, 12))
        widgets.RoundButton(row, "📡  Port testen", self.port_test, height=32).pack(side="left", anchor="s")
        widgets.RoundButton(row, "🌍  playit.gg einrichten", self.playit, height=32).pack(side="left", padx=8,
                                                                                       anchor="s")
        ttk.Label(pc, text="Ohne Portfreigabe im Router: alle nutzen Radmin VPN / Hamachi (Host-Adresse aus dem "
                           "VPN-Programm) oder der Host richtet playit.gg ein.",
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
        self.v_invert.set(bool(self.s.get("sm64_invert_camera_x")))
        self.v_public.set(self.s.get("public_address", ""))
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
                      sm64_invert_camera_x=self.v_invert.get())
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
        self.c_invert.pack_forget()
        self.b_mods.pack_forget()
        if g == "sm64":
            self.c_invert.pack(anchor="w")
        elif g == "soh":
            self.b_mods.pack(anchor="w")
        self._check_rom()
        self._update_install_label()
        self._refresh_buttons()

    def _check_rom(self):
        g = self.game
        if g not in GAMES:
            self.l_rom.configure(text="Keine ROM nötig.", foreground=theme.MUTED)
            return
        path = self.v_rom.get().strip()
        if not path:
            self.l_rom.configure(text="Bitte die eigene ROM auswählen (.z64/.n64/.v64).", foreground=theme.MUTED)
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
        self.l_inst.configure(text="✓ installiert" if ok else "● noch nicht installiert",
                              foreground=theme.OK if ok else theme.WARN)

    def _refresh_buttons(self):
        """Only the buttons that make sense right now are shown."""
        connected = self.ap_connected
        lobby_open = self.mode == "host" and self.lobby is not None and self.lobby.state == "lobby"
        if self.mode is None:
            visible = [self.b_host, self.b_join, self.b_resume]
            pill = ("busy", "Arbeitet …") if self.busy else ("offline", "Offline")
        elif lobby_open:
            visible = [self.b_gen, self.b_stop]
            pill = ("lobby", f"Lobby · {len(self.lobby.players)} Spieler")
        elif connected:
            visible = ([self.b_play, self.b_overlay] if self.game in GAMES else []) + [self.b_stop]
            pill = ("connected", "Verbunden")
        else:
            visible = [self.b_stop]
            pill = ("busy", "Lobby" if self.mode == "client" else "Startet …")
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
            self._log(f"FEHLER: {err}")
            messagebox.showerror("Fehler", str(err))
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
        path = filedialog.askopenfilename(title="ROM auswählen",
                                          filetypes=[("N64 ROM", "*.z64 *.n64 *.v64"), ("Alle Dateien", "*.*")])
        if path:
            self.v_rom.set(path)
            self._check_rom()
            self._save_fields()

    def pick_root(self):
        path = filedialog.askdirectory(title="Installationsordner (ohne Leerzeichen)")
        if path:
            if " " in path:
                messagebox.showerror("Ordner", "Der Ordner darf keine Leerzeichen enthalten (wegen MSYS2/make).")
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
                messagebox.showerror("ROM", text)
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
            self.log_threadsafe("Installation abgeschlossen.")
        self.background(work)

    def edit_yaml(self):
        g = self.game
        if g not in GAMES:
            messagebox.showinfo("Optionen", "Ohne eigenes Spiel gibt es keine Optionen.")
            return
        path = self.paths.yaml_for(g)
        if not path.is_file():
            messagebox.showinfo("Optionen", "Bitte erst 'Installieren / Prüfen' ausführen.")
            return
        os.startfile(path)

    def options_creator(self):
        exe = self.paths.ap / "ArchipelagoOptionsCreator.exe"
        if not exe.is_file():
            messagebox.showinfo("Options Creator", "Bitte erst 'Installieren / Prüfen' ausführen.")
            return
        subprocess.Popen([str(exe)], cwd=self.paths.ap)
        self._log(f"Options Creator gestartet. Die fertige YAML als {self.paths.yaml_for(self.game)} speichern.")

    def open_soh_mods(self):
        """SoH loads texture packs (.o2r/.otr) from the mods folder next to soh.exe."""
        if not self.paths.soh_exe.is_file():
            messagebox.showinfo("SoH Mods", "Ship of Harkinian ist noch nicht installiert. "
                                            "Erst OoT wählen und 'Installieren / Prüfen'.")
            return
        self._open(self.paths.soh / "mods")
        self._log("Texturpakete (.o2r/.otr) in den mods-Ordner legen. In SoH unter "
                  "Einstellungen → Mods bzw. 'Alternative Assets' (Taste Tab) aktivieren.")

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
                return "Dein Spiel ist noch nicht installiert. Erst 'Installieren / Prüfen'."
            if self._my_yaml() is None:
                return "Options-YAML fehlt. Erst 'Installieren / Prüfen'."
        return None

    # ================= hosting =================
    def host_start(self):
        self._save_fields()
        if not self._installer().archipelago_ok():
            messagebox.showerror("Host", "Archipelago ist noch nicht installiert. Erst 'Installieren / Prüfen'.")
            return
        plays = self.game in GAMES
        if plays:
            err = self._ready_to_play()
            if err:
                messagebox.showerror("Host", err)
                return
        try:
            self.lobby = lobby.Lobby(self.port, self.v_pw.get())
            self.lobby.start()
        except OSError as e:
            self.lobby = None
            messagebox.showerror("Host", f"Port {self.port} kann nicht geöffnet werden: {e}")
            return
        self.lobby.on_change = lambda: self.call(self._host_lobby_changed)
        if plays:
            self.lobby.add_player(self.v_name.get().strip(), self.game, self._my_yaml(), local=True)
        self.mode = "host"
        self.v_addr.set(f"localhost:{self.port}")
        self._log(f"Lobby offen auf Port {self.port}. Freunde tragen deine Adresse ein und klicken 'Beitreten'.")
        self.set_state("Lobby offen – warte auf Spieler. Dann 'Multiworld starten'.")
        self._show_public_address()
        self._host_lobby_changed()
        self._host_lobby_tick()

    def _show_public_address(self):
        if self.s.get("public_address"):
            self._set_friend_address(self.s["public_address"])
            return

        def work():
            ip = host.public_ip()
            self.call(self._set_friend_address, f"{ip}:{self.port}" if ip else "")
        threading.Thread(target=work, daemon=True).start()

    def _set_friend_address(self, address):
        self.friend_address = address
        self.l_addr.configure(text=f"📋  Für Freunde: {address}" if address else "")
        self.l_addr_net.configure(text=f"📋  {address}" if address else "– erst beim Hosten –",
                                  fg=theme.OK if address else theme.MUTED)

    def copy_address(self):
        if not self.friend_address:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.friend_address)
        self.toast.show(f"✓ Adresse kopiert: {self.friend_address}")

    def save_public_address(self):
        self.s["public_address"] = self.v_public.get().strip()
        config.save_settings(self.s)
        if self.mode == "host":
            self._show_public_address()
        self.toast.show("✓ Gespeichert" if self.s["public_address"] else "✓ Es wird wieder deine Internet-IP verwendet")

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

    def _show_vpn(self, found):
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
            status = ("bereit" if p["ready"] else "beigetreten") if p["online"] else "offline"
            self.tree.insert("", "end", values=(p["name"], GAMES[p["game"]]["label"], status, "-"),
                             tags=("me",) if p["name"] == me else ())

    def host_generate(self):
        lob = self.lobby
        yamls = lob.yamls()
        if not yamls:
            messagebox.showerror("Host", "Noch keine Spieler in der Lobby.")
            return
        if not messagebox.askyesno("Multiworld", f"Multiworld mit {len(yamls)} Spieler(n) erstellen und Server starten?\n"
                                                 "Danach kann niemand mehr beitreten."):
            return
        lob.set_state("generating", "Multiworld wird erstellt ...")
        self.set_state("Multiworld wird generiert ...")
        paths, port, pw = self.paths, self.port, self.v_pw.get()
        result = {}

        def work():
            try:
                result["zip"] = host.generate(paths, yamls, self.log_threadsafe)
            except Exception:
                lob.set_state("lobby", "")
                self.call(self._host_lobby_tick)
                raise
            lob.set_state("starting", "Server startet ...")
            import time
            time.sleep(LOBBY_POLL_S + 1.5)  # let clients see "starting" before the lobby goes away
            lob.stop()
            self._start_server(paths, result["zip"], port, pw)
        self.background(work, done=lambda: self._host_running(result["zip"]))

    def host_resume(self):
        self._save_fields()
        sessions = host.list_sessions(self.paths)
        if not sessions:
            messagebox.showinfo("Fortsetzen", "Keine gespeicherten Multiworlds gefunden.")
            return
        win = tk.Toplevel(self.root)
        win.title("Spielstand fortsetzen")
        win.configure(bg=theme.BG)
        # Tied to the launcher and modal, so it can never end up hidden behind it.
        win.transient(self.root)
        self.root.update_idletasks()
        w, h = 640, 340
        x = self.root.winfo_rootx() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - h) // 3
        win.geometry(f"{w}x{h}+{x}+{y}")
        theme.dark_titlebar(win)
        tk.Label(win, text="Welche Multiworld möchtest du fortsetzen?", bg=theme.BG, fg=theme.FG,
                 font=("Segoe UI Semibold", 11)).pack(anchor="w", padx=14, pady=(12, 0))
        tk.Label(win, text="Doppelklick oder Enter startet den Server mit diesem Spielstand.", bg=theme.BG,
                 fg=theme.MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=14)
        lb = tk.Listbox(win, font=("Segoe UI", 11), activestyle="none", exportselection=False)
        theme.style_text(lb)
        lb.pack(fill="both", expand=True, padx=14, pady=10)
        for z in sessions:
            stamp = z.parent.name  # YYYY-MM-DD_HH-MM-SS
            try:
                d, t = stamp.split("_")
                stamp = f"{d[8:10]}.{d[5:7]}.{d[0:4]}  {t[0:2]}:{t[3:5]}"
            except (ValueError, IndexError):
                pass
            lb.insert("end", f"  {stamp}    –    {', '.join(host.session_players(z))}")
        lb.selection_set(0)
        lb.activate(0)

        def go():
            sel = lb.curselection()
            if not sel:
                return
            z = sessions[sel[0]]
            win.destroy()
            self.mode = "host"
            paths, port, pw = self.paths, self.port, self.v_pw.get()
            self.v_addr.set(f"localhost:{port}")
            self._show_public_address()
            self.background(lambda: self._start_server(paths, z, port, pw), done=lambda: self._host_running(z))
        widgets.RoundButton(win, "▶  Diesen Spielstand starten", go, "primary", bg=theme.BG).pack(pady=(0, 12))
        lb.bind("<Double-Button-1>", lambda e: go())
        win.bind("<Return>", lambda e: go())
        win.bind("<Escape>", lambda e: win.destroy())
        widgets.fade_in(win, 180)
        win.lift()
        win.grab_set()
        lb.focus_set()

    def _start_server(self, paths, zip_path, port, pw):
        self.server = host.Server(paths, zip_path, port, pw, self.log_threadsafe)
        self.server.start()
        self.log_threadsafe("Archipelago-Server gestartet.")

    def _host_running(self, zip_path):
        self.lobby = None
        self.session_zip = zip_path
        self.set_state("Server läuft. Alle können jetzt '▶ Spielen' drücken.")
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
            err = "Zum Beitreten bitte ein Spiel auswählen."
        if err:
            messagebox.showerror("Beitreten", err)
            return
        addr, name, pw = self.v_addr.get().strip(), self.v_name.get().strip(), self.v_pw.get()
        g, yaml_text, cid = self.game, self._my_yaml(), self.s["cid"]
        result = {}

        def work():
            try:
                result["snap"] = lobby.join(addr, name, g, yaml_text, cid, pw)
            except lobby.LobbyError as e:
                if e.unreachable:
                    raise RuntimeError(
                        f"Der Host ist unter {addr} nicht erreichbar.\n\n"
                        "• Stimmt die Adresse (mit :Port)?\n"
                        "• Hat der Host 'Server hosten' geklickt?\n"
                        "• Beim Host fehlt evtl. die Portfreigabe im Router – dann playit.gg nutzen "
                        "und dessen Adresse eintragen.")
                # Something answered but it is not a lobby: probably the game already runs there.
                result["error"] = str(e)
        self.background(work, done=lambda: self._joined(result, addr, name))

    def _joined(self, result, addr, name):
        self.mode = "client"
        if "snap" in result:
            self._log(f"Lobby beigetreten als {name}.")
            self.set_state("In der Lobby – warte, bis der Host die Multiworld startet.")
            self._show_lobby_players(result["snap"])
            self.client_poll_stop.clear()
            threading.Thread(target=self._client_poll, args=(addr, name), daemon=True).start()
        else:
            self._log("Beim Host ist keine Lobby offen – dort läuft vermutlich schon eine Multiworld. "
                      "Verbinde mit dem laufenden Spiel ...")
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
                    self.call(self.set_state, snap.get("message") or "Multiworld wird erstellt ...")
                elif snap["state"] == "lobby":
                    self.call(self.set_state, "In der Lobby – warte, bis der Host die Multiworld startet.")
            except lobby.LobbyError as e:
                failures += 1
                if seen_starting or failures >= 3:
                    # Lobby is gone: the Archipelago server should be up now.
                    self.call(self._start_watcher, addr, name)
                    return
                self.call(self.set_state, f"Lobby nicht erreichbar: {e}")
            time.sleep(LOBBY_POLL_S)

    # ================= in game =================
    def _start_watcher(self, addr, slot):
        if self.watcher:
            self.watcher.stop()
        self.set_state("Verbinde mit dem Archipelago-Server ...")
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
                self.set_state("Verbunden. Server läuft – '▶ Spielen' drücken.")
            else:
                self.set_state(data["text"])
            self._refresh_buttons()
        elif kind == "error":
            self.set_state(f"Fehler: {data}")
            messagebox.showerror("Archipelago", data)

    def play(self):
        self._save_fields()
        err = self._ready_to_play()
        if err:
            messagebox.showerror("Spiel starten", err)
            return
        addr = f"localhost:{self.port}" if self.mode == "host" else self.v_addr.get().strip()
        name, pw = self.v_name.get().strip(), self.v_pw.get()
        try:
            if self.game == "sm64":
                region = self._installer().sm64_region_built()
                games.launch_sm64(self.paths, region, addr, name, pw, self.v_invert.get())
                self._log("Super Mario 64 gestartet (verbindet sich automatisch).")
            elif self.game == "soh":
                games.launch_soh(self.paths, addr, name, pw)
                self._log("Ship of Harkinian gestartet. Im Dateiauswahl-Menü 'Archipelago' wählen; "
                          "Server, Name und Passwort sind schon eingetragen.")
        except (games.GameError, OSError) as e:
            messagebox.showerror("Spiel starten", str(e))

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
            messagebox.showinfo("Overlay", "Bitte einmal 'Installieren / Prüfen' klicken (Overlay-Logik fehlt noch).")
            return
        inst.write_bridge_world()
        self.overlay = overlay.Overlay(self.root, self.paths, addr, name, pw, yaml_dir,
                                       on_close=self._overlay_closed)
        self._log("Overlay geöffnet. Es zeigt dein Ziel und was du gerade erreichen kannst.")

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
        self._log(f"Teste, ob Port {port} aus dem Internet erreichbar ist ...")

        def work():
            ok = host.port_reachable(port)
            if temp:
                temp.stop()
            if ok is None:
                msg = "Port-Test konnte nicht durchgeführt werden (Testdienst nicht erreichbar)."
            elif ok:
                msg = f"✓ Port {port} ist von außen erreichbar. Freunde können direkt beitreten."
            else:
                msg = (f"✗ Port {port} ist von außen NICHT erreichbar.\n"
                       f"Lösung: Im Router Port {port} (TCP) auf diesen PC weiterleiten und in der Windows-Firewall "
                       f"erlauben – oder playit.gg benutzen.")
            self.call(self._log, msg)
            self.call(self.toast.show, msg.splitlines()[0], theme.OK if ok else theme.WARN, 4000)
            if not ok:
                self.call(messagebox.showinfo, "Port-Test", msg)
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
            if not messagebox.askyesno("playit.gg", "playit.gg ist noch nicht installiert.\n\n"
                                                    "Jetzt das offizielle Installationspaket laden (ca. 6 MB) und "
                                                    "installieren? Windows fragt dabei nach Admin-Rechten."):
                return

            def work():
                msi = self._installer().download(config.PLAYIT_MSI_URL, "playit-windows-x86_64-signed.msi")
                self.log_threadsafe("Installiere playit.gg ...")
                subprocess.run(["msiexec", "/i", str(msi)], check=False)
                if not cli.is_file():
                    raise RuntimeError("playit.gg wurde nicht installiert (abgebrochen?).")
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
                                "Einmalige Einrichtung: Im neuen Fenster den Link öffnen, kostenlos anmelden und "
                                "den Agent bestätigen. Danach hier nochmal auf 'playit.gg' klicken.")
            return
        webbrowser.open(config.PLAYIT_TUNNELS_URL)
        current = self.s.get("public_address", "")
        addr = simpledialog.askstring(
            "playit.gg – Tunnel",
            "Auf der geöffneten playit-Seite (einmalig):\n"
            "  1. 'Add Tunnel' / 'Create Tunnel'\n"
            "  2. Typ: TCP (kein Spiel auswählen)\n"
            f"  3. Local Address 127.0.0.1, Local Port {self.port}\n"
            "  4. Speichern\n\n"
            "Dann die Tunnel-Adresse (z. B. abc.gl.at.ply.gg:12345) hier einfügen.\n"
            "Leer lassen = wieder deine eigene IP verwenden.",
            initialvalue=current, parent=self.root)
        if addr is None:
            return
        self.s["public_address"] = addr.strip()
        self.v_public.set(addr.strip())
        config.save_settings(self.s)
        if self.mode == "host":
            self._show_public_address()
        self._log(f"Adresse für Freunde: {addr.strip()}" if addr.strip() else "Adresse für Freunde: eigene IP")

    # ================= teardown =================
    def stop_all(self):
        if self.mode == "host" and self.server and self.server.running():
            if not messagebox.askyesno("Beenden", "Server wirklich beenden? Der Spielstand bleibt gespeichert "
                                                  "und kann mit 'Spielstand fortsetzen' weitergespielt werden."):
                return
        self._teardown()
        self.set_state("Nicht verbunden.")
        self.tree.delete(*self.tree.get_children())
        self._refresh_buttons()

    def _teardown(self):
        self.client_poll_stop.set()
        if self.overlay:
            self.overlay.close()
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

    def on_close(self):
        if self.server and self.server.running():
            if not messagebox.askyesno("Beenden", "Der Server läuft noch. Beenden? (Spielstand bleibt gespeichert)"):
                return
        self._save_fields()
        self._teardown()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    App().run()
