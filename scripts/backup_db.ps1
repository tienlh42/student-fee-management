# Backup Postgres cua moi truong dev (docker-compose.dev.yml) ra thu muc backups/.
#
#   .\scripts\backup_db.ps1
#   .\scripts\backup_db.ps1 -KeepDays 30
#
# Dung truoc khi lam thao tac rui ro (migration lon, --reset, sua tay trong DB)
# de co the quay lai neu hong. File .sql thuong (khong nen) cho don gian -
# day la backup tien dung cho dev, co che chinh la scripts/backup_db.sh tren VPS.
# backups/ da nam trong .gitignore.

param(
    [int]$KeepDays = 14
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Test-Path ".env")) {
    Write-Host ".env khong ton tai - chay .\scripts\dev.ps1 truoc, hoac tu tao tu .env.example." -ForegroundColor Red
    exit 1
}

$envContent = Get-Content ".env" -Raw
function Get-EnvValue([string]$name, [string]$default) {
    if ($envContent -match "(?m)^$name=(.*)$") { return $Matches[1].Trim() }
    return $default
}
$PgDb = Get-EnvValue "POSTGRES_DB" "hocphi"
$PgUser = Get-EnvValue "POSTGRES_USER" "hocphi_user"

$BackupDir = Join-Path $RepoRoot "backups"
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$OutFile = Join-Path $BackupDir "$PgDb-$Stamp.sql"

Write-Host "Dump database '$PgDb' ..." -ForegroundColor Cyan
$dump = docker compose -f docker-compose.dev.yml exec -T db pg_dump -U $PgUser $PgDb | Out-String

if ($LASTEXITCODE -ne 0) {
    Write-Host "pg_dump loi - kiem tra container 'db' co dang chay khong (docker compose -f docker-compose.dev.yml ps)." -ForegroundColor Red
    exit 1
}
Write-Host "Dump xong, dang ghi file..."

# Ghi UTF-8 khong BOM - BOM o dau file se lam psql doc sai khi restore.
# Retry vi thinh thoang $OutFile bi doc rong ngay sau lenh docker (chua ro
# nguyen nhan - co the la quirk cua console/host - nhung thu lai la qua).
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$written = $false
for ($i = 0; $i -lt 3 -and -not $written; $i++) {
    if ([string]::IsNullOrEmpty($OutFile)) {
        Start-Sleep -Milliseconds 200
        $OutFile = Join-Path $BackupDir "$PgDb-$Stamp.sql"
        continue
    }
    [System.IO.File]::WriteAllText($OutFile, $dump, $utf8NoBom)
    $written = $true
}
if (-not $written) {
    Write-Host "Khong the xac dinh duong dan file backup sau 3 lan thu - chay lai script." -ForegroundColor Red
    exit 1
}

$sizeKb = [math]::Round((Get-Item $OutFile).Length / 1KB, 1)
Write-Host "Da backup: $OutFile (${sizeKb} KB)" -ForegroundColor Green

Get-ChildItem $BackupDir -Filter "*.sql" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepDays) } |
    ForEach-Object {
        Write-Host "Xoa backup cu: $($_.Name)" -ForegroundColor DarkGray
        Remove-Item $_.FullName -Force
    }
