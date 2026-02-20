import webbrowser
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, 
                               QMessageBox)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont, QCursor

class IUCNSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações IUCN (Red List)")
        self.setFixedSize(450, 200)
        self.setStyleSheet("""
            QDialog {
                background-color: #F3F4F6;
            }
            QLabel {
                color: #374151;
            }
            QLineEdit {
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px;
                background-color: white;
            }
            QPushButton {
                background-color: #059669;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Título
        lbl_titulo = QLabel("Token de Acesso da IUCN API")
        lbl_titulo.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(lbl_titulo)

        # Campo de Chave
        self.input_key = QLineEdit()
        self.input_key.setPlaceholderText("Cole o seu token (ex: 9b2a1...)")
        self.input_key.setEchoMode(QLineEdit.Password)
        
        # Carregar chave salva se houver
        settings = QSettings("iBirder", "App")
        saved_key = settings.value("iucn_api_key", "")
        if saved_key:
            self.input_key.setText(saved_key)
            
        layout.addWidget(self.input_key)

        # Link de Ajuda ("Como conseguir?")
        self.btn_help = QPushButton("Como conseguir minha chave?")
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
        layout.addWidget(self.btn_help)

        # Disclaimer Transparência
        lbl_info = QLabel("<i>Sem a chave, o iBirder funcionará normalmente usando dados simplificados do iNaturalist, porém o mapa global não será gerado.</i>")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #6B7280; font-size: 10px;")
        layout.addWidget(lbl_info)

        layout.addStretch()

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
        
        layout.addLayout(layout_botoes)

    def _mostrar_guia(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Como obter seu Acesso à IUCN")
        msg.setText("""
        <b>Passo a passo para gerar o seu Token:</b><br><br>
        1. Acesse o site oficial: <a href="https://apiv3.iucnredlist.org/api/v3/token">apiv3.iucnredlist.org</a><br>
        2. Preencha o formulário informando que o uso será "Pesquisa/Educacional".<br>
        3. Após aprovação automática, um Token de Acesso será enviado para o seu e-mail.<br>
        4. Copie o token do e-mail e cole no campo da tela anterior.<br>
        """)
        # Permite links clicáveis
        msg.setTextFormat(Qt.RichText)
        msg.setTextInteractionFlags(Qt.TextBrowserInteraction)
        msg.setStyleSheet("QLabel { font-size: 12px; }")
        msg.exec()

    def _salvar_chave(self):
        nova_chave = self.input_key.text().strip()
        settings = QSettings("iBirder", "App")
        settings.setValue("iucn_api_key", nova_chave)
        self.accept()
