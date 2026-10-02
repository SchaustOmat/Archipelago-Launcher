# Archipelago Launcher (Mario 64 + Ocarina of Time)

Ein Programm für eine lokale Archipelago-Multiworld mit **Super Mario 64** (sm64ex, 60 FPS) und
**Ocarina of Time** (Ship of Harkinian). ROMs werden nie mitgeliefert – jeder wählt seine eigene.

## Für Spieler
1. `ArchipelagoLauncher.exe` starten.
2. Spielername, Spiel und eigene ROM wählen → **Installieren / Prüfen**.
   - Mario 64: ROM USA oder Japan (.z64/.n64/.v64). Das Spiel wird einmalig auf dem PC gebaut (ca. 3–10 Min.).
   - OoT: jede Nicht-Master-Quest-Version. SoH erzeugt daraus einmalig seine Spieldaten.
3. Optional: **Optionen bearbeiten (YAML)** oder **Options Creator**.
4. Adresse des Hosts eintragen → **Beitreten**. Wenn der Host startet: **▶ Spielen**.
   - Mario 64 verbindet sich automatisch.
   - SoH: im Dateiauswahl-Menü „Archipelago“ wählen; Server/Name/Passwort sind schon eingetragen.

## Overlay
**🗺 Overlay** öffnet ein Fenster über dem Spiel: Ziel-Fortschritt, alle gerade erreichbaren Orte
(nach Gebiet) und zuletzt erhaltene Items. Die Logik kommt vom
[Universal Tracker](https://github.com/FarisTheAncient/Archipelago) (`tracker.apworld`), den eine kleine
Brücke (`bridge/aplauncher_bridge`, als apworld installiert) innerhalb von Archipelago ansteuert und als
JSON an den Launcher gibt.

Das **HUD im Spiel** (klick-durchlässig, klebt am Spielfenster) zeigt, was am aktuellen Ort noch offen ist,
plus kurze Dungeon-Tipps (`aplauncher/places.py`). Den Ort liefert bei SoH dessen Sail-Schnittstelle
(der Launcher lauscht auf 127.0.0.1:43384, SoH wird beim Start dafür konfiguriert), bei Mario 64 ein
kleiner Patch (`patches/sm64_report_location.patch`), der das Level in `%APPDATA%\sm64ex` schreibt.

## Weitere Funktionen
- **💡 Hint:** ein Item aus dem eigenen Spiel wählen, der Server verrät den Ort (zeigt Hint-Punkte/Kosten).
- **Benachrichtigungen:** wichtiges Item von jemand anderem oder Ziel erreicht → Meldung im Launcher und
  im HUD, mit Ton (abschaltbar).
- **📊 Statistik** pro Multiworld: Spielzeit, Checks, wer wem geholfen hat, längste Durststrecke.
- **Spielstand-Backups** vor jedem Spielstart (`C:\APLauncher\backups`, Einrichtung → Backups).
- **Updates:** neue GitHub-Releases werden erkannt und auf Klick installiert.
- **Radmin VPN / Hamachi** werden erkannt; deren Adresse wird beim Hosten automatisch angezeigt.

## Für den Host
1. Wie oben installieren (oder Spiel „Kein Spiel (nur hosten)“).
2. **Server hosten** → Lobby öffnet sich auf Port 38281. Die Adresse für Freunde steht im Fenster.
3. **Port testen**. Falls nicht erreichbar: Port 38281 TCP im Router weiterleiten, oder **playit.gg** nutzen.
4. Wenn alle drin sind: **Multiworld starten**.
5. Später weiterspielen: **Spielstand fortsetzen …**

Alles wird nach `C:\APLauncher` installiert (Pfad ohne Leerzeichen, wegen MSYS2).

## Bauen
```powershell
.\build.ps1          # dist\ArchipelagoLauncher.exe (lädt beim Setup herunter)
.\build.ps1 -Full    # zusätzlich dist\ArchipelagoLauncher-Full.exe mit Archipelago + SoH eingebaut
.\build.ps1 -Full -Public   # Release-Build für GitHub nach release\public
```
Ergebnis: `release\ArchipelagoLauncher-Setup_<version>.exe` (Inno Setup 6 nötig). Ein eigenes Icon für
private Builds kann unter `assets\private\icon.ico`/`icon.png` liegen (nicht im Repo).
Mario 64 kann nicht vorgebaut mitgeliefert werden (die exe enthält Daten aus der ROM).

## Versionen
Archipelago 0.6.7 · SoH Archipelago 1.4.2 · sm64ex `archipelago`-Branch (N00byKing) mit `60fps_ex.patch`.
Test ohne Spiele: `python tests/flow_test.py C:\APLauncher`.

## Lizenz
MIT, siehe `LICENSE`. Archipelago, Ship of Harkinian und sm64ex haben eigene Lizenzen; ROMs werden nie mitgeliefert.
