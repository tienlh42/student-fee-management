@echo off
REM Double-click de chay dev.ps1 ma khong bi chan boi Execution Policy.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1" %*
