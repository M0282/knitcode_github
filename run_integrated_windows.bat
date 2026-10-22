@echo off
cd /d "%~dp0"
set /p "TARGET=GitHub URL or local Git path: "
py integrated_cli.py "%TARGET%"
if errorlevel 1 goto end
start "" "integrated_output\index.html"
:end
pause
