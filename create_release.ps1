param (
    [Parameter(Mandatory = $true)]
    [string]$Versao,  # Ex: v0.1
    [string]$Mensagem = "Versão oficial $Versao"
)

# 1. Garante que tudo está salvo antes
Write-Host "📦 Preparando para lançar a versão $Versao..." -ForegroundColor Cyan
git add .
git commit -m "Pre-release: salvando tudo antes da tag $Versao"

# 2. Cria a Tag (O Carimbo)
git tag -a "$Versao" -m "$Mensagem"
Write-Host "✅ Tag $Versao criada localmente." -ForegroundColor Green

# 3. Envia a Tag para o GitHub
git push origin "$Versao"
Write-Host "🚀 Versão $Versao enviada para o GitHub!" -ForegroundColor Yellow
Write-Host "Acesse para baixar/editar: https://github.com/KuriakinToscan/iBirder/releases/tag/$Versao"