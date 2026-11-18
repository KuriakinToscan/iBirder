; Versão vem do build (ISCC /DAppVersion=x.y, lida de core/config.py);
; o valor abaixo é só o padrão para compilação manual.
#ifndef AppVersion
  #define AppVersion "1.6"
#endif
; AppId fixo: é o valor que as versões 1.1 a 1.3 já usavam por padrão (= AppName). Não mudar,
; senão a atualização por cima vira uma segunda instalação. O Inno Setup registra a instalação em
; ...\CurrentVersion\Uninstall\iBirder_is1 (DisplayVersion = versão, InstallLocation = pasta).
#define MyAppId "iBirder"

[Setup]
AppId={#MyAppId}
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
; Com uma instalação anterior, a pasta não é perguntada de novo: atualiza no mesmo lugar, sem
; deixar uma segunda cópia em outra pasta (a escolha só aparece na primeira instalação).
DisableDirPage=auto
UsePreviousAppDir=yes
; Fecha o iBirder aberto antes de substituir os arquivos (padrão do Inno Setup, explícito aqui)
CloseApplications=yes

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[CustomMessages]
AvisoAtualizar=O iBirder %1 já está instalado neste computador.%n%nEle será atualizado para a versão %2, na mesma pasta. Suas configurações e chaves de API são mantidas, e suas fotos não são alteradas.%n%nDeseja continuar?
AvisoVersaoDesconhecida=Uma versão anterior do iBirder já está instalada neste computador.%n%nEla será substituída pela versão %1, na mesma pasta. Suas configurações e chaves de API são mantidas, e suas fotos não são alteradas.%n%nDeseja continuar?
AvisoReinstalar=O iBirder %1 já está instalado neste computador.%n%nDeseja instalar a mesma versão de novo? Isso repara a instalação; suas configurações e chaves de API são mantidas.
AvisoRebaixar=Uma versão mais nova do iBirder (%1) já está instalada neste computador. Este instalador é da versão %2, mais antiga.%n%nRecomendado: cancelar e continuar usando a versão %1.%n%nDeseja instalar a versão %2 mesmo assim?
MemoInstalacaoAnterior=Atualização:%n%1Versão instalada: %2%n%1Nova versão: %3
MemoVersaoDesconhecida=anterior (número não registrado)

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

[Code]
// Detecta uma instalação anterior pela chave de desinstalação do AppId e avisa a versão
// instalada x a deste instalador antes de começar. Em modo silencioso (/SILENT, /VERYSILENT)
// não pergunta nada: só registra no log (/LOG), o que o CI usa para conferir a detecção.
const
  ChaveDesinstalacao = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppId}_is1';
  VersaoNova = '{#AppVersion}';

var
  TemInstalacaoAnterior: Boolean;
  VersaoInstalada: String;
  PastaInstalada: String;

function LerInstalacao(RootKey: Integer): Boolean;
begin
  Result := RegKeyExists(RootKey, ChaveDesinstalacao);
  if Result then
  begin
    if not RegQueryStringValue(RootKey, ChaveDesinstalacao, 'DisplayVersion', VersaoInstalada) then
      VersaoInstalada := '';
    if not RegQueryStringValue(RootKey, ChaveDesinstalacao, 'InstallLocation', PastaInstalada) then
      PastaInstalada := '';
    VersaoInstalada := Trim(VersaoInstalada);
  end;
end;

// Instalação por máquina (padrão, 64 bits), por máquina em 32 bits ou só do usuário.
function ProcurarInstalacaoAnterior(): Boolean;
begin
  Result := False;
  if IsWin64 then
    Result := LerInstalacao(HKLM64);
  if not Result then
    Result := LerInstalacao(HKLM32);
  if not Result then
    Result := LerInstalacao(HKCU);
end;

// Tira o próximo número de uma versão "1.4.2" (o que não for número conta como 0).
function ProximaParte(var Versao: String): Integer;
var
  P: Integer;
  Parte: String;
begin
  P := Pos('.', Versao);
  if P > 0 then
  begin
    Parte := Copy(Versao, 1, P - 1);
    Delete(Versao, 1, P);
  end
  else
  begin
    Parte := Versao;
    Versao := '';
  end;
  Result := StrToIntDef(Trim(Parte), 0);
end;

// -1 se A < B, 0 se iguais (1.4 = 1.4.0), 1 se A > B.
function CompararVersoes(A, B: String): Integer;
var
  NA, NB: Integer;
begin
  Result := 0;
  while (Result = 0) and ((A <> '') or (B <> '')) do
  begin
    NA := ProximaParte(A);
    NB := ProximaParte(B);
    if NA < NB then
      Result := -1
    else if NA > NB then
      Result := 1;
  end;
end;

function InitializeSetup(): Boolean;
var
  Comparacao: Integer;
  Caso, Texto: String;
  Botoes: Integer;
begin
  Result := True;
  TemInstalacaoAnterior := ProcurarInstalacaoAnterior();
  if not TemInstalacaoAnterior then
  begin
    Log('[iBirder] anterior=nenhuma nova=' + VersaoNova);
    Exit;
  end;

  Botoes := MB_YESNO;
  if VersaoInstalada = '' then
  begin
    Caso := 'desconhecida';
    Texto := FmtMessage(CustomMessage('AvisoVersaoDesconhecida'), [VersaoNova]);
  end
  else
  begin
    Comparacao := CompararVersoes(VersaoInstalada, VersaoNova);
    if Comparacao < 0 then
    begin
      Caso := 'atualizar';
      Texto := FmtMessage(CustomMessage('AvisoAtualizar'), [VersaoInstalada, VersaoNova]);
    end
    else if Comparacao = 0 then
    begin
      Caso := 'reinstalar';
      Texto := FmtMessage(CustomMessage('AvisoReinstalar'), [VersaoInstalada]);
    end
    else
    begin
      // Voltar para uma versão antiga raramente é o que a pessoa quer: o padrão é "Não".
      Caso := 'rebaixar';
      Texto := FmtMessage(CustomMessage('AvisoRebaixar'), [VersaoInstalada, VersaoNova]);
      Botoes := MB_YESNO or MB_DEFBUTTON2;
    end;
  end;
  Log('[iBirder] anterior=' + VersaoInstalada + ' nova=' + VersaoNova + ' caso=' + Caso +
      ' pasta=' + PastaInstalada);

  if WizardSilent then
    Exit;
  if MsgBox(Texto, mbConfirmation, Botoes) <> IDYES then
  begin
    Log('[iBirder] instalação cancelada no aviso de versão anterior');
    Result := False;
  end;
end;

// Na tela "Pronto para instalar", mostra a versão instalada e a nova antes da pasta.
function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo,
  MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
var
  Instalada: String;
begin
  Result := '';
  if TemInstalacaoAnterior then
  begin
    Instalada := VersaoInstalada;
    if Instalada = '' then
      Instalada := CustomMessage('MemoVersaoDesconhecida');
    Result := FmtMessage(CustomMessage('MemoInstalacaoAnterior'), [Space, Instalada, VersaoNova]) +
      NewLine + NewLine;
  end;
  if MemoDirInfo <> '' then
    Result := Result + MemoDirInfo + NewLine + NewLine;
  if MemoGroupInfo <> '' then
    Result := Result + MemoGroupInfo + NewLine + NewLine;
  if MemoTasksInfo <> '' then
    Result := Result + MemoTasksInfo + NewLine + NewLine;
end;
