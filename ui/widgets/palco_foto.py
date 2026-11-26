#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Palco da foto (v1.6, layout Foco): a foto da pessoa ocupando a área toda, com zoom e
arrasto, espelhando o card da foto (ImageCardWidget) sem substituí-lo.

O card continua sendo o painel "foto" (é ele que recebe o arquivo e guarda o caminho);
o palco só mostra a mesma imagem em tamanho grande e repassa a ele o arquivo solto ou o
clique quando ainda não há foto. Zoom pela roda do mouse ou pelas teclas + e -; 0 volta a
ajustar a foto à área.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFont, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QGraphicsScene, QGraphicsView

from core.style_manager import StyleManager

ZOOM_PASSO = 1.15
ZOOM_MINIMO = 0.05
ZOOM_MAXIMO = 20.0
TEXTO_VAZIO = "Arraste uma foto para cá ou clique para escolher (Ctrl+O)"


class PalcoFoto(QGraphicsView):
    """Visualizador grande da foto aberta, com zoom; vazio, aceita arrastar e clicar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("palco_foto")
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self._cena = QGraphicsScene(self)
        self.setScene(self._cena)
        self._item = None
        self._card = None
        self._ajustada = True  # a foto acompanha o tamanho da área até a pessoa dar zoom

    # --- Ligação com o card da foto ---

    def espelhar(self, card):
        """Mostra a imagem do card e acompanha as trocas (sinal imagem_alterada)."""
        self._card = card
        sinal = getattr(card, "imagem_alterada", None)
        if sinal is not None:
            sinal.connect(self._copiar_do_card)
        self._copiar_do_card()

    def _copiar_do_card(self):
        pixmap = getattr(self._card, "pixmap", None) if self._card is not None else None
        self.definir_imagem(pixmap if isinstance(pixmap, QPixmap) else None)

    def definir_imagem(self, pixmap: QPixmap | None):
        self._cena.clear()
        self._item = None
        if pixmap is not None and not pixmap.isNull():
            self._item = self._cena.addPixmap(pixmap)
            self._item.setTransformationMode(Qt.SmoothTransformation)
            self._cena.setSceneRect(QRectF(pixmap.rect()))
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        else:
            self._cena.setSceneRect(QRectF())
            self.setDragMode(QGraphicsView.NoDrag)
        self.ajustar()
        self.viewport().update()

    def tem_imagem(self):
        return self._item is not None

    # --- Zoom ---

    def ajustar(self):
        """A foto inteira na área (tecla 0)."""
        self._ajustada = True
        self.resetTransform()
        if self._item is not None:
            self.fitInView(self._item, Qt.KeepAspectRatio)

    def zoom(self, fator):
        if self._item is None:
            return
        escala = self.transform().m11() * fator
        if not ZOOM_MINIMO <= escala <= ZOOM_MAXIMO:
            return
        self._ajustada = False
        self.scale(fator, fator)

    def escala(self):
        return self.transform().m11()

    def wheelEvent(self, evento):
        self.zoom(ZOOM_PASSO if evento.angleDelta().y() > 0 else 1 / ZOOM_PASSO)
        evento.accept()

    def keyPressEvent(self, evento):
        tecla = evento.key()
        if tecla in (Qt.Key_Plus, Qt.Key_Equal):
            self.zoom(ZOOM_PASSO)
        elif tecla == Qt.Key_Minus:
            self.zoom(1 / ZOOM_PASSO)
        elif tecla == Qt.Key_0:
            self.ajustar()
        else:
            super().keyPressEvent(evento)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        if self._ajustada:
            self.ajustar()

    # --- Sem foto: arrastar e clicar ---

    def drawBackground(self, painter, retangulo):
        painter.fillRect(retangulo, StyleManager.qcor("superficie_alt"))

    def drawForeground(self, painter, retangulo):
        if self._item is not None:
            return
        painter.save()
        painter.resetTransform()
        fonte = QFont(self.font())
        fonte.setPointSize(fonte.pointSize() + 3)
        painter.setFont(fonte)
        painter.setPen(StyleManager.qcor("texto_secundario"))
        painter.drawText(self.viewport().rect(), Qt.AlignCenter | Qt.TextWordWrap, TEXTO_VAZIO)
        painter.restore()

    def mousePressEvent(self, evento):
        if self._item is None and evento.button() == Qt.LeftButton:
            callback = getattr(self._card, "on_click_callback", None)
            if callback:
                callback()
            evento.accept()
            return
        super().mousePressEvent(evento)

    def dragEnterEvent(self, evento):
        if evento.mimeData().hasUrls():
            evento.acceptProposedAction()

    def dragMoveEvent(self, evento):
        if evento.mimeData().hasUrls():
            evento.acceptProposedAction()

    def dropEvent(self, evento):
        urls = evento.mimeData().urls()
        callback = getattr(self._card, "on_drop_callback", None)
        if urls and callback:
            callback(urls[0].toLocalFile())
            evento.acceptProposedAction()


__all__ = ["PalcoFoto"]
