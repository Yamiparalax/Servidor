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
from pathlib import Path

# Adiciona diretório atual para encontrar o pacote servidor
current_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(current_dir))

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
