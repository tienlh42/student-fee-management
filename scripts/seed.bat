@echo off
REM Double-click de chay seed.ps1 ma khong bi chan boi Execution Policy.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0seed.ps1" %*
