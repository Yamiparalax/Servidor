class EstilosGUI:
    @staticmethod
    def obter_paleta():
        return {
            "bg_fundo": "#0B0E14",       # Deep Dark Blue (Main Background)
            "bg_card": "#151922",        # Panel/Card Background
            "bg_card_hover": "#1E2330",  # Hover State
            "destaque": "#6C5DD3",       # Primary Purple/Blurple (Curated.Media style)
            "destaque_hover": "#5D5FEF",
            "sucesso": "#00FF94",        # Neon Green
            "aviso": "#FFB039",          # Orange
            "erro": "#FF4C4C",           # Red
            "branco": "#FFFFFF",
            "texto_sec": "#8F95B2",      # Blue-ish Gray
            "borda_suave": "#2D3246",    # Separators
            "azul": "#3F8CFF",           # Secondary Blue
            "amarelo": "#FFB039",
            "verde": "#00FF94",
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
                font-family: 'Montserrat', 'Segoe UI', sans-serif;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {p['bg_fundo']};
                width: 8px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {p['borda_suave']};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                border: none;
                background: {p['bg_fundo']};
                height: 8px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: {p['borda_suave']};
                min-width: 20px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QToolTip {{
                background-color: {p['bg_card']};
                color: {p['branco']};
                border: 1px solid {p['borda_suave']};
                padding: 5px;
            }}
            /* Sidebar List */
            QListWidget#listaNavegacao {{
                background-color: {p['bg_card']};
                border: none;
                border-right: 1px solid {p['borda_suave']};
                outline: none;
                padding-top: 30px;
            }}
            QListWidget#listaNavegacao::item {{
                height: 60px;
                padding-left: 25px;
                color: {p['texto_sec']};
                border-left: 3px solid transparent;
                margin-bottom: 4px;
                font-weight: 600;
                font-size: 13px;
                /* Transition effort via style sheet is limited in Qt, but we can tune colors */
            }}
            QListWidget#listaNavegacao::item:hover {{
                background-color: {p['bg_card_hover']};
                color: {p['branco']};
                border-left: 3px solid {p['texto_sec']};
            }}
            QListWidget#listaNavegacao::item:selected {{
                background-color: rgba(108, 93, 211, 0.10); /* Subtle Purple Tint */
                color: {p['branco']};
                border-left: 3px solid {p['destaque']};
                font-weight: 800;
            }}
        """

    @staticmethod
    def estilo_card_netflix():
        p = EstilosGUI.obter_paleta()
        return f"""
            QFrame#cardNetflix {{
                background-color: {p['bg_card']};
                border-radius: 12px;
                border: 1px solid {p['borda_suave']};
            }}
            QFrame#cardNetflix:hover {{
                background-color: {p['bg_card_hover']};
                border: 1px solid {p['destaque']}; 
                /* Simulation of a glow could be done with more complex border logic if needed */
            }}
            QLabel#tituloCard {{
                color: {p['branco']};
                font-size: 15px;
                font-weight: 800;
                background-color: transparent;
                letter-spacing: 0.5px;
            }}
            QLabel#subtituloCard {{
                color: {p['texto_sec']};
                font-size: 11px;
                font-weight: 500;
                background-color: transparent;
            }}
            QLabel#statusBadge {{
                font-size: 10px;
                font-weight: 800;
                padding: 4px 8px;
                border-radius: 4px;
            }}
            QPushButton {{
                background-color: {p['destaque']};
                color: {p['branco']};
                border: none;
                border-radius: 6px;
                font-weight: 700;
                font-size: 11px;
                text-transform: uppercase;
            }}
            QPushButton:hover {{
                background-color: {p['destaque_hover']};
            }}
            QPushButton:disabled {{
                background-color: {p['borda_suave']};
                color: {p['texto_sec']};
            }}
        """

    @staticmethod
    def estilo_dashboard_box(cor_topo):
        p = EstilosGUI.obter_paleta()
        return f"""
            QFrame#DashboardBox {{
                background-color: {p['bg_card']};
                border-radius: 16px;
                border: 1px solid {p['borda_suave']};
            }}
            QLabel#tituloBox {{
                color: {cor_topo};
                font-size: 14px;
                font-weight: 900;
                margin-bottom: 10px;
                text-transform: uppercase;
            }}
            QListWidget {{
                background-color: transparent;
                border: none;
                color: {p['texto_sec']};
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 5px;
                border-bottom: 1px solid {p['borda_suave']};
            }}
            QListWidget::item:selected {{
                background-color: {p['amarelo']};
                color: #000000;
                border-radius: 4px;
            }}
            QListWidget::item:hover {{
                background-color: {p['bg_card_hover']};
                color: {p['branco']};
            }}
        """

    @staticmethod
    def estilo_botao_topo():
        p = EstilosGUI.obter_paleta()
        return f"""
            QPushButton {{
                background-color: {p['destaque']};
                color: {p['branco']};
                border: none;
                border-radius: 10px;
                padding: 8px 16px;
                font-weight: 700;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {p['destaque_hover']};
            }}
            QPushButton:pressed {{
                background-color: {p['bg_card']};
            }}
        """

    @staticmethod
    def estilo_botao_toggle():
        p = EstilosGUI.obter_paleta()
        return f"""
            QPushButton {{
                background-color: {p['bg_card']};
                color: {p['texto_sec']};
                border: 1px solid {p['borda_suave']};
                border-radius: 10px;
                padding: 8px 16px;
                font-weight: 700;
                font-size: 11px;
            }}
            QPushButton:checked {{
                background-color: {p['sucesso']};
                color: #000000;
                border: 1px solid {p['sucesso']};
            }}
            QPushButton:hover {{
                border: 1px solid {p['branco']};
            }}
        """
