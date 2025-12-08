from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QWidget, QComboBox, QFrame, QAbstractItemView
)
from servidor.gui.styles import EstilosGUI
from servidor.api_clients import WeatherClient, FinanceClient

class WeatherDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CLIMA - SÃO PAULO")
        self.setFixedSize(400, 250)
        p = EstilosGUI.obter_paleta()
        self.setStyleSheet(f"background-color: {p['bg_fundo']}; color: {p['branco']}; font-family: 'Montserrat';")
        
        layout = QVBoxLayout(self)
        
        self.lbl_titulo = QLabel("SÃO PAULO, BR")
        self.lbl_titulo.setStyleSheet(f"font-size: 24px; font-weight: 900; color: {p['branco']};")
        self.lbl_titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_titulo)
        
        self.lbl_temp = QLabel("-- °C")
        self.lbl_temp.setStyleSheet(f"font-size: 48px; font-weight: 900; color: {p['destaque']};")
        self.lbl_temp.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_temp)
        
        self.lbl_desc = QLabel("Carregando...")
        self.lbl_desc.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {p['texto_sec']};")
        self.lbl_desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_desc)
        
        self.lbl_extra = QLabel("Vento: -- km/h")
        self.lbl_extra.setStyleSheet(f"font-size: 14px; color: {p['texto_sec']};")
        self.lbl_extra.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_extra)
        
        btn_fechar = QPushButton("FECHAR")
        btn_fechar.setStyleSheet(EstilosGUI.estilo_botao_topo())
        btn_fechar.clicked.connect(self.close)
        layout.addWidget(btn_fechar)
        
        QTimer.singleShot(100, self._carregar_dados)

    def _carregar_dados(self):
        dados = WeatherClient.get_weather_sp()
        if dados:
            self.lbl_temp.setText(f"{dados['temp']} °C")
            desc = WeatherClient.get_wmo_description(dados['code'])
            self.lbl_desc.setText(desc.upper())
            self.lbl_extra.setText(f"Vento: {dados['wind']} km/h | Atualizado: {dados['time']}")
        else:
            self.lbl_desc.setText("ERRO AO CARREGAR")

class CurrencyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MERCADO FINANCEIRO")
        self.resize(600, 700)
        p = EstilosGUI.obter_paleta()
        self.setStyleSheet(f"background-color: {p['bg_fundo']}; color: {p['branco']}; font-family: 'Montserrat';")
        
        layout = QVBoxLayout(self)
        
        topo = QHBoxLayout()
        lbl = QLabel("MERCADO FINANCEIRO")
        lbl.setStyleSheet("font-size: 20px; font-weight: 900;")
        topo.addWidget(lbl)
        
        self.btn_toggle = QPushButton("VER: CRIPTOMOEDAS")
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setChecked(False) # False = Crypto, True = Fiat
        self.btn_toggle.setStyleSheet(EstilosGUI.estilo_botao_topo())
        self.btn_toggle.clicked.connect(self._alternar_visualizacao)
        topo.addWidget(self.btn_toggle)
        layout.addLayout(topo)
        
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(5)
        self.tabela.setHorizontalHeaderLabels(["NOME", "SÍMBOLO", "PREÇO", "VAR 24H", "ATUALIZADO EM"])
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setStyleSheet(f"""
            QTableWidget {{
                background-color: {p['bg_fundo']};
                gridline-color: {p['borda_suave']};
                border: none;
            }}
            QHeaderView::section {{
                background-color: {p['bg_card']};
                color: {p['texto_sec']};
                padding: 5px;
                border: none;
                font-weight: 900;
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
        """)
        layout.addWidget(self.tabela)
        
        btn_fechar = QPushButton("FECHAR")
        btn_fechar.setStyleSheet(EstilosGUI.estilo_botao_topo())
        btn_fechar.clicked.connect(self.close)
        layout.addWidget(btn_fechar)
        
        QTimer.singleShot(100, self._carregar_dados)

    def _alternar_visualizacao(self):
        is_fiat = self.btn_toggle.isChecked()
        self.btn_toggle.setText("VER: MOEDAS FIAT" if not is_fiat else "VER: CRIPTOMOEDAS")
        # Se is_fiat=True, estamos vendo Fiat, entao o botao deve sugerir voltar pra Crypto?
        # O texto do botao geralmente diz o que vai acontecer ou o que esta vendo.
        # Vamos fazer: Texto mostra o que esta vendo.
        self.btn_toggle.setText("EXIBINDO: MOEDAS FIAT" if is_fiat else "EXIBINDO: CRIPTOMOEDAS")
        self._carregar_dados()

    def _carregar_dados(self):
        is_fiat = self.btn_toggle.isChecked()
        self.tabela.setRowCount(0)
        p = EstilosGUI.obter_paleta()
        
        if not is_fiat: # Crypto
            dados = FinanceClient.get_top_crypto(50)
            self.tabela.setRowCount(len(dados))
            for r, item in enumerate(dados):
                self.tabela.setItem(r, 0, QTableWidgetItem(str(item['name'])))
                self.tabela.setItem(r, 1, QTableWidgetItem(str(item['symbol'])))
                self.tabela.setItem(r, 2, QTableWidgetItem(f"$ {item['price_usd']}"))
                
                var = item['change_24h']
                item_var = QTableWidgetItem(f"{var:.2f}%")
                if var and var > 0:
                    item_var.setForeground(Qt.green)
                else:
                    item_var.setForeground(Qt.red)
                self.tabela.setItem(r, 3, item_var)
                
                # Formatando data ISO do coingecko
                dt = str(item.get("last_updated", ""))
                try:
                    # 2023-12-04T10:00:00.000Z
                    dt = dt.split("T")[1].split(".")[0]
                except: pass
                self.tabela.setItem(r, 4, QTableWidgetItem(dt))
                
        else: # Fiat
            dados = FinanceClient.get_top_fiat()
            self.tabela.setRowCount(len(dados))
            for r, item in enumerate(dados):
                self.tabela.setItem(r, 0, QTableWidgetItem(str(item['name'])))
                self.tabela.setItem(r, 1, QTableWidgetItem(f"{item['code']}/{item['codein']}"))
                self.tabela.setItem(r, 2, QTableWidgetItem(f"R$ {item['bid']:.4f}"))
                
                var = item['pct_change']
                item_var = QTableWidgetItem(f"{var}%")
                if var and var > 0:
                    item_var.setForeground(Qt.green)
                else:
                    item_var.setForeground(Qt.red)
                self.tabela.setItem(r, 3, item_var)

                self.tabela.setItem(r, 4, QTableWidgetItem(str(item.get("last_updated", ""))))

class CurrencyPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        p = EstilosGUI.obter_paleta()
        
        layout = QHBoxLayout(self)
        layout.setSpacing(20)
        
        # --- LEFT: FIAT ---
        frame_fiat = QFrame()
        frame_fiat.setStyleSheet(f"background-color: {p['bg_card']}; border-radius: 16px; border: 1px solid {p['borda_suave']};")
        layout_fiat = QVBoxLayout(frame_fiat)
        
        lbl_fiat = QLabel("MOEDAS FIAT (TOP 50)")
        lbl_fiat.setStyleSheet(f"font-size: 18px; font-weight: 900; color: {p['branco']}; margin-bottom: 10px;")
        lbl_fiat.setAlignment(Qt.AlignCenter)
        layout_fiat.addWidget(lbl_fiat)
        
        self.table_fiat = self._criar_tabela()
        layout_fiat.addWidget(self.table_fiat)
        
        layout.addWidget(frame_fiat)
        
        # --- RIGHT: CRYPTO ---
        frame_crypto = QFrame()
        frame_crypto.setStyleSheet(f"background-color: {p['bg_card']}; border-radius: 16px; border: 1px solid {p['borda_suave']};")
        layout_crypto = QVBoxLayout(frame_crypto)
        
        lbl_crypto = QLabel("CRIPTOMOEDAS (TOP 50)")
        lbl_crypto.setStyleSheet(f"font-size: 18px; font-weight: 900; color: {p['branco']}; margin-bottom: 10px;")
        lbl_crypto.setAlignment(Qt.AlignCenter)
        layout_crypto.addWidget(lbl_crypto)
        
        self.table_crypto = self._criar_tabela()
        layout_crypto.addWidget(self.table_crypto)
        
        layout.addWidget(frame_crypto)
        
        # Timer for auto-refresh
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._carregar_dados)
        self.timer.start(60000) # 60s refresh
        
        QTimer.singleShot(100, self._carregar_dados)

    def _criar_tabela(self):
        p = EstilosGUI.obter_paleta()
        t = QTableWidget()
        t.setColumnCount(5)
        t.setHorizontalHeaderLabels(["NOME", "SÍMBOLO", "PREÇO", "VAR 24H", "ATUALIZADO"])
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                gridline-color: {p['borda_suave']};
                border: none;
                color: {p['texto_sec']};
            }}
            QHeaderView::section {{
                background-color: {p['bg_card_hover']};
                color: {p['branco']};
                padding: 8px;
                border: none;
                font-weight: 900;
                text-transform: uppercase;
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {p['borda_suave']};
            }}
            QTableWidget::item:selected {{
                background-color: {p['amarelo']};
                color: #000000;
                border-radius: 4px;
            }}
        """)
        return t

    def _carregar_dados(self):
        self._carregar_fiat()
        self._carregar_crypto()

    def _carregar_fiat(self):
        dados = FinanceClient.get_top_fiat()
        self.table_fiat.setRowCount(0)
        self.table_fiat.setRowCount(len(dados))
        for r, item in enumerate(dados):
            self.table_fiat.setItem(r, 0, QTableWidgetItem(str(item['name'])))
            self.table_fiat.setItem(r, 1, QTableWidgetItem(f"{item['code']}/{item['codein']}"))
            self.table_fiat.setItem(r, 2, QTableWidgetItem(f"R$ {item['bid']:.4f}"))
            
            var = item['pct_change']
            item_var = QTableWidgetItem(f"{var}%")
            if var and var > 0:
                item_var.setForeground(Qt.green)
            else:
                item_var.setForeground(Qt.red)
            self.table_fiat.setItem(r, 3, item_var)
            self.table_fiat.setItem(r, 4, QTableWidgetItem(str(item.get("last_updated", ""))))

    def _carregar_crypto(self):
        dados = FinanceClient.get_top_crypto(50)
        self.table_crypto.setRowCount(0)
        self.table_crypto.setRowCount(len(dados))
        for r, item in enumerate(dados):
            self.table_crypto.setItem(r, 0, QTableWidgetItem(str(item['name'])))
            self.table_crypto.setItem(r, 1, QTableWidgetItem(str(item['symbol'])))
            self.table_crypto.setItem(r, 2, QTableWidgetItem(f"$ {item['price_usd']}"))
            
            var = item['change_24h']
            item_var = QTableWidgetItem(f"{var:.2f}%")
            if var and var > 0:
                item_var.setForeground(Qt.green)
            else:
                item_var.setForeground(Qt.red)
            self.table_crypto.setItem(r, 3, item_var)
            
            dt = str(item.get("last_updated", ""))
            try:
                dt = dt.split("T")[1].split(".")[0]
            except: pass
            self.table_crypto.setItem(r, 4, QTableWidgetItem(dt))

class WeatherWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        p = EstilosGUI.obter_paleta()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Container com fundo
        container = QFrame()
        container.setStyleSheet(f"background-color: {p['bg_card']}; border-radius: 8px; border: 1px solid {p['borda_suave']};")
        l_cont = QHBoxLayout(container)
        l_cont.setContentsMargins(15, 8, 15, 8)
        l_cont.setSpacing(15)
        
        # Temp
        self.lbl_temp = QLabel("--°C")
        self.lbl_temp.setStyleSheet(f"font-size: 16px; font-weight: 900; color: {p['destaque']};")
        l_cont.addWidget(self.lbl_temp)
        
        # Info Vertical
        vbox = QVBoxLayout()
        vbox.setSpacing(0)
        vbox.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_desc = QLabel("SP - ..")
        self.lbl_desc.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {p['branco']};")
        vbox.addWidget(self.lbl_desc)
        
        self.lbl_att = QLabel("Att: --:--")
        self.lbl_att.setStyleSheet(f"font-size: 9px; color: {p['texto_sec']};")
        vbox.addWidget(self.lbl_att)
        
        l_cont.addLayout(vbox)
        layout.addWidget(container)
        
        # Timer update 15 min
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update)
        self.timer.start(15 * 60 * 1000)
        
        QTimer.singleShot(1000, self._update)
        
    def _update(self):
        try:
            dados = WeatherClient.get_weather_sp()
            if dados:
                self.lbl_temp.setText(f"{dados['temp']}°C")
                desc = WeatherClient.get_wmo_description(dados['code'])
                self.lbl_desc.setText(desc.upper())
                try:
                    # Tenta formatar a hora se for HH:MM
                    hora = dados['time'].split(' ')[1]
                    self.lbl_att.setText(f"Att: {hora}") 
                except:
                    self.lbl_att.setText(f"Att: {dados['time']}")
            else:
                self.lbl_desc.setText("ERRO")
        except Exception:
            pass
