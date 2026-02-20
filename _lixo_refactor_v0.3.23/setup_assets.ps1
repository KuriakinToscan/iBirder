$ErrorActionPreference = "Stop"

$url = "https://exiftool.org/exiftool-13.20_64.zip" 
# Link de fallback se o acima falhar (versão anterior estável)
# Mas vamos tentar o mais recente se possível. O padrão é exiftool-VERSAO_64.zip
# Se der erro 404, o usuário terá que baixar manualmente.

$destDir = "assets"
$zipFile = "$destDir\exiftool.zip"
$exeName = "exiftool(-k).exe"
$finalName = "exiftool.exe"

# Cria diretório assets se não existir
if (-not (Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir | Out-Null
}

Write-Host "Baixando ExifTool de $url..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri $url -OutFile $zipFile
}
catch {
    Write-Host "Erro ao baixar ExifTool: $_" -ForegroundColor Red
    Write-Host "Por favor, baixe manualmente de https://exiftool.org/ e extraia 'exiftool(-k).exe' para a pasta 'assets', renomeando para 'exiftool.exe'." -ForegroundColor Yellow
    exit 1
}

Write-Host "Extraindo..." -ForegroundColor Cyan
Expand-Archive -Path $zipFile -DestinationPath $destDir -Force

# Procura o executável extraído
$extracted = Get-ChildItem -Path $destDir -Filter $exeName -Recurse
if ($extracted) {
    Write-Host "Renomeando $exeName para $finalName..." -ForegroundColor Cyan
    Move-Item -Path $extracted.FullName -Destination "$destDir\$finalName" -Force
    
    # Limpeza
    Remove-Item $zipFile
    # Remove diretorio se extraiu dentro de uma subpasta
    if ($extracted.Directory.Name -ne "assets") {
        Remove-Item $extracted.Directory.FullName -Recurse -Force
    }

    Write-Host "ExifTool configurado com sucesso em $destDir\$finalName" -ForegroundColor Green
}
else {
    Write-Host "Executável $exeName não encontrado no zip." -ForegroundColor Red
    exit 1
}
