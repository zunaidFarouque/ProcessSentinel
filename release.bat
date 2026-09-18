@echo off
setlocal
echo ===================================================
echo   ProcessSentinel Release Tool
echo ===================================================
echo.
echo WARNING: This tool will publish a new release to GitHub
echo and update the Scoop bucket repository.
echo.
echo Ensure you have:
echo   1. Verified code with pytest
echo   2. Run build-portable.bat to update dist\
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\release.ps1" %*

pause
