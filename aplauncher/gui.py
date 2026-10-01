"""Tkinter window tying install, lobby, server and games together."""
import os
import queue
import subprocess
import threading
import tkinter as tk
import uuid
import webbrowser
from tkinter import filedialog, messagebox, ttk

from . import apclient, config, games, host, lobby, roms
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
        self.root.geometry("980x760")
        self.root.minsize(820, 620)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._build()
        self._load_fields()
        self.root.after(POLL_MS, self._drain)

    # ================= layout =================
    def _build(self):
        pad = {"padx": 6, "pady": 3}
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="both", expand=True)

        me = ttk.LabelFrame(top, text="1. Mein Spiel", padding=8)
        me.pack(fill="x")
        ttk.Label(me, text="Spielername:").grid(row=0, column=0, sticky="w", **pad)
        self.v_name = tk.StringVar()
        ttk.Entry(me, textvariable=self.v_name, width=20).grid(row=0, column=1, sticky="w", **pad)
        ttk.Label(me, text="Spiel:").grid(row=0, column=2, sticky="e", **pad)
        self.game_labels = {**{k: g["label"] for k, g in GAMES.items()}, NO_GAME: "Kein Spiel (nur hosten)"}
        self.v_game = tk.StringVar()
        cb = ttk.Combobox(me, textvariable=self.v_game, values=list(self.game_labels.values()),
                          state="readonly", width=36)
        cb.grid(row=0, column=3, columnspan=2, sticky="w", **pad)
        cb.bind("<<ComboboxSelected>>", lambda e: self._game_changed())

        ttk.Label(me, text="ROM:").grid(row=1, column=0, sticky="w", **pad)
        self.v_rom = tk.StringVar()
        self.e_rom = ttk.Entry(me, textvariable=self.v_rom, width=70)
        self.e_rom.grid(row=1, column=1, columnspan=3, sticky="we", **pad)
        self.b_rom = ttk.Button(me, text="Durchsuchen ...", command=self.pick_rom)
        self.b_rom.grid(row=1, column=4, sticky="w", **pad)
        self.l_rom = ttk.Label(me, text="", foreground="gray")
        self.l_rom.grid(row=2, column=1, columnspan=4, sticky="w", padx=6)

        ttk.Label(me, text="Installationsordner:").grid(row=3, column=0, sticky="w", **pad)
        self.v_root = tk.StringVar()
        ttk.Entry(me, textvariable=self.v_root, width=40).grid(row=3, column=1, columnspan=2, sticky="we", **pad)
        ttk.Button(me, text="Ändern ...", command=self.pick_root).grid(row=3, column=3, sticky="w", **pad)

        row = ttk.Frame(me)
        row.grid(row=4, column=0, columnspan=5, sticky="we", pady=(6, 0))
        self.b_install = ttk.Button(row, text="Installieren / Prüfen", command=self.install)
        self.b_install.pack(side="left", padx=6)
        ttk.Button(row, text="Optionen bearbeiten (YAML)", command=self.edit_yaml).pack(side="left", padx=6)
        ttk.Button(row, text="Options Creator", command=self.options_creator).pack(side="left", padx=6)
        ttk.Button(row, text="Ordner öffnen", command=lambda: self._open(self.paths.root)).pack(side="left", padx=6)
        self.l_inst = ttk.Label(row, text="")
        self.l_inst.pack(side="left", padx=12)
        me.columnconfigure(3, weight=1)

        mw = ttk.LabelFrame(top, text="2. Multiworld", padding=8)
        mw.pack(fill="x", pady=(8, 0))
        ttk.Label(mw, text="Server-Adresse:").grid(row=0, column=0, sticky="w", **pad)
        self.v_addr = tk.StringVar()
        ttk.Entry(mw, textvariable=self.v_addr, width=30).grid(row=0, column=1, sticky="w", **pad)
        ttk.Label(mw, text="Passwort (optional):").grid(row=0, column=2, sticky="e", **pad)
        self.v_pw = tk.StringVar()
        ttk.Entry(mw, textvariable=self.v_pw, width=16, show="*").grid(row=0, column=3, sticky="w", **pad)
        ttk.Label(mw, text="Port:").grid(row=0, column=4, sticky="e", **pad)
        self.v_port = tk.StringVar()
        ttk.Entry(mw, textvariable=self.v_port, width=7).grid(row=0, column=5, sticky="w", **pad)

        btns = ttk.Frame(mw)
        btns.grid(row=1, column=0, columnspan=6, sticky="we", pady=(6, 0))
        self.b_host = ttk.Button(btns, text="Server hosten", command=self.host_start)
        self.b_join = ttk.Button(btns, text="Beitreten", command=self.client_join)
        self.b_gen = ttk.Button(btns, text="Multiworld generieren & starten", command=self.host_generate)
        self.b_resume = ttk.Button(btns, text="Spielstand fortsetzen ...", command=self.host_resume)
        self.b_play = ttk.Button(btns, text="▶ Spiel starten", command=self.play)
        self.b_stop = ttk.Button(btns, text="Beenden / Verlassen", command=self.stop_all)
        for b in (self.b_host, self.b_join, self.b_gen, self.b_resume, self.b_play, self.b_stop):
            b.pack(side="left", padx=4)
        net = ttk.Frame(mw)
        net.grid(row=2, column=0, columnspan=6, sticky="we", pady=(4, 0))
        ttk.Button(net, text="Port testen", command=self.port_test).pack(side="left", padx=4)
        ttk.Button(net, text="playit.gg (ohne Portfreigabe)", command=self.playit).pack(side="left", padx=4)
        self.l_addr = ttk.Label(net, text="", foreground="#0a5")
        self.l_addr.pack(side="left", padx=10)
        self.l_state = ttk.Label(mw, text="Nicht verbunden.", font=("Segoe UI", 10, "bold"))
        self.l_state.grid(row=3, column=0, columnspan=6, sticky="w", padx=6, pady=(6, 0))

        pane = ttk.PanedWindow(top, orient="vertical")
        pane.pack(fill="both", expand=True, pady=(8, 0))
        pf = ttk.LabelFrame(pane, text="Spieler", padding=4)
        cols = ("name", "game", "status", "progress")
        self.tree = ttk.Treeview(pf, columns=cols, show="headings", height=6)
        for c, t, w in zip(cols, ("Name", "Spiel", "Status", "Fortschritt"), (160, 260, 160, 140)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="w")
        self.tree.tag_configure("me", font=("Segoe UI", 9, "bold"))
        self.tree.pack(fill="both", expand=True)
        pane.add(pf, weight=1)

        lf = ttk.LabelFrame(pane, text="Log", padding=4)
        self.log_box = tk.Text(lf, height=12, wrap="word", state="disabled", font=("Consolas", 9))
        sb = ttk.Scrollbar(lf, command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_box.pack(fill="both", expand=True)
        pane.add(lf, weight=2)

        bottom = ttk.Frame(top)
        bottom.pack(fill="x", pady=(6, 0))
        self.pb = ttk.Progressbar(bottom, mode="determinate", maximum=1.0)
        self.pb.pack(side="left", fill="x", expand=True)
        self.l_prog = ttk.Label(bottom, text="", width=45)
        self.l_prog.pack(side="left", padx=6)

    # ================= settings / fields =================
    @property
    def paths(self) -> Paths:
        return Paths(self.v_root.get().strip() or config.DEFAULT_ROOT)

    @property
    def game(self) -> str:
        label = self.v_game.get()
        return next((k for k, v in self.game_labels.items() if v == label), NO_GAME)

    @property
    def port(self) -> int:
        try:
            return int(self.v_port.get())
        except ValueError:
            return config.DEFAULT_PORT

    def _load_fields(self):
        self.v_name.set(self.s["name"])
        self.v_game.set(self.game_labels.get(self.s["game"], self.game_labels["sm64"]))
        self.v_root.set(self.s["root"])
        self.v_addr.set(self.s["address"])
        self.v_pw.set(self.s["password"])
        self.v_port.set(str(self.s.get("port", config.DEFAULT_PORT)))
        self._game_changed()
        self._refresh_buttons()

    def _save_fields(self):
        if self.game in GAMES:
            self.s["roms"][self.game] = self.v_rom.get().strip()
        self.s.update(name=self.v_name.get().strip(), game=self.game, root=self.v_root.get().strip(),
                      address=self.v_addr.get().strip(), password=self.v_pw.get(), port=self.port)
        config.save_settings(self.s)

    def _game_changed(self):
        g = self.game
        state = "normal" if g in GAMES else "disabled"
        self.e_rom.configure(state=state)
        self.b_rom.configure(state=state)
        self.v_rom.set(self.s["roms"].get(g, "") if g in GAMES else "")
        self._check_rom()
        self._update_install_label()

    def _check_rom(self):
        g = self.game
        if g not in GAMES:
            self.l_rom.configure(text="Keine ROM nötig.", foreground="gray")
            return
        path = self.v_rom.get().strip()
        if not path:
            self.l_rom.configure(text="Bitte die eigene ROM auswählen (.z64/.n64/.v64).", foreground="gray")
            return
        ok, text = roms.describe(g, path)
        self.l_rom.configure(text=("✓ " if ok else "✗ ") + text, foreground="#0a5" if ok else "#c00")

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
        self.l_inst.configure(text="✓ installiert" if ok else "noch nicht installiert",
                              foreground="#0a5" if ok else "#c60")

    def _refresh_buttons(self):
        idle = self.mode is None
        self.b_host.configure(state="normal" if idle and not self.busy else "disabled")
        self.b_join.configure(state="normal" if idle and not self.busy else "disabled")
        self.b_resume.configure(state="normal" if idle and not self.busy else "disabled")
        lobby_open = self.mode == "host" and self.lobby is not None and self.lobby.state == "lobby"
        self.b_gen.configure(state="normal" if lobby_open and not self.busy else "disabled")
        self.b_stop.configure(state="disabled" if idle else "normal")
        self.b_play.configure(state="normal" if self.game in GAMES else "disabled")
        self.b_install.configure(state="disabled" if self.busy else "normal")

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
        self.set_state("Lobby offen – warte auf Spieler. Dann 'Multiworld generieren & starten'.")
        self._show_public_address()
        self._host_lobby_changed()
        self._host_lobby_tick()

    def _show_public_address(self):
        def work():
            ip = host.public_ip()
            self.call(self.l_addr.configure,
                      {"text": f"Adresse für Freunde: {ip}:{self.port}" if ip else "Öffentliche IP unbekannt"})
        threading.Thread(target=work, daemon=True).start()

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
        win.geometry("620x300")
        lb = tk.Listbox(win)
        lb.pack(fill="both", expand=True, padx=8, pady=8)
        for z in sessions:
            lb.insert("end", f"{z.parent.name}   –   {', '.join(host.session_players(z))}")
        lb.selection_set(0)

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
        ttk.Button(win, text="Diesen Spielstand starten", command=go).pack(pady=(0, 8))

    def _start_server(self, paths, zip_path, port, pw):
        self.server = host.Server(paths, zip_path, port, pw, self.log_threadsafe)
        self.server.start()
        self.log_threadsafe("Archipelago-Server gestartet.")

    def _host_running(self, zip_path):
        self.lobby = None
        self.set_state("Server läuft. Alle können jetzt '▶ Spiel starten' drücken.")
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
                # No lobby: maybe the game is already running on that address.
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
            self._log(f"Keine Lobby ({result['error']}). Versuche direkt mit dem Archipelago-Server zu verbinden ...")
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
        elif kind == "players":
            self.tree.delete(*self.tree.get_children())
            for r in data:
                self.tree.insert("", "end", values=(r["name"], r["game"], r["status"], r["progress"]),
                                 tags=("me",) if r["me"] else ())
        elif kind == "state":
            if data["connected"]:
                self.set_state("Verbunden. Server läuft – '▶ Spiel starten' drücken.")
            else:
                self.set_state(data["text"])
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
                games.launch_sm64(self.paths, region, addr, name, pw)
                self._log("Super Mario 64 gestartet (verbindet sich automatisch).")
            elif self.game == "soh":
                games.launch_soh(self.paths, addr, name, pw)
                self._log("Ship of Harkinian gestartet. Im Dateiauswahl-Menü 'Archipelago' wählen; "
                          "Server, Name und Passwort sind schon eingetragen.")
        except (games.GameError, OSError) as e:
            messagebox.showerror("Spiel starten", str(e))

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
            self.call(messagebox.showinfo, "Port-Test", msg)
        threading.Thread(target=work, daemon=True).start()

    def playit(self):
        exe = self.paths.root / "playit.exe"
        if not exe.is_file():
            if not messagebox.askyesno("playit.gg", "playit.gg herunterladen (ca. 10 MB) und starten?\n"
                                                    "Damit brauchst du keine Portfreigabe im Router."):
                return

            def work():
                path = self._installer().download(config.PLAYIT_URL, "playit.exe")
                if path != exe:
                    import shutil
                    shutil.copyfile(path, exe)
            self.background(work, done=self.playit)
            return
        subprocess.Popen([str(exe)], cwd=exe.parent, creationflags=subprocess.CREATE_NEW_CONSOLE)
        messagebox.showinfo("playit.gg",
                            "playit.gg läuft im neuen Fenster.\n\n"
                            "1. Den angezeigten Link öffnen und kostenlos anmelden.\n"
                            f"2. Einen Tunnel anlegen: Typ 'TCP', lokaler Port {self.port}.\n"
                            "3. Die Tunnel-Adresse (z. B. xyz.gl.joinmc.link:12345) an deine Freunde schicken –\n"
                            "   die tragen sie als Server-Adresse ein.")

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
