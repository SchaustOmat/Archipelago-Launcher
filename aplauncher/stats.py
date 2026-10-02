"""Per-multiworld statistics, collected from what the launcher's text client sees.

Stored per seed in %APPDATA%\\APLauncher\\stats\\<seed>.json, so resuming a multiworld keeps adding to it.
Only counts what happened while this launcher was connected.
"""
import json
import time
from datetime import datetime
from pathlib import Path

from . import config

FLAG_PROGRESSION = 0b001
SAVE_EVERY_S = 20


def stats_dir() -> Path:
    d = config.settings_path().parent / "stats"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _player(game="") -> dict:
    return {"game": game, "found_for_others": 0, "received": 0, "progression": 0, "suppliers": {},
            "longest_wait_s": 0, "checks": 0, "total": 0, "goal_at": None}


class RunStats:
    def __init__(self, seed: str):
        self.path = stats_dir() / f"{seed}.json"
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {"seed": seed, "started": _now(), "play_seconds": 0, "players": {}}
        self._last_prog = {}   # name -> monotonic time of the last progression item (this session only)
        self._dirty, self._saved = False, 0.0

    def _p(self, name, game="") -> dict:
        p = self.data["players"].setdefault(name, _player(game))
        if game:
            p["game"] = game
        return p

    def set_players(self, players: dict):
        """players: slot -> {"name", "game"}"""
        for info in players.values():
            self._p(info["name"], info["game"])
        self._changed()

    def item_sent(self, finder: str, receiver: str, flags: int):
        if finder != receiver:
            self._p(finder)["found_for_others"] += 1
            r = self._p(receiver)
            r["received"] += 1
            if flags & FLAG_PROGRESSION:
                r["suppliers"][finder] = r["suppliers"].get(finder, 0) + 1
        if flags & FLAG_PROGRESSION:
            r = self._p(receiver)
            if finder != receiver:
                r["progression"] += 1
            now = time.monotonic()
            if receiver in self._last_prog:
                r["longest_wait_s"] = max(r["longest_wait_s"], int(now - self._last_prog[receiver]))
            self._last_prog[receiver] = now
        self._changed()

    def goal(self, name: str):
        p = self._p(name)
        if not p["goal_at"]:
            p["goal_at"] = _now()
            self._changed(force=True)

    def progress(self, name: str, checks: int, total: int):
        p = self._p(name)
        if (p["checks"], p["total"]) != (checks, total):
            p["checks"], p["total"] = checks, total
            self._changed()

    def add_time(self, seconds: float):
        self.data["play_seconds"] += seconds
        self._changed()

    def _changed(self, force=False):
        self._dirty = True
        if force or time.monotonic() - self._saved > SAVE_EVERY_S:
            self.save()

    def save(self):
        if not self._dirty:
            return
        self.data["updated"] = _now()
        try:
            self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
            self._dirty, self._saved = False, time.monotonic()
        except OSError:
            pass


def list_runs() -> list[dict]:
    """Newest first."""
    runs = []
    for f in stats_dir().glob("*.json"):
        try:
            runs.append(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return sorted(runs, key=lambda r: r.get("updated", r.get("started", "")), reverse=True)


def duration(seconds: float) -> str:
    m = int(seconds) // 60
    return f"{m // 60} h {m % 60:02d} min" if m >= 60 else f"{m} min"


def _date(iso: str | None) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y %H:%M")
    except (TypeError, ValueError):
        return "?"


def run_title(run: dict) -> str:
    names = ", ".join(run.get("players", {})) or "?"
    return f"{_date(run.get('started'))}  –  {names}"


def report(run: dict) -> str:
    players = run.get("players", {})
    lines = [f"Gestartet: {_date(run.get('started'))}    Zuletzt: {_date(run.get('updated'))}",
             f"Spielzeit (Launcher verbunden): {duration(run.get('play_seconds', 0))}", ""]
    for name, p in sorted(players.items(), key=lambda kv: -kv[1].get("checks", 0)):
        pct = f" ({100 * p['checks'] // p['total']}%)" if p.get("total") else ""
        lines.append(f"■ {name}  ·  {p.get('game', '')}")
        lines.append(f"    Checks: {p.get('checks', 0)}/{p.get('total', 0)}{pct}"
                     + (f"    🏆 Ziel: {_date(p['goal_at'])}" if p.get("goal_at") else ""))
        lines.append(f"    Für andere gefunden: {p.get('found_for_others', 0)}    "
                     f"Von anderen bekommen: {p.get('received', 0)} (davon wichtig: {p.get('progression', 0)})")
        if p.get("suppliers"):
            best, n = max(p["suppliers"].items(), key=lambda kv: kv[1])
            lines.append(f"    Wichtigster Lieferant: {best} ({n} wichtige Items)")
        if p.get("longest_wait_s"):
            lines.append(f"    Längste Durststrecke ohne wichtiges Item: {duration(p['longest_wait_s'])}")
        lines.append("")
    if len(players) > 1:
        helper = max(players.items(), key=lambda kv: kv[1].get("found_for_others", 0))
        waiter = max(players.items(), key=lambda kv: kv[1].get("longest_wait_s", 0))
        lines.append(f"🤝 Größter Helfer: {helper[0]} ({helper[1].get('found_for_others', 0)} Items für andere)")
        if waiter[1].get("longest_wait_s"):
            lines.append(f"⏳ Am längsten gewartet: {waiter[0]} ({duration(waiter[1]['longest_wait_s'])})")
    return "\n".join(lines)
