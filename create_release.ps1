param (
    [Parameter(Mandatory = $true)]
    [string]$Versao,
    [string]$Mensagem = "Versao oficial $Versao"
)

Write-Host "Preparando para lancar a versao $Versao..." -ForegroundColor Cyan
git add .
git commit -m "Pre-release: salvando tudo antes da tag $Versao"

git tag -a "$Versao" -m "$Mensagem"
Write-Host "Tag $Versao criada localmente." -ForegroundColor Green

git push origin "$Versao"
# git push origin --tags # Explicitly push tags if needed, but push origin $Versao usually works for the tag ref
Write-Host "Versao $Versao enviada para o GitHub!" -ForegroundColor Yellow