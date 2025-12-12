import threading
import time
import gc
import re
import pandas as pd
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Optional

from servidor.config import Config
from servidor.core import NormalizadorDF
import getpass

class SincronizadorPlanilhas:
    def __init__(self, logger, cliente_bq, intervalo_segundos=600, callback_atualizacao=None):
        self.logger = logger
        self.cliente_bq = cliente_bq
        self.intervalo_segundos = int(intervalo_segundos)
        self.callback_atualizacao = callback_atualizacao
        self.ultima_execucao = None
        self.ultima_modificacao = None # Timestamp de qualquer alteração (Sync do BQ ou Local)
        self.proxima_execucao = None
        self._parar = False
        self._pausado = False
        self._lock_memoria = threading.Lock()
        self._memoria_local_execucoes = set()
        self._data_memoria_local = datetime.now(Config.TZ).date()
        self.df_exec = pd.DataFrame()
        self.df_reg = pd.DataFrame()
        self._sync_lock = threading.Lock()
        Config.DIR_XLSX_AUTEXEC.mkdir(parents=True, exist_ok=True)
        Config.DIR_XLSX_REG.mkdir(parents=True, exist_ok=True)
        Config.DIR_XLSX_REG.mkdir(parents=True, exist_ok=True)
        self._thread = None
        
        # Cache local para execuções imediatas (Manual ou Agendada) antes do Sync do BQ
        # Lista de dicts: {metodo_automacao, dt_full, status, ...}
        self._execucoes_locais_temporarias = []

    def iniciar_monitoramento(self):
        if self._thread and getattr(self._thread, "is_alive", lambda: False)():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def pausar(self, status: bool):
        self._pausado = bool(status)

    def forcar_atualizacao(self):
        t = threading.Thread(target=self._run_sync_once, daemon=True)
        t.start()

    def _run_sync_once(self):
        if not self._sync_lock.acquire(blocking=False):
            return
        try:
            self.sincronizar_de_arquivos()
        except Exception:
            pass
        finally:
            self._sync_lock.release()

    def registrar_execucao_local(self, metodo: str, data_hora: datetime, status: str = "RODANDO", log_path: str = ""):
        """Registra uma execução localmente para feedback imediato e evitar duplicidade de agendamento."""
        with self._lock_memoria:
            # Remove duplicatas exatas se houver
            self._execucoes_locais_temporarias = [
                x for x in self._execucoes_locais_temporarias 
                if not (x["metodo_automacao"] == metodo and x["dt_full"] == data_hora)
            ]
            
            self._execucoes_locais_temporarias.append({
                "metodo_automacao": metodo,
                "dt_full": data_hora,
                "data_exec": data_hora.strftime("%Y-%m-%d"),
                "hora_exec": data_hora.strftime("%H:%M:%S"),
                "status": status,
                "log_arquivo": log_path,
                "origem_dado": "LOCAL_CACHE"
            })
            
            # Força re-processamento do DF combinado
            # Mesmo se df_exec estiver vazio, devemos iniciar com este registro
            
            novo_row = pd.DataFrame([{
               "metodo_automacao": metodo,
               "dt_full": data_hora,
               "data_exec": data_hora.strftime("%Y-%m-%d"),
               "hora_exec": data_hora.strftime("%H:%M:%S"),
               "status": status,
               "log_arquivo": log_path
            }])
            
            if self.df_exec.empty:
                 self.df_exec = novo_row
            elif "dt_full" in self.df_exec.columns:
                 self.df_exec = pd.concat([novo_row, self.df_exec], ignore_index=True)
                 try:
                     self.df_exec = self.df_exec.sort_values("dt_full", ascending=False)
                 except: pass
                 
            self.ultima_modificacao = datetime.now(Config.TZ)


    def registrar_execucao_imediata(self, metodo: str, slot_hora: str = "MANUAL"):
        with self._lock_memoria:
            hoje = datetime.now(Config.TZ).date()
            if hoje != self._data_memoria_local:
                self._memoria_local_execucoes.clear()
                self._data_memoria_local = hoje
            norm = NormalizadorDF.norm_key(metodo)
            self._memoria_local_execucoes.add((norm, str(slot_hora)))

    def ja_executou_hoje(self, metodo: str) -> bool:
        norm = NormalizadorDF.norm_key(metodo)
        hoje = datetime.now(Config.TZ).date()
        with self._lock_memoria:
            if self._data_memoria_local == hoje:
                for m, _ in self._memoria_local_execucoes:
                    if m == norm:
                        return True
        if self.df_exec.empty or "dt_full" not in self.df_exec.columns:
            return False
        try:
            df_hj = self.df_exec[self.df_exec["dt_full"].dt.date == hoje]
            if df_hj.empty:
                return False
            cols = {c.lower(): c for c in df_hj.columns}
            c_met = cols.get("metodo_automacao")
            if not c_met:
                return False
            metodos = df_hj[c_met].apply(NormalizadorDF.norm_key).values
            return norm in metodos
        except Exception:
            return False

    def ja_executou_para_horario(self, metodo: str, dt_slot: datetime) -> bool:
        norm = NormalizadorDF.norm_key(metodo)
        hoje = datetime.now(Config.TZ).date()
        hora_slot_str = dt_slot.strftime("%H:%M")
        with self._lock_memoria:
            if self._data_memoria_local == hoje and (norm, hora_slot_str) in self._memoria_local_execucoes:
                return True
        if self.df_exec.empty or "dt_full" not in self.df_exec.columns:
            return False
        try:
            df_hoje = self.df_exec[self.df_exec["dt_full"].dt.date == hoje]
            if df_hoje.empty:
                return False
            cols = {c.lower(): c for c in df_hoje.columns}
            c_met = cols.get("metodo_automacao")
            if not c_met:
                return False
            df_metodo = df_hoje[df_hoje[c_met].apply(NormalizadorDF.norm_key) == norm]
            if df_metodo.empty:
                return False
            tolerancia = dt_slot.replace(tzinfo=None) - timedelta(minutes=15)
            tempos = df_metodo["dt_full"]
            if tempos.dt.tz is not None:
                tempos = tempos.dt.tz_localize(None)
            return (tempos >= tolerancia).any()
        except Exception:
            return False

    def _converter_data_robusta(self, series: pd.Series) -> pd.Series:
        if series is None:
            return pd.to_datetime(series)
        if getattr(series, "empty", False):
            return pd.to_datetime(series)
        s = series.astype(str).str.strip()
        res = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
        mask_iso = s.str.match(r"^\d{4}-\d{2}-\d{2}(\s|$)")
        if mask_iso.any():
            tmp = pd.to_datetime(s[mask_iso], format="%Y-%m-%d %H:%M:%S", errors="coerce")
            still_nat = tmp.isna()
            if still_nat.any():
                tmp2 = pd.to_datetime(s[mask_iso][still_nat], format="%Y-%m-%d", errors="coerce")
                tmp = tmp.combine_first(tmp2)
            res.loc[mask_iso] = tmp
        if (~mask_iso).any():
            res.loc[~mask_iso] = pd.to_datetime(s[~mask_iso], dayfirst=True, errors="coerce")
        return res

    def _preparar_exec_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        df = df.copy()
        df.columns = [c.strip() for c in df.columns]
        cols = {c.lower(): c for c in df.columns}
        c_data = cols.get("data_exec") or cols.get("data_execucao")
        c_hora = cols.get("hora_exec") or cols.get("hora_execucao")
        if not c_data:
            return df
        s_data = df[c_data].astype(str).str.strip()
        if c_hora:
            s_hora = df[c_hora].astype(str).str.strip()
            s_hora = s_hora.replace(["nan", "NaT", "None", "<NA>"], "00:00:00")
            s_hora = s_hora.str.replace(r"\.0$", "", regex=True)
            s_full = (s_data + " " + s_hora).str.strip()
        else:
            s_full = s_data
        dt_series = self._converter_data_robusta(s_full)
        try:
            if hasattr(dt_series, "dt") and getattr(dt_series.dt, "tz", None) is not None:
                try:
                    dt_series = dt_series.dt.tz_convert(Config.TZ).dt.tz_localize(None)
                except Exception:
                    dt_series = dt_series.dt.tz_localize(None)
        except Exception:
            pass
        df["dt_full"] = pd.to_datetime(dt_series, errors="coerce")
        df = df.sort_values("dt_full", ascending=False)
        return df

    def _converter_tudo_para_texto(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        df2 = df.copy()
        for col in df2.columns:
            if col == "dt_full":
                continue
            df2[col] = df2[col].astype(str).replace(["nan", "None", "NaT", "<NA>"], "")
        return df2

    def sincronizar_de_arquivos(self) -> bool:
        if Config.SERVIDOR_OFFLINE:
            self._gerar_dados_ficticios()
            return True

        if not self._sync_lock.acquire(blocking=False):
            return False
        try:
            if not getattr(self.cliente_bq, "offline", False) and getattr(self.cliente_bq, "client", None):
                try:
                    self.logger.info("Iniciando download BQ para arquivos locais...")
                    df_e = self.cliente_bq.query_df(f"SELECT * FROM `{Config.TBL_AUTOMACOES_EXEC}`")
                    df_e = df_e.astype(str)
                    df_e.to_excel(Config.ARQ_XLSX_AUTEXEC, index=False)
                    
                    df_r = self.cliente_bq.query_df(f"SELECT * FROM `{Config.TBL_REGISTRO_AUTOMACOES}`")
                    df_r = df_r.astype(str)
                    df_r.to_excel(Config.ARQ_XLSX_REG, index=False)
                    self.logger.info("Download BQ concluído com sucesso.")
                except Exception as e:
                    self.logger.error("FALHA AO BAIXAR DO BQ (Usando cache local): %s", e)
            try:
                if not Config.ARQ_XLSX_AUTEXEC.exists() or not Config.ARQ_XLSX_REG.exists():
                    return False
                df_exec = pd.read_excel(Config.ARQ_XLSX_AUTEXEC, sheet_name=0, dtype=str)
                df_reg = pd.read_excel(Config.ARQ_XLSX_REG, sheet_name=0, dtype=str)
                if df_reg.empty:
                    return False
                df_exec = self._preparar_exec_df(df_exec)
                df_exec = self._converter_tudo_para_texto(df_exec)
                df_reg = self._converter_tudo_para_texto(df_reg)
                
                # MERGE COM O CACHE LOCAL (PRESERVA O QUE O BQ AINDA NAO TEM)
                # Mantem apenas itens do cache que sao mais recentes que o timestamp do BQ ou que nao estao la
                # Simplificacao: Concatena tudo e deixa o sort resolver. 
                # Idealmente removeriamos do cache o que ja entrou no BQ.
                if self._execucoes_locais_temporarias:
                    df_local = pd.DataFrame(self._execucoes_locais_temporarias)
                    if not df_local.empty:
                        # Se BQ trouxe dados, removemos duplicatas baseadas em algum criterio?
                        # Melhor: Concatena e remove duplicatas exatas?
                        # Como status pode mudar, vamos assumir que o BQ é a fonte da verdade FINAL,
                        # exceto para o dia de hoje onde o local pode ser mais recente.
                        
                        # Limpa execucoes temporarias antigas (> 2 dias)
                        limit_date = datetime.now(Config.TZ) - timedelta(days=2)
                        self._execucoes_locais_temporarias = [
                            x for x in self._execucoes_locais_temporarias 
                            if x["dt_full"] > limit_date
                        ]
                        
                        # Recria df_local atualizado
                        if self._execucoes_locais_temporarias:
                            df_local = pd.DataFrame(self._execucoes_locais_temporarias)
                            df_exec = pd.concat([df_local, df_exec], ignore_index=True)
                            
                        df_exec = df_exec.sort_values("dt_full", ascending=False)

                with self._lock_memoria:
                    self.df_exec = df_exec
                    self.df_reg = df_reg
                self.ultima_execucao = datetime.now(Config.TZ)
                self.ultima_modificacao = self.ultima_execucao
                self.proxima_execucao = self.ultima_execucao + timedelta(seconds=self.intervalo_segundos)
                # if self.callback_atualizacao:
                #    try:
                #        self.callback_atualizacao(self.df_exec, self.df_reg)
                #    except Exception:
                #        pass
                return True
            except Exception:
                return False
        finally:
            try:
                self._sync_lock.release()
            except Exception:
                pass

    def _gerar_dados_ficticios(self):
        """Gera DataFrames fictícios para teste de interface."""
        import random
        
        # Gera DF de Registro
        registros = []
        areas = ["FINANCEIRO", "RISCO", "BACKOFFICE", "COMERCIAL", "TI"]
        
        for i in range(1, 15):
            nome = f"Metodo_Ficticio_{i:02d}"
            area = random.choice(areas)
            status = "ATIVA"
            if i % 5 == 0: status = "ISOLADO"
            elif i % 7 == 0: status = "PAUSADA"
            
            horarios = []
            if status == "ATIVA":
                for _ in range(random.randint(1, 3)):
                    h = random.randint(8, 18)
                    m = random.choice([0, 15, 30, 45])
                    horarios.append(f"{h:02d}:{m:02d}")
            
            registros.append({
                "metodo_automacao": nome,
                "nome_automacao": area, # Usando area como 'nome' para criar abas
                "status_automacao": status,
                "horario": "; ".join(horarios),
                "dia_semana": "segunda; terca; quarta; quinta; sexta",
                "responsavel": "Usuario Teste"
            })
            
        df_reg = pd.DataFrame(registros)
        
        # Gera DF de Execução
        execucoes = []
        agora = datetime.now(Config.TZ)
        for i in range(1, 15):
            nome = f"Metodo_Ficticio_{i:02d}"
            # Gera algumas execuções passadas
            for j in range(random.randint(0, 5)):
                delta_min = random.randint(10, 5000)
                dt = agora - timedelta(minutes=delta_min)
                execucoes.append({
                    "metodo_automacao": nome,
                    "data_exec": dt.strftime("%Y-%m-%d"),
                    "hora_exec": dt.strftime("%H:%M:%S"),
                    "status": random.choice(["SUCESSO", "FALHA", "SUCESSO", "SUCESSO"]),
                    "log_arquivo": f"log_fake_{nome}_{j}.txt"
                })
                
        df_exec = pd.DataFrame(execucoes)
        
        # Processa
        df_exec = self._preparar_exec_df(df_exec)
        df_exec = self._converter_tudo_para_texto(df_exec)
        df_reg = self._converter_tudo_para_texto(df_reg)
        
        with self._lock_memoria:
            self.df_exec = df_exec
            self.df_reg = df_reg
        
        self.ultima_execucao = datetime.now(Config.TZ)
        self.proxima_execucao = self.ultima_execucao + timedelta(seconds=self.intervalo_segundos)
        
        if self.callback_atualizacao:
            try:
                self.callback_atualizacao(self.df_exec, self.df_reg)
            except Exception:
                pass

    def _loop(self):
        while not self._parar:
             # Se pausado, espera curto e continua
             if self._pausado:
                 time.sleep(1)
                 continue

             try:
                 agora = datetime.now(Config.TZ)
                 
                 # Se não tem proxima definida, define para agora (primeira exec)
                 if not self.proxima_execucao:
                     self.proxima_execucao = agora
                 
                 # Se ainda não chegou a hora
                 if agora < self.proxima_execucao:
                     # Espera um pouco (max 1s para responder a stop/pause rapido) ou o tempo restante
                     # Mas como queremos responsividade ao STOP, sleep(1) é melhor que sleep(delta)
                     time.sleep(1)
                     continue
                 
                 # Hora de sincronizar
                 self.sincronizar_de_arquivos()
                 
                 # O sincronizar_de_arquivos JA ATUALIZA self.proxima_execucao
                 # Então o loop vai esperar naturalmente na próxima iteração
                 
             except Exception:
                 time.sleep(5)
             finally:
                 gc.collect()

    def parar(self):
        self._parar = True

class AgendadorMetodos:
    def __init__(
        self,
        logger,
        obter_mapeamento: Callable[[], Dict[str, Dict[str, Any]]],
        obter_exec_df: Callable[[], Optional[Any]],
        enfileirar_callback: Callable[[str, Any, Dict[str, Any], datetime], None],
        intervalo_segundos: int = 60,
    ):
        self.logger = logger
        self.obter_mapeamento = obter_mapeamento
        self.obter_exec_df = obter_exec_df
        self.enfileirar_callback = enfileirar_callback
        self.intervalo_segundos = max(5, int(intervalo_segundos))
        self.tz = Config.TZ
        self.lock = threading.Lock()
        self.proximas_execucoes = {}
        self.status_agendamento = {}
        self._ultimos_terminos = {} # {metodo: datetime_fim}
        self._metodos_rodando = set()
        self._stop = False
        self.data_ref = datetime.now(self.tz).date()
        self._catchup_executado = False
        self._execucoes_gatilho_local = set() # (metodo_norm, datetime_ref)
        self.thread_scheduler = threading.Thread(target=self._loop_scheduler, daemon=True)
        self.thread_recalc = threading.Thread(target=self._loop_recalc, daemon=True)
        self.thread_scheduler.start()
        self.thread_recalc.start()

    @property
    def df_exec(self):
        return self.obter_exec_df() if self.obter_exec_df else None

    def parar(self):
        self._stop = True

    def atualizar_planilhas(self):
        self._recalcular_agenda()

    def registrar_inicio_execucao(self, metodo):
        with self.lock:
            self._metodos_rodando.add(NormalizadorDF.norm_key(metodo))

    def registrar_fim_execucao(self, metodo):
        with self.lock:
            nk = NormalizadorDF.norm_key(metodo)
            if nk in self._metodos_rodando:
                self._metodos_rodando.remove(nk)
            self._ultimos_terminos[nk] = datetime.now(self.tz)

    def _normalizar_horarios(self, texto: str):
        if not texto: return []
        t = str(texto).strip().lower()
        if t in {"sem", "sob demanda", "sob_demanda"}: return []
        partes = re.split(r"[,\s;/]+", t)
        horarios = []
        for p in partes:
            p = p.strip()
            if re.fullmatch(r"\d{1,2}:\d{2}", p):
                try:
                    h, m = map(int, p.split(":"))
                    horarios.append(f"{h:02d}:{m:02d}")
                except: pass
        return sorted(list(set(horarios)))

    def _normalizar_dias_semana(self, texto: str):
        if not texto: return set(range(7))
        t = str(texto).strip().lower()
        if t in {"sem", "sob demanda"}: return set()
        res = set()
        partes = re.split(r"[,\s;/]+", t)
        for p in partes:
            p = p.strip()
            if p in Config.MAPA_DIAS_SEMANA: 
                res.add(Config.MAPA_DIAS_SEMANA[p])
        return res if res else set(range(7))

    def _calcular_proxima_execucao(self, horarios, dias_validos, base: datetime):
        if not horarios or not dias_validos: return None
        hoje = base.date()
        for soma in range(8):
            dia = hoje + timedelta(days=soma)
            if dia.weekday() not in dias_validos: continue
            for hhmm in horarios:
                try:
                    h, m = map(int, hhmm.split(":"))
                    dt = datetime(dia.year, dia.month, dia.day, h, m, 0, tzinfo=self.tz)
                    # FIX: Allow a small tolerance (1 min lookback) for tasks that *just* happened
                    # This handles the case where recalc runs at 08:00:01 and misses 08:00:00
                    if dt >= base - timedelta(minutes=1): 
                        return dt
                except: continue
        return None

    def _recalcular_agenda(self):
        try:
            agora = datetime.now(self.tz)
            mapeamento = self.obter_mapeamento() or {}
            proximas, status = {}, {}
            for met, info in ((m, i) for g in mapeamento.values() for m, i in g.items()):
                reg = info.get("registro") or {}
                if str(reg.get("status_automacao")).upper() != "ATIVA":
                    status[met] = "INATIVO"
                    continue
                hors = self._normalizar_horarios(reg.get("horario"))
                dias = self._normalizar_dias_semana(reg.get("dia_semana"))
                if not hors:
                    status[met] = "SEM_AGENDA"
                    continue
                dt = self._calcular_proxima_execucao(hors, dias, agora)
                proximas[met] = dt
                status[met] = "AGENDADO" if dt else "SEM_PROXIMA"
            with self.lock:
                self.proximas_execucoes = proximas
                self.status_agendamento = status
            
            # Log discreto apenas com totais para não spammar
            # self.logger.debug(f"Agenda recalculada: {len(proximas)} agendados.")
            pass
        except Exception:
            pass

    def _reset_diario(self, nova_data):
        self.data_ref = nova_data
        self._catchup_executado = False
        with self.lock:
             self._execucoes_gatilho_local.clear()
        self._recalcular_agenda()

    def _catchup_pendencias(self, agora: datetime):
        mapeamento = self.obter_mapeamento() or {}
        df_exec = self.obter_exec_df()
        
        # Converte df_exec para fácil consulta de contagem hoje
        contagem_hoje = {}
        if df_exec is not None and not df_exec.empty and "dt_full" in df_exec.columns:
            try:
                hoje = agora.date()
                df_hj = df_exec[df_exec["dt_full"].dt.date == hoje]
                if not df_hj.empty:
                    # Agrupa por método e conta
                    # Assumindo coluna 'metodo_automacao'
                    c_met = None
                    for c in df_hj.columns:
                        if c.lower() == "metodo_automacao":
                            c_met = c
                            break
                    if c_met:
                        cnt = df_hj[c_met].apply(NormalizadorDF.norm_key).value_counts()
                        contagem_hoje = cnt.to_dict()
            except Exception:
                pass

        for met, info in ((m, i) for g in mapeamento.values() for m, i in g.items()):
            path = info.get("path")
            reg = info.get("registro") or {}
            
            # 1. Verifica se ativo
            if str(reg.get("status_automacao")).upper() != "ATIVA": continue
            
            # 2. Verifica Dias da Semana
            dias = self._normalizar_dias_semana(reg.get("dia_semana"))
            if agora.weekday() not in dias: continue
            
            # 3. Calcula Slots Esperados até AGORA
            hors = self._normalizar_horarios(reg.get("horario"))
            slots_passados = []
            for hhmm in hors:
                try:
                    h, m = map(int, hhmm.split(":"))
                    dt_slot = datetime(agora.year, agora.month, agora.day, h, m, 0, tzinfo=self.tz)
                    if dt_slot <= agora: # Já deveria ter acontecido
                        # Considera apenas slots com mais de 5s de atraso (antes era 30s)
                        # Isso evita conflito com o scheduler normal, mas pega casos de lag de startup
                        if (agora - dt_slot).total_seconds() > 5:
                            slots_passados.append(dt_slot)
                except:
                    pass
            
            if not slots_passados:
                continue
                

            
            # 4. Verifica Execuções para CADA Slot Passado (Multi-Catchup)
            nk = NormalizadorDF.norm_key(met)
            
            # Filtra execuções deste método hoje no DF
            # Precisamos preparar df_hj aqui
            df_hj = pd.DataFrame()
            if self.df_exec is not None and not self.df_exec.empty and "dt_full" in self.df_exec.columns:
                try:
                    df_hj = self.df_exec[self.df_exec["dt_full"].dt.date == agora.date()].copy()
                except:
                    pass
            
            execs_hoje = []
            if not df_hj.empty and c_met and "dt_inicio" in df_hj.columns:
                 mask_met = df_hj[c_met].apply(NormalizadorDF.norm_key) == nk
                 df_m = df_hj[mask_met]
                 # Pega lista de tempos de execucao
                 if not df_m.empty:
                     # Converte coluna para datetime
                     try:
                         tempos = pd.to_datetime(df_m["dt_inicio"], errors='coerce')
                         # Filtra NaT
                         tempos = tempos.dropna()
                         # Localize/Convert TZ
                         if not tempos.empty:
                             # Se nao tiver tz, poe. Se tiver, converte.
                             # Simplificacao: assume que estao no fuso ou converte para naive para comparar
                             execs_hoje = [t.to_pydatetime() for t in tempos]
                     except: pass

            # Adiciona gatilhos da memoria local
            with self.lock:
                for (m_key, dt_ref) in self._execucoes_gatilho_local:
                    if m_key == nk and dt_ref.date() == agora.date():
                        execs_hoje.append(dt_ref.replace(tzinfo=None)) # Padroniza naive para comparação simples
            
            # Padroniza execs_hoje para ter timezone ou nao ter, igualando a slots
            # Vamos usar timestamps (float) para facilitar
            execs_ts = []
            for e in execs_hoje:
                if e.tzinfo: e = e.replace(tzinfo=None) # Ignora TZ para comparacao crua dia/hora
                execs_ts.append(e)

            # Para cada slot passado, verifica se houve execução "perto" (tolerancia)
            for slot in slots_passados:
                slot_naive = slot.replace(tzinfo=None)
                
                # Tolerancia: consideraremos executado se rodou entre (slot - 2h) e (slot + 12h)??
                # Nao, catchup é: se nao rodou DEPOIS do slot, roda.
                # Mas e se rodou 1 minuto antes? (ex: relogio adiantado). Dar 15 min de tolerancia antes.
                janela_inicio = slot_naive - timedelta(minutes=15)
                
                # Verifica se TEM alguma execucao valida para este slot
                executado = False
                for exec_time in execs_ts:
                    # Se rodou DEPOIS da janela de inicio deste slot, conta como execução deste slot (ou de um futuro).
                    # Problema: uma execucao as 10:00 conta pro slot das 08:00 e das 09:00?
                    # R: Sim, se eu rodei as 10:00, cobri tudo pra tras. O usuario quer catchup "inteligente" ou "executa N vezes"?
                    # O usuario disse: "se precisa rodar 3 vezes... esse metodo precisa rodar 3 vezees"
                    # ENTAO CADA SLOT PRECISA DE UMA EXECUÇÃO "DEDICADA"? 
                    # Se eu rodei UMA vez as 23:00, isso conta pelos slots das 18, 19 e 20? 
                    # Usuario disse: "precisa rodar 3 vezees". Entao não conta. Uma execução paga UM slot.
                    
                    # Logica de "Consumo de Slot":
                    # Ordenar slots e execuções. Casar 1 pra 1.
                    pass

                # Implementação Match Slots x Execuções
                # Ordena
                slots_passados.sort()
                execs_ts.sort()
                
                # Vamos contar quantos "créditos" de execução temos hoje
                # Se temos 3 slots passados e 1 execução, faltam 2.
                # Quais? Os mais antigos.
                
                # Mas precisamos respeitar horario. Uma execução as 09:00 não paga o slot das 10:00.
                
            # Refazendo logica simplificada de Contagem:
            # Slots Vencidos: S1, S2, S3 (ex: 18h, 19h, 20h). Agora 23h.
            # Execuções Hoje: E1 (ex: 18:05).
            # Saldo: E1 paga S1. Sobra S2 e S3.
            # Executar: S2. (Depois no proximo loop executa S3).
            
            # A execução paga o primeiro slot valido anterior a ela com tolerancia?
            
            slots_vencidos_pendentes = []
            copia_execs = list(sorted(execs_ts))
            
            for slot in sorted(slots_passados):
                slot_naive = slot.replace(tzinfo=None)
                janela_inicio = slot_naive - timedelta(minutes=15)
                
                # Procura a primeira execucao que satisfaca este slot
                match_idx = -1
                for i, ex in enumerate(copia_execs):
                    if ex >= janela_inicio:
                        # Achou uma execução que serve para este slot (foi feita junto ou depois)
                        match_idx = i
                        break
                
                if match_idx >= 0:
                    # Consome esta execução
                    copia_execs.pop(match_idx)
                else:
                    # Nenhuma execução disponivel para cobrir este slot
                    slots_vencidos_pendentes.append(slot)
            
            if not slots_vencidos_pendentes:
                continue

            # Pega o primeiro pendente (o mais antigo) para executar AGORA
            alvo_slot = slots_vencidos_pendentes[0]

            self.logger.info(
                f"CATCHUP_CHECK: {met} [slots_hoje={len(hors)}] [vencidos={len(slots_passados)}] "
                f"[execs_ok={len(execs_ts)}] -> PENDENTES: {[s.strftime('%H:%M') for s in slots_vencidos_pendentes]}"
            )

            # 5. Verifica se já está rodando
            with self.lock:
                if nk in self._metodos_rodando:
                    continue 
                ultimo_fim = self._ultimos_terminos.get(nk)
            
            # 6. Cooldown (Evita flood se tiver 10 slots atrasados, roda 1 por minuto)
            if ultimo_fim:
                if (agora - ultimo_fim).total_seconds() < 60:
                    continue
            
            # EXECUTA
            self.logger.warning(f"CATCHUP: {met} está atrasado para o slot {alvo_slot.strftime('%H:%M')}. Executando agora.")
            
            ctx = {
                "origem": "RECUPERACAO",
                "justificativa": f"Atrasado (Ref Slot {alvo_slot.strftime('%H:%M')})",
                "slot_ref": alvo_slot,
                "usuario": f"{getpass.getuser()}@c6bank.com"
            }
            
            with self.lock:
                self._metodos_rodando.add(nk)
                self._execucoes_gatilho_local.add((nk, agora))
                
            try:
                self.enfileirar_callback(met, path, ctx, agora)
            except:
                with self.lock:
                    self._metodos_rodando.discard(nk)

    def _disparar_vencidos(self):
        agora = datetime.now(self.tz)
        with self.lock: snapshot = dict(self.proximas_execucoes)
        if not snapshot:
            self._recalcular_agenda()
            return
        mapeamento = self.obter_mapeamento() or {}
        for metodo, dt_prox in snapshot.items():
            if not dt_prox or dt_prox > agora: continue
            path = None
            for g in mapeamento.values():
                if metodo in g: path = g[metodo]["path"]; break
            if path:
                ctx = {
                    "origem": "agendado",
                    "justificativa": "Pontual",
                    "slot_ref": dt_prox,
                    "usuario": f"{getpass.getuser()}@c6bank.com"
                }
                self.enfileirar_callback(metodo, path, ctx, dt_prox)
                with self.lock: 
                    self.proximas_execucoes[metodo] = None
                    nk = NormalizadorDF.norm_key(metodo)
                    self._execucoes_gatilho_local.add((nk, dt_prox))
                threading.Thread(target=self._recalcular_agenda, daemon=True).start()

    def _loop_scheduler(self):
        while not self._stop:
            try:
                agora = datetime.now(self.tz)
                if agora.date() != self.data_ref: self._reset_diario(agora.date())
                if agora.date() != self.data_ref: self._reset_diario(agora.date())
                
                # Verifica catchup ciclicamente (a cada loop)
                self._catchup_pendencias(agora)
                self._disparar_vencidos()
            except Exception:
                pass
            time.sleep(1)

    def _loop_recalc(self):
        while not self._stop:
            try: self._recalcular_agenda()
            except: pass
            for _ in range(60):
                if self._stop: break
                time.sleep(1)

    def get_proxima_exec_str(self, metodo):
        with self.lock: dt = self.proximas_execucoes.get(metodo)
        return dt.strftime("%d/%m/%Y %H:%M:%S") if dt else "-"

    def get_status_agendamento(self, metodo):
        with self.lock: return self.status_agendamento.get(metodo, "")

    def snapshot_agendamentos(self):
        with self.lock: return dict(self.proximas_execucoes)
