param(
    [string]$DistPath
)

$ErrorActionPreference = "Continue"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "dist slim" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not (Test-Path $DistPath)) {
    Write-Host "[error] missing: $DistPath" -ForegroundColor Red
    exit 1
}

$InitialSize = (Get-ChildItem -Path $DistPath -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "`ninitial: $([math]::Round($InitialSize, 2)) MB" -ForegroundColor Yellow

Get-ChildItem -Path $DistPath -Recurse -Include *.pdb -File -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem -Path $DistPath -Recurse -Include *.pyi -File -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem -Path $DistPath -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem -Path $DistPath -Recurse -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^tests?$' } |
    Remove-Item -Recurse -Force
Get-ChildItem -Path $DistPath -Recurse -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^(docs|examples|samples|demo)$' } |
    Remove-Item -Recurse -Force
Get-ChildItem -Path $DistPath -Recurse -Include *.pyc -File -ErrorAction SilentlyContinue | Remove-Item -Force

$distInfoDirs = Get-ChildItem -Path $DistPath -Recurse -Directory -Filter "*.dist-info" -ErrorAction SilentlyContinue
foreach ($infoDir in $distInfoDirs) {
    foreach ($fileName in @("RECORD", "INSTALLER", "direct_url.json")) {
        $file = Join-Path $infoDir.FullName $fileName
        if (Test-Path $file) {
            Remove-Item $file -Force
        }
    }
}

# PaperFlick does not decode AVIF or open TLS sockets in-process (About uses the
# system browser). Keep libcrypto-3-x64.dll: _hashlib.pyd links it.
$optionalBloat = @(
    "PIL\_avif.pyd",
    "_ssl.pyd",
    "libssl-3-x64.dll"
)
Write-Host "`n[optional bloat]" -ForegroundColor Green
foreach ($rel in $optionalBloat) {
    $path = Join-Path $DistPath $rel
    if (Test-Path -LiteralPath $path) {
        $mb = [math]::Round((Get-Item -LiteralPath $path).Length / 1MB, 2)
        Remove-Item -LiteralPath $path -Force
        Write-Host "  removed $rel ($mb MB)"
    } else {
        Write-Host "  missing $rel (already gone)" -ForegroundColor Gray
    }
}

$FinalSize = (Get-ChildItem -Path $DistPath -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "final: $([math]::Round($FinalSize, 2)) MB" -ForegroundColor Green
Write-Host "saved: $([math]::Round($InitialSize - $FinalSize, 2)) MB" -ForegroundColor Cyan
