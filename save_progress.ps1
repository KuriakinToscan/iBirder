param(
    [string]$Message = "Auto-save progress"
)

$ErrorActionPreference = "Continue"

Write-Host "Iniciando salvamento..." -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
    Write-Host "Erro: Repositório Git não encontrado neste diretório." -ForegroundColor Red
    exit 1
}

Write-Host "Adicionando alterações..." -ForegroundColor Yellow
git add .
if ($LASTEXITCODE -ne 0) { Write-Host "Erro no 'git add'." -ForegroundColor Red; exit 1 }

$status = git status --porcelain
if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "Nenhuma alteração para commitar." -ForegroundColor Green
} else {
    Write-Host "Commitando..." -ForegroundColor Yellow
    git commit -m "$Message"
    if ($LASTEXITCODE -ne 0) { Write-Host "Erro no 'git commit'." -ForegroundColor Red; exit 1 }
}

Write-Host "Enviando para o repositório remoto..." -ForegroundColor Yellow
git push
if ($LASTEXITCODE -ne 0) { 
    Write-Host "Erro no 'git push'. Verifique se o remote está configurado corretamente." -ForegroundColor Red 
    exit 1 
}

Write-Host "Sucesso! Todo o progresso foi salvo." -ForegroundColor Green
