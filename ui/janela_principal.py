import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QFileDialog, QLineEdit,
    QFrame, QStatusBar, QApplication, QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QFont, QDragEnterEvent, QDropEvent, QIcon, QColor, QPainter, QAction, QDesktopServices

# Importações do Core
from core.identificador_nuvem import IdentificadorNuvem
from core.servico_identificacao import ServicoIdentificacao
from core.erros import ChaveApiFaltandoErro
from core.config import carregar_config
from ui.janela_config import JanelaConfig
from ui.janela_manual import JanelaManual
from ui.dialogo_aviso import DialogoAviso
import keyring

class AreaDrop(QLabel):
    def __init__(self, callback_arquivo_carregado):
        super().__init__()
        self.callback = callback_arquivo_carregado
        self.setText("Arraste e solte uma foto aqui\n\nou clique para selecionar")
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumSize(250, 250)
        self.setProperty("class", "dropzone") 
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            caminho = urls[0].toLocalFile()
            self.callback(caminho)

    def mousePressEvent(self, event):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Foto", "", "Imagens (*.png *.jpg *.jpeg)"
        )
        if path:
            self.callback(path)

class AreaReferencia(QLabel):
    def __init__(self):
        super().__init__()
        self.setText("Referência")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(250, 250)
        self.setProperty("class", "referencia")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

class JanelaPrincipal(QMainWindow):
    def __init__(self, nome_icone_janela="logo_ave.png", modo_inicial="online"):
        super().__init__()
        self.nome_icone_janela = nome_icone_janela
        # Modo é sempre online agora (v0.7.0)
        
        self.setWindowTitle("iBirder")
        self.resize(1100, 700)
        
        # Inicialização dos Serviços
        self.id_nuvem = IdentificadorNuvem()
        self.servico = ServicoIdentificacao(self.id_nuvem) 
        
        self.caminho_imagem_atual = None
        self.dados_identificacao_atual = {}

        self._configurar_ui()
        self._aplicar_estilo()

    def _obter_caminho_asset(self, nome_arquivo):
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent / 'assets'
        return str(base_path / nome_arquivo)

    def _configurar_ui(self):
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout_principal = QHBoxLayout(widget_central)
        layout_principal.setContentsMargins(30, 30, 30, 30)
        layout_principal.setSpacing(30)

        # --- LADO ESQUERDO ---
        layout_esquerda = QVBoxLayout()
        layout_esquerda.setSpacing(20)
        
        caminho_logo_painel = self._obter_caminho_asset("logo_ave.png")
        if os.path.exists(caminho_logo_painel):
            lbl_logo = QLabel()
            pixmap_logo = QPixmap(caminho_logo_painel)
            lbl_logo.setPixmap(pixmap_logo.scaled(170, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            layout_esquerda.addWidget(lbl_logo, alignment=Qt.AlignLeft)
        else:
            lbl_logo = QLabel("iBirder")
            lbl_logo.setFont(QFont("Segoe UI Light", 32))
            layout_esquerda.addWidget(lbl_logo)

        caminho_icone_janela = self._obter_caminho_asset(self.nome_icone_janela)
        if os.path.exists(caminho_icone_janela):
            self.setWindowIcon(QIcon(caminho_icone_janela))

        # Layout de Comparação Lado a Lado (v0.8.0)
        layout_imagens = QHBoxLayout()
        layout_imagens.setSpacing(15)

        self.area_drop = AreaDrop(self._carregar_imagem)
        layout_imagens.addWidget(self.area_drop, stretch=1)
        
        self.area_referencia = AreaReferencia()
        layout_imagens.addWidget(self.area_referencia, stretch=1)
        
        layout_esquerda.addLayout(layout_imagens)
        
        self.btn_nova = QPushButton("Nova Identificação")
        self.btn_nova.setCursor(Qt.PointingHandCursor)
        self.btn_nova.clicked.connect(self._resetar_interface)
        layout_esquerda.addWidget(self.btn_nova)
        
        layout_principal.addLayout(layout_esquerda, stretch=3)

        # --- LADO DIREITO ---
        self.painel_direito = QFrame()
        self.painel_direito.setProperty("class", "painel")
        
        sombra = QGraphicsDropShadowEffect()
        sombra.setBlurRadius(20)
        sombra.setColor(QColor(0, 0, 0, 20))
        sombra.setOffset(0, 5)
        self.painel_direito.setGraphicsEffect(sombra)

        layout_direito = QVBoxLayout(self.painel_direito)
        layout_direito.setSpacing(30)
        layout_direito.setContentsMargins(25, 35, 25, 25)
        
        # Cabeçalho
        layout_cabecalho = QHBoxLayout()
        lbl_controle = QLabel("Identificação")
        lbl_controle.setFont(QFont("Segoe UI Semibold", 20))
        layout_cabecalho.addWidget(lbl_controle)
        
        layout_cabecalho.addStretch()
        
        # Botão Configuração
        self.btn_config = QPushButton()
        self.btn_config.setFixedSize(40, 40)
        self.btn_config.setProperty("class", "icon-btn")
        self.btn_config.setCursor(Qt.PointingHandCursor)
        caminho_gear = self._obter_caminho_asset("icon_config.svg")
        if os.path.exists(caminho_gear):
            self.btn_config.setIcon(QIcon(caminho_gear))
            self.btn_config.setIconSize(QSize(24, 24))
        else:
            self.btn_config.setText("⚙️")
        self.btn_config.clicked.connect(self._abrir_configuracoes)
        layout_cabecalho.addWidget(self.btn_config)

        # Botão Ajuda (Direita)
        self.btn_ajuda = QPushButton()
        self.btn_ajuda.setFixedSize(40, 40)
        self.btn_ajuda.setProperty("class", "icon-btn")
        self.btn_ajuda.setCursor(Qt.PointingHandCursor)
        caminho_help = self._obter_caminho_asset("icon_help.svg")
        if os.path.exists(caminho_help):
            self.btn_ajuda.setIcon(QIcon(caminho_help))
            self.btn_ajuda.setIconSize(QSize(24, 24))
        else:
             self.btn_ajuda.setText("?")
             self.btn_ajuda.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.btn_ajuda.clicked.connect(self._abrir_manual)
        layout_cabecalho.addWidget(self.btn_ajuda)
        
        layout_direito.addLayout(layout_cabecalho)
        
        # Grupo Resultados
        grupo_resultados = QGroupBox("RESULTADOS (IA)")
        layout_res = QVBoxLayout()
        layout_res.setSpacing(15)
        
        # Busca Manual
        layout_busca = QHBoxLayout()
        self.input_nome_cientifico = QLineEdit()
        self.input_nome_cientifico.setPlaceholderText("Insira o nome da espécie para busca manual")
        self.input_nome_cientifico.setFont(QFont("Segoe UI", 12))
        
        self.btn_buscar = QPushButton()
        self.btn_buscar.setFixedSize(36, 36)
        self.btn_buscar.setProperty("class", "icon-btn")
        self.btn_buscar.setCursor(Qt.PointingHandCursor)
        caminho_lupa = self._obter_caminho_asset("search_loupe.png")
        if os.path.exists(caminho_lupa):
            self.btn_buscar.setIcon(QIcon(caminho_lupa))
        else:
            self.btn_buscar.setText("🔍")
        self.btn_buscar.clicked.connect(self._buscar_especie_manual)
        
        layout_busca.addWidget(self.input_nome_cientifico)
        layout_busca.addWidget(self.btn_buscar)

        layout_res.addLayout(layout_busca)
        
        self.lbl_nome_comum = QLabel("-")
        self.lbl_nome_comum.setObjectName("lbl_nome_comum")
        self.lbl_nome_comum.setFont(QFont("Segoe UI", 13))
        self.lbl_nome_comum.setWordWrap(True)
        
        self.lbl_confianca = QLabel("-")
        self.lbl_confianca.setObjectName("lbl_confianca")
        self.lbl_confianca.setStyleSheet("color: #4B5563; font-size: 11px; font-weight: bold;")
        
        self.lbl_descricao = QLabel("-") 
        self.lbl_descricao.setObjectName("lbl_descricao")
        self.lbl_descricao.setWordWrap(True)

        layout_res.addWidget(QLabel("Nome Comum:"))
        layout_res.addWidget(self.lbl_nome_comum)
        layout_res.addWidget(QLabel("Descrição:"))
        layout_res.addWidget(self.lbl_descricao)
        layout_res.addWidget(self.lbl_confianca)
        
        grupo_resultados.setLayout(layout_res)
        layout_direito.addWidget(grupo_resultados)
        layout_direito.addStretch()
        layout_principal.addWidget(self.painel_direito, stretch=2)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Pronto (Online)")

    def _aplicar_estilo(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #F0F2F5; }
            QFrame.painel { background-color: #FFFFFF; border-radius: 12px; border: 1px solid #D1D5DB; }
            
            /* Textos Gerais */
            QLabel { color: #1F2937; font-family: "Segoe UI"; }
            
            /* Dropzone */
            QLabel.dropzone { 
                border: 2px dashed #9CA3AF; 
                border-radius: 12px; 
                background-color: #F3F4F6; 
                color: #4B5563; 
                font-size: 14px; 
                font-weight: bold; 
            }
            QLabel.dropzone:hover { background-color: #E5E7EB; border-color: #374151; }
            
            /* Area Referencia (v0.8.0) */
            QLabel.referencia {
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                background-color: #F9FAFB;
                color: #9CA3AF;
                font-size: 14px;
            }
            
            /* Botões */
            QPushButton { 
                background-color: #374151; 
                color: white; 
                border-radius: 8px; 
                padding: 12px; 
                font-weight: bold; 
                font-family: "Segoe UI";
            }
            QPushButton:hover { background-color: #1F2937; }
            
            /* Botões Icone */
            QPushButton[class="icon-btn"] { background-color: transparent; color: #374151; padding: 4px; border: none; }
            QPushButton[class="icon-btn"]:hover { background-color: #E5E7EB; border-radius: 4px; }
            
            /* Inputs (Resultados) */
            QLineEdit { 
                border: 1px solid #D1D5DB; 
                border-radius: 6px; 
                padding: 8px; 
                background-color: #FFFFFF; 
                color: #111827; 
                font-weight: bold;
                font-style: italic;
                font-size: 14px;
            }
            QLineEdit:focus { border: 1px solid #374151; }
            
            /* GroupBox */
            QGroupBox { 
                border: 1px solid #E5E7EB; 
                border-radius: 8px; 
                margin-top: 24px; 
                padding-top: 24px; 
                font-weight: bold; 
                font-size: 12px; 
                background-color: #FFFFFF; 
                color: #6B7280; 
                letter-spacing: 1px; 
                text-transform: uppercase; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                subcontrol-position: top left;
                left: 16px; 
                padding: 0 4px; 
                background-color: #FFFFFF; 
                color: #374151;
            }
        """)

    def _abrir_manual(self):
        janela_manual = JanelaManual(self)
        janela_manual.exec()

    def _abrir_configuracoes(self):
        janela_cfg = JanelaConfig(self)
        janela_cfg.exec()

    def _carregar_imagem(self, caminho: str):
        self.caminho_imagem_atual = caminho
        pixmap = QPixmap(caminho)
        if not pixmap.isNull():
            self.area_drop.setPixmap(pixmap.scaled(self.area_drop.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.status_bar.showMessage(f"Imagem: {Path(caminho).name}")
        self._identificar_ave()

    def _identificar_ave(self):
        if not self.caminho_imagem_atual:
            return

        # v0.7.9: Evita chamadas redundantes para preservar cota
        if getattr(self, "ultimo_caminho_processado", None) == self.caminho_imagem_atual:
            return

        self.ultimo_caminho_processado = self.caminho_imagem_atual
            
        self.lbl_nome_comum.setText("...")
        self.lbl_descricao.setText("-")
        self.status_bar.showMessage("Analisando com Google Gemini (Online)...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        try:
            # Fluxo Único: Nuvem
            resultado = self.servico.identificar(self.caminho_imagem_atual)
            
            if "erro" in resultado:
                DialogoAviso(resultado.get("titulo", "Erro"), resultado["erro"], self).exec()
                self.status_bar.showMessage("Falha.")
            else:
                self.input_nome_cientifico.setText(resultado.get("nome_cientifico", "?"))
                self.lbl_nome_comum.setText(resultado.get("nome_comum", "-"))
                self.lbl_descricao.setText(resultado.get("descricao", "-"))
                conf = resultado.get("confianca", 0.0)
                self.lbl_confianca.setText(f"Confiança IA: {conf:.1%}" if isinstance(conf, float) else str(conf))
                self.status_bar.showMessage("Identificado.")
                
        except ChaveApiFaltandoErro:
             DialogoAviso("Falta Chave", "Configure a chave de API no menu.", self).exec()
        except Exception as e:
             DialogoAviso("Erro", f"Erro fatal: {e}", self).exec()
        finally:
            QApplication.restoreOverrideCursor()

    def _resetar_interface(self):
        self.caminho_imagem_atual = None
        self.ultimo_caminho_processado = None
        self.area_drop.setPixmap(QPixmap())
        self.area_drop.setText("Arraste e solte uma foto aqui\n\nou clique para selecionar")
        self.input_nome_cientifico.clear()
        self.lbl_nome_comum.setText("-")
        self.lbl_descricao.setText("-")
        self.lbl_confianca.setText("-")
        self.status_bar.showMessage("Pronto (Online)")

    def _buscar_especie_manual(self):
        nome = self.input_nome_cientifico.text().strip()
        if len(nome) < 3:
            DialogoAviso("Busca", "Digite pelo menos 3 letras.", self).exec()
            return
            
        self.status_bar.showMessage(f"Pesquisando {nome}...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        try:
            resultado = self.id_nuvem.consultar_especie(nome)
            if "erro" in resultado:
                DialogoAviso("Não Encontrado", resultado["erro"], self).exec()
            else:
                self.input_nome_cientifico.setText(resultado.get("nome_cientifico", ""))
                self.lbl_nome_comum.setText(resultado.get("nome_comum", "-"))
                self.lbl_descricao.setText(resultado.get("descricao", "-"))
                self.lbl_confianca.setText("Busca Manual (Nuvem)")
        except Exception as e:
            DialogoAviso("Erro", str(e), self).exec()
        finally:
            QApplication.restoreOverrideCursor()
