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
from PySide6.QtWebEngineWidgets import QWebEngineView
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
        # 0. Player de Áudio (Topo)
        self.webview_player = QWebEngineView()
        self.webview_player.setFixedHeight(60)
        self.webview_player.setStyleSheet("background: transparent; border: none;")
        self.webview_player.page().setBackgroundColor(Qt.transparent)
        self.main_layout.addWidget(self.webview_player)
        
        # 0.1 Créditos (v0.8.2 - Movido para baixo do player)
        self.lbl_creditos = QLabel("")
        self.lbl_creditos.setStyleSheet("font-size: 11px; color: #4B5563; font-style: italic; margin-bottom: 5px;")
        self.lbl_creditos.setWordWrap(True)
        self.lbl_creditos.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.lbl_creditos)

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
        
        # 2. Localização do Registro (v0.8.2)
        lbl_loc_title = QLabel("Localização do Registro:")
        lbl_loc_title.setStyleSheet("font-weight: bold; color: #111827; margin-top: 10px;")
        self.main_layout.addWidget(lbl_loc_title)
        
        self.lbl_localizacao = QLabel("Desconhecida")
        self.lbl_localizacao.setStyleSheet("color: #374151; font-size: 11px; margin-bottom: 10px;")
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
        
        # Estilo Padronizado (Grey-Dark Sovereign)
        estilo_btn = """
            QPushButton {
                background-color: #374151;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1F2937;
            }
        """
        self.btn_registro.setStyleSheet(estilo_btn)
        self.btn_fechar.setStyleSheet(estilo_btn)
        
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
            
        if url_audio:
            logging.debug(f"Carregando player de áudio: {url_audio}")
            html = f"""
            <!DOCTYPE html>
            <html><head><style>
                body {{ 
                    margin: 0; padding: 0; background: transparent; 
                    display: flex; align-items: center; justify-content: center; 
                    height: 100vh; overflow: hidden; 
                }}
                audio {{ width: 95%; outline: none; }}
            </style></head><body>
                <audio id="player" controls controlsList="nodownload" preload="auto">
                    <source src="{url_audio}" type="audio/mpeg">
                    <source src="{url_audio}" type="audio/wav">
                    <source src="{url_audio}">
                    Seu navegador não suporta áudio.
                </audio>
                <script>
                    var audio = document.getElementById('player');
                    audio.onerror = function() {{
                        document.body.innerHTML = "<div style='color:#6B7280; font-family:sans-serif; text-align:center;'>Falha ao carregar áudio (Erro de Rede/Formato)</div>";
                    }};
                </script>
            </body></html>
            """
            self.webview_player.setHtml(html)
        else:
            logging.warning("Nenhuma URL de áudio disponível para o diálogo de detalhes.")
            self.webview_player.setHtml("<html><body style='color:#6B7280; font-family:sans-serif; display:flex; align-items:center; justify-content:center; height:100vh;'>Áudio não disponível na sessão</body></html>")

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

    def _abrir_registro(self):
        url = self.audio_data.get('final_link_obs')
        if url:
            QDesktopServices.openUrl(QUrl(url))
