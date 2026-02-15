from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtGui import QDesktopServices, QFont, QPixmap
from PySide6.QtCore import QUrl, Qt
import keyring

class PaginaIntro(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Bem-vindo ao Modo Online")
        self.setSubTitle("Identificação precisa com Inteligência Artificial")
        
        layout = QVBoxLayout()
        label = QLabel(
            "Para utilizar o modo de identificação online, precisamos de uma Chave de API do Google Gemini.\n\n"
            "É GRATUITO e seguro. Sua chave será armazenada no cofre de senhas do seu sistema.\n"
            "Nós não temos acesso a ela."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        self.setLayout(layout)

class PaginaObterChave(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Obter sua Chave de API")
        self.setSubTitle("Siga os passos abaixo:")

        layout = QVBoxLayout()
        
        passo1 = QLabel("1. Clique no botão abaixo para abrir o Google AI Studio:")
        layout.addWidget(passo1)
        
        btn_link = QPushButton("Abrir Google AI Studio ↗️")
        btn_link.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background-color: #222222; }
        """)
        btn_link.clicked.connect(self._abrir_link)
        layout.addWidget(btn_link)
        
        passo2 = QLabel("\n2. Faça login com sua conta do Google.")
        layout.addWidget(passo2)
        
        passo3 = QLabel("3. Clique em 'Get API key' e depois em 'Create API key'.")
        layout.addWidget(passo3)
        
        passo4 = QLabel("4. Copie a chave gerada (começa com 'AIza...').")
        layout.addWidget(passo4)

        self.setLayout(layout)

    def _abrir_link(self):
        QDesktopServices.openUrl(QUrl("https://aistudio.google.com/app/apikey"))

class PaginaSalvarChave(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Salvar Chave")
        self.setSubTitle("Cole sua chave abaixo:")

        layout = QVBoxLayout()
        
        self.input_chave = QLineEdit()
        self.input_chave.setPlaceholderText("Cole sua chave aqui (AIza...)")
        self.input_chave.setEchoMode(QLineEdit.Password)
        self.input_chave.textChanged.connect(self.completeChanged)
        layout.addWidget(self.input_chave)
        
        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)

        self.setLayout(layout)

    def isComplete(self):
        return len(self.input_chave.text().strip()) > 30

    def validatePage(self):
        chave = self.input_chave.text().strip()
        # Tenta salvar no keyring
        try:
            keyring.set_password("iBirder_Gemini_Key", "user", chave)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Não foi possível salvar a chave: {e}")
            return False

class WizardConfig(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuração do Modo Online")
        self.setWizardStyle(QWizard.ModernStyle)
        
        # Tema Industrial/Grafite
        self.setStyleSheet("""
            QWizard { background-color: #F5F5F5; color: #222222; }
            QLabel { font-size: 13px; color: #222222; }
            QLineEdit { 
                padding: 8px; 
                border-radius: 4px; 
                border: 1px solid #BDBDBD; 
                background-color: #FFFFFF;
                color: #222222;
            }
            QLineEdit:focus { border: 1px solid #444444; }
        """)

        self.addPage(PaginaIntro())
        self.addPage(PaginaObterChave())
        self.addPage(PaginaSalvarChave())
