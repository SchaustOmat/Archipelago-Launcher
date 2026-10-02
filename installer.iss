; Inno Setup script for ArchipelagoLauncher-Setup.exe. build.ps1 passes AppVersion, SourceExe, OutName, OutDir
; and IconFile.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceExe
  #define SourceExe "dist\ArchipelagoLauncher.exe"
#endif
#ifndef OutName
  #define OutName "ArchipelagoLauncher-Setup"
#endif
#ifndef OutDir
  #define OutDir "release"
#endif
#ifndef IconFile
  #define IconFile "assets\icon.ico"
#endif

[Setup]
AppId={{6E0B5C8E-3E52-4B8E-9A55-1C2D3E4F5A60}
AppName=Archipelago Launcher
AppVersion={#AppVersion}
AppPublisher=Archipelago Launcher
DefaultDirName={localappdata}\Programs\ArchipelagoLauncher
DefaultGroupName=Archipelago Launcher
; Installs for the current user only, so no admin prompt.
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir={#OutDir}
OutputBaseFilename={#OutName}_{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\ArchipelagoLauncher.exe
UninstallDisplayName=Archipelago Launcher

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
de.DesktopIcon=Verknüpfung auf dem Desktop erstellen
en.DesktopIcon=Create a desktop shortcut
de.Extra=Zusätzlich:
en.Extra=Additional:
de.Guide=Anleitung
en.Guide=Guide
de.Uninstall=Archipelago Launcher deinstallieren
en.Uninstall=Uninstall Archipelago Launcher
de.StartNow=Archipelago Launcher jetzt starten
en.StartNow=Start Archipelago Launcher now

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; GroupDescription: "{cm:Extra}"

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; DestName: "ArchipelagoLauncher.exe"; Flags: ignoreversion
Source: "ANLEITUNG.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme; Languages: de
Source: "GUIDE.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme; Languages: en
; Separate icon file: shortcuts use it, so Windows' icon cache of the exe never shows an old picture.
Source: "{#IconFile}"; DestDir: "{app}"; DestName: "icon.ico"; Flags: ignoreversion

[Icons]
Name: "{group}\Archipelago Launcher"; Filename: "{app}\ArchipelagoLauncher.exe"; IconFilename: "{app}\icon.ico"
Name: "{group}\{cm:Guide}"; Filename: "{app}\ANLEITUNG.txt"; Languages: de
Name: "{group}\{cm:Guide}"; Filename: "{app}\GUIDE.txt"; Languages: en
Name: "{group}\{cm:Uninstall}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Archipelago Launcher"; Filename: "{app}\ArchipelagoLauncher.exe"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\ArchipelagoLauncher.exe"; Description: "{cm:StartNow}"; Flags: nowait postinstall skipifsilent

[Messages]
de.FinishedLabel=Fertig! Spiele, ROM-Prüfung und Downloads erledigt der Launcher beim ersten Start.%n%nHeruntergeladene Spiele und Spielstände liegen in C:\APLauncher und bleiben beim Deinstallieren erhalten.
en.FinishedLabel=Done! The launcher takes care of games, ROM checks and downloads on first start.%n%nDownloaded games and saves are stored in C:\APLauncher and are kept when uninstalling.
