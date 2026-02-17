from PySide6.QtWidgets import QWidget, QSizePolicy, QApplication
from PySide6.QtCore import Qt, QSize, QRectF, QMimeData, QUrl, QPoint
from PySide6.QtGui import (
    QPainter, QPixmap, QColor, QFont, QPen, QPainterPath, 
    QFontMetrics, QDrag, QDragEnterEvent, QDropEvent
)
import os
import tempfile

class ImageCardWidget(QWidget):
    """
    Widget definitivo para exibição de imagens no iBirder.
    Suporta:
    - Rendering centralizado com KeepAspectRatio.
    - Overlay de texto (créditos) com fundo semitransparente.
    - Drag & Drop (Arrastar para fora e Soltar arquivo dentro).
    - Simetria rígida via SizePolicy(Expanding, Expanding) e sizeHint(1,1).
    - Clique para ação (ex: abrir seletor) quando vazio.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado
        self.pixmap = None
        self.image_path = None # Caminho do arquivo atual (para drag out)
        self.text_placeholder = "..."
        self.text_overlay = None
        self.on_drop_callback = None # Função (path) quando arquivo é solto
        self.on_click_callback = None # Função () quando clicado (se vazio)
        
        # Drag State
        self.drag_start_pos = None
        
        # Configuração de Estilo
        self.bg_color = QColor("#F9FAFB")
        self.border_color = QColor("#E5E7EB")
        self.text_color = QColor("#9CA3AF")
        self.overlay_bg_color = QColor(0, 0, 0, 160)
        self.overlay_text_color = QColor("#FFFFFF")
        
        # Layout & Simetria
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(250, 250)
        
        # Habilitar Drop
        self.setAcceptDrops(True)

    def sizeHint(self):
        """Retorna (1,1) para obrigar o layout a distribuir espaço igualmente."""
        return QSize(1, 1)

    def minimumSizeHint(self):
        return QSize(1, 1)

    # --- API Pública ---

    def set_pixmap(self, pixmap, path=None):
        """Define a imagem e opcionalmente o caminho do arquivo."""
        self.pixmap = pixmap
        if path:
            self.image_path = path
        self.update()

    def set_image_path(self, path):
        """Carrega imagem do caminho e define como atual."""
        if path and os.path.exists(path):
            self.image_path = path
            self.pixmap = QPixmap(path)
            self.update()
        else:
            self.image_path = None
            self.pixmap = None
            self.update()

    def set_placeholder(self, text):
        self.text_placeholder = text
        self.update()

    def set_overlay_text(self, text):
        self.text_overlay = text
        if text:
            self.setToolTip(text)
        else:
            self.setToolTip("")
        self.update()
        
    def set_on_drop(self, callback):
        """Define função callback(path) para quando um arquivo for solto no widget."""
        self.on_drop_callback = callback

    def set_on_click(self, callback):
        """Define função callback() para quando o widget for clicado (estando vazio)."""
        self.on_click_callback = callback

    # --- Eventos de Mouse & Drag (Arrastar PARA FORA) ---

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.image_path:
                self.drag_start_pos = event.position().toPoint()
            else:
                self.drag_start_pos = None
                if self.on_click_callback:
                    self.on_click_callback()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self.image_path or not self.drag_start_pos:
            return
            
        if (event.position().toPoint() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
            
        # Iniciar Drag
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Otimização (< 20MB)
        caminho_final = self.image_path
        try:
            tamanho_mb = os.path.getsize(self.image_path) / (1024 * 1024)
            if tamanho_mb > 15:
                print(f"[Drag] Imagem grande ({tamanho_mb:.1f}MB). Comprimindo para temp...")
                temp_dir = tempfile.gettempdir()
                nome_temp = f"ibirder_lens_optimized_{os.path.basename(self.image_path)}"
                caminho_temp = os.path.join(temp_dir, nome_temp)
                
                if self.pixmap and not self.pixmap.isNull():
                    self.pixmap.save(caminho_temp, "JPG", 85)
                    caminho_final = caminho_temp
                    print(f"[Drag] Imagem comprimida salva em: {caminho_final}")
        except Exception as e:
            print(f"[Drag] Erro na otimização: {e}")
            
        mime_data.setUrls([QUrl.fromLocalFile(caminho_final)])
        drag.setMimeData(mime_data)
        if self.pixmap:
             drag.setPixmap(self.pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
             drag.setHotSpot(QPoint(32, 32))
        
        drag.exec(Qt.CopyAction)

    # --- Eventos de Drop (Receber Arquivo) ---

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if self.on_drop_callback:
                self.on_drop_callback(path)

    # --- Rendering ---

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 1. Fundo e Borda
        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 12, 12)
        
        painter.fillPath(path, self.bg_color)
        
        pen = QPen(self.border_color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawPath(path)
        
        # 2. Imagem
        if self.pixmap and not self.pixmap.isNull():
            scaled = self.pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            
            painter.setClipPath(path)
            painter.drawPixmap(x, y, scaled)
            
            # 3. Overlay
            if self.text_overlay:
                h_overlay = 28
                r_overlay = QRectF(0, self.height() - h_overlay, self.width(), h_overlay)
                
                painter.fillRect(r_overlay, self.overlay_bg_color)
                
                painter.setPen(self.overlay_text_color)
                painter.setFont(QFont("Segoe UI", 8))
                
                r_text = r_overlay.adjusted(10, 0, -10, 0)
                metrics = QFontMetrics(painter.font())
                elided = metrics.elidedText(self.text_overlay, Qt.ElideRight, int(r_text.width()))
                
                painter.drawText(r_text, Qt.AlignRight | Qt.AlignVCenter, elided)
        
        else:
            # Placeholder
            painter.setPen(self.text_color)
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(rect, Qt.AlignCenter, self.text_placeholder)
