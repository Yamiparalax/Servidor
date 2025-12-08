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
    BloqueadorSuspensao,
)
from servidor.monitor import MonitorSolicitacoes, MonitorRecursos
from servidor.scheduler import SincronizadorPlanilhas, AgendadorMetodos
from servidor.executor import ExecutorMetodos
from servidor.gui.main_window import JanelaServidor

def main():
    # Inicia logger
    logger, log_path, fmt = ConfiguradorLogger.criar_logger()
    logger.info("=== SERVIDOR INICIADO (Refatorado) ===")
    logger.info(f"Versão Python: {sys.version}")
    logger.info(f"Log em: {log_path}")

    # Bloqueio de suspensão (Tela/Sistema)
    if BloqueadorSuspensao.manter_acordado():
        logger.info("Sistema configurado para não suspender/bloquear tela (Always On).")
    else:
        logger.warning("Falha ao configurar bloqueio de suspensão.")

    # Configurações iniciais
    Config.DIR_SERVIDOR.mkdir(parents=True, exist_ok=True)
    Config.DIR_LOGS_BASE.mkdir(parents=True, exist_ok=True)
    Config.DIR_CRED_CELPY.mkdir(parents=True, exist_ok=True)

    # Componentes principais
    cliente_bq = ClienteBigQuery(logger, modo="servidor")
    notificador = NotificadorEmail(logger)
    descobridor = DescobridorMetodos(logger)

    # Executor de métodos
    executor = ExecutorMetodos(logger, Config.MAX_CONCURRENCY)

    # Callbacks do sistema
    def cb_resolver(metodo):
        # Resolve caminho do método
        mapeamento = descobridor._scan_metodos()
        
        from servidor.core import NormalizadorDF
        chave = NormalizadorDF.norm_key(metodo)
        if chave in mapeamento:
            return mapeamento[chave]["norm_key"], mapeamento[chave]["path"]
        return None, None

    def cb_permissao(metodo, usuario):
        return True

    def cb_enfileirar(metodo, caminho, contexto, quando):
        executor.enfileirar(metodo, caminho, contexto, quando)

    # Inicia monitores
    monitor_solicitacoes = MonitorSolicitacoes(
        logger,
        Config.DIR_SOLICITACOES,
        cb_resolver,
        cb_permissao,
        cb_enfileirar,
        Config.DIR_HISTORICO_SOLICITACOES,
        notificador,
    )

    # Sincronizador e agendador
    # Cache global compartilhado
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

    # Callbacks para atualizar interface e agendador
    def cb_exec_inicio(metodo, ctx, inicio):
        logger.info(f"EXEC_INICIO: {metodo}")
        if janela_holder["janela"]:
            janela_holder["janela"].marcar_metodo_ocupado(metodo, True)

    def cb_exec_fim(metodo, ctx, rc, log_filho):
        logger.info(f"EXEC_FIM: {metodo} rc={rc}")
        if janela_holder["janela"]:
            janela_holder["janela"].marcar_metodo_ocupado(metodo, False)
        # Registra execução imediata e pode forçar sincronização se necessário 

    executor.callback_exec_inicio = cb_exec_inicio
    executor.callback_exec_fim = cb_exec_fim

    # Verifica modo headless
    if Config.HEADLESS:
        logger.info("Modo HEADLESS ativo. Sem GUI.")
        sincronizador.iniciar_monitoramento()
        try:
            while True:
                time.sleep(5)
                gc.collect()
        except KeyboardInterrupt:
            return 0

    # Configuração da interface
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion") 

    # Redireciona logs para painel na interface
    def emit_log_gui(msg):
        if janela_holder["janela"]:
            janela_holder["janela"].sig_log.emit(msg)

    qt_handler = QtLogHandler(emit_log_gui)
    qt_handler.setFormatter(fmt)
    logger.addHandler(qt_handler)
    
    sys.stdout = StdoutRedirector(logger, logging.INFO)
    sys.stderr = StdoutRedirector(logger, logging.ERROR)

    monitor_recursos = MonitorRecursos(logger)
    
    # Verifica se já executou hoje
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

    # Inicia threads
    sincronizador.iniciar_monitoramento()
    
    # Sincroniza dados iniciais
    if Config.SERVIDOR_OFFLINE:
        sincronizador.sincronizar_de_arquivos()
    else:
        # Tenta sincronização rápida em background
        t = threading.Thread(target=sincronizador.sincronizar_de_arquivos, daemon=True)
        t.start()

    janela.show()
    
    # Inicia monitor de recursos
    monitor_recursos.start()

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
