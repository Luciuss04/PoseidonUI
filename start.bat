@echo off
REM Start script for PoseidonUI Bot (BotDiscord4.0)
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
rem Comandos utilitarios: format, lint, fixlint
if /I "%~1"=="format" goto FORMAT
if /I "%~1"=="lint" goto LINT
if /I "%~1"=="fixlint" goto FIXLINT
if /I "%~1"=="test" goto TEST
goto START_BOT

:VENV_EXISTS
echo Activando virtualenv...
call venv\Scripts\activate.bat
rem Comandos utilitarios: format, lint, fixlint
if /I "%~1"=="format" goto FORMAT
if /I "%~1"=="lint" goto LINT
if /I "%~1"=="fixlint" goto FIXLINT
if /I "%~1"=="test" goto TEST
goto START_BOT

:NO_PY
echo Python no esta instalado o no esta en PATH. Instale Python 3.11+ y vuelva a intentarlo.
pause
exit /b 1

:START_BOT
if not exist ".env" (
    echo Error: no se encontro el archivo .env en la raiz del proyecto. Crea uno con tus claves.
    goto END
)
set "HAS_TOKEN="
findstr /I /C:"DISCORD_TOKEN=" ".env" >nul 2>&1
if errorlevel 1 (
    echo Error: .env no contiene DISCORD_TOKEN. Aborting.
    goto END
)
REM Crear marcador de modo dueño si no existe (local, ignorado por Git)
if not exist ".owner_mode" (
    echo.> ".owner_mode"
)
REM Comprobar coherencia de OWNER_USER_ID (.env) con OWNER_ID (bot/config.py)
set "OWNER_USER_ID="
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
  if /I "%%A"=="OWNER_USER_ID" set "OWNER_USER_ID=%%B"
)
for /f "tokens=3" %%I in ('findstr /R /C:"^[ ]*OWNER_ID[ ]*=" "bot\config.py"') do set "CONFIG_OWNER_ID=%%I"
if not "%OWNER_USER_ID%"=="" if not "%CONFIG_OWNER_ID%"=="" if "%OWNER_USER_ID%" NEQ "%CONFIG_OWNER_ID%" echo Aviso: OWNER_USER_ID en .env ("%OWNER_USER_ID%") no coincide con OWNER_ID del codigo ("%CONFIG_OWNER_ID%").
echo Iniciando el bot...
REM Priorizar valores de .env sobre variables del sistema
set "DISCORD_TOKEN="
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
  if /I "%%A"=="DISCORD_TOKEN" set "DISCORD_TOKEN=%%B"
)
python app.py
if errorlevel 1 (
    echo Error al iniciar el bot. Revisa DISCORD_TOKEN en .env y los intents.
)
goto END

:ENSURE_TOOLS
pip show ruff >nul 2>&1 || pip install ruff
pip show black >nul 2>&1 || pip install black
pip show isort >nul 2>&1 || pip install isort
exit /b 0

:FORMAT
echo Formateando codigo con black e isort...
call :ENSURE_TOOLS
python -m black .
python -m isort .
goto END

:LINT
echo Ejecutando ruff (lint)...
call :ENSURE_TOOLS
python -m ruff check .
goto END

:FIXLINT
echo Ejecutando ruff con auto-fix...
call :ENSURE_TOOLS
python -m ruff check --fix .
goto END

:TEST
echo Ejecutando pruebas basicas...
call :ENSURE_TOOLS
echo 1) Compilacion de Python
python -m compileall -q . || (
  echo Fallo en compilacion de Python & goto END
)
echo 2) Lint con ruff
python -m ruff check . || (
  echo Fallo en ruff & goto END
)
echo 3) Comprobando imports principales
python -c "import discord, aiohttp; import bot.cogs.moderacion.guardian as g; import bot.cogs.comunidad.oraculo as o; print('Imports OK')" || (
  echo Fallo al importar modulos & goto END
)
echo 4) Variables de entorno (.env)
if not exist ".env" (
  echo Aviso: falta archivo .env en la raiz.
  goto TEST_DONE
)
set "HAS_TOKEN="
set "HAS_OWNER="
set "HAS_RIOT="
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
  if /I "%%A"=="DISCORD_TOKEN" set "HAS_TOKEN=%%B"
  if /I "%%A"=="OWNER_USER_ID" set "HAS_OWNER=%%B"
  if /I "%%A"=="RIOT_API_KEY" set "HAS_RIOT=%%B"
)
if "%HAS_TOKEN%"=="" echo Aviso: falta DISCORD_TOKEN en .env
if "%HAS_OWNER%"=="" echo Aviso: falta OWNER_USER_ID en .env
if "%HAS_RIOT%"=="" echo Aviso: falta RIOT_API_KEY en .env
:
TEST_DONE
echo Pruebas basicas completadas correctamente.
goto END

ENDLOCAL
pause
