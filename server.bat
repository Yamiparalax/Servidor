@echo off
echo ========================================================
echo   SERVER STARTUP (NO ADMIN REQUIRED)
echo ========================================================

REM 1. Configura Node.js (Usa os binarios embutidos no repositorio)
if exist "binaries\node" (
    echo [OK] Usando Node.js da pasta 'binaries/node'
    SET "PATH=%CD%\binaries\node;%PATH%"
    
    REM Bypass SSL Corporativo (Para o Node funcionar na rede da empresa)
    SET NODE_TLS_REJECT_UNAUTHORIZED=0
) else (
    echo [AVISO] Pasta binaries\node nao encontrada.
    echo O frontend pode nao funcionar se voce nao tiver Node instalado no Windows.
)

REM 2. Inicia o Servidor Python
echo Iniciando Server.py...
python Server.py
pause
