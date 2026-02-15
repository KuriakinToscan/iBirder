from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class DialogoAviso(QDialog):
    def __init__(self, titulo, mensagem, parent=None, tipo="info"):
        super().__init__(parent)
        self.setWindowTitle(f"iBirder - {titulo}")
        self.setFixedSize(450, 220)
        
        self.titulo = titulo
        self.mensagem = mensagem
        self.tipo = tipo # "info", "erro", "pergunta"
        
        self._configurar_ui()
        self._aplicar_estilo()

    def _configurar_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 30)
        
        # Título
        lbl_titulo = QLabel(self.titulo)
        lbl_titulo.setAlignment(Qt.AlignLeft)
        font_titulo = QFont("Segoe UI", 16, QFont.Bold)
        lbl_titulo.setFont(font_titulo)
        # Forçar cor escura visualmente direto no widget além do QSS
        layout.addWidget(lbl_titulo)
        
        # Mensagem
        lbl_msg = QLabel(self.mensagem)
        lbl_msg.setWordWrap(True)
        lbl_msg.setFont(QFont("Segoe UI", 11))
        layout.addWidget(lbl_msg)
        
        layout.addStretch()
        
        # Botões
        layout_botoes = QHBoxLayout()
        layout_botoes.setSpacing(15)
        layout_botoes.addStretch()
        
        if self.tipo == "pergunta":
            btn_nao = QPushButton("Não")
            btn_nao.setCursor(Qt.PointingHandCursor)
            btn_nao.setFixedSize(100, 45)
            btn_nao.clicked.connect(self.reject)
            
            btn_sim = QPushButton("Sim")
            btn_sim.setCursor(Qt.PointingHandCursor)
            btn_sim.setFixedSize(100, 45)
            btn_sim.setProperty("class", "acao") # Destaque
            btn_sim.clicked.connect(self.accept)
            
            layout_botoes.addWidget(btn_nao)
            layout_botoes.addWidget(btn_sim)
        else:
            # Info / Erro / Aviso -> Apenas OK
            btn_ok = QPushButton("Entendi")
            btn_ok.setCursor(Qt.PointingHandCursor)
            btn_ok.setFixedSize(120, 45)
            btn_ok.setProperty("class", "acao")
            btn_ok.clicked.connect(self.accept)
            layout_botoes.addWidget(btn_ok)
            
        layout.addLayout(layout_botoes)

    def _aplicar_estilo(self):
        # Estilo Estrito v0.5.3 (Dark Text, White BG)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            QLabel {
                color: #2c3e50; /* Cinza Escuro/Preto */
                font-family: "Segoe UI";
            }
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #BDC3C7;
                border-radius: 6px;
                color: #2c3e50;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #ECF0F1;
                border-color: #95A5A6;
            }
            QPushButton[class="acao"] {
                background-color: #2c3e50;
                color: #FFFFFF;
                border: none;
            }
            QPushButton[class="acao"]:hover {
                background-color: #34495E;
            }
        """)
