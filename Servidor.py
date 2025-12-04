import sys
from pathlib import Path

# Adiciona o diretório atual ao path para garantir que o pacote 'servidor' seja encontrado
current_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(current_dir))

from servidor.main import main

if __name__ == "__main__":
    sys.exit(main())
