import threading
import time
import subprocess
import os
import sys
import gc
import psutil
from datetime import datetime
from typing import Dict, Any

from backend.config import Config

class ExecutorMetodos:
    def __init__(self, logger, max_concorrencia, callback_exec_inicio=None, callback_exec_fim=None):
        self.logger = logger
        self.max_concorrencia = max_concorrencia
        self.callback_exec_inicio = callback_exec_inicio
        self.callback_exec_fim = callback_exec_fim

        self.cv = threading.Condition()
        self.fila = []
        self.em_execucao: Dict[str, Dict[str, Any]] = {}
        self.metodos_ocupados = set()
        self.threads_trabalho = []

        for _ in range(self.max_concorrencia):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            self.threads_trabalho.append(t)

    def _worker(self):
        while True:
            with self.cv:
                while not self.fila:
                    self.cv.wait()
                metodo, caminho, contexto, quando = self.fila.pop(0)
                self.em_execucao[metodo] = {
                    "inicio": datetime.now(Config.TZ),
                    "contexto": contexto,
                    "pid": None,
                }
            try:
                self._executar_subprocesso(metodo, caminho, contexto)
            finally:
                gc.collect()

    def _executar_subprocesso(self, metodo, caminho, contexto):
        rc = 1
        log_filho = None
        proc = None
        try:
            env = os.environ.copy()
            env["SERVIDOR_ORIGEM"] = Config.NOME_SERVIDOR
            env["MODO_EXECUCAO"] = (contexto.get("origem", "") or "").upper()
            env["OBSERVACAO"] = contexto.get("observacao", "") or ""
            
            usuario_solicitante = contexto.get("usuario", "") or ""
            env["USUARIO_EXEC"] = usuario_solicitante
            
            if usuario_solicitante:
                user_only = usuario_solicitante.split("@")[0].strip()
                env["USERNAME"] = user_only
                env["USER"] = user_only
                env["LOGNAME"] = user_only

            dia_dir = Config.DIR_LOGS_BASE / metodo.lower() / datetime.now(Config.TZ).strftime("%d.%m.%Y")
            dia_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(Config.TZ).strftime("%Y%m%d_%H%M%S")
            log_filho = dia_dir / f"{metodo.upper()}_{ts}.child.log"

            cmd = [sys.executable, str(caminho), "--executado-por-servidor"]

            with open(log_filho, "w", encoding="utf-8", errors="replace") as fh:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                )

                with self.cv:
                    if metodo in self.em_execucao:
                        self.em_execucao[metodo]["pid"] = proc.pid

                if callable(self.callback_exec_inicio):
                    try:
                        self.callback_exec_inicio(metodo, contexto, datetime.now(Config.TZ))
                    except Exception:
                        pass

                for linha in iter(proc.stdout.readline, ""):
                    try:
                        fh.write(linha)
                        fh.flush()
                    except Exception:
                        pass

                rc = proc.wait()

            if rc is None: rc = 1
            rc_final = 0 if rc == 0 else (2 if rc == 2 else 1)

            if callable(self.callback_exec_fim):
                try:
                    self.callback_exec_fim(metodo, contexto, rc_final, str(log_filho))
                except Exception:
                    pass
        except Exception as e:
            self.logger.error("executor_erro tipo=%s erro=%s", type(e).__name__, e)
            if callable(self.callback_exec_fim):
                try:
                    self.callback_exec_fim(metodo, contexto, 1, str(log_filho) if log_filho else "")
                except:
                    pass
        finally:
            with self.cv:
                self.em_execucao.pop(metodo, None)
                self.metodos_ocupados.discard(metodo)
                self.cv.notify_all()

    def enfileirar(self, metodo, caminho, contexto, quando=None):
        with self.cv:
            if metodo in self.metodos_ocupados:
                self.logger.info("executor_metodo_ocupado metodo=%s ignorando", metodo)
                return False
            self.metodos_ocupados.add(metodo)
            self.fila.append((metodo, caminho, contexto, quando or datetime.now(Config.TZ)))
            self.cv.notify_all()
            return True

    def snapshot_execucao(self):
        with self.cv:
            return dict(self.em_execucao)

    def parar_processo(self, metodo) -> bool:
        with self.cv:
            info = self.em_execucao.get(metodo)
            pid = (info or {}).get("pid")

        if not pid: return False

        try:
            try:
                parent = psutil.Process(pid)
            except psutil.NoSuchProcess:
                return False
            
            children = parent.children(recursive=True)
            for p in children:
                try: p.terminate()
                except: pass
            try: parent.terminate()
            except: pass
            
            psutil.wait_procs([parent] + children, timeout=5)
            return True
        except Exception as e:
            self.logger.error("kill_switch_erro metodo=%s erro=%s", metodo, e)
            return False

    def parar_todos_processos(self):
        self.logger.info("executor_parar_tudo")
        with self.cv:
            self.fila.clear()
            snapshot = dict(self.em_execucao)
        for metodo in snapshot:
            self.parar_processo(metodo)
