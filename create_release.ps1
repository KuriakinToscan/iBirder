# Versao selecionada pelo usuario: v0.7
# Este script automatiza o git add, commit, tag e push.
param (
    [Parameter(Mandatory = $false)]
    [string]$Versao = "v0.7",
    [string]$Mensagem = "Sincronização v0.7 - Atualização conceitual e técnica da documentação"
)

Write-Host "Preparando para lancar a versao $Versao..." -ForegroundColor Cyan
git add .
git commit -m "Sincronização $Versao - Documentação EXIF e ajustes"

git tag -a "$Versao" -m "$Mensagem"
Write-Host "Tag $Versao criada localmente." -ForegroundColor Green

git push origin "$Versao"
Write-Host "Versao $Versao enviada para o GitHub!" -ForegroundColor Yellow
