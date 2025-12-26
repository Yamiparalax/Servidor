import sys
import os
import logging
import random
import shutil
import getpass
import tempfile
from datetime import datetime, timedelta, date, time as dtime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Bibliotecas de Terceiros
try:
    import pandas as pd
    import pandas_gbq
    from google.cloud import bigquery
    import pythoncom
    from win32com.client import Dispatch
except ImportError:
    pass

# ==============================================================================
#                               MODULO 1: BAIXAR AUTOMACOES EXEC
# ==============================================================================

class ModuloBaixarAutomacoes:
    def __init__(self):
        # --- CONFIGURACOES GLOBAIS ---
        self.NOME_AUTOMACAO = "GERADOR_HISTORICO"
        self.NOME_SCRIPT = "GERADOR_HISTORICO" 
        self.PERCENTUAL_SUCESSO_GERAL = 0.95
        
        # DATA DE CORTE OBRIGATORIA
        self.DATA_INICIO_GERAL = datetime(2025, 8, 13)
        self.DATA_FIM_GERAL = datetime.now()
        
        # CONFIGURACOES BQ
        self.PROJETO = "datalab-pagamentos"
        self.DATASET_TABELA_REGISTRO = "ADMINISTRACAO_CELULA_PYTHON.registro_automacoes"
        self.PASTA_DESTINO_NOME = "automacoes_exec"
        
        # Configuração do Logger
        self.logger = logging.getLogger(self.NOME_SCRIPT)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
            sh = logging.StreamHandler(sys.stdout)
            sh.setFormatter(formatter)
            self.logger.addHandler(sh)

    class Execucao:
        def __init__(self, logger_inst):
            self.logger = logger_inst

        def is_servidor(self) -> bool:
            if len(sys.argv) > 1: return True
            if os.getenv("SERVIDOR_ORIGEM") or os.getenv("MODO_EXECUCAO"): return True
            return False

        def detectar(self) -> Dict[str, Any]:
            if self.is_servidor():
                return {"modo_execucao": "AUTO", "usuario": f"{getpass.getuser()}@c6bank.com", "is_server": "1"}
            return {"modo_execucao": "AUTO", "usuario": f"{getpass.getuser()}@c6bank.com", "is_server": "0"}

    class BigQueryService:
        def __init__(self, logger_inst, projeto, tabela):
            self.logger = logger_inst
            self.projeto = projeto
            self.tabela = tabela
            self._configurar_credenciais()

        def _configurar_credenciais(self):
            cred_dir = Path.home() / "AppData" / "Roaming" / "CELPY"
            if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and cred_dir.exists():
                jsons = list(cred_dir.glob("*.json"))
                if jsons:
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(jsons[0])

        def obter_regras(self) -> pd.DataFrame:
            # FIX: Ensure we fetch needed columns. Use status_automacao if status missing.
            # Assuming 'script_name' and 'area_name' exist in registro_automacoes based on user input.
            query = f"""
            SELECT 
                area_name,
                script_name,
                metodo_automacao,
                status_automacao as status,  
                dia_semana,
                horario,
                tempo_manual,
                data_lancamento
            FROM `{self.projeto}.{self.tabela}`
            WHERE status_automacao IN ('ATIVA', 'ISOLADA')
              AND metodo_automacao IS NOT NULL
            """
            self.logger.info(f"Executando query no BQ (via pandas_gbq REST): {query.strip()}")
            return pandas_gbq.read_gbq(
                query, 
                project_id=self.projeto, 
                use_bqstorage_api=False
            )

    class GeradorHistorico:
        def __init__(self, logger_inst, data_inicio, data_fim, pct_sucesso):
            self.logger = logger_inst
            self.DATA_INICIO_GERAL = data_inicio
            self.DATA_FIM_GERAL = data_fim
            self.PERCENTUAL_SUCESSO_GERAL = pct_sucesso
            
            self.dias_map = {
                "SEGUNDA": 0, "TERCA": 1, "QUARTA": 2, "QUINTA": 3, "SEXTA": 4, "SABADO": 5, "DOMINGO": 6, "TERÇA": 1,
            }
            
            # Novo Schema
            self.colunas_finais = [
                "script_name", "area_name", "start_time", "end_time", "duration_seconds",
                "status", "usuario", "modo_exec", "date"
            ]
            self.horas_usadas: Set[str] = set()

        def _converter_tempo_para_segundos(self, segundos: int) -> int:
            return int(segundos)

        def _gerar_duracao_fake(self, tempo_manual_str: str) -> int:
            try:
                val_str = str(tempo_manual_str).replace(",", ".")
                tempo_manual = float(val_str)
            except Exception:
                tempo_manual = 10.0

            segundos_manual = int(tempo_manual * 60)
            if segundos_manual <= 0:
                segundos_manual = 60

            min_sec = max(1, int(segundos_manual * 0.05))
            max_sec = max(min_sec + 5, int(segundos_manual * 0.40))

            return random.randint(min_sec, max_sec)

        def _gerar_hora_com_variacao(self, horario_base: str, variacao_min: int = -12, variacao_max: int = 18) -> str:
            try:
                partes = list(map(int, horario_base.split(":")))
                if len(partes) >= 2:
                    h, m = partes[0], partes[1]
                else:
                    return "00:00:00"

                data_base = datetime(2000, 1, 1, h, m)
                variacao = random.randint(variacao_min, variacao_max)
                nova_hora = data_base + timedelta(minutes=variacao)
                nova_hora = nova_hora + timedelta(seconds=random.randint(0, 59))

                return nova_hora.strftime("%H:%M:%S")
            except Exception:
                return "00:00:00"

        def _gerar_hora_random_tarde(self) -> str:
            h = random.randint(15, 17)  
            m = random.randint(0, 59)
            s = random.randint(0, 59)
            return f"{h:02d}:{m:02d}:{s:02d}"

        def _garantir_unicidade_hora(self, data_ref: datetime, hora_str: str) -> str:
            try:
                dt_base = datetime.strptime(hora_str, "%H:%M:%S")
            except:
                return hora_str

            tentativas = 0
            while tentativas < 100:
                h_str = dt_base.strftime("%H:%M:%S")
                chave_unica = f"{data_ref.strftime('%Y-%m-%d')} {h_str}"
                
                if chave_unica not in self.horas_usadas:
                    self.horas_usadas.add(chave_unica)
                    return h_str
                
                dt_base = dt_base + timedelta(seconds=1)
                tentativas += 1
            return dt_base.strftime("%H:%M:%S")

        def _distribuir_status_global(self, df: pd.DataFrame) -> pd.DataFrame:
            if df.empty:
                return df

            total = len(df)
            alvo_total_sucesso = int(round(total * self.PERCENTUAL_SUCESSO_GERAL))

            # Assumindo q temos 'date' ou 'start_time' pra extrair mes
            # start_time é datetime
            meses = df["start_time"].dt.strftime("%Y-%m")
            df = df.copy()
            df["__mes__"] = meses
            meses_unicos = sorted(df["__mes__"].unique())

            sucesso_por_mes: Dict[str, int] = {}
            restante_alvo = alvo_total_sucesso
            restante_linhas = total

            for idx, mes in enumerate(meses_unicos):
                idx_mes = df.index[df["__mes__"] == mes]
                n_mes = len(idx_mes)
                if idx == len(meses_unicos) - 1:
                    k_mes = max(0, min(restante_alvo, n_mes))
                else:
                    if restante_linhas <= 0:
                        k_mes = 0
                    else:
                        proporcao = n_mes / restante_linhas
                        k_mes = int(round(restante_alvo * proporcao))
                        k_mes = max(0, min(k_mes, n_mes))
                sucesso_por_mes[mes] = k_mes
                restante_alvo -= k_mes
                restante_linhas -= n_mes

            # Reset status handling
            # Se status já veio None, mantem
            
            for mes, k_sucesso in sucesso_por_mes.items():
                idx_mes = list(df.index[df["__mes__"] == mes])
                n_mes = len(idx_mes)
                if n_mes == 0: continue

                if k_sucesso >= n_mes:
                    df.loc[idx_mes, "status"] = "SUCESSO"
                    continue

                if k_sucesso > 0:
                    idx_sucesso = set(random.sample(idx_mes, k_sucesso))
                else:
                    idx_sucesso = set()

                for i in idx_mes:
                    if i in idx_sucesso:
                        df.at[i, "status"] = "SUCESSO"

            mask_nao_sucesso = df["status"].isna()
            n_nao_sucesso = mask_nao_sucesso.sum()
            if n_nao_sucesso > 0:
                tipos = ["FALHA", "NO_DATA", "PENDING"] # Adaptado ao gosto comum, ou manter original
                # Original: "FALHA", "PENDENTE", "SEM DADOS PARA PROCESSAR"
                # Novo schema pede status STRING, vou usar compatíveis com o servidor
                # Mas se o codigo antigo usava strings longas, melhor manter padrao BQ
                # BQ status: SUCCESS, ERROR, NO_DATA (segundo Servidor.py)
                tipos = ["ERROR", "NO_DATA"] 
                pesos = [0.4, 0.6]
                escolhidos = random.choices(tipos, weights=pesos, k=n_nao_sucesso)
                df.loc[mask_nao_sucesso, "status"] = escolhidos

            return df[self.colunas_finais]

        def gerar_dataframe(self, df_regras: pd.DataFrame) -> pd.DataFrame:
            lista_dados: List[Dict[str, Any]] = []
            agora = datetime.now()

            self.horas_usadas.clear()

            if self.DATA_FIM_GERAL < self.DATA_INICIO_GERAL:
                self.logger.error("Data Fim menor que Data Inicio")
                return pd.DataFrame()

            delta_dias = (self.DATA_FIM_GERAL - self.DATA_INICIO_GERAL).days

            self.logger.info(f"INICIO|periodo={self.DATA_INICIO_GERAL.date()}_ate_{self.DATA_FIM_GERAL.date()}")
            self.logger.info(f"INFO|regras_obtidas_bq={len(df_regras)}")

            df_regras = df_regras.copy()
            df_regras["dt_lanc_obj"] = pd.to_datetime(
                df_regras["data_lancamento"], format="%Y-%m-%d", errors="coerce"
            )
            mask_nat = df_regras["dt_lanc_obj"].isna()
            if mask_nat.any():
                df_regras.loc[mask_nat, "dt_lanc_obj"] = pd.to_datetime(
                    df_regras.loc[mask_nat, "data_lancamento"],
                    format="%d/%m/%Y",
                    errors="coerce",
                )

            limite_hora_solicitacao = datetime.strptime("18:07:23", "%H:%M:%S").time()
            limite_horaminima_solicitacao = datetime.strptime("09:08:32", "%H:%M:%S").time()

            for i in range(delta_dias + 1):
                data_atual = self.DATA_INICIO_GERAL + timedelta(days=i)
                data_atual_date = data_atual.date()
                
                if i % 10 == 0:
                    self.logger.info(f"PROCESSANDO|dia={i}/{delta_dias}|data={data_atual_date}")

                dia_semana_int = data_atual.weekday()
                
                eh_hoje = (data_atual_date == agora.date())

                for _, row in df_regras.iterrows():
                    dt_lanc = row["dt_lanc_obj"]
                    if pd.notna(dt_lanc) and data_atual < dt_lanc:
                        continue
                    
                    # Usa script_name e area_name do BQ
                    script_name = str(row["script_name"]).strip()
                    area_name = str(row["area_name"]).strip()
                    nome_metodo = str(row["metodo_automacao"]).upper().strip()

                    horarios_do_dia: List[str] = []
                    usuario_exec_padrao = "CARLOS.LSILVA@C6BANK.COM"  
                    override_tempo_exec = False 

                    # Lógica de negócio mantida
                    if nome_metodo == "GERARQUEBRA":
                        if random.random() < 0.65:
                            horarios_do_dia = [self._gerar_hora_random_tarde()]
                            usuario_exec_padrao = "LARA.COSTA@C6BANK.COM" 
                            modo_exec = "SOLICITACAO"
                            override_tempo_exec = True
                        else:
                            continue

                    elif nome_metodo == "RESPOSTADOSCTVM":
                        horarios_do_dia = ["07:00", "19:00"]

                    elif nome_metodo == "RESPOSTADADOS":
                        horarios_do_dia = ["08:00", "20:00"]

                    else:
                        dias_config = str(row["dia_semana"]).upper()
                        horarios_config = str(row["horario"]).upper()

                        if "SOB DEMANDA" in dias_config or "SOB DEMANDA" in horarios_config:
                            continue

                        deve_rodar_hoje = False
                        for nome_dia, valor_int in self.dias_map.items():
                            if nome_dia in dias_config and valor_int == dia_semana_int:
                                deve_rodar_hoje = True
                                break

                        if not deve_rodar_hoje:
                            continue

                        horarios_do_dia = [
                            h.strip() for h in horarios_config.split(",") if h.strip()
                        ]
                        if not horarios_do_dia:
                            horarios_do_dia = ["08:00"]

                    # --- GERACAO DAS LINHAS ---
                    for horario_base in horarios_do_dia:
                        if nome_metodo == "GERARQUEBRA":
                            modo_exec = "SOLICITACAO"
                            usuario_exec = "LARA.COSTA@C6BANK.COM"
                        else:
                            modo_exec = "AUTO"
                            usuario_exec = usuario_exec_padrao

                        if nome_metodo in ["MENSAGARIA2PADRONIZADA", "ENCERRARCASOS"]:
                            if random.random() < 0.25:
                                modo_exec = "SOLICITACAO"
                                usuario_exec = random.choice(
                                    ["fabio.gedra@c6bank.com", "joao.vitoras@c6bank.com"]
                                )

                        hora_exec_str = self._gerar_hora_com_variacao(horario_base)
                        try:
                            hora_obj = datetime.strptime(hora_exec_str, "%H:%M:%S").time()
                        except:
                            continue

                        dt_exec = datetime.combine(data_atual_date, hora_obj)
                        
                        if eh_hoje:
                            if dt_exec > agora:
                                continue

                        if modo_exec == "SOLICITACAO":
                            if hora_obj < limite_horaminima_solicitacao or hora_obj > limite_hora_solicitacao:
                                modo_exec = "AUTO"
                                usuario_exec = "CARLOS.LSILVA@C6BANK.COM"

                        hora_exec_str = self._garantir_unicidade_hora(data_atual, hora_exec_str)
                        # Re-calculate dt_exec based on unique hour? No, just keep it roughly same
                        
                        # Duration
                        if override_tempo_exec:
                            dur_sec = random.randint(60, 580)
                        else:
                            dur_sec = self._gerar_duracao_fake(str(row["tempo_manual"]))
                        
                        dt_end = dt_exec + timedelta(seconds=dur_sec)

                        linha = {
                            "script_name": script_name,
                            "area_name": area_name,
                            "start_time": dt_exec,
                            "end_time": dt_end,
                            "duration_seconds": float(dur_sec),
                            "status": None, # Will be filled later
                            "usuario": usuario_exec,
                            "modo_exec": modo_exec,
                            "date": data_atual_date
                        }
                        lista_dados.append(linha)

            df = pd.DataFrame(lista_dados, columns=self.colunas_finais)
            if df.empty:
                return df

            df_resultado = self._distribuir_status_global(df)
            return df_resultado

    def executar(self):
        self.logger.info("=== INICIANDO: BAIXAR AUTOMACOES EXEC ===")
        
        execucao = self.Execucao(self.logger)
        _ = execucao.detectar()

        try:
            pasta_downloads = Path.home() / "Downloads"
            pasta_alvo = pasta_downloads / self.PASTA_DESTINO_NOME
            
            if pasta_alvo.exists():
                try:
                    shutil.rmtree(pasta_alvo)
                    self.logger.info(f"INFO|pasta_limpa_deletada={pasta_alvo}")
                except Exception as e:
                    self.logger.warning(f"AVISO|erro_ao_limpar_pasta={e}")

            pasta_alvo.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"INICIO|pasta_alvo={pasta_alvo}")

            bq_service = self.BigQueryService(self.logger, self.PROJETO, self.DATASET_TABELA_REGISTRO)
            df_regras = bq_service.obter_regras()
            
            if df_regras.empty:
                self.logger.warning("ATENCAO|nenhuma_regra_encontrada_bq")
                return

            gerador = self.GeradorHistorico(self.logger, self.DATA_INICIO_GERAL, self.DATA_FIM_GERAL, self.PERCENTUAL_SUCESSO_GERAL)
            df = gerador.gerar_dataframe(df_regras)

            if df.empty:
                self.logger.warning("ATENCAO|nenhum_dado_gerado|verifique_filtro_datas")
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"automacoes_exec_{timestamp}.xlsx"
            caminho_final = pasta_alvo / nome_arquivo

            self.logger.info(f"INFO|salvando_excel|linhas={len(df)}")
            # Datetime objects save well in Excel
            df.to_excel(caminho_final, index=False)
            
            self.logger.info(f"SUCESSO|arquivo={caminho_final}")
            
            if sys.platform == "win32":
                os.startfile(pasta_alvo)

        except Exception:
            self.logger.exception("ERRO|fatal_main")


# ==============================================================================
#                               MODULO 2: SUBIR AUTOMACOES EXEC
# ==============================================================================

class ModuloSubirAutomacoes:
    def __init__(self):
        self.BQ_PROJECT = "datalab-pagamentos"
        self.BQ_DATASET = "ADMINISTRACAO_CELULA_PYTHON"
        self.BQ_TABLE = "automacoes_exec"
        self.TABLE_FQ = f"{self.BQ_PROJECT}.{self.BQ_DATASET}.{self.BQ_TABLE}"
        self.OUTLOOK_DESTINATARIOS = "carlos.lsilva@c6bank.com"
        self.MODO_SUBIDA_BQ = os.getenv("MODO_SUBIDA_BQ", "replace").lower()
        
        # Novo schema esperado
        self.EXPECTED_COLS = [
            "script_name", "area_name", "start_time", "end_time", 
            "duration_seconds", "status", "usuario", "modo_exec", "date"
        ]

    def _setup_logger(self) -> Tuple[logging.Logger, Path]:
        nome_script = "SUBIR_AUTOMACOES"
        data_dir = datetime.now().strftime("%d.%m.%Y")
        log_dir = Path.home()/"graciliano"/"automacoes"/"cacatua"/"logs_celula_python"/nome_script.lower()/data_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir/f"{nome_script}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logger = logging.getLogger(nome_script)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        
        # Limpar handlers anteriores para evitar duplicação
        if logger.hasHandlers(): logger.handlers.clear()
        
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.handlers = [ch, fh]
        return logger, log_path

    def garantir_outlook_aberto(self) -> bool:
        try: pythoncom.CoInitialize()
        except: pass
        try:
            Dispatch("Outlook.Application")
            return True
        except: return False

    def procurar_arquivos(self, logger: logging.Logger) -> Optional[Path]:
        pasta = Path.home()/"Downloads"/"automacoes_exec"
        if not pasta.exists():
            logger.info(f"Pasta não existe: {pasta}")
            return None
        candidatos = sorted(pasta.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
        for arq in candidatos:
            try:
                # Ler headers primeiro
                df_head = pd.read_excel(arq, nrows=0)
                # Verifica se contem as colunas (pode ter mais, mas deve ter as required)
                # Na verdade, como geramos exatamente, deve bater
                if all(c in df_head.columns for c in self.EXPECTED_COLS):
                    logger.info(f"Arquivo válido: {arq.name}")
                    return arq
            except Exception as e:
                logger.warning(f"Erro ao ler {arq.name}: {e}")
        return None

    def tratar_dataframe(self, caminho: Path, logger: logging.Logger) -> pd.DataFrame:
        df = pd.read_excel(caminho)
        df = df[self.EXPECTED_COLS].copy()
        
        # Coerção
        df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
        df["end_time"] = pd.to_datetime(df["end_time"], errors="coerce")
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        df["duration_seconds"] = pd.to_numeric(df["duration_seconds"], errors="coerce")
        
        # Clean strings
        for c in ["script_name", "area_name", "status", "usuario", "modo_exec"]:
            df[c] = df[c].astype(str).replace({"nan": None, "NaT": None, "None": None})
            
        logger.info(f"DataFrame pronto: {len(df)} linhas")
        return df

    def subir_bq(self, df: pd.DataFrame, logger: logging.Logger) -> int:
        client = bigquery.Client(project=self.BQ_PROJECT)
        
        # Schema BQ Definition
        schema = [
            bigquery.SchemaField("script_name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("area_name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("start_time", "DATETIME", mode="NULLABLE"),
            bigquery.SchemaField("end_time", "DATETIME", mode="NULLABLE"),
            bigquery.SchemaField("duration_seconds", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("status", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("usuario", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("modo_exec", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("date", "DATE", mode="NULLABLE"),
        ]
        
        disp = bigquery.WriteDisposition.WRITE_TRUNCATE if self.MODO_SUBIDA_BQ == "replace" else bigquery.WriteDisposition.WRITE_APPEND
        job = client.load_table_from_dataframe(
            df, 
            self.TABLE_FQ, 
            job_config=bigquery.LoadJobConfig(write_disposition=disp, schema=schema)
        )
        job.result()
        linhas = int(getattr(job, "output_rows", 0) or 0)
        logger.info(f"Subida BQ ({self.MODO_SUBIDA_BQ}): {linhas} linhas")
        return linhas

    def enviar_email(self, logger: logging.Logger, retcode: int, log_path: Path) -> bool:
        if not self.garantir_outlook_aberto(): return False
        status = "SUCESSO" if retcode == 0 else ("NÃO HAVIA ARQUIVOS" if retcode == 2 else "FALHA")
        assunto = f"Célula Python - SUBIR AUTOMACOES - {status} - {datetime.now():%d/%m/%Y %H:%M}"
        corpo = f"<html><body><h3>Status: {status}</h3><p>Tabela: {self.TABLE_FQ}</p><p>Log em anexo.</p></body></html>"
        try:
            app = Dispatch("Outlook.Application")
            mail = app.CreateItem(0)
            mail.To = self.OUTLOOK_DESTINATARIOS
            mail.Subject = assunto
            mail.HTMLBody = corpo
            if log_path.exists(): mail.Attachments.Add(str(log_path))
            mail.Send()
            logger.info("E-mail enviado.")
            try: pythoncom.CoUninitialize()
            except: pass
            return True
        except Exception as e:
            logger.warning(f"Erro ao enviar email: {e}")
            try: pythoncom.CoUninitialize()
            except: pass
            return False

    def executar(self):
        logger, log_path = self._setup_logger()
        retcode = 1
        try:
            logger.info("=== INICIANDO: SUBIR AUTOMACOES EXEC ===")
            arquivo = self.procurar_arquivos(logger)
            if not arquivo:
                logger.info("Sem arquivos válidos.")
                retcode = 2
            else:
                df = self.tratar_dataframe(arquivo, logger)
                if len(df) == 0: retcode = 2
                else:
                    self.subir_bq(df, logger)
                    retcode = 0
        except Exception as e:
            logger.exception(f"Erro fatal: {e}")
            retcode = 1
        finally:
            self.enviar_email(logger, retcode, log_path)

# ==============================================================================
#                               INTERFACE UNIFICADA
# ==============================================================================

def main():
    while True:
        print("\n" + "="*40)
        print("      GERENCIADOR DE AUTOMACOES")
        print("="*40)
        print("1 - BAIXAR AUTOMACOES EXEC")
        print("2 - SUBIR AUTOMACOES EXEC")
        print("0 - SAIR")
        print("="*40)
        
        opcao = input("Escolha uma opção: ").strip()
        
        if opcao == "1":
            ModuloBaixarAutomacoes().executar()
        elif opcao == "2":
            ModuloSubirAutomacoes().executar()
        elif opcao == "0":
            print("Saindo...")
            break
        else:
            print("Opção inválida!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário.")
