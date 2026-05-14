@echo off
rem PaleoLeon launcher - Windows
rem Bootstraps uv on first run, then launches the dashboard.
setlocal

set "PALEO_HOME=%USERPROFILE%\.paleoleon"
if not exist "%PALEO_HOME%" mkdir "%PALEO_HOME%"

set "UV=%PALEO_HOME%\uv.exe"
where uv >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%i in ('where uv') do set "UV=%%i"
    goto :run
)
if exist "%UV%" goto :run

echo First run: installing uv into %PALEO_HOME% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$env:UV_INSTALL_DIR='%PALEO_HOME%'; $env:UV_UNMANAGED_INSTALL='%PALEO_HOME%'; try { irm https://astral.sh/uv/install.ps1 | iex } catch { Write-Host 'Failed to download uv. Are you connected to the internet?'; exit 1 }"
if errorlevel 1 (
    echo.
    pause
    exit /b 1
)

:run
echo Launching PaleoLeon...
"%UV%" tool run --refresh --from "git+https://github.com/ms3001/PaleoLeon" paleoleon

pause
