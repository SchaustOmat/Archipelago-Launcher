# Changelog

## 0.8.2

### Changed
- **The extreme interface is gone again.** It was too heavy and lagged. The launcher is back to the animated
  interface of 0.7.0 (no style switch, no Pillow dependency).

## 0.8.1

### Changed
- **Extreme interface is lighter:** the backdrop updates 6 times a second instead of 10, the grain stands
  still and the glass is refreshed once a second. Much less to transfer when watching over AnyDesk or
  similar tools.
- New switch **Options → Animated backdrop**: off keeps a still picture (about 3 % CPU instead of about 14 %);
  the build-up, glitches and banners still move.

## 0.8.0

### New
- **Extreme interface** (Setup → Interface: Clean / Extreme). The clean interface stays the default. Extreme
  draws the whole window on one canvas: drifting purple nebula with particles, scanlines, grain and vignette;
  frosted-glass panels that blur what is behind them; RGB-glitch page changes; killstreak-style banners for
  important items.
- **The launcher builds itself up at start** (about 2.5 s): a scan line reveals the backdrop, the logo appears
  with a light ring, particles fly in and lock onto the panel edges, panels are printed line by line, small
  parts form out of pixel noise, texts decode out of random characters, buttons go from corner brackets to a
  line to a flash. System start lines show real checks (Archipelago, game, ROM, VPN). A click or key skips
  it; it can be turned off (Options → Start animation). Page changes use a short version.
- **Interface sounds** (optional, off by default), generated in code.
- The backdrop runs at 10 fps (about 15 % of one CPU core) and stops completely while the launcher is in the
  background.

## 0.7.0

### New
- **Animated interface.** All animations run on one clock that matches the monitor's refresh rate (60, 144,
  165 Hz …) and are time-based, so they stay smooth. Buttons glow, press in and flash on click; the tab
  underline springs to the selected tab; pages slide in and their cards light up; game cards glow with a
  check mark; switches instead of check boxes; glowing progress bar; drifting light band and shimmering
  title; status with a radar ping. Decoration pauses while the launcher is in the background.
- **Delete saves:** the resume list has a 🗑 Delete button (or the Del key). The save goes to the recycle
  bin, so it can be restored.
- **Exact times:** the resume list shows when each multiworld was created and last played, to the second.

## 0.6.2 – first public release

### New
- **English interface.** Language choice under Setup → "Sprache / Language"; on first start it follows the
  Windows language. English guide (`GUIDE.txt`), English README, bilingual installer.
- **💡 Hint button:** pick an item of your own game, the server tells you where it is; hint points and cost
  are shown.
- **Notifications:** important item from someone else or someone reaching their goal → message in the
  launcher and the in-game HUD, with a sound (can be turned off).
- **📊 Statistics** per multiworld: checks, items found for others / received (and from whom), play time,
  longest wait for an important item. The host's numbers come straight from the server's save file, so they
  are complete even for time without the launcher.
- **Save backups** before every game start (SoH, Mario 64 and the server's save), restore under
  Setup → Backups.
- **Update check:** new releases show an "⬆ Update" button that downloads and installs them.
- **Radmin VPN / Hamachi** address is used automatically as the address for friends when hosting.
- **Resume save** list is sorted by "last played".

### Changed
- New neutral app icon.

## 0.5.3 and earlier
Private versions: lobby, hosting/joining, overlay and in-game HUD (Universal Tracker), playit.gg setup,
port test, Mario 64 (sm64ex, 60 FPS) and Ocarina of Time (Ship of Harkinian) install.
