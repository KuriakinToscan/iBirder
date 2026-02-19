from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter

class ZoomableView(QGraphicsView):
    """
    Widget visualizador de imagens com suporte a Zoom (Wheel) e Pan (Drag).
    Baseado em QGraphicsView para performance e fluidez.
    """
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Configurar Cena
        self.scene = QGraphicsScene(self)
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.setScene(self.scene)
        
        # Estado inicial (para saber se já fizemos o fit inicial)
        self._first_show = True

    def wheelEvent(self, event):
        """Implementa Zoom In/Out com a roda do mouse."""
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        # Se delta > 0, zoom in
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        # Limites de Zoom (opcional, mas bom para UX)
        current_scale = self.transform().m11() # Escala X atual
        
        # Evitar zoom muito pequeno ou absurdamente grande
        if (zoom_factor < 1 and current_scale < 0.1) or (zoom_factor > 1 and current_scale > 20):
             return

        self.scale(zoom_factor, zoom_factor)
        
        # Aceitar evento para impedir propagação
        event.accept()

    def showEvent(self, event):
        """Garante que a imagem comece ajustada à visão."""
        super().showEvent(event)
        if self._first_show:
            self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
            self._first_show = False
