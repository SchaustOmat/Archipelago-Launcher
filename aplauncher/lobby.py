"""Pre-game lobby: a small HTTP server on the host that collects players and their YAMLs.

It listens on the same port the Archipelago server uses later, so friends only need one
forwarded port. When the host starts the game the lobby closes and Archipelago takes the port.
"""
import json
import re
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config
from .i18n import _

NAME_RE = re.compile(r"^[^\s{}:][^{}:]{0,15}$")
ONLINE_TIMEOUT = 10  # seconds without a poll before a player shows as offline


def validate_name(name: str) -> str | None:
    name = name.strip()
    if not name:
        return _("Bitte einen Spielernamen eintragen.")
    if len(name) > 16:
        return _("Spielername darf höchstens 16 Zeichen haben.")
    if not NAME_RE.match(name):
        return _("Spielername darf keine { } : enthalten.")
    return None


class Lobby:
    def __init__(self, port: int, password: str = ""):
        self.port = port
        self.password = password
        self.lock = threading.Lock()
        self.players: dict[str, dict] = {}
        self.state = "lobby"   # lobby | generating | starting | error
        self.message = ""
        self.httpd = None
        self.on_change = lambda: None

    # ----- state -----
    def add_player(self, name, game, yaml_text, ready=True, local=False, cid=""):
        err = validate_name(name)
        if err:
            return err
        if game not in config.GAMES:
            return "Unbekanntes Spiel."
        with self.lock:
            if self.state != "lobby":
                return _("Die Multiworld wird schon erstellt; Beitreten geht nicht mehr.")
            existing = self.players.get(name)
            if existing and (existing["local"] != local or existing["cid"] != cid):
                return _("Dieser Name ist schon vergeben.")
            for other, p in self.players.items():
                if other != name and cid and p["cid"] == cid:
                    del self.players[other]  # same launcher renamed itself
                    break
            self.players[name] = {"game": game, "yaml": yaml_text, "ready": ready,
                                  "seen": time.time(), "local": local, "cid": cid}
        self.on_change()
        return None

    def remove_player(self, name):
        with self.lock:
            self.players.pop(name, None)
        self.on_change()

    def set_state(self, state, message=""):
        with self.lock:
            self.state, self.message = state, message
        self.on_change()

    def snapshot(self) -> dict:
        now = time.time()
        with self.lock:
            return {
                "app": "aplauncher", "version": config.APP_VERSION,
                "state": self.state, "message": self.message,
                "need_password": bool(self.password),
                "players": [{"name": n, "game": p["game"], "ready": p["ready"],
                             "online": p["local"] or now - p["seen"] < ONLINE_TIMEOUT}
                            for n, p in sorted(self.players.items())],
            }

    def yamls(self) -> dict[str, str]:
        with self.lock:
            return {n: p["yaml"] for n, p in self.players.items()}

    # ----- http -----
    def start(self):
        lobby = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, obj):
                body = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path.startswith("/aplobby/state"):
                    m = re.search(r"[?&]name=([^&]+)", self.path)
                    if m:
                        name = urllib.request.unquote(m.group(1))
                        with lobby.lock:
                            if name in lobby.players:
                                lobby.players[name]["seen"] = time.time()
                    self._send(200, lobby.snapshot())
                else:
                    self._send(404, {"error": "not found"})

            def do_POST(self):
                try:
                    length = min(int(self.headers.get("Content-Length") or 0), 2_000_000)
                    data = json.loads(self.rfile.read(length) or b"{}")
                except ValueError:
                    return self._send(400, {"error": _("Ungültige Anfrage.")})
                if lobby.password and data.get("password") != lobby.password:
                    return self._send(403, {"error": "Falsches Passwort."})
                if self.path == "/aplobby/join":
                    err = lobby.add_player(str(data.get("name", "")), str(data.get("game", "")),
                                           str(data.get("yaml", "")), bool(data.get("ready", True)),
                                           cid=str(data.get("cid", "")))
                    self._send(400 if err else 200, {"error": err} if err else lobby.snapshot())
                elif self.path == "/aplobby/leave":
                    name = str(data.get("name", ""))
                    with lobby.lock:
                        local = lobby.players.get(name, {}).get("local")
                    if not local:
                        lobby.remove_player(name)
                    self._send(200, {"ok": True})
                else:
                    self._send(404, {"error": "not found"})

        self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port), Handler)
        self.httpd.daemon_threads = True
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None


# ----- client side -----
class LobbyError(Exception):
    def __init__(self, message, unreachable=False):
        super().__init__(message)
        self.unreachable = unreachable  # no TCP answer at all, as opposed to "something else answered"


def _url(address: str, path: str) -> str:
    address = address.strip()
    for prefix in ("ws://", "wss://", "http://", "https://"):
        if address.startswith(prefix):
            address = address[len(prefix):]
    if ":" not in address:
        address += f":{config.DEFAULT_PORT}"
    return f"http://{address}{path}"


def _request(address, path, payload=None, timeout=5):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(_url(address, path), data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            obj = json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            obj = json.loads(e.read())
        except ValueError:
            obj = {}
        raise LobbyError(obj.get("error") or f"HTTP {e.code}")
    except (urllib.error.URLError, OSError) as e:
        raise LobbyError(_("Host nicht erreichbar ({reason})").format(reason=getattr(e, 'reason', e)), unreachable=True)
    except ValueError:
        raise LobbyError(_("Unter dieser Adresse läuft keine Launcher-Lobby."))
    if obj.get("app") != "aplauncher" and "ok" not in obj:
        raise LobbyError(_("Unter dieser Adresse läuft keine Launcher-Lobby."))
    return obj


def get_state(address, name=""):
    q = "?name=" + urllib.request.quote(name) if name else ""
    return _request(address, "/aplobby/state" + q)


def join(address, name, game, yaml_text, cid, password="", ready=True):
    return _request(address, "/aplobby/join", {"name": name, "game": game, "yaml": yaml_text,
                                               "cid": cid, "password": password, "ready": ready})


def leave(address, name, password=""):
    try:
        _request(address, "/aplobby/leave", {"name": name, "password": password}, timeout=3)
    except LobbyError:
        pass
