from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QDialog,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QGridLayout,
)

from servidor.gui.styles import EstilosGUI

class AutomationCard(QFrame):
    sig_parar_solicitado = pyqtSignal(str)

    def __init__(self, titulo):
        super().__init__()
        self.titulo_texto = str(titulo).upper()
        self.setObjectName("AutomationCard")
        # Material Card Size: Consistent width, height adapts but minimum provided
        self.setFixedSize(320, 190) 

        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 1. Header: Title + Status Chip
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        self.lbl_titulo = QLabel(self.titulo_texto)
        self.lbl_titulo.setObjectName("cardTitle")
        self.lbl_titulo.setWordWrap(True)
        
        self.lbl_status_chip = QLabel("AGUARDANDO")
        self.lbl_status_chip.setObjectName("statusChip")
        self.lbl_status_chip.setAlignment(Qt.AlignCenter)
        self.lbl_status_chip.setFixedSize(90, 24)
        
        header_layout.addWidget(self.lbl_titulo, stretch=1)
        header_layout.addWidget(self.lbl_status_chip)
        layout.addLayout(header_layout)

        # 2. Details Grid (Last Run, Next Run)
        details_layout = QGridLayout()
        details_layout.setVerticalSpacing(4)
        details_layout.setHorizontalSpacing(10)
        
        # Row 1: Labels
        lbl_last_label = QLabel("ÙLTIMA EXECUÇÃO")
        lbl_last_label.setObjectName("cardDetail")
        lbl_last_label.setStyleSheet("font-weight: 600; font-size: 10px; color: #9AA0A6;")
        
        lbl_next_label = QLabel("PRÓXIMA EXECUÇÃO")
        lbl_next_label.setObjectName("cardDetail")
        lbl_next_label.setStyleSheet("font-weight: 600; font-size: 10px; color: #9AA0A6;")
        
        details_layout.addWidget(lbl_last_label, 0, 0)
        details_layout.addWidget(lbl_next_label, 0, 1)
        
        # Row 2: Values
        self.lbl_ultima = QLabel("-")
        self.lbl_ultima.setObjectName("cardDetail")
        
        self.lbl_proxima = QLabel("-")
        self.lbl_proxima.setObjectName("cardDetail")
        
        details_layout.addWidget(self.lbl_ultima, 1, 0)
        details_layout.addWidget(self.lbl_proxima, 1, 1)
        
        layout.addLayout(details_layout)
        
        layout.addStretch(1)

        # 3. Action Bar
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        self.btn_executar = QPushButton("PLAY")
        self.btn_executar.setObjectName("btnActionMajor")
        self.btn_executar.setCursor(Qt.PointingHandCursor)
        self.btn_executar.setFixedHeight(36)
        
        self.btn_log = QPushButton("LOG")
        self.btn_log.setCursor(Qt.PointingHandCursor)
        self.btn_log.setFixedHeight(36)
        
        self.btn_parar = QPushButton("STOP")
        self.btn_parar.setCursor(Qt.PointingHandCursor)
        self.btn_parar.setFixedHeight(36)
        self.btn_parar.setVisible(False)
        self.btn_parar.setStyleSheet("color: #F28B82; border: 1px solid #F28B82;") # Red for Stop
        
        actions_layout.addWidget(self.btn_executar, stretch=2)
        actions_layout.addWidget(self.btn_log, stretch=1)
        actions_layout.addWidget(self.btn_parar, stretch=1)
        
        layout.addLayout(actions_layout)

        self.definir_status_visual("AGUARDANDO")

    def mouseDoubleClickEvent(self, event):
        self.sig_parar_solicitado.emit(self.titulo_texto)
        super().mouseDoubleClickEvent(event)

    def definir_status_visual(self, status_texto: str):
        p = EstilosGUI.obter_paleta()
        st = (str(status_texto) or "").upper()
        
        self.setStyleSheet(EstilosGUI.estilo_card_material())
        
        bg = "#5F6368" # Default Grey
        fg = "#FFFFFF"
        
        if st == "RODANDO":
            bg = p["azul"]
            fg = "#202124" # Dark text on blue
        elif st in ["FALHA", "ERRO"]:
            bg = p["erro"]
            fg = "#202124"
        elif st == "SUCESSO":
            bg = p["sucesso"]
            fg = "#202124"
        elif st == "AGENDADO":
            bg = p["amarelo"]
            fg = "#202124"
            
        self.lbl_status_chip.setText(st)
        self.lbl_status_chip.setStyleSheet(f"background-color: {bg}; color: {fg}; border-radius: 12px;")

def smart_update_listwidget(widget: QListWidget, itens_texto):
    """
    Atualiza QListWidget sem destruir tudo: mantém seleção e ordem,
    só adiciona/remove/reordena o necessário.
    """
    novos = list(itens_texto or [])
    atuais = [widget.item(i).text() for i in range(widget.count())]
    if atuais == novos:
        return

    selecionados = {i.text() for i in widget.selectedItems()}

    itens_existentes = {
        widget.item(i).text(): widget.item(i) for i in range(widget.count())
    }
    novos_set = set(novos)

    # remove o que não existe mais
    for texto, item in list(itens_existentes.items()):
        if texto not in novos_set:
            row = widget.row(item)
            widget.takeItem(row)
            itens_existentes.pop(texto, None)

    # garante ordem e cria novos
    for idx, texto in enumerate(novos):
        item = itens_existentes.get(texto)
        if item is None:
            item = QListWidgetItem(texto)
            widget.insertItem(idx, item)
        else:
            row_atual = widget.row(item)
            if row_atual != idx:
                widget.takeItem(row_atual)
                widget.insertItem(idx, item)
        item.setSelected(texto in selecionados)

class DashboardBox(QFrame):
    def __init__(self, titulo, cor_topo):
        super().__init__()
        self.setObjectName("DashboardBox")
        self.setStyleSheet(EstilosGUI.estilo_dashboard_box(cor_topo))
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(20, 20, 20, 20)
        self.layout().setSpacing(0)
        
        lbl = QLabel(titulo)
        lbl.setObjectName("tituloBox")
        lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.layout().addWidget(lbl)
        
        self.lista = QListWidget()
        self.lista.setAlternatingRowColors(False)
        self.layout().addWidget(self.lista)

    def atualizar_lista(self, itens_texto):
        smart_update_listwidget(self.lista, itens_texto)

    def add_widget(self, widget):
        self.layout().addWidget(widget)

class LogDialog(QDialog):
    def __init__(self, titulo, conteudo, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Log: {titulo}")
        self.resize(900, 700)
        p = EstilosGUI.obter_paleta()
        self.setStyleSheet(f"background-color: {p['bg_fundo']}; color: {p['branco']};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        
        lbl = QLabel(f"Último Log Disponível - {titulo}")
        lbl.setStyleSheet("font-weight: 500; font-size: 18px; margin-bottom: 16px; color: #FFFFFF;")
        layout.addWidget(lbl)
        
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet(
            f"background-color: {p['bg_card']}; border: 1px solid {p['borda_suave']}; "
            "padding: 16px; font-family: 'Consolas', 'Roboto Mono', monospace; font-size: 13px; border-radius: 8px;"
        )
        self.text_edit.setText(conteudo)
        layout.addWidget(self.text_edit)
        
        btn_fechar = QPushButton("FECHAR")
        btn_fechar.setStyleSheet(EstilosGUI.estilo_botao_topo())
        btn_fechar.setCursor(Qt.PointingHandCursor)
        btn_fechar.clicked.connect(self.close)
        
        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(btn_fechar)
        layout.addLayout(hbox)
