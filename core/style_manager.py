#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#
#  Este programa é um software livre: você pode redistribuí-lo e/ou
#  modificá-lo sob os termos da Licença Pública Geral GNU conforme
#  publicada pela Free Software Foundation, tanto a versão 3 da
#  Licença, como (a seu critério) qualquer versão posterior.
#
#  Este programa é distribuído na esperança de que possa ser útil,
#  mas SEM NENHUMA GARANTIA; sem uma garantia implícita de
#  ADEQUAÇÃO A QUALQUER MERCADO OU APLICAÇÃO EM PARTICULAR.
#  Veja a Licença Pública Geral GNU para mais detalhes.
#
#  Você deve ter recebido uma cópia da Licença Pública Geral GNU
#  junto com este programa. Se não, veja <https://www.gnu.org/licenses/>.

from pathlib import Path
import logging
import platform

from core.temas import TEMAS, TEMA_PADRAO, obter_tema, renderizar, barra_titulo_escura, cor_bgr

# Propriedades dinâmicas que guardam o modelo (com var(--token)) de um widget,
# para renderizá-lo de novo quando o tema muda
_PROP_QSS = "_ibirder_qss"
_PROP_HTML = "_ibirder_html"
_PROP_HTML_RENDER = "_ibirder_html_render"

# Fontes embarcadas em assets/ (registradas uma vez, antes do primeiro tema)
_FONTES_EMBARCADAS = ("Figtree-VariableFont_wght.ttf",)


def _caminho_assets():
    from core.paths import APP_DIR
    return APP_DIR / "assets"


class _Notificador:
    """Cria sob demanda o QObject que emite tema_alterado (evita QObject antes do QApplication)."""
    _instancia = None

    @classmethod
    def obter(cls):
        if cls._instancia is None:
            from PySide6.QtCore import QObject, Signal

            class _Sinais(QObject):
                tema_alterado = Signal(str)

            cls._instancia = _Sinais()
        return cls._instancia


class StyleManager:
    """Centralizador de Estilos e Temas do iBirder (v1.4: temas por tokens)."""

    # Constantes de Design
    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 12
    SPACING_LG = 20

    _tema = obter_tema(TEMA_PADRAO)
    _tema_aplicado = None  # id do último tema aplicado ao QApplication
    _fontes_registradas = False

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

    # --- Tema ativo -------------------------------------------------------

    @staticmethod
    def tema_atual():
        return StyleManager._tema

    @staticmethod
    def cor(token):
        """Valor de um token do tema ativo (ex.: StyleManager.cor("destaque") -> "#374151")."""
        return StyleManager._tema[token]

    @staticmethod
    def qcor(token):
        from PySide6.QtGui import QColor
        return QColor(StyleManager._tema[token])

    @staticmethod
    def render(texto):
        """Renderiza um QSS ou HTML escrito com var(--token) para o tema ativo."""
        return renderizar(texto, StyleManager._tema)

    @staticmethod
    def sinal_tema_alterado():
        """Sinal emitido (com o id do tema) depois que um tema novo é aplicado."""
        return _Notificador.obter().tema_alterado

    @staticmethod
    def estilizar(widget, modelo_qss):
        """setStyleSheet com tokens; o widget é reestilizado sozinho quando o tema muda."""
        widget.setProperty(_PROP_QSS, modelo_qss)
        widget.setStyleSheet(StyleManager.render(modelo_qss))

    @staticmethod
    def definir_texto(rotulo, modelo_html):
        """setText de rótulo com HTML e tokens; o texto é renderizado de novo quando o tema muda."""
        texto = StyleManager.render(modelo_html)
        rotulo.setProperty(_PROP_HTML, modelo_html)
        rotulo.setProperty(_PROP_HTML_RENDER, texto)
        rotulo.setText(texto)

    @staticmethod
    def caminho_logo():
        """Logo do painel para o tema ativo (o original, recolorido); cai no original se faltar."""
        base = _caminho_assets()
        caminho = base / StyleManager._tema.logo
        if not caminho.exists():
            caminho = base / "logo_ave.svg"
        return str(caminho)

    @staticmethod
    def _registrar_fontes():
        if StyleManager._fontes_registradas:
            return
        from PySide6.QtGui import QFontDatabase
        for nome in _FONTES_EMBARCADAS:
            caminho = _caminho_assets() / nome
            if caminho.exists() and QFontDatabase.addApplicationFont(str(caminho)) < 0:
                logging.warning(f"Fonte não carregada: {caminho}")
        StyleManager._fontes_registradas = True

    @staticmethod
    def apply_theme(app, tema=None, dark_mode=None, forcar=False):
        """
        Aplica o tema (Paleta + CSS + Tradução) ao QApplication.
        tema: id em core.temas.TEMAS; None = o salvo em config.json (ou Off-White).
        dark_mode: mantido por compatibilidade; o modo escuro do Windows só afeta a barra
        de título quando o próprio tema pede barra escura.
        """
        if tema is None:
            from core.config import carregar_config
            tema = carregar_config().get("tema") or TEMA_PADRAO
        novo = obter_tema(tema)
        if StyleManager._tema_aplicado == novo.id and not forcar:
            return  # Evita re-aplicação redundante e loops de eventos (changeEvent da janela)

        from PySide6.QtGui import QFont
        from PySide6.QtCore import QLibraryInfo, QTranslator, QLocale

        primeira_vez = StyleManager._tema_aplicado is None
        StyleManager._tema = novo
        StyleManager._tema_aplicado = novo.id

        if primeira_vez:
            app.setStyle("Fusion")
            StyleManager._registrar_fontes()

        app.setPalette(StyleManager._get_palette())
        app.setFont(QFont(novo["fonte"], 10))

        # Tradução do Qt
        if not hasattr(app, "_translator"):
            path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
            translator = QTranslator(app)
            if translator.load(QLocale("pt_BR"), "qtbase", "_", path):
                app.installTranslator(translator)
                app._translator = translator

        app.setStyleSheet(StyleManager.get_global_stylesheet())

        if not primeira_vez:
            StyleManager._reestilizar_widgets(app)
        logging.info(f"Tema aplicado: {novo.nome}")
        StyleManager.sinal_tema_alterado().emit(novo.id)

    @staticmethod
    def _reestilizar_widgets(app):
        """Renderiza de novo os estilos e textos com tokens e redesenha tudo (troca sem reiniciar)."""
        for w in app.allWidgets():
            modelo = w.property(_PROP_QSS)
            if modelo:
                w.setStyleSheet(StyleManager.render(modelo))
            modelo = w.property(_PROP_HTML)
            # Só se o texto não foi trocado depois por um setText comum
            if modelo and hasattr(w, "text") and w.text() == w.property(_PROP_HTML_RENDER):
                StyleManager.definir_texto(w, modelo)
            w.update()
        for janela in app.topLevelWidgets():
            if janela.isWindow() and janela.isVisible():
                StyleManager.setup_window_theme(janela)

    @staticmethod
    def _get_palette():
        from PySide6.QtGui import QPalette, QColor
        t = StyleManager._tema
        palette = QPalette()
        fundo = QColor(t["fundo"])
        superficie = QColor(t["superficie"])
        texto = QColor(t["texto"])

        palette.setColor(QPalette.Window, fundo)
        palette.setColor(QPalette.WindowText, texto)
        palette.setColor(QPalette.Base, superficie)
        palette.setColor(QPalette.AlternateBase, QColor(t["superficie_alt"]))
        palette.setColor(QPalette.Text, texto)
        palette.setColor(QPalette.Button, superficie)
        palette.setColor(QPalette.ButtonText, texto)
        palette.setColor(QPalette.Highlight, QColor(t["selecao"]))
        palette.setColor(QPalette.HighlightedText, texto)
        palette.setColor(QPalette.PlaceholderText, QColor(t["texto_suave"]))
        palette.setColor(QPalette.Link, QColor(t["link"]))
        palette.setColor(QPalette.ToolTipBase, superficie)
        palette.setColor(QPalette.ToolTipText, texto)

        # Blindagem Inativa
        palette.setColor(QPalette.Inactive, QPalette.Window, fundo)
        palette.setColor(QPalette.Inactive, QPalette.WindowText, texto)
        return palette

    # Compatibilidade com chamadas antigas
    @staticmethod
    def _get_light_palette():
        return StyleManager._get_palette()

    @staticmethod
    def _get_dark_palette():
        return StyleManager._get_palette()

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
        """Retorna o CSS unificado do tema ativo (dark_mode mantido só por compatibilidade)."""
        return StyleManager.render(QSS_GLOBAL)

    @staticmethod
    def setup_window_theme(window, force_dark=None):
        """
        Ajusta a Title Bar via DWM API com as cores do tema ativo (v1.4).
        Utiliza Immersive Dark Mode e Força Refresh de Frame (SWP_FRAMECHANGED).
        force_dark: mantido por compatibilidade; quem decide é o tema (barra clara ou escura).
        """
        if platform.system() != "Windows":
            return

        try:
            from ctypes import wintypes
            import ctypes

            hwnd = window.winId()
            if hasattr(hwnd, 'id'): hwnd = hwnd.id()

            handle = wintypes.HWND(hwnd)
            tema = StyleManager._tema

            mode = ctypes.c_int(1 if barra_titulo_escura(tema) else 0)

            # 1. Modo escuro imersivo (Compatibilidade Win10/11): define a cor dos botões Min/Max/Close
            ctypes.windll.dwmapi.DwmSetWindowAttribute(handle, 19, ctypes.byref(mode), ctypes.sizeof(mode))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(handle, 20, ctypes.byref(mode), ctypes.sizeof(mode))

            # 2. Cor da Barra e Texto (Windows 11). DWMWA_CAPTION_COLOR = 35, DWMWA_TEXT_COLOR = 36
            bg_color = ctypes.c_int(cor_bgr(tema["barra_titulo"]))
            text_color = ctypes.c_int(cor_bgr(tema["texto_barra_titulo"]))

            ctypes.windll.dwmapi.DwmSetWindowAttribute(handle, 35, ctypes.byref(bg_color), ctypes.sizeof(bg_color))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(handle, 36, ctypes.byref(text_color), ctypes.sizeof(text_color))

            # 3. FORÇA REFRESH DE FRAME (CRÍTICO v0.8.0)
            # Isso força o Windows 11 a re-calcular a área dos botões (Min/Max/Close)
            # SWP_FRAMECHANGED = 0x0020, SWP_NOMOVE = 0x0002, SWP_NOSIZE = 0x0001, SWP_NOZORDER = 0x0004
            ctypes.windll.user32.SetWindowPos(handle, 0, 0, 0, 0, 0, 0x0020 | 0x0002 | 0x0001 | 0x0004 | 0x0010)

        except Exception as e:
            logging.error(f"Erro ao ajustar Title Bar: {e}")


# QSS global, escrito com tokens (core/temas.py). Botão comum usa botao_*; o principal
# de cada tela leva a classe "primario" (no Off-White os dois são iguais).
QSS_GLOBAL = """
    QMainWindow { background-color: var(--fundo); }
    QDialog { background-color: var(--fundo); }
    QStatusBar { background-color: var(--fundo); color: var(--texto_secundario); }
    QToolTip { background-color: var(--superficie); color: var(--texto); border: 1px solid var(--borda); padding: 4px; }

    QScrollArea#area_rolagem, QWidget#container_rolagem { background-color: var(--fundo); border: none; }

    QFrame.painel {
        background-color: var(--superficie);
        border-radius: var(--raio);
        border: 1px solid var(--borda);
    }

    QLabel { color: var(--texto); font-family: 'var(--fonte)'; font-size: 13px; }

    #lbl_slogan {
        font-family: 'var(--fonte_titulo)';
        font-size: 26px;
        font-style: italic;
        font-weight: 500;
        color: var(--texto);
    }

    /* Nome Científico: Formatação Biológica Rigorosa */
    QLineEdit.sci-name-input {
        font-family: 'var(--fonte_titulo)';
        font-style: italic;
        font-weight: 500;
        color: var(--texto);
        background-color: var(--superficie);
        border: 1px solid var(--borda);
        border-radius: 6px;
        padding: 6px;
    }

    QLineEdit, QTextEdit {
        background-color: var(--superficie);
        border: 1px solid var(--borda);
        border-radius: 6px;
        padding: 6px;
        color: var(--texto);
        font-family: 'var(--fonte)';
    }

    .lbl-placeholder {
        color: var(--texto_suave);
        font-style: italic;
        font-weight: 500;
        font-size: 13px;
    }

    QListWidget, QListView {
        background-color: var(--superficie);
        border: 1px solid var(--borda);
        border-radius: 8px;
        color: var(--texto);
        outline: none;
        padding: 4px;
    }
    QListWidget::item, QListView::item {
        padding: 8px;
        border-radius: 6px;
        color: var(--texto);
    }
    QListWidget::item:hover, QListView::item:hover { background-color: var(--hover); }
    QListWidget::item:selected, QListView::item:selected {
        background-color: var(--selecao);
        color: var(--texto);
    }

    /* ScrollArea e ScrollBars (v0.6.6) */
    QScrollArea { border: none; background-color: transparent; }
    QScrollBar:vertical {
        border: none;
        background: transparent;
        width: 8px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: var(--borda);
        min-height: 20px;
        border-radius: 4px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

    /* Botões (Padrão Slim: altura do tema) */
    QPushButton {
        background-color: var(--botao_fundo);
        color: var(--botao_texto);
        border: 1px solid var(--botao_borda);
        border-radius: var(--raio_botao);
        padding: 2px 16px;
        min-height: var(--altura_botao);
        max-height: var(--altura_botao);
        font-weight: bold;
        font-family: 'var(--fonte)';
    }
    QPushButton:hover { background-color: var(--botao_hover); }
    QPushButton:disabled {
        background-color: var(--borda_suave);
        color: var(--texto_suave);
        border: 1px solid var(--borda_suave);
    }

    /* Botão principal da tela */
    QPushButton.primario {
        background-color: var(--destaque);
        color: var(--texto_destaque);
        border: 1px solid var(--destaque);
    }
    QPushButton.primario:hover { background-color: var(--destaque_hover); }

    /* Botões Secundários */
    QPushButton.secundario {
        background-color: var(--secundario_fundo);
        color: var(--secundario_texto);
        border: 1px solid var(--borda);
    }
    QPushButton.secundario:hover { background-color: var(--selecao); }
    /* Sugestões de espécie (chips): nome científico em itálico, clique pesquisa */
    QPushButton.chip {
        background-color: var(--superficie_alt);
        color: var(--link);
        border: 1px solid var(--borda);
        border-radius: 13px;
        padding: 0px 12px;
        font-style: italic;
        font-weight: normal;
        min-height: 26px;
        max-height: 26px;
    }
    QPushButton.chip:hover { background-color: var(--selecao); border-color: var(--link); }
    QPushButton.primario:disabled, QPushButton.secundario:disabled {
        background-color: var(--borda_suave);
        color: var(--texto_suave);
        border: 1px solid var(--borda_suave);
    }

    /* Botões da barra de status (novidades) */
    QPushButton#btn_status_novidade {
        background-color: var(--destaque);
        color: var(--texto_destaque);
        border: none;
        border-radius: 4px;
        padding: 2px 10px;
        font-size: 11px;
        min-height: 18px;
        max-height: 22px;
    }

    /* Botões Ícone */
    QPushButton[class="icon-btn"] { background-color: transparent; color: var(--texto_secundario); padding: 4px; border: none; }
    QPushButton[class="icon-btn"]:hover { background-color: var(--hover); border-radius: 4px; }

    /* Botões de Link */
    QPushButton.btn-link {
         background: transparent;
         color: var(--link);
         text-decoration: underline;
         border: none;
         font-size: 11px;
         padding: 0px;
         text-align: left;
    }
    QPushButton.btn-link:hover { color: var(--link_hover); }

    /* Menus (Harmonização v0.6.7+ - Blindagem 2.0) */
    QMenu {
        background-color: var(--superficie) !important;
        border: 1px solid var(--borda) !important;
        border-radius: 8px !important;
        padding: 6px !important;
    }
    QMenu::item {
        background-color: transparent !important;
        color: var(--texto) !important;
        padding: 8px 32px 8px 12px !important;
        border-radius: 6px !important;
        margin: 2px 4px !important;
    }
    QMenu::item:selected {
        background-color: var(--hover) !important;
        color: var(--texto) !important;
    }
    QMenu::item:disabled {
        color: var(--texto_suave) !important;
        background-color: transparent !important;
    }
    QMenu::separator {
        height: 1px;
        background: var(--borda_suave);
        margin: 6px 10px;
    }
    QMenu::icon { margin-left: 8px; }

    /* GroupBox */
    QGroupBox {
        border: 1px solid var(--borda);
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 12px;
        font-weight: bold;
        font-size: 11px;
        background-color: var(--superficie);
        color: var(--texto_secundario);
        text-transform: uppercase;
    }
    QGroupBox::title {
        background-color: var(--superficie);
        color: var(--texto);
    }

    /* Checkbox e RadioButton (Visibilidade v0.8.3) */
    QCheckBox, QRadioButton {
        color: var(--texto);
        spacing: 8px;
        font-family: 'var(--fonte)';
    }
    QCheckBox::indicator, QRadioButton::indicator {
        width: 18px;
        height: 18px;
        border: 1px solid var(--borda);
        border-radius: 4px;
        background-color: var(--superficie);
    }
    QRadioButton::indicator { border-radius: 9px; }
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {
        background-color: var(--destaque);
        border: 1px solid var(--destaque);
    }
    QCheckBox:disabled, QRadioButton:disabled { color: var(--texto_suave); }
    QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {
        background-color: var(--borda_suave);
        border: 1px solid var(--borda_suave);
    }

    /* Fluxo guiado: barra de etapas (ui/layouts/guiado.py) */
    QLabel.etapa {
        color: var(--texto_secundario);
        font-family: 'var(--fonte_titulo)';
        font-size: 13px;
        padding: 4px 10px 6px 10px;
        border-bottom: 3px solid var(--borda_suave);
    }
    QLabel.etapa-ativa { color: var(--destaque); font-weight: bold; border-bottom: 3px solid var(--destaque); }
    QLabel.etapa-feita { color: var(--texto); border-bottom: 3px solid var(--enfase); }
    QLabel.etapa-seta { color: var(--texto_suave); font-size: 14px; }
    QLabel#lbl_dica_etapa { color: var(--texto_secundario); font-size: 12px; }

    /* Abas (Fluxo guiado) */
    QTabWidget::pane {
        border: 1px solid var(--borda);
        border-radius: var(--raio_botao);
        background-color: var(--superficie);
        top: -1px;
    }
    QTabBar::tab {
        background-color: transparent;
        color: var(--texto_secundario);
        font-family: 'var(--fonte)';
        padding: 6px 14px;
        border: 1px solid transparent;
        border-bottom: none;
        margin-right: 2px;
    }
    QTabBar::tab:hover { color: var(--texto); background-color: var(--hover); }
    QTabBar::tab:selected {
        color: var(--texto);
        font-weight: 600;
        background-color: var(--superficie);
        border: 1px solid var(--borda);
        border-bottom: 2px solid var(--destaque);
    }

    /* Classes Abstratas para Widgets Customizados */
    .lbl-titulo-sessao { font-family: 'var(--fonte_titulo)'; font-weight: bold; color: var(--titulo_sessao); font-size: 11px; }
    .container-borda-cinza { border: 1px solid var(--borda); border-radius: 6px; padding: 4px; color: var(--texto); }
    .container-borda-cinza-fill { background-color: var(--superficie_alt); border: 1px solid var(--borda_suave); border-radius: 6px; padding: 6px; color: var(--texto); font-size: 11px; }

    /* Faixa de etimologia */
    QFrame#frame_etimologia {
        background-color: var(--superficie_alt);
        border-left: 4px solid var(--enfase);
        border-radius: 4px;
        padding: 10px;
        margin-top: 10px;
    }

    /* Botão Fechar Modal (Lightbox) */
    QPushButton.btn-fechar-modal {
        background-color: transparent;
        color: var(--texto_secundario);
        border: none;
        font-size: 16px;
        font-weight: bold;
        padding: 0px;
        border-radius: 16px;
    }
    QPushButton.btn-fechar-modal:hover {
        background-color: var(--hover);
        color: var(--texto);
    }

    /* Overlays de Alerta */
    QFrame#overlay_alert {
        background-color: var(--alerta_fundo);
        border: 2px solid var(--alerta_borda); border-radius: 8px;
    }
    QLabel#alert_text { color: var(--alerta_texto); font-size: 12px; font-weight: bold; }
"""
