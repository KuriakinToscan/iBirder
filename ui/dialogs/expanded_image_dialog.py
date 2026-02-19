import sys
from pathlib import Path
from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QApplication, QSizePolicy, QGraphicsDropShadowEffect, QFrame
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QCursor, QColor
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
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Layout Principal com Margem para Sombra
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(20, 20, 20, 20) # Margem para a sombra
        self.layout_principal.setSpacing(0)
        
        # Container (Moldura)
        self.container = QFrame()
        self.container.setObjectName("container_lightbox")
        self.container.setStyleSheet("""
            QFrame#container_lightbox {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 12px;
            }
        """)
        
        # Sombra
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)
        
        layout_container = QVBoxLayout(self.container)
        layout_container.setContentsMargins(2, 2, 2, 2) # Pequena margem interna
        
        # 1. Widget de Visualização
        self.viewer = ZoomableView(pixmap, self.container)
        self.viewer.setStyleSheet("background: transparent;")
        layout_container.addWidget(self.viewer)
        
        self.layout_principal.addWidget(self.container)

        # 2. Botão Fechar (Flutuante)
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
            
        # Estilo Escuro (Contraste no fundo branco)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                border-radius: 20px;
                border: 1px solid #1F2937;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1F2937;
            }
        """)
        self.btn_close.clicked.connect(self.close)

        # Dimensionamento Inicial (70% da tela)
        screen_geo = QApplication.primaryScreen().availableGeometry()
        w = int(screen_geo.width() * 0.70)
        h = int(screen_geo.height() * 0.70)
        self.resize(w, h)

    def resizeEvent(self, event):
        """Posiciona o botão de fechar no canto superior direito (dentro da margem visual)."""
        super().resizeEvent(event)
        # Ajuste para ficar sobre o canto do container, considerando as margens do dialog
        margin_dialog = 10 # Um pouco para fora da borda visual fica bonito
        x = self.width() - self.btn_close.width() - margin_dialog
        y = margin_dialog
        self.btn_close.move(x, y)
        self.btn_close.raise_()

    def _get_asset_path(self, filename):
        """Helper para localizar assets (compatível com PyInstaller)."""
        if getattr(sys, 'frozen', False):
             base_path = Path(sys._MEIPASS)
        else:
             # Assume estrutura: iBirder/ui/dialogs/../../assets
             base_path = Path(__file__).parent.parent.parent / 'assets'
        
        full_path = base_path / filename
        return str(full_path) if full_path.exists() else None
