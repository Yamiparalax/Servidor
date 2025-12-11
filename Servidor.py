# ==============================================================================
# BANCO C6 S.A. | C6 HOLDING S.A.
# Mensageria e Cargas Operacionais - 11.Célula Python
# Analista Responsável - Monitoração e Sustentação
#
# PROJETO: Servidor de Automações (Agendador Central)
# ARQUIVO: Servidor.py
# DESCRIÇÃO: Ponto de entrada principal da aplicação. Gerencia inicialização
#            e configuração de ambiente (HML/PROD/OFFLINE).
# ==============================================================================
import sys
import os
import subprocess
from pathlib import Path

# Adiciona diretório atual para encontrar o pacote servidor
current_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(current_dir))

def check_dependencies():
    """Verifica e instala dependências críticas automaticamente na primeira execução."""
    required = {
        "PyQt5": "PyQt5",
        "pandas": "pandas",
        "psutil": "psutil",
        "win32api": "pywin32"
    }
    
    missing = []
    
    # 1. Check imports basicos
    try:
        import pandas
    except ImportError:
        missing.append("pandas")
        
    try:
        import psutil
    except ImportError:
        missing.append("psutil")

    try:
        import win32api
    except ImportError:
        missing.append("pywin32")
        
    # 2. Check PyQt5 Advanced (DLL Load Limit)
    pyqt_broken = False
    try:
        import PyQt5
        from PyQt5.QtWidgets import QApplication
    except (ImportError, Exception):
        # Includes DLL load failed
        pyqt_broken = True
        missing.append("PyQt5")
        
    if missing:
        print(f"--- CORRIGINDO DEPENDÊNCIAS FALTANTES/QUEBRADAS: {', '.join(missing)} ---")
        try:
            cmd = [sys.executable, "-m", "pip", "install"]
            
            # Se PyQt5 estiver quebrado, força reinstall para corrigir DLLs
            if pyqt_broken:
                cmd.append("--force-reinstall")
                cmd.append("--ignore-installed")
                
            cmd.extend(missing)
            
            print(f"Tentando instalar via repositório padrão...")
            subprocess.check_call(cmd)
            
        except Exception:
            print("--- FALHA NO REPOSITÓRIO PADRÃO. TENTANDO PYPI OFICIAL... ---")
            try:
                # Fallback para PyPI oficial (bypass proxy/artifactory corporativo se falhar)
                cmd_fallback = [sys.executable, "-m", "pip", "install"]
                if pyqt_broken:
                    cmd_fallback.append("--force-reinstall")
                    cmd_fallback.append("--ignore-installed")
                
                cmd_fallback.extend(["--index-url", "https://pypi.org/simple", "--trusted-host", "pypi.org"])
                cmd_fallback.extend(missing)
                
                subprocess.check_call(cmd_fallback)
                
            except Exception as e:
                print(f"ERRO CRÍTICO AO INSTALAR: {e}")
                print("Tente rodar manualmente: pip install PyQt5 PyQt5-Qt5 --force-reinstall --index-url https://pypi.org/simple")
                input("Pressione ENTER para sair...")
                sys.exit(1)

        print("--- CORREÇÃO CONCLUÍDA. REINICIANDO AGORA... ---")
        
        # Restart script
        try:
             os.execv(sys.executable, ['python'] + sys.argv)
        except OSError:
             # Fallback execution replacer
             subprocess.call([sys.executable] + sys.argv)
             sys.exit()

check_dependencies()

from servidor.config import Config
from servidor.main import main

# Configuração de modo offline
# True: Usa arquivos locais (Excel)
# False: Tenta conectar ao BigQuery/SharePoint
SERVIDOR_OFFLINE = True

if __name__ == "__main__":
    # Injeta configuração correta
    Config.SERVIDOR_OFFLINE = SERVIDOR_OFFLINE
    
    sys.exit(main())
