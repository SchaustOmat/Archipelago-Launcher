import argparse
import asyncio
import ctypes
import json
import os
import time
import traceback


def _parent_alive(pid: int) -> bool:
    # os.kill(pid, 0) would terminate the process on Windows, so ask the kernel instead.
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    code = ctypes.c_ulong()
    kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
    kernel32.CloseHandle(handle)
    return code.value == 259  # STILL_ACTIVE


def run(*argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--connect", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--password", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--yaml-dir", default=None)
    parser.add_argument("--parent-pid", type=int, default=0)
    args = parser.parse_args(list(argv))

    def write(obj):
        obj["ts"] = time.time()
        tmp = args.out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f)
        os.replace(tmp, args.out)

    write({"status": "starting"})
    try:
        from CommonClient import server_loop
        from worlds.tracker.TrackerClient import TrackerGameContext
    except Exception:
        write({"status": "error", "error": "Universal Tracker fehlt:\n" + traceback.format_exc()})
        return

    class BridgeContext(TrackerGameContext):
        slot_data: dict = {}
        last_error = ""

        def on_package(self, cmd, data):
            if cmd == "Connected":
                self.slot_data = data.get("slot_data") or {}
            if cmd == "ConnectionRefused":
                write({"status": "error", "error": "Verbindung abgelehnt: " + ", ".join(data.get("errors", []))})
            super().on_package(cmd, data)

        def updateTracker(self):
            ret = super().updateTracker()
            try:
                self.snapshot(ret)
            except Exception:
                write({"status": "error", "error": traceback.format_exc()})
            return ret

        def snapshot(self, ret):
            core = self.tracker_core
            world = core.get_current_world()
            if world is None or ret.state is None:
                write({"status": "error", "error": core.gen_error or "Logik konnte nicht erzeugt werden."})
                return
            mw, player = core.multiworld, core.player_id

            def region_of(name):
                try:
                    loc = mw.get_location(name, player)
                    return loc.parent_region.name if loc.parent_region else ""
                except KeyError:
                    return ""

            hinted = {loc.name for loc in ret.hinted_locations}
            received = []
            for item in self.items_received[-15:]:
                received.append({"item": self.item_names.lookup_in_slot(item.item, self.slot),
                                 "from": self.player_names.get(item.player, "?"),
                                 "location": self.location_names.lookup_in_slot(item.location, item.player)})
            write({
                "status": "ok",
                "game": self.game,
                "slot_name": self.player_names.get(self.slot, ""),
                "slot_data": self.slot_data,
                "checked": len(self.checked_locations),
                "total": len(self.checked_locations) + len(self.missing_locations),
                "in_logic": [{"name": n, "region": region_of(n), "hinted": n in hinted}
                             for n in ret.in_logic_locations],
                "glitched": len(ret.glitched_locations),
                "items": dict(ret.all_items),
                "prog_items": dict(ret.prog_items),
                "events": ret.events,
                "beaten": bool(mw.has_beaten_game(ret.state, player)),
                "received": received,
            })

    async def main():
        ctx = BridgeContext(args.connect, args.password)
        ctx.auth = args.name
        if args.yaml_dir:
            ctx.tracker_core.player_folder_override = args.yaml_dir
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
        ctx.run_generator()
        while not ctx.exit_event.is_set():
            if args.parent_pid and not _parent_alive(args.parent_pid):
                break
            try:
                await asyncio.wait_for(ctx.exit_event.wait(), 2)
            except asyncio.TimeoutError:
                pass
        await ctx.shutdown()

    try:
        asyncio.run(main())
    except Exception:
        write({"status": "error", "error": traceback.format_exc()})
