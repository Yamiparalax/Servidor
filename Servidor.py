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
    
    try:
        import PyQt5
    except ImportError:
        missing.append("PyQt5")
        
    try:
        import pandas
    except ImportError:
        missing.append("pandas")
        
    try:
        import psutil
    except ImportError:
        missing.append("psutil")
        
    if missing:
        print(f"--- INSTALANDO DEPENDÊNCIAS FALTANTES: {', '.join(missing)} ---")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("--- INSTALAÇÃO CONCLUÍDA. REINICIANDO... ---")
        except Exception as e:
            print(f"ERRO AO INSTALAR: {e}")
            input("Pressione ENTER para sair...")
            sys.exit(1)

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
