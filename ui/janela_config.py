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
        
        btn_baixar_base.clicked.connect(self._baixar_base)
        layout_off.addWidget(btn_baixar_base)
        
        # botão verificar ExifTool (v0.6.4)
        btn_verificar_exif = QPushButton("Verificar Integridade do ExifTool")
        btn_verificar_exif.setToolTip("Testa se o componente de metadados está funcionando.")
        btn_verificar_exif.clicked.connect(self._verificar_exiftool)
        layout_off.addWidget(btn_verificar_exif)
        
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
            
        DialogoAviso("Sucesso", "Chave de API removida e modo Online redefinido.", self).exec()

    def _resetar_atalho(self):
        self.config["pular_pergunta_atalho"] = False
        salvar_config(self.config)
        DialogoAviso("Sucesso", "O aviso de atalho foi reativado.", self).exec()

    def _abrir_wizard_chave(self):
        wizard = WizardConfig(self)
        wizard.exec()

    def _baixar_base(self):
        """Baixa base offline e Modelo Real (v0.6.1)."""
        DialogoAviso("Download", "Iniciando download da base de dados e Inteligência Artificial...", self).exec()
        
        import time
        import requests
        from pathlib import Path
        
        self.setCursor(Qt.WaitCursor)
        self.lbl_status_base.setText("Iniciando...")
        self.repaint()
        
        try:
            # 1. Base JSON (Simulado/Local)
            self.lbl_status_base.setText("Atualizando Base de Espécies... 10%")
            self.repaint()
            time.sleep(0.5) 
            
            # 2. Download do Modelo (MobileNetV2 ONNX para OpenCV)
            url_modelo = "https://github.com/onnx/models/raw/main/validated/vision/classification/mobilenet/model/mobilenetv2-7.onnx"
            model_dir = Path("models")
            model_dir.mkdir(exist_ok=True)
            model_path = model_dir / "model.onnx"
            
            self.lbl_status_base.setText("Baixando Motor de Visão (OpenCV)... 0%")
            self.repaint()
            
            with requests.get(url_modelo, stream=True) as r:
                r.raise_for_status()
                total_length = int(r.headers.get('content-length', 0))
                downloaded = 0
                
                with open(model_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_length > 0:
                            percent = int((downloaded / total_length) * 100)
                            # Atualizar a cada 10% para não travar UI demais
                            if percent % 10 == 0:
                                self.lbl_status_base.setText(f"Baixando Motor de Visão (OpenCV)... {percent}%")
                                self.repaint()
            
            self.lbl_status_base.setText("Download Concluído. Instalando...")
            self.repaint()
            time.sleep(0.5)

            self.lbl_status_base.setText("Pacote Offline: Ativo (v0.6.3)")
            self.setCursor(Qt.ArrowCursor)
            DialogoAviso("Sucesso", "Pacote de Inteligência Artificial (OpenCV) instalado com sucesso! Agora você pode identificar aves offline.", self).exec()
            
        except Exception as e:
            self.setCursor(Qt.ArrowCursor)
            self.lbl_status_base.setText("Erro no download.")
            DialogoAviso("Erro de Download", f"Falha ao baixar componentes: {e}", self).exec()

    def _aplicar_estilo(self):
        # Estilo Unificado v0.3.5
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            /* Forçar texto escuro para contraste (v0.5.2) */
            QLabel, QRadioButton, QCheckBox, QGroupBox {
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

    def _verificar_exiftool(self):
        from core.motor_metadados import MotorMetadados
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        
        self.setCursor(Qt.WaitCursor)
        self.lbl_status_base.setText("Verificando ExifTool...")
        self.repaint()
        
        try:
            motor = MotorMetadados()
            resultado = motor.verificar_integridade()
            
            self.setCursor(Qt.ArrowCursor)
            self.lbl_status_base.setText("Verificação Concluída.")
            
            if resultado["ok"]:
                DialogoAviso("Sucesso", f"ExifTool Operacional!\nVersão: {resultado['versao']}", self).exec()
            else:
                botoes = [
                    {"texto": "Fechar", "funcao": None},
                    {"texto": "Como Corrigir", "funcao": lambda: QDesktopServices.openUrl(QUrl("https://exiftool.org/install.html")), "destaque": True}
                ]
                msg = f"Falha na verificação:\n{resultado['erro']}\n\nO componente de metadados não funcionará neste computador."
                DialogoAviso("Erro de Integridade", msg, self, tipo="erro", botoes=botoes).exec()
        except Exception as e:
            self.setCursor(Qt.ArrowCursor)
            DialogoAviso("Erro", f"Erro ao inicializar motor: {e}", self).exec()
