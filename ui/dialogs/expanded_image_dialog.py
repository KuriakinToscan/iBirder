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

        # 2. Botão Fechar (Ghost Style)
        self.btn_close = QPushButton("✕", self)
        self.btn_close.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_close.setFixedSize(32, 32)
        self.btn_close.setProperty("class", "btn-fechar-modal")
        self.btn_close.clicked.connect(self.close)

        # Dimensionamento Inicial (70% da tela)
        screen_geo = QApplication.primaryScreen().availableGeometry()
        w = int(screen_geo.width() * 0.70)
        h = int(screen_geo.height() * 0.70)
        self.resize(w, h)

    def resizeEvent(self, event):
        """Posiciona o botão de fechar dentro da moldura branca."""
        super().resizeEvent(event)
        
        # Margem do Layout (20) + Padding Interno desejado (8)
        margin_top = 28
        margin_right = 28
        
        x = self.width() - self.btn_close.width() - margin_right
        y = margin_top
        
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
