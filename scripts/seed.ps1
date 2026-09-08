# Seed du lieu mau (seed_demo) cho server/may dev da co backend dang chay.
#
# Chay:
#   .\scripts\seed.ps1
#
# Tuy chon (chuyen thang cho manage.py seed_demo):
#   .\scripts\seed.ps1 -Students 20 -Invoices
#   .\scripts\seed.ps1 -Reset

param(
    [int]$Students,
    [switch]$Invoices,
    [switch]$Reset,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "Cho backend san sang ..." -ForegroundColor Cyan
$waited = 0
while ($true) {
    try {
        Invoke-WebRequest -Uri "http://localhost:8001/api/accounts/me/" -UseBasicParsing -TimeoutSec 3 | Out-Null
        break
    } catch {
        if ($_.Exception.Response) { break }
    }
    Start-Sleep -Seconds 2
    $waited += 2
    if ($waited -ge 60) {
        Write-Host "Backend chua san sang sau 60s. Chay '.\scripts\dev.ps1' truoc." -ForegroundColor Red
        exit 1
    }
}

$seedArgs = @()
if ($Students) { $seedArgs += @("--students", $Students) }
if ($Invoices) { $seedArgs += "--invoices" }
if ($Reset) { $seedArgs += "--reset" }
if ($Force) { $seedArgs += "--force" }

docker compose -f docker-compose.dev.yml exec web python manage.py seed_demo @seedArgs
