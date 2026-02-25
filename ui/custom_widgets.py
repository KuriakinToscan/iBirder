from PySide6.QtWidgets import QWidget, QSizePolicy, QApplication, QPushButton, QHBoxLayout, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QSize, QRectF, QMimeData, QUrl, QPoint
from PySide6.QtGui import (
    QPainter, QPixmap, QColor, QFont, QPen, QPainterPath, 
    QFontMetrics, QDrag, QDragEnterEvent, QDropEvent, QIcon, QCursor
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
import os
import sys
from pathlib import Path
import tempfile
from ui.dialogs.expanded_image_dialog import ExpandedImageDialog

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
        self.text_overlay = None # Tooltip only now basically
        self.text_overlay_left = None
        self.text_overlay_right = None
        self.on_drop_callback = None # Função (path) quando arquivo é solto
        self.on_click_callback = None # Função () quando clicado (se vazio)
        
        # Drag State
        self.drag_start_pos = None
        
        # Configuração de Estilo (v0.8.1 - Sync com StyleManager)
        self.bg_color = QColor("#FFFFFF") # Branco puro como os cards
        self.border_color = QColor("#D1D5DB")
        self.text_color = QColor("#4B5563")
        self.overlay_bg_color = QColor(31, 41, 55, 180) # Cinza escuro semi-transparente
        self.overlay_text_color = QColor("#FFFFFF")
        
        # Layout & Simetria (Proporção 1:1 rigorosa)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setMinimumSize(250, 250)
        
        # Habilitar Drop
        self.setAcceptDrops(True)

        # --- Botão Expandir (Lightbox) ---
        self.btn_expand = QPushButton(self)
        self.btn_expand.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_expand.setFixedSize(32, 32)
        self.btn_expand.hide() # Inicialmente oculto
        
        icon_path = self._get_asset_path("icon_expandejanela.svg")
        if icon_path:
            self.btn_expand.setIcon(QIcon(icon_path))
            self.btn_expand.setIconSize(QSize(20, 20))
        else:
            self.btn_expand.setText("⤢")
            
        self.btn_expand.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.8);
                border-radius: 6px;
                border: 1px solid #D1D5DB;
            }
            QPushButton:hover {
                background-color: #FFFFFF;
                border-color: #9CA3AF;
            }
        """)
        self.btn_expand.clicked.connect(self._open_expanded_view)

    def _get_asset_path(self, filename):
        if getattr(sys, 'frozen', False):
             base_path = Path(sys._MEIPASS)
        else:
             # iBirder/ui/custom_widgets.py -> iBirder/assets
             base_path = Path(__file__).parent.parent / 'assets'
        
        full_path = base_path / filename
        return str(full_path) if full_path.exists() else None

    def _open_expanded_view(self):
        if self.pixmap and not self.pixmap.isNull():
            dialog = ExpandedImageDialog(self.pixmap, self.window()) # Parent = Main Window para modal correto
            dialog.exec()

    def resizeEvent(self, event):
        """Posiciona o botão de expandir no canto superior direito e tranca proporção 1:1."""
        super().resizeEvent(event)
        
        # Hard constraint: Força o widget a ser um quadrado exato dinamicamente
        self.setFixedHeight(self.width())
        
        margin = 8
        x = self.width() - self.btn_expand.width() - margin
        y = margin
        self.btn_expand.move(x, y)
        self.btn_expand.raise_()

    def _update_expand_button(self):
        """Mostra o botão apenas se houver imagem válida."""
        has_image = self.pixmap is not None and not self.pixmap.isNull()
        self.btn_expand.setVisible(has_image)
    def sizeHint(self):
        """Retorna uma sugestão base quadrada."""
        return QSize(250, 250)

    def minimumSizeHint(self):
        return QSize(250, 250)
        
    def hasHeightForWidth(self):
        """Sinaliza ao Qt Layout Manager que a altura depende da largura."""
        return True

    def heightForWidth(self, width):
        """Força Proporção Áurea 1:1 (Quadrado)."""
        return width

    # --- API Pública ---

    def set_pixmap(self, pixmap, path=None):
        """Define a imagem e opcionalmente o caminho do arquivo."""
        self.pixmap = pixmap
        if path:
            self.image_path = path
        self.update()
        self._update_expand_button()

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
        self._update_expand_button()

    def set_placeholder(self, text):
        self.text_placeholder = text
        self.update()

    def set_overlay_text(self, text):
        # Mantido para compatibilidade, define como tooltip
        self.text_overlay = text
        if text:
            self.setToolTip(text)
        else:
            self.setToolTip("")
        self.update()
        
    def set_overlay_details(self, left_text, right_text):
        """Define textos para a barra inferior (EXIF)."""
        self.text_overlay_left = left_text
        self.text_overlay_right = right_text
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
                # print(f"[Drag] Imagem grande ({tamanho_mb:.1f}MB). Comprimindo para temp...")
                temp_dir = tempfile.gettempdir()
                nome_temp = f"ibirder_lens_optimized_{os.path.basename(self.image_path)}"
                caminho_temp = os.path.join(temp_dir, nome_temp)
                
                if self.pixmap and not self.pixmap.isNull():
                    self.pixmap.save(caminho_temp, "JPG", 85)
                    caminho_final = caminho_temp
                    # print(f"[Drag] Imagem comprimida salva em: {caminho_final}")
        except Exception:
            pass
            
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
            
            # 3. Overlay (Barra Inferior)
            # Mostra se houver overlay_text (tooltip legacy) OU se tiver detalhes (EXIF)
            if self.text_overlay or (self.text_overlay_left or self.text_overlay_right):
                h_overlay = 28
                r_overlay = QRectF(0, self.height() - h_overlay, self.width(), h_overlay)
                
                painter.fillRect(r_overlay, self.overlay_bg_color)
                
                painter.setPen(self.overlay_text_color)
                painter.setFont(QFont("Segoe UI", 9)) # Fonte um pouco maior para leitura
                
                metrics = QFontMetrics(painter.font())
                margin_x = 10
                
                # MODO 1: Detalhes Duplos (EXIF - Esquerda e Direita)
                if self.text_overlay_left or self.text_overlay_right:
                    # Texto Esquerda (Autor)
                    if self.text_overlay_left:
                        r_left = r_overlay.adjusted(margin_x, 0, -self.width()/2, 0)
                        str_left = metrics.elidedText(self.text_overlay_left, Qt.ElideRight, int(r_left.width()))
                        painter.drawText(r_left, Qt.AlignLeft | Qt.AlignVCenter, str_left)
                    
                    # Texto Direita (Data)
                    if self.text_overlay_right:
                        r_right = r_overlay.adjusted(self.width()/2, 0, -margin_x, 0)
                        str_right = metrics.elidedText(self.text_overlay_right, Qt.ElideLeft, int(r_right.width()))
                        painter.drawText(r_right, Qt.AlignRight | Qt.AlignVCenter, str_right)
                
                # MODO 2: Texto Simples (Referência/Créditos)
                # Alinhado à esquerda com elisão à direita
                elif self.text_overlay:
                    r_text = r_overlay.adjusted(margin_x, 0, -margin_x, 0)
                    str_elided = metrics.elidedText(self.text_overlay, Qt.ElideRight, int(r_text.width()))
                    painter.drawText(r_text, Qt.AlignLeft | Qt.AlignVCenter, str_elided)
        
        else:
            # Placeholder
            painter.setPen(QColor("#4B5563"))
            font_placeholder = QFont("Segoe UI", 12)
            font_placeholder.setItalic(True)
            painter.setFont(font_placeholder)
            painter.drawText(rect, Qt.AlignCenter, self.text_placeholder)

class AudioPage(QWebEnginePage):
    def __init__(self, parent=None):
         super().__init__(parent)
         self.on_play_callback = None
    
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
         if message == "AUDIO_PLAYED" and hasattr(self, 'on_play_callback') and self.on_play_callback:
              self.on_play_callback()

class AudioPlayerWidget(QWidget):
    def __init__(self, url, autor, fonte, tipo_canto="", distancia_texto="", audio_data=None, on_play=None, parent=None):
        super().__init__(parent)
        self.url = url
        self.autor = autor
        self.fonte = fonte
        self.tipo_canto = tipo_canto
        self.distancia_texto = distancia_texto
        self.audio_data = audio_data

        self.setProperty("class", "container-borda-cinza-fill")
        
        layout = QHBoxLayout(self)
        from core.style_manager import StyleManager
        # Obedecer simetria SPACING_MD da v0.3.52 global
        layout.setContentsMargins(StyleManager.SPACING_MD, StyleManager.SPACING_MD, StyleManager.SPACING_MD, StyleManager.SPACING_MD)
        
        # Player HTML5 Embutido
        self.webview = QWebEngineView()
        self.page = AudioPage(self.webview)
        if hasattr(on_play, '__call__'):
             self.page.on_play_callback = lambda: on_play(self.audio_data)
        self.webview.setPage(self.page)
        
        self.webview.setFixedHeight(40)
        self.webview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Custom HTML para o player de áudio nativo do navegador
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background-color: transparent;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    overflow: hidden;
                }}
                audio {{
                    width: 100%;
                    max-height: 40px;
                    outline: none;
                }}
            </style>
        </head>
        <body>
            <audio controls controlsList="nodownload" onplay="console.log('AUDIO_PLAYED')">
                <source src="{self.url}">
                Seu navegador não suporta o elemento de áudio.
            </audio>
        </body>
        </html>
        """
        self.webview.setHtml(html)
        # webview tem background branco by default
        self.webview.setStyleSheet("background: transparent; border: none;")
        self.webview.page().setBackgroundColor(Qt.transparent)
        
        layout_infos = QVBoxLayout()
        layout_infos.setSpacing(2)
        
        # Coletar dados extras se existirem (para retrocompatibilidade com chamadas simples)
        licenca = "CC BY-NC"
        data_grav = "Desconhecida"
        duracao = "0:00"
        if isinstance(self.audio_data, dict):
             licenca = self.audio_data.get('licenca', licenca)
             data_grav = self.audio_data.get('data', data_grav)
             duracao = self.audio_data.get('duracao', duracao)
             
        # Montagem do HTML Semântico e Elegante V0.4
        info_html = ""
        # 1. Título/Tipo + Distância
        if self.tipo_canto:
             dist_str = f" • a {int(self.audio_data.get('distancia'))}km de você" if (isinstance(self.audio_data, dict) and self.audio_data.get('distancia') not in [None, float('inf')]) else ""
             info_html += f"<b>{self.tipo_canto}</b>{dist_str}<br>"
        
        # 2. Autor e Metadata Temporal
        id_str = f" [ID: {self.audio_data.get('id')}]" if (isinstance(self.audio_data, dict) and self.audio_data.get('id')) else ""
        info_html += f"Gravado por {self.autor}{id_str} em {data_grav} ({duracao}) "
        if isinstance(self.audio_data, dict) and self.audio_data.get('q'):
             info_html += f"• <b style='color: #059669;'>{self.audio_data['q']}</b>"
        info_html += "<br>"
        
        # 3. Comentários (Opcional - Útil para iNaturalist v0.8.6)
        comentarios = self.audio_data.get('comentarios', '') if isinstance(self.audio_data, dict) else ""
        if comentarios:
             # Limitar tamanho dos comentários para não quebrar o layout
             coment_curto = (comentarios[:60] + '...') if len(comentarios) > 60 else comentarios
             info_html += f"<i style='color: #4B5563;'>\"{coment_curto}\"</i><br>"
             
        info_html += f"<span style='color: #6B7280; font-size: 10px;'>Fonte: {self.fonte} ({licenca})</span>"

        lbl_info = QLabel(info_html)
        lbl_info.setProperty("class", "lbl-titulo-sessao")
        lbl_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        self.btn_source = QPushButton("Ver Link")
        self.btn_source.setCursor(Qt.PointingHandCursor)
        self.btn_source.setProperty("class", "btn-link") # Sovereign Style v0.6.3
        self.btn_source.clicked.connect(self._open_link)
        
        layout_infos.addWidget(lbl_info)
        layout_infos.addWidget(self.btn_source)
        
        layout.addWidget(self.webview, stretch=1)
        layout.addLayout(layout_infos)
        
    def _open_link(self):
        from PySide6.QtGui import QDesktopServices
        # Priorizar o link da página web (v0.4.32) em vez da URL do arquivo mp3
        final_url = self.url
        if isinstance(self.audio_data, dict) and self.audio_data.get('link_web'):
             final_url = self.audio_data['link_web']
             
        QDesktopServices.openUrl(QUrl(final_url))

    def highlight(self):
        """Destaque visual temporário ao clicar no pin do mapa (v0.4.4)."""
        self.setStyleSheet("background-color: #FEF3C7; border: 2px solid #F59E0B; border-radius: 6px;")
        QTimer.singleShot(3000, lambda: self.setStyleSheet(""))

class VocalAuditCard(QWidget):
    """
    Widget de Auditoria Vocal (v0.7.1).
    Exibe um ícone responsivo (logo_ave_vocal.svg) e a distância do registro.
    Ao clicar no ícone, dispara um callback para abrir detalhes.
    """
    def __init__(self, audio_data, ranking_index=None, on_click=None, parent=None):
        super().__init__(parent)
        self.audio_data = audio_data
        self.ranking_index = ranking_index
        self.on_click_callback = on_click
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # 0. Número de Ordem (v0.7.3)
        if self.ranking_index:
            self.lbl_ranking = QLabel(f"{self.ranking_index}.")
            self.lbl_ranking.setStyleSheet("color: #9CA3AF; font-size: 11px; font-weight: bold; min-width: 15px;")
            layout.addWidget(self.lbl_ranking)
        
        # 1. Ícone Responsivo (Botão Flat v0.7.3)
        self.btn_icon = QPushButton()
        self.btn_icon.setCursor(Qt.PointingHandCursor)
        self.btn_icon.setFixedSize(72, 72) # v0.7.5: Tamanho dobrado
        
        # Buscar ícone nos assets
        icon_path = self._get_asset_path("logo_ave_vocal.svg")
        if icon_path and os.path.exists(icon_path):
            self.btn_icon.setIcon(QIcon(icon_path))
            self.btn_icon.setIconSize(self.btn_icon.size() * 0.9)
        else:
            self.btn_icon.setText("📻")
            
        self.btn_icon.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #F3F4F6;
                border-radius: 4px;
            }
        """)
        
        if self.on_click_callback:
            self.btn_icon.clicked.connect(lambda: self.on_click_callback(self.audio_data))
            
        layout.addWidget(self.btn_icon)
        
        # 2. Texto de Distância
        dist = self.audio_data.get('distancia_km')
        import math
        
        if dist is None or dist == float('inf') or (isinstance(dist, float) and math.isinf(dist)):
            # Fallback para quando o GPS da foto está ausente
            localidade = self.audio_data.get('audit_geo', 'Local desconhecido')
            texto_distancia = f"Registrado em {localidade} (GPS fotográfico indisponível)."
        else:
            # Formatação amigável para distâncias válidas
            dist_str = f"{dist:.0f}" if dist >= 1 else f"{dist:.1f}"
            texto_distancia = f"Registrado a {dist_str} km do local da fotografia."
        
        self.lbl_distancia = QLabel(texto_distancia)
        self.lbl_distancia.setStyleSheet("color: #4B5563; font-size: 11px; font-weight: 500;")
        self.lbl_distancia.setWordWrap(True)
        
        layout.addWidget(self.lbl_distancia, stretch=1)
        
        # Estilo do Card
        self.setObjectName("vocal_audit_card")
        self.setStyleSheet("""
            QWidget#vocal_audit_card {
                background-color: #FFFFFF;
                border-bottom: 1px solid #F3F4F6;
            }
        """)

    def _get_asset_path(self, filename):
        # Reuso do método auxiliar existente no ImageCardWidget
        if getattr(sys, 'frozen', False):
             base_path = Path(sys._MEIPASS)
        else:
             base_path = Path(__file__).parent.parent / 'assets'
        
        full_path = base_path / filename
        return str(full_path) if full_path.exists() else None
