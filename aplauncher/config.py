"""Paths, pinned versions and persistent settings."""
import json
import os
import sys
from pathlib import Path

APP_NAME = "Archipelago Launcher"
APP_VERSION = "0.4.0"
DEFAULT_PORT = 38281
# MSYS2 and make break on paths with spaces, so the install folder must not contain any.
DEFAULT_ROOT = r"C:\APLauncher"

AP_VERSION = "0.6.7"
AP_URL = f"https://github.com/ArchipelagoMW/Archipelago/releases/download/{AP_VERSION}/Setup.Archipelago.{AP_VERSION}.exe"

SOH_VERSION = "1.4.2"
_SOH_BASE = "https://github.com/HarbourMasters/Archipelago-SoH/releases/download/Soh_1.4.2"
SOH_ZIP_URL = f"{_SOH_BASE}/SoH_Archipelago_1-4-2_Windows.zip"
SOH_APWORLD_URL = f"{_SOH_BASE}/oot_soh.apworld"

# Universal Tracker provides the "what is in logic" calculation for the overlay.
UT_VERSION = "0.3.4"
UT_URL = f"https://github.com/FarisTheAncient/Archipelago/releases/download/Tracker_v{UT_VERSION}/tracker.apworld"

MSYS2_URL ="https://repo.msys2.org/distrib/msys2-x86_64-latest.sfx.exe"
MSYS2_PACKAGES = [
    "unzip", "git", "make", "python3",
    "mingw-w64-x86_64-gcc", "mingw-w64-x86_64-glew",
    "mingw-w64-x86_64-SDL2", "mingw-w64-x86_64-cmake",
]
SM64_REPO = "https://github.com/N00byKing/sm64ex"
SM64_BRANCH = "archipelago"
# 60 FPS (from the sm64ex repo) renders interpolated frames, logic stays at 30.
# "launcher:" patches ship with the launcher (patches/); camera_invert_x adds a config switch.
SM64_PATCHES = ["enhancements/60fps_ex.patch", "launcher:sm64_camera_invert_x.patch"]

# playit 1.x ships as an MSI (service + tray + CLI); the bare exe is only the headless daemon.
PLAYIT_MSI_URL = "https://github.com/playit-cloud/playit-agent/releases/latest/download/playit-windows-x86_64-signed.msi"
PLAYIT_TUNNELS_URL = "https://playit.gg/account/tunnels"

# Games a player can pick. "ap_game" is the name Archipelago uses in YAMLs.
GAMES = {
    "sm64": {"label": "Super Mario 64", "ap_game": "Super Mario 64"},
    "soh": {"label": "Ocarina of Time (Ship of Harkinian)", "ap_game": "Ship of Harkinian"},
}
NO_GAME = "none"  # host only, does not play
GAME_BY_AP_NAME = {g["ap_game"]: key for key, g in GAMES.items()}


def bundle_dir() -> Path:
    """Folder with files PyInstaller packed into the exe (or the source tree)."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


def payload_dir() -> Path:
    """Optional offline payload (installers) bundled into a full package."""
    return bundle_dir() / "payload"


def settings_path() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home())) / "APLauncher"
    base.mkdir(parents=True, exist_ok=True)
    return base / "settings.json"


DEFAULT_SETTINGS = {
    "root": DEFAULT_ROOT,
    "name": "",
    "game": "sm64",
    "roms": {"sm64": "", "soh": ""},
    "address": "localhost:38281",
    "password": "",
    "port": DEFAULT_PORT,
    "sm64_invert_camera_x": False,
}


def load_settings() -> dict:
    s = json.loads(json.dumps(DEFAULT_SETTINGS))
    try:
        stored = json.loads(settings_path().read_text(encoding="utf-8"))
        roms = {**s["roms"], **stored.get("roms", {})}
        s.update(stored)
        s["roms"] = roms
    except (OSError, ValueError):
        pass
    return s


def save_settings(s: dict) -> None:
    settings_path().write_text(json.dumps(s, indent=2), encoding="utf-8")


class Paths:
    """Everything the launcher installs lives under one root folder."""

    def __init__(self, root: str):
        self.root = Path(root)
        self.ap = self.root / "archipelago"
        self.soh = self.root / "soh"
        self.msys = self.root / "msys64"
        self.sm64 = self.root / "sm64ex"
        self.sessions = self.root / "sessions"
        self.yamls = self.root / "yamls"
        self.downloads = self.root / "downloads"

    @property
    def ap_generate(self):
        return self.ap / "ArchipelagoGenerate.exe"

    @property
    def ap_server(self):
        return self.ap / "ArchipelagoServer.exe"

    @property
    def soh_exe(self):
        return self.soh / "soh.exe"

    @property
    def sm64_exe(self):
        return self.sm64 / "build" / "us_pc" / "sm64.us.f3dex2e.exe"

    def sm64_exe_for(self, region: str):
        return self.sm64 / "build" / f"{region}_pc" / f"sm64.{region}.f3dex2e.exe"

    def yaml_for(self, game: str) -> Path:
        return self.yamls / f"{game}.yaml"
