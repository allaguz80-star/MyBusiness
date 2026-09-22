@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Готую Лію до запуску...

where python >nul 2>nul
if errorlevel 1 (
    echo Python не знайдено. Встанови його з https://www.python.org/downloads/ і спробуй ще раз.
    echo Під час встановлення обовʼязково постав галочку "Add Python to PATH".
    pause
    exit /b 1
)

if not exist .venv (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -q -r requirements.txt

python bot.py

pause
