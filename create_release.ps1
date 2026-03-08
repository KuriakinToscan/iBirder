# Versao selecionada pelo usuario: v1.0
# Este script automatiza o git add, commit, tag e push.
param (
    [Parameter(Mandatory = $false)]
    [string]$Versao = "v1.0",
    [string]$Mensagem = "Lançamento Oficial iBirder v1.0 - Executável, Instalador e Menu de Contexto"
)

Write-Host "Preparando para lancar a versao $Versao..." -ForegroundColor Cyan
git add .
git commit -m "Sincronização $Versao - Documentação EXIF e ajustes"

git tag -a "$Versao" -m "$Mensagem"
Write-Host "Tag $Versao criada localmente." -ForegroundColor Green

git push origin "$Versao"
Write-Host "Versao $Versao enviada para o GitHub!" -ForegroundColor Yellow
