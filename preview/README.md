# Vorschau: animierter Launcher

Ein eigenständiger Prototyp zum Ausprobieren. Er ist nicht Teil des Launchers, wird nicht gebaut und benutzt
nichts aus `aplauncher/`. Alle Daten (Mitspieler, Funde, Log, Ping) sind ausgedacht.

```
py -3.14 preview\fancy_launcher.py            # Bildrate = Monitorfrequenz (z. B. 165 Hz)
py -3.14 preview\fancy_launcher.py --fps 240
```

Tasten: `1`–`4` Tabs, `F` Bildraten-Anzeige, `Q` Effekte hoch/niedrig, `F11` Vollbild.

Was drin ist:
- **Spielen**: Karten mit 3D-drehendem Stern bzw. Edelstein, schweben beim Drüberfahren, Glühen bei Auswahl.
  Der Spielen-Knopf hat Pulsringe und einen Glanzstreifen, beim Klick gibt es eine Partikel-Explosion und der
  Server „läuft“. Mitspieler-Liste mit Fortschritt, Gesamtring, Toasts für Funde.
- **Einrichtung**: Prüf-Animation mit Spinnern und Häkchen, die gezeichnet werden.
- **Netzwerk**: Radar mit Mitspielern, Live-Ping-Kurve und Datenverkehr.
- **Log**: Zeilen erscheinen per Schreibmaschine und scrollen weich nach oben.
- Hintergrund: Farbwolken und Sterne mit Parallaxe, die der Maus ausweichen. Der Tab-Indikator dehnt sich
  beim Wechseln.

Technik: reines tkinter auf einem Canvas. Alle Bewegungen laufen über Federn mit echter Zeit (`dt`) und sehen
deshalb bei jeder Bildrate gleich aus. Unter Windows wird der Timer auf 1 ms gestellt (`timeBeginPeriod`),
sonst wäre `after()` bei ~64 Hz gedeckelt. Canvas-Aufrufe passieren nur bei echten Änderungen, und Farben
werden in 64 Stufen gecacht.
