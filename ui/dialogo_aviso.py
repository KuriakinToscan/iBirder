from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.base.base_dialog import BaseDialog

class DialogoAviso(BaseDialog):
    def __init__(self, titulo, mensagem, parent=None, tipo="info", botoes=None):
        super().__init__(titulo, parent)
        self.setFixedSize(450, 220)
        
        self.titulo = titulo
        self.mensagem = mensagem
        self.tipo = tipo # "info", "erro", "pergunta"
        self.botoes = botoes
        
        self._configurar_ui()
        self._aplicar_estilo()

    def _configurar_ui(self):
        layout = self.main_layout
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 30)
        
        # Título
        lbl_titulo = QLabel(self.titulo)
        lbl_titulo.setAlignment(Qt.AlignLeft)
        font_titulo = QFont("Segoe UI", 16, QFont.Bold)
        lbl_titulo.setFont(font_titulo)
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
        
        if self.botoes:
            # Modo Personalizado (v0.6.4)
            for btn_data in self.botoes:
                btn = QPushButton(btn_data["texto"])
                btn.setCursor(Qt.PointingHandCursor)
                btn.setFixedSize(120, 45)
                
                if btn_data.get("destaque"):
                    btn.setProperty("class", "acao")
                    
                funcao = btn_data.get("funcao")
                if funcao:
                    # Conecta e fecha o diálogo
                    btn.clicked.connect(lambda f=funcao: (f(), self.accept()))
                else:
                    # Padrão é fechar
                    btn.clicked.connect(self.accept)
                    
                layout_botoes.addWidget(btn)
                
        elif self.tipo == "pergunta":
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
        # Estilo Estrito conforme REGRA 2 (#F8F9FA / #2C3E50)
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }
            QLabel {
                color: #2C3E50;
                font-family: "Segoe UI";
            }
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                color: #2C3E50;
                font-weight: 600;
                font-size: 13px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #F3F4F6;
                border-color: #9CA3AF;
            }
            QPushButton[class="acao"] {
                background-color: #374151; /* Dark Gray do App */
                color: #FFFFFF;
                border: none;
            }
            QPushButton[class="acao"]:hover {
                background-color: #1F2937;
            }
        """)
