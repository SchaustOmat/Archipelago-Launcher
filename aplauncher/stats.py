"""Per-multiworld statistics.

Item counts are complete: the host reads them from the server's save, every other launcher gets them from
the server on connect (each publishes its own tally). Play time and the longest wait between important
items are only measured while the launcher is connected. Stored per seed in
%APPDATA%\\APLauncher\\stats\\<seed>.json, so resuming a multiworld keeps adding to it.
"""
import json
import time
from datetime import datetime
from pathlib import Path

from . import config, i18n
from .i18n import _

FLAG_PROGRESSION = 0b001
SAVE_EVERY_S = 20


def stats_dir() -> Path:
    d = config.settings_path().parent / "stats"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _player(game="") -> dict:
    # received() adds "from"/"prog_from": sender name -> items (of those: progression) this player got from
    # them. They come from the server's complete item list, so they also cover time without the launcher.
    return {"game": game, "longest_wait_s": 0, "checks": 0, "total": 0, "goal_at": None}


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

    def received(self, name: str, by_sender: dict, prog_by_sender: dict):
        """Complete tally of what a player got from others (from the server, published by their launcher)."""
        p = self._p(name)
        if (p.get("from"), p.get("prog_from")) != (by_sender, prog_by_sender):
            p["from"], p["prog_from"] = dict(by_sender), dict(prog_by_sender)
            self._changed()

    def item_sent(self, finder: str, receiver: str, flags: int):
        """Live event, only used for the longest wait between progression items."""
        if flags & FLAG_PROGRESSION:
            r = self._p(receiver)
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


def tally(received, slot: int) -> tuple[dict, dict]:
    """Items a slot got from other players, by sender slot: (all, progression only).
    received: (sender slot, flags) of every item the slot got."""
    got, prog = {}, {}
    for sender, flags in received:
        if sender in (0, slot):  # 0 = server (start inventory), own slot = found it yourself
            continue
        got[sender] = got.get(sender, 0) + 1
        if flags & FLAG_PROGRESSION:
            prog[sender] = prog.get(sender, 0) + 1
    return got, prog


def _from_save(run: dict, session: dict):
    """Overwrite counts with the server's save, which knows everything that ever happened."""
    names = {slot: p["name"] for slot, p in session["players"].items()}
    for slot, sp in session["players"].items():
        p = run["players"].setdefault(sp["name"], _player(sp["game"]))
        got, prog = tally(sp["received"], slot)
        p.update(game=sp["game"], checks=sp["checks"], total=sp["total"],
                 **{"from": {names.get(s, _("Spieler {n}").format(n=s)): n for s, n in got.items()},
                    "prog_from": {names.get(s, _("Spieler {n}").format(n=s)): n for s, n in prog.items()}})


def list_runs(sessions_dir: Path | None = None) -> list[dict]:
    """Newest first. With the host's sessions folder, counts come from the saved multiworlds."""
    from . import apsave
    runs = {}
    for f in stats_dir().glob("*.json"):
        try:
            run = json.loads(f.read_text(encoding="utf-8"))
            runs[run["seed"]] = run
        except (OSError, ValueError, KeyError):
            continue
    if sessions_dir and sessions_dir.is_dir():
        for zip_path in sessions_dir.glob("*/AP_*.zip"):
            session = apsave.read_session(zip_path)
            if not session:
                continue
            created = datetime.fromtimestamp(zip_path.stat().st_mtime).isoformat(timespec="seconds")
            played = max(f.stat().st_mtime for f in [zip_path, *zip_path.parent.glob("*.apsave")])
            run = runs.setdefault(session["seed"], {"seed": session["seed"], "started": created,
                                                    "play_seconds": 0, "players": {}})
            run["started"] = min(run.get("started") or created, created)
            run["updated"] = max(run.get("updated") or "",
                                 datetime.fromtimestamp(played).isoformat(timespec="seconds"))
            _from_save(run, session)
    return sorted(runs.values(), key=lambda r: r.get("updated", r.get("started", "")), reverse=True)


def duration(seconds: float) -> str:
    m = int(seconds) // 60
    return f"{m // 60} h {m % 60:02d} min" if m >= 60 else f"{m} min"


def _date(iso: str | None) -> str:
    try:
        return i18n.date(datetime.fromisoformat(iso))
    except (TypeError, ValueError):
        return "?"


def run_title(run: dict) -> str:
    names = ", ".join(run.get("players", {})) or "?"
    return f"{_date(run.get('started'))}  –  {names}"


def report(run: dict) -> str:
    players = run.get("players", {})
    # What X found for others = what everyone else got from X.
    found = {name: sum(p.get("from", {}).get(name, 0) for p in players.values()) for name in players}
    lines = [_("Gestartet: {start}    Zuletzt: {last}").format(start=_date(run.get("started")),
                                                              last=_date(run.get("updated"))),
             _("Spielzeit (Launcher verbunden): {time}").format(time=duration(run.get("play_seconds", 0))), ""]
    for name, p in sorted(players.items(), key=lambda kv: -kv[1].get("checks", 0)):
        pct = f" ({100 * p['checks'] // p['total']}%)" if p.get("total") else ""
        got, prog = sum(p.get("from", {}).values()), sum(p.get("prog_from", {}).values())
        lines.append(f"■ {name}  ·  {p.get('game', '')}")
        lines.append(f"    Checks: {p.get('checks', 0)}/{p.get('total', 0)}{pct}"
                     + ("    " + _("🏆 Ziel: {date}").format(date=_date(p["goal_at"])) if p.get("goal_at") else ""))
        lines.append("    " + _("Für andere gefunden: {found}    Von anderen bekommen: {got} (davon wichtig: {prog})")
                     .format(found=found[name], got=got, prog=prog))
        if p.get("prog_from"):
            best, n = max(p["prog_from"].items(), key=lambda kv: kv[1])
            lines.append("    " + _("Wichtigster Lieferant: {name} ({n} wichtige Items)").format(name=best, n=n))
        if p.get("longest_wait_s"):
            lines.append("    " + _("Längste Durststrecke ohne wichtiges Item: {time}").format(
                time=duration(p["longest_wait_s"])))
        lines.append("")
    if len(players) > 1:
        helper = max(found.items(), key=lambda kv: kv[1])
        waiter = max(players.items(), key=lambda kv: kv[1].get("longest_wait_s", 0))
        if helper[1]:
            lines.append(_("🤝 Größter Helfer: {name} ({n} Items für andere)").format(name=helper[0], n=helper[1]))
        if waiter[1].get("longest_wait_s"):
            lines.append(_("⏳ Am längsten gewartet: {name} ({time})").format(
                name=waiter[0], time=duration(waiter[1]["longest_wait_s"])))
    missing = [n for n, p in players.items() if "from" not in p]
    if missing:
        lines.append("\n" + _("Noch keine Daten von: {names} (deren Launcher muss einmal verbunden sein).").format(
            names=", ".join(missing)))
    return "\n".join(lines)
