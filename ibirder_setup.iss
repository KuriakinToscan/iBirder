; Script do Inno Setup para iBirder v1.0.3
; Este script gera o instalador profissional para Windows

[Setup]
AppId={{C1B7D141-8B9CAD-4E1F-8D01-A1F620976779}}
AppName=iBirder
AppVersion=1.0.3
AppPublisher=Kuriakin Toscan
AppPublisherURL=https://github.com/KuriakinToscan/iBirder
AppSupportURL=https://github.com/KuriakinToscan/iBirder
AppUpdatesURL=https://github.com/KuriakinToscan/iBirder
DefaultDirName={autopf}\iBirder
DefaultGroupName=iBirder
AllowNoIcons=yes
SetupIconFile=assets\logo_ave.ico
; Local onde o instalador será salvo
OutputDir=C:\Users\98015753953\AppData\Local\Temp\iBirderInstaller
OutputBaseFilename=iBirder_v1.0.3_Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Inclui todos os arquivos gerados pelo PyInstaller na pasta dist/iBirder
Source: "dist\iBirder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTA: O arquivo config.json será criado/lido na pasta {app}

[Icons]
Name: "{group}\iBirder"; Filename: "{app}\iBirder.exe"
Name: "{group}\{cm:UninstallProgram,iBirder}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\iBirder"; Filename: "{app}\iBirder.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\iBirder.exe"; Description: "{cm:LaunchProgram,iBirder}"; Flags: nowait postinstall skipifsilent

[Registry]
; Integração com o Menu de Contexto (Botão Direito em Imagens)

; Para arquivos .jpg
Root: HKCR; Subkey: "SystemFileAssociations\.jpg\shell\iBirder"; ValueType: string; ValueData: "Abrir no iBirder"; Flags: uninsdeletekey
Root: HKCR; Subkey: "SystemFileAssociations\.jpg\shell\iBirder\command"; ValueType: string; ValueData: """{app}\iBirder.exe"" ""%1"""; Flags: uninsdeletekey

; Para arquivos .jpeg
Root: HKCR; Subkey: "SystemFileAssociations\.jpeg\shell\iBirder"; ValueType: string; ValueData: "Abrir no iBirder"; Flags: uninsdeletekey
Root: HKCR; Subkey: "SystemFileAssociations\.jpeg\shell\iBirder\command"; ValueType: string; ValueData: """{app}\iBirder.exe"" ""%1"""; Flags: uninsdeletekey

; Para arquivos .png
Root: HKCR; Subkey: "SystemFileAssociations\.png\shell\iBirder"; ValueType: string; ValueData: "Abrir no iBirder"; Flags: uninsdeletekey
Root: HKCR; Subkey: "SystemFileAssociations\.png\shell\iBirder\command"; ValueType: string; ValueData: """{app}\iBirder.exe"" ""%1"""; Flags: uninsdeletekey
