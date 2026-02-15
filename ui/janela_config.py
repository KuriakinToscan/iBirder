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
        btn_reset_online = QPushButton("Apagar Chave de API e Redefinir")
        btn_reset_online.setToolTip("Apaga a chave de API e esquece a escolha do modo.")
        btn_reset_online.setStyleSheet("color: #D32F2F; border-color: #EF9A9A;") # Vermelho alerta
        btn_reset_online.clicked.connect(self._resetar_online)
        layout_id.addWidget(btn_reset_online)
        
        grupo_identificacao.setLayout(layout_id)
        layout.addWidget(grupo_identificacao)

        # Grupo: Dados Offline (v0.5.0)
        grupo_offline = QGroupBox("DADOS OFFLINE")
        layout_off = QVBoxLayout()
        
        self.lbl_status_base = QLabel("Base de dados: 5 espécies")
        layout_off.addWidget(self.lbl_status_base)
        
        btn_baixar_base = QPushButton("Baixar Base de Dados Local (~20MB)")
        btn_baixar_base.setToolTip("Simula o download de dados para uso offline.")
        btn_baixar_base.clicked.connect(self._baixar_base)
        layout_off.addWidget(btn_baixar_base)
        
        grupo_offline.setLayout(layout_off)
        layout.addWidget(grupo_offline)
        
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

    def _baixar_base(self):
        """Simula download da base offline (v0.5.0)."""
        QMessageBox.information(self, "Download", "Iniciando download da base de dados...")
        # Simulação
        import time
        self.setCursor(Qt.WaitCursor)
        self.lbl_status_base.setText("Baixando... 20%")
        self.repaint() # Forçar atualização visual
        # time.sleep(0.5) # Bloqueia UI mas ok para simulação rápida
        self.lbl_status_base.setText("Baixando... 80%")
        self.repaint()
        # time.sleep(0.5)
        self.lbl_status_base.setText("Processando...")
        self.repaint()
        
        self.lbl_status_base.setText("Base de dados: Atualizada (Versão 2026.02)")
        self.setCursor(Qt.ArrowCursor)
        QMessageBox.information(self, "Sucesso", "Base de dados offline atualizada com sucesso!")

    def _aplicar_estilo(self):
        # Estilo Unificado v0.3.5
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            QGroupBox {
                font-family: "Segoe UI";
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 20px;
                padding-top: 15px;
                background-color: #FFFFFF;
                color: #555555;
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
                font-family: "Segoe UI";
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
            QPushButton[class="acao"] {
                background-color: #444444;
                color: white;
                border: none;
            }
            QPushButton[class="acao"]:hover {
                background-color: #222222;
            }
        """)
