import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QFileDialog, QLineEdit, QTextEdit,
    QFrame, QStatusBar, QApplication, QSizePolicy, QGraphicsDropShadowEffect,
    QMessageBox, QCheckBox, QGridLayout
)
from PySide6.QtCore import Qt, QSize, QThread, Signal, QSettings, QMimeData, QUrl, QTimer
from PySide6.QtGui import (
    QPixmap, QFont, QDragEnterEvent, QDropEvent, QIcon, QColor, 
    QPainter, QAction, QDesktopServices, QDrag, QResizeEvent, QPalette
)
from PySide6.QtWebEngineWidgets import QWebEngineView

# Importações do Core
from core.geo_utils import extract_lat_lon
from core.local_worker import LocalIdentificationWorker
from ui.janela_manual import JanelaManual
from ui.dialogo_aviso import DialogoAviso
from ui.worker_referencia import ReferenceImageWorker
from core.buscador_worker import BuscadorWorker
from core.logger import save_crash_log
from ui.widgets.map_widget import MapWidget
from ui.custom_widgets import ImageCardWidget

class JanelaPrincipal(QMainWindow):
    def __init__(self, nome_icone_janela="logo_ave.svg", modo_inicial="online", ai_status="READY"):
        super().__init__()
        self.nome_icone_janela = nome_icone_janela
        self.ai_status = ai_status
        
        self.setWindowTitle("iBirder")
        self.resize(1100, 700)
        
        self.caminho_imagem_atual = None
        self.dados_identificacao_atual = {}

        self._configurar_ui()
        self._configurar_ui()
        self._aplicar_estilo()
        
        # Ajuste inicial de alturas
        # QTimer.singleShot(100, lambda: self._ajustar_altura_etimologia())
        # QTimer.singleShot(100, lambda: self._ajustar_altura_descricao())

    def _obter_caminho_asset(self, nome_arquivo):
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent / 'assets'
        return str(base_path / nome_arquivo)

    def _iniciar_busca_imagem(self, nome_cientifico):
        # Reset visual
        self.card_ref.set_placeholder("Aguardando a identificação da ave.")
        self.card_ref.set_pixmap(None)
        self.card_ref.set_overlay_text(None)
        self.btn_fonte.setEnabled(False) 
        
        self.txt_descricao.clear() # Reset descrição anterior
        
        # Reset para estado "Aguardando"
        self.txt_etimologia.clear()
        self.txt_etimologia.setPlaceholderText("Aguardando identificação...")
        self.lbl_titulo_etimologia.setVisible(True)
        self.txt_etimologia.setVisible(True)

        # Para worker anterior se existir
        if getattr(self, "worker_referencia", None) is not None:
            try:
                if self.worker_referencia.isRunning():
                    self.worker_referencia.quit()
                    self.worker_referencia.wait()
                self.worker_referencia.deleteLater()
            except RuntimeError:
                pass 
            
        self.worker_referencia = ReferenceImageWorker(nome_cientifico)
        self.worker_referencia.image_found.connect(self._ao_encontrar_imagem_referencia)
        self.worker_referencia.search_failed.connect(lambda: self.card_ref.set_placeholder("Sem referência"))
        self.worker_referencia.start()
        
        # Iniciar worker de informações da espécie (iNaturalist)
        self._iniciar_busca_info_especie(nome_cientifico)

    def _iniciar_busca_info_especie(self, nome_cientifico):
        if getattr(self, "worker_species", None) is not None:
             try:
                 if self.worker_species.isRunning():
                     self.worker_species.quit()
                     self.worker_species.wait()
                 self.worker_species.deleteLater()
             except: pass

        self.worker_species = BuscadorWorker(nome_cientifico)
        self.worker_species.info_found.connect(self._ao_receber_info_especie)
        self.worker_species.error_occurred.connect(self._ao_erro_api)
        self.worker_species.start()

    def _ao_encontrar_imagem_referencia(self, path, creditos, url_fonte=""):
        # set_image_path carrega o pixmap e prepara para drag
        self.card_ref.set_image_path(path) 
        
        if creditos:
             self.card_ref.set_overlay_text(f"Foto: {creditos}")
        else:
             self.card_ref.set_overlay_text(None)
        
        if url_fonte:
            self.btn_fonte.setProperty("url_alvo", url_fonte)
            self.btn_fonte.setEnabled(True)
            self.btn_fonte.setText("Abrir Fonte")
        else:
            self.btn_fonte.setEnabled(False)

    def _ao_receber_info_especie(self, dados):
        # Mapeamento do BuscadorBlindado
        # dados['nome_cientifico'] -> Etimologia
        # dados['caracteristicas'] -> Descrição
        
        etimologia_texto = dados.get("nome_cientifico", "")
        caracteristicas = dados.get("caracteristicas", "")

        # Atualiza Campo Etimologia
        # Atualiza Campo Etimologia
        if etimologia_texto and etimologia_texto != "Não encontrado":
            self.txt_etimologia.setPlainText(etimologia_texto)
        elif etimologia_texto == "Não encontrado":
            self.txt_etimologia.setPlaceholderText("Etimologia não disponível.")
            self.txt_etimologia.clear()

        # Atualiza Campo Descrição (Rodapé)
        if caracteristicas and caracteristicas != "Não encontrado":
            self.txt_descricao.setPlainText(caracteristicas)
            self.btn_fonte.setText("Abrir no WikiAves")
            self.btn_fonte.setEnabled(True)
            
            # Se quiser linkar direto, precisaríamos que o bot retornasse o link.
            # O BuscadorBlindado retorna dados, mas o Worker atual só passa 'dados'.
            # Vamos ajustar se necessário, mas por enquanto, assume-se que o usuário pode clicar no "WikiAves" botão existente.
            
        self.frame_etimologia.setVisible(False) # Esconde o antigo frame do iNaturalist se ainda visível

    def _ao_erro_api(self, erro_msg):
        self.lbl_etimologia_texto.setText(f"Erro: {erro_msg}")
        self.frame_etimologia.setVisible(True)

    def _ajustar_altura_descricao(self):
        """Ajusta a altura do campo de descrição conforme o conteúdo."""
        doc_height = self.txt_descricao.document().size().height()
        margins = self.txt_descricao.contentsMargins().top() + self.txt_descricao.contentsMargins().bottom() + 15
        self.txt_descricao.setFixedHeight(max(int(doc_height + 10), 45))

    def _ajustar_altura_etimologia(self):
        """Ajusta a altura do campo de etimologia conforme o conteúdo."""
        doc_height = self.txt_etimologia.document().size().height()
        # Ajuste fino para evitar scrollbar e espaço extra (padding css + margem segurança)
        self.txt_etimologia.setFixedHeight(max(int(doc_height + 10), 45))

    def resizeEvent(self, event):
        """Recalcula altura dos campos de texto ao redimensionar a janela."""
        # Usa timer para garantir que o layout já foi atualizado e a largura dos campos está correta
        QTimer.singleShot(0, self._ajustar_altura_etimologia)
        QTimer.singleShot(0, self._ajustar_altura_descricao)
        super().resizeEvent(event)

    def _configurar_ui(self):
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout_principal = QHBoxLayout(widget_central)
        layout_principal.setContentsMargins(30, 30, 30, 30)
        layout_principal.setSpacing(30)

        # --- LADO ESQUERDO ---
        layout_esquerda = QVBoxLayout()
        layout_esquerda.setSpacing(20)
        
        # Branding Header
        layout_branding = QHBoxLayout()
        layout_branding.setSpacing(12)
        layout_branding.setAlignment(Qt.AlignLeft)
        
        caminho_logo_painel = self._obter_caminho_asset("logo_ave.svg")
        lbl_logo = QLabel()
        if os.path.exists(caminho_logo_painel):
            pixmap_logo = QIcon(caminho_logo_painel).pixmap(QSize(48, 48))
            lbl_logo.setPixmap(pixmap_logo)
        else:
            lbl_logo.setText("🐦")
            lbl_logo.setFont(QFont("Segoe UI Emoji", 32))
        
        layout_branding.addWidget(lbl_logo)
        
        layout_textos_header = QVBoxLayout()
        layout_textos_header.setSpacing(0)
        
        lbl_titulo_app = QLabel("iBirder")
        lbl_titulo_app.setStyleSheet("color: #1F2937; font-size: 24px; font-weight: bold; font-family: 'Segoe UI';")
        lbl_subtitulo = QLabel("IA para BirdWatching")
        lbl_subtitulo.setStyleSheet("color: #6B7280; font-size: 14px; font-weight: normal; font-family: 'Segoe UI';")
        
        layout_textos_header.addWidget(lbl_titulo_app)
        layout_textos_header.addWidget(lbl_subtitulo)
        
        layout_branding.addLayout(layout_textos_header)
        layout_branding.addStretch()
        
        layout_esquerda.addLayout(layout_branding)

        caminho_icone_janela = self._obter_caminho_asset(self.nome_icone_janela)
        if os.path.exists(caminho_icone_janela):
            self.setWindowIcon(QIcon(caminho_icone_janela))

        # Layout de Imagens (Horizontal 50/50 com Stretch)
        layout_imagens = QHBoxLayout()
        layout_imagens.setSpacing(15) 
        # Não usamos QGridLayout pois QHBoxLayout lida melhor com stretch igual

        # --- Coluna Esquerda (User) ---
        layout_col_user = QVBoxLayout()
        
        lbl_titulo_user = QLabel("Imagem Pesquisada")
        lbl_titulo_user.setStyleSheet("font-weight: bold; color: #374151; font-size: 11px; margin-bottom: 4px;")
        layout_col_user.addWidget(lbl_titulo_user)

        self.card_user = ImageCardWidget()
        self.card_user.set_placeholder("Arraste e solte uma foto aqui\n\nou clique para selecionar")
        self.card_user.set_on_drop(self._carregar_imagem)
        self.card_user.set_on_click(self._abrir_seletor_arquivo)
        
        layout_col_user.addWidget(self.card_user, stretch=1) # Stretch vertical para o card

        self.btn_google_lens = QPushButton("Pesquisar com Google Lens")
        self.btn_google_lens.setCursor(Qt.PointingHandCursor)
        self.btn_google_lens.setEnabled(False)
        self.btn_google_lens.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #374151;
                border: 1px solid #d1d5db;
                padding: 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #f3f4f6;
            }
        """)
        self.btn_google_lens.clicked.connect(self._abrir_google_lens)
        layout_col_user.addWidget(self.btn_google_lens)
        
        layout_imagens.addLayout(layout_col_user, stretch=1) # 50% largura

        # --- Coluna Direita (Referência) ---
        layout_col_ref = QVBoxLayout()
        
        lbl_titulo_ref = QLabel("Imagem Referência")
        lbl_titulo_ref.setStyleSheet("font-weight: bold; color: #374151; font-size: 11px; margin-bottom: 4px;")
        layout_col_ref.addWidget(lbl_titulo_ref)

        self.card_ref = ImageCardWidget()
        self.card_ref.set_placeholder("Aguardando a identificação da ave.")
        # Reference card doesn't need click/drop actions usually
        
        layout_col_ref.addWidget(self.card_ref, stretch=1) # Stretch vertical

        self.btn_fonte = QPushButton("Abrir Fonte")
        self.btn_fonte.setCursor(Qt.PointingHandCursor)
        self.btn_fonte.setVisible(True)
        self.btn_fonte.setEnabled(False)
        self.btn_fonte.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #374151;
                border: 1px solid #d1d5db;
                padding: 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #f3f4f6;
            }
        """)
        self.btn_fonte.clicked.connect(lambda: QDesktopServices.openUrl(self.btn_fonte.property("url_alvo")))
        layout_col_ref.addWidget(self.btn_fonte)
        
        layout_imagens.addLayout(layout_col_ref, stretch=1) # 50% largura
        
        layout_esquerda.addLayout(layout_imagens)
        
        # --- Campo de Descrição Rica (v0.2.1) ---
        lbl_titulo_desc = QLabel('Descrição da Espécie <i>(WikiAves)</i>')
        lbl_titulo_desc.setStyleSheet("font-weight: bold; color: #374151; font-size: 11px; margin-top: 8px;")
        layout_esquerda.addWidget(lbl_titulo_desc)

        self.txt_descricao = QTextEdit()
        self.txt_descricao.setReadOnly(True)
        self.txt_descricao.setPlaceholderText("Descrição da espécie...")
        self.txt_descricao.setMinimumHeight(45) 
        self.txt_descricao.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.txt_descricao.textChanged.connect(self._ajustar_altura_descricao)
        
        self.txt_descricao.setStyleSheet("""
            QTextEdit {
                background-color: #F8F9FA;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                padding: 6px;
                color: #4B5563;
                font-size: 12px;
                font-family: "Segoe UI";
                font-style: italic;
            }
        """)
        
        layout_esquerda.addWidget(self.txt_descricao)
        
        self.btn_nova = QPushButton("Nova Identificação")
        self.btn_nova.setCursor(Qt.PointingHandCursor)
        self.btn_nova.clicked.connect(self._abrir_seletor_arquivo)
        layout_esquerda.addWidget(self.btn_nova)
        
        # --- NOVO: Mapa Único (v0.3.3) ---
        lbl_titulo_geo = QLabel("Localização Geográfica")
        lbl_titulo_geo.setStyleSheet("font-weight: bold; color: #374151; font-size: 11px; margin-bottom: 4px;")
        layout_esquerda.addWidget(lbl_titulo_geo)
        
        self.map_principal = MapWidget()
        self.map_principal.setMinimumHeight(350) 
        self.map_principal.show_placeholder_message("Aguardando dados de Localização")
        layout_esquerda.addWidget(self.map_principal)
        
        layout_principal.addLayout(layout_esquerda, stretch=3)

        # --- LADO DIREITO (Painel Lateral) ---
        layout_coluna_direita = QVBoxLayout()
        layout_coluna_direita.setSpacing(10)
        
        # Botões Header (Reload + Ajuda)
        layout_ajuda = QHBoxLayout()
        layout_ajuda.addStretch()
        
        self.btn_reload = QPushButton()
        self.btn_reload.setFixedSize(40, 40)
        self.btn_reload.setProperty("class", "icon-btn")
        self.btn_reload.setCursor(Qt.PointingHandCursor)
        self.btn_reload.setToolTip("Recarregar / Limpar")
        caminho_reload = self._obter_caminho_asset("icon_reload.svg")
        if os.path.exists(caminho_reload):
            self.btn_reload.setIcon(QIcon(caminho_reload))
            self.btn_reload.setIconSize(QSize(24, 24))
        else:
            self.btn_reload.setText("⟳")
            self.btn_reload.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.btn_reload.clicked.connect(self._resetar_interface)
        
        layout_ajuda.addWidget(self.btn_reload)
        
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
        
        layout_ajuda.addWidget(self.btn_ajuda)
        layout_coluna_direita.addLayout(layout_ajuda)

        # Painel Branco
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
        
        # Grupo Resultados
        grupo_resultados = QGroupBox("") 
        layout_res = QVBoxLayout()
        layout_res.setSpacing(15)
        
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

        self.lbl_descricao.setWordWrap(True)
        
        # Label Nome Científico Padronizado
        lbl_titulo_nc = QLabel("Nome Científico")
        lbl_titulo_nc.setStyleSheet("font-weight: bold; color: #374151; font-size: 11px; margin-top: 8px;")
        layout_res.addWidget(lbl_titulo_nc)

        # Container de Busca Manual
        container_busca = QHBoxLayout()
        container_busca.setContentsMargins(0, 0, 0, 0)
        container_busca.setSpacing(5)
        
        self.input_especie = QLineEdit()
        self.input_especie.setPlaceholderText("pesquise ou digite")
        # Força a cor do placeholder para #4B5563
        palette = self.input_especie.palette()
        palette.setColor(self.input_especie.foregroundRole(), QColor("#4B5563"))
        palette.setColor(QPalette.PlaceholderText, QColor("#4B5563"))
        palette.setColor(QPalette.Text, QColor("#4B5563"))
        self.input_especie.setPalette(palette)
        
        self.input_especie.setStyleSheet("background: transparent; border: 1px solid #D1D5DB; border-radius: 6px; padding: 4px; color: #4B5563; font-style: italic; font-size: 12px; font-family: 'Segoe UI';")
        self.input_especie.returnPressed.connect(self._realizar_busca_manual)
        
        self.btn_search = QPushButton()
        self.btn_search.setCursor(Qt.PointingHandCursor)
        self.btn_search.setFixedSize(32, 32)
        self.btn_search.setStyleSheet("background-color: transparent; border: none;") 
        
        caminho_lupa = self._obter_caminho_asset("search_loupe.svg")
        if os.path.exists(caminho_lupa):
             self.btn_search.setIcon(QIcon(caminho_lupa))
             self.btn_search.setIconSize(QSize(20, 20))
        else:
             self.btn_search.setText("🔍")
             
        self.btn_search.clicked.connect(self._realizar_busca_manual)
        
        container_busca.addWidget(self.input_especie)
        container_busca.addWidget(self.btn_search)
        
        layout_res.addLayout(container_busca)

        # --- NOVOS CAMPOS: ETIMOLOGIA (Abaixo do Nome Científico) ---
        self.lbl_titulo_etimologia = QLabel('Etimologia <i>(WikiAves)</i>')
        self.lbl_titulo_etimologia.setStyleSheet("font-weight: bold; color: #374151; font-size: 11px; margin-top: 8px;")
        self.lbl_titulo_etimologia.setVisible(True)
        layout_res.addWidget(self.lbl_titulo_etimologia)

        self.txt_etimologia = QTextEdit()
        self.txt_etimologia.setReadOnly(True)
        self.txt_etimologia.setPlaceholderText("Aguardando identificação...")
        self.txt_etimologia.setMinimumHeight(30) 
        self.txt_etimologia.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.txt_etimologia.textChanged.connect(self._ajustar_altura_etimologia)
        self.txt_etimologia.setStyleSheet("""
            QTextEdit {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 6px;
                color: #4B5563;
                font-size: 12px;
                font-style: italic;
            }
        """)
        self.txt_etimologia.setVisible(True)
        layout_res.addWidget(self.txt_etimologia)
        # -------------------------------------------------------------

        layout_res.addWidget(QLabel("Info:"))
        layout_res.addWidget(self.lbl_descricao)
        layout_res.addWidget(self.lbl_confianca)
        
        # Botões de Busca Externa
        layout_botoes = QHBoxLayout()
        layout_botoes.setSpacing(10)
        
        self.btn_wiki = QPushButton("WikiAves")
        self.btn_wiki.setCursor(Qt.PointingHandCursor)
        self.btn_wiki.setStyleSheet("background-color: #F97316; border: none;") 
        self.btn_wiki.clicked.connect(self._buscar_wikiaves)
        layout_botoes.addWidget(self.btn_wiki)
        
        self.btn_ebird = QPushButton("eBird")
        self.btn_ebird.setCursor(Qt.PointingHandCursor)
        self.btn_ebird.setStyleSheet("background-color: #65A30D; border: none;")
        self.btn_ebird.clicked.connect(self._buscar_ebird)
        layout_botoes.addWidget(self.btn_ebird)

        self.btn_google = QPushButton("Google")
        self.btn_google.setCursor(Qt.PointingHandCursor)
        self.btn_google.setStyleSheet("background-color: #3B82F6; border: none;")
        self.btn_google.clicked.connect(self._buscar_google)
        layout_botoes.addWidget(self.btn_google)
        
        layout_res.addLayout(layout_botoes)
        
        # --- Card Etimologia ---
        self.frame_etimologia = QFrame()
        self.frame_etimologia.setObjectName("frame_etimologia")
        self.frame_etimologia.setStyleSheet("""
            QFrame#frame_etimologia {
                background-color: #F8F9FA;
                border-left: 4px solid #10B981;
                border-radius: 4px;
                padding: 10px;
                margin-top: 10px;
            }
        """)
        
        layout_etimologia = QVBoxLayout(self.frame_etimologia)
        layout_etimologia.setContentsMargins(0, 0, 0, 0)
        
        lbl_titulo = QLabel("Detalhes (WikiAves)")
        lbl_titulo.setStyleSheet("font-weight: bold; color: #059669; font-size: 11px; text-transform: uppercase;")
        layout_etimologia.addWidget(lbl_titulo)
        
        self.lbl_etimologia_texto = QLabel("Carregando...")
        self.lbl_etimologia_texto.setWordWrap(True)
        self.lbl_etimologia_texto.setStyleSheet("color: #374151; font-size: 12px; margin-top: 4px;")
        layout_etimologia.addWidget(self.lbl_etimologia_texto)
        
        self.frame_etimologia.setVisible(False)
        layout_res.addWidget(self.frame_etimologia)
        
        # --- NOVO: Card Vocalizações (v0.3.3) ---
        grupo_audio = QGroupBox("")
        grupo_audio.setStyleSheet("margin-top: 10px; padding-top: 10px;")
        layout_audio = QVBoxLayout()
        
        lbl_titulo_audio = QLabel("Vocalizações")
        lbl_titulo_audio.setStyleSheet("font-weight: bold; color: #374151; font-size: 11px; margin-bottom: 4px;")
        layout_audio.addWidget(lbl_titulo_audio)
        
        self.lbl_audio_placeholder = QLabel("Áudio não carregado")
        self.lbl_audio_placeholder.setAlignment(Qt.AlignCenter)
        self.lbl_audio_placeholder.setStyleSheet("color: #9CA3AF; font-style: italic; border: 1px dashed #D1D5DB; border-radius: 4px; padding: 20px;")
        layout_audio.addWidget(self.lbl_audio_placeholder)
        
        grupo_audio.setLayout(layout_audio)
        layout_res.addWidget(grupo_audio)
        
        grupo_resultados.setLayout(layout_res)
        layout_direito.addWidget(grupo_resultados)
        layout_direito.addStretch()
        
        layout_coluna_direita.addWidget(self.painel_direito)
        layout_principal.addLayout(layout_coluna_direita, stretch=2)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Pronto para uso (Local)")

    def _aplicar_estilo(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #F0F2F5; }
            QFrame.painel { background-color: #FFFFFF; border-radius: 12px; border: 1px solid #D1D5DB; }
            
            QLabel { color: #1F2937; font-family: "Segoe UI"; }
            
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

    def _obter_sciname_atual(self):
        return self.dados_identificacao_atual.get("nome_cientifico", "")

    def _buscar_wikiaves(self):
        sciname = self._obter_sciname_atual()
        if sciname and "Inconclusiva" not in sciname:
            url = f"https://www.wikiaves.com.br/index.php?t=s&s={sciname}"
            QDesktopServices.openUrl(url)

    def _buscar_ebird(self):
        sciname = self._obter_sciname_atual()
        if sciname and "Inconclusiva" not in sciname:
            url = f"https://www.google.com/search?q={sciname}+site:ebird.org"
            QDesktopServices.openUrl(url)

    def _buscar_google(self):
        sciname = self._obter_sciname_atual()
        if sciname and "Inconclusiva" not in sciname:
            url = f"https://www.google.com/search?q={sciname}"
            QDesktopServices.openUrl(url)

    def _realizar_busca_manual(self):
        texto = self.input_especie.text().strip()
        if not texto:
             return
        
        self.status_bar.showMessage(f"Busca manual: {texto}")
        if self.dados_identificacao_atual is None:
             self.dados_identificacao_atual = {}
             
        # Formatação Taxonômica Rigorosa
        import re
        sci_clean = re.sub(r'[\(\[].*?[\)\]]', '', texto).strip()
        parts = sci_clean.split()
        if len(parts) >= 2:
            sci_formatted = f"{parts[0].capitalize()} {parts[1].lower()}"
        else:
            sci_formatted = sci_clean.capitalize()
            
        # Atualiza Campo e Estilo
        self.input_especie.setText(sci_formatted)
        self.input_especie.setStyleSheet("background: transparent; border: 1px solid #D1D5DB; border-radius: 6px; padding: 4px; color: #374151; font-style: italic;")

        self.dados_identificacao_atual["nome_cientifico"] = sci_formatted
        self.lbl_nome_comum.setText("...")
        
        self._iniciar_busca_imagem(sci_formatted)
        self._iniciar_busca_info_especie(sci_formatted)
        
        self.btn_wiki.setVisible(True)
        self.btn_google.setVisible(True)
        self.btn_ebird.setVisible(True)

    def _abrir_google_lens(self):
        if not self.caminho_imagem_atual:
             return
        
        clipboard = QApplication.clipboard()
        clipboard.setText(self.caminho_imagem_atual)
        QDesktopServices.openUrl("https://lens.google.com/upload")
        
        settings = QSettings("iBirder", "App")
        dont_show = settings.value("lens_dont_show_again", False, type=bool)
        
        if dont_show:
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("iBirder - Pesquisa Visual")
        
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #F9FAFB;
            }
            QLabel {
                color: #1F2937;
                font-size: 13px;
            }
            QPushButton {
                background-color: #374151;
                color: white;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
                border: 1px solid #1F2937;
            }
            QPushButton:hover {
                background-color: #111827;
            }
            QCheckBox {
                background-color: transparent;
                color: #4B5563;
                font-size: 11px;
                margin-top: 10px;
            }
            QCheckBox::indicator {
                border: 1px solid #9CA3AF;
                background: white;
                width: 14px;
                height: 14px;
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                background-color: #374151;
                border-color: #374151;
            }
        """)
        
        msg.setText("O Google Lens foi aberto no seu navegador.")
        msg.setInformativeText(
            "Agora, <b>arraste a foto do iBirder</b> ou copie e cole (Ctrl+V) a imagem na página para identificar.<br><br>"
            "<i>(O caminho da imagem foi copiado para sua área de transferência)</i>"
            "<br><br><span style='font-size: 10px; color: #6B7280;'>Nota: A imagem foi otimizada para garantir a compatibilidade com o Google.</span>"
        )
        msg.setIcon(QMessageBox.Information)
        msg.addButton("Entendi", QMessageBox.AcceptRole)
        
        chk_dont_show = QCheckBox("Não exibir esta mensagem novamente", msg)
        msg.setCheckBox(chk_dont_show)
        msg.exec()
        
        if chk_dont_show.isChecked():
            settings.setValue("lens_dont_show_again", True)

    def _carregar_imagem(self, caminho: str):
        self._resetar_interface() # Limpa tudo primeiro

        self.caminho_imagem_atual = caminho
        # Carrega no card (e configura drag)
        self.card_user.set_image_path(caminho) 
        
        # Persistência
        folder = str(Path(caminho).parent)
        settings = QSettings("iBirder", "App")
        settings.setValue("last_folder", folder)
        
        self.status_bar.showMessage(f"Imagem: {Path(caminho).name}")
        self.btn_google_lens.setEnabled(True)
        
        # --- Geo (v0.3.1) ---
        # --- Geo (v0.3.3) ---
        coords = extract_lat_lon(caminho)
        if coords:
            lat, lon = coords
            print(f"[MAPA] Coordenadas encontradas: {lat}, {lon}")
            
            if self.map_principal:
                self.map_principal.update_map(lat, lon, zoom=13, add_marker=True)
                
        else:
            print("[MAPA] Sem dados GPS. Exibindo mensagem de aviso.")
            msg_erro = "Dados de localização não disponíveis na imagem"
            
            if self.map_principal:
                self.map_principal.show_placeholder_message(msg_erro)
             
        self._identificar_ave()

    def _identificar_ave(self):
        if not self.caminho_imagem_atual:
            return

        if self.ai_status == 'RESTART_REQUIRED':
             msg = QMessageBox()
             msg.setIcon(QMessageBox.Information)
             msg.setWindowTitle("Reinicialização Necessária")
             msg.setText("Os componentes de Inteligência Artificial foram instalados com sucesso!\n\nPor favor, feche e abra o iBirder novamente para ativar o novo sistema.")
             msg.addButton("Entendi, vou reiniciar", QMessageBox.AcceptRole)
             msg.exec()
             return

        self.lbl_nome_comum.setText("...")
        self.lbl_descricao.setText("-")
        self.txt_descricao.clear() # Limpa descrição rica
        
        self.txt_etimologia.clear()
        self.txt_etimologia.setPlaceholderText("Aguardando identificação...")
        self.lbl_titulo_etimologia.setVisible(True)
        self.txt_etimologia.setVisible(True)
        
        self.input_especie.clear() 
        self.input_especie.clear() 
        self.input_especie.setStyleSheet("background: transparent; border: 1px solid #D1D5DB; border-radius: 6px; padding: 4px; color: #4B5563; font-style: italic; font-size: 12px; font-family: 'Segoe UI';")  
        
        self.card_ref.set_placeholder("aguardando identificação da espécie...")
        self.status_bar.showMessage("Iniciando IA Local...")
        
        self.card_user.setAcceptDrops(False) # Bloqueia novos drops durante processamento
        
        self.worker_local = LocalIdentificationWorker(self.caminho_imagem_atual)
        self.worker_local.progress_updated.connect(self._ao_progresso_identificacao)
        self.worker_local.identification_complete.connect(self._ao_concluir_identificacao)
        self.worker_local.error_occurred.connect(self._ao_erro_identificacao)
        self.worker_local.start()
        
    def _ao_progresso_identificacao(self, mensagem):
        self.status_bar.showMessage(mensagem)

    def _ao_concluir_identificacao(self, resultado):
        self.card_user.setAcceptDrops(True)
        self._atualizar_info_ave(resultado)

    def _atualizar_info_ave(self, dados: dict):
        self.dados_identificacao_atual = dados
        
        nc = dados.get("nome_comum", "-")
        raw_sci = dados.get("nome_cientifico", "")
        
        import re
        sci_clean = re.sub(r'[\(\[].*?[\)\]]', '', raw_sci)
        parts = sci_clean.strip().split()
        if len(parts) >= 2:
            sci = f"{parts[0]} {parts[1]}"
        else:
            sci = sci_clean.strip()
            
        desc = dados.get("descricao", "")
        conf = dados.get("confianca", 0.0)
        status_msg = dados.get("status_msg", "")
        
        self.lbl_nome_comum.setText(nc)
        
        if "Inconclusiva" not in status_msg and "Baixa" not in status_msg and sci:
            sci_clean = re.sub(r'[\(\[].*?[\)\]]', '', sci).strip()
            parts = sci_clean.split()
            if len(parts) >= 2:
                sci_formatted = f"{parts[0].capitalize()} {parts[1].lower()}"
            else:
                sci_formatted = sci_clean.capitalize()

            self.input_especie.setText(sci_formatted)
            self.input_especie.setStyleSheet("background: transparent; border: 1px solid #D1D5DB; border-radius: 6px; padding: 4px; color: #374151; font-style: italic;")
            
            if self.dados_identificacao_atual:
                self.dados_identificacao_atual["nome_cientifico"] = sci_formatted
        else:
             self.input_especie.clear()
             self.input_especie.setStyleSheet("background: transparent; border: 1px solid #D1D5DB; border-radius: 6px; padding: 4px; color: #4B5563; font-style: italic; font-size: 12px; font-family: 'Segoe UI';")
        
        self.lbl_descricao.setText(desc)
        
        if status_msg == "Baixa confiança":
            self.lbl_confianca.setText(f"{conf*100:.1f}% (Baixa)")
            self.lbl_confianca.setStyleSheet("color: #EF4444")
            self.status_bar.showMessage("Identificação inconclusiva.")
            
            self.btn_wiki.setVisible(False)
            self.btn_google.setVisible(False)
            self.btn_ebird.setVisible(False)
            
            self.card_ref.set_placeholder("Busca visual suspensa")
            self.card_ref.set_pixmap(None)
            self.card_ref.set_overlay_text(None)
            
            self.lbl_descricao.setText("Não foi possível identificar com segurança.\n\nTente o botão do Google Lens abaixo para uma análise visual.")
            self.btn_google_lens.setEnabled(True)

        else:
            self.lbl_confianca.setText(f"{conf*100:.1f}%")
            self.lbl_confianca.setStyleSheet("color: #059669")
            self.status_bar.showMessage("Identificação concluída.")
            
            self.btn_wiki.setVisible(True)
            self.btn_google.setVisible(True)
            self.btn_ebird.setVisible(True)
            
            if sci:
                self._iniciar_busca_imagem(sci)
        
        if status_msg:
             print(f"[UI] Status de Identificação: {status_msg}")

    def _ao_erro_identificacao(self, erro_msg):
        self.card_user.setAcceptDrops(True)
        self.status_bar.showMessage("Falha na identificação.")
        DialogoAviso("Erro de Identificação", erro_msg, self).exec()

    def _abrir_seletor_arquivo(self):
        self.activateWindow()
        self.raise_()
        
        settings = QSettings("iBirder", "App")
        last_folder = settings.value("last_folder", "")
        
        path, _ = QFileDialog.getOpenFileName(
            self, "Nova Identificação", last_folder, "Imagens (*.png *.jpg *.jpeg)"
        )
        if path:
            self._carregar_imagem(path)

    def _resetar_interface(self):
        self.caminho_imagem_atual = None
        
        # User Card Reset
        self.card_user.set_image_path(None)
        self.card_user.set_placeholder("Arraste e solte uma foto aqui\n\nou clique para selecionar")
        
        # Ref Card Reset
        self.card_ref.set_image_path(None)
        self.card_ref.set_placeholder("Aguardando a identificação da ave.")
        self.card_ref.set_overlay_text(None)
        
        self.btn_fonte.setEnabled(False)
        self.input_especie.clear()
        self.input_especie.setStyleSheet("background: transparent; border: 1px solid #D1D5DB; border-radius: 6px; padding: 4px; color: #4B5563; font-style: italic; font-size: 12px; font-family: 'Segoe UI';")
        
        self.lbl_nome_comum.setText("-")
        self.lbl_descricao.setText("-")
        self.lbl_confianca.setText("-")
        
        self.txt_descricao.clear()
        self.txt_etimologia.clear()
        self.txt_etimologia.setPlaceholderText("Aguardando identificação...")
        self.lbl_titulo_etimologia.setVisible(True)
        self.txt_etimologia.setVisible(True)
        
        self.frame_etimologia.setVisible(False) 
        self.btn_google_lens.setEnabled(False)
        self.status_bar.showMessage("Pronto (Local)")
