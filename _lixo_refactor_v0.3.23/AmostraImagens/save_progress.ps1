param (
    [string]$Mensagem = "Auto-save: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
)

Write-Host "💾 Iniciando backup para o GitHub..." -ForegroundColor Cyan
git add .
git commit -m "$Mensagem"
git push
Write-Host "✅ Código salvo com sucesso no GitHub!" -ForegroundColor Green