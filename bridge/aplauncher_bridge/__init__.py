"""APLauncher bridge: runs inside Archipelago and exposes Universal Tracker's logic to the launcher overlay.

Start: ArchipelagoLauncher.exe "APLauncher Bridge" -- --connect HOST:PORT --name SLOT --out FILE
       [--password PW] [--yaml-dir DIR] [--parent-pid PID]
It writes a JSON snapshot to FILE after every tracker update.
"""
from worlds.LauncherComponents import Component, Type, components


def launch(*args):
    from .bridge import run
    run(*args)


components.append(Component("APLauncher Bridge", func=launch, component_type=Type.HIDDEN))
