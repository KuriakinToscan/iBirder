class StyleManager:
    # ------------------
    # MÉTRICAS DE DESIGN
    # ------------------
    SPACING_SM = 8
    SPACING_MD = 15
    SPACING_LG = 20
    
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
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 6px 20px 6px 20px;
                color: #2C3E50;
                font-family: 'Segoe UI';
                font-size: 13px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #FEF3C7;
                color: #2C3E50;
            }
            QMenu::separator {
                height: 1px;
                background-color: #E5E7EB;
                margin: 4px 0px 4px 0px;
            }
            #lbl_slogan {
                color: #2C3E50;
                font-size: 44px;
                font-style: italic;
                font-weight: bold;
                font-family: 'Figtree', sans-serif;
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
