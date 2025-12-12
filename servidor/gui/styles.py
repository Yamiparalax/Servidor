class EstilosGUI:
    @staticmethod
    def obter_paleta():
        return {
            "bg_fundo": "#202124",       # Google Dark Background
            "bg_card": "#303134",        # Google Dark Surface
            "bg_card_hover": "#3C4043",  # Lighter Surface
            "destaque": "#8AB4F8",       # Google Blue (Light)
            "destaque_hover": "#AECBFA",
            "sucesso": "#81C995",        # Google Green (Light)
            "aviso": "#FDD663",          # Google Yellow (Light)
            "erro": "#F28B82",           # Google Red (Light)
            "branco": "#E8EAED",         # High Emphasis Text
            "texto_sec": "#9AA0A6",      # Medium Emphasis Text
            "borda_suave": "#5F6368",    # Borders
            "azul": "#8AB4F8",           # Secondary Blue
            "amarelo": "#FDD663",
            "verde": "#81C995",
            "vermelho": "#F28B82",
            "roxo": "#C58AF9",           # Google Python Purpleish
        }

    @staticmethod
    def estilo_janela():
        p = EstilosGUI.obter_paleta()
        return f"""
            QMainWindow {{
                background-color: {p['bg_fundo']};
            }}
            QWidget {{
                background-color: {p['bg_fundo']};
                color: {p['branco']};
                font-family: 'Roboto', 'Segoe UI', sans-serif;
            }}
            /* Material Scrollbar */
            QScrollBar:vertical {{
                border: none;
                background: {p['bg_fundo']};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {p['borda_suave']};
                min-height: 30px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {p['texto_sec']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                border: none;
                background: {p['bg_fundo']};
                height: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: {p['borda_suave']};
                min-width: 30px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {p['texto_sec']};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            
            QToolTip {{
                background-color: {p['bg_card_hover']};
                color: {p['branco']};
                border: 1px solid {p['borda_suave']};
                padding: 8px;
                border-radius: 4px;
            }}
            
            /* Sidebar - Navigation Rail Style */
            QListWidget#listaNavegacao {{
                background-color: {p['bg_fundo']};
                border: none;
                padding-top: 20px;
                outline: none;
            }}
            QListWidget#listaNavegacao::item {{
                height: 56px; /* Material standard list item height */
                padding-left: 24px;
                color: {p['texto_sec']};
                border-radius: 0 28px 28px 0; /* Pill shape right */
                margin-right: 16px; 
                font-weight: 500;
                font-size: 14px;
            }}
            QListWidget#listaNavegacao::item:hover {{
                background-color: rgba(138, 180, 248, 0.08); /* Blue Tint */
                color: {p['destaque']};
            }}
            QListWidget#listaNavegacao::item:selected {{
                background-color: rgba(138, 180, 248, 0.16); /* Stronger Blue Tint */
                color: {p['destaque']};
                font-weight: 700;
            }}
        """

    @staticmethod
    def estilo_card_material():
        p = EstilosGUI.obter_paleta()
        return f"""
            QFrame#AutomationCard {{
                background-color: {p['bg_card']};
                border-radius: 16px;
                border: 1px solid {p['borda_suave']};
                margin: 4px;
            }}
            QFrame#AutomationCard:hover {{
                background-color: {p['bg_card_hover']};
                border: 1px solid {p['destaque']};
            }}
            QLabel#cardTitle {{
                color: {p['branco']};
                font-size: 15px;
                font-family: 'Roboto', 'Segoe UI', sans-serif;
                font-weight: 700;
                background-color: transparent;
                letter-spacing: 0.5px;
            }}
            QLabel#cardDetail {{
                color: {p['texto_sec']};
                font-size: 11px;
                font-weight: 500;
                background-color: transparent;
                text-transform: uppercase;
            }}
            QLabel#statusChip {{
                font-size: 10px;
                font-weight: 800;
                padding: 4px 10px;
                border-radius: 10px;
                letter-spacing: 0.5px;
            }}
            QPushButton {{
                background-color: transparent;
                color: {p['destaque']};
                border: 1px solid {p['borda_suave']};
                border-radius: 16px;
                font-weight: 700;
                font-size: 11px;
                padding: 0 16px;
                text-transform: uppercase;
            }}
            QPushButton:hover {{
                background-color: rgba(138, 180, 248, 0.1);
                border: 1px solid {p['destaque']};
                color: {p['destaque_hover']};
            }}
            QPushButton#btnActionMajor {{
                background-color: {p['destaque']};
                color: {p['bg_fundo']};
                border: none;
            }}
            QPushButton#btnActionMajor:hover {{
                background-color: {p['destaque_hover']};
            }}
        """

    @staticmethod
    def estilo_dashboard_box(cor_topo):
        p = EstilosGUI.obter_paleta()
        return f"""
            QFrame#DashboardBox {{
                background-color: {p['bg_card']};
                border-radius: 16px;
                border: 1px solid transparent; 
            }}
            QLabel#tituloBox {{
                color: {cor_topo};
                font-size: 14px;
                font-weight: 700;
                margin-bottom: 16px;
                letter-spacing: 1px;
                background: transparent;
            }}
            QListWidget {{
                background-color: transparent;
                border: none;
                color: {p['branco']};
                font-size: 13px;
                font-weight: 400;
            }}
            QListWidget::item {{
                padding: 12px 0;
                border-bottom: 1px solid {p['borda_suave']};
            }}
            QListWidget::item:last {{
                border-bottom: none;
            }}
            QListWidget::item:hover {{
                background-color: rgba(255, 255, 255, 0.04);
            }}
        """

    @staticmethod
    def estilo_botao_topo():
        p = EstilosGUI.obter_paleta()
        return f"""
            QPushButton {{
                background-color: {p['destaque']};
                color: {p['bg_fundo']};
                border: none;
                border-radius: 20px;
                padding: 10px 24px;
                font-weight: 600;
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background-color: {p['destaque_hover']};
                /* box-shadow not supported in Qt stylesheets natively */
            }}
            QPushButton:pressed {{
                background-color: {p['destaque']};
            }}
        """

    @staticmethod
    def estilo_botao_toggle():
        p = EstilosGUI.obter_paleta()
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {p['texto_sec']};
                border: 1px solid {p['borda_suave']};
                border-radius: 18px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:checked {{
                background-color: rgba(129, 201, 149, 0.16); 
                color: {p['verde']};
                border: 1px solid {p['verde']};
            }}
            QPushButton:hover {{
                border: 1px solid {p['branco']};
            }}
        """
