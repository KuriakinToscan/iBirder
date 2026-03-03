import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QCheckBox, 
                               QScrollArea, QWidget, QMessageBox, QFrame)
from PySide6.QtCore import Qt
try:
    from core.style_manager import StyleManager
except ImportError:
    StyleManager = None

class ExifConfigDialog(QDialog):
    def __init__(self, parent=None, dados=None, tem_gps_nativo=False):
        super().__init__(parent)
        self.setWindowTitle("Configurar Gravação de Dados na Fotografia")
        self.setMinimumWidth(480)
        self.setMinimumHeight(640)
        self.dados = dados or {}
        self.tem_gps_nativo = tem_gps_nativo
        self.opcoes_selecionadas = {}

        self._setup_ui()
        if StyleManager: StyleManager.setup_window_theme(self)

    def _setup_ui(self):
        # O Fundo da janela usará a cor base do app
        self.setStyleSheet("QDialog { background-color: #f7f7f9; }")
        
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)
        layout_principal.setSpacing(15)

        # Cabeçalho
        lbl_instrucao = QLabel("Selecione quais dados devem ser gravados permanentemente na fotografia:")
        lbl_instrucao.setWordWrap(True)
        lbl_instrucao.setProperty("class", "lbl-titulo-sessao")
        lbl_instrucao.style().unpolish(lbl_instrucao)
        lbl_instrucao.style().polish(lbl_instrucao)
        layout_principal.addWidget(lbl_instrucao)

        # Card Central (Fundo Branco, Borda Suave, Sombra)
        card_central = QFrame()
        card_central.setProperty("class", "painel")
        if StyleManager: StyleManager.apply_shadow(card_central)
        layout_card = QVBoxLayout(card_central)
        layout_card.setContentsMargins(15, 15, 15, 15)

        # Scroll Area limpo por cima do Card
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        container_checks = QWidget()
        container_checks.setStyleSheet("QWidget { background: transparent; }")
        self.layout_checks = QVBoxLayout(container_checks)
        self.layout_checks.setSpacing(12)

        self.lista_opcoes = [
            ("Nome Científico", "nome_cientifico", True),
            ("Nome Comum", "nome_comum", True),
            ("Nome em Inglês", "nome_ingles", True),
            ("Classe", "classe", True),
            ("Ordem", "ordem", True),
            ("Família", "familia", True),
            ("Gênero", "genero", True),
            ("Status IUCN", "iucn_status", True),
            ("Status Nacional", "status_icmbio", True),
            ("Status CITES", "status_cites", True),
            ("País", "pais", True),
            ("Estado", "estado", True),
            ("Município", "municipio", True),
            ("Bioma", "bioma", True),
            ("Endêmico do Brasil", "endemismo", True),
            ("Coordenadas Geográficas (GPS)", "coord_gps", True)  
        ]

        self.checkboxes = {}

        # Estilo raw das checkboxes customizadas para leitura elegante
        check_style = """
            QCheckBox {
                font-family: 'Segoe UI'; font-size: 14px; color: #374151;
            }
            QCheckBox::indicator {
                width: 18px; height: 18px; border-radius: 4px;
                border: 1px solid #9CA3AF;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #1F2937;
                border: 1px solid #1F2937;
            }
            QCheckBox:disabled { color: #9CA3AF; }
        """

        for texto_exibicao, chave_dict, default_checked in self.lista_opcoes:
            valor_atual = self.dados.get(chave_dict, "N/A")
            
            if chave_dict == "genero" and valor_atual == "N/A":
                nome_cientifico = self.dados.get("nome_cientifico", "")
                if nome_cientifico:
                    valor_atual = nome_cientifico.split()[0]
            
            if chave_dict == "coord_gps":
                lat = self.dados.get("latitude")
                lon = self.dados.get("longitude")
                if lat and lon:
                    valor_atual = f"{lat:.5f}, {lon:.5f}"
                else:
                    valor_atual = "Não disponíveis na sessão"

            cb = QCheckBox(f"{texto_exibicao}: {valor_atual}")
            cb.setStyleSheet(check_style)
            
            if chave_dict == "coord_gps":
                if self.tem_gps_nativo:
                    cb.setChecked(False)
                    cb.setEnabled(False)
                    cb.setText(f"{texto_exibicao}: [Protegido - Imagem possui GPS original]")
                elif valor_atual == "Não disponíveis na sessão":
                    cb.setChecked(False)
                    cb.setEnabled(False)
                else:
                    cb.setChecked(default_checked)
            else:
                if valor_atual == "N/A" or not valor_atual:
                    cb.setChecked(False)
                    cb.setEnabled(False)
                else:
                    cb.setChecked(default_checked)

            self.checkboxes[chave_dict] = cb
            self.layout_checks.addWidget(cb)

        self.layout_checks.addStretch()
        scroll.setWidget(container_checks)
        layout_card.addWidget(scroll)
        layout_principal.addWidget(card_central)

        # Resumo de Alerta usando CSS class
        if self.tem_gps_nativo:
            lbl_aviso_gps = QLabel("⚠️ A imagem original já possui coordenadas GPS. Elas foram protegidas contra sobrescrita manual.")
            lbl_aviso_gps.setWordWrap(True)
            lbl_aviso_gps.setProperty("class", "lbl-titulo-sessao")
            lbl_aviso_gps.style().unpolish(lbl_aviso_gps)
            lbl_aviso_gps.style().polish(lbl_aviso_gps)
            lbl_aviso_gps.setStyleSheet("color: #B45309; font-size: 13px; background-color: #FEF3C7; padding: 10px; border-radius: 6px; border: 1px solid #FDE68A;")
            layout_principal.addWidget(lbl_aviso_gps)

        # Botões Invertidos (Padrão Windows) - Cancelar esq, Gravar dir
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        btn_cancelar.setProperty("class", "btn-acao-alinhado")
        btn_cancelar.style().unpolish(btn_cancelar)
        btn_cancelar.style().polish(btn_cancelar)
        btn_cancelar.setStyleSheet("background-color: transparent; border: 1px solid #9CA3AF; color: #4B5563;")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_gravar = QPushButton("Gravar Dados na Fotografia")
        btn_gravar.setCursor(Qt.PointingHandCursor)
        btn_gravar.setProperty("class", "btn-acao-alinhado")
        btn_gravar.style().unpolish(btn_gravar)
        btn_gravar.style().polish(btn_gravar)
        btn_gravar.clicked.connect(self._confirmar_gravacao)
        
        layout_botoes.addWidget(btn_cancelar)
        layout_botoes.addWidget(btn_gravar)
        
        layout_principal.addLayout(layout_botoes)

    def _confirmar_gravacao(self):
        for chave, cb in self.checkboxes.items():
            self.opcoes_selecionadas[chave] = cb.isChecked()
        self.accept()

    def get_selected_fields(self):
        """Retorna o dicionário de campos selecionados pelo usuário (v0.8.8)."""
        return self.opcoes_selecionadas
