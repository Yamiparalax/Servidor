import logging
import sys
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import uvicorn

from backend.config import Config
from backend.core import ConfiguradorLogger, ClienteBigQuery, NotificadorEmail, DescobridorMetodos, BloqueadorSuspensao
from backend.logic.scheduler import SincronizadorPlanilhas, AgendadorMetodos
from backend.logic.executor import ExecutorMetodos
from backend.logic.monitor import MonitorSolicitacoes

# Globals
logger = logging.getLogger(Config.NOME_SCRIPT)
executor = None
sincronizador = None
agendador = None
monitor_solicitacoes = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global logger, executor, sincronizador, agendador, monitor_solicitacoes
    
    logger, log_path, fmt = ConfiguradorLogger.criar_logger()
    logger.info("=== SERVIDOR WEB INICIADO ===")
    
    if BloqueadorSuspensao.manter_acordado():
        logger.info("Bloqueio de suspensão ativo.")

    cliente_bq = ClienteBigQuery(logger, modo="servidor")
    notificador = NotificadorEmail(logger)
    descobridor = DescobridorMetodos(logger)
    executor = ExecutorMetodos(logger, Config.MAX_CONCURRENCY)

    # Callbacks
    def cb_resolver(metodo):
        mapeamento = descobridor._scan_metodos()
        from backend.core import NormalizadorDF
        chave = NormalizadorDF.norm_key(metodo)
        if chave in mapeamento:
            return mapeamento[chave]["norm_key"], mapeamento[chave]["path"]
        return None, None

    def cb_permissao(metodo, usuario): return True
    def cb_enfileirar(metodo, caminho, ctx, quando): executor.enfileirar(metodo, caminho, ctx, quando)

    monitor_solicitacoes = MonitorSolicitacoes(
        logger, Config.DIR_SOLICITACOES, cb_resolver, cb_permissao, cb_enfileirar,
        Config.DIR_HISTORICO_SOLICITACOES, notificador
    )

    sincronizador = SincronizadorPlanilhas(logger, cliente_bq, intervalo_segundos=600)
    
    # Agendador needs access to dynamic mapping which comes from sync callbacks
    # In web app, we can store mapping in a singleton or access directly from sync
    # For now, simplistic approach:
    global _mapeamento_cache, _df_exec_cache
    _mapeamento_cache = {}
    _df_exec_cache = None

    def cb_atualizacao(df_exec, df_reg):
        global _mapeamento_cache, _df_exec_cache
        _df_exec_cache = df_exec
        _mapeamento_cache = descobridor.mapear_por_registro(df_reg)
    
    sincronizador.callback_atualizacao = cb_atualizacao
    sincronizador.iniciar_monitoramento()

    agendador = AgendadorMetodos(
        logger,
        lambda: _mapeamento_cache,
        lambda: _df_exec_cache,
        cb_enfileirar
    )
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    if executor: executor.parar_todos_processos()
    if sincronizador: sincronizador.parar()
    if agendador: agendador.parar()

app = FastAPI(lifespan=lifespan)

# Static Files
# Assuming run from 'servidor_html' root
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

@app.get("/")
async def read_root():
    return FileResponse("frontend/index.html")

@app.get("/api/status")
async def get_status():
    return {
        "status": "online", 
        "time": datetime.now(Config.TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "active_threads": threading.active_count()
    }

@app.get("/api/dashboard")
async def get_dashboard():
    # Coleta snapshot de execução
    em_execucao = executor.snapshot_execucao() if executor else {}
    
    # Coleta status do agendador
    snapshot_agenda = agendador.snapshot_agendamentos() if agendador else {}
    
    # Processa histórico recente
    global _df_exec_cache, _mapeamento_cache
    historico = {"sucesso": [], "falha": []}
    
    if _df_exec_cache is not None and not _df_exec_cache.empty and "dt_full" in _df_exec_cache.columns:
        try:
            hoje = datetime.now(Config.TZ).date()
            df_hoje = _df_exec_cache[_df_exec_cache["dt_full"].dt.date == hoje].copy()
            if not df_hoje.empty:
                df_hoje.sort_values("dt_full", ascending=False, inplace=True)
                for _, row in df_hoje.iterrows():
                    s = str(row.get("status", "")).upper()
                    item = {
                        "metodo": str(row.get("metodo_automacao", "")),
                        "hora": str(row.get("hora_exec", "")),
                        "status": s
                    }
                    if "SUCESSO" in s:
                        historico["sucesso"].append(item)
                    else:
                        historico["falha"].append(item)
        except Exception as e:
            logger.error(f"dashboard_history_error: {e}")

    # Lista de rodando
    rodando = []
    for met, info in em_execucao.items():
        ctx = info.get("contexto", {})
        rodando.append({
            "metodo": met,
            "inicio": info.get("inicio").strftime("%H:%M:%S") if info.get("inicio") else "-",
            "usuario": ctx.get("usuario", "-"),
            "origem": ctx.get("origem", "-"),
            "pid": info.get("pid")
        })

    return {
        "mapeamento": _mapeamento_cache,
        "rodando": rodando,
        "historico": historico,
        "offline": Config.SERVIDOR_OFFLINE
    }

@app.post("/api/stop/{metodo}")
async def stop_method(metodo: str):
    logger.info(f"API Solicitacao Stop: {metodo}")
    if executor:
        success = executor.parar_processo(metodo)
        if success:
            return {"status": "stopped", "metodo": metodo}
    raise HTTPException(status_code=400, detail="Falha ao parar processo ou processo não encontrado")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
