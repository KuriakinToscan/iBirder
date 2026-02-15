from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QMessageBox, QFrame, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from core.config import carregar_config, salvar_config
from ui.wizard_config import WizardConfig
import keyring

class JanelaConfig(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações - iBirder")
        self.resize(500, 450)
        self.config = carregar_config()
        self.parent_window = parent # Referência para callback se necessário
        
        self._configurar_ui()
        self._aplicar_estilo()

    def _configurar_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(25)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Título
        lbl_titulo = QLabel("Configurações")
        lbl_titulo.setFont(QFont("Segoe UI", 18, QFont.Bold))
        layout.addWidget(lbl_titulo)
        
        # Grupo: Identificação
        grupo_identificacao = QGroupBox("IDENTIFICAÇÃO")
        layout_id = QVBoxLayout()
        layout_id.setSpacing(15)
        
        # Status do Modo Atual
        modo_atual = self.config.get("modo_operacao", "Não definido")
        if modo_atual == "online": modo_exibicao = "Online (Preciso)"
        elif modo_atual == "offline": modo_exibicao = "Offline (Rápido)"
        else: modo_exibicao = "Automático/Indefinido"
        
        self.lbl_modo = QLabel(f"Modo Padrão: <b>{modo_exibicao}</b>")
        layout_id.addWidget(self.lbl_modo)
        
        # Botão Resetar Escolha
        btn_reset_modo = QPushButton("Redefinir Modo Padrão")
        btn_reset_modo.setToolTip("O app perguntará novamente na próxima inicialização.")
        btn_reset_modo.clicked.connect(self._resetar_modo)
        layout_id.addWidget(btn_reset_modo)
        
        # Botão Chave API
        btn_chave = QPushButton("Gerenciar Chave Google AI")
        btn_chave.clicked.connect(self._abrir_wizard_chave)
        layout_id.addWidget(btn_chave)
        
        # Botão Resetar Online (Novo v0.3.4)
        btn_reset_online = QPushButton("Apagar Configurações Online")
        btn_reset_online.setToolTip("Apaga a chave de API e esquece a escolha do modo.")
        btn_reset_online.setStyleSheet("color: #D32F2F;") # Vermelho alerta
        btn_reset_online.clicked.connect(self._resetar_online)
        layout_id.addWidget(btn_reset_online)
        
        grupo_identificacao.setLayout(layout_id)
        layout.addWidget(grupo_identificacao)
        
        # Grupo: Sistema
        grupo_sistema = QGroupBox("SISTEMA")
        layout_sys = QVBoxLayout()
        
        # Botão Resetar Atalho
        btn_reset_atalho = QPushButton("Redefinir Aviso de Atalho")
        btn_reset_atalho.setToolTip("Volta a perguntar se deseja criar atalho na área de trabalho.")
        btn_reset_atalho.clicked.connect(self._resetar_atalho)
        layout_sys.addWidget(btn_reset_atalho)
        
        grupo_sistema.setLayout(layout_sys)
        layout.addWidget(grupo_sistema)
        
        layout.addStretch()
        
        # Botão Fechar
        btn_fechar = QPushButton("Fechar")
        btn_fechar.setProperty("class", "acao")
        btn_fechar.clicked.connect(self.accept)
        layout.addWidget(btn_fechar, alignment=Qt.AlignRight)

    def _resetar_modo(self):
        self.config["modo_operacao"] = None
        self.config["lembrar_modo"] = False
        salvar_config(self.config)
        self.lbl_modo.setText("Modo Padrão: <b>Redefinido</b>")
        QMessageBox.information(self, "Sucesso", "Na próxima vez, perguntaremos qual modo usar.")

    def _resetar_online(self):
        """Apaga chave do keyring e limpa preferência online."""
        try:
            # Apaga do Keyring
            keyring.delete_password("iBirder_Gemini_Key", "user")
        except keyring.errors.PasswordDeleteError:
            pass # Senha não existia
            
        # Limpa config se for online
        if self.config.get("modo_operacao") == "online":
            self.config["modo_operacao"] = None
            self.config["lembrar_modo"] = False
            salvar_config(self.config)
            self.lbl_modo.setText("Modo Padrão: <b>Redefinido</b>")
            
        QMessageBox.information(self, "Sucesso", "Chave de API removida e modo Online redefinido.")

    def _resetar_atalho(self):
        self.config["pular_pergunta_atalho"] = False
        salvar_config(self.config)
        QMessageBox.information(self, "Sucesso", "O aviso de atalho foi reativado.")

    def _abrir_wizard_chave(self):
        wizard = WizardConfig(self)
        wizard.exec()

    def _aplicar_estilo(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 20px;
                padding-top: 15px;
                background-color: #FFFFFF;
                color: #757575;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                background-color: #FFFFFF;
            }
            QLabel {
                color: #222222;
                font-size: 13px;
            }
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #BDBDBD;
                border-radius: 6px;
                padding: 8px 15px;
                color: #424242;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #EEEEEE;
                border-color: #9E9E9E;
                color: #212121;
            }
            QPushButton[class="acao"] {
                background-color: #444444;
                color: white;
                border: none;
            }
            QPushButton[class="acao"]:hover {
                background-color: #222222;
            }
        """)
