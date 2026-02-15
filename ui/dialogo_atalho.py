from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QLabel, QCheckBox, QHBoxLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class DialogoAtalho(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuração - iBirder")
        self.setFixedSize(450, 250)
        self.criar_atalho = False
        self.nao_perguntar = False
        
        self._configurar_ui()
        self._aplicar_estilo()

    def _configurar_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Título
        lbl_titulo = QLabel("Criar Atalho")
        lbl_titulo.setAlignment(Qt.AlignLeft)
        lbl_titulo.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(lbl_titulo)
        
        # Texto Descritivo
        lbl_desc = QLabel("Deseja criar um atalho do iBirder na sua Área de Trabalho para facilitar o acesso?")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #444444; font-size: 14px;")
        layout.addWidget(lbl_desc)
        
        layout.addStretch()
        
        # Checkbox
        self.cb_nao_perguntar = QCheckBox("Não perguntar novamente")
        layout.addWidget(self.cb_nao_perguntar)
        
        # Botões (Sim/Não na direita)
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()
        
        self.btn_nao = QPushButton("Não")
        self.btn_nao.setFixedSize(100, 40)
        self.btn_nao.clicked.connect(self.reject)
        layout_botoes.addWidget(self.btn_nao)

        self.btn_sim = QPushButton("Sim")
        self.btn_sim.setFixedSize(100, 40)
        self.btn_sim.setProperty("class", "destaque") # Para estilizar diferente se quiser
        self.btn_sim.clicked.connect(self.accept)
        layout_botoes.addWidget(self.btn_sim)
        
        layout.addLayout(layout_botoes)

    def accept(self):
        self.criar_atalho = True
        self.nao_perguntar = self.cb_nao_perguntar.isChecked()
        super().accept()

    def reject(self):
        self.criar_atalho = False
        self.nao_perguntar = self.cb_nao_perguntar.isChecked()
        super().reject()

    def _aplicar_estilo(self):
        # Estilo Unificado v0.3.5/v0.3.6 (White Theme)
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
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
                color: #333333;
            }
            QPushButton:hover {
                border-color: #999999;
                color: #000000;
                background-color: #F8F8F8;
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
            QCheckBox {
                color: #666666;
                spacing: 8px;
                font-size: 13px;
            }
        """)
