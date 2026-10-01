# Archipelago Launcher – Hinweise für Claude

Antworte auf Deutsch, kurz. Python immer mit `py -3.14` bzw. `.venv\Scripts\python`.

## Was das ist
Windows-Launcher (tkinter, PyInstaller-onefile, Inno-Setup) für eine lokale Archipelago-Multiworld mit
**Super Mario 64** (sm64ex Archipelago-Build, aus eigener ROM kompiliert, 60 FPS) und **Ocarina of Time**
(Ship of Harkinian Archipelago 1.4.2). Minecraft ist bewusst nicht drin.

## Bauen / Verteilen
- `.\build.ps1 -Full` → `release\ArchipelagoLauncher-Setup_<ver>.exe` (+ Full-Variante, Zips). Version in
  `aplauncher/config.py` (`APP_VERSION`) erhöhen. Danach `build/`, `dist/`, `*.spec` löschen.
- Installiert pro Benutzer nach `%LOCALAPPDATA%\Programs\ArchipelagoLauncher`; Spiele/Spielstände in
  `C:\APLauncher` (`sessions\` = Host-Spielstände `.apsave`, `soh\Save` = SoH-Saves).
- Server und Tracker hängen per Windows-Job (`jobs.py`) am Launcher und sterben mit ihm.
- **Nie still installieren, solange `ArchipelagoLauncher.exe` oder `ArchipelagoServer.exe` läuft** –
  Inno schließt den Launcher und der Server läuft verwaist weiter (Mitspieler noch verbunden).
- Testen auf anderen Ports (z. B. 38299), nie einen laufenden Server auf 38281 anfassen.
- Bash-Heredocs in dieser Umgebung machen aus `\n` in Python-Strings echte Zeilenumbrüche → Code-Änderungen
  lieber mit dem Edit-Tool, danach `python -c "import aplauncher.gui"` prüfen.

## Aufbau (`aplauncher/`)
- `gui.py` App (Tabs Spielen/Einrichtung/Netzwerk/Log), `widgets.py` animierte Buttons/Pill/Tabs/Toast,
  `theme.py` lila Dark-Theme.
- `install.py` AP-Silent-Install, SoH-Zip + `oot.o2r` aus ROM, MSYS2 + sm64ex-Build (`SM64_PATCHES` in
  config; `launcher:`-Patches aus `patches/`), installiert `tracker.apworld` (Universal Tracker) +
  Brücken-apworld aus `bridge/`.
- `lobby.py` HTTP-Lobby auf demselben Port wie der AP-Server (38281); `host.py` Generieren/Server,
  Port-Test, verwaisten Server finden; `apclient.py` TextOnly-Client für Spielerliste/Log/Fortschritt.
- `overlay.py` + `hud.py` + `goals.py` + `places.py`: Overlay-Fenster und klick-durchlässiges HUD im Spiel.
  Logik kommt aus `bridge/aplauncher_bridge` (läuft in Archipelago, nutzt Universal Trackers TrackerCore,
  schreibt JSON). Ort: SoH über Sail (`sail.py`, 127.0.0.1:43384, wird in `games.configure_soh` aktiviert),
  Mario über `patches/sm64_report_location.patch` → `%APPDATA%\sm64ex\aplauncher_location.txt`.
- `tests/flow_test.py` End-to-End ohne Spiele.

## Offene Ideen
- Schritt-für-Schritt-Tempelanleitung im HUD (Weiterschalten über Sail-Flag-Events / Tastenkürzel).
- Kompass-Pfeil (Links Position aus SoH auslesen), echte 3D-Marker (eigener SoH-Build) – aufwendig.
- Radmin/Hamachi-IP automatisch als Freundes-Adresse vorschlagen (Erkennung existiert im Netzwerk-Tab).
