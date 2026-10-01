"""Host side: generate the multiworld and run the Archipelago server."""
import re
import socket
import subprocess
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from .config import Paths

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class HostError(Exception):
    pass


def set_yaml_name(yaml_text: str, name: str) -> str:
    """Force the top-level `name:` of a player YAML to the lobby name."""
    line = f"name: {name}"
    if re.search(r"^name:.*$", yaml_text, flags=re.M):
        return re.sub(r"^name:.*$", lambda _: line, yaml_text, count=1, flags=re.M)
    return line + "\n" + yaml_text


def _run_logged(args, cwd, log) -> int:
    proc = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, creationflags=NO_WINDOW,
                            text=True, encoding="utf-8", errors="replace")
    for line in proc.stdout:
        if line.strip():
            log(line.rstrip())
    return proc.wait()


def generate(paths: Paths, yamls: dict[str, str], log) -> Path:
    """Write the YAMLs into a new session folder and run ArchipelagoGenerate. Returns the multiworld zip."""
    if not yamls:
        raise HostError("Keine Spieler in der Lobby.")
    session = paths.sessions / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    players = session / "players"
    players.mkdir(parents=True)
    for i, (name, text) in enumerate(sorted(yamls.items())):
        (players / f"{i:02d}.yaml").write_text(set_yaml_name(text, name), encoding="utf-8")
    log(f"Generiere Multiworld für {len(yamls)} Spieler ...")
    code = _run_logged([str(paths.ap_generate), "--player_files_path", str(players),
                        "--outputpath", str(session)], paths.ap, log)
    zips = sorted(session.glob("AP_*.zip"))
    if code != 0 or not zips:
        raise HostError("Generieren fehlgeschlagen. Meist ist eine YAML ungültig; Details im Log.")
    log(f"Multiworld erstellt: {zips[0].name}")
    return zips[0]


def list_sessions(paths: Paths) -> list[Path]:
    """Previous multiworlds (newest first) that can be resumed."""
    if not paths.sessions.is_dir():
        return []
    out = [z for s in paths.sessions.iterdir() for z in s.glob("AP_*.zip")]
    return sorted(out, key=lambda z: z.stat().st_mtime, reverse=True)


def session_players(zip_path: Path) -> list[str]:
    names = []
    for y in sorted((zip_path.parent / "players").glob("*.yaml")):
        m = re.search(r"^name:\s*(.+)$", y.read_text(encoding="utf-8", errors="replace"), flags=re.M)
        if m:
            names.append(m.group(1).strip())
    return names


class Server:
    """Runs ArchipelagoServer.exe; it saves progress next to the zip (.apsave) by itself."""

    def __init__(self, paths: Paths, zip_path: Path, port: int, password: str, log):
        self.paths, self.zip, self.port, self.password, self.log = paths, zip_path, port, password, log
        self.proc = None

    def start(self):
        wait_port_free(self.port)
        args = [str(self.paths.ap_server), str(self.zip), "--port", str(self.port)]
        if self.password:
            args += ["--password", self.password]
        # stdin stays an open pipe: the server's console loop would stop on EOF.
        self.proc = subprocess.Popen(args, cwd=self.paths.ap, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     stdin=subprocess.PIPE, creationflags=NO_WINDOW,
                                     text=True, encoding="utf-8", errors="replace")
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        for line in self.proc.stdout:
            if line.strip():
                self.log("[Server] " + line.rstrip())
        self.log(f"[Server] beendet (Code {self.proc.wait()}).")

    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def command(self, text: str):
        if self.running():
            self.proc.stdin.write(text + "\n")
            self.proc.stdin.flush()

    def stop(self):
        if self.running():
            try:
                self.command("/exit")
                self.proc.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                self.proc.kill()


def wait_port_free(port: int, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        with socket.socket() as s:
            try:
                s.bind(("0.0.0.0", port))
                return
            except OSError:
                time.sleep(0.5)
    raise HostError(f"Port {port} ist belegt (läuft schon ein anderer Server?).")


# ----- network helpers -----
def _ipv4_only(fn):
    """Run fn with name resolution limited to IPv4 (port forwarding is almost always IPv4)."""
    orig = socket.getaddrinfo

    def v4(host, port, family=0, *a, **kw):
        return orig(host, port, socket.AF_INET, *a, **kw)
    socket.getaddrinfo = v4
    try:
        return fn()
    finally:
        socket.getaddrinfo = orig


def public_ip() -> str | None:
    try:
        return _ipv4_only(lambda: urllib.request.urlopen("https://api.ipify.org", timeout=8).read().decode().strip())
    except OSError:
        return None


def port_reachable(port: int) -> bool | None:
    """Ask ifconfig.co to connect back to us. None if the check itself failed."""
    import json

    def check():
        req = urllib.request.Request(f"https://ifconfig.co/port/{port}", headers={"Accept": "application/json"})
        return json.loads(urllib.request.urlopen(req, timeout=15).read()).get("reachable")
    try:
        return _ipv4_only(check)
    except (OSError, ValueError):
        return None
