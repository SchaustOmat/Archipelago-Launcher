"""Host side: generate the multiworld and run the Archipelago server."""
import re
import socket
import subprocess
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from . import jobs
from .config import Paths
from .i18n import _

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
        raise HostError(_("Keine Spieler in der Lobby."))
    session = paths.sessions / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    players = session / "players"
    players.mkdir(parents=True)
    for i, (name, text) in enumerate(sorted(yamls.items())):
        (players / f"{i:02d}.yaml").write_text(set_yaml_name(text, name), encoding="utf-8")
    log(_("Generiere Multiworld für {n} Spieler ...").format(n=len(yamls)))
    code = _run_logged([str(paths.ap_generate), "--player_files_path", str(players),
                        "--outputpath", str(session)], paths.ap, log)
    zips = sorted(session.glob("AP_*.zip"))
    if code != 0 or not zips:
        raise HostError(_("Generieren fehlgeschlagen. Meist ist eine YAML ungültig; Details im Log."))
    log(_("Multiworld erstellt: {name}").format(name=zips[0].name))
    return zips[0]


def list_sessions(paths: Paths) -> list[Path]:
    """Previous multiworlds that can be resumed, the one played last first."""
    if not paths.sessions.is_dir():
        return []
    out = [z for s in paths.sessions.iterdir() for z in s.glob("AP_*.zip")]
    return sorted(out, key=last_played, reverse=True)


def last_played(zip_path: Path) -> float:
    """The server rewrites the .apsave while playing, so its time is when the multiworld was last played."""
    return max(f.stat().st_mtime for f in [zip_path, *zip_path.parent.glob("*.apsave")])


def created(zip_path: Path) -> datetime:
    """The session folder is named after its creation time (YYYY-MM-DD_HH-MM-SS)."""
    try:
        return datetime.strptime(zip_path.parent.name, "%Y-%m-%d_%H-%M-%S")
    except ValueError:
        return datetime.fromtimestamp(zip_path.stat().st_mtime)


def delete_session(paths: Paths, zip_path: Path):
    """Move a saved multiworld (its whole session folder) to the Windows recycle bin."""
    import ctypes
    from ctypes import wintypes
    folder = zip_path.parent.resolve()
    if folder.parent != paths.sessions.resolve():
        raise HostError(_("Kein Spielstand-Ordner: {path}").format(path=folder))

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]
    FO_DELETE, FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI = 3, 0x4, 0x10, 0x40, 0x400
    op = SHFILEOPSTRUCTW(wFunc=FO_DELETE, pFrom=str(folder) + "\0",  # list ends with a double NUL
                         fFlags=FOF_SILENT | FOF_NOCONFIRMATION | FOF_ALLOWUNDO | FOF_NOERRORUI)
    code = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if code or folder.exists():
        raise HostError(_("Spielstand konnte nicht gelöscht werden (Code {code}). Läuft der Server noch?").format(
            code=code))


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
        jobs.bind(self.proc)  # dies with the launcher, never left running on its own
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        for line in self.proc.stdout:
            if line.strip():
                self.log("[Server] " + line.rstrip())
        self.log(_("[Server] beendet (Code {code}).").format(code=self.proc.wait()))

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


def server_pid_on_port(port: int) -> int | None:
    """PID of an ArchipelagoServer.exe listening on the port (e.g. left over after the launcher crashed)."""
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, timeout=10,
                             creationflags=NO_WINDOW).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1].endswith(f":{port}") and parts[3].upper().startswith(("LISTEN", "ABH")):
            pid = int(parts[4])
            name = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True,
                                  text=True, timeout=10, creationflags=NO_WINDOW).stdout
            if "archipelagoserver" in name.lower():
                return pid
    return None


def kill_pid(pid: int):
    subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, creationflags=NO_WINDOW)


def wait_port_free(port: int, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        with socket.socket() as s:
            try:
                s.bind(("0.0.0.0", port))
                return
            except OSError:
                time.sleep(0.5)
    raise HostError(_("Port {port} ist belegt (läuft schon ein anderer Server?).").format(port=port))


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


UA = {"User-Agent": "Mozilla/5.0 (APLauncher)"}  # ifconfig.co answers 403 to Python's default agent


def port_reachable(port: int) -> bool | None:
    """Ask an outside service to connect back to us over IPv4. None if no service answered."""
    import json

    def ifconfig():
        req = urllib.request.Request(f"https://ifconfig.co/port/{port}", headers={"Accept": "application/json", **UA})
        return json.loads(urllib.request.urlopen(req, timeout=15).read())["reachable"]

    def portchecker():
        ip = public_ip()
        body = json.dumps({"host": ip, "ports": [port]}).encode()
        req = urllib.request.Request("https://portchecker.io/api/v1/query", data=body,
                                     headers={"Content-Type": "application/json", **UA})
        return json.loads(urllib.request.urlopen(req, timeout=20).read())["check"][0]["status"]

    for check in (ifconfig, portchecker):
        try:
            return bool(_ipv4_only(check))
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            continue
    return None
