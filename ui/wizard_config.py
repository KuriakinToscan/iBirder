from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
    QRadioButton, QButtonGroup, QSpacerItem, QSizePolicy
)
from PySide6.QtGui import QDesktopServices, QFont, QPixmap
from PySide6.QtCore import QUrl, Qt
import keyring
from core.config import carregar_config, salvar_config

# --- Estilo Global Minimalista ---
# Fundo Branco, Texto Escuro, Botões Clean
STYLE_SHEET_WIZARD = """
    QWizard { 
        background-color: #FFFFFF; 
        color: #222222; 
    }
    QWizardPage {
        background-color: #FFFFFF;
        margin: 25px; 
    }
    QLabel { 
        font-family: "Segoe UI";
        font-size: 14px; 
        color: #333333; 
    }
    QLabel#titulo {
        font-size: 22px;
        font-weight: bold;
        color: #111111;
        margin-bottom: 5px;
    }
    QLabel#subtitulo {
        font-size: 14px;
        color: #666666;
        margin-bottom: 20px;
    }
    QLineEdit { 
        padding: 12px; 
        border-radius: 8px; 
        border: 1px solid #CCCCCC; 
        background-color: #FAFAFA;
        color: #222222;
        font-family: "Consolas", monospace;
    }
    QLineEdit:focus { 
        border: 2px solid #444444; 
        background-color: #FFFFFF;
    }
    QPushButton {
        background-color: #FFFFFF;
        border: 1px solid #CCCCCC;
        border-radius: 8px;
        padding: 15px;
        min-width: 100px;
        font-weight: 600;
        color: #333333;
    }
    QPushButton:hover {
        background-color: #F0F0F0;
        border-color: #999999;
        color: #000000;
    }
    QPushButton:pressed {
        background-color: #E0E0E0;
    }
    QPushButton[class="destaque"] {
        background-color: #444444;
        color: #FFFFFF;
        border: none;
    }
    QPushButton[class="destaque"]:hover {
        background-color: #222222;
    }
"""

class PaginaEscolha(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("") # Remove título padrão do Qt
        self.setSubTitle("")
        self.escolha = None # "tenho" ou "ajuda"

        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Cabeçalho Personalizado
        lbl_titulo = QLabel("Configuração do Modo Online")
        lbl_titulo.setObjectName("titulo")
        layout.addWidget(lbl_titulo)

        lbl_desc = QLabel("Para identificar aves com Inteligência Artificial, precisamos de uma Chave de API do Google Gemini. É gratuito e seguro.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setObjectName("subtitulo")
        layout.addWidget(lbl_desc)
        
        layout.addSpacing(10)

        # Opção 1: Já tenho
        self.btn_tenho = QPushButton("🔑  Já tenho uma Chave de API")
        self.btn_tenho.clicked.connect(lambda: self._escolher("tenho"))
        layout.addWidget(self.btn_tenho)

        # Opção 2: Preciso de ajuda
        self.btn_ajuda = QPushButton("❓  Preciso criar uma Chave (Ajuda)")
        self.btn_ajuda.clicked.connect(lambda: self._escolher("ajuda"))
        layout.addWidget(self.btn_ajuda)
        
        layout.addStretch()
        self.setLayout(layout)

    def _escolher(self, opcao):
        self.escolha = opcao
        self.wizard().next()

    def nextId(self):
        # Lógica de Ramificação
        if self.escolha == "tenho":
            return WizardConfig.ID_SALVAR
        elif self.escolha == "ajuda":
            return WizardConfig.ID_TUTORIAL
        return -1 # Fica na mesma página se nada escolhido (tecnicamente next() só chama se validar)
    
    def isComplete(self):
        return self.escolha is not None

class PaginaTutorial(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("")
        
        layout = QVBoxLayout()
        lbl_titulo = QLabel("Criando sua Chave")
        lbl_titulo.setObjectName("titulo")
        layout.addWidget(lbl_titulo)
        
        # Instruções Simplificadas
        instrucoes = QLabel(
            "1. Acesse o **Google AI Studio**.\n"
            "2. Faça login com sua conta Google.\n"
            "3. Clique no botão azul **'Get API key'**.\n"
            "4. Clique em **'Create API key'**.\n"
            "5. Copie o código gerado (começa com 'AIza')."
        )
        instrucoes.setTextFormat(Qt.MarkdownText)
        instrucoes.setWordWrap(True)
        layout.addWidget(instrucoes)
        
        layout.addSpacing(20)
        
        btn_link = QPushButton("Abrir Google AI Studio no Navegador ↗️")
        btn_link.setProperty("class", "destaque")
        btn_link.setCursor(Qt.PointingHandCursor)
        btn_link.clicked.connect(self._abrir_link)
        layout.addWidget(btn_link)
        
        layout.addStretch()
        self.setLayout(layout)

    def _abrir_link(self):
        QDesktopServices.openUrl(QUrl("https://aistudio.google.com/app/apikey"))
    
    def nextId(self):
        return WizardConfig.ID_SALVAR

class PaginaSalvar(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("")
        
        layout = QVBoxLayout()
        lbl_titulo = QLabel("Validar e Salvar")
        lbl_titulo.setObjectName("titulo")
        layout.addWidget(lbl_titulo)
        
        lbl_inst = QLabel("Cole sua chave abaixo. Ela será salva de forma segura no seu computador.")
        layout.addWidget(lbl_inst)

        self.input_chave = QLineEdit()
        self.input_chave.setPlaceholderText("Cole aqui: AIzaSy...")
        self.input_chave.setEchoMode(QLineEdit.Password) # Oculta por padrão
        self.input_chave.textChanged.connect(self.completeChanged)
        layout.addWidget(self.input_chave)
        
        # Checkbox para mostrar senha (opcional, mas útil)
        # Simplificando para v0.3.5

        layout.addStretch()
        self.setLayout(layout)

    def isComplete(self):
        # Validação básica: tamanho mínimo da chave AIza...
        texto = self.input_chave.text().strip()
        return len(texto) > 30 and texto.startswith("AIza")

    def validatePage(self):
        chave = self.input_chave.text().strip()
        try:
            # Salva no Keyring
            keyring.set_password("iBirder_Gemini_Key", "user", chave)
            
            # Marca flag no config (opcional, user pediu)
            config = carregar_config()
            config["modo_online_configurado"] = True
            salvar_config(config)
            
            return True
        except Exception as e:
            from ui.dialogo_aviso import DialogoAviso
            DialogoAviso("Erro", f"Falha ao salvar chave: {e}", self, tipo="erro").exec()
            return False

class WizardConfig(QWizard):
    # IDs das páginas para navegação customizada
    ID_ESCOLHA = 0
    ID_TUTORIAL = 1
    ID_SALVAR = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuração Online - iBirder")
        self.setWizardStyle(QWizard.ClassicStyle)
        self.setFixedSize(600, 400) # Tamanho confortável
        
        # Configura IDs manuais
        self.setPage(self.ID_ESCOLHA, PaginaEscolha())
        self.setPage(self.ID_TUTORIAL, PaginaTutorial())
        self.setPage(self.ID_SALVAR, PaginaSalvar())
        
        self.setStartId(self.ID_ESCOLHA)
        
        # Botões
        self.setButtonText(QWizard.NextButton, "Próximo")
        self.setButtonText(QWizard.BackButton, "Voltar")
        self.setButtonText(QWizard.FinishButton, "Concluir e Salvar")
        self.setButtonText(QWizard.CancelButton, "Cancelar")
        
        # Estilo
        self.setStyleSheet(STYLE_SHEET_WIZARD)
