from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class DialogoAviso(QDialog):
    def __init__(self, titulo, mensagem, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aviso - iBirder")
        self.setFixedSize(400, 200)
        
        self.titulo = titulo
        self.mensagem = mensagem
        
        self._configurar_ui()
        self._aplicar_estilo()

    def _configurar_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Título
        lbl_titulo = QLabel(self.titulo)
        lbl_titulo.setAlignment(Qt.AlignLeft)
        # Fonte um pouco maior que o corpo
        font_titulo = QFont("Segoe UI", 14, QFont.Bold)
        lbl_titulo.setFont(font_titulo)
        layout.addWidget(lbl_titulo)
        
        # Mensagem
        lbl_msg = QLabel(self.mensagem)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("color: #444444; font-size: 13px;")
        layout.addWidget(lbl_msg)
        
        layout.addStretch()
        
        # Botão OK
        self.btn_ok = QPushButton("Entendi")
        self.btn_ok.setFixedSize(100, 40)
        self.btn_ok.clicked.connect(self.accept)
        # Alinhado à direita
        layout.addWidget(self.btn_ok, alignment=Qt.AlignRight)

    def _aplicar_estilo(self):
        # Estilo Unificado v0.3.7 (White Theme)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            QLabel {
                color: #222222;
                font-family: "Segoe UI";
            }
            QPushButton {
                background-color: #444444; /* Destaque sutil para ação principal */
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #222222;
            }
            QPushButton:pressed {
                background-color: #000000;
            }
        """)
