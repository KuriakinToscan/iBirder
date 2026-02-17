from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QPainter, QPixmap, QColor, QFont, QPen, QPainterPath

class ImageCardWidget(QWidget):
    """
    Widget personalizado que desenha uma imagem centralizada (KeepAspectRatio)
    e suporta overlay de texto (créditos) e placeholder.
    Garante que o widget (container) dite o tamanho da imagem, e não o contrário.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = None
        self.text_placeholder = "..."
        self.text_overlay = None  # Texto a ser exibido sobre a imagem (créditos)
        
        # Configuração de Estilo Padrão (pode ser sobrescrita)
        self.bg_color = QColor("#F9FAFB")
        self.border_color = QColor("#E5E7EB")
        self.text_color = QColor("#9CA3AF")
        self.overlay_bg_color = QColor(0, 0, 0, 160) # Preto semitransparente
        self.overlay_text_color = QColor("#FFFFFF")
        
        # Política de Tamanho Ignorada (Layout comanda)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(250, 250)

    def sizeHint(self):
        """Retorna tamanho mínimo para forçar layout a decidir a distribuição."""
        return QSize(1, 1)

    def minimumSizeHint(self):
        return QSize(1, 1)

    def set_pixmap(self, pixmap):
        self.pixmap = pixmap
        self.update() # Força repintura

    def set_placeholder(self, text):
        self.text_placeholder = text
        self.update()

    def set_overlay_text(self, text):
        self.text_overlay = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 1. Desenhar Fundo e Borda (Card)
        rect = self.rect().adjusted(1, 1, -1, -1) # Margem para borda não cortar
        
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 12, 12)
        
        painter.fillPath(path, self.bg_color)
        
        pen = QPen(self.border_color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawPath(path)
        
        # 2. Desenhar Conteúdo
        if self.pixmap and not self.pixmap.isNull():
            # Escalar imagem mantendo aspecto
            scaled_pixmap = self.pixmap.scaled(
                self.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            
            # Calcular posição para centralizar
            x = (self.width() - scaled_pixmap.width()) // 2
            y = (self.height() - scaled_pixmap.height()) // 2
            
            # Clip path para garantir que a imagem não saia das bordas arredondadas (opcional, mas bom)
            painter.setClipPath(path)
            painter.drawPixmap(x, y, scaled_pixmap)
            
            # 3. Desenhar Overlay de Créditos (apenas se houver imagem e texto)
            if self.text_overlay:
                overlay_height = 24
                # Faixa na parte inferior da IMAGEM ou do WIDGET? Pedido: "parte inferior do widget"
                # Mas visualmente fica melhor se for na parte inferior da imagem ou do widget.
                # Como o widget é o container visual (o card), vamos desenhar na parte inferior do WIDGET, 
                # mas respeitando o clip arredondado.
                
                overlay_rect = QRectF(0, self.height() - overlay_height, self.width(), overlay_height)
                
                # Fundo do Overlay
                painter.fillRect(overlay_rect, self.overlay_bg_color)
                
                # Texto do Overlay
                painter.setPen(self.overlay_text_color)
                painter.setFont(QFont("Segoe UI", 8)) # 10px ~ 8pt
                
                text_rect = overlay_rect.adjusted(10, 0, -10, 0) # Padding lateral
                painter.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, self.text_overlay)
                
        else:
            # Desenhar Placeholder
            painter.setPen(self.text_color)
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(rect, Qt.AlignCenter, self.text_placeholder)
