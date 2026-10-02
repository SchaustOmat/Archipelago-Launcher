"""Reads what the Archipelago server saved: the multiworld (.archipelago inside the zip) and its .apsave.

Both are zlib-compressed pickles referencing Archipelago's own classes (NetworkItem, NetworkSlot, ...).
The unpickler below only allows plain containers and turns every Archipelago class into a tuple,
so nothing from the file can run code.
"""
import io
import pickle
import zipfile
import zlib
from pathlib import Path

_SAFE = {
    "builtins": {"set", "frozenset", "dict", "list", "tuple", "int", "float", "str", "bytes", "bool", "complex",
                 "range", "slice"},
    "collections": {"OrderedDict", "defaultdict", "Counter", "deque"},
}


class _Obj(tuple):
    """Stand-in for any Archipelago class: keeps the constructor arguments as tuple items."""

    def __new__(cls, *args, **kwargs):
        return tuple.__new__(cls, args)

    def __setstate__(self, state):
        self.__dict__["state"] = state


class _Unpickler(pickle.Unpickler):
    _stand_ins: dict = {}

    def find_class(self, module, name):
        if name in _SAFE.get(module, ()):
            return super().find_class(module, name)
        return self._stand_ins.setdefault((module, name), type(name, (_Obj,), {}))


def _load(data: bytes):
    return _Unpickler(io.BytesIO(zlib.decompress(data))).load()


def read_session(zip_path: Path) -> dict | None:
    """{"seed", "players": {slot: {"name", "game", "total", "checks", "received": [(sender, flags), ...]}}}
    or None if the files can't be read. "received" holds every item the slot got, own finds included."""
    try:
        with zipfile.ZipFile(zip_path) as z:
            name = next(n for n in z.namelist() if n.endswith(".archipelago"))
            multi = _load(z.read(name)[1:])  # first byte: format version
        saves = list(zip_path.parent.glob("*.apsave"))
        save = _load(saves[0].read_bytes()) if saves else {}
    except (OSError, StopIteration, zipfile.BadZipFile, zlib.error, pickle.UnpicklingError, EOFError,
            ValueError, TypeError, AttributeError, IndexError):
        return None
    players = {}
    for slot, info in multi.get("slot_info", {}).items():
        player_name, game = info[0], info[1]
        checks = save.get("location_checks", {}).get((0, slot), set())
        # (team, slot, True) lists every item the slot received; the False list only those from others.
        received = save.get("received_items", {}).get((0, slot, True))
        if received is None:
            received = save.get("received_items", {}).get((0, slot, False), [])
        players[slot] = {"name": player_name, "game": game, "total": len(multi.get("locations", {}).get(slot, {})),
                         "checks": len(checks), "received": [(item[2], item[3]) for item in received]}
    return {"seed": multi.get("seed_name") or zip_path.stem.removeprefix("AP_"), "players": players}
