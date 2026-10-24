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

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QFrame
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon, QDesktopServices
import os
import requests
import logging
from ui.widgets.audio_player import PlayerAudio
from ui.base.base_dialog import BaseDialog
from core.style_manager import StyleManager

class VocalDetailDialog(BaseDialog):
    """
    Janela de Detalhes de Auditoria Vocal (v0.8.2).
    Interface simplificada com player no topo e foco na identificação.
    """
    def __init__(self, audio_data, parent=None):
        super().__init__(title="Detalhes da Vocalização", parent=parent)
        self.audio_data = audio_data
        logging.debug(f"Inicializando VocalDetailDialog para ID: {self.audio_data.get('id')}")
        self.setFixedWidth(500)
        self.setMinimumHeight(280) # Altura reduzida para refletir a simplificação
        
        self.setup_ui()
        self.preencher_dados()
        
        # Blindagem da Title Bar: Manter cor cinza escuro oficial do iBirder
        StyleManager.setup_window_theme(self)
        logging.debug("VocalDetailDialog UI montada.")

    def setup_ui(self):
        # 0. Player de Áudio (Topo) — nativo; ver ui/widgets/audio_player.py
        self.layout_player = QVBoxLayout()
        self.main_layout.addLayout(self.layout_player)
        self.player = None
        
        # 0.1 Créditos (v0.8.2 - Movido para baixo do player)
        self.lbl_creditos = QLabel("")
        StyleManager.estilizar(self.lbl_creditos, "font-size: 11px; color: var(--texto_secundario); font-style: italic; margin-bottom: 5px;")
        self.lbl_creditos.setWordWrap(True)
        self.lbl_creditos.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.lbl_creditos)

        # 1. Identificação do Registro
        lbl_instrucao = QLabel("Identificação do Registro:")
        StyleManager.estilizar(lbl_instrucao, "font-weight: bold; color: var(--texto); margin-top: 5px;")
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
        
        # 2. Localização do Registro (v0.8.2)
        lbl_loc_title = QLabel("Localização do Registro:")
        StyleManager.estilizar(lbl_loc_title, "font-weight: bold; color: var(--texto); margin-top: 10px;")
        self.main_layout.addWidget(lbl_loc_title)
        
        self.lbl_localizacao = QLabel("Desconhecida")
        StyleManager.estilizar(self.lbl_localizacao, "color: var(--texto_secundario); font-size: 11px; margin-bottom: 10px;")
        self.lbl_localizacao.setWordWrap(True)
        self.main_layout.addWidget(self.lbl_localizacao)

        # 3. Ações no Rodapé
        self.main_layout.addStretch()
        layout_botoes = QHBoxLayout()
        
        self.btn_registro = QPushButton("Abrir Registro")
        self.btn_registro.setCursor(Qt.PointingHandCursor)
        self.btn_registro.clicked.connect(self._abrir_registro)
        self.btn_registro.setFixedHeight(32)
        
        self.btn_fechar = QPushButton("Fechar")
        self.btn_fechar.setCursor(Qt.PointingHandCursor)
        self.btn_fechar.clicked.connect(self.accept)
        self.btn_fechar.setFixedHeight(32)
        
        # Os dois botões em destaque, nas cores do tema
        estilo_btn = """
            QPushButton {
                background-color: var(--destaque);
                color: var(--texto_destaque);
                border: none;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: var(--destaque_hover);
            }
        """
        StyleManager.estilizar(self.btn_registro, estilo_btn)
        StyleManager.estilizar(self.btn_fechar, estilo_btn)
        
        layout_botoes.addWidget(self.btn_registro)
        layout_botoes.addWidget(self.btn_fechar)
        self.main_layout.addLayout(layout_botoes)

    def preencher_dados(self):
        # 0. Carregar Player (Robusto v0.8.9)
        url_audio = (
            self.audio_data.get('url') or 
            self.audio_data.get('link_audio') or 
            self.audio_data.get('file_url')
        )
        
        # Sanitização agressiva de URL (v0.8.9 - Forçar HTTPS p/ Chromium)
        if url_audio:
            if url_audio.startswith('//'):
                url_audio = 'https:' + url_audio
            elif url_audio.startswith('http://'):
                url_audio = url_audio.replace('http://', 'https://', 1)
            
        logging.debug(f"Carregando player de áudio: {url_audio}")
        self.player = PlayerAudio(url_audio, self)
        self.layout_player.addWidget(self.player)

        # 1. Carregar ID e Fonte
        id_reg = self.audio_data.get('id_original') or self.audio_data.get('id', '-')
        fonte = self.audio_data.get('fonte', 'Desconhecida')
        
        self.input_id.setText(str(id_reg))
        self.input_fonte.setText(fonte)
        
        # 1.1 Preencher Créditos (v0.8.2 - Font 11px)
        autor = self.audio_data.get('autor', 'Desconhecido')
        licenca = self.audio_data.get('licenca', 'Todos os direitos reservados')
        self.lbl_creditos.setText(f"© {autor}, {licenca}")
        
        # 1.2 Preencher Localização (v0.8.2)
        local = self.audio_data.get('audit_geo') or "Localização não informada"
        self.lbl_localizacao.setText(local)
        
        # Configurar Links com Fallbacks
        link_obs = self.audio_data.get('link_observacao') or self.audio_data.get('link_web')
        if link_obs:
            self.btn_registro.setVisible(True)
            self.audio_data['final_link_obs'] = link_obs # Cache interno
        else:
            self.btn_registro.setVisible(False)

    def done(self, resultado):
        if self.player:
            self.player.parar()  # o som não continua após fechar a janela
        super().done(resultado)

    def _abrir_registro(self):
        url = self.audio_data.get('final_link_obs')
        if url:
            QDesktopServices.openUrl(QUrl(url))
