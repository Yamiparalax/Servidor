import threading
import time
import shutil
import gc
import psutil
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Dict, Any

from PyQt5.QtCore import QThread, pyqtSignal

from servidor.config import Config
from servidor.core import NotificadorEmail

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
            self.logger.info(
                "solicitacao_arquivo_movido origem=%s destino=%s",
                str(arquivo),
                str(destino),
            )
            return destino
        except Exception as e:
            self.logger.error(
                "solicitacao_mover_erro arquivo=%s tipo=%s erro=%s",
                str(arquivo),
                type(e).__name__,
                e,
            )
            return None

    def _enviar_email_inicio(self, metodo, login, arquivo_anexo):
        if not self.notificador_email or not login:
            return
        assunto = f"Solicitação de método {metodo} em execução"
        corpo = (
            "Seu método foi recebido pelo servidor e está em execução. "
            "Aguarde de 5 a 10 minutos para receber o status da execução."
        )
        anexos = [arquivo_anexo] if arquivo_anexo else []
        self.notificador_email.enviar(assunto, corpo, [login], anexos)

    def _enviar_email_metodo_nao_encontrado(self, metodo, login, arquivo_anexo):
        if not self.notificador_email or not login:
            return
        assunto = f"Solicitação de método {metodo} não localizado"
        corpo = (
            "Não foi possível localizar o método solicitado. "
            "Entre em contato com carlos.lsilva@c6bank.com ou sofia.fernandes@c6bank.com para confirmar o nome correto."
        )
        anexos = [arquivo_anexo] if arquivo_anexo else []
        self.notificador_email.enviar(assunto, corpo, [login], anexos)

    def _loop(self):
        while not self._parar:
            try:
                arquivos = list(self.dir.glob("*.txt"))
                if arquivos:
                    self.logger.info(
                        "monitor_solicitacoes_arquivos_encontrados total=%s dir=%s",
                        len(arquivos),
                        str(self.dir),
                    )
                for f in arquivos:
                    try:
                        nome = f.name

                        self.logger.info(
                            "monitor_solicitacoes_arquivo_encontrado nome=%s caminho=%s",
                            nome,
                            str(f),
                        )

                        if nome.startswith("~") or nome.startswith("."):
                            destino_temp = self._mover_para_historico(f)
                            self.logger.info(
                                "solicitacao_ignorada_nome_temporario nome=%s destino=%s",
                                nome,
                                str(destino_temp) if destino_temp else "",
                            )
                            continue

                        try:
                            tamanho = f.stat().st_size
                        except Exception as e_stat:
                            destino_stat = self._mover_para_historico(f)
                            self.logger.error(
                                "solicitacao_arquivo_inacessivel nome=%s tipo=%s erro=%s destino=%s",
                                nome,
                                type(e_stat).__name__,
                                e_stat,
                                str(destino_stat) if destino_stat else "",
                            )
                            continue

                        if tamanho == 0:
                            self.logger.warning(
                                "solicitacao_arquivo_vazio nome=%s caminho=%s",
                                nome,
                                str(f),
                            )

                        try:
                            conteudo = f.read_text(encoding="utf-8", errors="ignore").strip()
                        except Exception:
                            conteudo = ""

                        stem = f.stem
                        metodo_raw, login_raw = self._extrair_metodo_login(stem)
                        if not metodo_raw:
                            destino_nome = self._mover_para_historico(f)
                            self.logger.warning(
                                "solicitacao_sem_metodo nome=%s destino=%s",
                                nome,
                                str(destino_nome) if destino_nome else "",
                            )
                            continue

                        alvo_login = str(login_raw or "").strip().lower()
                        if alvo_login and "@" not in alvo_login:
                            alvo_login = f"{alvo_login}@c6bank.com"

                        metodo_norm, caminho = self.callback_resolver_metodo(metodo_raw)
                        if not caminho:
                            destino = self._mover_para_historico(f)
                            self._enviar_email_metodo_nao_encontrado(
                                metodo_raw, alvo_login, destino
                            )
                            self.logger.info(
                                "solicitacao_metodo_nao_encontrado metodo=%s arquivo=%s",
                                metodo_raw,
                                nome,
                            )
                            continue

                        pode = self.callback_checar_permissao(
                            metodo_norm or metodo_raw,
                            alvo_login or "*",
                        )
                        if not pode:
                            self._mover_para_historico(f)
                            self.logger.info(
                                "solicitacao_sem_permissao metodo=%s login=%s",
                                metodo_raw,
                                alvo_login,
                            )
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
                        self.callback_enfileirar(
                            metodo_norm or metodo_raw,
                            caminho,
                            ctx,
                            datetime.now(Config.TZ),
                        )
                        self.logger.info(
                            "solicitacao_enfileirada metodo=%s login=%s destino=%s",
                            metodo_norm or metodo_raw,
                            alvo_login,
                            str(destino) if destino else "",
                        )
                    except Exception as e_arquivo:
                        self.logger.error(
                            "monitor_solicitacoes_arquivo_erro arquivo=%s tipo=%s erro=%s",
                            getattr(f, "name", "?"),
                            type(e_arquivo).__name__,
                            e_arquivo,
                        )
                        destino_falha = self._mover_para_historico(f)
                        if destino_falha:
                            self.logger.info(
                                "solicitacao_movida_pos_erro nome=%s destino=%s",
                                getattr(f, "name", "?"),
                                str(destino_falha),
                            )
                        continue
            except Exception as e:
                self.logger.error("monitor_solicitacoes_erro tipo=%s erro=%s", type(e).__name__, e)
            finally:
                gc.collect()
            time.sleep(self.intervalo_segundos)

    def parar(self):
        self._parar = True

class MonitorRecursos(QThread):
    sinal_recursos = pyqtSignal(float, float, float, int)  # cpu, ram%, swap%, temp_MB
    sinal_msg = pyqtSignal(str)

    def __init__(self, logger, parent=None):
        super().__init__(parent)
        self.logger = logger
        self._stop = False
        self._temp_dir = self._resolver_temp_dir()
        self._temp_size_mb_cache = 0
        self._lock = threading.Lock()

    def _resolver_temp_dir(self) -> Path:
        # Usa o mesmo diretório de logs definido na Config para garantir que limpamos o lugar certo
        return Config.DIR_LOGS_BASE

    def _calcular_tamanho_temp_mb(self) -> int:
        try:
            if not self._temp_dir.exists():
                return 0
            total = 0
            for root, dirs, files in os.walk(self._temp_dir):
                for f in files:
                    fp = Path(root) / f
                    try:
                        total += fp.stat().st_size
                    except Exception:
                        pass
            return int((total + (1024 * 1024 - 1)) / (1024 * 1024))
        except Exception as e:
            self.logger.error(
                "monitor_recursos_temp_size_erro tipo=%s erro=%s",
                type(e).__name__,
                e,
            )
            return self._temp_size_mb_cache

    def limpar_temp(self):
        """Dispara limpeza da pasta TEMP em thread separada."""
        t = threading.Thread(target=self._limpar_temp_bg, daemon=True)
        t.start()

    def _limpar_temp_bg(self):
        try:
            if not self._temp_dir.exists():
                self.sinal_msg.emit("Pasta TEMP não existe, nada a limpar.")
                return
            for item in self._temp_dir.iterdir():
                try:
                    if item.is_file() or item.is_symlink():
                        item.unlink(missing_ok=True)
                    elif item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                except Exception:
                    # ignora arquivo travado
                    pass
            novo_tam = self._calcular_tamanho_temp_mb()
            with self._lock:
                self._temp_size_mb_cache = novo_tam
            self.sinal_msg.emit(f"TEMP limpa. Tamanho atual: {novo_tam} MB")
        except Exception as e:
            self.logger.error(
                "monitor_recursos_limpar_temp_erro tipo=%s erro=%s",
                type(e).__name__,
                e,
            )
            self.sinal_msg.emit(f"Erro ao limpar TEMP: {e}")

    def run(self):
        # pequeno delay para não competir com renderização inicial
        time.sleep(0.5)

        contador_temp = 0
        # calcula uma vez no início
        with self._lock:
            self._temp_size_mb_cache = self._calcular_tamanho_temp_mb()

        while not self._stop:
            try:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                swap = psutil.swap_memory()

                if contador_temp == 0:
                    novo = self._calcular_tamanho_temp_mb()
                    with self._lock:
                        self._temp_size_mb_cache = novo

                with self._lock:
                    temp_mb = self._temp_size_mb_cache

                self.sinal_recursos.emit(
                    float(cpu),
                    float(mem.percent),
                    float(swap.percent),
                    int(temp_mb),
                )
            except Exception as e:
                self.logger.error("monitor_recursos_loop_erro tipo=%s erro=%s", type(e).__name__, e)
            finally:
                gc.collect()

            time.sleep(1)
            contador_temp = (contador_temp + 1) % 300  # 300 segundos = 5 minutos
            
            # Auto-limpeza a cada 5 minutos
            if contador_temp == 0:
                 self.limpar_temp()

    def parar(self):
        self._stop = True
