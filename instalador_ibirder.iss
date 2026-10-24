; Versão vem do build (ISCC /DAppVersion=x.y, lida de core/config.py);
; o valor abaixo é só o padrão para compilação manual.
#ifndef AppVersion
  #define AppVersion "1.3"
#endif

[Setup]
; AppId fixo: é o valor que as versões 1.1 a 1.3 já usavam por padrão (= AppName). Não mudar,
; senão a atualização por cima vira uma segunda instalação.
AppId=iBirder
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
; Fecha o iBirder aberto antes de substituir os arquivos (padrão do Inno Setup, explícito aqui)
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; Remove a versão anterior do programa antes de copiar a nova: arquivos que deixaram de existir
; (ex.: bibliotecas Qt removidas na v1.3) não ficam para trás. Os dados do usuário ficam em
; %APPDATA%\iBirder e não são tocados.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\iBirder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\logo_ave.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
Name: "{group}\iBirder"; Filename: "{app}\iBirder.exe"; IconFilename: "{app}\assets\logo_ave.ico"
Name: "{commondesktop}\iBirder"; Filename: "{app}\iBirder.exe"; IconFilename: "{app}\assets\logo_ave.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\iBirder.exe"; Description: "{cm:LaunchProgram,iBirder}"; Flags: nowait postinstall skipifsilent
