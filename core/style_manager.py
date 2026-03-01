import sys
import platform
import ctypes
from pathlib import Path

class StyleManager:
    """Centralizador de Estilos e Temas do iBirder (v0.6.6)"""
    
    # Constantes de Design
    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 12
    SPACING_LG = 20
    
    @staticmethod
    def apply_shadow(widget, blur=20, offset=(0, 5), color=(0, 0, 0, 20)):
        """Aplica um efeito de sombra suave a um widget (v1.6.15)."""
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        sombra = QGraphicsDropShadowEffect()
        sombra.setBlurRadius(blur)
        sombra.setOffset(*offset)
        sombra.setColor(QColor(*color))
        widget.setGraphicsEffect(sombra)

    _last_mode = None # Cache do último tema aplicado

    @staticmethod
    def apply_theme(app, dark_mode=False):
        """Aplica o tema adaptativo (Paleta + CSS + Tradução) ao QApplication."""
        if StyleManager._last_mode == dark_mode:
            return # Evita re-aplicação redundante e loops de eventos
            
        from PySide6.QtGui import QPalette, QColor
        from PySide6.QtCore import QLibraryInfo, QTranslator, QLocale
        
        # 1. Configurar Estilo Base (Apenas na primeira vez ou se necessário)
        if StyleManager._last_mode is None:
            app.setStyle("Fusion")

        # 2. Paleta Soberana (Apenas Off-White v0.6.6)
        # O aplicativo ignora o modo escuro interno para manter a estética Off-White Premium.
        # O Dark Mode do sistema afetará apenas a Title Bar através do DWM API.
        palette = StyleManager._get_light_palette()
        app.setPalette(palette)
        
        # 3. Injetar Tradução do Qt
        if not hasattr(app, "_translator"):
            path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
            translator = QTranslator(app)
            if translator.load(QLocale("pt_BR"), "qtbase", "_", path):
                app.installTranslator(translator)
                app._translator = translator

        # 4. Aplicar Stylesheet Global Adaptativo
        app.setStyleSheet(StyleManager.get_global_stylesheet(dark_mode))
        StyleManager._last_mode = dark_mode

    @staticmethod
    def _get_light_palette():
        from PySide6.QtGui import QPalette, QColor
        palette = QPalette()
        off_white = QColor("#F0F2F5")
        pure_white = QColor("#FFFFFF")
        gray_text = QColor("#374151")
        dark_text = QColor("#1F2937")
        highlight = QColor("#F3F4F6")
        
        palette.setColor(QPalette.Window, off_white)
        palette.setColor(QPalette.WindowText, dark_text)
        palette.setColor(QPalette.Base, pure_white)
        palette.setColor(QPalette.AlternateBase, off_white)
        palette.setColor(QPalette.Text, gray_text)
        palette.setColor(QPalette.Button, pure_white)
        palette.setColor(QPalette.ButtonText, gray_text)
        palette.setColor(QPalette.Highlight, highlight)
        palette.setColor(QPalette.HighlightedText, QColor("#111827"))
        
        # Blindagem Inativa
        palette.setColor(QPalette.Inactive, QPalette.Window, off_white)
        palette.setColor(QPalette.Inactive, QPalette.WindowText, dark_text)
        return palette

    @staticmethod
    def _get_dark_palette():
        """Alias para _get_light_palette para garantir soberania Off-White."""
        return StyleManager._get_light_palette()

    @staticmethod
    def is_windows_dark_mode():
        """Alias para detect_dark_mode (Retrocompatibilidade v0.8.2)."""
        return StyleManager.detect_dark_mode()

    @staticmethod
    def get_app_icon_name(dark_mode=None):
        """Retorna o nome do ícone baseado no tema (v0.6.5)."""
        if dark_mode is None:
            dark_mode = StyleManager.detect_dark_mode()
        return "logo_ave_claro.svg" if dark_mode else "logo_ave_escuro.svg"

    @staticmethod
    def set_app_icon(window, dark_mode=None):
        """Aplica o ícone correto à janela conforme o tema (v0.6.5)."""
        from PySide6.QtGui import QIcon
        from PySide6.QtCore import QSize
        import os
        import sys
        
        if dark_mode is None:
            dark_mode = StyleManager.detect_dark_mode()
            
        icon_name = StyleManager.get_app_icon_name(dark_mode)
        
        # Obter caminho (Adaptado da JanelaPrincipal)
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent / 'assets'
            
        caminho_svg = str(base_path / icon_name)
        caminho_ico = str(base_path / "logo_ave.ico")
        
        icone = QIcon()
        if os.path.exists(caminho_svg):
            icone.addFile(caminho_svg)
        if os.path.exists(caminho_ico):
            icone.addFile(caminho_ico) # Fallback para Titlebar
            
        if not icone.isNull():
            window.setWindowIcon(icone)

    @staticmethod
    def detect_dark_mode():
        """Detecta se o Windows está em modo escuro."""
        if platform.system() != "Windows":
            return False
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
            return False

    @staticmethod
    def get_global_stylesheet(dark_mode=False):
        """Retorna o CSS unificado: Estética Off-White (v0.8.1)."""
        # ESTÉTICA SOBERANA: Mantemos o Off-White/Branco por padrão no corpo
        # A detecção de tema afetará principalmente os Menus e detalhes sutis
        bg_app = "#F0F2F5"
        bg_card = "#FFFFFF"
        text_primary = "#1F2937"
        text_secondary = "#4B5563"
        border = "#D1D5DB"
        accent_btn = "#374151"
        accent_hover = "#1F2937"

        # Cores para o campo de Input de Nome Científico (Biologia v0.8.1)
        # Usamos uma classe específica para o itálico biológico
        
        return f"""
            QMainWindow {{ background-color: {bg_app}; }}
            QDialog {{ background-color: {bg_app}; }}
            
            QFrame.painel {{ 
                background-color: {bg_card}; 
                border-radius: 12px; 
                border: 1px solid {border}; 
            }}
            
            QLabel {{ color: {text_primary}; font-family: 'Segoe UI'; font-size: 13px; }}
            
            #lbl_slogan {{
                font-size: 26px;
                font-style: italic;
                font-weight: 500;
                color: {text_primary};
            }}
            
            /* Nome Científico: Formatação Biológica Rigorosa */
            QLineEdit.sci-name-input {{
                font-family: 'Segoe UI';
                font-style: italic;
                font-weight: 500;
                color: #1F2937;
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px;
            }}
            
            QLineEdit, QTextEdit {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px;
                color: {text_primary};
            }}

            QLineEdit::placeholder, QTextEdit::placeholder {{
                color: #9CA3AF;
                font-style: italic;
            }}

            .lbl-placeholder {{
                color: #9CA3AF;
                font-style: italic;
                font-weight: 500;
                font-size: 13px;
            }}
            
            QListWidget, QListView {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 8px;
                color: {text_primary};
                outline: none;
                padding: 4px;
            }}
            QListWidget::item, QListView::item {{
                padding: 8px;
                border-radius: 6px;
                color: {text_primary};
            }}
            QListWidget::item:hover, QListView::item:hover {{
                background-color: #F3F4F6;
            }}
            QListWidget::item:selected, QListView::item:selected {{
                background-color: #E5E7EB;
                color: {text_primary};
            }}

            /* ScrollArea e ScrollBars (v0.6.6) */
            QScrollArea {{ border: none; background-color: transparent; }}
            
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #D1D5DB;
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            
            /* Botões Primários (Padrão Extra-Slim 26px) */
            QPushButton {{ 
                background-color: {accent_btn}; 
                color: white; 
                border-radius: 8px; 
                padding: 2px 16px; 
                min-height: 26px;
                max-height: 26px;
                font-weight: bold; 
                font-family: 'Segoe UI';
            }}
            QPushButton:hover {{ background-color: {accent_hover}; }}
            
            /* Botões Secundários */
            QPushButton.secundario {{
                background-color: #E5E7EB;
                color: #374151;
                border: 1px solid #D1D5DB;
            }}
            QPushButton.secundario:hover {{ background-color: #D1D5DB; }}
            
            /* Botões Ícone */
            QPushButton[class="icon-btn"] {{ background-color: transparent; color: {text_secondary}; padding: 4px; border: none; }}
            QPushButton[class="icon-btn"]:hover {{ background-color: #E5E7EB; border-radius: 4px; }}
            
            /* Botões de Link */
            QPushButton.btn-link {{
                 background: transparent;
                 color: #3B82F6;
                 text-decoration: underline;
                 border: none;
                 font-size: 11px;
                 padding: 0px;
                 text-align: left;
            }}
            QPushButton.btn-link:hover {{ color: #2563EB; }}

            /* Menus (Harmonização v0.6.7+ - Blindagem 2.0) */
            QMenu {{
                background-color: #FFFFFF !important;
                border: 1px solid #D1D5DB !important;
                border-radius: 8px !important;
                padding: 6px !important;
            }}
            QMenu::item {{
                background-color: transparent !important;
                color: #1F2937 !important;
                padding: 8px 32px 8px 12px !important;
                border-radius: 6px !important;
                margin: 2px 4px !important;
            }}
            QMenu::item:selected {{
                background-color: #F3F4F6 !important;
                color: #1F2937 !important;
            }}
            QMenu::item:disabled {{ 
                color: #9CA3AF !important; 
                background-color: transparent !important;
            }}
            QMenu::separator {{ 
                height: 1px; 
                background: #E5E7EB; 
                margin: 6px 10px; 
            }}
            QMenu::icon {{
                margin-left: 8px;
            }}

            /* GroupBox */
            QGroupBox {{ 
                border: 1px solid {border}; 
                border-radius: 8px; 
                margin-top: 12px; 
                padding-top: 12px; 
                font-weight: bold; 
                font-size: 11px; 
                background-color: {bg_card}; 
                color: {text_secondary}; 
                text-transform: uppercase; 
            }}
            QGroupBox::title {{ 
                background-color: {bg_card}; 
                color: {text_primary};
            }}

            /* Checkbox e RadioButton (Visibilidade v0.8.3) */
            QCheckBox, QRadioButton {{
                color: {text_primary};
                spacing: 8px;
            }}
            QCheckBox::indicator, QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {border};
                border-radius: 4px;
                background-color: white;
            }}
            QCheckBox::indicator:checked {{
                background-color: {accent_btn};
                image: url(none); /* Pode ser substituído por um SVG check se carregado */
            }}
            /* Fallback visual simples para checked se não houver asset */
            QCheckBox::indicator:checked {{ background-color: #374151; }}

            /* Classes Abstratas para Widgets Customizados */
            .lbl-titulo-sessao {{ font-weight: bold; color: {text_secondary}; font-size: 11px; }}
            .container-borda-cinza {{ border: 1px solid {border}; border-radius: 6px; padding: 4px; color: {text_primary}; }}
            .container-borda-cinza-fill {{ background-color: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 6px; padding: 6px; color: #1F2937; font-size: 11px; }}
            
            /* Botão Fechar Modal (Lightbox) */
            QPushButton.btn-fechar-modal {{
                background-color: transparent;
                color: #374151;
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding: 0px;
                border-radius: 16px;
            }}
            QPushButton.btn-fechar-modal:hover {{
                background-color: #F3F4F6;
                color: #1F2937;
            }}
            
            /* Overlays de Alerta */
            QFrame#overlay_alert {{
                background-color: {"rgba(254, 243, 199, 0.95)" if not dark_mode else "rgba(69, 26, 3, 0.9)"};
                border: 2px solid #F59E0B; border-radius: 8px;
            }}
            QLabel#alert_text {{ color: {"#92400E" if not dark_mode else "#FDE68A"}; font-size: 12px; font-weight: bold; }}
        """

    @staticmethod
    def setup_window_theme(window, force_dark=True):
        """
        Ajusta a Title Bar via DWM API para combinar com o tema (v0.8.0).
        Utiliza Immersive Dark Mode e Força Refresh de Frame (SWP_FRAMECHANGED).
        """
        if platform.system() != "Windows":
            return
            
        try:
            from ctypes import wintypes
            import ctypes
            
            hwnd = window.winId()
            if hasattr(hwnd, 'id'): hwnd = hwnd.id()
            
            handle = wintypes.HWND(hwnd)
            dark_mode = StyleManager.detect_dark_mode()
            
            is_dark = 1 if (dark_mode or force_dark) else 0
            mode = ctypes.c_int(is_dark)
            
            # 1. Ativar modo escuro imersivo (Compatibilidade Win10/11)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(handle, 19, ctypes.byref(mode), ctypes.sizeof(mode))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(handle, 20, ctypes.byref(mode), ctypes.sizeof(mode))
            
            # 2. Cor da Barra e Texto (v0.8.0: Re-introduzidos para consistência visual)
            # DWMWA_CAPTION_COLOR = 35, DWMWA_TEXT_COLOR = 36
            # iBirder Dark Gray: #374151 -> BGR: 0x00514137
            bg_color = ctypes.c_int(0x00514137)
            text_color = ctypes.c_int(0x00FFFFFF)
            
            ctypes.windll.dwmapi.DwmSetWindowAttribute(handle, 35, ctypes.byref(bg_color), ctypes.sizeof(bg_color))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(handle, 36, ctypes.byref(text_color), ctypes.sizeof(text_color))
            
            # 3. FORÇA REFRESH DE FRAME (CRÍTICO v0.8.0)
            # Isso força o Windows 11 a re-calcular a área dos botões (Min/Max/Close)
            # SWP_FRAMECHANGED = 0x0020, SWP_NOMOVE = 0x0002, SWP_NOSIZE = 0x0001, SWP_NOZORDER = 0x0004
            ctypes.windll.user32.SetWindowPos(handle, 0, 0, 0, 0, 0, 0x0020 | 0x0002 | 0x0001 | 0x0004 | 0x0010)
            
        except Exception as e:
            print(f"[STYLE] Erro ao ajustar Title Bar: {e}")
