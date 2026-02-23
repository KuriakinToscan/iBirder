import sys
import platform
import ctypes
from pathlib import Path

class StyleManager:
    """Centralizador de Estilos e Temas do iBirder (v0.6.4)"""
    
    # Constantes de Design
    SPACING_SM = 8
    SPACING_MD = 12
    SPACING_LG = 20
    
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

        # 2. Paleta Adaptativa
        if dark_mode:
            palette = StyleManager._get_dark_palette()
        else:
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
        from PySide6.QtGui import QPalette, QColor
        palette = QPalette()
        dark_bg = QColor("#1F2937")
        dark_base = QColor("#111827")
        light_text = QColor("#F3F4F6")
        accent = QColor("#3B82F6")
        
        palette.setColor(QPalette.Window, dark_bg)
        palette.setColor(QPalette.WindowText, light_text)
        palette.setColor(QPalette.Base, dark_base)
        palette.setColor(QPalette.AlternateBase, dark_bg)
        palette.setColor(QPalette.ToolTipBase, dark_base)
        palette.setColor(QPalette.ToolTipText, light_text)
        palette.setColor(QPalette.Text, light_text)
        palette.setColor(QPalette.Button, dark_bg)
        palette.setColor(QPalette.ButtonText, light_text)
        palette.setColor(QPalette.Highlight, accent)
        palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        
        # Peças Inativas
        palette.setColor(QPalette.Inactive, QPalette.Window, dark_bg)
        palette.setColor(QPalette.Inactive, QPalette.WindowText, light_text)
        return palette

    @staticmethod
    def is_windows_dark_mode():
        """Alias para detect_dark_mode (Retrocompatibilidade v0.8.2)."""
        return StyleManager.detect_dark_mode()

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
            
            /* Botões Primários */
            QPushButton {{ 
                background-color: {accent_btn}; 
                color: white; 
                border-radius: 8px; 
                padding: 10px 16px; 
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
            QPushButton[class="icon-btn"]:hover {{ background-color: {"#E5E7EB" if not dark_mode else "#4B5563"}; border-radius: 4px; }}
            
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

            /* Menus (Correção v0.6.3) */
            QMenu {{
                background-color: {bg_card} !important;
                border: 1px solid {border} !important;
                border-radius: 6px !important;
                padding: 5px !important;
            }}
            QMenu::item {{
                color: {text_primary} !important;
                padding: 6px 30px !important;
                border-radius: 4px !important;
            }}
            QMenu::item:selected {{
                background-color: {"#F3F4F6" if not dark_mode else "#374151"} !important;
            }}
            QMenu::item:disabled {{ color: #9CA3AF !important; }}
            QMenu::separator {{ height: 1px; background: {border}; margin: 4px 10px; }}

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
            
            /* Overlays de Alerta */
            QFrame#overlay_alert {{
                background-color: {"rgba(254, 243, 199, 0.95)" if not dark_mode else "rgba(69, 26, 3, 0.9)"};
                border: 2px solid #F59E0B; border-radius: 8px;
            }}
            QLabel#alert_text {{ color: {"#92400E" if not dark_mode else "#FDE68A"}; font-size: 12px; font-weight: bold; }}
        """

    @staticmethod
    def setup_window_theme(window):
        """Ajusta a Title Bar via DWM API para combinar com o tema (v0.6.3.1)."""
        if platform.system() != "Windows":
            return
            
        try:
            from ctypes import wintypes
            hwnd = window.winId()
            if hasattr(hwnd, 'id'): hwnd = hwnd.id()
            
            # Garantir tipagem HWND para 64-bit (Prevenir crash silencioso)
            handle = wintypes.HWND(hwnd)
            dark_mode = StyleManager.detect_dark_mode()
            
            # 1. Ativar modo escuro imersivo na barra
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            mode = ctypes.c_int(1 if dark_mode else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                handle, 20, ctypes.byref(mode), ctypes.sizeof(mode)
            )
            
            # 2. Cor da Barra (DWMWA_CAPTION_COLOR = 35)
            # Valor em 0x00RRGGBB (B e R invertidos para BGR)
            bg_color = ctypes.c_int(0x00514137 if not dark_mode else 0x00271811)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                handle, 35, ctypes.byref(bg_color), ctypes.sizeof(bg_color)
            )
            
            # 3. Cor do Texto (DWMWA_TEXT_COLOR = 36)
            text_color = ctypes.c_int(0x00FFFFFF)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                handle, 36, ctypes.byref(text_color), ctypes.sizeof(text_color)
            )
            
        except Exception as e:
            print(f"[STYLE] Erro ao ajustar Title Bar: {e}")
