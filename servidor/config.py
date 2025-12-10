import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo



class Config:
    # Informações básicas
    NOME_SERVIDOR = "Servidor.py"
    NOME_AUTOMACAO = "novo_servidor"
    NOME_SCRIPT = Path(__file__).parent.parent.stem.lower()
    TZ = ZoneInfo("America/Sao_Paulo")
    
    # Modo headless
    _env_headless = os.getenv("SERVIDOR_HEADLESS", "").strip().lower()
    HEADLESS = _env_headless in {"1", "true", "yes", "sim"}
    if HEADLESS:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    # Modo offline
    # Definido por padrão como True, mas sobrescrito em Servidor.py
    SERVIDOR_OFFLINE = True

    # Caminhos do sistema
    BASE_SERVIDOR_DIR = Path(__file__).resolve().parent.parent
    
    @staticmethod
    def _path_from_env(var_name: str, default: Path) -> Path:
        valor = os.getenv(var_name)
        if valor:
            try:
                return Path(valor).expanduser().resolve()
            except Exception:
                return default
        return default

    DIR_SERVIDOR = _path_from_env(
        "SERVIDOR_DIR",
        Path.home()
        / "C6 CTVM LTDA, BANCO C6 S.A. e C6 HOLDING S.A"
        / "Mensageria e Cargas Operacionais - 11.CelulaPython"
        / "graciliano"
        / "novo_servidor",
    )
    
    BASE_DIR = _path_from_env(
        "SERVIDOR_BASE_DIR",
        Path.home()
        / "C6 CTVM LTDA, BANCO C6 S.A. e C6 HOLDING S.A"
        / "Mensageria e Cargas Operacionais - 11.CelulaPython"
        / "graciliano"
        / "automacoes",
    )
    
    DIR_LOGS_BASE = _path_from_env(
        "SERVIDOR_LOG_DIR",
        Path(os.environ.get("TEMP", os.environ.get("TMP", "/tmp"))) / "Servidor_Logs",
    )
    
    DIR_SOLICITACOES = DIR_SERVIDOR / "solicitacoes_das_areas"
    DIR_HISTORICO_SOLICITACOES = DIR_SERVIDOR / "historico_solicitacoes"
    
    DIR_CRED_CELPY = _path_from_env(
        "SERVIDOR_CRED_DIR",
        Path.home() / "AppData" / "Roaming" / "CELPY" / "tokens",
    )

    # Concorrência
    MAX_CONCURRENCY = int(os.getenv("SERVIDOR_MAX_CONCURRENCY", "5"))

    # Downloads e planilhas
    DOWNLOADS_DIR = _path_from_env("SERVIDOR_DOWNLOAD_DIR", Path.home() / "Downloads")
    DIR_XLSX_AUTEXEC = DOWNLOADS_DIR / "automacoes_exec"
    DIR_XLSX_REG = DOWNLOADS_DIR / "registro_automacoes"
    ARQ_XLSX_AUTEXEC = DIR_XLSX_AUTEXEC / "automacoes_exec.xlsx"
    ARQ_XLSX_REG = DIR_XLSX_REG / "registro_automacoes.xlsx"

    # Configurações BigQuery
    PROJECT_ID = "datalab-pagamentos"
    DATASET_ADMIN = "ADMINISTRACAO_CELULA_PYTHON"
    TBL_AUTOMACOES_EXEC = f"{PROJECT_ID}.{DATASET_ADMIN}.automacoes_exec"
    TBL_REGISTRO_AUTOMACOES = f"{PROJECT_ID}.{DATASET_ADMIN}.Registro_automacoes"

    # Constantes
    MAPA_DIAS_SEMANA = {
        "segunda": 0, "terca": 1, "terça": 1, "quarta": 2,
        "quinta": 3, "sexta": 4, "sabado": 5, "sábado": 5, "domingo": 6,
    }
