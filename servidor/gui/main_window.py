import getpass
import traceback
import psutil
import pandas as pd
from datetime import datetime
from functools import partial

from PySide6.QtCore import Qt, Signal, Slot, QTimer, QSize
from PySide6.QtGui import QIcon, QAction, QTextCursor
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QProgressBar,
    QSystemTrayIcon,
    QMenu,
    QLineEdit,
    QStackedWidget,
    QCheckBox,
    QApplication,
)

from servidor.config import Config
from servidor.core import NormalizadorDF
from servidor.gui.styles import EstilosGUI
from servidor.gui.components import (
    AutomationCard,
    DashboardBox,
    LogDialog,
    smart_update_listwidget,
)
# from servidor.gui.widgets_extras import WeatherDialog, CurrencyDialog, CurrencyPage, WeatherWidget (REMOVIDO)

class JanelaServidor(QMainWindow):
    sig_atualizar_dados = Signal(object, object)
    sig_marcar_ocupado = Signal(str, bool)
    sig_log = Signal(str)

    def __init__(
        self,
        logger,
        executor,
        descobridor,
        sincronizador,
        monitor_solicitacoes,
        get_proxima_exec_str_callback=None,
        get_status_agendamento_callback=None,
        verificar_execucao_hoje=None,
    ):
        super().__init__()
        self.logger = logger
        self.executor = executor
        self.descobridor = descobridor
        self.sincronizador = sincronizador
        self.monitor_solicitacoes = monitor_solicitacoes
        self.get_prox_exec = get_proxima_exec_str_callback
        self.get_status_agendamento = get_status_agendamento_callback
        self.verificar_execucao_hoje = verificar_execucao_hoje

        self.mapeamento = {}
        self.df_exec = pd.DataFrame()
        self.df_reg = pd.DataFrame()
        self.cards = {}
        self.infos = {}
        self.dashboard_boxes = {}
        self.agendador = None

        self.log_painel = None
        self.btn_parar_rodando = None
        self.chk_auto_sync = None
        self.log_painel = None
        self.btn_parar_rodando = None
        self.chk_auto_sync = None
        # self.input_busca = None # REMOVIDO
        self.nav_list = None
        self.stack = None
        self.navegacao_indices = {}
        self.card_secao = {}
        # self._busca_texto = "" # REMOVIDO
        # self._busca_ativa = False # REMOVIDO
        # self._tab_antes_busca = None # REMOVIDO
        
        # Controle de Virada de Dia (Midnight Reset)
        self.data_atual_gui = datetime.now(Config.TZ).date()

        self._ultima_atualizacao_planilhas = None
        self._proxima_atualizacao_planilhas = None

        self._resumo_sucesso = []
        self._resumo_falhas = []
        self._resumo_outros = []

        self.tray_icon = None
        self.setWindowTitle("SERVIDOR DE AUTOMAÇÕES - C6")
        self.resize(1400, 900)
        self.showMaximized()

        self._ps_cache = {}
        self._ps_cpu_init = set()

        self._setup_ui()
        self._setup_tray_icon()

        self.sig_atualizar_dados.connect(self.atualizar_dados)
        self.sig_marcar_ocupado.connect(self._slot_marcar_ocupado)
        self.sig_log.connect(self._append_log)

        try:
            self.monitor_solicitacoes.sinal_msg.connect(self._append_log)
        except Exception:
            pass

        self.timer_gui = QTimer(self)
        self.timer_gui.timeout.connect(self._tick_gui)
        self.timer_gui.start(1000)

    def _setup_tray_icon(self):
        try:
            if not QSystemTrayIcon.isSystemTrayAvailable():
                return
        except Exception:
            return

        try:
            self.tray_icon = QSystemTrayIcon(self)
            icon = self.windowIcon()
            # If window icon is null, use a standard icon from style or empty
            if not icon or icon.isNull():
                # Tenta usar um icone padrao do sistema ou criar um pixmap colorido
                icon = self.style().standardIcon(self.style().SP_ComputerIcon)
            self.tray_icon.setIcon(icon)
            self.tray_icon.setToolTip("Servidor Automacoes")

            menu = QMenu()
            act_show = QAction("Restaurar", self)
            act_quit = QAction("Sair", self)
            act_show.triggered.connect(self._from_tray_show)
            act_quit.triggered.connect(self._sair_definitivo)
            menu.addAction(act_show)
            menu.addAction(act_quit)

            self.tray_icon.setContextMenu(menu)
            self.tray_icon.activated.connect(self._on_tray_activated)
            self.tray_icon.show()
        except Exception:
            self.tray_icon = None

    def _from_tray_show(self):
        try:
            self.showNormal()
            self.raise_()
            self.activateWindow()
        except Exception:
            pass

    def _on_tray_activated(self, reason):
        try:
            if reason == QSystemTrayIcon.Trigger:
                self._from_tray_show()
        except Exception:
            pass

    def _sair_definitivo(self):
        try:
            if QMessageBox.question(self, "Sair", "Encerrar servidor?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                inst = QApplication.instance()
                if inst:
                    inst.quit()
        except Exception:
            inst = QApplication.instance()
            if inst:
                inst.quit()

    def closeEvent(self, event):
        try:
            if self.tray_icon and self.tray_icon.isVisible():
                event.ignore()
                self.hide()
                try:
                    self.tray_icon.showMessage("Servidor", "Minimizado na bandeja.", QSystemTrayIcon.Information, 2000)
                except Exception:
                    pass
                return
        except Exception:
            pass

        try:
            inst = QApplication.instance()
            if inst:
                inst.quit()
        except Exception:
            pass

    def _start_monitor_recursos(self):
        try:
            if hasattr(self.monitor_recursos, "isRunning") and not self.monitor_recursos.isRunning():
                self.monitor_recursos.start()
        except Exception:
            pass

    def closeEvent(self, event):
        self.logger.info("GUI: Solicitação de fechamento recebida. Encerrando processos...")
        try:
            self.hide()
        except Exception:
            pass
            
        try:
            if self.sincronizador:
                self.sincronizador._parar = True
            
            if self.monitor_solicitacoes:
                self.monitor_solicitacoes.parar()
                
            if self.executor:
                self.executor.parar_todos_processos()
                
        except Exception as e:
            self.logger.error("Erro ao encerrar componentes: %s", e)
            
        event.accept()

    def _setup_ui(self):
        self.setStyleSheet(EstilosGUI.estilo_janela())
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(8)

        topo = self._criar_topo()
        p_topo = EstilosGUI.obter_paleta()
        topo_frame = QFrame()
        topo_frame.setObjectName("topoFrame")
        topo_frame.setStyleSheet(
            f"QFrame#topoFrame {{ background: transparent; border-bottom: 1px solid {p_topo['borda_suave']}; }}"
        )
        topo_frame.setLayout(topo)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("listaNavegacao")
        self.nav_list.setFixedWidth(220)
        try:
            self.nav_list.currentRowChanged.connect(self._on_secao_alterada)
        except Exception:
            pass

        self.stack = QStackedWidget()
        self.stack.setObjectName("pilhaSecoes")

        splitter = QSplitter()
        splitter.addWidget(self.nav_list)
        splitter.addWidget(self.stack)
        try:
            splitter.setStretchFactor(1, 1)
        except Exception:
            pass

        self.main_layout.addWidget(topo_frame)
        self.main_layout.addWidget(splitter, stretch=1)

    def _criar_topo(self):
        p = EstilosGUI.obter_paleta()
        topo = QHBoxLayout()
        topo.setSpacing(15)
        topo.setContentsMargins(0, 0, 0, 10)
        
        # Status Label
        self.lbl_status = QLabel("AGUARDANDO DADOS...")
        self.lbl_status.setObjectName("statusLabel")
        self.lbl_status.setStyleSheet(f"font-weight: 800; color: {p['aviso']};")
        
        # Search Input - REMOVED
        # self.input_busca = self._criar_input_busca()

        # Adiciona widgets ao layout topo
        topo.addWidget(self.lbl_status)
        topo.addStretch()

        # Auto Sync Button
        self.btn_auto_sync = QPushButton("AUTO SYNC: ON")
        self.btn_auto_sync.setFixedWidth(130) # Fixa largura para evitar pulo
        self.btn_auto_sync.setCheckable(True)
        self.btn_auto_sync.setChecked(True)
        self.btn_auto_sync.setStyleSheet(EstilosGUI.estilo_botao_toggle())
        self.btn_auto_sync.setCursor(Qt.PointingHandCursor)
        try:
            self.btn_auto_sync.clicked.connect(self._on_toggle_auto_sync)
        except Exception:
            pass

        # Refresh Button
        self.btn_force = QPushButton("REFRESH")
        self.btn_force.setStyleSheet(EstilosGUI.estilo_botao_topo())
        try:
            self.btn_force.clicked.connect(self._on_clique_refresh)
        except Exception:
            pass

        # Layout Assembly
        topo.addWidget(self.lbl_status)
        topo.addStretch(1) # Empurra o resto para a direita
        topo.addSpacing(10)
        topo.addWidget(self.btn_auto_sync)
        topo.addSpacing(10)
        topo.addWidget(self.btn_force)
        
        return topo

    def _on_secao_alterada(self, row):
        try:
            if self.stack:
                self.stack.setCurrentIndex(row)
        except Exception:
            pass

    def _ir_para_secao(self, secao):
        alvo = str(secao or "").lower().strip()
        if not alvo:
            return
        try:
            for i in range(self.nav_list.count()):
                it = self.nav_list.item(i)
                if it and it.data(Qt.UserRole) == alvo:
                    self.nav_list.setCurrentRow(i)
                    return
        except Exception:
            pass

    def _on_toggle_auto_sync(self):
        chk = self.btn_auto_sync.isChecked()
        try:
            self.btn_auto_sync.setText("AUTO SYNC: ON" if chk else "AUTO SYNC: OFF")
        except Exception:
            pass
        try:
            self.sincronizador.pausar(not chk)
        except Exception:
            pass

    def _on_clique_refresh(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("ATUALIZAR")
        msg.setText("DESEJA PROSSEGUIR EM FORÇAR A ATUALIZAR?")
        msg.setStyleSheet(EstilosGUI.estilo_janela()) # Aplica estilo dark
        
        btn_sim = msg.addButton("SIM, PROSSEGUIR", QMessageBox.YesRole)
        btn_nao = msg.addButton("NÃO, CANCELAR", QMessageBox.NoRole)
        
        msg.exec()
        
        if msg.clickedButton() == btn_sim:
            self._iniciar_refresh_timer()
            self._forcar_update()

    def _iniciar_refresh_timer(self):
        self.btn_force.setEnabled(False)
        self.refresh_start_time = datetime.now()
        if not hasattr(self, "timer_refresh_label"):
            self.timer_refresh_label = QTimer(self)
            self.timer_refresh_label.timeout.connect(self._update_refresh_label)
        self.timer_refresh_label.start(1000)
        self._update_refresh_label()

    def _update_refresh_label(self):
        if not hasattr(self, "refresh_start_time"):
            return
        delta = datetime.now() - self.refresh_start_time
        s = int(delta.total_seconds())
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        self.btn_force.setText(f"{h:02d}:{m:02d}:{sec:02d}")

    def _parar_refresh_timer(self):
        if hasattr(self, "timer_refresh_label") and self.timer_refresh_label.isActive():
            self.timer_refresh_label.stop()
        self.btn_force.setText("REFRESH")
        self.btn_force.setEnabled(True)

    def _forcar_update(self):
        try:
            self.lbl_status.setText("Atualizando...")
        except Exception:
            pass
        try:
            self.sincronizador.forcar_atualizacao()
        except Exception:
            pass

    @Slot(float, float, float, int)
    def _on_recursos_atualizados(self, c, r, s, t):
        p = EstilosGUI.obter_paleta()
        
        def update_bar(bar, lbl, val, nome):
            try:
                bar.setValue(int(val))
                lbl.setText(f"{nome} {int(val)}%")
                
                cor = p['verde']
                if val >= 80:
                    cor = p['aviso'] # Vermelho
                elif val >= 50:
                    cor = p['amarelo']
                
                bar.setStyleSheet(f"""
                    QProgressBar {{
                        background-color: #333333;
                        border-radius: 4px;
                    }}
                    QProgressBar::chunk {{
                        background-color: {cor};
                        border-radius: 4px;
                    }}
                """)
            except Exception:
                pass

        try:
            if self.cpu_bar and self.cpu_lbl:
                update_bar(self.cpu_bar, self.cpu_lbl, c, "CPU")
            if self.ram_bar and self.ram_lbl:
                update_bar(self.ram_bar, self.ram_lbl, r, "RAM")
            if self.swap_bar and self.swap_lbl:
                update_bar(self.swap_bar, self.swap_lbl, s, "SWAP")
        except Exception:
            pass

    @Slot(object, object)
    def atualizar_dados(self, df_exec, df_reg):
        self._parar_refresh_timer()
        self.df_exec = df_exec.copy() if df_exec is not None else pd.DataFrame()
        self.df_reg = df_reg.copy() if df_reg is not None else pd.DataFrame()

        try:
            self._ultima_atualizacao_planilhas = getattr(self.sincronizador, "ultima_execucao", None)
            self._proxima_atualizacao_planilhas = getattr(self.sincronizador, "proxima_execucao", None)
        except Exception:
            pass

        novo = self.descobridor.mapear_por_registro(self.df_reg)
        mudou = set(novo.keys()) != set(self.mapeamento.keys())
        vazio = (self.stack.count() == 0) if self.stack else True
        self.mapeamento = novo

        self._recalcular_resumos_execucao()

        if mudou or vazio:
            QTimer.singleShot(0, self._reconstruir_abas)
        else:
            QTimer.singleShot(0, self._preencher_cards)
            QTimer.singleShot(0, self._atualizar_monitor)

        u = self._ultima_atualizacao_planilhas
        p = self._proxima_atualizacao_planilhas
        if u or p:
            self.atualizar_status_planilhas(u, p)

    def atualizar_mapeamento_threadsafe(self, e, r):
        # Envia sinal para atualizar na thread da GUI.
        # NUNCA chamar self.atualizar_dados diretamente daqui se estiver em outra thread.
        self.sig_atualizar_dados.emit(e, r)

    def _recalcular_resumos_execucao(self):
        self._resumo_sucesso = []
        self._resumo_falhas = []
        self._resumo_outros = []

        if self.df_exec.empty or "dt_full" not in self.df_exec.columns:
            self.logger.warning("GUI: DataFrame EXEC vazio ou sem dt_full.")
            return

        try:
            self.df_exec["dt_full"] = pd.to_datetime(self.df_exec["dt_full"], errors="coerce")
        except Exception:
            pass

        cols = {c.lower(): c for c in self.df_exec.columns}
        c_met = cols.get("metodo_automacao")
        c_stat = cols.get("status") or cols.get("status_exec") or cols.get("status_execucao")

        if not c_met or not c_stat:
            self.logger.warning("GUI: Colunas não encontradas. Disp: %s", list(cols.keys()))
            return

        hoje = datetime.now(Config.TZ).date()

        try:
            dt_series = self.df_exec["dt_full"]
            dates = dt_series.dt.date
            count_hoje = int((dates == hoje).sum())

            top = dates.value_counts(dropna=True).head(12)
            top_fmt = {str(k): int(v) for k, v in top.items()}

            self.logger.info(
                "GUI_DT_FULL_DIAG: dtype=%s min=%s max=%s hoje=%s count_hoje=%s top_dates=%s",
                str(dt_series.dtype),
                str(dt_series.min()),
                str(dt_series.max()),
                str(hoje),
                count_hoje,
                top_fmt,
            )

            df_hj = self.df_exec[dates == hoje].copy()
            if df_hj.empty:
                self.logger.warning(
                    "GUI: Nenhum registro encontrado para %s. amostra_dt_full=%s",
                    str(hoje),
                    dt_series.head(12).astype(str).tolist(),
                )
                return

            df_hj = df_hj.sort_values("dt_full", ascending=False)

            for _, r in df_hj.iterrows():
                m = str(r.get(c_met, ""))
                s = str(r.get(c_stat, "")).strip().upper()
                h = r["dt_full"].strftime("%H:%M") if pd.notna(r.get("dt_full")) else "-"
                txt = f"{h} - {m}"
                if s == "SUCESSO":
                    self._resumo_sucesso.append(txt)
                elif s in ["FALHA", "ERRO"]:
                    self._resumo_falhas.append(txt + f" ({s})")
                else:
                    self._resumo_outros.append(txt + f" ({s})")

        except Exception as e:
            self.logger.error("GUI_recalc_erro: %s\n%s", e, traceback.format_exc())

    def _reconstruir_abas(self):
        self.navegacao_indices = {}
        self.card_secao = {}
        self.cards.clear()
        self.infos.clear()
        self.dashboard_boxes.clear()
        self.layouts_categorias = {}

        try:
            self.nav_list.clear()
        except Exception:
            pass

        try:
            while self.stack.count():
                w = self.stack.widget(0)
                self.stack.removeWidget(w)
                try:
                    w.deleteLater()
                except Exception:
                    pass
        except Exception:
            pass

        p = EstilosGUI.obter_paleta()

        # MONITOR
        pm = QWidget()
        # Layout principal da aba MONITOR
        # Queremos 5 colunas verticais ocupando a tela inteira
        lm = QHBoxLayout(pm)
        lm.setSpacing(10)
        lm.setContentsMargins(10, 10, 10, 10)
        
        # Cria as 5 colunas
        self.dashboard_boxes["pendentes"] = DashboardBox("A RODAR HOJE", p["amarelo"])
        self.dashboard_boxes["rodando"] = DashboardBox("RODANDO AGORA", p["azul"])
        
        # Conecta duplo clique na lista de rodando para parar
        try:
            self.dashboard_boxes["rodando"].lista.itemDoubleClicked.connect(self._acao_parar_duplo_clique_lista)
        except Exception:
            pass

        self.dashboard_boxes["sucesso"] = DashboardBox("SUCESSO HOJE", p["sucesso"])
        self.dashboard_boxes["falhas"] = DashboardBox("FALHAS / ATENÇÃO", p["destaque"])
        self.dashboard_boxes["outros"] = DashboardBox("OUTROS STATUS", p["texto_sec"])
        
        # Adiciona ao layout horizontal (5 colunas lado a lado)
        lm.addWidget(self.dashboard_boxes["pendentes"])
        lm.addWidget(self.dashboard_boxes["rodando"])
        lm.addWidget(self.dashboard_boxes["sucesso"])
        lm.addWidget(self.dashboard_boxes["falhas"])
        lm.addWidget(self.dashboard_boxes["outros"])

        item = QListWidgetItem("MONITOR")
        item.setData(Qt.UserRole, "monitor")
        item.setSizeHint(QSize(200, 44))
        self.nav_list.addItem(item)
        self.stack.addWidget(pm)

        # ABA BUSCA (Global)
        pb = QWidget()
        lb = QVBoxLayout(pb)
        # Scroll para busca
        sb = QScrollArea()
        sb.setWidgetResizable(True)
        cb = QWidget()
        # Flow layout para resultados de busca (usando grid para simular)
        self.gb_busca = QGridLayout(cb)
        self.gb_busca.setSpacing(20)
        self.gb_busca.setContentsMargins(30, 30, 30, 30)
        # Alinhamento topo/esquerda
        self.gb_busca.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        sb.setWidget(cb)
        lb.addWidget(sb)
        
        self.idx_busca = self.stack.addWidget(pb)
        # Não adicionamos na nav_list pois é acessada via barra de busca

        # 1. CURRENCY (REMOVIDO)
        # item_cur = QListWidgetItem("CURRENCY")
        # item_cur.setData(Qt.UserRole, "currency")
        # item_cur.setSizeHint(QSize(200, 50))
        # self.nav_list.addItem(item_cur)
        # 
        # page_currency = CurrencyPage()
        # self.stack.addWidget(page_currency)

        # 2. ABAS DINAMICAS POR CATEGORIA
        # Ordena categorias (keys do mapeamento)
        categorias = sorted(self.mapeamento.keys())
        
        for cat in categorias:
            # Item da Sidebar
            item = QListWidgetItem(str(cat).upper())
            item.setData(Qt.UserRole, str(cat).lower())
            item.setSizeHint(QSize(200, 50))
            self.nav_list.addItem(item)
            
            # Pagina de Scroll para essa categoria
            page_widget = QWidget()
            page_layout = QVBoxLayout(page_widget)
            page_layout.setSpacing(20)
            page_layout.setContentsMargins(30,30,30,30)
            page_layout.setAlignment(Qt.AlignTop)
            
            # Titulo da Categoria na Pagina
            lbl_tit = QLabel(str(cat).upper())
            lbl_tit.setStyleSheet(f"font-size: 24px; font-weight: 900; color: {p['branco']}; margin-bottom: 20px;")
            page_layout.addWidget(lbl_tit)
            
            # Grid ou Flow para os cards desta categoria
            # Vamos usar um FlowLayout simulado (wrapre) ou QGridLayout se soubermos quantos por linha.
            # Simples: Flow layout usando QGridLayout com col-count calculado ou apenas FlowLayout customizado.
            # Como nao tenho FlowLayout pronto aqui, vou usar um layout que empilha linhas horizontais de 3 em 3 ou 4 em 4.
            
            cards_container = QWidget()
            grid_cards = QGridLayout(cards_container)
            grid_cards.setSpacing(20)
            self.layouts_categorias[str(cat).lower()] = grid_cards # Store grid_cards for later restoration
            
            itens = self.mapeamento[cat]
            col = 0
            row = 0
            MAX_COLS = 3
            
            for met in sorted(itens.keys()):
                info = itens[met].get("registro") or {}
                self.infos[met] = info
                
                card = AutomationCard(met)
                
                # Configura callbacks do card
                try:
                    card.btn_executar.clicked.connect(partial(self._acao_executar, met))
                    card.sig_parar_solicitado.connect(self._acao_parar_duplo_clique)
                    card.btn_parar.clicked.connect(partial(self._acao_parar, met))
                    card.btn_log.clicked.connect(partial(self._acao_ver_log, met))
                except Exception:
                    pass
                
                self.cards[met] = card
                self.card_secao[met] = str(cat).lower()
                
                grid_cards.addWidget(card, row, col)
                col += 1
                if col >= MAX_COLS:
                    col = 0
                    row += 1
            
            page_layout.addWidget(cards_container)
            page_layout.addStretch(1) # Empurra tudo pra cima
            
            scroll_page = QScrollArea()
            scroll_page.setWidgetResizable(True)
            scroll_page.setWidget(page_widget)
            scroll_page.setStyleSheet(f"background: transparent; border: none;")
            
            self.stack.addWidget(scroll_page)

        self._preencher_cards()
        self._atualizar_monitor()
        if self._busca_ativa:
            self._aplicar_busca_cards_global()

        try:
            # Tenta selecionar a primeira categoria encontrada, se houver, senao Monitor
            if len(categorias) > 0:
                # 0=Monitor, 1=Recursos, 2=Primeira Categoria...
                self.nav_list.setCurrentRow(2) 
            else:
                self.nav_list.setCurrentRow(0)
        except Exception:
            pass

    def _preencher_cards(self):
        execs_snapshot = {}
        try:
            execs_snapshot = self.executor.snapshot_execucao()
        except Exception:
            execs_snapshot = {}

        grp = None

        agora_naive = datetime.now(Config.TZ).replace(tzinfo=None)
        agora_ts = pd.Timestamp(agora_naive)

        if not self.df_exec.empty and "dt_full" in self.df_exec.columns:
            try:
                cols = {c.lower(): c for c in self.df_exec.columns}
                c_met = cols.get("metodo_automacao")
                if c_met:
                    df = self.df_exec.copy()
                    df["dt_full"] = pd.to_datetime(df["dt_full"], errors="coerce")
                    df["_norm"] = df[c_met].apply(NormalizadorDF.norm_key)
                    df = df.sort_values("dt_full", ascending=False)
                    grp = df.groupby("_norm")
            except Exception as e:
                self.logger.error("GUI_preencher_cards_grp_erro tipo=%s erro=%s", type(e).__name__, e)

        cols_exec = {c.lower(): c for c in self.df_exec.columns} if not self.df_exec.empty else {}
        c_st = cols_exec.get("status") or cols_exec.get("status_exec") or cols_exec.get("status_execucao")

        for met, card in self.cards.items():
            norm = NormalizadorDF.norm_key(met)
            inf = self.infos.get(met, {})

            prox = self.get_prox_exec(met) if self.get_prox_exec else "-"
            try:
                card.lbl_proxima.setText(prox)
            except Exception:
                pass

            st_txt = "-"
            st_ag = self.get_status_agendamento(met) if self.get_status_agendamento else ""
            if st_ag == "AGENDADO":
                st_txt = "AGENDADO"

            ultima_ok = False

            if grp is not None and norm in getattr(grp, "groups", {}):
                try:
                    grupo = grp.get_group(norm).copy()
                    grupo["dt_full"] = pd.to_datetime(grupo["dt_full"], errors="coerce")

                    mask_fut = grupo["dt_full"].notna() & (grupo["dt_full"] > agora_ts)
                    if mask_fut.any():
                        try:
                            self.logger.warning(
                                "GUI_ULTIMA_FUTURA metodo=%s total_futuras=%s exemplo=%s",
                                met,
                                int(mask_fut.sum()),
                                str(grupo.loc[mask_fut, "dt_full"].iloc[0]),
                            )
                        except Exception:
                            pass

                    grupo_valid = grupo[grupo["dt_full"].notna() & (grupo["dt_full"] <= agora_ts)]
                    if not grupo_valid.empty:
                        ult = grupo_valid.sort_values("dt_full", ascending=False).iloc[0]
                        try:
                            card.lbl_ultima.setText(ult['dt_full'].strftime('%d/%m %H:%M'))
                        except Exception:
                            pass
                        if c_st:
                            st_txt = str(ult.get(c_st, "")).strip().upper() or st_txt
                        ultima_ok = True
                except Exception as e:
                    self.logger.error(
                        "GUI_preencher_cards_last_erro metodo=%s tipo=%s erro=%s",
                        met,
                        type(e).__name__,
                        e,
                    )

            if not ultima_ok:
                try:
                    card.lbl_ultima.setText("-")
                except Exception:
                    pass

            if met in execs_snapshot:
                try:
                    card.definir_status_visual("RODANDO")
                except Exception:
                    pass
                try:
                    ini = execs_snapshot[met]["inicio"]
                    s = int((datetime.now(Config.TZ) - ini).total_seconds())
                    card.lbl_status_badge.setText(f"RODANDO {s//60:02d}:{s%60:02d}")
                except Exception:
                    pass
            else:
                try:
                    card.definir_status_visual(st_txt if st_txt != "-" else "AGUARDANDO")
                except Exception:
                    pass

            is_run = met in execs_snapshot
            try:
                card.btn_executar.setEnabled(not is_run)
                card.btn_executar.setText("RODANDO..." if is_run else "PLAY")
                card.btn_parar.setVisible(False)
            except Exception:
                pass

    def _atualizar_monitor(self):
        try:
            execs = self.executor.snapshot_execucao()
        except Exception:
            execs = {}

        l_run = []
        for m, i in execs.items():
            try:
                dur = str(datetime.now(Config.TZ) - i["inicio"]).split(".")[0]
            except Exception:
                dur = "-"
            l_run.append(f"{m} ({dur})")

        try:
            self.dashboard_boxes["rodando"].atualizar_lista(l_run if l_run else ["Nada rodando."])
        except Exception:
            pass

        l_pend = []
        try:
            if self.agendador:
                snap = self.agendador.snapshot_agendamentos()
                now = datetime.now(Config.TZ)
                for m, dt in snap.items():
                    if dt and dt.date() == now.date() and dt > now:
                        l_pend.append(f"{dt.strftime('%H:%M')} - {m}")
        except Exception:
            pass

        try:
            self.dashboard_boxes["pendentes"].atualizar_lista(sorted(l_pend) if l_pend else ["Nada pendente."])
            self.dashboard_boxes["sucesso"].atualizar_lista(self._resumo_sucesso or ["-"])
            self.dashboard_boxes["falhas"].atualizar_lista(self._resumo_falhas or ["-"])
            self.dashboard_boxes["outros"].atualizar_lista(self._resumo_outros or ["-"])
        except Exception:
            pass

    def _acao_executar(self, metodo):
            path = None
            try:
                if "ISOLADOS" in self.mapeamento and metodo in self.mapeamento["ISOLADOS"]:
                    path = self.mapeamento["ISOLADOS"][metodo]["path"]
                else:
                    for _, its in self.mapeamento.items():
                        if metodo in its:
                            path = its[metodo]["path"]
                            break
            except Exception:
                path = None

            try:
                if self.verificar_execucao_hoje and self.verificar_execucao_hoje(metodo):
                    self.logger.info("Manual: %s já rodou hoje, mas execução forçada pelo usuário.", metodo)
            except Exception:
                pass

            if not path:
                self._append_log(f"Não achei path do método: {metodo}")
                return

            try:
                usuario_manual = f"{getpass.getuser()}@c6bank.com"
                ok = self.executor.enfileirar(metodo, path, {"origem": "manual", "usuario": usuario_manual})
                if ok and metodo in self.cards:
                    self.cards[metodo].btn_executar.setText("INICIANDO...")
                    self.cards[metodo].btn_executar.setEnabled(False)
            except Exception as e:
                self._append_log(f"Falha ao enfileirar {metodo}: {e}")

    # Antigos metodos removidos em favor dos novos implementados no final
    # (Mantendo apenas o que nao for duplicado)

    # --- LÓGICA DE BUSCA GLOBAL ---
    def _on_busca_text_changed(self, texto):
        texto = texto.lower().strip()
        
        if not texto and self._busca_ativa:
            # Limpou: Restaura todos os cards para suas posições originais
            self._restaurar_cards_posicao_original()
            
            self._busca_ativa = False
            if self._tab_antes_busca is not None:
                # Volta para a tab que estava antes
                if self._tab_antes_busca < self.stack.count():
                   self.stack.setCurrentIndex(self._tab_antes_busca)
            self._tab_antes_busca = None
            return

        self._busca_texto = texto
        
        # Se começou a buscar agora, salva onde estava e vai para a tab de busca
        if texto and not self._busca_ativa:
            self._busca_ativa = True
            self._tab_antes_busca = self.stack.currentIndex()
            # Muda para a tab de busca (índice salvo em self.idx_busca)
            self.stack.setCurrentIndex(self.idx_busca)

        if self._busca_ativa:
            self._aplicar_busca_cards_global()

    def _restaurar_cards_posicao_original(self):
        # Itera sobre os métodos e restaura para seus layouts originais
        # Precisamos saber qual layout pertence a qual metodo.
        # self.card_secao[met] = nome_categoria_lower
        # self.layouts_categorias[nome_categoria_lower] = QGridLayout
        
        # Agrupar metodos por categoria para reinserir em ordem (opcional, mas bom)
        
        # Limpa o grid de busca primeiro (sem deletar os cards, apenas remove)
        while self.gb_busca.count():
            item = self.gb_busca.takeAt(0)
            if item.widget():
                item.widget().setParent(None) # Desacopla
                
        # Recoloca nos layouts originais
        # Para manter a ordem visual, o ideal seria reconstruir ou apenas re-adicionar na ordem.
        # Como o gridLayout preenche row/col, vamos apenas re-adicionar sequencialmente.
        
        # Zerar contadores dos grids originais?
        # A forma mais segura é: limpar todos os grids de categoria e repopular.
        
        # 1. Limpa grids de categoria
        if not hasattr(self, "layouts_categorias"):
            return

        for cat_lower, grid in self.layouts_categorias.items():
            # Remove tudo do grid
            while grid.count():
                item = grid.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
                    
        # 2. Repopula
        # Precisamos da ordem original. self.mapeamento tem a estrutura.
        MAX_COLS = 3
        
        for cat, itens in self.mapeamento.items():
            cat_lower = str(cat).lower()
            grid = self.layouts_categorias.get(cat_lower)
            if not grid:
                continue
                
            row, col = 0, 0
            for met in sorted(itens.keys()):
                if met in self.cards:
                    card = self.cards[met]
                    card.setVisible(True) # Garante visivel
                    grid.addWidget(card, row, col)
                    col += 1
                    if col >= MAX_COLS:
                        col = 0
                        row += 1

    def _aplicar_busca_cards_global(self):
        texto = self._busca_texto
        if not texto:
            return

        # Remove cards de seus layouts atuais e joga no grid de busca se der match
        
        c = 0
        r = 0
        MAX_COLS_BUSCA = 4
        
        # Limpa grid de busca antes de popular
        while self.gb_busca.count():
            it = self.gb_busca.takeAt(0)
            if it.widget():
                it.widget().setParent(None)

        for met, card in self.cards.items():
            # Match?
            # card.lbl_status_chip (ANTIGO lbl_status)
            try:
                st_text = card.lbl_status_chip.text()
            except:
                st_text = ""
                
            txt = f"{met} {st_text}".lower()
            if texto in txt:
                # Match! Move para gb_busca
                self.gb_busca.addWidget(card, r, c)
                card.setVisible(True)
                c += 1
                if c >= MAX_COLS_BUSCA:
                    c = 0
                    r += 1
            else:
                # Se nao match, o card fica "sem pai" ou invisivel?
                # Melhor esconder ou deixar quieto.
                # Como movemos apenas os que dão match, os outros ficam onde estão?
                # NAO, porque se mudarmos de aba, o layout original vai estar "furado" ou duplicado.
                # O ideal na busca é roubar TODOS os cards ou apenas os visiveis.
                # Simplificação: O search "rouba" o card. Se sair do search, chamamos restaurar.
                # Então, aqui, se não der match, garantimos que ele não está no grid de busca.
                pass

    def _achar_ultimo_log_metodo(self, met):
        try:
            base = Config.DIR_LOGS_BASE / str(met).lower()
            if not base.exists():
                return None
            arquivos = [p for p in base.rglob("*.log") if p.is_file()]
            if not arquivos:
                return None
            return max(arquivos, key=lambda p: p.stat().st_mtime)
        except Exception:
            return None

    def _acao_ver_log(self, met):
        try:
            arq = self._achar_ultimo_log_metodo(met)
            if not arq:
                try:
                    QMessageBox.information(self, "Log", f"Nenhum log encontrado para {met}.")
                except Exception:
                    pass
                return

            try:
                conteudo = arq.read_text(encoding="utf-8", errors="replace")
            except Exception:
                conteudo = ""

            dlg = LogDialog(met, conteudo, parent=self)
            try:
                dlg.exec()
            except Exception:
                pass
        except Exception as e:
            try:
                QMessageBox.information(self, "Log", f"Erro ao abrir log de {met}: {e}")
            except Exception:
                pass




    def _tick_gui(self):
        try:
            # --- Check de Virada de Dia (Midnight Reset) ---
            hoje_atual = datetime.now(Config.TZ).date()
            if hasattr(self, "data_atual_gui") and hoje_atual != self.data_atual_gui:
                self.logger.info("VIRADA DE DIA DETECTADA (GUI): %s -> %s. Resetando visualização.", self.data_atual_gui, hoje_atual)
                self.data_atual_gui = hoje_atual
                
                # Reseta listas locais
                self._resumo_sucesso = []
                self._resumo_falhas = []
                self._resumo_outros = []
                
                # Limpa DF de execucoes da GUI para não mostrar dados de ontem enquanto não sincroniza
                # (Opcional: ou filtra). Vamos filtrar para garantir limpeza visual imediata
                if not self.df_exec.empty and "dt_full" in self.df_exec.columns:
                     # Mantem apenas o que for >= hoje (provavelmente nada se acabou de virar)
                     try:
                         # self.df_exec = self.df_exec[self.df_exec["dt_full"].dt.date == hoje_atual].copy() 
                         # Melhor: Não alterar o DF global sem sync, mas limpar as listas
                         pass
                     except:
                         pass

                # Limpa Listas de Monitor (DashboardBoxes)
                for box in self.dashboard_boxes.values():
                    try:
                        box.lista.clear()
                    except:
                        pass
                
                # Forca atualizacao para baixar planilhas do novo dia (que estarao vazias ou com novos agendamentos)
                self.logger.info("Forçando sincronização pós-virada...")
                self._forcar_update()
            
            self._preencher_cards()
        except Exception:
            pass
        try:
            self._atualizar_monitor()
        except Exception:
            pass

        try:
            u = getattr(self.sincronizador, "ultima_execucao", None)
            p = getattr(self.sincronizador, "proxima_execucao", None)
            if u or p:
                self.atualizar_status_planilhas(u, p)
        except Exception:
            pass


        try:
            execs = self.executor.snapshot_execucao()
        except Exception:
            execs = {}

        linhas = []
        agora = datetime.now(Config.TZ)

        for met, info in execs.items():
            pid = (info or {}).get("pid")
            ini = (info or {}).get("inicio")
            dur = "-"
            try:
                if ini:
                    dur = str(agora - ini).split(".")[0]
            except Exception:
                pass

            cpu = "-"
            mem = "-"

            if pid:
                try:
                    p = self._ps_cache.get(pid)
                    if p is None or not p.is_running():
                        p = psutil.Process(pid)
                        self._ps_cache[pid] = p
                        try:
                            p.cpu_percent(None)
                            self._ps_cpu_init.add(pid)
                        except Exception:
                            pass

                    try:
                        cpu_val = p.cpu_percent(None)
                        cpu = f"{cpu_val:.1f}%"
                    except Exception:
                        cpu = "-"

                    try:
                        mem_mb = p.memory_info().rss / (1024 * 1024)
                        mem = f"{mem_mb:.0f}MB"
                    except Exception:
                        mem = "-"

                except Exception:
                    cpu = "-"
                    mem = "-"

            linhas.append(f"{met} | pid={pid or '-'} | cpu={cpu} | mem={mem} | dur={dur}")

        try:
            smart_update_listwidget(self.lista_recursos_metodos, linhas if linhas else ["Nenhum processo em execução."])
        except Exception:
            try:
                self.lista_recursos_metodos.clear()
                for x in (linhas if linhas else ["Nenhum processo em execução."]):
                    self.lista_recursos_metodos.addItem(x)
            except Exception:
                pass

    def atualizar_status_planilhas(self, u, p):
        try:
            txt = []
            if u:
                txt.append(f"ÚLTIMA ATUALIZAÇÃO: {u.strftime('%H:%M')}")
            if p:
                txt.append(f"PRÓXIMA ATUALIZAÇÃO: {p.strftime('%H:%M')}")
            self.lbl_status.setText("   |   ".join(txt) if txt else "AGUARDANDO DADOS...")
        except Exception:
            pass

    def marcar_metodo_ocupado(self, met, ocupado: bool):
        try:
            self.sig_marcar_ocupado.emit(met, bool(ocupado))
        except Exception:
            self._slot_marcar_ocupado(met, bool(ocupado))

    @Slot(str, bool)
    def _slot_marcar_ocupado(self, met, ocupado):
        try:
            card = self.cards.get(met)
            if not card:
                return

            if ocupado:
                try:
                    card.btn_executar.setEnabled(False)
                    card.btn_executar.setText("RODANDO...")
                    card.definir_status_visual("RODANDO")
                except Exception:
                    pass
            else:
                try:
                    card.btn_executar.setEnabled(True)
                    card.btn_executar.setText("EXECUTAR")
                except Exception:
                    pass
        except Exception:
            pass

    @Slot(str)
    def _append_log(self, msg):
        try:
            if not self.log_painel:
                return

            self.log_painel.append(str(msg))
            try:
                cur = self.log_painel.textCursor()
                cur.movePosition(QTextCursor.End)
                self.log_painel.setTextCursor(cur)
            except Exception:
                pass

            # poda o log do painel (evita exploding)
            try:
                if self.log_painel.document().blockCount() > 2000:
                    doc = self.log_painel.document()
                    cur = QTextCursor(doc)
                    cur.movePosition(QTextCursor.Start)
                    for _ in range(200):
                        cur.select(QTextCursor.LineUnderCursor)
                        cur.removeSelectedText()
                        cur.deleteChar()
            except Exception:
                pass
        except Exception:
            pass


    def _abrir_financeiro(self):
        try:
            dlg = CurrencyDialog(self)
            dlg.exec()
        except Exception:
            pass
    def _acao_parar_duplo_clique(self, met):
        self._acao_parar(met)

    def _acao_parar_duplo_clique_lista(self, item):
        if not item:
            return
        # O texto geralmente é "METODO (Iniciado ha X)" ou apenas "METODO"
        # Vamos tentar extrair o nome do metodo.
        texto = item.text()
        # Assumindo que o nome do metodo é a primeira parte antes de qualquer " ("
        # Ou se for formatado diferente, ajustamos. 
        # No _atualizar_monitor (vermelho/azul), geralmente inserimos o nome puro ou com detalhes.
        # Vamos pegar a primeira palavra ou limpar.
        
        # Estrategia: tentar casar com chaves de self.mapeamento (lower)
        # removemos parenteses de tempo se houver
        provavel_nome = texto.split("(")[0].strip()
        
        # Verifica se existe no mapeamento (case insensitive)
        met_alvo = None
        for cat, dic in self.mapeamento.items():
            for m in dic.keys():
                if m.lower() == provavel_nome.lower():
                    met_alvo = m
                    break
            if met_alvo:
                break
        
        if met_alvo:
            self._acao_parar(met_alvo)
        else:
            # Fallback: tenta parar pelo texto cru se for um nome valido
            self._acao_parar(provavel_nome)

    def _acao_parar(self, met):
        msg = QMessageBox(self)
        msg.setWindowTitle("PARAR EXECUÇÃO")
        msg.setText(f"Deseja interromper a execução de:\n\n{met}?")
        msg.setStyleSheet(EstilosGUI.estilo_janela())
        btn_sim = msg.addButton("SIM, PARAR", QMessageBox.YesRole)
        btn_nao = msg.addButton("NÃO", QMessageBox.NoRole)
        msg.exec()
        
        if msg.clickedButton() == btn_sim:
            try:
                self.executor.parar_processo(met)
                self.logger.info("GUI: Solicitado parada forçada de %s", met)
                # O feedback visual virá na proxima atualização
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Erro ao parar: {e}")
