@echo on
REM DEBUG VERSION
cd /d "%~dp0"
python --version >nul 2>&1
echo ERRORLEVEL(After python): %errorlevel%
if errorlevel 1 (
    echo Python not found
    pause
    exit /b 1
)
if not exist "venv\Scripts\python.exe" (
    echo WILL CREATE VENV
    python -m venv venv
    echo ERRORLEVEL(After venv): %errorlevel%
    call venv\Scripts\activate.bat
) else (
    echo VENV EXISTS, going to activate
    call venv\Scripts\activate.bat
)

echo continue...
pause
