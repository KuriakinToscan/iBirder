$lixoDir = "_lixo_geral_recursivo"
New-Item -ItemType Directory -Force -Path $lixoDir | Out-Null
$logFile = "$lixoDir\auditoria_limpeza.txt"
New-Item -ItemType File -Force -Path $logFile | Out-Null

$protectedPatterns = @('\\assets\\models', '\\\.git', '\\\.venv', '\\_lixo')

function IsProtected($path) {
    foreach ($pat in $protectedPatterns) {
        if ($path -match $pat) { return $true }
    }
    return $false
}

$movedCount = 0

# 1. Clean __pycache__ directories
Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Where-Object { -not (IsProtected $_.FullName) } | ForEach-Object {
    $relPath = Resolve-Path -Relative $_.FullName
    $logLine = "[MOVIDO] $relPath -> Lixo"
    Add-Content -Path $logFile -Value $logLine
    Move-Item -Path $_.FullName -Destination $lixoDir -Force -ErrorAction SilentlyContinue
    $movedCount++
}

# 2. Clean temporary files and caches
$extensions = @('*.pyc', '*.pyo', '*.bak', '*.tmp', '*.old', '*.swp', 'Thumbs.db', '.DS_Store', '*.log')
foreach ($ext in $extensions) {
    Get-ChildItem -Path . -Recurse -File -Filter $ext -ErrorAction SilentlyContinue | Where-Object { -not (IsProtected $_.FullName) } | ForEach-Object {
        $relPath = Resolve-Path -Relative $_.FullName
        $logLine = "[MOVIDO] $relPath -> Lixo"
        Add-Content -Path $logFile -Value $logLine
        Move-Item -Path $_.FullName -Destination $lixoDir -Force -ErrorAction SilentlyContinue
        $movedCount++
    }
}

# 3. Clean temp/ directory contents
if (Test-Path "temp") {
    Get-ChildItem -Path "temp" -ErrorAction SilentlyContinue | ForEach-Object {
        $relPath = Resolve-Path -Relative $_.FullName
        $logLine = "[MOVIDO] $relPath -> Lixo"
        Add-Content -Path $logFile -Value $logLine
        Move-Item -Path $_.FullName -Destination $lixoDir -Force -ErrorAction SilentlyContinue
        $movedCount++
    }
}

Write-Host "TOTAL_MOVIDOS=$movedCount"
Get-Content -Path $logFile -Tail 5 -ErrorAction SilentlyContinue
