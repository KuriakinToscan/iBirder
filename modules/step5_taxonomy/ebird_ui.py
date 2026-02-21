import webbrowser
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, 
                               QMessageBox)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont, QCursor
from ui.base.base_dialog import BaseDialog

class EBirdSettingsDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(title="Configurações eBird (Taxonomia)", parent=parent)
        self.setFixedSize(450, 200)

        # O layout principal (QVBoxLayout) já vem pronto de BaseDialog como self.main_layout
        
        # Título
        lbl_titulo = QLabel("Token de Acesso da API eBird")
        lbl_titulo.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.main_layout.addWidget(lbl_titulo)

        # Campo de Chave
        self.input_key = QLineEdit()
        self.input_key.setPlaceholderText("Cole o seu token (ex: xq12...)")
        self.input_key.setEchoMode(QLineEdit.Password)
        
        # Carregar chave salva se houver
        settings = QSettings("iBirder", "App")
        saved_key = settings.value("ebird_api_key", "")
        if saved_key:
            self.input_key.setText(saved_key)
            
        self.main_layout.addWidget(self.input_key)

        # Link de Ajuda ("Como conseguir?")
        self.btn_help = QPushButton("Como obter minha chave?")
        self.btn_help.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #2563EB;
                text-decoration: underline;
                font-size: 11px;
                font-weight: normal;
                padding: 0px;
                text-align: left;
            }
            QPushButton:hover {
                color: #1D4ED8;
                background-color: transparent;
            }
        """)
        self.btn_help.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_help.clicked.connect(self._mostrar_guia)
        self.main_layout.addWidget(self.btn_help)

        # Disclaimer Transparência
        lbl_info = QLabel("<i>Sem a chave, o iBirder buscará a taxonomia básica no iNaturalist, porém a frequência regional ficará oculta.</i>")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #6B7280; font-size: 10px;")
        self.main_layout.addWidget(lbl_info)

        self.main_layout.addStretch()

        # Botões Rodapé
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("""
             QPushButton {
                 background-color: #E5E7EB;
                 color: #374151;
             }
             QPushButton:hover {
                 background-color: #D1D5DB;
             }
        """)
        btn_cancelar.clicked.connect(self.reject)
        
        btn_salvar = QPushButton("Salvar Configuração")
        btn_salvar.clicked.connect(self._salvar_chave)
        
        layout_botoes.addWidget(btn_cancelar)
        layout_botoes.addWidget(btn_salvar)
        
        self.main_layout.addLayout(layout_botoes)

    def _mostrar_guia(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Como obter seu Acesso ao eBird")
        msg.setText("""
        <b>Passo a passo para gerar o seu Token:</b><br><br>
        1. Crie uma conta gratuita no Cornell Lab of Ornithology.<br>
        2. Acesse o portal da API: <a href="https://ebird.org/api/keygen">ebird.org/api/keygen</a><br>
        3. Gere uma nova chave de acesso (API Key).<br>
        4. Copie o token gerado e cole no campo da tela anterior.<br>
        """)
        # Permite links clicáveis
        msg.setTextFormat(Qt.RichText)
        msg.setTextInteractionFlags(Qt.TextBrowserInteraction)
        msg.setStyleSheet("QLabel { font-size: 12px; }")
        msg.exec()

    def _salvar_chave(self):
        nova_chave = self.input_key.text().strip()
        settings = QSettings("iBirder", "App")
        settings.setValue("ebird_api_key", nova_chave)
        self.accept()
