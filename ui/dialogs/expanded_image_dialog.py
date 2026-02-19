import sys
from pathlib import Path
from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QApplication, QSizePolicy
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QCursor
from ui.widgets.zoomable_view import ZoomableView

class ExpandedImageDialog(QDialog):
    """
    Janela modal estilo Lightbox para exibir imagem em alta resolução.
    Ocupa 70% da tela e permite zoom/pan.
    Ação de fechar via botão flutuante.
    """
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground) # Fundo transparente para bordas arredondadas/sombra se quisermos
        
        # Layout Principal
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(0, 0, 0, 0)
        self.layout_principal.setSpacing(0)
        
        # Estilo do Container (Fundo Escuro)
        self.setStyleSheet("QDialog { background-color: rgba(0, 0, 0, 0.9); border-radius: 12px; }")
        
        # 1. Widget de Visualização
        self.viewer = ZoomableView(pixmap, self)
        # O viewer precisa ter fundo transparente para mesclar com o dialog escuro ou próprio fundo
        self.viewer.setStyleSheet("background: transparent;")
        self.layout_principal.addWidget(self.viewer)

        # 2. Botão Fechar (Flutuante na lógica, mas aqui no layout sobreposto ou absoluto)
        # Para simplificar e garantir que fique sobre o viewer, vamos instanciar com PARENT = self e mover manualmente no resizeEvent
        self.btn_close = QPushButton(self)
        self.btn_close.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_close.setFixedSize(40, 40)
        
        # Carregar ícone
        path_icon = self._get_asset_path("icon_retraijanela.svg")
        if path_icon:
            self.btn_close.setIcon(QIcon(path_icon))
            self.btn_close.setIconSize(QSize(24, 24))
        else:
            self.btn_close.setText("X")
            
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.4);
            }
        """)
        self.btn_close.clicked.connect(self.close)

        # Dimensionamento Inicial (70% da tela)
        screen_geo = QApplication.primaryScreen().availableGeometry()
        w = int(screen_geo.width() * 0.70)
        h = int(screen_geo.height() * 0.70)
        self.resize(w, h)
        
        # Centralizar (opcional, o Qt já tenta centralizar dialogs)
        # self.move(screen_geo.center() - self.rect().center())

    def resizeEvent(self, event):
        """Posiciona o botão de fechar no canto superior direito."""
        super().resizeEvent(event)
        margin = 20
        # x = largura - largura_botao - margem
        x = self.width() - self.btn_close.width() - margin
        y = margin
        self.btn_close.move(x, y)
        self.btn_close.raise_() # Garante que fique no topo

    def _get_asset_path(self, filename):
        """Helper para localizar assets (compatível com PyInstaller)."""
        if getattr(sys, 'frozen', False):
             base_path = Path(sys._MEIPASS)
        else:
             # Assume estrutura: iBirder/ui/dialogs/../../assets
             base_path = Path(__file__).parent.parent.parent / 'assets'
        
        full_path = base_path / filename
        return str(full_path) if full_path.exists() else None
