$ErrorActionPreference = "Stop"
# Build local do iBirder. O GitHub Actions (.github/workflows/build-windows.yml)
# executa os mesmos passos num Windows limpo.

Write-Host "Ativando ambiente virtual..."
. .\.venv\Scripts\Activate.ps1

Write-Host "Removendo Anaconda do PATH do Build para evitar envenenamento de DLLs..."
$env:PATH = ($env:PATH.Split(';') | Where-Object { $_ -notmatch 'anaconda|miniconda' }) -join ';'

Write-Host "Instalando dependencias, PyInstaller e pytest no .venv local usando uv..."
uv pip install -r requirements.txt pyinstaller pytest

Write-Host "Rodando testes..."
$env:IBIRDER_TESTES_GUI = "1"
python -m pytest -q tests
if ($LASTEXITCODE -ne 0) { throw "Testes falharam." }

Write-Host "Limpando diretórios antigos..."
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

Write-Host "Rodando PyInstaller (ibirder.spec)..."
pyinstaller -y ibirder.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou." }

Write-Host "Autoteste do executável (--smoke-test)..."
$proc = Start-Process -FilePath "dist\iBirder\iBirder.exe" -ArgumentList "--smoke-test" -Wait -PassThru
if ($proc.ExitCode -ne 0) { throw "Autoteste falhou (código $($proc.ExitCode)). Veja %APPDATA%\iBirder\logs." }

$versao = python -c "from core.config import APP_VERSION; print(APP_VERSION)"
$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (Test-Path $iscc) {
    Write-Host "Gerando instalador v$versao..."
    & $iscc "/DAppVersion=$versao" instalador_ibirder.iss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup falhou." }
    Write-Host "Instalador gerado em dist_installer\Instalador_iBirder_v$versao.exe"
} else {
    Write-Host "Inno Setup 6 não encontrado; pulei o instalador. Pasta gerada: dist\iBirder"
}
