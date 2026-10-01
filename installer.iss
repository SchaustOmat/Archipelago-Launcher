; Inno Setup script for ArchipelagoLauncher-Setup.exe. build.ps1 passes AppVersion, SourceExe and OutName.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceExe
  #define SourceExe "dist\ArchipelagoLauncher.exe"
#endif
#ifndef OutName
  #define OutName "ArchipelagoLauncher-Setup"
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
OutputDir=release
OutputBaseFilename={#OutName}_{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\ArchipelagoLauncher.exe
UninstallDisplayName=Archipelago Launcher

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Verknüpfung auf dem Desktop erstellen"; GroupDescription: "Zusätzlich:"

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; DestName: "ArchipelagoLauncher.exe"; Flags: ignoreversion
Source: "ANLEITUNG.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme
; Separate icon file: shortcuts use it, so Windows' icon cache of the exe never shows an old picture.
Source: "assets\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Archipelago Launcher"; Filename: "{app}\ArchipelagoLauncher.exe"; IconFilename: "{app}\icon.ico"
Name: "{group}\Anleitung"; Filename: "{app}\ANLEITUNG.txt"
Name: "{group}\Archipelago Launcher deinstallieren"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Archipelago Launcher"; Filename: "{app}\ArchipelagoLauncher.exe"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\ArchipelagoLauncher.exe"; Description: "Archipelago Launcher jetzt starten"; Flags: nowait postinstall skipifsilent

[Messages]
de.FinishedLabel=Fertig! Spiele, ROM-Prüfung und Downloads erledigt der Launcher beim ersten Start.%n%nHeruntergeladene Spiele und Spielstände liegen in C:\APLauncher und bleiben beim Deinstallieren erhalten.
