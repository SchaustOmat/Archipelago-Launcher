# Archipelago Launcher (Mario 64 + Ocarina of Time)

🇬🇧 **English** · 🇩🇪 [Deutsch](README.de.md) · Full guide: [GUIDE.txt](GUIDE.txt)

A one-stop Windows launcher for a local [Archipelago](https://archipelago.gg) multiworld with
**Super Mario 64** (sm64ex, 60 FPS) and **Ocarina of Time** (Ship of Harkinian). Install, host, join and play
from one window – no command line, no manual YAML juggling. ROMs are never included; everyone uses their own.

## For players
1. Download the setup from [Releases](https://github.com/SchaustOmat/Archipelago-Launcher/releases/latest),
   install it and start the launcher. Language: Setup → "Sprache / Language".
2. Pick a player name, your game and your own ROM → **Install / Check**.
   - Mario 64: USA or Japan ROM (.z64/.n64/.v64). The game is built on your PC once (about 10–15 min).
   - OoT: any non-Master-Quest version. SoH creates its game data from it once.
3. Optional: **Edit YAML** or **Options Creator** for game settings.
4. Enter the host's address → **Join**. When the host starts: **▶ Play**.
   - Mario 64 connects by itself.
   - SoH: choose "Archipelago" in the file select menu; server, name and password are already filled in.

The setup comes in two flavours: `ArchipelagoLauncher-Setup` (small, downloads Archipelago and SoH while
setting up) and `ArchipelagoLauncher-Full-Setup` (Archipelago and SoH included). Windows may show
"Windows protected your PC" because the program is not signed: "More info" → "Run anyway".

## Overlay and in-game HUD
**🗺 Overlay** opens a window on top of the game: goal progress, every location currently in logic (by area)
and recently received items. The logic comes from the
[Universal Tracker](https://github.com/FarisTheAncient/Archipelago) (`tracker.apworld`), driven inside
Archipelago by a small bridge (`bridge/aplauncher_bridge`, installed as an apworld) that hands it to the
launcher as JSON.

The **in-game HUD** (click-through, glued to the game window) shows what is still open where you are, plus short
dungeon tips (`aplauncher/places.py`). SoH reports the location through its Sail interface (the launcher
listens on 127.0.0.1:43384, SoH is configured for it on start); Mario 64 through a small patch
(`patches/sm64_report_location.patch`) that writes the level to `%APPDATA%\sm64ex`.

## More features
- **💡 Hint:** pick an item of your own game and the server tells you where it is (shows hint points and cost).
- **Notifications:** important item from someone else or a goal reached → message in the launcher and the HUD,
  with a sound (can be turned off).
- **📊 Statistics** per multiworld: play time, checks, who helped whom, longest wait for an important item.
  The host's numbers come straight from the server's save file.
- **Save backups** before every game start (`C:\APLauncher\backups`, Setup → Backups).
- **Updates:** new GitHub releases are detected and installed with one click.
- **Radmin VPN / Hamachi** are detected; their address is shown automatically when hosting.
- **German and English** interface.

## For the host
1. Install as above (or pick "No game (host only)").
2. **Host server** → a lobby opens on port 38281. The address for friends is shown in the window.
3. **Test port**. If it is not reachable: forward TCP port 38281 in your router, use Radmin VPN/Hamachi, or
   **playit.gg** (set up from the launcher).
4. When everyone is in: **Start multiworld**.
5. Continue later: **Resume save …** (sorted by last played, with creation and play times; Delete moves a
   save to the recycle bin).

Everything is installed to `C:\APLauncher` (a path without spaces, because of MSYS2).

## Building
Python 3.14, PyInstaller and [Inno Setup 6](https://jrsoftware.org/isinfo.php):
```powershell
.\build.ps1                 # dist\ArchipelagoLauncher.exe (downloads at setup)
.\build.ps1 -Full           # also dist\ArchipelagoLauncher-Full.exe with Archipelago + SoH bundled
.\build.ps1 -Full -Public   # release build for GitHub into release\public
```
Result: `release\ArchipelagoLauncher-Setup_<version>.exe`. Private builds can use their own icon from
`assets\private\icon.ico`/`icon.png` (not in the repo). Mario 64 can't be shipped prebuilt (the exe contains
data from the ROM).

Tests without games: `python tests/flow_test.py C:\APLauncher` (uses port 38299) and
`python tests/i18n_check.py` (every text has an English translation in `aplauncher/en.py`).

## Translations
The German text in the code is the source; `aplauncher/en.py` maps it to English. Another language would be
one more file like `en.py` plus an entry in `aplauncher/i18n.py`.

## Versions
Archipelago 0.6.7 · SoH Archipelago 1.4.2 · sm64ex `archipelago` branch (N00byKing) with `60fps_ex.patch`.

## License
MIT, see `LICENSE`. Archipelago, Ship of Harkinian and sm64ex have their own licenses; ROMs are never included.
