"""English texts, keyed by the German source text (see i18n.py). tests/i18n_check.py finds missing ones."""

TEXT = {
    # ---------------------------------------------------------------- main window
    "Version {v}": "Version {v}",
    "🎮  Spielen": "🎮  Play",
    "⚙  Einrichtung": "⚙  Setup",
    "🌐  Netzwerk": "🌐  Network",
    "📜  Log": "📜  Log",
    "Verbindung": "Connection",
    "Server-Adresse (vom Host)": "Server address (from the host)",
    "Passwort (optional)": "Password (optional)",
    "🖥  Server hosten": "🖥  Host server",
    "🔗  Beitreten": "🔗  Join",
    "💾  Spielstand fortsetzen": "💾  Resume save",
    "🚀  Multiworld starten": "🚀  Start multiworld",
    "▶  Spielen": "▶  Play",
    "📊  Statistik": "📊  Statistics",
    "Beenden": "Stop",
    "Nicht verbunden.": "Not connected.",
    "Spieler": "Players",
    "Name": "Name",
    "Spiel": "Game",
    "Status": "Status",
    "Fortschritt": "Progress",
    "Du": "You",
    "Spielername (max. 16 Zeichen)": "Player name (max. 16 characters)",
    "Kein Spiel (nur hosten)": "No game (host only)",
    "Nur hosten": "Host only",
    "kein eigenes Spiel": "no game of your own",
    "Durchsuchen …": "Browse …",
    "Installation": "Installation",
    "⬇  Installieren / Prüfen": "⬇  Install / Check",
    "Ändern …": "Change …",
    "Ordner:": "Folder:",
    "Optionen": "Options",
    "📝  YAML bearbeiten": "📝  Edit YAML",
    "📂  Ordner öffnen": "📂  Open folder",
    "🔔 Ton bei wichtigen Items": "🔔 Sound for important items",
    "🎨  SoH Mods / Texturen": "🎨  SoH mods / textures",
    "Adresse für Freunde": "Address for friends",
    "Wird beim Hosten angezeigt. Anklicken kopiert sie. Eigene Adresse (z. B. playit-Adresse) hier festlegen. "
    "Leer = automatisch: Radmin/Hamachi-Adresse, falls vorhanden, sonst Internet-IP:":
        "Shown while hosting. Click it to copy. Set your own address here (e.g. a playit address). "
        "Empty = automatic: Radmin/Hamachi address if there is one, otherwise your internet IP:",
    "Speichern": "Save",
    "Erreichbarkeit": "Reachability",
    "Port": "Port",
    "📡  Port testen": "📡  Test port",
    "🌍  playit.gg einrichten": "🌍  Set up playit.gg",
    "Ohne Portfreigabe im Router: alle nutzen Radmin VPN / Hamachi (Host-Adresse aus dem VPN-Programm) "
    "oder der Host richtet playit.gg ein.":
        "Without port forwarding in the router: everyone uses Radmin VPN / Hamachi (host address from the VPN "
        "program) or the host sets up playit.gg.",
    "Keine ROM nötig.": "No ROM needed.",
    "Bitte die eigene ROM auswählen (.z64/.n64/.v64).": "Please choose your own ROM (.z64/.n64/.v64).",
    "✓ installiert": "✓ installed",
    "● noch nicht installiert": "● not installed yet",
    "Arbeitet …": "Working …",
    "Offline": "Offline",
    "Lobby · {n} Spieler": "Lobby · {n} players",
    "Verbunden": "Connected",
    "Lobby": "Lobby",
    "Startet …": "Starting …",
    "Fehler": "Error",
    "FEHLER: {error}": "ERROR: {error}",
    "ROM auswählen": "Choose ROM",
    "Alle Dateien": "All files",
    "Installationsordner (ohne Leerzeichen)": "Install folder (no spaces)",
    "Ordner": "Folder",
    "Der Ordner darf keine Leerzeichen enthalten (wegen MSYS2/make).":
        "The folder must not contain spaces (because of MSYS2/make).",
    "ROM": "ROM",
    "Installation abgeschlossen.": "Installation finished.",
    "Ohne eigenes Spiel gibt es keine Optionen.": "Without a game of your own there are no options.",
    "Bitte erst 'Installieren / Prüfen' ausführen.": "Please run 'Install / Check' first.",
    "Options Creator gestartet. Die fertige YAML als {path} speichern.":
        "Options Creator started. Save the finished YAML as {path}.",
    "Ship of Harkinian ist noch nicht installiert. Erst OoT wählen und 'Installieren / Prüfen'.":
        "Ship of Harkinian is not installed yet. Choose OoT first and click 'Install / Check'.",
    "Texturpakete (.o2r/.otr) in den mods-Ordner legen. In SoH unter Einstellungen → Mods bzw. "
    "'Alternative Assets' (Taste Tab) aktivieren.":
        "Put texture packs (.o2r/.otr) into the mods folder. Enable them in SoH under Settings → Mods or "
        "'Alternate Assets' (Tab key).",
    "Dein Spiel ist noch nicht installiert. Erst 'Installieren / Prüfen'.":
        "Your game is not installed yet. Run 'Install / Check' first.",
    "Options-YAML fehlt. Erst 'Installieren / Prüfen'.": "Options YAML is missing. Run 'Install / Check' first.",
    "Server läuft noch": "Server still running",
    "Auf Port {port} läuft noch ein Archipelago-Server (z. B. von einem geschlossenen Launcher). Mitspieler sind "
    "evtl. noch damit verbunden.\n\nBeenden? Der Spielstand ist gespeichert und kann fortgesetzt werden.":
        "An Archipelago server is still running on port {port} (e.g. from a launcher that was closed). Other "
        "players may still be connected to it.\n\nStop it? The game is saved and can be resumed.",
    "Alten Archipelago-Server beendet.": "Stopped the old Archipelago server.",
    "Host": "Host",
    "Archipelago ist noch nicht installiert. Erst 'Installieren / Prüfen'.":
        "Archipelago is not installed yet. Run 'Install / Check' first.",
    "Port {port} kann nicht geöffnet werden: {error}": "Port {port} cannot be opened: {error}",
    "Lobby offen auf Port {port}. Freunde tragen deine Adresse ein und klicken 'Beitreten'.":
        "Lobby open on port {port}. Friends enter your address and click 'Join'.",
    "Lobby offen – warte auf Spieler. Dann 'Multiworld starten'.":
        "Lobby open – waiting for players. Then 'Start multiworld'.",
    "{vpn} erkannt: Freunde im selben {vpn}-Netzwerk nutzen {address}. Andere Adresse im Netzwerk-Tab festlegen.":
        "{vpn} detected: friends in the same {vpn} network use {address}. Set a different address in the "
        "Network tab.",
    "📋  Für Freunde: {address}": "📋  For friends: {address}",
    "– erst beim Hosten –": "– shown when hosting –",
    "✓ Adresse kopiert: {address}": "✓ Address copied: {address}",
    "✓ Gespeichert": "✓ Saved",
    "✓ Adresse wird wieder automatisch gewählt": "✓ The address is chosen automatically again",
    "bereit": "ready",
    "beigetreten": "joined",
    "Noch keine Spieler in der Lobby.": "No players in the lobby yet.",
    "Multiworld mit {n} Spieler(n) erstellen und Server starten?\nDanach kann niemand mehr beitreten.":
        "Create the multiworld with {n} player(s) and start the server?\nNobody can join after that.",
    "Multiworld wird erstellt ...": "Creating the multiworld ...",
    "Multiworld wird generiert ...": "Generating the multiworld ...",
    "Server startet ...": "Server starting ...",
    "Fortsetzen": "Resume",
    "Keine gespeicherten Multiworlds gefunden.": "No saved multiworlds found.",
    "Archipelago-Server gestartet.": "Archipelago server started.",
    "Server läuft. Alle können jetzt '▶ Spielen' drücken.": "Server running. Everyone can press '▶ Play' now.",
    "Zum Beitreten bitte ein Spiel auswählen.": "Please choose a game to join.",
    "Beitreten": "Join",
    "Der Host ist unter {address} nicht erreichbar.\n\n• Stimmt die Adresse (mit :Port)?\n• Hat der Host "
    "'Server hosten' geklickt?\n• Beim Host fehlt evtl. die Portfreigabe im Router – dann playit.gg nutzen und "
    "dessen Adresse eintragen.":
        "The host cannot be reached at {address}.\n\n• Is the address right (with :port)?\n• Did the host click "
        "'Host server'?\n• The host may be missing port forwarding in the router – then use playit.gg and enter "
        "its address.",
    "Lobby beigetreten als {name}.": "Joined the lobby as {name}.",
    "In der Lobby – warte, bis der Host die Multiworld startet.":
        "In the lobby – waiting for the host to start the multiworld.",
    "Beim Host ist keine Lobby offen – dort läuft vermutlich schon eine Multiworld. Verbinde mit dem laufenden "
    "Spiel ...":
        "The host has no lobby open – a multiworld is probably running already. Connecting to the running game ...",
    "Lobby nicht erreichbar: {error}": "Lobby not reachable: {error}",
    "Verbinde mit dem Archipelago-Server ...": "Connecting to the Archipelago server ...",
    "Verbunden. Server läuft – '▶ Spielen' drücken.": "Connected. Server running – press '▶ Play'.",
    "Fehler: {error}": "Error: {error}",
    "⭐ {item} von {sender}": "⭐ {item} from {sender}",
    "🏆 {name} hat das Ziel erreicht!": "🏆 {name} reached their goal!",
    "Die Item-Liste ist noch nicht geladen. Gleich nochmal versuchen.":
        "The item list has not loaded yet. Try again in a moment.",
    "Spiel starten": "Start game",
    "Spielstände gesichert (Einrichtung → Backups).": "Saves backed up (Setup → Backups).",
    "Backup fehlgeschlagen: {error}": "Backup failed: {error}",
    "Super Mario 64 gestartet (verbindet sich automatisch).": "Super Mario 64 started (connects by itself).",
    "Ship of Harkinian gestartet. Im Dateiauswahl-Menü 'Archipelago' wählen; Server, Name und Passwort sind "
    "schon eingetragen.":
        "Ship of Harkinian started. Choose 'Archipelago' in the file select menu; server, name and password are "
        "already filled in.",
    "Bitte einmal 'Installieren / Prüfen' klicken (Overlay-Logik fehlt noch).":
        "Please click 'Install / Check' once (the overlay logic is still missing).",
    "Overlay geöffnet. Im Spiel erscheint oben rechts das HUD mit dem, was hier noch offen ist.":
        "Overlay opened. In the game, the HUD in the top right shows what is still open where you are.",
    "Teste, ob Port {port} aus dem Internet erreichbar ist ...":
        "Testing whether port {port} is reachable from the internet ...",
    "Port-Test konnte nicht durchgeführt werden (Testdienst nicht erreichbar).":
        "The port test could not run (test service not reachable).",
    "✓ Port {port} ist von außen erreichbar. Freunde können direkt beitreten.":
        "✓ Port {port} is reachable from outside. Friends can join directly.",
    "✗ Port {port} ist von außen NICHT erreichbar.\nLösung: Im Router Port {port} (TCP) auf diesen PC weiterleiten "
    "und in der Windows-Firewall erlauben – oder playit.gg benutzen.":
        "✗ Port {port} is NOT reachable from outside.\nFix: forward port {port} (TCP) to this PC in your router and "
        "allow it in the Windows firewall – or use playit.gg.",
    "Port-Test": "Port test",
    "playit.gg ist noch nicht installiert.\n\nJetzt das offizielle Installationspaket laden (ca. 6 MB) und "
    "installieren? Windows fragt dabei nach Admin-Rechten.":
        "playit.gg is not installed yet.\n\nDownload the official installer (about 6 MB) and install it now? "
        "Windows will ask for admin rights.",
    "Installiere playit.gg ...": "Installing playit.gg ...",
    "playit.gg wurde nicht installiert (abgebrochen?).": "playit.gg was not installed (cancelled?).",
    "Einmalige Einrichtung: Im neuen Fenster den Link öffnen, kostenlos anmelden und den Agent bestätigen. "
    "Danach hier nochmal auf 'playit.gg' klicken.":
        "One-time setup: open the link in the new window, sign up for free and confirm the agent. Then click "
        "'playit.gg' here again.",
    "Auf der geöffneten playit-Seite (einmalig):\n  1. 'Add Tunnel' / 'Create Tunnel'\n  2. Typ: TCP (kein Spiel "
    "auswählen)\n  3. Local Address 127.0.0.1, Local Port {port}\n  4. Speichern\n\nDann die Tunnel-Adresse "
    "(z. B. abc.gl.at.ply.gg:12345) hier einfügen.\nLeer lassen = wieder deine eigene IP verwenden.":
        "On the playit page that just opened (one time only):\n  1. 'Add Tunnel' / 'Create Tunnel'\n  2. Type: TCP "
        "(don't pick a game)\n  3. Local Address 127.0.0.1, Local Port {port}\n  4. Save\n\nThen paste the tunnel "
        "address (e.g. abc.gl.at.ply.gg:12345) here.\nLeave empty = use your own IP again.",
    "Adresse für Freunde: {address}": "Address for friends: {address}",
    "Adresse für Freunde: eigene IP": "Address for friends: your own IP",
    "⬆  Update {version}": "⬆  Update {version}",
    "Neue Version {version} verfügbar: {url}": "New version {version} available: {url}",
    "Version {version} ist verfügbar.": "Version {version} is available.",
    "Release-Seite im Browser öffnen?": "Open the release page in your browser?",
    "Erst den Server beenden – das Update schließt den Launcher.":
        "Stop the server first – the update closes the launcher.",
    "Version {version} jetzt herunterladen und installieren?": "Download and install version {version} now?",
    "Der Launcher wird dafür geschlossen. Spiele und Spielstände bleiben erhalten.":
        "The launcher will close for this. Games and saves are kept.",
    "Lade {name} herunter ...": "Downloading {name} ...",
    "Server wirklich beenden? Der Spielstand bleibt gespeichert und kann mit 'Spielstand fortsetzen' "
    "weitergespielt werden.":
        "Really stop the server? The game stays saved and can be continued with 'Resume save'.",
    "Der Server läuft noch. Beenden? (Spielstand bleibt gespeichert)":
        "The server is still running. Quit? (The game stays saved)",

    # ---------------------------------------------------------------- dialogs
    "Spielstand fortsetzen": "Resume save",
    "Welche Multiworld möchtest du fortsetzen?": "Which multiworld do you want to resume?",
    "Sortiert nach „zuletzt gespielt“. Doppelklick oder Enter startet den Server mit diesem Spielstand.\n"
    "Löschen verschiebt den Spielstand in den Papierkorb.":
        "Sorted by “last played”. Double-click or Enter starts the server with this save.\n"
        "Delete moves the save to the recycle bin.",
    "Erstellt": "Created",
    "Zuletzt gespielt": "Last played",
    "Spielstand löschen": "Delete save",
    "🗑  Löschen": "🗑  Delete",
    "Spielstand vom {date} löschen?\nSpieler: {players}\n\nEr kommt in den Papierkorb und lässt sich dort "
    "wiederherstellen.":
        "Delete the save from {date}?\nPlayers: {players}\n\nIt goes to the recycle bin and can be restored from there.",
    "Spielstand vom {date} in den Papierkorb verschoben.": "Save from {date} moved to the recycle bin.",
    "Kein Spielstand-Ordner: {path}": "Not a save folder: {path}",
    "Spielstand konnte nicht gelöscht werden (Code {code}). Läuft der Server noch?":
        "The save could not be deleted (code {code}). Is the server still running?",
    "▶  Diesen Spielstand starten": "▶  Start this save",
    "Wo ist mein Item?": "Where is my item?",
    "Ein Hint verrät, in welcher Welt und an welchem Ort ein Item von dir liegt.\nDie Antwort erscheint im "
    "Live-Feed und im Log.":
        "A hint tells you in which world and at which location one of your items is.\nThe answer shows up in the "
        "live feed and the log.",
    "💡  Hint holen": "💡  Get hint",
    "📜  Meine Hints anzeigen": "📜  Show my hints",
    "Hint-Punkte: {points}  ·  ein Hint kostet {cost}": "Hint points: {points}  ·  a hint costs {cost}",
    "noch zu wenig (mehr Checks machen)": "not enough yet (do more checks)",
    "Hint-Punkte: {points}  ·  Hints sind kostenlos": "Hint points: {points}  ·  hints are free",
    "Hint für „{item}“ angefragt.\nDie Antwort steht gleich im Live-Feed.":
        "Asked for a hint for “{item}”.\nThe answer will be in the live feed in a moment.",
    "Statistik": "Statistics",
    "Noch keine Statistik. Sie erscheint, sobald du eine Multiworld hostest oder mit einer verbunden bist.":
        "No statistics yet. They appear once you host a multiworld or are connected to one.",
    "Items und Checks: kompletter Spielstand. Spielzeit und Durststrecke: nur, solange dein Launcher verbunden war.":
        "Items and checks: the complete save. Play time and longest wait: only while your launcher was connected.",
    "Spielstand-Backups": "Save backups",
    "Vor jedem Spielstart werden SoH-, Mario-64- und Server-Spielstände gesichert (die letzten {n}).\n"
    "Wiederherstellen geht nur, wenn Spiel und Server beendet sind.":
        "Before every game start, SoH, Mario 64 and server saves are backed up (the last {n}).\n"
        "Restoring only works while game and server are closed.",
    "({n} Dateien)": "({n} files)",
    "Backup erstellt.": "Backup created.",
    "Keine Spielstände gefunden.": "No saves found.",
    "Wiederherstellen": "Restore",
    "Spielstände vom {date} zurückspielen?\nDer aktuelle Stand wird vorher selbst gesichert.":
        "Restore the saves from {date}?\nThe current state is backed up first.",
    "Backup vom {date} wiederhergestellt.": "Backup from {date} restored.",
    "Fertig.": "Done.",
    "↩  Wiederherstellen": "↩  Restore",
    "💾  Jetzt sichern": "💾  Back up now",
    "📂  Ordner": "📂  Folder",
    "vor dem Spielstart": "before starting the game",
    "vor dem Fortsetzen": "before resuming",
    "von Hand": "manual",
    "Stand vor dem Wiederherstellen": "state before restoring",
    "Erst Spiel und Server beenden, sonst überschreiben sie die Dateien sofort wieder:":
        "Close the game and the server first, otherwise they overwrite the files again right away:",

    # ---------------------------------------------------------------- Archipelago client
    "Verbindung zum Server getrennt, verbinde neu ...": "Disconnected from the server, reconnecting ...",
    "Server nicht erreichbar, versuche weiter ... ({error})": "Server not reachable, still trying ... ({error})",
    "'{name}' ist in der laufenden Multiworld nicht dabei. Der Host muss 'Beenden' und dann 'Server hosten' "
    "klicken; danach hier 'Beenden' und 'Beitreten'.":
        "'{name}' is not part of the running multiworld. The host has to click 'Stop' and then 'Host server'; "
        "after that click 'Stop' and 'Join' here.",
    "Falsches Server-Passwort.": "Wrong server password.",
    "Verbindung abgelehnt.": "Connection refused.",
    "Mit dem Server verbunden.": "Connected to the server.",
    "Ziel erreicht": "Goal reached",
    "Spiel verbunden": "Game connected",
    "Launcher online": "Launcher online",
    "offline": "offline",
    "Spieler {n}": "Player {n}",
    "Ort {n}": "Location {n}",
    "{player} hat {item} gefunden ({location})": "{player} found {item} ({location})",
    "{player} ist mit {game} beigetreten.": "{player} joined with {game}.",
    "{player} hat das Spiel verlassen.": "{player} left the game.",

    # ---------------------------------------------------------------- statistics
    "Gestartet: {start}    Zuletzt: {last}": "Started: {start}    Last: {last}",
    "Spielzeit (Launcher verbunden): {time}": "Play time (launcher connected): {time}",
    "🏆 Ziel: {date}": "🏆 Goal: {date}",
    "Für andere gefunden: {found}    Von anderen bekommen: {got} (davon wichtig: {prog})":
        "Found for others: {found}    Received from others: {got} (important: {prog})",
    "Wichtigster Lieferant: {name} ({n} wichtige Items)": "Main supplier: {name} ({n} important items)",
    "Längste Durststrecke ohne wichtiges Item: {time}": "Longest wait for an important item: {time}",
    "🤝 Größter Helfer: {name} ({n} Items für andere)": "🤝 Biggest helper: {name} ({n} items for others)",
    "⏳ Am längsten gewartet: {name} ({time})": "⏳ Waited longest: {name} ({time})",
    "Noch keine Daten von: {names} (deren Launcher muss einmal verbunden sein).":
        "No data yet from: {names} (their launcher has to connect once).",

    # ---------------------------------------------------------------- overlay / HUD / goals
    "Berechne …": "Calculating …",
    "Immer oben": "Always on top",
    "HUD im Spiel": "In-game HUD",
    "📍 Hier": "📍 Here",
    "Ort unbekannt – Spiel starten": "Location unknown – start the game",
    "🎯 Ziel": "🎯 Goal",
    "🧭 Alles Erreichbare": "🧭 Everything reachable",
    "📦 Zuletzt erhalten": "📦 Recently received",
    "Tracker aus": "Tracker off",
    "Logik-Tracker wurde beendet. Overlay schließen und neu öffnen.":
        "The logic tracker stopped. Close the overlay and open it again.",
    "Fehler im Logik-Tracker: ": "Error in the logic tracker: ",
    "✅ Du kannst dein Ziel jetzt erreichen!": "✅ You can reach your goal now!",
    "{n} nur mit Tricks": "{n} only with tricks",
    "Gefunden {checked}/{total} · erreichbar {reachable}": "Found {checked}/{total} · reachable {reachable}",
    "… und {n} weitere": "… and {n} more",
    "Nichts erreichbar – du brauchst erst neue Items.": "Nothing reachable – you need new items first.",
    "📍 Ort unbekannt": "📍 Location unknown",
    "Hier ist nichts mehr erreichbar. Nächste Ziele: ": "Nothing left to reach here. Next places: ",
    "Gerade nichts erreichbar – du brauchst erst neue Items.":
        "Nothing reachable right now – you need new items first.",
    "✅ Go-Mode – du kannst dein Ziel erreichen!": "✅ Go mode – you can reach your goal!",
    "Hier erreichbar ({n}):": "Reachable here ({n}):",
    "Warte auf Daten …": "Waiting for data …",
    "Heilige Steine": "Spiritual Stones",
    "Amulette": "Medallions",
    "Steine + Amulette": "Stones + Medallions",
    "Dungeons abschließen": "Complete dungeons",
    "Zählt nach dem blauen Warp hinter dem Boss.": "Counts after the blue warp behind the boss.",
    "Goldene Skulltulas": "Gold Skulltulas",
    "Greg (grüner Rubin) finden": "Find Greg (the green rupee)",
    "Regenbogenbrücke: Schatten- + Geist-Amulett + Lichtpfeile":
        "Rainbow Bridge: Shadow + Spirit Medallion + Light Arrows",
    "Regenbogenbrücke ist offen": "Rainbow Bridge is open",
    "Brücke": "Bridge",
    "Ganons Boss-Schlüssel": "Ganon's Boss Key",
    "Ganons Boss-Schlüssel: Schatten- + Geist-Amulett": "Ganon's Boss Key: Shadow + Spirit Medallion",
    "Danach in der Zitadelle der Zeit abholen (Zelda-Szene).": "Then pick it up in the Temple of Time (Zelda scene).",
    "Ganons Boss-Schlüssel finden": "Find Ganon's Boss Key",
    "Ganons Schloss: {n} Prüfungen": "Ganon's Castle: {n} trials",
    "Triforce-Splitter": "Triforce Pieces",
    "Ganon besiegen": "Defeat Ganon",
    "1. Bowser-Tür": "1st Bowser door",
    "Keller-Tür": "Basement door",
    "Obergeschoss-Tür": "Upstairs door",
    "Nächste Sterntür: {door}": "Next star door: {door}",
    "Keller-Schlüssel": "Basement key",
    "Obergeschoss-Schlüssel": "Upstairs key",
    "alle Bowser-Level": "all Bowser levels",
    "letzter Bowser": "final Bowser",
    "Sterne für das Ende ({what})": "Stars for the ending ({what})",

    # ---------------------------------------------------------------- places (OoT names as in the English game)
    "Schloss": "Castle",
    "Grotte": "Grotto",
    "Kokiri-Wald": "Kokiri Forest",
    "Verlorene Wälder": "Lost Woods",
    "Heilige Lichtung": "Sacred Forest Meadow",
    "Hylianische Steppe": "Hyrule Field",
    "Lon Lon-Farm": "Lon Lon Ranch",
    "Marktplatz": "Market",
    "Zitadelle der Zeit": "Temple of Time",
    "Hyrule-Schloss": "Hyrule Castle",
    "Vor Ganons Schloss": "Outside Ganon's Castle",
    "Kakariko": "Kakariko Village",
    "Friedhof": "Graveyard",
    "Todesberg-Pfad": "Death Mountain Trail",
    "Todesberg-Krater": "Death Mountain Crater",
    "Goronia": "Goron City",
    "Zora-Fluss": "Zora's River",
    "Zoras Reich": "Zora's Domain",
    "Zoras Quelle": "Zora's Fountain",
    "Hylia-See": "Lake Hylia",
    "Gerudotal": "Gerudo Valley",
    "Gerudo-Festung": "Gerudo's Fortress",
    "Gespenster-Wüste": "Haunted Wasteland",
    "Wüstenkoloss": "Desert Colossus",
    "Deku-Baum": "Deku Tree",
    "Brauchst: Schwert und Deku-Schild (gegen Gohmas Larven), Schleuder fürs Weiterkommen oben.":
        "Needed: sword and Deku Shield (against Gohma's larvae), slingshot to get further up.",
    "Netze im Boden mit einem brennenden Deku-Stab (an Fackel anzünden) wegbrennen.":
        "Burn the webs in the floor with a burning Deku Stick (light it at a torch).",
    "Unten: Block in Wasser schieben, über die Plattformen zum Boss.":
        "Down below: push the block into the water, then cross the platforms to the boss.",
    "Gohma: Auge mit Schleuder treffen, wenn es rot ist, dann zuschlagen.":
        "Gohma: hit the eye with the slingshot when it is red, then strike.",
    "Dodongos Höhle": "Dodongo's Cavern",
    "Brauchst: Bomben (oder Sprengkraft) – ohne geht hier fast nichts.":
        "Needed: bombs (or something that explodes) – almost nothing works without them.",
    "Risse in Wänden und Augen der großen Dodongo-Statue mit Bomben öffnen.":
        "Open cracked walls and the eyes of the big Dodongo statue with bombs.",
    "Feuer-Dodongos meiden, Bombenblumen zum Sprengen nutzen.":
        "Avoid fire-breathing Dodongos, use Bomb Flowers to blast things.",
    "King Dodongo: Bombe in das offene Maul, dann mit dem Schwert zuschlagen.":
        "King Dodongo: throw a bomb into his open mouth, then strike with the sword.",
    "Jabu-Jabus Bauch": "Inside Jabu-Jabu's Belly",
    "Brauchst: Bumerang ist hier der Schlüssel (Tentakel, Schalter, Gegner).":
        "Needed: the Boomerang is the key here (tentacles, switches, enemies).",
    "Prinzessin Ruto tragen und auf Schalter/Plattformen absetzen.":
        "Carry Princess Ruto and set her down on switches/platforms.",
    "Rote Tentakel mit dem Bumerang durchtrennen, um Wege zu öffnen.":
        "Cut the red tentacles with the Boomerang to open paths.",
    "Barinade: zuerst die Halterungen mit dem Bumerang lösen, dann Quallen und Kern treffen.":
        "Barinade: first cut the tentacles holding it with the Boomerang, then hit the jellyfish and the core.",
    "Waldtempel": "Forest Temple",
    "Eingang über den Baum in der Heiligen Lichtung (Fanghaken).":
        "Entrance via the tree in Sacred Forest Meadow (Hookshot).",
    "Brauchst: Bogen für die vier Irrlicht-Schwestern (je eine Fackel/Farbe).":
        "Needed: bow for the four Poe Sisters (one torch/colour each).",
    "Der verdrehte Gang: Augen-Schalter mit Bogen treffen, um ihn zu drehen.":
        "The twisted corridor: shoot the eye switch with the bow to turn it.",
    "Blöcke im Innenhof-Bereich schieben, Kistenrätsel mit den Gemälden.":
        "Push blocks around the courtyard area, block puzzles with the paintings.",
    "Phantom-Ganon: Energiebälle mit dem Schwert zurückschlagen, Pfeile auf das Pferd.":
        "Phantom Ganon: hit the energy balls back with the sword, shoot arrows at the horse.",
    "Feuertempel": "Fire Temple",
    "Brauchst: Goronen-Rüstung (sonst Hitzeschaden) und Bomben.":
        "Needed: Goron Tunic (heat damage otherwise) and bombs.",
    "Eingesperrte Goronen befreien – oft hinter Schaltern und Schlüsseltüren.":
        "Free the imprisoned Gorons – often behind switches and locked doors.",
    "Stahlhammer öffnet Pfosten und Blöcke, Feuerwände mit Schaltern löschen.":
        "The Megaton Hammer breaks posts and blocks; switch off fire walls with switches.",
    "Volvagia: wenn der Kopf aus einem Loch kommt, mit dem Hammer draufhauen.":
        "Volvagia: when its head comes out of a hole, hit it with the hammer.",
    "Wassertempel": "Water Temple",
    "Brauchst: Eisenstiefel, Zora-Rüstung und Fanghaken.": "Needed: Iron Boots, Zora Tunic and Hookshot.",
    "Wasserstand an den Triforce-Symbolen mit Zeldas Wiegenlied ändern (oben/mitte/unten).":
        "Change the water level at the Triforce symbols with Zelda's Lullaby (high/middle/low).",
    "Überall nach Kristall-Schaltern und Wasserwirbeln schauen; Schlüssel gut einteilen.":
        "Look for crystal switches and whirlpools everywhere; spend your keys carefully.",
    "Dunkel-Link: Schwert schwer, besser mit Hammer/Feuer oder abwechseln.":
        "Dark Link: hard with the sword, better use the hammer/Din's Fire or mix it up.",
    "Morpha: Wasserkern mit dem Fanghaken rausziehen und zuschlagen.":
        "Morpha: pull the nucleus out of the water with the Hookshot and strike.",
    "Schattentempel": "Shadow Temple",
    "Eingang am Friedhof: Fackeln mit Dins Feuerinferno anzünden.":
        "Entrance at the Graveyard: light the torches with Din's Fire.",
    "Brauchst: Auge der Wahrheit (unsichtbare Wände/Böden) und Gleitstiefel.":
        "Needed: Lens of Truth (invisible walls/floors) and Hover Boots.",
    "Bomben für Wände; Riesensense und Fallen mit Timing umgehen.":
        "Bombs for walls; get past the giant scythe and traps with good timing.",
    "Bongo Bongo: mit Auge der Wahrheit Hände betäuben (Pfeile), dann ins Auge schießen.":
        "Bongo Bongo: with the Lens of Truth, stun the hands (arrows), then shoot the eye.",
    "Geistertempel": "Spirit Temple",
    "Teils als Kind, teils als Erwachsener – Kind-Teil durch das kleine Loch.":
        "Partly as a child, partly as an adult – the child part goes through the small hole.",
    "Brauchst: Silberhandschuhe (Erwachsener) bzw. Schleuder/Bomben (Kind).":
        "Needed: Silver Gauntlets (adult) or slingshot/bombs (child).",
    "Spiegelschild: Licht auf Sonnensymbole lenken, um Türen und Wege zu öffnen.":
        "Mirror Shield: reflect light onto sun symbols to open doors and paths.",
    "Twinrova: Feuer/Eis mit dem Spiegelschild aufnehmen und zurückschießen.":
        "Twinrova: absorb fire/ice with the Mirror Shield and shoot it back.",
    "Grund des Brunnens": "Bottom of the Well",
    "Nur als Kind; Brunnen in Kakariko leer machen (Hymne des Sturms in der Mühle).":
        "Child only; drain the well in Kakariko (Song of Storms in the windmill).",
    "Auge der Wahrheit zeigt falsche Wände und Löcher – viele Fallen.":
        "The Lens of Truth shows fake walls and holes – lots of traps.",
    "Dead Hand: nicht zu nah an die Hände, auf den Kopf zielen.":
        "Dead Hand: don't get too close to the hands, aim for the head.",
    "Eishöhle": "Ice Cavern",
    "Eingang hinter dem König Zora in Zoras Quelle (als Erwachsener).":
        "Entrance behind King Zora, in Zora's Fountain (as an adult).",
    "Blaues Feuer in Flaschen sammeln, damit rotes Eis schmelzen.":
        "Collect blue fire in bottles and melt red ice with it.",
    "Eisblock-Rätsel: Block so schieben, dass er an den Silberrubinen vorbeirutscht.":
        "Ice block puzzle: push the block so it slides past the silver rupees.",
    "Gerudo-Trainingsarena": "Gerudo Training Ground",
    "Brauchst: Gerudo-Mitgliedskarte für den Eintritt.": "Needed: Gerudo Membership Card to get in.",
    "Viele Räume mit Zeitlimit und Silberrubinen; Schlüssel öffnen die Mitte.":
        "Many rooms with time limits and silver rupees; keys open the middle.",
    "Hilfreich: Bogen, Fanghaken, Eisenstiefel, Hammer, Auge der Wahrheit.":
        "Useful: bow, Hookshot, Iron Boots, hammer, Lens of Truth.",
    "Diebesversteck": "Thieves' Hideout",
    "Zimmerleute befreien: Wächterinnen mit Pfeilen/Fanghaken betäuben.":
        "Free the carpenters: stun the guards with arrows/Hookshot.",
    "Erwischt werden heißt Gefängnis – leise von hinten an die Wachen.":
        "Getting caught means jail – sneak up on the guards from behind.",
    "Ganons Schloss": "Ganon's Castle",
    "Prüfungen (je nach Einstellung) brauchen Lichtpfeile, Feuerpfeile, Auge der Wahrheit u. a.":
        "The trials (depending on settings) need Light Arrows, Fire Arrows, the Lens of Truth and more.",
    "Boss-Schlüssel nötig für den Turm (siehe Ziel oben).": "The boss key is needed for the tower (see goal above).",
    "Ganons Turm": "Ganon's Tower",
    "Ganondorf: Energiebälle zurückschlagen, dann Lichtpfeil und zuschlagen.":
        "Ganondorf: hit the energy balls back, then a Light Arrow and strike.",
    "Ganon: Schwanz treffen; Master-Schwert nötig für den letzten Schlag.":
        "Ganon: hit the tail; the Master Sword is needed for the final blow.",
    "Rote Münzen und den Bowser-Schlüssel gibt es hier; Bowser am Schwanz packen und gegen eine Bombe werfen.":
        "Red coins and the Bowser key are here; grab Bowser by the tail and throw him into a bomb.",
    "Plattformen kippen und sinken – zügig weiter. Bowser gegen die Bomben am Rand werfen.":
        "Platforms tilt and sink – keep moving. Throw Bowser into the bombs at the edge.",
    "Letzter Bowser: dreimal gegen Bomben werfen; die Arena zerbricht nach dem ersten Treffer.":
        "Final Bowser: throw him into bombs three times; the arena breaks after the first hit.",

    # ---------------------------------------------------------------- install / host / lobby / ROMs / games
    "Nutze mitgelieferte Datei {name}": "Using bundled file {name}",
    "Befehl fehlgeschlagen ({code}): {cmd}": "Command failed ({code}): {cmd}",
    "Installiere Archipelago {version} nach {path} ...": "Installing Archipelago {version} to {path} ...",
    "Archipelago wird installiert ...": "Installing Archipelago ...",
    "Archipelago-Installation fehlgeschlagen.": "Archipelago installation failed.",
    "Archipelago ist bereit.": "Archipelago is ready.",
    "Erzeuge Options-Vorlagen ...": "Creating option templates ...",
    "ROM erkannt: {label}": "ROM detected: {label}",
    "Entpacke Ship of Harkinian ...": "Unpacking Ship of Harkinian ...",
    "SoH wird entpackt ...": "Unpacking SoH ...",
    "Ship of Harkinian ist bereit.": "Ship of Harkinian is ready.",
    "Erzeuge Spieldaten aus der ROM (SoH startet kurz, 1-5 Minuten) ...":
        "Creating game data from the ROM (SoH starts briefly, 1-5 minutes) ...",
    "OoT-Daten werden erzeugt ...": "Creating OoT data ...",
    "SoH hat sich beendet, ohne oot.o2r zu erzeugen.": "SoH exited without creating oot.o2r.",
    "Zeitüberschreitung beim Erzeugen von oot.o2r.": "Timed out while creating oot.o2r.",
    "oot.o2r erzeugt.": "oot.o2r created.",
    "Wende Patch an: {patch}": "Applying patch: {patch}",
    "Entpacke MSYS2 (Compiler-Umgebung) ...": "Unpacking MSYS2 (compiler environment) ...",
    "MSYS2 wird entpackt ...": "Unpacking MSYS2 ...",
    "MSYS2 Ersteinrichtung ...": "MSYS2 first-time setup ...",
    "Aktualisiere MSYS2 und installiere Compiler (einige Minuten) ...":
        "Updating MSYS2 and installing compilers (a few minutes) ...",
    "Compiler werden installiert ...": "Installing compilers ...",
    "Der Installationsordner darf keine Leerzeichen enthalten (MSYS2/make).":
        "The install folder must not contain spaces (MSYS2/make).",
    "Super Mario 64 ist schon gebaut.": "Super Mario 64 is already built.",
    "Lade sm64ex (Archipelago) Quellcode ...": "Downloading the sm64ex (Archipelago) source code ...",
    "Quellcode wird geladen ...": "Downloading source code ...",
    "Kompiliere Super Mario 64 ({jobs} Kerne, ca. 5-10 Minuten) ...":
        "Compiling Super Mario 64 ({jobs} cores, about 5-10 minutes) ...",
    "Super Mario 64 wird kompiliert ...": "Compiling Super Mario 64 ...",
    "Build fertig, aber die sm64-exe fehlt. Siehe Log.": "Build finished, but the sm64 exe is missing. See the log.",
    "Super Mario 64 ist bereit.": "Super Mario 64 is ready.",
    "Keine Spieler in der Lobby.": "No players in the lobby.",
    "Generiere Multiworld für {n} Spieler ...": "Generating the multiworld for {n} players ...",
    "Generieren fehlgeschlagen. Meist ist eine YAML ungültig; Details im Log.":
        "Generating failed. Usually a YAML is invalid; details in the log.",
    "Multiworld erstellt: {name}": "Multiworld created: {name}",
    "[Server] beendet (Code {code}).": "[Server] stopped (code {code}).",
    "Port {port} ist belegt (läuft schon ein anderer Server?).": "Port {port} is in use (is another server running?).",
    "Bitte einen Spielernamen eintragen.": "Please enter a player name.",
    "Spielername darf höchstens 16 Zeichen haben.": "The player name can have at most 16 characters.",
    "Spielername darf keine { } : enthalten.": "The player name must not contain { } :",
    "Die Multiworld wird schon erstellt; Beitreten geht nicht mehr.":
        "The multiworld is already being created; joining is no longer possible.",
    "Dieser Name ist schon vergeben.": "This name is already taken.",
    "Ungültige Anfrage.": "Invalid request.",
    "Host nicht erreichbar ({reason})": "Host not reachable ({reason})",
    "Unter dieser Adresse läuft keine Launcher-Lobby.": "There is no launcher lobby at this address.",
    "Das ist keine N64-ROM (unbekannter Dateianfang). ISO/ZIP-Dateien gehen nicht, es muss eine entpackte "
    ".z64/.n64/.v64 sein.":
        "This is not an N64 ROM (unknown file header). ISO/ZIP files don't work, it has to be an unpacked "
        ".z64/.n64/.v64.",
    "ROM-Datei nicht gefunden.": "ROM file not found.",
    "Bitte die ROM erst entpacken (.z64/.n64/.v64).": "Please unpack the ROM first (.z64/.n64/.v64).",
    "Datei ist zu groß für eine N64-ROM.": "The file is too big for an N64 ROM.",
    "Super Mario 64 erkannt, aber falsche Version. Nur USA oder Japan (nicht Europa/Shindou) werden unterstützt.":
        "Super Mario 64 detected, but the wrong version. Only USA or Japan (not Europe/Shindou) are supported.",
    "Keine passende Super-Mario-64-ROM (USA oder Japan nötig).":
        "Not a matching Super Mario 64 ROM (USA or Japan needed).",
    "Das ist Master Quest. SoH-Archipelago braucht die normale (nicht-MQ) Version.":
        "This is Master Quest. SoH Archipelago needs the normal (non-MQ) version.",
    "Zelda-ROM erkannt, aber keine von SoH unterstützte Version (evtl. verändert/gepatcht oder Majora's Mask).":
        "Zelda ROM detected, but not a version SoH supports (maybe modified/patched, or Majora's Mask).",
    "Keine passende Ocarina-of-Time-ROM.": "Not a matching Ocarina of Time ROM.",
    "ROM nicht lesbar: {error}": "Cannot read the ROM: {error}",
    "Super Mario 64 ist noch nicht gebaut. Erst 'Installieren' ausführen.":
        "Super Mario 64 is not built yet. Run 'Install' first.",
    "Ship of Harkinian ist noch nicht eingerichtet. Erst 'Installieren' ausführen.":
        "Ship of Harkinian is not set up yet. Run 'Install' first.",
    # interface style / extreme interface
    "Oberfläche": "Interface",
    "Extrem": "Extreme",
    "Die Oberfläche wechselt beim nächsten Start des Launchers.":
        "The interface changes the next time the launcher starts.",
    "Launcher jetzt neu starten?": "Restart the launcher now?",
    "AKTIV": "ACTIVE",
    "Oberflächen-Sounds": "Interface sounds",
    "Startanimation": "Start animation",
    "Progressions-Item": "Progression item",
    "Ziel erreicht": "Goal reached",
    "von {sender}": "from {sender}",
    "VPN  kein Radmin/Hamachi/Tailscale/ZeroTier-Adapter": "VPN  no Radmin/Hamachi/Tailscale/ZeroTier adapter",
    "Update  Version {version} verfügbar": "Update  version {version} available",
    "Grafik-Kern  {hz} Hz · {w}×{h}": "Graphics core  {hz} Hz · {w}×{h}",
    "keine ROM gewählt": "no ROM selected",
    "Spiel  nur hosten": "Game  host only",
    "Archipelago  {state}": "Archipelago  {state}",
    "installiert": "installed",
    "fehlt": "missing",
}
