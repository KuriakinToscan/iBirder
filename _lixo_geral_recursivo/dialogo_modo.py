from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QLabel, QCheckBox, QHBoxLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon

class DialogoModo(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("iBirder - Bem-vindo")
        self.setFixedSize(450, 350)
        self.modo_selecionado = None # "online" ou "offline"
        self.lembrar = False
        
        self._configurar_ui()
        self._aplicar_estilo()

    def _configurar_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Título
        lbl_titulo = QLabel("Escolha o Modo de Identificação")
        lbl_titulo.setAlignment(Qt.AlignCenter)
        lbl_titulo.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(lbl_titulo)
        
        lbl_subtitulo = QLabel("Como você quer usar o iBirder hoje?")
        lbl_subtitulo.setAlignment(Qt.AlignCenter)
        lbl_subtitulo.setStyleSheet("color: #616161;")
        layout.addWidget(lbl_subtitulo)
        
        layout.addSpacing(10)
        
        # Botões Principais
        self.btn_online = QPushButton("Modo Online (Preciso)")
        self.btn_online.setToolTip("Usa Inteligência Artificial do Google. Requer internet.")
        self.btn_online.clicked.connect(lambda: self._finalizar("online"))
        layout.addWidget(self.btn_online)
        
        self.btn_offline = QPushButton("Modo Offline (Rápido)")
        self.btn_offline.setToolTip("Usa base local limitada. Não requer internet.")
        self.btn_offline.clicked.connect(lambda: self._finalizar("offline"))
        layout.addWidget(self.btn_offline)
        
        layout.addStretch()
        
        # Checkbox "Lembrar"
        self.cb_lembrar = QCheckBox("Lembrar minha escolha e não perguntar novamente")
        layout.addWidget(self.cb_lembrar)

    def _finalizar(self, modo):
        self.modo_selecionado = modo
        self.lembrar = self.cb_lembrar.isChecked()
        self.accept()

    def _aplicar_estilo(self):
        # Estilo Unificado v0.3.5 (Match Wizard)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            QLabel {
                color: #222222;
                font-family: "Segoe UI";
            }
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
                font-weight: 600;
                color: #333333;
                text-align: left;
                padding-left: 20px;
            }
            QPushButton:hover {
                border-color: #999999;
                color: #000000;
                background-color: #F8F8F8;
            }
            QPushButton:pressed {
                background-color: #E0E0E0;
            }
            QCheckBox {
                color: #666666;
                spacing: 8px;
            }
        """)
