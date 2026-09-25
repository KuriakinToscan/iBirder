$ErrorActionPreference = "Stop"

Write-Host "Ativando ambiente virtual..."
. .\.venv\Scripts\Activate.ps1

Write-Host "Limpando diretórios antigos..."
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

Write-Host "Instalando PyInstaller e dependencias no .venv local usando uv..."
uv pip install pyinstaller

Write-Host "Removendo Anaconda do PATH do Build para evitar envenenamento de DLLs..."
$env:PATH = ($env:PATH.Split(';') | Where-Object { $_ -notmatch 'anaconda|miniconda' }) -join ';'

Write-Host "Rodando PyInstaller (ONEDIR Mode)..."
.\.venv\Scripts\pyinstaller.exe -y --name "iBirder" `
            --windowed `
            --icon "assets\logo_ave.ico" `
            --add-data "assets;assets" `
            --add-data "Geo;Geo" `
            --add-data "config.json;." `
            --add-data "guia_do_usuario.md;." `
            --add-data "README.md;." `
            --add-data "RULES.md;." `
            --add-data "manual_apis_nuvem.md;." `
            --collect-all "selenium" `
            --collect-all "folium" `
            --hidden-import "PIL._tkinter_finder" `
            --hidden-import "email" `
            --hidden-import "email.mime" `
            --hidden-import "email.mime.multipart" `
            --hidden-import "email.mime.text" `
            --hidden-import "email.mime.base" `
            --hidden-import "email.mime.application" `
            main.py

Write-Host "PyInstaller finalizado com sucesso. Pasta gerada: dist\iBirder"
