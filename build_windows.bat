@echo off
REM Build a standalone .exe (no Python required to run it).
REM Run this ON WINDOWS, from this folder, after installing Python 3.10+.

pip install -r requirements.txt
pyinstaller --noconfirm --windowed --onefile --name "PhotoLookToXMP" main.py

echo.
echo Done. Find the app at: dist\PhotoLookToXMP.exe
pause
