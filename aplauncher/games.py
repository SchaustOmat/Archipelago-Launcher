"""Starts the players' games already pointed at the server."""
import json
import os
import subprocess

from .config import Paths


class GameError(Exception):
    pass


def server_address(address: str) -> str:
    a = address.strip()
    for prefix in ("ws://", "wss://"):
        if a.startswith(prefix):
            a = a[len(prefix):]
    return a if ":" in a else f"{a}:38281"


def launch_sm64(paths: Paths, region: str, address: str, name: str, password: str):
    exe = paths.sm64_exe_for(region)
    if not exe.is_file():
        raise GameError("Super Mario 64 ist noch nicht gebaut. Erst 'Installieren' ausführen.")
    args = [str(exe), "--sm64ap_name", name, "--sm64ap_ip", server_address(address)]
    if password:
        args += ["--sm64ap_passwd", password]
    env = dict(os.environ)
    # The MinGW build needs SDL2/GLEW/libgcc DLLs from MSYS2.
    env["PATH"] = str(paths.msys / "mingw64" / "bin") + os.pathsep + env.get("PATH", "")
    return subprocess.Popen(args, cwd=exe.parent, env=env)


def configure_soh(paths: Paths, address: str, name: str, password: str):
    """Write the Archipelago connection into shipofharkinian.json (CVars gRemote.Archipelago.*)."""
    cfg_path = paths.soh / "shipofharkinian.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    ap = cfg.setdefault("CVars", {}).setdefault("gRemote", {}).setdefault("Archipelago", {})
    ap["ServerAddress"] = server_address(address)
    ap["SlotName"] = name
    ap["Password"] = password or ""
    cfg_path.write_text(json.dumps(cfg, indent=4), encoding="utf-8")


def launch_soh(paths: Paths, address: str, name: str, password: str):
    if not paths.soh_exe.is_file() or not (paths.soh / "oot.o2r").is_file():
        raise GameError("Ship of Harkinian ist noch nicht eingerichtet. Erst 'Installieren' ausführen.")
    configure_soh(paths, address, name, password)
    return subprocess.Popen([str(paths.soh_exe)], cwd=paths.soh)
