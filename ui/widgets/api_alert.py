from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QGraphicsOpacityEffect, QVBoxLayout, QFrame
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtGui import QColor, QFont, QIcon

class APIAlertWidget(QFrame):
    """
    Widget dismissible para exibição de alertas de API ausente (IUCN, eBird).
    Emite o sinal alert_dismissed(api_name) quando a Dona Maria clica no 'X'.
    """
    alert_dismissed = Signal(str)  # ex: "IUCN" ou "EBIRD"

    def __init__(self, api_name, message, parent=None):
        super().__init__(parent)
        self.api_name = api_name
        self.setObjectName("api_alert_card")
        
        # Tema Amarelo Pastel / Âmbar (Consistente com MapWidget v0.3.34)
        self.setStyleSheet("""
            QFrame#api_alert_card {
                background-color: rgba(254, 243, 199, 0.95);
                border: 1px solid #F59E0B;
                border-radius: 8px;
            }
            QLabel#alert_msg {
                color: #92400E;
                font-size: 13px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QLabel#alert_sub {
                color: #B45309;
                font-size: 11px;
                font-family: 'Segoe UI';
            }
            QPushButton#btn_close {
                background: transparent;
                border: none;
                color: #92400E;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#btn_close:hover {
                color: #B91C1C; /* Vermelho escuro no hover */
            }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 10, 10)
        main_layout.setSpacing(10)

        # Textos (Vertical)
        v_layout = QVBoxLayout()
        v_layout.setSpacing(2)
        
        self.lbl_msg = QLabel(message, self)
        self.lbl_msg.setObjectName("alert_msg")
        self.lbl_msg.setWordWrap(True)
        
        self.lbl_sub = QLabel("Você pode reativar este aviso em Ferramentas > Configurações de API.", self)
        self.lbl_sub.setObjectName("alert_sub")
        self.lbl_sub.setWordWrap(True)
        
        v_layout.addWidget(self.lbl_msg)
        v_layout.addWidget(self.lbl_sub)
        
        main_layout.addLayout(v_layout)

        main_layout.addStretch()

        # Botão Fechar (Dismiss)
        self.btn_close = QPushButton("✖", self)
        self.btn_close.setObjectName("btn_close")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.clicked.connect(self._iniciar_fade_out)
        
        main_layout.addWidget(self.btn_close, alignment=Qt.AlignTop)

        # Preparar Efeito de Opacidade para a Animação
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)
        
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(400) # 400ms suave
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.OutQuad)
        self.animation.finished.connect(self._ao_animacao_concluida)

    def _iniciar_fade_out(self):
        """Dispara a animação e desabilita o botão imediatamente."""
        self.btn_close.setEnabled(False)
        self.animation.start()

    def _ao_animacao_concluida(self):
        """Conclui o descarte emitindo o sinal para o ConfigManager e se destrói."""
        self.alert_dismissed.emit(self.api_name)
        self.hide()
        self.deleteLater()
