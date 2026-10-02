"""A text-only Archipelago client used for the player list, live log and progress.

It connects as the player's own slot with the TextOnly tag, so it never touches items.
Each launcher publishes its own progress and whether its game is connected into the
server's data storage (key APL_<team>_<slot>); every launcher subscribes to all of them.
"""
import asyncio
import json
import threading
import uuid

from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from . import config, stats

NON_GAME_TAGS = {"TextOnly", "Tracker", "HintGame"}
CLIENT_GOAL = 30
STATUS_TEXT = {0: "offline", 5: "verbunden", 10: "bereit", 20: "spielt", 30: "Ziel erreicht"}


class APWatcher:
    def __init__(self, address: str, slot_name: str, password: str, emit):
        self.address = address.strip()
        self.slot_name = slot_name
        self.password = password or None
        # emit(kind, data): "log", "players", "state", "error", "hints" (points/cost), "received" (item for me
        # from someone else: {"item", "sender", "progression"}), "goal" (player name)
        self.emit = emit
        self.loop = asyncio.new_event_loop()
        self.ws = None
        self.stopped = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        # session data
        self.team = 0
        self.slot = 0
        self.players = {}       # slot -> {"name", "game"}
        self.status = {}        # slot -> client status
        self.launcher = {}      # slot -> {"checked", "total", "game"}
        self.checked = set()
        self.total = 0
        self.game_clients = 0
        self.item_names = {}    # game -> {id: name}
        self.location_names = {}
        self.hint_cost_pct = 0
        self.hint_points = 0
        self.stats: stats.RunStats | None = None

    @property
    def my_game(self) -> str:
        return self.players.get(self.slot, {}).get("game", "")

    @property
    def hint_cost(self) -> int:
        """Same formula as the server: a percentage of this slot's location count, at least 1."""
        if not self.hint_cost_pct:
            return 0
        return max(1, int(self.hint_cost_pct * 0.01 * self.total))

    def my_item_names(self) -> list[str]:
        return sorted(self.item_names.get(self.my_game, {}).values(), key=str.lower)

    def say(self, text: str):
        """Chat message or server command (e.g. !hint) as this slot."""
        if self.ws:
            asyncio.run_coroutine_threadsafe(self.send({"cmd": "Say", "text": text}), self.loop)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stopped = True
        if self.ws:
            asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop)

    # ----- connection -----
    def _urls(self):
        a = self.address
        if a.startswith(("ws://", "wss://")):
            return [a]
        if ":" not in a:
            a += f":{config.DEFAULT_PORT}"
        return [f"ws://{a}", f"wss://{a}"]

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._main())

    async def _main(self):
        announced = False
        while not self.stopped:
            last = None
            for url in self._urls():
                try:
                    async with connect(url, max_size=None, ping_interval=20, open_timeout=8) as ws:
                        self.ws = ws
                        await self._session(ws)
                    if not self.stopped:
                        self.emit("state", {"connected": False, "text": "Verbindung zum Server getrennt, verbinde neu ..."})
                    announced = False
                    break
                except FatalError as e:
                    self.emit("error", str(e))
                    return
                except (OSError, WebSocketException, asyncio.TimeoutError) as e:
                    last = e
            else:
                if not announced and not self.stopped:
                    self.emit("state", {"connected": False, "text": f"Server nicht erreichbar, versuche weiter ... ({last})"})
                    announced = True
            if self.stopped:
                return
            await asyncio.sleep(3)

    async def send(self, *cmds):
        await self.ws.send(json.dumps(list(cmds)))

    async def _session(self, ws):
        clock = asyncio.create_task(self._count_time())
        try:
            async for raw in ws:
                for msg in json.loads(raw):
                    await self._handle(msg)
        finally:
            clock.cancel()
            if self.stats:
                self.stats.save()

    async def _count_time(self, step=30):
        while True:
            await asyncio.sleep(step)
            if self.stats:
                self.stats.add_time(step)

    async def _handle(self, msg):
        cmd = msg.get("cmd")
        if cmd == "RoomInfo":
            self.hint_cost_pct = msg.get("hint_cost", 0)
            if msg.get("seed_name") and (self.stats is None or self.stats.data["seed"] != msg["seed_name"]):
                self.stats = stats.RunStats(msg["seed_name"])
            games = [g for g in msg.get("games", []) if g not in self.item_names]
            if games:
                await self.send({"cmd": "GetDataPackage", "games": games})
            await self.send({"cmd": "Connect", "password": self.password, "game": "", "name": self.slot_name,
                             "uuid": uuid.uuid4().hex, "items_handling": 0, "tags": ["TextOnly", "APLauncher"],
                             "slot_data": False,
                             "version": {"major": 0, "minor": 6, "build": 7, "class": "Version"}})
        elif cmd == "DataPackage":
            for game, pkg in msg["data"]["games"].items():
                self.item_names[game] = {v: k for k, v in pkg.get("item_name_to_id", {}).items()}
                self.location_names[game] = {v: k for k, v in pkg.get("location_name_to_id", {}).items()}
        elif cmd == "ConnectionRefused":
            errs = msg.get("errors", [])
            text = {"InvalidSlot": f"'{self.slot_name}' ist in der laufenden Multiworld nicht dabei. "
                                   "Der Host muss 'Beenden' und dann 'Server hosten' klicken; "
                                   "danach hier 'Beenden' und 'Beitreten'.",
                    "InvalidPassword": "Falsches Server-Passwort."}
            raise FatalError(" ".join(text.get(e, e) for e in errs) or "Verbindung abgelehnt.")
        elif cmd == "Connected":
            self.team, self.slot = msg["team"], msg["slot"]
            self.players = {int(s): {"name": i["name"], "game": i["game"]}
                            for s, i in msg.get("slot_info", {}).items() if i.get("type", 1) == 1}
            for p in msg.get("players", []):
                if p["team"] == self.team and p["slot"] in self.players:
                    self.players[p["slot"]]["name"] = p["alias"] or p["name"]
            self.checked = set(msg.get("checked_locations", []))
            self.total = len(self.checked) + len(msg.get("missing_locations", []))
            self.hint_points = msg.get("hint_points", 0)
            if self.stats:
                self.stats.set_players(self.players)
            self._emit_hints()
            keys =[k for s in self.players for k in (f"_read_client_status_{self.team}_{s}",
                                                      f"APL_{self.team}_{s}")]
            await self.send({"cmd": "SetNotify", "keys": keys}, {"cmd": "Get", "keys": keys})
            await self._publish()
            self.emit("state", {"connected": True, "text": "Mit dem Server verbunden."})
            self._emit_players()
        elif cmd == "RoomUpdate":
            if "hint_points" in msg:
                self.hint_points = msg["hint_points"]
                self._emit_hints()
            if "hint_cost" in msg:
                self.hint_cost_pct = msg["hint_cost"]
                self._emit_hints()
            if "checked_locations" in msg:
                self.checked.update(msg["checked_locations"])
                await self._publish()
            if "players" in msg:
                for p in msg["players"]:
                    if p["team"] == self.team and p["slot"] in self.players:
                        self.players[p["slot"]]["name"] = p["alias"] or p["name"]
                self._emit_players()
        elif cmd in ("Retrieved", "SetReply"):
            values = msg.get("keys", {}) if cmd == "Retrieved" else {msg["key"]: msg.get("value")}
            for key, value in values.items():
                self._store(key, value)
            self._emit_players()
        elif cmd == "PrintJSON":
            await self._print(msg)

    def _store(self, key, value):
        try:
            slot = int(key.rsplit("_", 1)[1])
        except (ValueError, IndexError):
            return
        if key.startswith("_read_client_status_"):
            self.status[slot] = value or 0
        elif key.startswith("APL_") and isinstance(value, dict):
            self.launcher[slot] = value
            if self.stats and slot in self.players and value.get("total"):
                self.stats.progress(self.players[slot]["name"], value.get("checked", 0), value["total"])

    def _emit_hints(self):
        self.emit("hints", {"points": self.hint_points, "cost": self.hint_cost})

    async def _publish(self):
        value = {"checked": len(self.checked), "total": self.total, "game": self.game_clients > 0}
        self.launcher[self.slot] = value
        await self.send({"cmd": "Set", "key": f"APL_{self.team}_{self.slot}", "default": {},
                         "want_reply": False, "operations": [{"operation": "replace", "value": value}]})
        self._emit_players()

    def _emit_players(self):
        rows = []
        for slot, p in sorted(self.players.items()):
            info = self.launcher.get(slot, {})
            status = self.status.get(slot, 0)
            if status >= CLIENT_GOAL:
                text = "Ziel erreicht"
            elif info.get("game"):
                text = "Spiel verbunden"
            elif status:
                text = "Launcher online"
            else:
                text = "offline"
            total = info.get("total") or 0
            progress = f"{info.get('checked', 0)}/{total} ({100 * info.get('checked', 0) // total}%)" if total else "-"
            rows.append({"name": p["name"], "game": p["game"], "status": text, "progress": progress,
                         "me": slot == self.slot})
        self.emit("players", rows)

    # ----- log -----
    def _name(self, slot):
        return self.players.get(int(slot), {}).get("name", f"Spieler {slot}")

    def _game(self, slot):
        return self.players.get(int(slot), {}).get("game", "")

    def _render(self, parts):
        out = []
        for part in parts:
            t, text = part.get("type"), part.get("text", "")
            if t == "player_id":
                out.append(self._name(text))
            elif t == "item_id":
                out.append(self.item_names.get(self._game(part.get("player", 0)), {}).get(int(text), f"Item {text}"))
            elif t == "location_id":
                out.append(self.location_names.get(self._game(part.get("player", 0)), {}).get(int(text), f"Ort {text}"))
            else:
                out.append(text)
        return "".join(out)

    async def _print(self, msg):
        kind = msg.get("type")
        # Track whether this player's actual game client is connected.
        if kind == "Join" and msg.get("slot") == self.slot and msg.get("team") == self.team:
            if not NON_GAME_TAGS & set(msg.get("tags", [])):
                self.game_clients += 1
                await self._publish()
        elif kind == "Part" and msg.get("slot") == self.slot and msg.get("team") == self.team:
            text = self._render(msg.get("data", []))
            if not any(f"'{t}'" in text for t in NON_GAME_TAGS) and self.game_clients > 0:
                self.game_clients -= 1
                await self._publish()
        elif kind == "ItemSend" and "item" in msg:
            self._item_event(msg)
        elif kind == "Goal" and "slot" in msg:
            if self.stats:
                self.stats.goal(self._name(msg["slot"]))
            self.emit("goal", self._name(msg["slot"]))
        if kind in ("Tutorial",):
            return
        text = self._render(msg.get("data", []))
        if kind in ("Join", "Part") and "'TextOnly'" in text:
            return
        text = self._german(kind, msg) or text
        if text:
            self.emit("log", text)

    def _item_event(self, msg):
        item = msg["item"]
        finder, receiver = item["player"], msg.get("receiving", item["player"])
        flags = item.get("flags", 0)
        if self.stats:
            self.stats.item_sent(self._name(finder), self._name(receiver), flags)
        if receiver == self.slot and finder != self.slot:
            name = self.item_names.get(self._game(receiver), {}).get(item["item"], f"Item {item['item']}")
            self.emit("received", {"item": name, "sender": self._name(finder),
                                   "progression": bool(flags & stats.FLAG_PROGRESSION)})

    def _german(self, kind, msg) -> str | None:
        if kind == "ItemSend" and "item" in msg:
            item = msg["item"]
            finder, receiver = item["player"], msg.get("receiving", item["player"])
            name = self.item_names.get(self._game(receiver), {}).get(item["item"], f"Item {item['item']}")
            where = self.location_names.get(self._game(finder), {}).get(item["location"], "?")
            if finder == receiver:
                return f"{self._name(finder)} hat {name} gefunden ({where})"
            return f"{self._name(finder)} → {self._name(receiver)}: {name} ({where})"
        if kind == "Join" and "slot" in msg:
            return f"{self._name(msg['slot'])} ist mit {self._game(msg['slot'])} beigetreten."
        if kind == "Part" and "slot" in msg:
            return f"{self._name(msg['slot'])} hat das Spiel verlassen."
        if kind == "Goal" and "slot" in msg:
            return f"🏆 {self._name(msg['slot'])} hat das Ziel erreicht!"
        return None


class FatalError(Exception):
    pass
