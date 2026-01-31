@echo off
echo.
echo ==========================================
echo       LYRN SERVER STARTUP WIZARD
echo ==========================================
echo.

:ASK_DEPS
set /p "install=Install/Update Dependencies? (Y/N): "
if /i "%install%"=="Y" goto INSTALL
if /i "%install%"=="N" goto START
echo Invalid choice.
goto ASK_DEPS

:INSTALL
echo.
echo Installing/Updating Dependencies...
pip install -r dependencies\requirements.txt
if %errorlevel% neq 0 (
    echo Error installing dependencies.
    pause
    exit /b
)

:START
echo.
echo Starting LYRN Dashboard...
python lyrn_web_v5.py
pause
