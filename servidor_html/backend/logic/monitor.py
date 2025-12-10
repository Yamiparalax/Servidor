import threading
import time
import shutil
import gc
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable

from backend.config import Config
from backend.core import NotificadorEmail

class MonitorSolicitacoes:
    def __init__(
        self,
        logger,
        diretorio_solicitacoes: Path,
        callback_resolver_metodo,
        callback_checar_permissao,
        callback_enfileirar,
        diretorio_historico: Path,
        notificador_email: Optional[NotificadorEmail] = None,
        intervalo_segundos: int = 10,
    ):
        self.logger = logger
        self.dir = diretorio_solicitacoes
        self.dir.mkdir(parents=True, exist_ok=True)
        self.dir_historico = diretorio_historico
        self.dir_historico.mkdir(parents=True, exist_ok=True)
        self.callback_resolver_metodo = callback_resolver_metodo
        self.callback_checar_permissao = callback_checar_permissao
        self.callback_enfileirar = callback_enfileirar
        self.notificador_email = notificador_email
        self.intervalo_segundos = intervalo_segundos
        self._parar = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _extrair_metodo_login(self, stem: str):
        texto = stem.strip()
        if "_" in texto:
            metodo, login = texto.split("_", 1)
            return metodo.strip(), login.strip()
        if "." in texto:
            metodo, login = texto.split(".", 1)
            return metodo.strip(), login.strip()
        return texto, ""

    def _mover_para_historico(self, arquivo: Path) -> Optional[Path]:
        try:
            ts = datetime.now(Config.TZ).strftime("%Y%m%d_%H%M%S")
            destino = self.dir_historico / f"{arquivo.stem}_{ts}{arquivo.suffix}"
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(arquivo), destino)
            self.logger.info("solicitacao_arquivo_movido origem=%s destino=%s", str(arquivo), str(destino))
            return destino
        except Exception as e:
            self.logger.error("solicitacao_mover_erro arquivo=%s erro=%s", str(arquivo), e)
            return None

    def _enviar_email_inicio(self, metodo, login, arquivo_anexo):
        if not self.notificador_email or not login: return
        assunto = f"Solicitação de método {metodo} em execução"
        corpo = "Seu método foi recebido pelo servidor e está em execução."
        anexos = [arquivo_anexo] if arquivo_anexo else []
        self.notificador_email.enviar(assunto, corpo, [login], anexos)

    def _enviar_email_metodo_nao_encontrado(self, metodo, login, arquivo_anexo):
        if not self.notificador_email or not login: return
        assunto = f"Solicitação de método {metodo} não localizado"
        corpo = "Não foi possível localizar o método solicitado."
        anexos = [arquivo_anexo] if arquivo_anexo else []
        self.notificador_email.enviar(assunto, corpo, [login], anexos)

    def _loop(self):
        while not self._parar:
            try:
                arquivos = list(self.dir.glob("*.txt"))
                for f in arquivos:
                    try:
                        nome = f.name
                        if nome.startswith("~") or nome.startswith("."):
                            self._mover_para_historico(f)
                            continue
                        
                        try:
                            if f.stat().st_size == 0:
                                pass # Logging warning?
                            conteudo = f.read_text(encoding="utf-8", errors="ignore").strip()
                        except:
                            conteudo = ""

                        stem = f.stem
                        metodo_raw, login_raw = self._extrair_metodo_login(stem)
                        if not metodo_raw:
                            self._mover_para_historico(f)
                            continue

                        alvo_login = str(login_raw or "").strip().lower()
                        if alvo_login and "@" not in alvo_login:
                            alvo_login = f"{alvo_login}@c6bank.com"

                        metodo_norm, caminho = self.callback_resolver_metodo(metodo_raw)
                        if not caminho:
                            destino = self._mover_para_historico(f)
                            self._enviar_email_metodo_nao_encontrado(metodo_raw, alvo_login, destino)
                            continue

                        pode = self.callback_checar_permissao(metodo_norm or metodo_raw, alvo_login or "*")
                        if not pode:
                            self._mover_para_historico(f)
                            continue

                        destino = self._mover_para_historico(f)
                        ctx = {
                            "origem": "solicitacao",
                            "usuario": alvo_login,
                            "observacao": conteudo,
                            "justificativa": "Solicitação da área",
                            "arquivo_solicitacao": str(destino) if destino else "",
                        }
                        self._enviar_email_inicio(metodo_norm or metodo_raw, alvo_login, destino)
                        self.callback_enfileirar(metodo_norm or metodo_raw, caminho, ctx, datetime.now(Config.TZ))
                    except Exception as e:
                        self.logger.error(f"Erro processando arquivo {f}: {e}")
            except Exception:
                pass
            time.sleep(self.intervalo_segundos)
