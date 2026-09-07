# Khoi phuc Postgres dev tu file backup do backup_db.ps1 tao ra.
#
#   .\scripts\restore_db.ps1 .\backups\hocphi-20260907-020000.sql
#
# XOA SACH database dev hien tai roi nap lai tu file - chi dung cho dev.
# Khong hoi xac nhan bang go ten DB nhu ban VPS (restore_db.sh) vi day la
# du lieu dev, mat cung khong sao - nhung van canh bao truoc khi xoa.

param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Test-Path $BackupFile)) {
    Write-Host "Khong tim thay file: $BackupFile" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path ".env")) {
    Write-Host ".env khong ton tai." -ForegroundColor Red
    exit 1
}

$envContent = Get-Content ".env" -Raw
function Get-EnvValue([string]$name, [string]$default) {
    if ($envContent -match "(?m)^$name=(.*)$") { return $Matches[1].Trim() }
    return $default
}
$PgDb = Get-EnvValue "POSTGRES_DB" "hocphi"
$PgUser = Get-EnvValue "POSTGRES_USER" "hocphi_user"

Write-Host "Se XOA SACH database dev '$PgDb' va nap lai tu: $BackupFile" -ForegroundColor Yellow
$confirm = Read-Host "Go 'yes' de xac nhan"
if ($confirm -ne "yes") {
    Write-Host "Huy." -ForegroundColor Yellow
    exit 1
}

Write-Host "Dung web..." -ForegroundColor Cyan
docker compose -f docker-compose.dev.yml stop web

Write-Host "Ngat ket noi dang mo toi '$PgDb'..." -ForegroundColor Cyan
docker compose -f docker-compose.dev.yml exec -T db psql -U $PgUser -d postgres -c `
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$PgDb' AND pid <> pg_backend_pid();"

Write-Host "Xoa va tao lai database rong..." -ForegroundColor Cyan
docker compose -f docker-compose.dev.yml exec -T db psql -U $PgUser -d postgres -c "DROP DATABASE IF EXISTS `"$PgDb`";"
docker compose -f docker-compose.dev.yml exec -T db psql -U $PgUser -d postgres -c "CREATE DATABASE `"$PgDb`" OWNER `"$PgUser`";"

Write-Host "Nap du lieu tu backup..." -ForegroundColor Cyan
Get-Content $BackupFile -Raw | docker compose -f docker-compose.dev.yml exec -T db psql -U $PgUser -d $PgDb

Write-Host "Chay migrate..." -ForegroundColor Cyan
docker compose -f docker-compose.dev.yml up -d web
Start-Sleep -Seconds 3
docker compose -f docker-compose.dev.yml exec -T web python manage.py migrate

Write-Host "Restore xong tu $BackupFile" -ForegroundColor Green
