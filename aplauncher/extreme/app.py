"""Extreme interface on top of the shared launcher logic (gui.App): same buttons and fields, drawn on one canvas,
and the launcher builds itself up visibly at start."""
import ctypes
import threading
import tkinter as tk
import winsound
from tkinter import ttk

from .. import anim, config, dialogs, i18n, roms, theme
from ..config import GAMES, NO_GAME
from ..gui import App
from ..i18n import _
from ..install import Installer
from . import look
from .fx import Banner, BootConsole, Emblem, ScanLine, Toast
from .items import Button, Choice, Embed, Panel, Pill, Progress, Tabs, Text, Toggle
from .scene import Scene, Timeline
from .sound import Sounds

M = 24          # outer margin
TOP = 138       # pages start here
FOOT = 44       # footer height
BOOT_GAP = 170  # ms between two boot lines


def _styles(root):
    s = ttk.Style(root)
    s.configure("X.TEntry", fieldbackground=look.FIELD, foreground=look.FG, bordercolor=look.WIRE,
                lightcolor=look.FIELD, darkcolor=look.FIELD, insertcolor=look.FG, padding=(5, 3))
    s.map("X.TEntry", bordercolor=[("focus", look.ACCENT)], lightcolor=[("focus", look.FIELD)],
          fieldbackground=[("disabled", "#140e22")], foreground=[("disabled", theme.DISABLED)])
    s.configure("X.TCombobox", fieldbackground=look.FIELD, background="#1a1230", foreground=look.FG,
                arrowcolor=look.FG, bordercolor=look.WIRE, lightcolor=look.FIELD, darkcolor=look.FIELD, padding=(5, 3))
    s.map("X.TCombobox", fieldbackground=[("readonly", look.FIELD)], foreground=[("readonly", look.FG)],
          selectbackground=[("readonly", look.FIELD)], selectforeground=[("readonly", look.FG)],
          bordercolor=[("focus", look.ACCENT)], background=[("active", "#2b1e4e")])
    s.configure("X.Treeview", background=look.FIELD, fieldbackground=look.FIELD, foreground=look.FG,
                bordercolor=look.WIRE, lightcolor=look.FIELD, darkcolor=look.FIELD, rowheight=26)
    s.map("X.Treeview", background=[("selected", "#3a2a62")], foreground=[("selected", "#ffffff")])
    s.configure("X.Treeview.Heading", background="#160f26", foreground=look.ACCENT_HI, bordercolor="#160f26",
                lightcolor="#160f26", darkcolor="#160f26", font=("Segoe UI", 10, "bold"), relief="flat")
    s.map("X.Treeview.Heading", background=[("active", "#221838")])
    s.configure("X.Vertical.TScrollbar", background="#2a1f45", troughcolor=look.FIELD, bordercolor=look.FIELD,
                arrowcolor=look.MUTED, lightcolor="#2a1f45", darkcolor="#2a1f45")


def _caption(win, color):
    """Title bar in the colour of the backdrop (Windows 11)."""
    try:
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        c = ctypes.c_int(int(color[5:7] + color[3:5] + color[1:3], 16))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(c), ctypes.sizeof(c))
    except (AttributeError, OSError):
        pass


class ExtremeApp(App):
    # ================= construction =================
    def _build(self):
        W, H = 1100, 800
        self.root.geometry(f"{W}x{H}")
        self.root.minsize(980, 740)
        self.root.configure(bg=look.VOID)
        _caption(self.root, look.VOID)
        _styles(self.root)
        self.sc = sc = Scene(self.root, W, H)
        self.sounds = Sounds(self.s.get("ui_sounds", False))
        sc.sound = self.sounds.play
        sc.on_layout = self._layout
        self.started = self.intro_done = False
        self.tl = None
        self.console = None
        self.boot_queue, self.boot_pumping = [], False
        self.sys_info = {}
        self.toast = Toast(sc)

        self.emblem = Emblem(sc)
        self.h_title = Text(sc, None, "ARCHIPELAGO", look.F_TITLE, "#ffffff")
        self.h_sub = Text(sc, None, "LAUNCHER  //  SUPER MARIO 64 · OCARINA OF TIME  //  V" + config.APP_VERSION,
                          look.F_LABEL, look.MUTED)
        self.pill = Pill(sc)
        self.b_update = Button(sc, None, "⬆  Update", self.install_update, "primary", height=30)
        self.b_update.shown = False
        self.banner = Banner(sc, lambda: (M + 58 + self.h_sub.text_width() + 24,
                                          self.sc.w - M - self.pill.w - 24 - (self.b_update.w + 12 if self.b_update.shown else 0)))
        self.tabs = Tabs(sc, [("play", _("🎮  Spielen")), ("setup", _("⚙  Einrichtung")), ("net", _("🌐  Netzwerk")),
                              ("log", _("📜  Log"))], self._show_tab)

        self.page_order = ("play", "setup", "net", "log")
        self.panels = {k: [] for k in self.page_order}
        self.current_page = None
        self._build_play()
        self._build_setup()
        self._build_net()
        self._build_log()

        self.pb = Progress(sc)
        self.pb.shown = False
        self.l_prog = Text(sc, None, "", look.F_SMALL, look.MUTED, anchor="w")
        self.l_sys = Text(sc, None, f"{anim.engine.hz} HZ", look.F_MONO, "#6c5a9c", anchor="e")
        self._layout(sc.w, sc.h)
        sc.show_page(None)
        self.root.bind("<Button-1>", self._skip, add="+")
        self.root.bind("<Key>", self._skip, add="+")
        self.root.after(80, self._intro)

    def _panel(self, page, title):
        p = Panel(self.sc, page, title)
        self.panels[page].append(p)
        return p

    def _label(self, page, text):
        return Text(self.sc, page, text.upper(), look.F_LABEL, look.MUTED)

    def _entry(self, page, var, show=""):
        e = ttk.Entry(self.sc.c, textvariable=var, style="X.TEntry", show=show, font=look.F_BODY)
        return Embed(self.sc, page, e, "entry")

    def _build_play(self):
        sc, pg = self.sc, "play"
        p = self.p_conn = self._panel(pg, _("Verbindung"))
        self.v_addr, self.v_pw = tk.StringVar(), tk.StringVar()
        self.t_addr = p.add(self._label(pg, _("Server-Adresse (vom Host)")))
        self.x_addr = p.add(self._entry(pg, self.v_addr))
        self.t_pw = p.add(self._label(pg, _("Passwort (optional)")))
        self.x_pw = p.add(self._entry(pg, self.v_pw, "•"))

        def mk(text, cmd, kind="secondary", size=10):
            b = p.add(Button(sc, pg, text, cmd, kind, height=34, size=size))
            b.shown = False
            return b
        self.b_host = mk(_("🖥  Server hosten"), self.host_start, "primary")
        self.b_join = mk(_("🔗  Beitreten"), self.client_join, "primary")
        self.b_resume = mk(_("💾  Spielstand fortsetzen"), self.host_resume)
        self.b_gen = mk(_("🚀  Multiworld starten"), self.host_generate, "primary")
        self.b_play = mk(_("▶  Spielen"), self.play, "primary", 11)
        self.b_overlay = mk("🗺  Overlay", self.toggle_overlay)
        self.b_hint = mk("💡  Hint", self.open_hints)
        self.b_stats = mk(_("📊  Statistik"), lambda: dialogs.show_stats(self.root, self.paths))
        self.b_stop = mk(_("Beenden"), self.stop_all, "danger")
        self.action_buttons = [self.b_host, self.b_join, self.b_resume, self.b_gen, self.b_play, self.b_overlay,
                               self.b_hint, self.b_stats, self.b_stop]
        self.actions_visible = []
        self.l_state = p.add(Text(sc, pg, _("Nicht verbunden."), ("Segoe UI Semibold", 10), look.FG))
        self.l_addr = p.add(Text(sc, pg, "", ("Segoe UI Semibold", 10), look.OK, anchor="ne"))
        self.l_addr.bind("<Button-1>", lambda e: self.copy_address())
        self.l_addr.hand()

        pp = self.p_players = self._panel(pg, _("Spieler"))
        cols = ("name", "game", "status", "progress")
        self.tree = ttk.Treeview(sc.c, columns=cols, show="headings", style="X.Treeview")
        for c, t in zip(cols, (_("Name"), _("Spiel"), _("Status"), _("Fortschritt"))):
            self.tree.heading(c, text=t, anchor="w")
        self.tree.tag_configure("me", font=("Segoe UI Semibold", 10), foreground=look.ACCENT_HI)
        self.x_tree = pp.add(Embed(sc, pg, self.tree, "tree"))

        pl = self.p_live = self._panel(pg, "Live")
        self.feed = tk.Text(sc.c, wrap="word", state="disabled", font=("Segoe UI", 9), padx=8, pady=4)
        theme.style_text(self.feed)
        self.feed.configure(bg=look.FIELD, highlightbackground=look.WIRE)
        self.x_feed = pl.add(Embed(sc, pg, self.feed, "text"))

    def _build_setup(self):
        sc, pg = self.sc, "setup"
        p = self.p_who = self._panel(pg, _("Du"))
        self.v_name = tk.StringVar()
        self.t_name = p.add(self._label(pg, _("Spielername (max. 16 Zeichen)")))
        self.x_name = p.add(self._entry(pg, self.v_name))
        self.t_lang = p.add(self._label(pg, "Sprache / Language"))
        self.v_lang = tk.StringVar(value=i18n.LANGS[i18n.lang()])
        lang_box = ttk.Combobox(sc.c, textvariable=self.v_lang, values=list(i18n.LANGS.values()), state="readonly",
                                style="X.TCombobox", font=look.F_BODY)
        lang_box.bind("<<ComboboxSelected>>", lambda e: self.change_language())
        self.x_lang = p.add(Embed(sc, pg, lang_box, "combo"))
        self.t_style = p.add(self._label(pg, _("Oberfläche")))
        style_box = self._style_box(sc.c)
        style_box.configure(style="X.TCombobox", font=look.F_BODY)
        self.x_style = p.add(Embed(sc, pg, style_box, "combo"))

        g = self.p_game = self._panel(pg, _("Spiel"))
        self.game_labels = {**{k: gm["label"] for k, gm in GAMES.items()}, NO_GAME: _("Kein Spiel (nur hosten)")}
        self.v_game = tk.StringVar()
        self.game_cards = {}
        for key, icon, title, sub in (("sm64", "★", "Super Mario 64", "sm64ex · 60 FPS"),
                                      ("soh", "⚔", "Ocarina of Time", "Ship of Harkinian"),
                                      (NO_GAME, "▣", _("Nur hosten"), _("kein eigenes Spiel"))):
            card = g.add(Choice(sc, pg, icon, title, sub, lambda k=key: self._select_game(k)))
            card.set_mark_text(_("AKTIV"))
            self.game_cards[key] = card

        r = self.p_rom = self._panel(pg, "ROM")
        self.v_rom = tk.StringVar()
        self.e_rom = ttk.Entry(sc.c, textvariable=self.v_rom, style="X.TEntry", font=look.F_BODY)
        self.x_rom = r.add(Embed(sc, pg, self.e_rom))
        self.b_rom = r.add(Button(sc, pg, _("Durchsuchen …"), self.pick_rom, height=30))
        self.l_rom = r.add(Text(sc, pg, "", look.F_SMALL, look.MUTED))

        i = self.p_inst = self._panel(pg, _("Installation"))
        self.b_install = i.add(Button(sc, pg, _("⬇  Installieren / Prüfen"), self.install, "primary", height=32))
        self.l_inst = i.add(Text(sc, pg, "", ("Segoe UI Semibold", 10), look.FG, anchor="w"))
        self.v_root = tk.StringVar()
        self.t_root = i.add(Text(sc, pg, _("Ordner:").upper(), look.F_LABEL, look.MUTED, anchor="e"))
        self.x_root = i.add(self._entry(pg, self.v_root))
        self.b_root = i.add(Button(sc, pg, _("Ändern …"), self.pick_root, "ghost", height=30))

        o = self.p_opts = self._panel(pg, _("Optionen"))
        self.opt_buttons = [
            o.add(Button(sc, pg, _("📝  YAML bearbeiten"), self.edit_yaml, height=30)),
            o.add(Button(sc, pg, "🧩  Options Creator", self.options_creator, height=30)),
            o.add(Button(sc, pg, "🗄  Backups", lambda: dialogs.show_backups(self.root, self.paths, self._log),
                         height=30)),
            o.add(Button(sc, pg, _("📂  Ordner öffnen"), lambda: self._open(self.paths.root), "ghost", height=30))]
        self.b_mods = o.add(Button(sc, pg, _("🎨  SoH Mods / Texturen"), self.open_soh_mods, height=30))
        self.v_sounds = tk.BooleanVar()
        self.v_intro = tk.BooleanVar(value=self.s.get("intro", True))
        self.v_uisnd = tk.BooleanVar(value=self.s.get("ui_sounds", False))
        self.toggles = [
            o.add(Toggle(sc, pg, look.plain(_("🔔 Ton bei wichtigen Items")), self.v_sounds, self._save_fields)),
            o.add(Toggle(sc, pg, _("Oberflächen-Sounds"), self.v_uisnd, self._save_extreme)),
            o.add(Toggle(sc, pg, _("Startanimation"), self.v_intro, self._save_extreme))]

    def _build_net(self):
        sc, pg = self.sc, "net"
        a = self.p_addr = self._panel(pg, _("Adresse für Freunde"))
        self.l_addr_net = a.add(Text(sc, pg, "", ("Bahnschrift SemiBold", 15), look.OK))
        self.l_addr_net.bind("<Button-1>", lambda e: self.copy_address())
        self.l_addr_net.hand()
        self.t_addr_help = a.add(Text(sc, pg, _("Wird beim Hosten angezeigt. Anklicken kopiert sie. Eigene Adresse (z. B. "
                                                "playit-Adresse) hier festlegen. Leer = automatisch: Radmin/Hamachi-Adresse, "
                                                "falls vorhanden, sonst Internet-IP:"), look.F_SMALL, look.MUTED))
        self.v_public = tk.StringVar()
        self.x_public = a.add(self._entry(pg, self.v_public))
        self.b_public = a.add(Button(sc, pg, _("Speichern"), self.save_public_address, height=30))
        self.vpn_buttons = []

        e = self.p_reach = self._panel(pg, _("Erreichbarkeit"))
        self.v_port = tk.StringVar()
        self.t_port = e.add(self._label(pg, _("Port")))
        self.x_port = e.add(self._entry(pg, self.v_port))
        self.b_port = e.add(Button(sc, pg, _("📡  Port testen"), self.port_test, height=30))
        self.b_playit = e.add(Button(sc, pg, _("🌍  playit.gg einrichten"), self.playit, height=30))
        self.t_reach_help = e.add(Text(sc, pg, _("Ohne Portfreigabe im Router: alle nutzen Radmin VPN / Hamachi "
                                                 "(Host-Adresse aus dem VPN-Programm) oder der Host richtet playit.gg ein."),
                                       look.F_SMALL, look.MUTED))

    def _build_log(self):
        sc = self.sc
        p = self.p_log = self._panel("log", "Log")
        frame = tk.Frame(sc.c, bg=look.FIELD, highlightthickness=1, highlightbackground=look.WIRE)
        self.log_box = tk.Text(frame, wrap="word", state="disabled", font=("Consolas", 10), padx=8, pady=6)
        theme.style_text(self.log_box)
        self.log_box.configure(bg=look.FIELD, highlightthickness=0)
        sb = ttk.Scrollbar(frame, command=self.log_box.yview, style="X.Vertical.TScrollbar")
        self.log_box.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_box.pack(fill="both", expand=True)
        frame.copy_source = self.log_box
        self.x_log = p.add(Embed(sc, "log", frame, "text"))

    # ================= layout =================
    def _layout(self, W, H):
        cw = W - 2 * M
        bottom = H - FOOT
        self.emblem.place(M + 22, 46)
        self.h_title.place(M + 56, 20)
        self.h_sub.place(M + 58, 58)
        self._layout_header()
        self.tabs.place(M + 2, 104, w=W - M)

        # play
        p = self.p_conn.place(M, TOP, cw, 196)
        x, y = p.x + 20, p.y + 44
        self.t_addr.place(x, y)
        self.x_addr.place(x, y + 16, 340, 30)
        self.t_pw.place(x + 356, y)
        self.x_pw.place(x + 356, y + 16, 180, 30)
        self._layout_actions()
        self.l_state.place(x, p.y + 158)
        self.l_addr.place(p.x + p.w - 20, p.y + 158)
        y2 = TOP + 196 + 12
        lw = int(cw * 0.58)
        pp = self.p_players.place(M, y2, lw, bottom - y2)
        self.x_tree.place(pp.x + 14, pp.y + 40, pp.w - 28, pp.h - 54)
        tw = pp.w - 32
        for col, f in zip(self.tree["columns"], (0.27, 0.37, 0.2, 0.16)):
            self.tree.column(col, width=int(tw * f), anchor="w")
        pl = self.p_live.place(M + lw + 12, y2, cw - lw - 12, bottom - y2)
        self.x_feed.place(pl.x + 14, pl.y + 40, pl.w - 28, pl.h - 54)

        # setup
        wh = 186
        p = self.p_who.place(M, TOP, 334, wh)
        x, y = p.x + 20, p.y + 44
        self.t_name.place(x, y)
        self.x_name.place(x, y + 16, 294, 30)
        self.t_lang.place(x, y + 60)
        self.x_lang.place(x, y + 76, 142, 30)
        self.t_style.place(x + 152, y + 60)
        self.x_style.place(x + 152, y + 76, 142, 30)
        g = self.p_game.place(M + 346, TOP, cw - 346, wh)
        tile = (g.w - 40 - 20) / 3
        for i, card in enumerate(self.game_cards.values()):
            card.place(g.x + 20 + i * (tile + 10), g.y + 48, tile, 112)
        y = TOP + wh + 12
        r = self.p_rom.place(M, y, cw, 104)
        self.b_rom.place(r.x + r.w - 20 - self.b_rom.w, r.y + 44)
        self.x_rom.place(r.x + 20, r.y + 44, r.w - 50 - self.b_rom.w, 30)
        self.l_rom.place(r.x + 20, r.y + 80)
        y += 116
        i = self.p_inst.place(M, y, cw, 88)
        self.b_install.place(i.x + 20, i.y + 42)
        self.l_inst.place(i.x + 36 + self.b_install.w, i.y + 58)
        bx = i.x + i.w - 20 - self.b_root.w
        self.b_root.place(bx, i.y + 43)
        self.x_root.place(bx - 250, i.y + 43, 240, 30)
        self.t_root.place(bx - 258, i.y + 58)
        y += 100
        o = self.p_opts.place(M, y, cw, bottom - y)
        x = o.x + 20
        for b in self.opt_buttons + [self.b_mods]:
            b.place(x, o.y + 44)
            x += b.w + 8
        x = o.x + 20
        for t in self.toggles:
            t.place(x, o.y + 94)
            x += t.w + 30

        # network
        a = self.p_addr.place(M, TOP, cw, 200)
        self.l_addr_net.place(a.x + 20, a.y + 44)
        self.t_addr_help.place(a.x + 20, a.y + 84)
        self.t_addr_help.set_width(a.w - 40)
        self.x_public.place(a.x + 20, a.y + 144, 330, 30)
        self.b_public.place(a.x + 360, a.y + 144)
        self._layout_vpn()
        e = self.p_reach.place(M, TOP + 212, cw, 170)
        self.t_port.place(e.x + 20, e.y + 44)
        self.x_port.place(e.x + 20, e.y + 60, 100, 30)
        self.b_port.place(e.x + 132, e.y + 60)
        self.b_playit.place(e.x + 140 + self.b_port.w, e.y + 60)
        self.t_reach_help.place(e.x + 20, e.y + 112)
        self.t_reach_help.set_width(e.w - 40)

        # log
        lp = self.p_log.place(M, TOP, cw, bottom - TOP)
        self.x_log.place(lp.x + 14, lp.y + 40, lp.w - 28, lp.h - 54)

        # footer
        self.pb.place(M, H - 22, w=int(W * 0.34))
        self.l_prog.place(M + int(W * 0.34) + 14, H - 22)
        self.l_sys.place(W - M, H - 22)

    def _layout_header(self):
        W = self.sc.w
        self.pill.place(W - M, 44)
        self.b_update.place(W - M - self.pill.w - 12 - self.b_update.w, 29)

    def _layout_actions(self):
        p = self.p_conn
        x, y, right = p.x + 20, p.y + 100, p.x + p.w - 20
        for b in self.actions_visible:
            if b is self.b_stop:
                b.place(right - b.w, y)
            else:
                b.place(x, y)
                x += b.w + 8

    def _layout_vpn(self):
        a = self.p_addr
        x = a.x + 368 + self.b_public.w
        for b in self.vpn_buttons:
            b.place(x, a.y + 144)
            x += b.w + 8

    # ================= overrides of the shared logic =================
    def _show_actions(self, visible):
        new = [b for b in visible if b not in self.actions_visible]
        self.actions_visible = list(visible)
        for b in self.action_buttons:
            b.shown = b in visible
        self._layout_actions()
        for b in self.action_buttons:
            b.sync()
        if self.intro_done:
            for i, b in enumerate(new):
                b.appear(delay=45 * i)

    def _show_progress(self, frac, text):
        self.pb.shown = frac is not None or bool(text)
        self.pb.sync()
        if frac is None:
            self.pb.indeterminate() if text else self.pb.reset()
        else:
            self.pb.set(frac)
        self.l_prog.configure(text=text)

    def _vpn_button(self, text, command):
        b = self.p_addr.add(Button(self.sc, "net", text, command, "ghost", height=30))
        self.vpn_buttons.append(b)
        self._layout_vpn()
        b.sync()
        if self.intro_done and self.current_page == "net":
            b.appear()

    def _show_vpn(self, found):
        super()._show_vpn(found)
        if found:
            self._boot("OK", "VPN  " + ", ".join(f"{v} {ip}" for v, ip in found))
            self._sys("vpn", "VPN " + found[0][0].upper())
        else:
            self._boot("--", _("VPN  kein Radmin/Hamachi/Tailscale/ZeroTier-Adapter"), look.MUTED)
            self._sys("vpn", "VPN –")

    def _show_update(self, info):
        super()._show_update(info)
        self._layout_header()
        self.b_update.sync()
        if self.intro_done:
            self.b_update.appear()
        self._boot("NEU", _("Update  Version {version} verfügbar").format(version=info["version"]), look.WARN)

    def set_state(self, text):
        if text == self.l_state.cget("text"):
            return
        self.l_state.configure(foreground=look.GLOW)
        self.l_state.scramble_to(text, 420)
        anim.Tween(self.sc.c, 900, lambda t: self.l_state.configure(foreground=anim.mix(look.GLOW, look.FG, t)),
                   ease=anim.in_out_sine, delay=250)

    def _watch_event(self, kind, data):
        if kind == "received" and data["progression"]:
            self.banner.show(_("Progressions-Item"), data["item"], _("von {sender}").format(sender=data["sender"]))
            self._notify(_("⭐ {item} von {sender}").format(item=data["item"], sender=data["sender"]), toast=False)
        elif kind == "goal":
            self.banner.show(_("Ziel erreicht"), data, "🏆")
            self._notify(_("🏆 {name} hat das Ziel erreicht!").format(name=data), toast=False)
        else:
            super()._watch_event(kind, data)

    def _notify(self, text, toast=True):
        if toast:
            self.toast.show(text, ms=4000)
        if self.overlay:
            self.overlay.hud.notify(text)
        if self.v_sounds.get() and not self.sounds.enabled:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)

    def _save_extreme(self):
        self.s["intro"] = self.v_intro.get()
        self.s["ui_sounds"] = self.v_uisnd.get()
        self.sounds.enabled = self.s["ui_sounds"]
        config.save_settings(self.s)

    # ================= pages =================
    def _show_tab(self, key):
        if key == self.current_page:
            return
        self.current_page = key
        if not self.started:
            self.sc.show_page(key)
            return
        if self.tl and self.tl.running():
            self._skip()
        self.sc.c.delete("fx")  # effects of the previous page
        self.sc.sound("glitch")
        self.sc.glitch()
        self.sc.show_page(key)
        self._build_page(key, Timeline(self.sc.c), 70, quick=True)

    def _build_page(self, key, tl, delay, quick):
        """Panels build one after another; their content appears where the print edge passes it."""
        embeds = []
        for i, p in enumerate(self.panels[key]):
            fill_at, fill_ms = p.build(tl, delay + i * (80 if quick else 150), quick)
            for ch in p.children:
                if not ch.shown:
                    continue
                rel = max(0.0, min(1.0, (ch.y - p.y) / max(1, p.h)))
                ch.build(tl, int(fill_at + fill_ms * rel * 0.9), quick)
                if isinstance(ch, Embed):
                    embeds.append(ch)
        end = int(tl.end_ms()) + 40
        def finish():
            for e in embeds:
                e.swap()
            self.sc.c.delete("fx")  # leftovers of effects must not catch clicks
        tl.at(end, finish)
        self.sc.boost(end + 300)
        return end

    # ================= intro =================
    def _intro(self):
        self.started = True
        sc = self.sc
        self.sys_info["hz"] = f"{anim.engine.hz} HZ"
        self._boot_checks()
        if not self.s.get("intro", True):
            self._intro_end()
            return
        tl = self.tl = Timeline(sc.c)
        for e in sc.elems:
            if e.shown and e.page in (None, self.current_page):
                e.hide_for_build()
        sc.compose()
        sc.wipe = 0.0
        ScanLine(sc).run(tl, 0, 520)
        self.emblem.build(tl, 120)
        self.h_title.build(tl, 330)
        self.h_sub.build(tl, 560)
        self.tabs.build(tl, 720)
        self.pill.build(tl, 950)
        if self.b_update.shown:
            self.b_update.build(tl, 1050)
        end = self._build_page(self.current_page, tl, 260, quick=False)
        self.l_sys.build(tl, 1500)
        tl.at(280, self._open_console)
        tl.at(max(600, end - 420), self._close_console)
        tl.at(end + 20, self._intro_end)
        sc.boost(end + 500)
        self.sounds.play("intro")

    def _skip(self, _e=None):
        if self.started and not self.intro_done and self.tl and self.tl.running():
            self.tl.finish()
            self.sc.c.delete("fx")
            if self.sounds.enabled:
                winsound.PlaySound(None, 0)

    def _intro_end(self):
        if self.intro_done:
            return
        self.intro_done = True
        self.sc.wipe = 1.0
        self._close_console()
        for e in self.sc.elems:
            if not e.built:
                e.reveal()
        for e in self.panels[self.current_page]:
            for ch in e.children:
                if isinstance(ch, Embed):
                    ch.swap()
        self.sc.compose()

    # ================= boot checks =================
    def _open_console(self):
        self.console = BootConsole(self.sc, M + 8, self.sc.h - FOOT - 10)
        self._pump()

    def _close_console(self):
        if self.console:
            self.console.close()
            self.console = None

    def _boot(self, status, text, color=look.OK):
        """A boot line: in the console while it is open, always in the log."""
        self._log(f"[{status:^4}] {text}")
        self.boot_queue.append((status, text, color))
        self._pump()

    def _pump(self):
        if self.boot_pumping or not self.console or not self.boot_queue:
            if not self.console and self.intro_done:
                self.boot_queue.clear()  # too late for the console; the lines are in the log
            return
        self.boot_pumping = True
        self.console.line(*self.boot_queue.pop(0))

        def next_():
            self.boot_pumping = False
            self._pump()
        self.root.after(BOOT_GAP, next_)

    def _sys(self, key, text):
        self.sys_info[key] = text
        order = ("ap", "game", "rom", "vpn", "hz")
        self.l_sys.configure(text="  ·  ".join(self.sys_info[k] for k in order if k in self.sys_info))

    def _boot_checks(self):
        self._boot("OK", _("Grafik-Kern  {hz} Hz · {w}×{h}").format(hz=anim.engine.hz, w=self.sc.w, h=self.sc.h))
        self._sys("hz", f"{anim.engine.hz} HZ")
        paths, game, rom = self.paths, self.game, self.v_rom.get().strip()

        def work():
            res = []
            inst = Installer(paths, lambda *a: None, lambda *a: None)
            ap = inst.archipelago_ok()
            res.append(("OK" if ap else "FAIL", _("Archipelago  {state}").format(
                state=_("installiert") if ap else _("fehlt")), look.OK if ap else look.ERR, "ap",
                "AP ✓" if ap else "AP ✗"))
            if game in GAMES:
                label = GAMES[game]["label"]
                ok = inst.sm64_region_built() is not None if game == "sm64" else inst.soh_ok()
                res.append(("OK" if ok else "FAIL", f"{label}  " + (_("installiert") if ok else _("fehlt")),
                            look.OK if ok else look.WARN, "game", game.upper() + (" ✓" if ok else " ✗")))
                if rom:
                    rok, text = roms.describe(game, rom)
                else:
                    rok, text = False, _("keine ROM gewählt")
                res.append(("OK" if rok else "FAIL", "ROM  " + text, look.OK if rok else look.WARN, "rom",
                            "ROM ✓" if rok else "ROM ✗"))
            else:
                res.append(("--", _("Spiel  nur hosten"), look.MUTED, "game", "HOST"))
            self.call(self._boot_results, res)
        threading.Thread(target=work, daemon=True).start()

    def _boot_results(self, res):
        for status, text, color, key, short in res:
            self._boot(status, text, color)
            self._sys(key, short)
