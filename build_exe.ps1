# Script de Construção do Executável iBirder v1.0.4

Write-Host "Iniciando processo de build do iBirder v1.0.4..." -ForegroundColor Cyan

# 1. Garante que o PyInstaller está instalado
Write-Host "Verificando PyInstaller..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe -m pip install pyinstaller

# 2. Instala dependências do projeto
Write-Host "Instalando dependencias do requirements.txt..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Limpa builds anteriores
Write-Host "Limpando pastas de build anteriores..." -ForegroundColor Yellow
if (Test-Path "./build") { Remove-Item -Recurse -Force "./build" }
if (Test-Path "./dist") { Remove-Item -Recurse -Force "./dist" }

# 4. Executa o PyInstaller
Write-Host "Executando PyInstaller (isso pode levar alguns minutos)..." -ForegroundColor Green
& .\.venv\Scripts\pyinstaller.exe --noconfirm ibirder.spec

Write-Host "Build concluído! O executável está na pasta dist/iBirder/" -ForegroundColor Cyan
