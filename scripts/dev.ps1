# Khoi dong moi truong dev tren Windows: Postgres + Django (Docker) o mot cua so,
# Vite dev server (host, co HMR) o mot cua so khac.
#
# Chay:
#   .\scripts\dev.ps1
#
# Tuy chon:
#   .\scripts\dev.ps1 -Seed     # sau khi backend san sang, chay them seed_demo
#   .\scripts\dev.ps1 -NoNewWindows  # chay backend nen (-d), frontend ngay trong cua so hien tai

param(
    [switch]$Seed,
    [switch]$NoNewWindows
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Test-Path ".env")) {
    Write-Host ".env khong ton tai, tao tu .env.example ..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    (Get-Content ".env") `
        -replace '^DJANGO_DEBUG=.*', 'DJANGO_DEBUG=True' `
        -replace '^DJANGO_ALLOWED_HOSTS=.*', 'DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1' |
        Set-Content ".env"
    Write-Host "Da tao .env cho dev (DJANGO_DEBUG=True). Sua them neu can." -ForegroundColor Yellow
}

function Test-DockerRunning {
    docker info *> $null
    return $LASTEXITCODE -eq 0
}

if (-not (Test-DockerRunning)) {
    Write-Host "Docker Desktop chua chay. Dang mo Docker Desktop, cho khoi dong..." -ForegroundColor Yellow
    Start-Process "$Env:ProgramFiles\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
    $waited = 0
    while (-not (Test-DockerRunning)) {
        Start-Sleep -Seconds 3
        $waited += 3
        if ($waited -ge 120) {
            Write-Host "Docker Desktop khong khoi dong duoc sau 120s. Mo tay roi chay lai script." -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "Docker da san sang." -ForegroundColor Green
}

if (-not (Test-Path "frontend/node_modules")) {
    Write-Host "Chua co node_modules, chay npm install ..." -ForegroundColor Yellow
    Push-Location "frontend"
    npm install
    Pop-Location
}

function Wait-Backend {
    param([int]$TimeoutSeconds = 60)
    Write-Host "Cho backend migrate xong va san sang ..." -ForegroundColor Cyan
    $waited = 0
    while ($true) {
        try {
            Invoke-WebRequest -Uri "http://localhost:8000/api/accounts/me/" -UseBasicParsing -TimeoutSec 3 | Out-Null
            return $true
        } catch {
            if ($_.Exception.Response) { return $true }
        }
        Start-Sleep -Seconds 2
        $waited += 2
        if ($waited -ge $TimeoutSeconds) {
            Write-Host "Backend chua san sang sau ${TimeoutSeconds}s, thu seed_demo van se chay (co the loi)." -ForegroundColor Yellow
            return $false
        }
    }
}

if ($NoNewWindows) {
    Write-Host "Khoi dong backend (nen) ..." -ForegroundColor Cyan
    docker compose -f docker-compose.dev.yml up -d

    if ($Seed) {
        Wait-Backend | Out-Null
        docker compose -f docker-compose.dev.yml exec web python manage.py seed_demo
    }

    Write-Host "Khoi dong Vite dev server (Ctrl+C de dung ca hai, backend van chay nen)..." -ForegroundColor Cyan
    Push-Location "frontend"
    npm run dev
    Pop-Location
    exit 0
}

Write-Host "Mo cua so backend (Postgres + Django) ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$RepoRoot'; docker compose -f docker-compose.dev.yml up"
)

if ($Seed) {
    Wait-Backend | Out-Null
    docker compose -f docker-compose.dev.yml exec web python manage.py seed_demo
}

Write-Host "Mo cua so frontend (Vite) ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$RepoRoot\frontend'; npm run dev"
)

Write-Host ""
Write-Host "Da khoi dong xong. Mo http://localhost:8000" -ForegroundColor Green
