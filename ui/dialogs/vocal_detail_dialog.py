from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QFrame
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtWebEngineWidgets import QWebEngineView
from ui.base.base_dialog import BaseDialog
from core.style_manager import StyleManager

class VocalDetailDialog(BaseDialog):
    """
    Janela de Detalhes de Auditoria Vocal (v1.0.0).
    Interface simplificada com player no topo e foco na identificação.
    """
    def __init__(self, audio_data, parent=None):
        super().__init__(title="Vocalização", parent=parent)
        self.audio_data = audio_data
        print(f"[VocalDetailDialog] Inicializando para ID: {self.audio_data.get('id')}")
        self.setFixedWidth(500)
        self.setMinimumHeight(280) # Altura reduzida para refletir a simplificação
        
        self.setup_ui()
        self.preencher_dados()
        
        # Blindagem da Title Bar: Manter cor cinza escuro oficial do iBirder
        StyleManager.setup_window_theme(self)
        print(f"[VocalDetailDialog] UI Montada com sucesso.")

    def setup_ui(self):
        # 0. Player de Áudio (Topo)
        self.webview_player = QWebEngineView()
        self.webview_player.setFixedHeight(60)
        self.webview_player.setStyleSheet("background: transparent; border: none;")
        self.webview_player.page().setBackgroundColor(Qt.transparent)
        self.main_layout.addWidget(self.webview_player)

        # 1. Identificação do Registro
        lbl_instrucao = QLabel("Identificação do Registro:")
        lbl_instrucao.setStyleSheet("font-weight: bold; color: #111827; margin-top: 5px;")
        self.main_layout.addWidget(lbl_instrucao)
        
        container_id = QHBoxLayout()
        self.input_id = QLineEdit()
        self.input_id.setReadOnly(True)
        self.input_id.setPlaceholderText("ID do Registro")
        
        self.input_fonte = QLineEdit()
        self.input_fonte.setReadOnly(True)
        self.input_fonte.setPlaceholderText("Fonte")
        
        container_id.addWidget(QLabel("ID:"))
        container_id.addWidget(self.input_id, stretch=1)
        container_id.addWidget(QLabel("Fonte:"))
        container_id.addWidget(self.input_fonte, stretch=1)
        self.main_layout.addLayout(container_id)
        
        # 2. Links Externos
        layout_links = QHBoxLayout()
        self.btn_registro = QPushButton("Abrir Registro")
        self.btn_registro.setCursor(Qt.PointingHandCursor)
        self.btn_registro.clicked.connect(self._abrir_registro)
        self.btn_registro.setVisible(False)
        
        self.btn_audio = QPushButton("Áudio Bruto")
        self.btn_audio.setCursor(Qt.PointingHandCursor)
        self.btn_audio.clicked.connect(self._abrir_audio)
        self.btn_audio.setVisible(False)
        
        layout_links.addWidget(self.btn_registro)
        layout_links.addWidget(self.btn_audio)
        self.main_layout.addLayout(layout_links)

        # 3. Botão Fechar
        self.btn_fechar = QPushButton("Fechar")
        self.btn_fechar.setCursor(Qt.PointingHandCursor)
        self.btn_fechar.clicked.connect(self.accept)
        self.btn_fechar.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: white;
            }
            QPushButton:hover {
                background-color: #1F2937;
            }
        """)
        self.main_layout.addWidget(self.btn_fechar)

    def preencher_dados(self):
        # 0. Carregar Player (Robusto v1.0.0)
        url_audio = (
            self.audio_data.get('url') or 
            self.audio_data.get('link_audio') or 
            self.audio_data.get('file_url')
        )
        
        # Sanitização failsafe de URL
        if url_audio and url_audio.startswith('//'):
            url_audio = 'https:' + url_audio
            
        if url_audio:
            html = f"""
            <html><head><style>
                body {{ margin: 0; padding: 0; background: transparent; display: flex; align-items: center; justify-content: center; height: 100vh; overflow: hidden; }}
                audio {{ width: 100%; outline: none; }}
            </style></head><body>
                <audio controls controlsList="nodownload"><source src="{url_audio}"></audio>
            </body></html>
            """
            self.webview_player.setHtml(html)
        else:
            self.webview_player.setHtml("<html><body style='color:#6B7280; font-family:sans-serif; display:flex; align-items:center; justify-content:center; height:100vh;'>Áudio não disponível</body></html>")

        # 1. Carregar ID e Fonte
        id_reg = self.audio_data.get('id_original') or self.audio_data.get('id', '-')
        fonte = self.audio_data.get('fonte', 'Desconhecida')
        
        self.input_id.setText(str(id_reg))
        self.input_fonte.setText(fonte)
        
        # Configurar Links com Fallbacks
        link_obs = self.audio_data.get('link_observacao') or self.audio_data.get('link_web')
        if link_obs:
            self.btn_registro.setVisible(True)
            self.audio_data['final_link_obs'] = link_obs # Cache interno
            
        if url_audio:
            self.btn_audio.setVisible(True)
            self.audio_data['final_link_audio'] = url_audio # Cache interno

    def _abrir_registro(self):
        url = self.audio_data.get('final_link_obs')
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _abrir_audio(self):
        url = self.audio_data.get('final_link_audio')
        if url:
            QDesktopServices.openUrl(QUrl(url))
