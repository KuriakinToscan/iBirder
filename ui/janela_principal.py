import sys
import os
import json
import logging
import traceback
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFileDialog,
                             QScrollArea, QFrame, QGraphicsDropShadowEffect,
                             QMessageBox, QTextEdit, QLineEdit, QGroupBox, QGridLayout,
                             QStatusBar, QSizePolicy, QCheckBox)
from PySide6.QtCore import Qt, QSize, QTimer, Slot, Signal, QThread, QSettings, QUrl, QMimeData
from PySide6.QtGui import (QIcon, QPixmap, QColor, QFont, QDesktopServices, QPalette, QFontDatabase,
    QPainter, QAction, QDrag, QResizeEvent, QDragEnterEvent, QDropEvent
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PIL import Image, ExifTags
from datetime import datetime

# Importações do Core
from modules.step3_geography.geo_utils import extract_lat_lon
from modules.step1_identity.id_worker import LocalIdentificationWorker
from modules.step1_identity.finder_ui import JanelaManual
from ui.dialogo_aviso import DialogoAviso
from modules.step1_identity.worker_referencia import ReferenceImageWorker
from modules.step2_biology.wiki_worker import BuscadorWorker
from modules.step4_vocalization.audio_worker import AudioWorker
from core.logger import save_crash_log
from core.style_manager import StyleManager
from ui.widgets.map_widget import MapWidget
from ui.custom_widgets import ImageCardWidget, AudioPlayerWidget
from ui.dialogs.location_dialog import LocationDialog
from modules.step3_geography.geo_analyst import GeoAnalyst
from core.session_logger import SessionLogger
from modules.step3_geography.iucn_worker import IUCNWorker
from modules.step5_taxonomy.ebird_worker import EBirdWorker

class GeoWorker(QThread):
    finished = Signal(dict)
    
    def __init__(self, lat, lon, parent=None):
        super().__init__(parent)
        self.lat = lat
        self.lon = lon
        
    def run(self):
        # Instancia aqui para carregar biomas em background (thread segura)
        # Nota: Idealmente GeoAnalyst seria singleton ou carregado uma vez, 
        # mas seguindo instruções, instanciamos/usamos no fluxo.
        # Se o loading for pesado, vai ocorrer aqui sem travar UI.
        analyst = GeoAnalyst()
        details = analyst.get_full_details(self.lat, self.lon)
        self.finished.emit(details)

class JanelaPrincipal(QMainWindow):
    def __init__(self, nome_icone_janela="logo_ave.svg", modo_inicial="online", ai_status="READY"):
        super().__init__()
        self.nome_icone_janela = nome_icone_janela
        self.ai_status = ai_status
        
        # Logging de Sessão Temporária (v0.3.15)
        self.session_logger = SessionLogger()
        
        # O Cérebro do Aplicativo (Orchestrator via Feature-Based Architecture)
        from core.orchestrator import Orchestrator
        self.orchestrator = Orchestrator(self.session_logger, parent=self)
        self.orchestrator.step1_identificacao_concluida.connect(self._ao_concluir_identificacao)
        self.orchestrator.step1_identificacao_erro.connect(self._ao_erro_identificacao)
        self.orchestrator.step1_progress_updated.connect(self._ao_progresso_identificacao)
        self.orchestrator.step2_wiki_concluida.connect(self._ao_receber_info_especie)
        self.orchestrator.step3_iucn_concluida.connect(self._ao_concluir_iucn)
        self.orchestrator.step4_audio_concluido.connect(self._ao_encontrar_audio)
        self.orchestrator.step4_audio_erro.connect(self._ao_erro_audio)
        self.orchestrator.step5_ebird_concluido.connect(self._ao_concluir_ebird)
        self.orchestrator.update_available.connect(self._ao_update_disponivel)
        
        self.setWindowTitle("iBirder")
        self.resize(1100, 700)
        
        self.caminho_imagem_atual = None
        self.dados_identificacao_atual = {}
        self.lat_atual = None
        self.lon_atual = None

        self._configurar_ui()
        self._aplicar_estilo()
        
        # O Porteiro (Aviso de Funcionalidades em Falta - v0.3.41)
        from ui.dialogs.startup_status_dialog import StartupStatusDialog
        StartupStatusDialog.verificar_e_exibir(self)
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
        
        # Reset mapa e botão de location se for nova busca por texto (manual)
        # Se for por imagem, o _carregar_imagem lida com isso.
        # Mas aqui é _iniciar_busca_imagem(nome_cientifico), chamado após identificação ou busca manual de texto.
        # Não devemos resetar a localização aqui se ela veio da imagem carregada.
        
        self.txt_descricao.clear() # Reset descrição anterior
        
        # Reset para estado "Aguardando"
        self.txt_etimologia.clear()
        self.txt_etimologia.setPlaceholderText("Aguardando identificação...")
        self.lbl_titulo_etimologia.setVisible(True)
        self.txt_etimologia.setVisible(True)

        # Limpeza segura do worker anterior
        old_worker_ref = getattr(self, "worker_referencia", None)
        if old_worker_ref is not None:
            try:
                old_worker_ref.image_found.disconnect()
                old_worker_ref.search_failed.disconnect()
            except: pass
            
            if old_worker_ref.isRunning():
                old_worker_ref.requestInterruption()
                old_worker_ref.quit()
                old_worker_ref.wait() # Bloqueia brevemente para garantir parada
            old_worker_ref.deleteLater()

        self.worker_referencia = ReferenceImageWorker(nome_cientifico, parent=self)
        self.worker_referencia.image_found.connect(self._ao_encontrar_imagem_referencia)
        self.worker_referencia.search_failed.connect(lambda: self.card_ref.set_placeholder("Sem referência"))
        self.worker_referencia.start()
        
        self.worker_referencia.start()
        
        # A busca de biologia via iNaturalist/WikiAves foi transferida para o Orchestrator
        
        
    def _ao_update_disponivel(self, manifest_data):
        ver = manifest_data.get("version", "?")
        btn_update = QPushButton(f"Nova I.A. das Aves (v{ver}) Disponível! Clique para turbinar.")
        btn_update.setStyleSheet("background-color: #27ae60; color: white; border-radius: 4px; padding: 2px 10px; font-weight: bold; font-size: 11px;")
        btn_update.setCursor(Qt.PointingHandCursor)
        btn_update.clicked.connect(lambda: self._iniciar_download_update(manifest_data))
        
        self.statusBar().addWidget(btn_update)
        self._btn_update_ota = btn_update

    def _iniciar_download_update(self, manifest_data):
        resposta = QMessageBox.question(
            self,
            "Turbinar Inteligência Artificial",
            "Deseja ensinar centenas de novas espécies de aves ao iBirder?\n\n"
            "Isso consumirá cerca de 3.5 MB de dados rápidos.\n"
            "O aplicativo continuará funcionando normalmente durante o aprendizado.",
            QMessageBox.Yes | QMessageBox.No
        )
        if resposta == QMessageBox.Yes:
            if hasattr(self, '_btn_update_ota'):
                self._btn_update_ota.deleteLater()
            
            self.statusBar().showMessage("Iniciando aprendizado da nova IA...", 5000)
            
            # Aciona o worker de download real (Fase B/C)
            from core.updater import ModelDownloadWorker
            self.download_worker = ModelDownloadWorker(manifest_data, parent=self)
            self.download_worker.progress_updated.connect(self.statusBar().showMessage)
            self.download_worker.download_complete.connect(self._ao_concluir_download_ota)
            self.download_worker.error_occurred.connect(self._ao_erro_download_ota)
            self.download_worker.start()
            
    def _ao_concluir_download_ota(self, info_dict):
        from modules.step1_identity.id_worker import free_interpreter_cache
        free_interpreter_cache()
        self.statusBar().showMessage("Inteligência artificial turbinada com sucesso! O cérebro foi substituído silenciosamente.", 8000)
        
    def _ao_erro_download_ota(self, erro_msg):
        self.statusBar().showMessage(f"Falha na atualização invisível: {erro_msg}", 8000)


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
        # Mapeamento do BuscadorBlindado (Agora com chaves nativas corretas - v0.3.17)
        etimologia_texto = dados.get("etimologia", "")
        caracteristicas = dados.get("caracteristicas", "")
        
        # LOGGING DE SESSÃO: ETAPA 2 (v0.3.17)
        dados_etapa_2 = {
            "link_origem": dados.get("link_origem", ""),
            "descricao": caracteristicas,
            "nome_comum": dados.get("nome_comum", ""),
            "etimologia": etimologia_texto
        }
        
        if hasattr(self, 'session_logger'):
            self.session_logger.atualizar_ultimo_registro(dados_etapa_2)

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
            
        self.frame_etimologia.setVisible(False) # Esconde o antigo frame do iNaturalist se ainda visível

        # --- ATUALIZAR MAPA COM GBIF (v0.3.8) ---
        # Se temos nome científico e o mapa está ativo, atualizamos a camada
        # IMPORTANTE: Usar o nome original, pois 'nome_cientifico' do WikiAves contém a etimologia.
        raw_sciname = dados.get("original_scientific_name") or dados.get("nome_cientifico", "")
        
        # Validação Robusta para evitar chamadas inúteis ao GBIF
        termos_invalidos = ["Não encontrado", "Inconclusiva", "Baixa confiança", "Erro", "Analisando..."]
        sciname_valido = raw_sciname and not any(termo in raw_sciname for termo in termos_invalidos)
        
        sciname = raw_sciname if sciname_valido else None
        
        if self.map_principal:
             # Atualização do Mapa com Camada GBIF (Desacoplado do GPS)
             # Usa coordenadas da classe (já extraídas no carregamento ou manual)
             lat = self.lat_atual
             lon = self.lon_atual
             add_marker = True
             zoom_level = 10

             # Fallback: Se não tem coords, usa Centro do Brasil apenas para mostrar a distribuição
             if lat is None or lon is None:
                 lat = -15.7801
                 lon = -47.9292
                 add_marker = False
                 zoom_level = 4
                 print("[UI] Sem GPS: Usando fallback (Centro BR) para exibir mapa de distribuição.")

             print(f"[UI] Atualizando Widget de Mapa... (GBIF: {sciname}) [Lat: {lat}, Lon: {lon}]")
             try:
                 self.map_principal.update_map(lat, lon, zoom=zoom_level, add_marker=add_marker, scientific_name=sciname)
                 
                 # GeoAnalyst: Só roda se tivermos localização real (marker=True)
                 if add_marker:
                     self._atualizar_geo_info(lat, lon)
                     print("[UI] GeoAnalyst atualizado com dados reais.")
                 
                 print("[UI] Mapa renderizado com sucesso.")
             except Exception as e:
                 print(f"[UI] ERRO CRÍTICO ao atualizar mapa: {e}")
            
             print("[UI] --- PROCESSO DE IDENTIFICAÇÃO FINALIZADO ---\n")
        
    def _ao_erro_api(self, erro_msg):
        print(f"[UI] Erro na API (Info Espécie): {erro_msg}")
        self.lbl_etimologia_texto.setText(f"Erro ao buscar informações: {erro_msg}")
        self.frame_etimologia.setVisible(True)

    def _ao_erro_identificacao(self, erro_msg):
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
        # 0. Carregar Fontes Customizadas
        caminho_figtree = self._obter_caminho_asset("Figtree-VariableFont_wght.ttf")
        if os.path.exists(caminho_figtree):
            QFontDatabase.addApplicationFont(caminho_figtree)

        # Menu Bar para Configurações Adicionais
        from PySide6.QtGui import QAction
        menu_bar = self.menuBar()
        ferramentas_menu = menu_bar.addMenu("Ferramentas")
        
        action_config_api = QAction("⚙️ Configurações de Avisos de API", self)
        action_config_api.triggered.connect(lambda: __import__("ui.dialogs.api_settings_dialog", fromlist=["APISettingsDialog"]).APISettingsDialog(self).exec())
        ferramentas_menu.addAction(action_config_api)

        # --- CARREGAMENTO DO ÍCONE DA JANELA ---
        caminho_icone_janela = self._obter_caminho_asset(self.nome_icone_janela)
        caminho_ico_seguro = self._obter_caminho_asset("logo_ave.ico")
        
        icone_principal = QIcon()
        if os.path.exists(caminho_icone_janela):
            icone_principal.addFile(caminho_icone_janela)
        if os.path.exists(caminho_ico_seguro):
            icone_principal.addFile(caminho_ico_seguro) # Fallback robusto para Windows Titlebar
            
        if not icone_principal.isNull():
            self.setWindowIcon(icone_principal)

        # Container Principal com Scroll
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        # Garante fundo claro na área de scroll
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #F0F2F5; }")

        widget_central = QWidget()
        widget_central.setObjectName("container_rolagem")
        # Garante que o widget interno também tenha fundo claro, mas sem afetar filhos
        widget_central.setStyleSheet("#container_rolagem { background-color: #F0F2F5; }")
        self.scroll_area.setWidget(widget_central)
        self.setCentralWidget(self.scroll_area)

        layout_mestre = QVBoxLayout(widget_central)
        layout_mestre.setContentsMargins(StyleManager.SPACING_MD, StyleManager.SPACING_MD, StyleManager.SPACING_MD, StyleManager.SPACING_MD)
        layout_mestre.setSpacing(StyleManager.SPACING_SM)

        # --- HEADER GLOBAL (Branding + Actions) ---
        layout_header = QHBoxLayout()
        layout_header.setSpacing(StyleManager.SPACING_MD)
        
        # Branding 
        layout_branding = QHBoxLayout()
        layout_branding.setSpacing(StyleManager.SPACING_MD)
        layout_branding.setAlignment(Qt.AlignLeft)
        
        caminho_logo_painel = self._obter_caminho_asset("logo_ave.svg")
        lbl_logo = QLabel()
        lbl_logo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        if os.path.exists(caminho_logo_painel):
            pixmap_logo = QIcon(caminho_logo_painel).pixmap(QSize(96, 96))
            lbl_logo.setPixmap(pixmap_logo)
        else:
            lbl_logo.setText("🐦")
            lbl_logo.setFont(QFont("Segoe UI Emoji", 32))
        
        layout_branding.addWidget(lbl_logo)
        
        layout_textos_header = QVBoxLayout()
        layout_textos_header.setSpacing(0)
        
        lbl_subtitulo = QLabel("IA para Birdwatching")
        lbl_subtitulo.setObjectName("lbl_slogan")
        lbl_subtitulo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        layout_textos_header.addWidget(lbl_subtitulo)
        
        layout_branding.addLayout(layout_textos_header)
        layout_header.addLayout(layout_branding)
        
        # Espaçador Central
        layout_header.addStretch()

        # Botões Header (Reload, Ajuda, Config)
        layout_ajuda = QHBoxLayout()
        
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
        self.btn_ajuda.setToolTip("Manual de Instruções")
        caminho_help = self._obter_caminho_asset("icon_help.svg")
        if os.path.exists(caminho_help):
            self.btn_ajuda.setIcon(QIcon(caminho_help))
            self.btn_ajuda.setIconSize(QSize(24, 24))
        else:
             self.btn_ajuda.setText("?")
             self.btn_ajuda.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.btn_ajuda.clicked.connect(self._abrir_manual)
        
        layout_ajuda.addWidget(self.btn_ajuda)
        
        # Novo: Botão de Configurações
        self.btn_config_global = QPushButton()
        self.btn_config_global.setFixedSize(40, 40)
        self.btn_config_global.setProperty("class", "icon-btn")
        self.btn_config_global.setCursor(Qt.PointingHandCursor)
        self.btn_config_global.setToolTip("Configurações do Sistema")
        caminho_config = self._obter_caminho_asset("icon_config.svg")
        if os.path.exists(caminho_config):
            self.btn_config_global.setIcon(QIcon(caminho_config))
            self.btn_config_global.setIconSize(QSize(24, 24))
        else:
            self.btn_config_global.setText("⚙")
            self.btn_config_global.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.btn_config_global.clicked.connect(lambda: __import__("ui.dialogs.api_settings_dialog", fromlist=["APISettingsDialog"]).APISettingsDialog(self).exec())
        
        layout_ajuda.addWidget(self.btn_config_global)
        
        # --- SOLDA CIRÚRGICA DE BRANDING PERDIDA NA FASE L ---
        layout_header.addLayout(layout_ajuda)
        layout_mestre.addLayout(layout_header)
        
        # --- NOVO: GRID DE COLUNAS COM SIMETRIA ABSOLUTA (v0.3.46/v0.3.47/v0.3.50) ---
        layout_cards_superiores = QGridLayout()
        layout_cards_superiores.setSpacing(15)
        
        # OBRIGAR SIMETRIA: As colunas 0, 1 e 2 devem ter exato peso 1
        layout_cards_superiores.setColumnStretch(0, 1)
        layout_cards_superiores.setColumnStretch(1, 1)
        layout_cards_superiores.setColumnStretch(2, 1)

        # LINHA 0: TÍTULOS
        lbl_titulo_user = QLabel("Imagem Pesquisada")
        lbl_titulo_user.setProperty("class", "lbl-titulo-sessao")
        lbl_titulo_user.setProperty("margin-bottom", "sm")
        layout_cards_superiores.addWidget(lbl_titulo_user, 0, 0)
        
        lbl_titulo_ref = QLabel("Imagem Referência")
        lbl_titulo_ref.setProperty("class", "lbl-titulo-sessao")
        lbl_titulo_ref.setProperty("margin-bottom", "sm")
        layout_cards_superiores.addWidget(lbl_titulo_ref, 0, 1)

        lbl_titulo_res = QLabel("Resultados da Análise")
        lbl_titulo_res.setProperty("class", "lbl-titulo-sessao")
        lbl_titulo_res.setProperty("margin-bottom", "sm")
        layout_cards_superiores.addWidget(lbl_titulo_res, 0, 2)
        
        # LINHA 1: WIDGETS E PAINÉIS
        # Célula (1, 0) - Imagem User e Botão Lens (Integrados Diretamente no Grid + VBoxLayout filho p/ botao)
        layout_imagem_btn_user = QVBoxLayout()
        layout_imagem_btn_user.setSpacing(StyleManager.SPACING_SM)
        
        self.card_user = ImageCardWidget()
        self.card_user.set_placeholder("Arraste e solte uma foto aqui\n\nou clique para selecionar")
        self.card_user.set_on_drop(self._carregar_imagem)
        self.card_user.set_on_click(self._abrir_seletor_arquivo)
        layout_imagem_btn_user.addWidget(self.card_user, stretch=1)
        
        self.btn_google_lens = QPushButton("Pesquisar com Google Lens")
        self.btn_google_lens.setCursor(Qt.PointingHandCursor)
        self.btn_google_lens.setEnabled(False)
        self.btn_google_lens.clicked.connect(self._abrir_google_lens)
        layout_imagem_btn_user.addWidget(self.btn_google_lens)
        
        # Ancorando estritamente ao topo sem stretch inflador:
        layout_cards_superiores.addLayout(layout_imagem_btn_user, 1, 0, alignment=Qt.AlignTop)

        # Célula (1, 1) - Imagem Referência e Botão Fonte
        layout_imagem_btn_ref = QVBoxLayout()
        layout_imagem_btn_ref.setSpacing(StyleManager.SPACING_SM)
        
        self.card_ref = ImageCardWidget()
        self.card_ref.set_placeholder("Aguardando a identificação da ave.")
        layout_imagem_btn_ref.addWidget(self.card_ref, stretch=1)
        
        self.btn_fonte = QPushButton("Abrir Fonte")
        self.btn_fonte.setCursor(Qt.PointingHandCursor)
        self.btn_fonte.setVisible(True)
        self.btn_fonte.setEnabled(False)
        self.btn_fonte.clicked.connect(lambda: QDesktopServices.openUrl(self.btn_fonte.property("url_alvo")))
        layout_imagem_btn_ref.addWidget(self.btn_fonte)
        
        # Ancorando estritamente ao topo sem stretch inflador:
        layout_cards_superiores.addLayout(layout_imagem_btn_ref, 1, 1, alignment=Qt.AlignTop)
        
        # Célula (1, 2) - Painel de Resultados (Antigo Lado Direito)
        self.painel_direito = QFrame()
        self.painel_direito.setProperty("class", "painel")
        
        sombra = QGraphicsDropShadowEffect()
        sombra.setBlurRadius(20)
        sombra.setColor(QColor(0, 0, 0, 20))
        sombra.setOffset(0, 5)
        self.painel_direito.setGraphicsEffect(sombra)

        layout_direito = QVBoxLayout()
        self.painel_direito.setLayout(layout_direito)
        layout_direito.setSpacing(StyleManager.SPACING_MD)
        layout_direito.setContentsMargins(12, 18, 12, 12)
        
        layout_cards_superiores.addWidget(self.painel_direito, 1, 2, 3, 1) # RowSpan=3, ColSpan=1
        
        # Junta o bloco principal de 3 colunas ao mestre
        layout_mestre.addLayout(layout_cards_superiores)
        
        # --- BLOCO INFERIOR CENTRALIZADO (PÓS-GRID) ---
        layout_inferior = QVBoxLayout()
        layout_inferior.setSpacing(StyleManager.SPACING_MD)
        
        # --- Campo de Descrição Rica (v0.2.1) ---
        lbl_titulo_desc = QLabel('Descrição da Espécie <i>(WikiAves)</i>')
        lbl_titulo_desc.setProperty("class", "lbl-titulo-sessao")
        lbl_titulo_desc.setProperty("margin-top", "md")
        layout_inferior.addWidget(lbl_titulo_desc)

        self.txt_descricao = QTextEdit()
        self.txt_descricao.setReadOnly(True)
        self.txt_descricao.setPlaceholderText("Descrição da espécie...")
        self.txt_descricao.setMinimumHeight(45) 
        self.txt_descricao.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.txt_descricao.textChanged.connect(self._ajustar_altura_descricao)
        
        self.txt_descricao.setProperty("class", "container-borda-cinza")
        
        layout_inferior.addWidget(self.txt_descricao)
        
        self.btn_nova = QPushButton("Nova Identificação")
        self.btn_nova.setCursor(Qt.PointingHandCursor)
        self.btn_nova.clicked.connect(self._abrir_seletor_arquivo)
        layout_inferior.addWidget(self.btn_nova)
        
        # --- NOVO: Mapa Único (v0.3.3) ---
        lbl_titulo_geo = QLabel("Localização Geográfica")
        lbl_titulo_geo.setProperty("class", "lbl-titulo-sessao")
        lbl_titulo_geo.setProperty("margin-bottom", "md")
        layout_inferior.addWidget(lbl_titulo_geo)
        
        self.map_principal = MapWidget()
        self.map_principal.setMinimumHeight(350) 
        self.map_principal.show_placeholder_message("Aguardando dados de Localização")
        self.map_principal.marker_dragged.connect(self._ao_arrastar_pino)
        layout_inferior.addWidget(self.map_principal)
        
        # --- Botão Definir Localização Manualmente e IUCN (v0.3.19) ---
        layout_map_botoes = QHBoxLayout()
        layout_map_botoes.setSpacing(StyleManager.SPACING_SM)
        
        self.btn_set_location = QPushButton("Definir Localização Manualmente")
        self.btn_set_location.setCursor(Qt.PointingHandCursor)
        self.btn_set_location.setVisible(True)
        self.btn_set_location.clicked.connect(self._abrir_dialogo_localizacao)
        self.btn_set_location.setStyleSheet("""
            QPushButton {
                background-color: #374151; 
                color: white; 
                border-radius: 8px; 
                padding: 10px; 
                font-weight: bold;
                font-family: "Segoe UI";
                margin-top: 10px;
            }
            QPushButton:hover { background-color: #1F2937; }
        """)
        
        layout_map_botoes.addWidget(self.btn_set_location, stretch=1)
        
        layout_inferior.addLayout(layout_map_botoes)
        
        # Adiciona o bloco inferior restrito às colunas 0 e 1 do Grid (Logo abaixo das imagens)
        layout_cards_superiores.addLayout(layout_inferior, 2, 0, 2, 2) # Row=2, Col=0, RowSpan=2, ColSpan=2
        
        # Painel Branco Interno Layouts
        # (O layout_direito já foi inicializado e setado acima no `self.painel_direito.setLayout(layout_direito)`)
        # Layouts de grupo_resultados continuarão a ser inseridos nele mais tarde no código.
        
        # Grupo Resultados
        grupo_resultados = QGroupBox("") 
        layout_res = QVBoxLayout()
        layout_res.setSpacing(8)
        
        self.lbl_nome_comum = QLabel("-")
        self.lbl_nome_comum.setObjectName("lbl_nome_comum")
        self.lbl_nome_comum.setFont(QFont("Segoe UI", 13))
        self.lbl_nome_comum.setWordWrap(True)
        self.lbl_nome_comum.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        self.lbl_confianca = QLabel("-")
        self.lbl_confianca.setObjectName("lbl_confianca")
        self.lbl_confianca.setProperty("class", "lbl-titulo-sessao")
        self.lbl_confianca.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        self.lbl_descricao = QLabel("-") 
        self.lbl_descricao.setObjectName("lbl_descricao")
        self.lbl_descricao.setWordWrap(True)
        self.lbl_descricao.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.lbl_descricao.setWordWrap(True)
        
        # Label Nome Científico Padronizado
        lbl_titulo_nc = QLabel("Nome Científico")
        lbl_titulo_nc.setProperty("class", "lbl-titulo-sessao")
        lbl_titulo_nc.setProperty("margin-top", "md")
        layout_res.addWidget(lbl_titulo_nc)

        # Container de Busca Manual
        container_busca = QHBoxLayout()
        container_busca.setContentsMargins(0, 0, 0, 0)
        container_busca.setSpacing(StyleManager.SPACING_SM)
        
        self.input_especie = QLineEdit()
        self.input_especie.setPlaceholderText("pesquise ou digite")
        # Força a cor do placeholder para #4B5563
        palette = self.input_especie.palette()
        palette.setColor(self.input_especie.foregroundRole(), QColor("#4B5563"))
        palette.setColor(QPalette.PlaceholderText, QColor("#4B5563"))
        palette.setColor(QPalette.Text, QColor("#4B5563"))
        self.input_especie.setPalette(palette)
        
        self.input_especie.setProperty("class", "container-borda-cinza")
        self.input_especie.returnPressed.connect(self._realizar_busca_manual)
        
        self.btn_search = QPushButton()
        self.btn_search.setCursor(Qt.PointingHandCursor)
        self.btn_search.setFixedSize(32, 32)
        # O botão da lupa é icon-only e não usa os backgrounds globais.
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
        self.lbl_titulo_etimologia.setProperty("class", "lbl-titulo-sessao")
        self.lbl_titulo_etimologia.setProperty("margin-top", "md")
        self.lbl_titulo_etimologia.setVisible(True)
        layout_res.addWidget(self.lbl_titulo_etimologia)

        self.txt_etimologia = QTextEdit()
        self.txt_etimologia.setReadOnly(True)
        self.txt_etimologia.setPlaceholderText("Aguardando identificação...")
        self.txt_etimologia.setMinimumHeight(30) 
        self.txt_etimologia.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.txt_etimologia.textChanged.connect(self._ajustar_altura_etimologia)
        self.txt_etimologia.setProperty("class", "container-borda-cinza")
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
        # Estilo Global
        self.btn_wiki.clicked.connect(self._buscar_wikiaves)
        layout_botoes.addWidget(self.btn_wiki)
        
        self.btn_ebird = QPushButton("eBird")
        self.btn_ebird.setCursor(Qt.PointingHandCursor)
        # Estilo Global
        self.btn_ebird.clicked.connect(self._buscar_ebird)
        layout_botoes.addWidget(self.btn_ebird)

        self.btn_google = QPushButton("Google")
        self.btn_google.setCursor(Qt.PointingHandCursor)
        # Estilo Global
        self.btn_google.clicked.connect(self._buscar_google)
        layout_botoes.addWidget(self.btn_google)
        
        layout_res.addLayout(layout_botoes)
        
        # Etapa 5 (Taxonomia Fallback)
        self.lbl_ebird_fallback = QLabel("<a href='ebird' style='color: #9CA3AF; font-style: italic; font-size: 11px; text-decoration: none;'>Taxonomia: Acesso aos dados não configurado</a>")
        self.lbl_ebird_fallback.linkActivated.connect(lambda link: self._abrir_configuracoes_ebird())
        self.lbl_ebird_fallback.setVisible(False)
        layout_res.addWidget(self.lbl_ebird_fallback)
        
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
        grupo_audio.setProperty("class", "grupo-sessao-inferior")
        layout_audio = QVBoxLayout()
        
        lbl_titulo_audio = QLabel("Vocalizações")
        lbl_titulo_audio.setProperty("class", "lbl-titulo-sessao")
        lbl_titulo_audio.setProperty("margin-bottom", "md")
        layout_audio.addWidget(lbl_titulo_audio)
        
        self.lbl_audio_placeholder = QLabel("Áudio não carregado")
        self.lbl_audio_placeholder.setAlignment(Qt.AlignCenter)
        self.lbl_audio_placeholder.setProperty("class", "container-borda-tracejada")
        layout_audio.addWidget(self.lbl_audio_placeholder)
        
        grupo_audio.setLayout(layout_audio)
        layout_res.addWidget(grupo_audio)

        # --- NOVO: Card Informações Geográficas (v0.3.5) ---
        # --- NOVO: Card Dados Geográficos (v0.3.19 - Realocado) ---
        grupo_geo = QGroupBox("")
        grupo_geo.setProperty("class", "grupo-sessao-inferior")
        layout_geo = QVBoxLayout()
        
        lbl_titulo_geo_card = QLabel("Dados Geográficos")
        lbl_titulo_geo_card.setProperty("class", "lbl-titulo-sessao")
        lbl_titulo_geo_card.setProperty("margin-bottom", "md")
        layout_geo.addWidget(lbl_titulo_geo_card)
        
        # Reutilizando self.lbl_geo_details aqui
        self.lbl_geo_details = QLabel("Aguardando localização...")
        self.lbl_geo_details.setWordWrap(True)
        self.lbl_geo_details.setTextFormat(Qt.RichText)
        self.lbl_geo_details.setProperty("class", "container-borda-cinza-fill")
        # Diferente da esquerda, aqui ele pode começar visivel como placeholder ou invisivel. 
        # O User pediu para seguir formatação dos demais. Vamos manter visivel com placeholder ou vazio.
        # Mas a logica de _ao_concluir atualiza o texto. Vamos iniciar vazio ou com msg.
        self.lbl_geo_details.setVisible(False) 
        
        layout_geo.addWidget(self.lbl_geo_details)
        
        # Etapa 3 (IUCN Fallback)
        self.lbl_iucn_fallback = QLabel("<a href='iucn' style='color: #9CA3AF; font-style: italic; font-size: 11px; text-decoration: none;'>IUCN: Acesso aos dados não configurado</a>")
        self.lbl_iucn_fallback.linkActivated.connect(lambda link: self._abrir_configuracoes_iucn())
        self.lbl_iucn_fallback.setVisible(False)
        layout_geo.addWidget(self.lbl_iucn_fallback)
        
        grupo_geo.setLayout(layout_geo)
        layout_res.addWidget(grupo_geo)
        # ---------------------------------------------------
        
        grupo_resultados.setLayout(layout_res)
        layout_direito.addWidget(grupo_resultados)
        layout_direito.addStretch()

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
                margin-top: 12px; 
                padding-top: 12px; 
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
            url = f"https://ebird.org/species/{sciname.replace(' ', '%20')}" 
            # Tentativa de link direto melhorado, ou busca google falback
            url = f"https://www.google.com/search?q={sciname}+site:ebird.org"
            QDesktopServices.openUrl(url)

    def _atualizar_mapa_com_gbif(self, sciname):
        """Atualiza o mapa com a camada GBIF se houver coordenadas definidas."""
        # Tenta recuperar coordenadas do card geo ou do mapa (se tivessemos getter)
        # Vamos assumir que se o mapa está visivel, temos coordenadas no self.map_principal (folium não guarda estado fácil assim no widget)
        # Melhor abordagem: Se temos sciname, re-renderizamos o mapa com as coordenadas atuais.
        # Mas onde guardamos as coords atuais?
        # Vamos extrair do texto do placeholder por enquanto ou salvar numa variavel de estado da classe.
        pass # Implementado no _identificar_ave atualizando o estado global seria melhor.

    # ... Metodos auxiliares ...

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
        self.orchestrator.start_cascade_from_step2(sci_formatted)
        
        self.btn_wiki.setVisible(True)
        self.btn_google.setVisible(True)
        self.btn_ebird.setVisible(True)

        # LOGGING DE SESSÃO: ETAPA 1 (v0.3.16)
        dados_etapa_1 = {
             "nome_cientifico": sci_formatted,
             "descricao": "Identificação inserida manualmente pelo usuário.",
             "status_msg": "Busca Direta",
             "confianca": "Identificado pelo usuário"
        }
        if hasattr(self, 'session_logger'):
             self.session_logger.registrar_identificacao(dados_etapa_1)

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
        
        # --- Extração de Metadados (EXIF) v0.3.14 (Granular & Safe) ---
        autor_exif = "Autor desconhecido"
        data_exif = "Data não disponível"
        
        exif_raw = None
        try:
            with Image.open(caminho) as img:
                exif_raw = img._getexif()
        except Exception:
            pass
            
        if exif_raw:
            # Mapear Tags (Código -> Nome)
            try:
                exif = {ExifTags.TAGS.get(k, k): v for k, v in exif_raw.items()}
            except Exception:
                exif = {}

            # 1. Autor (Isolado)
            try:
                artist = exif.get("Artist")
                xp_author = exif.get("XPAuthor")
                
                if artist:
                     autor_exif = f"Autor: {str(artist).strip()}"
                elif xp_author:
                     # XP tags geralmente são bytes com null terminator
                     if isinstance(xp_author, bytes):
                        val = xp_author.decode("utf-16le").replace('\x00', '').strip()
                        if val: autor_exif = f"Autor: {val}"
            except Exception:
                pass # Mantém default "Autor desconhecido"
            
            # 2. Data (Isolado)
            try:
                date_str = exif.get("DateTimeOriginal")
                if date_str:
                     dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                     data_exif = dt.strftime("%d/%m/%Y - %H:%M")
            except Exception:
                pass # Mantém default "Data não disponível"

        self.card_user.set_overlay_details(autor_exif, data_exif)
        
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
            self.lat_atual = lat
            self.lon_atual = lon
            print(f"[MAPA] Coordenadas encontradas: {lat}, {lon}")
            
            if self.map_principal:
                # Mapa atualiza apenas com coordenadas por enquanto. 
                # O nome científico virá depois, na identificação.
                self.map_principal.update_map(lat, lon, zoom=6, add_marker=True)
                
            # Atualiza card geo
            # Atualiza card geo
            self.lbl_geo_details.setVisible(True)
            self.lbl_geo_details.setText(f"Lat: {lat:.4f}, Lon: {lon:.4f} (Processando...)")
            self.lbl_geo_details.setStyleSheet("""
                QLabel {
                    background-color: #F9FAFB;
                    border: 1px solid #E5E7EB;
                    border-radius: 6px;
                    padding: 6px;
                    color: #374151;
                    font-size: 12px;
                }
            """)
            
            # GeoAnalyst (v0.3.11)
            self._atualizar_geo_info(lat, lon)
                
        else:
            # Se não tem na imagem, verifica se tem manual anterior para manter como atual
            if getattr(self, "ultima_localizacao_manual", None):
                 self.lat_atual, self.lon_atual = self.ultima_localizacao_manual
            
            print("[MAPA] Sem dados GPS. Exibindo mensagem de aviso.")
            msg_erro = "Dados de localização não disponíveis na imagem"
            
            if self.map_principal:
                 # Se já tivermos uma localização manual definida anteriormente, não mostramos erro, mantemos o mapa.
                 # Mas como é uma NOVA imagem carregada, o ideal é resetar ou mostrar o erro.
                 # Vamos mostrar o erro para incentivar o uso do botão manual se necessário.
                 self.map_principal.show_placeholder_message(msg_erro)
                 self.map_principal.show_placeholder_message(msg_erro)
                 self.lbl_geo_details.setVisible(True)
                 self.lbl_geo_details.setText("Localização não detectada na imagem.")
                 self.lbl_geo_details.setStyleSheet("color: #9CA3AF; font-style: italic; border: 1px dashed #D1D5DB; border-radius: 6px; padding: 10px;")
             
        self._identificar_ave()

    def _ao_arrastar_pino(self, lat, lon):
        print(f"[UI] Pino do mapa arrastado para: Lat {lat}, Lon {lon}")
        lat = round(lat, 6)
        lon = round(lon, 6)
        self.lat_atual = lat
        self.lon_atual = lon
        self.status_bar.showMessage(f"Coordenadas atualizadas via mapa (Lat {lat}, Lon {lon})")
        # Update map to prevent marker jumping back and forth awkwardly? No, it's already there. 
        # But we must update _atualizar_geo_info to fetch biome, municipality, IUCN state, etc.
        self._atualizar_geo_info(lat, lon)

    def _abrir_dialogo_localizacao(self):
        dialog = LocationDialog(self)
        if dialog.exec():
            lat, lon = dialog.get_coordinates()
            if lat is not None and lon is not None:
                self.lat_atual = lat
                self.lon_atual = lon
                # Atualizar mapa
                if self.map_principal:
                    # Se já temos espécie identificada, passamos o nome para o GBIF
                    sciname = self.dados_identificacao_atual.get("nome_cientifico")
                    self.map_principal.update_map(lat, lon, zoom=6, add_marker=True, scientific_name=sciname)
                
                # Atualizar card geográfico
                # Atualizar card geográfico
                self.lbl_geo_details.setVisible(True)
                self.lbl_geo_details.setText(f"Lat: {lat:.4f}, Lon: {lon:.4f} (Manual)")
                self.lbl_geo_details.setStyleSheet("""
                    QLabel {
                        background-color: #F9FAFB;
                        border: 1px solid #E5E7EB;
                        border-radius: 6px;
                        padding: 6px;
                        color: #374151;
                        font-size: 12px;
                    }
                """)
                
                self._atualizar_geo_info(lat, lon)
                
                # Salva a localização manual para ser usada ao recarregar imagem ou atualizar mapa
                self.ultima_localizacao_manual = (lat, lon)
                
                # Oculta o botão se a localização foi definida com sucesso
                self.btn_set_location.setVisible(False)           
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
        
        try:
            self.orchestrator.start_pipeline_identificacao(self.caminho_imagem_atual)
        except Exception as e:
            self._ao_erro_identificacao(f"Falha ao iniciar orchestrator: {e}")

    def _ao_progresso_identificacao(self, mensagem):
        self.status_bar.showMessage(mensagem)

    def _ao_concluir_identificacao(self, resultado):
        self.card_user.setAcceptDrops(True)
        self._atualizar_info_ave(resultado)

    def _atualizar_info_ave(self, dados: dict):
        print("\n[UI] --- INICIANDO ATUALIZAÇÃO DA INTERFACE ---")
        print(f"[UI] Dados recebidos do WikiAves. Link: {dados.get('link_origem')}")
        
        # Ativar Placeholder Etapa 5 (se a chave nao existe)
        from PySide6.QtCore import QSettings
        settings = QSettings("iBirder", "App")
        import os
        if not settings.value("ebird_api_key", os.environ.get("EBIRD_API_KEY", "")).strip():
            self.lbl_ebird_fallback.setVisible(True)
        else:
            self.lbl_ebird_fallback.setVisible(False)
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
            self.input_especie.setProperty("class", "container-borda-cinza")
            # Force repaint via QStyle dynamic properties
            self.input_especie.style().unpolish(self.input_especie)
            self.input_especie.style().polish(self.input_especie)
            
            if self.dados_identificacao_atual:
                self.dados_identificacao_atual["nome_cientifico"] = sci_formatted
        else:
             self.input_especie.clear()
             self.input_especie.setProperty("class", "container-borda-cinza")
             self.input_especie.style().unpolish(self.input_especie)
             self.input_especie.style().polish(self.input_especie)
        
        self.lbl_descricao.setText(desc)
        
        if status_msg == "Baixa confiança":
            self.lbl_confianca.setText(f"{conf*100:.1f}% (Baixa)")
            self.lbl_confianca.setProperty("class", "lbl-titulo-sessao lbl-confianca-baixa")
            self.lbl_confianca.style().unpolish(self.lbl_confianca)
            self.lbl_confianca.style().polish(self.lbl_confianca)
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
            self.lbl_confianca.setProperty("class", "lbl-titulo-sessao lbl-confianca-alta")
            self.lbl_confianca.style().unpolish(self.lbl_confianca)
            self.lbl_confianca.style().polish(self.lbl_confianca)
            self.status_bar.showMessage("Identificação concluída.")
            
            self.btn_wiki.setVisible(True)
            self.btn_google.setVisible(True)
            self.btn_ebird.setVisible(True)
            
            if sci:
                self._iniciar_busca_imagem(sci)
                
            # LOGGING DE SESSÃO: ETAPA 1 (v0.3.16)
            valor = float(conf) if conf else 0.0
            dados_etapa_1 = {
                 "nome_cientifico": self.dados_identificacao_atual.get("nome_cientifico", ""),
                 "descricao": desc,
                 "status_msg": status_msg,
                 "confianca": f"{valor*100:.1f}%"
            }
            if hasattr(self, 'session_logger'):
                 self.session_logger.registrar_identificacao(dados_etapa_1)
        
        if status_msg:
             print(f"[UI] Status de Identificação: {status_msg}")

    def _ao_erro_identificacao(self, erro_msg):
        self.status_bar.showMessage("Erro na identificação.")
        self.card_user.setAcceptDrops(True)
        self.lbl_nome_comum.setText("Erro")
        self.lbl_descricao.setText(erro_msg)
        self.lbl_etimologia_texto.setText("Ocorreu um erro durante a identificação local.")
        
    # --- Áudio Player (v0.4.0) ---

    # A busca de áudio foi encapsulada no Orchestrator

    def _ao_encontrar_audio(self, resultados):
        """Recebe lista de áudios e cria os players."""
        self.lbl_audio_placeholder.setVisible(False)
        
        # Recuperar o layout do grupo de áudio
        # self.grupo_audio está em self.layout_direito -> ...
        # Precisamos acessar o layout onde os players serão inseridos.
        # No init, criamos: grupo_audio = QGroupBox... layout_audio = QVBoxLayout()
        # Mas não guardamos self.layout_audio como atributo.
        # Vamos achar pelo findChild ou guardar no init. 
        # Como não posso editar o init agora facilmente sem ver tudo, vou tentar achar o widget container.
        # O widget placeholder é self.lbl_audio_placeholder. O parent dele é o layout ou widget?
        # Layouts não são parents de widgets. O parent do lbl_audio_placeholder é o grupo? Não, o addWidget não reparenta sempre.
        # O QGroupBox 'grupo_audio' (que não é self) tem o layout.
        
        # Correção: O 'grupo_audio' não foi salvo em self. Apenas adicionado ao layout.
        # Mas 'self.lbl_audio_placeholder' está lá. Podemos pegar o layout dele.
        layout = self.lbl_audio_placeholder.parentWidget().layout()
        if not layout:
            return

        # Adiciona players
        audio_markers = []
        for audio in resultados:
            player = AudioPlayerWidget(
                url=audio['url'], 
                autor=audio['autor'], 
                fonte=audio['fonte'], 
                tipo_canto=audio.get('tipo_canto', ''), 
                distancia_texto=audio.get('distancia_texto', ''),
                audio_data=audio,
                on_play=self._registrar_audio_session,
                parent=layout.parentWidget()
            )
            layout.addWidget(player)
            
            # Adiciona coordenadas para o mapa
            if audio.get('lat') is not None and audio.get('lon') is not None:
                audio_markers.append({
                     'lat': audio['lat'],
                     'lon': audio['lon'],
                     'title': f"{audio.get('tipo_canto')} - {audio['autor']}"
                })
            
            # Guardar referencia para limpeza futura
            if not hasattr(self, 'active_audio_players'):
                self.active_audio_players = []
            self.active_audio_players.append(player)
            
        # Atualiza o mapa se tivermos novos marcadores e já existir a tela principal montada
        if audio_markers and self.map_principal:
             sci = self._obter_sciname_atual()
             self.map_principal.update_map(self.lat_atual, self.lon_atual, zoom=6, add_marker=True, scientific_name=sci, audio_markers=audio_markers)
             
    def _registrar_audio_session(self, audio):
        if not audio or not hasattr(self, 'session_logger'):
             return
             
        dados_etapa_4 = {
            "audio_url": audio.get('url', ''),
            "audio_autor": audio.get('autor', 'Desconhecido'),
            "audio_licenca": audio.get('licenca', 'CC BY-NC'),
            "audio_tipo": audio.get('tipo_canto', ''),
            "audio_qualidade": audio.get('q', ''),
            "audio_lat": audio.get('lat'),
            "audio_lon": audio.get('lon'),
            "audio_distancia_km": audio.get('distancia'),
            "audio_link_web": audio.get('link_web', ''),
            "audio_source": audio.get('fonte', 'Xeno-canto')
        }
        self.session_logger.atualizar_ultimo_registro(dados_etapa_4)

    def _ao_erro_audio(self):
        self.lbl_audio_placeholder.setText("Nenhuma gravação encontrada.")
        self.lbl_audio_placeholder.setVisible(True)

    def _atualizar_geo_info(self, lat, lon):
        """Inicia worker para buscar detalhes administrativos e bioma."""
        if not hasattr(self, 'lbl_geo_details'):
             return

        self.lbl_geo_details.setText("🔄 Analisando local e bioma...")
        self.lbl_geo_details.setVisible(True)
        
        # Limpeza Segura do Worker Anterior
        old_geo_worker = getattr(self, "geo_worker", None)
        if old_geo_worker is not None:
            if old_geo_worker.isRunning():
                old_geo_worker.requestInterruption()
                old_geo_worker.quit()
                old_geo_worker.wait() # Bloqueia brevemente para garantir parada
            old_geo_worker.deleteLater()
        
        # Instancia como atributo da classe com PARENT para evitar GC prematuro
        self.geo_worker = GeoWorker(lat, lon, parent=self)
        self.geo_worker.finished.connect(self._ao_concluir_geo_analise)
        self.geo_worker.start()
        
    def _ao_concluir_geo_analise(self, details):
        self.last_geo_data = details
        self._registrar_dados_geo_iucn()
        
        if not hasattr(self, 'lbl_geo_details'):
             return

        lat = details.get('lat')
        lon = details.get('lon')
        
        # Formatação Lat/Lon segura
        lat_str = f"{lat:.5f}" if isinstance(lat, float) else "?"
        lon_str = f"{lon:.5f}" if isinstance(lon, float) else "?"

        texto = f"""
        <b>Coordenadas:</b> Lat {lat_str}, Long {lon_str}<br>
        <b>País:</b> {details.get('pais', '-')}<br>
        <b>Estado:</b> {details.get('estado', '-')}<br>
        <b>Município:</b> {details.get('municipio', '-')}<br>
        <b>Localidade/Bairro:</b> {details.get('localidade', '-')}<br>
        <b>Bioma:</b> {details.get('bioma', '-')}<br>
        """
        self.lbl_geo_details.setText(texto)
        self.lbl_geo_details.setVisible(True)
        
        # Ativar Placeholder Etapa 3 (se a chave nao existe)
        from PySide6.QtCore import QSettings
        settings = QSettings("iBirder", "App")
        import os
        if not settings.value("iucn_api_key", os.environ.get("TOKEN_IUCN", "")).strip():
            self.lbl_iucn_fallback.setVisible(True)
        else:
            self.lbl_iucn_fallback.setVisible(False)

    # --- IUCN e Integração Geoespacial (v0.3.19) ---
    def _abrir_configuracoes_iucn(self):
        from modules.step3_geography.iucn_ui import IUCNSettingsDialog
        dlg = IUCNSettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            # Re-disparar worker caso chave inserida no meio de uma sessao
            sci = self._obter_sciname_atual()
            if sci and "Inconclusiva" not in sci:
                if hasattr(self, 'orchestrator'):
                    self.orchestrator.start_step3_geography(sci)

    def _abrir_configuracoes_ebird(self):
        from modules.step5_taxonomy.ebird_ui import EBirdSettingsDialog
        dlg = EBirdSettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            sci = self._obter_sciname_atual()
            if sci and "Inconclusiva" not in sci:
                if hasattr(self, 'orchestrator'):
                    self.orchestrator.start_step5_taxonomy(sci)
        
    def _ao_concluir_iucn(self, results):
        self.last_iucn_data = results
        self._registrar_dados_geo_iucn()

    # A busca do ebird foi movida para o Orchestrator
        
    def _ao_concluir_ebird(self, results):
        if hasattr(self, 'session_logger'):
            self.session_logger.atualizar_ultimo_registro({
                "nome_ingles": results.get("nome_ingles", ""),
                "classe": results.get("classe", "Aves"),
                "ordem": results.get("ordem", ""),
                "familia": results.get("familia", ""),
                "ebird_code": results.get("ebird_code", ""),
                "raridade_regional": results.get("raridade_regional", ""),
                "link_ebird": results.get("link_ebird", "")
            })
            print("[UI] Etapa 5 (eBird/Clements) integrada ao SessionLogger.")
            
            # Preparar persistência EXIF (Futuro v0.3.22+)
            # from modules.step6_persistence.exif_manager import EXIFManager
            # exif_manager = EXIFManager()
            # Se a imagem tiver um caminho salvo no widget card principal, passarremos.
            # exif_manager.escrever_metadados_completos(self.card_user.image_path, self.session_logger.obter_ultimo_registro())
            print("[EXIF] Módulo placeholder preparado para receber dados (Etapa Final).")


    def _registrar_dados_geo_iucn(self):
        geo = getattr(self, 'last_geo_data', {})
        iucn = getattr(self, 'last_iucn_data', {})
        
        if not geo and not iucn: return
        
        from modules.step3_geography.gbif_client import get_gbif_taxon_key
        sciname = self._obter_sciname_atual()
        link_gbif = ""
        if sciname:
            try:
                # Opcional: Pegar a key rapidamente (isso é blocante mas rápido, e o user n se importa com latência de API rapida aqui)
                taxon_key = get_gbif_taxon_key(sciname)
                if taxon_key:
                    link_gbif = f"https://www.gbif.org/species/{taxon_key}"
            except: pass

        dados = {
            "lat": self.lat_atual,
            "lon": self.lon_atual,
            "pais": geo.get("pais", "-"),
            "estado": geo.get("estado", "-"),
            "municipio": geo.get("municipio", "-"),
            "bioma": geo.get("bioma", "-"),
            "iucn_status": iucn.get("iucn_status", "Não Avaliado"),
            "link_gbif": link_gbif,
            "link_iucn": iucn.get("link_iucn", ""),
            "caminho_geojson": iucn.get("geojson_path", "")
        }
        
        if hasattr(self, 'session_logger'):
             self.session_logger.atualizar_ultimo_registro(dados)

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
        # Stop Workers
        for worker_name in ["worker_local", "geo_worker", "audio_worker"]:
            old_worker = getattr(self, worker_name, None)
            if old_worker is not None:
                if old_worker.isRunning():
                    old_worker.requestInterruption()
                    old_worker.quit()
                    old_worker.wait()
                old_worker.deleteLater()
                setattr(self, worker_name, None)

        # Limpeza de Players de Áudio (v0.4.0)
        if hasattr(self, 'active_audio_players'):
            for player in self.active_audio_players:
                try:
                    player.stop()
                    player.setParent(None)
                    player.deleteLater()
                except:
                    pass
            self.active_audio_players = []
        
        # Resetar placeholder de áudio
        if hasattr(self, 'lbl_audio_placeholder'):
            self.lbl_audio_placeholder.setText("Áudio não carregado")
            self.lbl_audio_placeholder.setVisible(True)

        self.worker_species = None
        self.audio_worker = None
        self.geo_worker = None
        self.iucn_worker = None
        self.last_geo_data = {}
        self.last_iucn_data = {}
        
        self.caminho_imagem_atual = None
        self.lat_atual = None
        self.lon_atual = None
        
        # User Card Reset
        self.card_user.set_image_path(None)
        self.card_user.set_placeholder("Arraste e solte uma foto aqui\n\nou clique para selecionar")
        
        # Ref Card Reset
        self.card_ref.set_image_path(None)
        self.card_ref.set_placeholder("Aguardando a identificação da ave.")
        self.card_ref.set_overlay_text(None)
        
        self.btn_fonte.setEnabled(False)
        self.input_especie.clear()
        self.input_especie.setProperty("class", "container-borda-cinza")
        self.input_especie.style().unpolish(self.input_especie)
        self.input_especie.style().polish(self.input_especie)
        
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
        if self.map_principal:
             self.map_principal.show_placeholder_message("Aguardando dados de Localização")
        self.status_bar.showMessage("Pronto (Local)")

    def closeEvent(self, event):
        """Sobrescreve o fechamento para limpar a caderneta de campo temporária."""
        if hasattr(self, 'session_logger'):
            self.session_logger.limpar_sessao()
        event.accept()
