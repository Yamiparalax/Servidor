@echo off
echo ========================================================
echo   SERVER STARTUP (NO ADMIN REQUIRED)
echo ========================================================

REM 1. O Python agora gerencia o Node automaticamente
REM (Extrai do zip se necessario e configura o PATH em tempo de execucao)

REM 2. Inicia o Servidor Python
echo Iniciando Server.py...
python Server.py
pause
