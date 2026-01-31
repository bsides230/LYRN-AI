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
if exist "admin_token.txt" goto RUN_SERVER

echo.
echo [WARNING] No admin_token.txt found!
echo.
echo You must have an Admin Token to access the system.
echo.
set /p "create_token=Create Admin Token now? (Y/N): "
if /i "%create_token%"=="Y" goto CREATE_TOKEN
if /i "%create_token%"=="N" goto NO_TOKEN
goto START

:CREATE_TOKEN
python token_generator.py
goto RUN_SERVER

:NO_TOKEN
echo.
echo WARNING: Starting without an Admin Token. You will NOT be able to access the system.
timeout /t 5
goto RUN_SERVER

:RUN_SERVER
echo.
echo Starting LYRN Dashboard...
python lyrn_web_v5.py
pause
