@echo off
REM WinFlash Pro — Build standalone .exe for Windows
REM Run this on a Windows machine to create the distributable .exe

echo [WinFlash Pro] Installing build dependencies...
pip install pyinstaller PyQt6 psutil requests

echo [WinFlash Pro] Building executable...
pyinstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --uac-admin ^
    --name "WinFlashPro" ^
    --add-data "app;app" ^
    --add-data "core;core" ^
    main.py

echo.
echo [WinFlash Pro] Done! Find WinFlashPro.exe in the dist/ folder.
pause
