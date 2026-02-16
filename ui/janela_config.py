from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFrame, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from core.config import carregar_config, salvar_config
from ui.wizard_config import WizardConfig
from ui.dialogo_aviso import DialogoAviso
import keyring

class JanelaConfig(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações - iBirder")
        self.resize(500, 350)
        self.config = carregar_config()
        self.parent_window = parent 
        
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
        grupo_identificacao = QGroupBox("CHAVE GOOGLE AI (GEMINI)")
        layout_id = QVBoxLayout()
        layout_id.setSpacing(15)
        
        # Botão Chave API
        btn_chave = QPushButton("Gerenciar Chave de API")
        btn_chave.clicked.connect(self._abrir_wizard_chave)
        layout_id.addWidget(btn_chave)
        
        # Botão Resetar Online
        btn_reset_online = QPushButton("Apagar Chave Salva")
        btn_reset_online.setToolTip("Remove a chave de API e exige reconfiguração.")
        btn_reset_online.setStyleSheet("color: #D32F2F; border-color: #EF9A9A;") 
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
        
        # Botão Salvar
        btn_salvar = QPushButton("Fechar")
        btn_salvar.setProperty("class", "acao")
        btn_salvar.clicked.connect(self._salvar_e_fechar)
        layout.addWidget(btn_salvar, alignment=Qt.AlignRight)

    def _salvar_e_fechar(self):
        # Apenas fecha, pois não há mais modos para salvar aqui
        self.accept()

    def _resetar_online(self):
        """Apaga chave do keyring."""
        try:
            keyring.delete_password("iBirder_Gemini_Key", "user")
        except keyring.errors.PasswordDeleteError:
            pass 
            
        DialogoAviso("Sucesso", "Chave de API removida.", self).exec()

    def _resetar_atalho(self):
        self.config["pular_pergunta_atalho"] = False
        salvar_config(self.config)
        DialogoAviso("Sucesso", "O aviso de atalho foi reativado.", self).exec()

    def _abrir_wizard_chave(self):
        wizard = WizardConfig(self)
        wizard.exec()

    def _aplicar_estilo(self):
        # Estilo Unificado v0.3.5
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            QLabel, QGroupBox {
                color: #2c3e50; 
                background-color: transparent;
                font-family: "Segoe UI";
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 20px;
                padding-top: 15px;
                background-color: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                background-color: #FFFFFF;
                color: #2c3e50;
            }
            QLabel {
                font-size: 13px;
            }
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                padding: 8px 15px;
                color: #333333;
                font-weight: 600;
                font-family: "Segoe UI";
            }
            QPushButton:hover {
                background-color: #F8F8F8;
                border-color: #999999;
                color: #000000;
            }
            /* Botão Salvar e Fechar - Destaque (v0.5.2) */
            QPushButton[class="acao"] {
                background-color: #2c3e50; 
                color: #FFFFFF;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton[class="acao"]:hover {
                background-color: #1a252f;
            }
        """)
