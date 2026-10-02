# Archipelago Launcher – Hinweise für Claude

Antworte auf Deutsch, kurz. Python immer mit `py -3.14` bzw. `.venv\Scripts\python`.

## Was das ist
Windows-Launcher (tkinter, PyInstaller-onefile, Inno-Setup) für eine lokale Archipelago-Multiworld mit
**Super Mario 64** (sm64ex Archipelago-Build, aus eigener ROM kompiliert, 60 FPS) und **Ocarina of Time**
(Ship of Harkinian Archipelago 1.4.2). Minecraft ist bewusst nicht drin. Das Repo ist öffentlich: keine
persönlichen Daten (Namen, IPs, Pfade mit Benutzernamen) und keine fremden Marken/Bilder einchecken.

## Bauen / Verteilen
- `.\build.ps1 -Full` → `release\ArchipelagoLauncher-Setup_<ver>.exe` (+ Full-Variante, Zips), private
  Version: nimmt `assets\private\icon.*` (nicht in git), falls vorhanden.
- `.\build.ps1 -Full -Public` → dasselbe in `release\public\` mit dem neutralen Icon; nur diese Dateien
  kommen in GitHub-Releases (Tag `v<ver>`). Nur Public-Builds installieren Updates selbst
  (`assets\public_build`-Marker), private zeigen nur die Release-Seite.
- Version in `aplauncher/config.py` (`APP_VERSION`) erhöhen; Update-Check fragt
  `config.UPDATE_REPO` (GitHub `owner/repo`). Danach `build/`, `dist/`, `*.spec` löschen.
- Installiert pro Benutzer nach `%LOCALAPPDATA%\Programs\ArchipelagoLauncher`; Spiele/Spielstände in
  `C:\APLauncher` (`sessions\` = Host-Spielstände `.apsave`, `soh\Save` = SoH-Saves, `backups\`).
- Server und Tracker hängen per Windows-Job (`jobs.py`) am Launcher und sterben mit ihm.
- **Nie still installieren, solange `ArchipelagoLauncher.exe` oder `ArchipelagoServer.exe` läuft** –
  Inno schließt den Launcher und der Server läuft verwaist weiter (Mitspieler noch verbunden).
- Testen auf anderen Ports (z. B. 38299), nie einen laufenden Server auf 38281 anfassen.
- Bash-Heredocs in dieser Umgebung machen aus `\n` (und `\b`) in Python-Strings echte Steuerzeichen →
  Code-Änderungen lieber mit dem Edit-Tool, danach `python -c "import aplauncher.gui"` prüfen.

## Sprachen
Oberfläche Deutsch/Englisch (`i18n.py`): deutscher Text im Code ist die Quelle, mit `_("...")` markiert
(Platzhalter nur über `.format(name=...)`, keine f-Strings in `_()`), Übersetzung in `en.py`. Neue/geänderte
Texte → `python tests/i18n_check.py --missing`. Sprache wird beim Start gesetzt (Einstellung `lang`, sonst
Windows-Sprache). `_` nie als Wegwerf-Variable benutzen. README.md englisch, README.de.md + ANLEITUNG.txt
deutsch, GUIDE.txt englisch.

## Aufbau (`aplauncher/`)
- `gui.py` App (Tabs Spielen/Einrichtung/Netzwerk/Log), `dialogs.py` modale Fenster (Fortsetzen, Hint,
  Statistik, Backups), `widgets.py` animierte Buttons/Pill/Tabs/Toast, `theme.py` lila Dark-Theme.
- `install.py` AP-Silent-Install, SoH-Zip + `oot.o2r` aus ROM, MSYS2 + sm64ex-Build (`SM64_PATCHES` in
  config; `launcher:`-Patches aus `patches/`), installiert `tracker.apworld` (Universal Tracker) +
  Brücken-apworld aus `bridge/`.
- `lobby.py` HTTP-Lobby auf demselben Port wie der AP-Server (38281); `host.py` Generieren/Server,
  Port-Test, verwaisten Server finden; `apclient.py` TextOnly-Client für Spielerliste/Log/Fortschritt,
  Hint-Punkte und `!hint` (`say`), Ereignisse für Benachrichtigungen, füttert `stats.py`
  (pro Seed in `%APPDATA%\APLauncher\stats`).
- `backup.py` sichert vor jedem Spielstart SoH-/SM64-Saves und `.apsave` (letzte 20, mit Manifest).
- `updates.py` GitHub-Release-Check + Download des Setups.
- `overlay.py` + `hud.py` + `goals.py` + `places.py`: Overlay-Fenster und klick-durchlässiges HUD im Spiel.
  Logik kommt aus `bridge/aplauncher_bridge` (läuft in Archipelago, nutzt Universal Trackers TrackerCore,
  schreibt JSON). Ort: SoH über Sail (`sail.py`, 127.0.0.1:43384, wird in `games.configure_soh` aktiviert),
  Mario über `patches/sm64_report_location.patch` → `%APPDATA%\sm64ex\aplauncher_location.txt`.
- `tests/flow_test.py` End-to-End ohne Spiele (Port 38299, Sessions/Statistik im Temp-Ordner).

## Offene Ideen
- Aufräumen + Plugin-System pro Spiel (`gui.py` aufteilen, SM64/SoH-Spezifisches nach `games/<name>/`),
  damit weitere Spiele leicht dazukommen. Neue Spiele brauchen kein Overlay/HUD.
- Schritt-für-Schritt-Tempelanleitung im HUD (Weiterschalten über Sail-Flag-Events / Tastenkürzel).
- Kompass-Pfeil (Links Position aus SoH auslesen), echte 3D-Marker (eigener SoH-Build) – aufwendig.
