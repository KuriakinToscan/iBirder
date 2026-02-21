$whitelist = @("modules", "core", "ui", "assets", ".git", ".venv", "main.py", "create_release.ps1", ".gitignore", "requirements.txt", ".env", "README.md", "_lixo_refactor_v0.3.23", "cleanup.ps1")

New-Item -ItemType Directory -Force -Path "_lixo_refactor_v0.3.23" | Out-Null
$logFile = "_lixo_refactor_v0.3.23\limpeza_log.txt"

Get-ChildItem -Path . | Where-Object { $_.Name -notin $whitelist } | ForEach-Object {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] MOVIDO: " + $_.Name
    Add-Content -Path $logFile -Value $logLine
    Move-Item -Path $_.FullName -Destination "_lixo_refactor_v0.3.23" -Force
}

Get-Content -Path $logFile -TotalCount 5
