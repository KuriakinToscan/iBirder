class StyleManager:
    # ------------------
    # MÉTRICAS DE DESIGN
    # ------------------
    SPACING_SM = 8
    SPACING_MD = 15
    SPACING_LG = 20
    
    @staticmethod
    def apply_theme(app):
        """Aplica o tema unificado (Paleta + CSS + Tradução) ao QApplication."""
        from PySide6.QtGui import QPalette, QColor
        from PySide6.QtCore import QLibraryInfo, QTranslator, QLocale
        import os

        # 1. Configurar Estilo Base
        app.setStyle("Fusion")

        # 2. Forçar QPalette Clara (Garante cores de sistema consistentes)
        palette = QPalette()
        white = QColor("#FFFFFF")
        off_white = QColor("#F8F9FA")
        gray_text = QColor("#374151")
        border_gray = QColor("#D1D5DB")
        highlight = QColor("#F3F4F6")

        palette.setColor(QPalette.Window, off_white) # Volta a ser claro para menus brancos
        palette.setColor(QPalette.WindowText, gray_text)
        palette.setColor(QPalette.Base, white)
        palette.setColor(QPalette.AlternateBase, off_white)
        palette.setColor(QPalette.ToolTipBase, white)
        palette.setColor(QPalette.ToolTipText, gray_text)
        palette.setColor(QPalette.Text, gray_text)
        palette.setColor(QPalette.Button, white)
        palette.setColor(QPalette.ButtonText, gray_text)
        palette.setColor(QPalette.BrightText, white)
        palette.setColor(QPalette.Link, QColor("#3B82F6"))
        palette.setColor(QPalette.Highlight, highlight)
        palette.setColor(QPalette.HighlightedText, QColor("#111827"))
        
        # Desabilitados
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#9CA3AF"))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#9CA3AF"))
        palette.setColor(QPalette.Disabled, QPalette.Window, off_white)

        app.setPalette(palette)
        
        # 3. Garantir que a Janela Principal e outros widgets escutam apenas esta paleta (v0.6.8)
        # Em alguns OS, o Qt herda do sistema. O StyleManager agora centraliza isso.
        
        # 4. Injetar Tradução do Qt (Menus Padrão: Copy/Paste/Undo)
        path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
        translator = QTranslator(app)
        if translator.load(QLocale("pt_BR"), "qtbase", "_", path):
            app.installTranslator(translator)
            # Guardamos para evitar que o GC limpe o tradutor
            app._translator = translator

        # 4. Aplicar Stylesheet Global
        app.setStyleSheet(StyleManager.get_global_stylesheet())

    @staticmethod
    def get_global_stylesheet():
        return """
            QDialog {
                background-color: #F8F9FA;
            }
            QLabel {
                color: #374151;
                font-family: 'Segoe UI';
                font-size: 13px;
            }
            QLineEdit, QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px;
                color: #374151;
                font-family: 'Segoe UI';
                font-size: 13px;
            }
            QCheckBox {
                color: #374151;
                font-family: 'Segoe UI';
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background-color: #374151;
                border: 1px solid #374151;
                image: url(none); /* Opcional: SVG interno do QT lida s/ SVG */
            }
            QPushButton {
                background-color: #374151;
                color: white;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-family: 'Segoe UI';
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1F2937;
            }
            QPushButton.secundario {
                background-color: #F3F4F6;
                color: #374151;
                border: 1px solid #D1D5DB;
            }
            QPushButton.secundario:hover {
                background-color: #E5E7EB;
                color: #111827;
                border-color: #9CA3AF;
            }
            QMenu {
                background-color: #FFFFFF !important;
                border: 1px solid #D1D5DB !important;
                border-radius: 6px !important;
                padding: 5px !important;
            }
            QMenu::item {
                background-color: transparent !important;
                padding: 6px 30px 6px 30px !important;
                color: #374151 !important; /* Cinza escuro padrão v0.7.5 */
                font-family: 'Segoe UI' !important;
                font-weight: 600 !important;
                font-size: 13px !important;
                border-radius: 4px !important;
                margin: 1px 0px !important;
            }
            QMenu::item:selected {
                background-color: #F3F4F6 !important;
                color: #111827 !important;
            }
            QMenu::item:disabled {
                color: #9CA3AF !important;
                background-color: transparent !important;
            }
            QMenu::separator {
                height: 1px !important;
                background-color: #E5E7EB !important;
                margin: 5px 10px !important;
            }
            QMenu::right-arrow {
                image: none; /* Simplificação visual premium */
            }
            #lbl_slogan {
                color: #2C3E50;
                font-size: 32px;
                font-style: italic;
                font-weight: normal;
                font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
            }
            /* Classes Abstratas Injetadas na Fase S */
            .lbl-titulo-sessao {
                font-weight: bold; 
                color: #374151; 
                font-size: 11px; 
            }
            .lbl-titulo-sessao[margin-bottom="sm"] {
                margin-bottom: 2px;
            }
            .lbl-titulo-sessao[margin-bottom="md"] {
                margin-bottom: 4px;
            }
            .lbl-titulo-sessao[margin-top="md"] {
                margin-top: 8px;
            }
            .lbl-titulo-verde {
                font-weight: bold; 
                color: #059669; 
                font-size: 11px; 
                text-transform: uppercase;
            }
            .container-borda-cinza {
                background: transparent; 
                border: 1px solid #D1D5DB; 
                border-radius: 6px; 
                padding: 4px; 
                color: #374151; 
                font-style: italic;
            }
            .lbl-confianca-alta {
                color: #059669; /* Verde */
            }
            .container-borda-cinza-fill {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 6px;
                color: #374151;
                font-size: 12px;
            }
            .grupo-sessao-inferior {
                margin-top: 10px;
                padding-top: 10px;
            }
            .container-borda-tracejada {
                color: #9CA3AF;
                font-style: italic;
                border: 1px dashed #D1D5DB;
                border-radius: 4px;
                padding: 20px;
            }
            QPushButton[class="btn-fechar-modal"] {
                background-color: rgba(255, 255, 255, 0.75);
                color: #374151;
                font-weight: bold;
                font-family: "Segoe UI", sans-serif;
                font-size: 18px;
                border-radius: 16px;
                border: none;
                padding: 0px;
            }
            QPushButton[class="btn-fechar-modal"]:hover {
                background-color: rgba(255, 255, 255, 0.95);
                color: #EF4444; 
            }
            .alert-nudge {
                background-color: #FEF3C7;
                border: 1px solid #FDE68A;
                border-radius: 6px;
                color: #92400E;
                font-weight: bold;
                padding: 10px;
                text-align: center;
            }
            .alert-nudge:hover {
                background-color: #FDE68A;
            }
            .input-success {
                border: 2px solid #10B981;
            }
        """

    @staticmethod
    def is_windows_dark_mode() -> bool:
        import winreg
        try:
            registry_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                0,
                winreg.KEY_READ
            )
            value, _ = winreg.QueryValueEx(registry_key, "AppsUseLightTheme")
            winreg.CloseKey(registry_key)
            return value == 0
        except OSError:
            return False # Default to false if registry not found

    @staticmethod
    def setup_window_theme(window):
        """Reforça a Title Bar escura via DWM API (Apenas Windows 10/11 v0.7.2)."""
        import platform
        import ctypes
        
        if platform.system() != "Windows":
            return
            
        try:
            hwnd = window.winId()
            
            # 1. Pintar o fundo da Barra (DWMWA_CAPTION_COLOR = 35)
            # Valor em 0x00RRGGBB (Python int format)
            # Cor: #374151 -> R:37(55), G:41(65), B:51(81)
            # Nota: Windows usa BGR internamente: 0x00514137
            color_background = 0x00514137
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 35, ctypes.byref(ctypes.c_int(color_background)), 4
            )
            
            # 2. Pintar o texto da Barra (DWMWA_TEXT_COLOR = 36)
            # Cor: Branco (0x00FFFFFF)
            color_text = 0x00FFFFFF
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 36, ctypes.byref(ctypes.c_int(color_text)), 4
            )
            
        except Exception as e:
            print(f"[STYLE] Erro ao pintar Title Bar Seletiva: {e}")
