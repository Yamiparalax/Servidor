import logging
import sys
import ctypes
import os
import unicodedata
import re
import importlib
import importlib.util
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import pandas as pd
from google.oauth2.credentials import Credentials
from google.cloud import bigquery

from .config import Config

class ConfiguradorLogger:
    @staticmethod
    def criar_logger():
        logger = logging.getLogger(Config.NOME_SCRIPT)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        for h in list(logger.handlers):
            logger.removeHandler(h)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        dia_dir = Config.DIR_LOGS_BASE / datetime.now(Config.TZ).strftime("%d.%m.%Y")
        dia_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(Config.TZ).strftime("%Y%m%d_%H%M%S")
        log_path = dia_dir / f"{Config.NOME_SCRIPT}_{ts}.log"
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(sh)
        logger.addHandler(fh)
        return logger, log_path, fmt

class StdoutRedirector:
    """Redireciona prints para o logger."""
    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level

    def write(self, msg):
        msg = str(msg)
        if msg.strip():
            self.logger.log(self.level, msg.rstrip())

    def flush(self):
        pass

class NormalizadorDF:
    @staticmethod
    def norm_key(valor):
        if valor is None:
            return ""
        texto = str(valor).strip()
        if texto.lower().endswith(".py"):
            texto = texto[:-3]
        texto = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
        return texto.lower()

class ClienteBigQuery:
    def __init__(self, logger, modo: str = "servidor", location: Optional[str] = None, timeout: Optional[int] = None):
        self.logger = logger
        self.client: Optional[bigquery.Client] = None
        self.location = location or os.getenv("BQ_LOCATION", "US")
        self.timeout = int(timeout or os.getenv("BQ_QUERY_TIMEOUT", "180"))
        self.offline = False
        self.modo = (modo or "servidor").lower().strip()
        self.inicializar()

    def inicializar(self):
        if Config.SERVIDOR_OFFLINE:
            self.logger.warning("bq_offline_mode_enabled - BigQuery desativado")
            self.client = None
            self.offline = True
            return
        try:
            if self.modo == "planilhas":
                self._inicializar_planilhas()
            else:
                self._inicializar_servidor()
        except Exception as e:
            self.logger.error("bq_inicializar_erro_fatal modo=%s tipo=%s erro=%s - modo OFFLINE", self.modo, type(e).__name__, e)
            self.client = None
            self.offline = True

    def _inicializar_servidor(self):
        cred_path = Config.DIR_CRED_CELPY / "pydata_google_credentials.json"
        try:
            if cred_path.exists():
                try:
                    creds = Credentials.from_authorized_user_file(str(cred_path))
                    self.client = bigquery.Client(project=Config.PROJECT_ID, credentials=creds)
                    self.logger.info("bq_inicializar_ok modo=servidor_credencial_arquivo")
                    return
                except Exception as e:
                    self.logger.error("bq_servidor_cred_arquivo_erro caminho=%s tipo=%s erro=%s", cred_path, type(e).__name__, e)

            try:
                self.client = bigquery.Client(project=Config.PROJECT_ID)
                self.logger.info("bq_inicializar_ok modo=servidor_adc_sem_arquivo")
                return
            except Exception as e_adc:
                self.logger.error("bq_servidor_adc_erro tipo=%s erro=%s", type(e_adc).__name__, e_adc)

        except Exception as e:
            self.logger.error("bq_servidor_inicializar_erro tipo=%s erro=%s", type(e).__name__, e)

        self.client = None
        self.offline = True
        self.logger.warning("bq_servidor_modo_offline_ativado")

    def _inicializar_planilhas(self):
        try:
            cred = None
            cred_especifico = Config.DIR_CRED_CELPY / "pydata_google_credentials.json"
            if cred_especifico.exists():
                cred = str(cred_especifico)
            elif Config.DIR_CRED_CELPY.exists():
                cand = list(Config.DIR_CRED_CELPY.glob("*.json"))
                if cand:
                    cred = str(cand[0])

            if cred:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred
                self.client = bigquery.Client(project=Config.PROJECT_ID)
                return

            self.client = bigquery.Client(project=Config.PROJECT_ID)
        except Exception as e:
            self.logger.error("bq_planilhas_inicializar_erro tipo=%s erro=%s", type(e).__name__, e)
            self.client = None
            self.offline = True

    def query_df(self, sql, params=None) -> pd.DataFrame:
        if self.offline or self.client is None:
            self.logger.warning("bq_query_df_offline sql_ignorado=%s", str(sql)[:200])
            return pd.DataFrame()
        try:
            job_config = bigquery.QueryJobConfig()
            if params:
                job_config.query_parameters = params
            job = self.client.query(sql, job_config=job_config, location=self.location)
            df = job.result(timeout=self.timeout).to_dataframe(create_bqstorage_client=False)
            return df
        except Exception as e:
            self.logger.error("bq_query_df_erro tipo=%s erro=%s sql=%s", type(e).__name__, e, sql)
            return pd.DataFrame()

class NotificadorEmail:
    def __init__(self, logger):
        self.logger = logger
        self.pythoncom = importlib.import_module("pythoncom") if importlib.util.find_spec("pythoncom") else None
        self.win32com = importlib.import_module("win32com.client") if importlib.util.find_spec("win32com.client") else None

    def _normalizar_destinatarios(self, destinatarios):
        lista = []
        for item in destinatarios or []:
            partes = re.split(r"[;,]", item or "")
            for p in partes:
                if p and p.strip():
                    lista.append(p.strip())
        return lista

    def _enviar_outlook(self, assunto, corpo, dest, anexos):
        if not self.pythoncom or not self.win32com:
            self.logger.warning("email_outlook_indisponivel")
            return False
        try:
            self.pythoncom.CoInitialize()
            outlook = self.win32com.Dispatch("Outlook.Application")
            mail = outlook.CreateItem(0)
            mail.Subject = assunto
            mail.To = ";".join(dest)
            mail.HTMLBody = corpo
            for anexo in anexos or []:
                p = Path(anexo)
                if not p.exists(): continue
                mail.Attachments.Add(str(p))
            mail.Send()
            self.logger.info("email_outlook_enviado para=%s", ";".join(dest))
            return True
        except Exception as e:
            self.logger.error("email_outlook_erro tipo=%s erro=%s", type(e).__name__, e)
            return False
        finally:
            try: self.pythoncom.CoUninitialize()
            except: pass

    def enviar(self, assunto, corpo, destinatarios, anexos=None):
        if Config.SERVIDOR_OFFLINE:
            self.logger.info("email_offline_simulacao assunto=%s", assunto)
            return True
        dest = self._normalizar_destinatarios(destinatarios)
        if not dest: return False
        return self._enviar_outlook(assunto, corpo, dest, anexos or [])

class DescobridorMetodos:
    def __init__(self, logger):
        self.logger = logger

    def _scan_metodos(self) -> dict:
        resultado = {}
        try:
            if not Config.BASE_DIR.exists(): return resultado
            for automacao_dir in Config.BASE_DIR.iterdir():
                if not automacao_dir.is_dir() or "gaveta" in automacao_dir.name.lower(): continue
                pasta_metodos = automacao_dir / "metodos"
                if not pasta_metodos.exists(): continue
                for py in pasta_metodos.rglob("*.py"):
                    if not py.is_file() or py.name.startswith("__"): continue
                    stem = py.stem
                    chave = NormalizadorDF.norm_key(stem)
                    resultado[chave] = {"stem": stem, "path": py, "norm_key": chave}
        except Exception as e:
            self.logger.error(f"scan_metodos_erro: {e}")
        
        if Config.SERVIDOR_OFFLINE:
            for i in range(1, 15):
                nome = f"Metodo_Ficticio_{i:02d}"
                chave = NormalizadorDF.norm_key(nome)
                resultado[chave] = {"stem": nome, "path": Path(f"C:/Fake/Path/{nome}.py"), "norm_key": chave}
        return resultado

    def mapear_por_registro(self, df_reg):
        metodos_fs = self._scan_metodos()
        mapeamento = {}
        registro_por_norm = {}
        if df_reg is not None and not df_reg.empty:
            cols = {c.lower(): c for c in df_reg.columns}
            col_metodo = cols.get("metodo_automacao")
            if col_metodo:
                for _, linha in df_reg.iterrows():
                    m_raw = str(linha[col_metodo] or "").strip()
                    if not m_raw: continue
                    norm = NormalizadorDF.norm_key(m_raw)
                    dados = {"norm_key": norm, "metodo_automacao": m_raw}
                    for k_std, k_real in cols.items():
                        dados[k_std] = str(linha[k_real]).strip() if pd.notna(linha[k_real]) else ""
                    registro_por_norm[norm] = dados

        for norm, dados_fs in metodos_fs.items():
            info_reg = registro_por_norm.get(norm)
            path = dados_fs["path"]
            stem = dados_fs["stem"]
            aba = "SEM REGISTRO"
            if info_reg:
                status = info_reg.get("status_automacao", "").upper()
                nome_auto = info_reg.get("nome_automacao", "GERAL")
                if status in ["ISOLADO", "ISOLADOS"]: aba = "ISOLADOS"
                elif status != "ATIVA": aba = "SEM AGENDAMENTOS"
                else: aba = nome_auto.upper()
            
            mapeamento.setdefault(aba, {})[stem] = {"path": path, "registro": info_reg, "norm_key": norm}
            
        if not mapeamento: mapeamento["SEM REGISTRO"] = {}
        return mapeamento

class BloqueadorSuspensao:
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002

    @staticmethod
    def manter_acordado():
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(
                BloqueadorSuspensao.ES_CONTINUOUS | BloqueadorSuspensao.ES_SYSTEM_REQUIRED | BloqueadorSuspensao.ES_DISPLAY_REQUIRED
            )
            return True
        except Exception:
            return False
