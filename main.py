import sys
import time
import gc
import logging
import threading
from PySide6.QtWidgets import QApplication

from servidor.config import Config
from servidor.core import (
    ConfiguradorLogger,
    QtLogHandler,
    StdoutRedirector,
    ClienteBigQuery,
    NotificadorEmail,
    DescobridorMetodos,
)
from servidor.monitor import MonitorSolicitacoes, MonitorRecursos
from servidor.scheduler import SincronizadorPlanilhas, AgendadorMetodos
from servidor.executor import ExecutorMetodos
from servidor.gui.main_window import JanelaServidor

def main():
    # 1. Logger
    logger, log_path, fmt = ConfiguradorLogger.criar_logger()
    logger.info("=== SERVIDOR INICIADO (Refatorado) ===")
    logger.info(f"Versão Python: {sys.version}")
    logger.info(f"Log em: {log_path}")

    # 2. Configurações Iniciais
    Config.DIR_SERVIDOR.mkdir(parents=True, exist_ok=True)
    Config.DIR_LOGS_BASE.mkdir(parents=True, exist_ok=True)
    Config.DIR_CRED_CELPY.mkdir(parents=True, exist_ok=True)

    # 3. Componentes Core
    cliente_bq = ClienteBigQuery(logger, modo="servidor")
    notificador = NotificadorEmail(logger)
    descobridor = DescobridorMetodos(logger)

    # 4. Executor
    executor = ExecutorMetodos(logger, Config.MAX_CONCURRENCY)

    # 5. Callbacks
    def cb_resolver(metodo):
        # Retorna (nome_normalizado, path)
        mapeamento = descobridor._scan_metodos() # Scan direto ou cache?
        # O ideal seria o descobridor ter um cache ou o agendador passar isso.
        # Por simplificação, vamos fazer um scan rápido ou usar o mapeamento da janela se possível.
        # Mas aqui estamos no monitor de solicitações, que roda em thread separada.
        # Vamos usar o scan direto por enquanto.
        from servidor.core import NormalizadorDF
        chave = NormalizadorDF.norm_key(metodo)
        if chave in mapeamento:
            return mapeamento[chave]["norm_key"], mapeamento[chave]["path"]
        return None, None

    def cb_permissao(metodo, usuario):
        return True # Por enquanto tudo permitido

    def cb_enfileirar(metodo, caminho, contexto, quando):
        executor.enfileirar(metodo, caminho, contexto, quando)

    # 6. Monitores
    monitor_solicitacoes = MonitorSolicitacoes(
        logger,
        Config.DIR_SOLICITACOES,
        cb_resolver,
        cb_permissao,
        cb_enfileirar,
        Config.DIR_HISTORICO_SOLICITACOES,
        notificador,
    )

    # 7. Sincronizador e Agendador
    # Cache global compartilhado (simulado via variaveis)
    cache_global = {"df_exec": None, "df_reg": None}
    janela_holder = {"janela": None}

    def cb_atualizacao_dados(df_exec, df_reg):
        cache_global["df_exec"] = df_exec
        cache_global["df_reg"] = df_reg
        if janela_holder["janela"]:
            janela_holder["janela"].atualizar_mapeamento_threadsafe(df_exec, df_reg)

    sincronizador = SincronizadorPlanilhas(
        logger,
        cliente_bq,
        intervalo_segundos=600,
        callback_atualizacao=cb_atualizacao_dados
    )

    def obter_mapeamento_agendador():
        if janela_holder["janela"]:
            return janela_holder["janela"].mapeamento
        return {}

    def obter_exec_df_agendador():
        return cache_global["df_exec"]

    agendador = AgendadorMetodos(
        logger,
        obter_mapeamento_agendador,
        obter_exec_df_agendador,
        cb_enfileirar,
    )

    # Callbacks do Executor para atualizar GUI e Agendador
    def cb_exec_inicio(metodo, ctx, inicio):
        logger.info(f"EXEC_INICIO: {metodo}")
        if janela_holder["janela"]:
            janela_holder["janela"].marcar_metodo_ocupado(metodo, True)

    def cb_exec_fim(metodo, ctx, rc, log_filho):
        logger.info(f"EXEC_FIM: {metodo} rc={rc}")
        if janela_holder["janela"]:
            janela_holder["janela"].marcar_metodo_ocupado(metodo, False)
        # Registrar execução imediata no sincronizador para evitar re-execução
        sincronizador.registrar_execucao_imediata(metodo)
        # Forçar sync para atualizar status na planilha (opcional, pode ser pesado)
        # sincronizador.forcar_atualizacao() 

    executor.callback_exec_inicio = cb_exec_inicio
    executor.callback_exec_fim = cb_exec_fim

    # 8. Headless Check
    if Config.HEADLESS:
        logger.info("Modo HEADLESS ativo. Sem GUI.")
        sincronizador.iniciar_monitoramento()
        try:
            while True:
                time.sleep(5)
                gc.collect()
        except KeyboardInterrupt:
            return 0

    # 9. GUI Setup
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion") # Garante estilo consistente

    # Redirecionar stdout/stderr para log panel
    def emit_log_gui(msg):
        if janela_holder["janela"]:
            janela_holder["janela"].sig_log.emit(msg)

    qt_handler = QtLogHandler(emit_log_gui)
    qt_handler.setFormatter(fmt)
    logger.addHandler(qt_handler)
    
    sys.stdout = StdoutRedirector(logger, logging.INFO)
    sys.stderr = StdoutRedirector(logger, logging.ERROR)

    monitor_recursos = MonitorRecursos(logger)
    
    # Ja rodou hoje callback
    def ja_rodou(metodo):
        return sincronizador.ja_executou_hoje(metodo)

    janela = JanelaServidor(
        logger,
        executor,
        descobridor,
        sincronizador,
        monitor_recursos,
        lambda m: agendador.get_proxima_exec_str(m),
        lambda m: agendador.get_status_agendamento(m),
        ja_rodou
    )
    janela_holder["janela"] = janela
    janela.agendador = agendador

    # Iniciar threads
    sincronizador.iniciar_monitoramento()
    
    # Loop inicial para pegar dados (bloqueante ou não? melhor não travar a GUI)
    # Vamos deixar o sincronizador rodar em background e atualizar a GUI quando der.
    # Mas para a primeira vez, se for offline, é instantaneo.
    if Config.SERVIDOR_OFFLINE:
        sincronizador.sincronizar_de_arquivos()
    else:
        # Tenta um sync rápido sem bloquear muito
        t = threading.Thread(target=sincronizador.sincronizar_de_arquivos, daemon=True)
        t.start()

    janela.show()
    
    # Monitor de recursos start
    monitor_recursos.start()

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
