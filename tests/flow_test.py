"""End-to-end check without games: lobby -> generate -> server -> watchers -> fake game client.

Needs an installed root (Archipelago + yamls). Run: python tests/flow_test.py C:\\APLauncher
"""
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from websockets.asyncio.client import connect

from aplauncher import apclient, host, lobby
from aplauncher.config import Paths

PORT = 38299
paths = Paths(sys.argv[1] if len(sys.argv) > 1 else r"C:\APLauncher")
log = lambda m: print("  |", m) if not m.startswith(" ") else None

# 1. lobby with a local host player and a remote player
lob = lobby.Lobby(PORT, "pw")
lob.start()
assert lob.add_player("Mario", "sm64", paths.yaml_for("sm64").read_text(encoding="utf-8"), local=True) is None
addr = f"127.0.0.1:{PORT}"
try:
    lobby.join(addr, "Link", "soh", "x", "cid1", "wrong")
    raise SystemExit("wrong password accepted")
except lobby.LobbyError as e:
    print("wrong password rejected:", e)
snap = lobby.join(addr, "Link", "soh", paths.yaml_for("soh").read_text(encoding="utf-8"), "cid1", "pw")
assert [p["name"] for p in snap["players"]] == ["Link", "Mario"], snap
try:
    lobby.join(addr, "Mario", "soh", "x", "cid2", "pw")
    raise SystemExit("duplicate name accepted")
except lobby.LobbyError as e:
    print("duplicate rejected:", e)
print("lobby ok:", [(p["name"], p["game"], p["online"]) for p in lobby.get_state(addr, "Link")["players"]])

# 2. generate + server on the same port
zip_path = host.generate(paths, lob.yamls(), lambda m: None)
print("generated", zip_path.name, host.session_players(zip_path))
lob.stop()
srv = host.Server(paths, zip_path, PORT, "pw", lambda m: None)
srv.start()
time.sleep(4)

# 3. watchers for both players
events = {"Mario": [], "Link": []}
watchers = [apclient.APWatcher(addr, n, "pw", lambda k, d, n=n: events[n].append((k, d))) for n in events]
for w in watchers:
    w.start()
time.sleep(4)


# 4. fake SM64 game client: connects as Mario and checks a few locations
async def fake_game():
    async with connect(f"ws://{addr}", max_size=None) as ws:
        await ws.recv()
        await ws.send(json.dumps([{"cmd": "Connect", "password": "pw", "game": "Super Mario 64", "name": "Mario",
                                   "uuid": uuid.uuid4().hex, "items_handling": 7, "tags": ["AP"],
                                   "version": {"major": 0, "minor": 6, "build": 7, "class": "Version"}}]))
        while True:
            msgs = json.loads(await ws.recv())
            con = next((m for m in msgs if m["cmd"] == "Connected"), None)
            if con:
                break
        await ws.send(json.dumps([{"cmd": "LocationChecks", "locations": con["missing_locations"][:5]}]))
        await asyncio.sleep(4)

asyncio.run(fake_game())
time.sleep(2)

for n, ev in events.items():
    players = [d for k, d in ev if k == "players"]
    logs = [d for k, d in ev if k == "log"]
    print(f"--- watcher {n}: states={[d['text'] for k, d in ev if k == 'state']}")
    print("   last players:", players[-1] if players else None)
    print("   log lines:", len(logs))
    for line in logs[:12]:
        print("     ", line)

for w in watchers:
    w.stop()
srv.stop()
print("apsave exists:", any(zip_path.parent.glob("*.apsave")))
