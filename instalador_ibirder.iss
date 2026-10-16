; Versão vem do build (ISCC /DAppVersion=x.y, lida de core/config.py);
; o valor abaixo é só o padrão para compilação manual.
#ifndef AppVersion
  #define AppVersion "1.2"
#endif

[Setup]
AppName=iBirder
AppVersion={#AppVersion}
AppPublisher=Kuriakin Toscan
AppPublisherURL=https://github.com/KuriakinToscan/iBirder
DefaultDirName={autopf}\iBirder
DefaultGroupName=iBirder
OutputDir=dist_installer
OutputBaseFilename=Instalador_iBirder_v{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
DisableDirPage=no

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\iBirder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\logo_ave.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
Name: "{group}\iBirder"; Filename: "{app}\iBirder.exe"; IconFilename: "{app}\assets\logo_ave.ico"
Name: "{commondesktop}\iBirder"; Filename: "{app}\iBirder.exe"; IconFilename: "{app}\assets\logo_ave.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\iBirder.exe"; Description: "{cm:LaunchProgram,iBirder}"; Flags: nowait postinstall skipifsilent
