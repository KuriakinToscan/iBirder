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
        
        # Grupo: Preferências de Conexão (v0.5.1)
        grupo_conexao = QGroupBox("PREFERÊNCIAS DE CONEXÃO")
        layout_con = QVBoxLayout()
        layout_con.setSpacing(10)
        
        from PySide6.QtWidgets import QRadioButton, QButtonGroup
        
        self.radio_online = QRadioButton("Online (Google Gemini)")
        self.radio_online.setToolTip("Requer chave de API e Internet. Identificação mais precisa.")
        self.radio_offline = QRadioButton("Offline (Processamento Local)")
        self.radio_offline.setToolTip("Usa base de dados interna. Ideal para campo sem internet.")
        
        # Estado Inicial
        modo_atual = self.config.get("modo_operacao", "offline") # Default offline se none
        if modo_atual == "online":
            self.radio_online.setChecked(True)
        else:
            self.radio_offline.setChecked(True)
            
        # Conectar mudanças
        self.group_modo = QButtonGroup(self)
        self.group_modo.addButton(self.radio_online)
        self.group_modo.addButton(self.radio_offline)
        
        layout_con.addWidget(self.radio_online)
        layout_con.addWidget(self.radio_offline)
        
        lbl_info_offline = QLabel("Nota: O modo offline utiliza o banco de dados interno e modelos locais.")
        lbl_info_offline.setStyleSheet("color: #757575; font-style: italic; font-size: 11px;")
        lbl_info_offline.setWordWrap(True)
        layout_con.addWidget(lbl_info_offline)
        
        grupo_conexao.setLayout(layout_con)
        layout.addWidget(grupo_conexao)

        # Grupo: Identificação (Mantendo botões de chave, mas removendo infos antigas de modo se redundante)
        grupo_identificacao = QGroupBox("CHAVES E DADOS")
        layout_id = QVBoxLayout()
        layout_id.setSpacing(15)
        
        # Botão Chave API
        btn_chave = QPushButton("Gerenciar Chave Google AI")
        btn_chave.clicked.connect(self._abrir_wizard_chave)
        layout_id.addWidget(btn_chave)
        
        # Botão Resetar Online
        btn_reset_online = QPushButton("Apagar Chave de API")
        btn_reset_online.setToolTip("Remove a chave de API salva.")
        btn_reset_online.setStyleSheet("color: #D32F2F; border-color: #EF9A9A;") 
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
        
        # Botão Salvar
        btn_salvar = QPushButton("Salvar e Fechar")
        btn_salvar.setProperty("class", "acao")
        btn_salvar.clicked.connect(self._salvar_e_fechar)
        layout.addWidget(btn_salvar, alignment=Qt.AlignRight)

    def _salvar_e_fechar(self):
        # Salvar Modo
        novo_modo = "online" if self.radio_online.isChecked() else "offline"
        self.config["modo_operacao"] = novo_modo
        self.config["lembrar_modo"] = True # Força lembrar, já que é config explicita
        salvar_config(self.config)
        
        self.accept()


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
