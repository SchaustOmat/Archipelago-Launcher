"""Save backups: SoH saves, the Mario 64 save file and the server's .apsave, copied before playing.

Each backup is a folder under <root>/backups with a manifest that maps every copied file back to
where it came from, so restoring is just copying them back.
"""
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from .config import Paths

KEEP = 20
MIN_GAP_S = 10 * 60  # at most one automatic backup every 10 minutes (resume + play right after each other)
SM64_SAVE_DIR = Path(os.environ.get("APPDATA", Path.home())) / "sm64ex"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
# Processes that write these files; restoring while they run would be overwritten right away.
WRITERS = ("soh.exe", "sm64.", "archipelagoserver.exe")


class BackupError(Exception):
    pass


def _dir(paths: Paths) -> Path:
    return paths.root / "backups"


def _saves(paths: Paths, apsaves) -> list[Path]:
    files = list((paths.soh / "Save").glob("*.sav")) + list(SM64_SAVE_DIR.glob("*.bin")) + list(apsaves)
    return [f for f in files if f.is_file()]


def _write(paths: Paths, files: list[Path], reason: str, prune=True) -> Path:
    now = datetime.now()
    dest = _dir(paths) / now.strftime("%Y-%m-%d_%H-%M-%S")
    while dest.exists():  # two backups within the same second (restore right after a backup)
        dest = dest.with_name(dest.name + "_")
    dest.mkdir(parents=True)
    manifest = {"time": now.isoformat(timespec="seconds"), "reason": reason, "files": {}}
    for i, f in enumerate(files):
        name = f"{i:02d}_{f.name}"
        shutil.copy2(f, dest / name)
        manifest["files"][name] = str(f)
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for old in list_backups(paths)[KEEP:] if prune else []:
        shutil.rmtree(old["path"], ignore_errors=True)
    return dest


def list_backups(paths: Paths) -> list[dict]:
    """Newest first: {"path", "time", "reason", "files"}."""
    out = []
    if _dir(paths).is_dir():
        for d in _dir(paths).iterdir():
            try:
                m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
                out.append({"path": d, "time": datetime.fromisoformat(m["time"]), "reason": m.get("reason", ""),
                            "files": m["files"]})
            except (OSError, ValueError, KeyError):
                continue
    return sorted(out, key=lambda b: (b["time"], b["path"].name), reverse=True)


def create(paths: Paths, reason: str, session_zip: Path | None = None, force=False) -> Path | None:
    """Backup before playing. None when there is nothing to save or (unless forced) the last one is very recent.
    Without a session the .apsave files of all sessions are included."""
    if session_zip:
        apsaves = session_zip.parent.glob("*.apsave")
    else:
        apsaves = paths.sessions.glob("*/*.apsave") if paths.sessions.is_dir() else []
    files = _saves(paths, apsaves)
    last = list_backups(paths)[:1]
    if not files or (not force and last and (datetime.now() - last[0]["time"]).total_seconds() < MIN_GAP_S):
        return None
    return _write(paths, files, reason)


def running_writers() -> list[str]:
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=10,
                             creationflags=NO_WINDOW).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    names = {line.split(",")[0].strip('"') for line in out.splitlines() if line}
    return sorted(n for n in names if n.lower().startswith(WRITERS))


def restore(paths: Paths, backup: dict):
    """Copy a backup back. Everything on disk is backed up first, so a restore can be undone."""
    busy = running_writers()
    if busy:
        raise BackupError("Erst Spiel und Server beenden, sonst überschreiben sie die Dateien sofort wieder:\n"
                          + ", ".join(busy))
    current = _saves(paths, paths.sessions.glob("*/*.apsave") if paths.sessions.is_dir() else [])
    if current:
        # No pruning here: the backup being restored may be the oldest one.
        _write(paths, current, "Stand vor dem Wiederherstellen", prune=False)
    for name, target in backup["files"].items():
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup["path"] / name, target)
