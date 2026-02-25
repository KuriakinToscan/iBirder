from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QFrame
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon, QDesktopServices
from ui.base.base_dialog import BaseDialog

class VocalDetailDialog(BaseDialog):
    """
    Janela de Detalhes de Auditoria Vocal (v0.8.2).
    Utiliza o template estrutural do LocationDialog para garantir estabilidade e consistência.
    """
    def __init__(self, audio_data, parent=None):
        super().__init__(title="Vocalização", parent=parent)
        self.audio_data = audio_data
        self.setFixedWidth(500)
        self.setMinimumHeight(400)
        
        self.setup_ui()
        self.preencher_dados()

    def setup_ui(self):
        # 1. Identificação do Registro
        lbl_instrucao = QLabel("Identificação do Registro:")
        lbl_instrucao.setStyleSheet("font-weight: bold; color: #111827;")
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
        
        # 2. Genealogia Geográfica e Ranking
        lbl_detalhes = QLabel("Genealogia e Ranking:")
        lbl_detalhes.setStyleSheet("font-weight: bold; color: #111827; margin-top: 5px;")
        self.main_layout.addWidget(lbl_detalhes)
        
        self.lista_info = QListWidget()
        self.lista_info.setMaximumHeight(100)
        self.main_layout.addWidget(self.lista_info)
        
        # 3. Coordenadas de Origem
        lbl_coords = QLabel("Coordenadas de Origem:")
        lbl_coords.setStyleSheet("font-weight: bold; color: #111827; margin-top: 5px;")
        self.main_layout.addWidget(lbl_coords)
        
        container_coords = QHBoxLayout()
        self.input_lat = QLineEdit()
        self.input_lat.setReadOnly(True)
        self.input_lon = QLineEdit()
        self.input_lon.setReadOnly(True)
        
        container_coords.addWidget(QLabel("Lat:"))
        container_coords.addWidget(self.input_lat)
        container_coords.addWidget(QLabel("Lon:"))
        container_coords.addWidget(self.input_lon)
        self.main_layout.addLayout(container_coords)
        
        # 4. Links Externos
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
        
        # 5. Botão Fechar (Padronizado como btn_confirmar do template)
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
        # Carregar dados do dicionário
        id_reg = self.audio_data.get('id_original') or self.audio_data.get('id', '-')
        fonte = self.audio_data.get('fonte', 'Desconhecida')
        lat = self.audio_data.get('lat', '-')
        lon = self.audio_data.get('lon', '-')
        dist = self.audio_data.get('distancia_km', 0)
        camada = self.audio_data.get('camada', '?')
        localidade = self.audio_data.get('audit_geo', '-')
        
        self.input_id.setText(str(id_reg))
        self.input_fonte.setText(fonte)
        self.input_lat.setText(str(lat))
        self.input_lon.setText(str(lon))
        
        # Lista de Detalhes
        self.lista_info.addItem(f"📍 Localidade: {localidade}")
        self.lista_info.addItem(f"📏 Distância: {dist:.2f} km do local da foto")
        self.lista_info.addItem(f"🏆 Camada do Ranking: C{camada}")
        
        # Configurar Links
        if self.audio_data.get('link_observacao'):
            self.btn_registro.setVisible(True)
        if self.audio_data.get('link_audio'):
            self.btn_audio.setVisible(True)

    def _abrir_registro(self):
        if self.audio_data.get('link_observacao'):
            QDesktopServices.openUrl(QUrl(self.audio_data['link_observacao']))

    def _abrir_audio(self):
        if self.audio_data.get('link_audio'):
            QDesktopServices.openUrl(QUrl(self.audio_data['link_audio']))
