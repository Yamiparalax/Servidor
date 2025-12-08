from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
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
)

from servidor.gui.styles import EstilosGUI

class CardNetflix(QFrame):
    sig_parar_solicitado = Signal(str)

    def __init__(self, titulo):
        super().__init__()
        self.titulo_texto = str(titulo).upper()
        self.setObjectName("cardNetflix")
        self.setFixedSize(280, 160) # Aspect ratio mais wide

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(5)

        # Header: Titulo + Status
        header = QHBoxLayout()
        self.lbl_titulo = QLabel(self.titulo_texto)
        self.lbl_titulo.setObjectName("tituloCard")
        self.lbl_titulo.setWordWrap(True)
        
        self.lbl_status_badge = QLabel("AGUARDANDO")
        self.lbl_status_badge.setObjectName("statusBadge")
        self.lbl_status_badge.setAlignment(Qt.AlignCenter)
        self.lbl_status_badge.setFixedSize(80, 20)
        
        header.addWidget(self.lbl_titulo, stretch=1)
        header.addWidget(self.lbl_status_badge)
        layout.addLayout(header)

        # Info Area
        self.lbl_ultima = QLabel("ULTIMA EXECUÇÃO: -")
        self.lbl_ultima.setObjectName("subtituloCard")
        layout.addWidget(self.lbl_ultima)

        self.lbl_proxima = QLabel("PROXIMA EXECUÇÃO: -")
        self.lbl_proxima.setObjectName("subtituloCard")
        layout.addWidget(self.lbl_proxima)
        
        layout.addStretch(1)

        # Actions
        btns = QHBoxLayout()
        btns.setSpacing(10)
        
        self.btn_executar = QPushButton("PLAY")
        self.btn_executar.setCursor(Qt.PointingHandCursor)
        self.btn_executar.setFixedHeight(30)
        
        self.btn_log = QPushButton("LOG")
        self.btn_log.setCursor(Qt.PointingHandCursor)
        self.btn_log.setFixedWidth(50)
        self.btn_log.setFixedHeight(30)
        
        self.btn_parar = QPushButton("STOP")
        self.btn_parar.setCursor(Qt.PointingHandCursor)
        self.btn_parar.setFixedWidth(50)
        self.btn_parar.setFixedHeight(30)
        self.btn_parar.setVisible(False)

        btns.addWidget(self.btn_executar, stretch=1)
        btns.addWidget(self.btn_log)
        btns.addWidget(self.btn_parar)
        
        layout.addLayout(btns)

        self.definir_status_visual("AGUARDANDO")

    def mouseDoubleClickEvent(self, event):
        self.sig_parar_solicitado.emit(self.titulo_texto)
        super().mouseDoubleClickEvent(event)

    def definir_status_visual(self, status_texto: str):
        p = EstilosGUI.obter_paleta()
        st = (str(status_texto) or "").upper()
        
        self.setStyleSheet(EstilosGUI.estilo_card_netflix())
        
        bg_badge = "#333333"
        fg_badge = "#FFFFFF"
        
        if st == "RODANDO":
            bg_badge = p["azul"]
            fg_badge = "#000000"
        elif st in ["FALHA", "ERRO"]:
            bg_badge = p["destaque"]
        elif st == "SUCESSO":
            bg_badge = p["sucesso"]
            fg_badge = "#000000"
        elif st == "AGENDADO":
            bg_badge = p["amarelo"]
            fg_badge = "#000000"
            
        self.lbl_status_badge.setText(st)
        self.lbl_status_badge.setStyleSheet(f"background-color: {bg_badge}; color: {fg_badge}; border-radius: 2px;")

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
    def __init__(self, titulo, cor_titulo):
        super().__init__()
        self.setObjectName("DashboardBox")
        self.setStyleSheet(EstilosGUI.estilo_dashboard_box(cor_titulo))
        self.setMinimumSize(400, 300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        lbl = QLabel(titulo)
        lbl.setObjectName("tituloBox")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        self.lista = QListWidget()
        self.lista.setAlternatingRowColors(True)
        layout.addWidget(self.lista)

    def atualizar_lista(self, itens_texto):
        smart_update_listwidget(self.lista, itens_texto)

    def add_widget(self, widget):
        self.layout().addWidget(widget)

class LogDialog(QDialog):
    def __init__(self, titulo, conteudo, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Log: {titulo}")
        self.resize(800, 600)
        p = EstilosGUI.obter_paleta()
        self.setStyleSheet(f"background-color: {p['bg_fundo']}; color: {p['branco']};")
        layout = QVBoxLayout(self)
        lbl = QLabel(f"Último Log Disponível - {titulo}")
        lbl.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(lbl)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet(
            f"background-color: {p['bg_card']}; border: 1px solid {p['borda_suave']}; "
            "padding: 10px; font-family: Consolas, monospace;"
        )
        self.text_edit.setText(conteudo)
        layout.addWidget(self.text_edit)
        btn_fechar = QPushButton("FECHAR")
        btn_fechar.setStyleSheet(EstilosGUI.estilo_botao_topo())
        btn_fechar.clicked.connect(self.close)
        layout.addWidget(btn_fechar, alignment=Qt.AlignRight)
