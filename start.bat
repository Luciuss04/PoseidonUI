@echo off
REM Start script for Atenea Bot (BotDiscord4.0)
SETLOCAL

REM Move to script directory
cd /d "%~dp0"

REM Check for Python installation
python --version >nul 2>&1
if errorlevel 1 goto NO_PY

:CHECK_VENV
if exist "venv\Scripts\python.exe" goto VENV_EXISTS

:CREATE_VENV
echo Creando entorno virtual (venv)...
python -m venv venv
if errorlevel 1 (
    echo Fallo al crear el venv.
    pause
    exit /b 1
)
echo Activando virtualenv e instalando dependencias...
call venv\Scripts\activate.bat
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    pip install discord.py==2.1.0 python-dotenv aiohttp psutil
)
goto START_BOT

:VENV_EXISTS
echo Activando virtualenv...
call venv\Scripts\activate.bat
goto START_BOT

:NO_PY
echo Python no esta instalado o no esta en PATH. Instale Python 3.11+ y vuelva a intentarlo.
pause
exit /b 1

:START_BOT
if not exist ".env" echo Advertencia: no se encontro el archivo .env en la raiz del proyecto. Crea uno con tus claves.
echo Iniciando el bot...
python main.py

ENDLOCAL
pause
