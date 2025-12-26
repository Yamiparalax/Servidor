@echo off
echo ========================================================
echo   INICIANDO SERVIDOR COM NODE.JS PORTATIL
echo ========================================================
echo.

REM Se nao existir o node_bin, tenta rodar o setup automatico
if not exist "node_bin" (
    echo [!] Node.js nao encontrado. Tentando baixar com script Python...
    python setup_node.py
)

if exist "node_bin" (
    echo [OK] Node.js detectado!
    
    REM Adiciona ao PATH
    SET "PATH=%CD%\node_bin;%PATH%"
    
    REM --- BYPASS SSL EMPRESARIAL (FIX "Self Signed Certificate") ---
    REM Conforme sua documentacao, isso desativa a verificacao estrita
    SET NODE_TLS_REJECT_UNAUTHORIZED=0
    
    echo [SECURITY] SSL/TLS Verification Disabled for Node (Corp Network Fix)
    
    REM Tenta instalar dependencias do frontend se nao existirem
    if not exist "web_frontend\node_modules" (
        echo.
        echo [NPM] Instalando dependencias do frontend (primeira vez)...
        echo Isso pode demorar um pouco...
        cd web_frontend
        call npm install --no-audit
        cd ..
    )
    
) else (
    echo [AVISO] Nao foi possivel instalar o Node.js.
    echo O servidor rodara em modo API-ONLY (sem interface bonitinha).
)

echo.
echo Iniciando Server.py...
python Server.py
pause
