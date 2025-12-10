import os
import sys
import time
import json
import socket
import getpass
import logging
import traceback
import msvcrt
import pythoncom
import pytz

from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from win32com.client import Dispatch
from google.cloud import bigquery

# --- CONFIGURAÇÕES GERAIS ---
BASE_DIR = Path.home() / "graciliano" / "automacoes" / "cacatua"
TZ = pytz.timezone("America/Sao_Paulo")
TABLE_ID = "datalab-pagamentos.ADMINISTRACAO_CELULA_PYTHON.automacoes_exec"

SCRIPT_STEM = Path(__file__).stem
SCRIPT_NAME = SCRIPT_STEM.upper()

# Logs e Locks
_env_log = os.environ.get("SERVIDOR_LOG_DIR")
if _env_log:
    LOG_ROOT = Path(_env_log) / SCRIPT_STEM.upper()
else:
    LOG_ROOT = BASE_DIR / "logs" / SCRIPT_STEM.upper()

LOCK_DIR = BASE_DIR / ".locks"
LOCK_FILE = LOCK_DIR / "automacoes_exec.lock"

# Credenciais
BQ_CRED_DIR = Path.home() / "AppData" / "Roaming" / "CELPY"

LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"


# --- FUNÇÕES AUXILIARES ---

def _ensure_dirs(p: Path) -> None:
    """Garante que o diretório exista."""
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

def _now_sp() -> datetime:
    """Retorna data/hora atual em SP."""
    return datetime.now(TZ)

def _fmt_date(dt: datetime) -> str:
    """Formata data YYYY-MM-DD."""
    return dt.strftime("%Y-%m-%d")

def _fmt_time(dt: datetime) -> str:
    """Formata hora HH:MM:SS."""
    return dt.strftime("%H:%M:%S")

def _setup_logger() -> tuple[logging.Logger, Path]:
    """Configura o logger rotativo diário."""
    daily_dir = LOG_ROOT / _now_sp().strftime("%d.%m.%Y")
    _ensure_dirs(daily_dir)
    
    filename = f"{SCRIPT_NAME}_{_now_sp().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = daily_dir / filename
    
    logger = logging.getLogger(SCRIPT_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    
    # Limpa handlers antigos para evitar duplicidade se chamado múltiplas vezes
    if logger.handlers:
        logger.handlers = []

    fh = logging.FileHandler(log_path, encoding="utf-8")
    sh = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter(LOG_FORMAT)
    
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)
    
    logger.addHandler(fh)
    logger.addHandler(sh)
    
    return logger, log_path

def _find_bq_cred_json() -> Optional[Path]:
    """Procura credenciais JSON do Google no diretório padrão."""
    if BQ_CRED_DIR.exists():
        for p in sorted(BQ_CRED_DIR.glob("*.json")):
            return p
    return None

def _get_bq_client() -> bigquery.Client:
    """Retorna cliente autenticado do BigQuery."""
    cred = _find_bq_cred_json()
    if cred and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred)
    
    return bigquery.Client(project="datalab-pagamentos")

def _read_log_full(log_path: Optional[str], log_text: Optional[str]) -> str:
    """Lê o log de arquivo ou retorna o texto passado, com limite de caracteres."""
    txt = ""
    if log_text and isinstance(log_text, str):
        txt = log_text
    elif log_path and Path(log_path).exists():
        try:
            txt = Path(log_path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            txt = ""
            
    # Limite do BigQuery para STRING (segurança para não estourar payload)
    if len(txt) > 900000:
        txt = txt[-900000:]
    return txt

def _coerce_status(s: str) -> str:
    """Normaliza o status."""
    v = s.strip().upper()
    return v

def _guess_usuario_email(u: Optional[str]) -> str:
    """Gera o email do usuário ou usa o logado no Windows."""
    if u and "@" in u:
        return u
    base = u if u else getpass.getuser()
    return f"{base}@c6bank.com"


# --- CLASSES ---

class FileLock:
    """Gerenciador de Contexto para Lock de Arquivo (Windows)."""
    def __init__(self, path: Path, timeout_s: int = 60, poll_ms: int = 200):
        self.path = path
        self.timeout_s = timeout_s
        self.poll_ms = poll_ms
        self._fh = None

    def __enter__(self):
        _ensure_dirs(self.path.parent)
        start = time.time()
        self._fh = open(self.path, "a+b")
        acquired = False
        while time.time() - start < self.timeout_s:
            try:
                # Tenta travar os primeiros bytes do arquivo
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
                acquired = True
                break
            except OSError:
                time.sleep(self.poll_ms / 1000.0)
        
        if not acquired:
            self._fh.close()
            raise TimeoutError(f"Timeout aguardando lock em {self.path}")
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._fh:
            try:
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            except Exception:
                pass
            try:
                self._fh.close()
            except Exception:
                pass


class OutlookMailer:
    """Wrapper simples para envio via Outlook Desktop."""
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.app = None

    def ensure(self):
        try:
            pythoncom.CoInitialize()
            self.app = Dispatch("Outlook.Application")
        except Exception as e:
            self.logger.warning(f"Falha ao inicializar Outlook: {e}")
            self.app = None
        return self

    def send(self, to_list: List[str], subject: str, body: str, attachments: Optional[List[Path]] = None):
        if not self.app:
            return
        try:
            msg = self.app.CreateItem(0) # 0 = olMailItem
            # Limpeza simples da lista de emails
            clean_to = [e.strip() for e in to_list if e and "@" in e]
            if not clean_to:
                self.logger.warning("Lista de emails vazia, email nao enviado.")
                return

            msg.To = ";".join(clean_to)
            msg.Subject = subject
            msg.HTMLBody = body # Usando HTMLBody para suportar formatação
            
            if attachments:
                for p in attachments:
                    if p and Path(p).exists():
                        msg.Attachments.Add(str(p))
            
            msg.Send()
        except Exception as e:
            self.logger.error(f"Erro ao enviar email: {e}")


class AutomacoesExecClient:
    """Cliente principal para registrar execuções."""
    
    def __init__(self, logger: Optional[logging.Logger] = None, log_file: Optional[Path] = None):
        if logger:
            self.logger = logger
            self._own_logger = False
            self.log_file = log_file
        else:
            self.logger, self.log_file = _setup_logger()
            self._own_logger = True

    def publicar(
        self, 
        nome_automacao: str, 
        metodo_automacao: str, 
        status: str, 
        tempo_exec: str, 
        data_exec: Optional[str] = None, 
        hora_exec: Optional[str] = None, 
        usuario: Optional[str] = None, 
        log_path: Optional[str] = None, 
        log_text: Optional[str] = None, 
        
        # --- Parâmetros que você quer controlar ---
        tabela_referencia: Optional[str] = None, 
        observacao: Optional[str] = "AUTO", 
        log_completo: Optional[str] = None, 
        execucao_do_dia: Optional[int] = None, 
        
        modo_execucao: Optional[str] = "AUTO", 
        destinatarios: Optional[List[str]] = None, 
        send_email: bool = True, 
        lock_timeout_s: int = 60,
        anexos: Optional[List[Any]] = None  # <--- ADICIONADO: Parâmetro para receber lista de arquivos
    ) -> Dict[str, Any]:
        
        # --- INTEGRAÇÃO SERVIDOR: Verifica variaveis de ambiente ---
        if (not modo_execucao or modo_execucao == "AUTO") and os.environ.get("MODO_EXECUCAO"):
            modo_execucao = os.environ.get("MODO_EXECUCAO")
        
        if (not observacao or observacao == "AUTO") and os.environ.get("OBSERVACAO"):
            observacao = os.environ.get("OBSERVACAO")

        if not usuario and os.environ.get("USUARIO_EXEC"):
            usuario = os.environ.get("USUARIO_EXEC")
        # -----------------------------------------------------------

        inicio = _now_sp()
        host = socket.gethostname()
        st = _coerce_status(status)
        
        self.logger.info(f"INICIO app={SCRIPT_NAME} host={host} op=publicar nome={nome_automacao} metodo={metodo_automacao} status={st}")

        try:
            # 1. Preparação de Dados
            dt_obj = _now_sp()
            dstr = data_exec if data_exec else _fmt_date(dt_obj)
            hstr = hora_exec if hora_exec else _fmt_time(dt_obj)
            usr = _guess_usuario_email(usuario)
            
            # 2. Construção do Payload para BigQuery
            # REQUISITO: As últimas 4 colunas devem ser NULL, independente do que foi passado
            rec = {
                "nome_automacao": str(nome_automacao),
                "metodo_automacao": str(metodo_automacao),
                "status": str(st),
                "modo_execucao": str(modo_execucao if modo_execucao else "AUTO"),
                "tempo_exec": str(tempo_exec),
                "data_exec": str(dstr),
                "hora_exec": str(hstr),
                "usuario": str(usr),
                
                # --- CAMPOS FORÇADOS PARA NULL (NULLABLE NO BQ) ---
                "log_completo": None,
                "tabela_referencia": None,
                "execucao_do_dia": None,
                "observacao": None
            }

            # 3. Inserção no BigQuery com Lock
            with FileLock(LOCK_FILE, timeout_s=lock_timeout_s):
                client = _get_bq_client()
                errors = client.insert_rows_json(TABLE_ID, [rec], row_ids=[None])
                if errors:
                    raise RuntimeError(f"BQ Insert Errors: {json.dumps(errors, ensure_ascii=False)}")

            self.logger.info(f"SUCESSO BQ app={SCRIPT_NAME} status={st}")

            # 4. Envio de Email (Opcional)
            if send_email:
                # Nota: Aqui usamos os valores originais passados (como tabela_referencia) 
                # para o corpo do email, mesmo que pro banco vá NULL.
                self._enviar_email_sucesso(
                    st, metodo_automacao, nome_automacao, tempo_exec, 
                    dstr, hstr, usr, tabela_referencia, observacao, 
                    destinatarios, log_path, host, 
                    anexos_extras=anexos  # <--- PASSANDO OS ANEXOS EXTRAS
                )

            dur = round((_now_sp() - inicio).total_seconds(), 3)
            return {"ok": True, "status": st, "duracao_seg": dur}

        except Exception as e:
            err_msg = str(e)
            tb = traceback.format_exc()
            self.logger.error(f"ERRO app={SCRIPT_NAME} detalhe={err_msg} tb={tb}")
            
            # Tenta enviar email de erro mesmo se falhou o BQ
            if send_email:
                self._enviar_email_falha(
                    nome_automacao, metodo_automacao, tempo_exec, 
                    usuario, destinatarios, log_path, host, err_msg, tb,
                    anexos_extras=anexos # <--- PASSANDO OS ANEXOS EXTRAS (opcional, mas útil se gerou algo antes do erro)
                )
            
            return {"ok": False, "status": "FALHA", "erro": err_msg}

    def _enviar_email_sucesso(self, st, metodo, nome, tempo, dstr, hstr, usr, tab_ref, obs, dest, log_path, host, anexos_extras=None):
        try:
            mailer = OutlookMailer(self.logger).ensure()
            if not mailer.app: return

            subj = f"Célula Python - {metodo} - {st} - {dstr} {hstr}"
            
            # Monta corpo do email em HTML
            body = (
                f"<html><body>"
                f"<p><strong>STATUS:</strong> {st}</p>"
                f"<p><strong>AUTOMACAO:</strong> {nome}</p>"
                f"<p><strong>METODO:</strong> {metodo}</p>"
                f"<p><strong>TEMPO EXEC:</strong> {tempo}</p>"
                f"<p><strong>DATA:</strong> {dstr} {hstr}</p>"
                f"</body></html>"
            )
            
            dest_final = dest if dest else [usr]
            # Mescla logs com os anexos extras passados
            anexos = self._preparar_anexos(log_path, anexos_extras)
            
            mailer.send(dest_final, subj, body, anexos)
        except Exception:
            self.logger.error(f"ERRO_EMAIL_SUCESSO detalhe={traceback.format_exc()}")

    def _enviar_email_falha(self, nome, metodo, tempo, usuario, dest, log_path, host, erro, tb, anexos_extras=None):
        try:
            mailer = OutlookMailer(self.logger).ensure()
            if not mailer.app: return

            dstr = _fmt_date(_now_sp())
            hstr = _fmt_time(_now_sp())
            usr = _guess_usuario_email(usuario)
            
            subj = f"Célula Python - {metodo} - FALHA CRÍTICA - {dstr} {hstr}"
            body = (
                f"<html><body>"
                f"<h2>FALHA NA EXECUÇÃO</h2>"
                f"<p><strong>APP:</strong> {SCRIPT_NAME}</p>"
                f"<p><strong>HOST:</strong> {host}</p>"
                f"<p><strong>STATUS:</strong> FALHA</p>"
                f"<p><strong>AUTOMACAO:</strong> {nome}</p>"
                f"<p><strong>METODO:</strong> {metodo}</p>"
                f"<p><strong>TEMPO:</strong> {tempo}</p>"
                f"<p><strong>ERRO:</strong> {erro}</p>"
                f"<hr>"
                f"<pre>{tb}</pre>"
                f"</body></html>"
            )
            
            dest_final = dest if dest else [usr]
            # Mescla logs com os anexos extras passados
            anexos = self._preparar_anexos(log_path, anexos_extras)
            
            mailer.send(dest_final, subj, body, anexos)
        except Exception:
            self.logger.error(f"ERRO_EMAIL_FALHA detalhe={traceback.format_exc()}")

    def _preparar_anexos(self, external_log_path: Optional[str], extras: Optional[List[Any]] = None) -> List[Path]:
        anexos = []
        # Anexa o log da própria execução (se existir)
        if self.log_file and Path(self.log_file).exists():
            anexos.append(self.log_file)
        # Anexa o log passado por parametro (do script que chamou)
        if external_log_path and Path(external_log_path).exists():
            anexos.append(Path(external_log_path))
            
        # Adiciona os anexos extras solicitados (csvs, excels, etc.)
        if extras:
            for item in extras:
                if item:
                    try:
                        p = Path(str(item))
                        if p.exists():
                            anexos.append(p)
                    except Exception:
                        pass
                        
        return anexos

def main():
    """Modo de teste standalone."""
    client = AutomacoesExecClient()
    # Teste simples
    res = client.publicar(
        nome_automacao="TESTE_MANUAL",
        metodo_automacao="TEST_SCRIPT",
        status="SUCESSO",
        tempo_exec="00:00:01",
        observacao="Isso não deve ir pro banco",
        tabela_referencia="TB_TESTE_NAO_IR",
        log_completo="Texto de log ignorado",
        send_email=False,
        anexos=["C:/temp/teste.txt"] # Teste da nova funcionalidade
    )
    print(f"Resultado teste: {res}")

if __name__ == "__main__":
    main()