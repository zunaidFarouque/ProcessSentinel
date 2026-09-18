@echo off
echo ===================================================
echo Building ProcessSentinel Portable Application
echo ===================================================

.\.venv\Scripts\pyinstaller.exe ^
    --onedir ^
    --noconsole ^
    --name "ProcessSentinel" ^
    --contents-directory "ProcessSentinel_files" ^
    --collect-all customtkinter ^
    --clean ^
    -y ^
    src/main.py

echo.
echo ===================================================
echo Portable Build Complete!
echo Output folder: dist\ProcessSentinel\
echo   - ProcessSentinel.exe
echo   - config.json (created automatically beside exe)
echo   - ProcessSentinel_files\ (runtime dependencies)
echo ===================================================
