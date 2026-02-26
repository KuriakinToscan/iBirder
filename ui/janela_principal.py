# ADVERTÊNCIA: Proibido adicionar barras de menu ou ferramentas tradicionais conforme RULES v1.1.
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
    QPainter, QDrag, QResizeEvent, QDragEnterEvent, QDropEvent
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
from ui.custom_widgets import ImageCardWidget, AudioPlayerWidget, VocalAuditCard
from ui.dialogs.location_dialog import LocationDialog
from ui.dialogs.vocal_detail_dialog import VocalDetailDialog
from modules.step3_geography.geo_analyst import GeoAnalyst
from core.session_logger import SessionLogger
from modules.step3_geography.iucn_worker import IUCNWorker
from modules.step5_taxonomy.ebird_worker import EBirdWorker

# GeoWorker migrado para o Orchestrator v0.4.2

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
        self.orchestrator.step3_geo_concluida.connect(self._ao_concluir_geo_analise)
        self.orchestrator.step3_conservacao_concluida.connect(self._ao_concluir_conservacao_nacional)
        self.orchestrator.step4_audio_concluido.connect(self._ao_encontrar_audio)
        self.orchestrator.step4_audio_erro.connect(self._ao_erro_audio)
        self.orchestrator.audio_processed.connect(self._plotar_pins_audio)
        self.orchestrator.limpar_painel_audio.connect(self._limpar_painel_audio)
        self.orchestrator.step5_ebird_concluido.connect(self._ao_concluir_ebird)
        self.orchestrator.update_available.connect(self._ao_update_disponivel)
        
        self.setWindowTitle("iBirder")
        self.resize(1100, 700)
        
        self.caminho_imagem_atual = None
        self.dados_identificacao_atual = {}
        self.lat_atual = None
        self.lon_atual = None
        
        # Flag de Persistência Atômica (v0.6.8)
        # Mantém o nome científico mesmo durante resets de interface
        self.especie_em_processamento = None 
        
        # Trava de Estilo (v0.6.9): Impede recursão infinita no changeEvent
        self._bloqueio_palette = False

        self._configurar_ui()
        self._aplicar_estilo()
        
        # Reforço de Title Bar Dark (v0.7.2)
        StyleManager.setup_window_theme(self)
        
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
        self.lbl_etimologia_texto.setText("Carregando...")
        self.card_etimologia.setVisible(True)

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
        print(f"[UI] SINAL: Dados biológicos recebidos via Orchestrator (WikiAves). Especial: {dados.get('nome_comum')}")
        # Mapeamento do BuscadorBlindado (Agora com chaves nativas corretas - v0.3.17)
        etimologia_texto = dados.get("etimologia", "")
        caracteristicas = dados.get("caracteristicas", "")
        
        # LOGGING DE SESSÃO: ETAPA 2 (v0.3.17)
        dados_etapa_2 = {
            "link_origem": dados.get("link_origem", ""),
            "descricao": caracteristicas,
            "nome_comum": dados.get("nome_comum", ""),
            "nome_ingles": dados.get("nome_ingles", ""),
            "etimologia": etimologia_texto
        }
        
        if hasattr(self, 'session_logger'):
            self.session_logger.atualizar_ultimo_registro(dados_etapa_2)

        # Persistência de Estado (v0.6.7): Garante que dados retornados populem o dicionário de identificação atual
        # Usamos o nome original da busca (taxonômico) para não poluir o estado com etimologia
        sci_persist = dados.get("original_scientific_name", self.dados_identificacao_atual.get("nome_cientifico", ""))
        
        if not self.dados_identificacao_atual:
            self.dados_identificacao_atual = {}
            
        self.dados_identificacao_atual.update(dados_etapa_2)
        self.dados_identificacao_atual["nome_cientifico"] = sci_persist

        # Atualiza Campo Etimologia (v0.8.2)
        if etimologia_texto and etimologia_texto != "Não encontrado":
            self.lbl_etimologia_texto.setText(etimologia_texto)
            self.card_etimologia.setVisible(True)
        elif etimologia_texto == "Não encontrado":
            self.lbl_etimologia_texto.setText("Etimologia não disponível.")
            self.card_etimologia.setVisible(True)

        # Atualiza Campo Descrição (Rodapé)
        if caracteristicas and caracteristicas != "Não encontrado":
            self.txt_descricao.setPlainText(caracteristicas)
            self.txt_descricao.setVisible(True)

        # --- AJUSTE ESTÉTICO v0.8.2: Padronização de Fontes ---
        nome_pop = dados.get("nome_comum")
        if nome_pop and nome_pop != "Não encontrado":
            self.lbl_nome_popular.setText(f"<b>Nome Popular:</b> {nome_pop}")
        else:
            self.lbl_nome_popular.setText("<b>Nome Popular:</b> <i>Não encontrado no WikiAves</i>")
        self.lbl_nome_popular.setVisible(True)

        nome_en = dados.get("nome_ingles")
        if nome_en and nome_en != "Não encontrado":
            self.lbl_nome_ingles.setText(f"<b>Nome em Inglês:</b> {nome_en}")
        else:
            self.lbl_nome_ingles.setText("<b>Nome em Inglês:</b> <i>Não encontrado no WikiAves</i>")
        self.lbl_nome_ingles.setVisible(True)

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
             zoom_level = 6

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
                 
                 # GeoAnalyst: Removido disparo manual v0.8.9. 
                 # A cascata 2 -> 3 agora é gerida exclusivamente pelo Orchestrator para evitar crash de threads.
                 if add_marker:
                     # Apenas atualizamos a label visual na UI, se necessário
                     pass
                 
                 print("[UI] Mapa renderizado com sucesso.")
             except Exception as e:
                 print(f"[UI] ERRO CRÍTICO ao atualizar mapa: {e}")
            
             # REFORÇO V0.7.7: Reafirmar soberania após carga de componentes Chromium
             StyleManager.setup_window_theme(self)
             
             print("[UI] --- PROCESSO DE IDENTIFICAÇÃO FINALIZADO ---\n")
        
    def _ao_erro_api(self, erro_msg):
        print(f"[UI] Erro na API (Info Espécie): {erro_msg}")
        self.lbl_etimologia_texto.setText(f"Erro ao buscar informações: {erro_msg}")
        self.card_etimologia.setVisible(True)

    def _ao_erro_identificacao(self, erro_msg):
        self.lbl_etimologia_texto.setText(f"Erro: {erro_msg}")
        self.card_etimologia.setVisible(True)

    def _ajustar_altura_descricao(self):
        """Ajusta a altura do campo de descrição conforme o conteúdo."""
        doc_height = self.txt_descricao.document().size().height()
        margins = self.txt_descricao.contentsMargins().top() + self.txt_descricao.contentsMargins().bottom() + 15
        self.txt_descricao.setFixedHeight(max(int(doc_height + 10), 45))

    def resizeEvent(self, event):
        """Recalcula altura dos campos de texto ao redimensionar a janela."""
        # Usa timer para garantir que o layout já foi atualizado e a largura dos campos está correta
        QTimer.singleShot(0, self._ajustar_altura_descricao)
        super().resizeEvent(event)

    def _configurar_ui(self):
        # 0. Carregar Fontes Customizadas
        caminho_figtree = self._obter_caminho_asset("Figtree-VariableFont_wght.ttf")
        if os.path.exists(caminho_figtree):
            QFontDatabase.addApplicationFont(caminho_figtree)


        # --- CARREGAMENTO DO ÍCONE DA JANELA (Dinâmico v0.6.5) ---
        StyleManager.set_app_icon(self)

        # Container Principal com Scroll
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("scroll_area_principal")
        self.scroll_area.setWidgetResizable(True)

        widget_central = QWidget()
        widget_central.setObjectName("container_rolagem")
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
        layout_branding.setSpacing(StyleManager.SPACING_MD * 2)
        layout_branding.setAlignment(Qt.AlignLeft)
        
        caminho_logo_painel = self._obter_caminho_asset("logo_ave.svg")
        lbl_logo = QLabel()
        lbl_logo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        if os.path.exists(caminho_logo_painel):
            pixmap_logo = QIcon(caminho_logo_painel).pixmap(QSize(130, 130))
            lbl_logo.setPixmap(pixmap_logo)
        else:
            lbl_logo.setText("🐦")
            lbl_logo.setFont(QFont("Segoe UI Emoji", 32))
        
        layout_branding.addWidget(lbl_logo)
        
        layout_textos_header = QVBoxLayout()
        layout_textos_header.setSpacing(0)
        
        lbl_subtitulo = QLabel("IA para Birdwatching")
        lbl_subtitulo.setObjectName("lbl_slogan")
        
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
        pass
        
        # --- SOLDA CIRÚRGICA DE BRANDING PERDIDA NA FASE L ---
        layout_header.addLayout(layout_ajuda)
        
        # Adiciona o Frame do Header ao Layout Mestre
        layout_mestre.addLayout(layout_header)
        layout_mestre.addSpacing(StyleManager.SPACING_LG)
        
        # --- NOVO: GRID DE COLUNAS COM SIMETRIA ABSOLUTA (v0.3.46/v0.3.47/v0.3.50/v0.3.53) ---
        layout_cards_superiores = QGridLayout()
        layout_cards_superiores.setSpacing(15)
        
        # OBRIGAR SIMETRIA: As colunas 0, 1 e 2 devem ter exato peso 1
        layout_cards_superiores.setColumnStretch(0, 1)
        layout_cards_superiores.setColumnStretch(1, 1)
        layout_cards_superiores.setColumnStretch(2, 1)
        
        # FASE S.1 (v0.3.53) - GRAVIDADE ZERO DAS IMAGENS, SUCÇÃO PELO MAPA
        layout_cards_superiores.setRowStretch(1, 0)
        layout_cards_superiores.setRowStretch(2, 0)
        layout_cards_superiores.setRowStretch(3, 1)

        # ANCORAGEM 0: TÍTULOS
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

        # ANCORAGEM 1: INICIALIZAÇÃO ATÔMICA DOS WIDGETS CRÍTICOS (v2.0)
        # --- Lado Esquerdo ---
        self.card_user = ImageCardWidget()
        self.card_user.set_placeholder("Arraste e solte uma foto aqui\n\nou clique para selecionar")
        self.card_user.set_on_drop(self._carregar_imagem)
        self.card_user.set_on_click(self._abrir_seletor_arquivo)
        
        sombra_user = QGraphicsDropShadowEffect(self.card_user)
        sombra_user.setBlurRadius(18)
        sombra_user.setColor(QColor(0, 0, 0, 25))
        sombra_user.setOffset(0, 4)
        self.card_user.setGraphicsEffect(sombra_user)
        
        self.btn_google_lens = QPushButton("Pesquisar com Google Lens")
        self.btn_google_lens.setCursor(Qt.PointingHandCursor)
        self.btn_google_lens.setEnabled(False)
        self.btn_google_lens.clicked.connect(self._abrir_google_lens)

        # --- Lado Centro ---
        self.card_ref = ImageCardWidget()
        self.card_ref.set_placeholder("Aguardando a identificação da ave.")
        
        sombra_ref = QGraphicsDropShadowEffect(self.card_ref)
        sombra_ref.setBlurRadius(18)
        sombra_ref.setColor(QColor(0, 0, 0, 25))
        sombra_ref.setOffset(0, 4)
        self.card_ref.setGraphicsEffect(sombra_ref)
        
        self.btn_fonte = QPushButton("Abrir Fonte")
        self.btn_fonte.setCursor(Qt.PointingHandCursor)
        self.btn_fonte.setEnabled(False)
        self.btn_fonte.clicked.connect(lambda: QDesktopServices.openUrl(self.btn_fonte.property("url_alvo")))

        # --- Lado Direito (Ações Separadas p/ Grade) ---
        self.btn_gravar_exif = QPushButton("Confirmar a identificação")
        self.btn_gravar_exif.setToolTip("Gravar dados na fotografia")
        self.btn_gravar_exif.setCursor(Qt.PointingHandCursor)

        # ANCORAGEM 2: MONTAGEM DO GRID v2.0 (GRAVIDADE ZERO)
        
        # LINHA 1: IMAGENS E PAINEL SUPERIOR
        layout_cards_superiores.addWidget(self.card_user, 1, 0, alignment=Qt.AlignTop)
        layout_cards_superiores.addWidget(self.card_ref, 1, 1, alignment=Qt.AlignTop)
        
        self.painel_direito_superior = QFrame()
        self.layout_direito_superior = QVBoxLayout(self.painel_direito_superior)
        self.layout_direito_superior.setSpacing(StyleManager.SPACING_MD)
        self.layout_direito_superior.setContentsMargins(0, 0, 0, 0)
        layout_cards_superiores.addWidget(self.painel_direito_superior, 1, 2)

        # LINHA 2: BOTÕES ALINHADOS (A META DO USUÁRIO)
        layout_cards_superiores.addWidget(self.btn_google_lens, 2, 0)
        layout_cards_superiores.addWidget(self.btn_fonte, 2, 1)
        layout_cards_superiores.addWidget(self.btn_gravar_exif, 2, 2)
        
        # Célula (1, 2) - Coluna de Cards Inferior
        self.painel_direito_inferior = QFrame()
        self.layout_direito_inferior = QVBoxLayout(self.painel_direito_inferior)
        self.layout_direito_inferior.setSpacing(StyleManager.SPACING_MD + 5)
        self.layout_direito_inferior.setContentsMargins(0, 0, 0, 0)
        
        layout_cards_superiores.addWidget(self.painel_direito_inferior, 3, 2)

        # Junta o mestre
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
        self.map_principal.audio_clicked.connect(self._ao_clicar_pin_audio)
        self.map_principal.alert_clicked.connect(self._abrir_dialogo_localizacao) # v0.6.3
        layout_inferior.addWidget(self.map_principal)
        
        
        # Adiciona o bloco inferior restrito às colunas 0 e 1 do Grid
        layout_cards_superiores.addLayout(layout_inferior, 3, 0, 1, 2)
        
        # --- CARD 1: IDENTIFICAÇÃO E TAXONOMIA (v0.8.2) ---
        self.card_id = QFrame()
        self.card_id.setProperty("class", "painel")
        self.card_id.setAttribute(Qt.WA_StyledBackground, True)
        
        sombra_id = QGraphicsDropShadowEffect(self.card_id)
        sombra_id.setBlurRadius(18)
        sombra_id.setColor(QColor(0, 0, 0, 25))
        sombra_id.setOffset(0, 4)
        self.card_id.setGraphicsEffect(sombra_id)
        
        layout_card_id = QVBoxLayout(self.card_id)
        layout_card_id.setSpacing(StyleManager.SPACING_SM)
        layout_card_id.setContentsMargins(15, 18, 15, 15)
        
        # Nome Científico / Busca
        lbl_titulo_nc = QLabel("Nome Científico")
        lbl_titulo_nc.setProperty("class", "lbl-titulo-sessao")
        layout_card_id.addWidget(lbl_titulo_nc)

        container_busca = QHBoxLayout()
        container_busca.setSpacing(StyleManager.SPACING_SM)
        self.input_especie = QLineEdit()
        self.input_especie.setPlaceholderText("pesquise ou digite")
        self.input_especie.setProperty("class", "sci-name-input")
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
        layout_card_id.addLayout(container_busca)
        layout_card_id.addSpacing(10)

        # Identificação
        lbl_titulo_id = QLabel("Identificação")
        lbl_titulo_id.setProperty("class", "lbl-titulo-sessao")
        layout_card_id.addWidget(lbl_titulo_id)

        self.lbl_confianca = QLabel("")
        self.lbl_confianca.setObjectName("lbl_confianca")
        self.lbl_confianca.setWordWrap(True)
        self.lbl_confianca.setVisible(False)
        layout_card_id.addWidget(self.lbl_confianca)

        self.lbl_nome_popular = QLabel("<b>Nome Popular:</b> <i>Aguardando identificação...</i>")
        self.lbl_nome_popular.setObjectName("lbl_nome_popular")
        self.lbl_nome_popular.setWordWrap(True)
        self.lbl_nome_popular.setTextFormat(Qt.RichText)
        self.lbl_nome_popular.setProperty("class", "container-borda-cinza-fill")
        self.lbl_nome_popular.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_nome_popular.setVisible(True)
        layout_card_id.addWidget(self.lbl_nome_popular)

        self.lbl_nome_ingles = QLabel("<b>Nome em Inglês:</b> <i>Aguardando identificação...</i>")
        self.lbl_nome_ingles.setObjectName("lbl_nome_ingles")
        self.lbl_nome_ingles.setWordWrap(True)
        self.lbl_nome_ingles.setTextFormat(Qt.RichText)
        self.lbl_nome_ingles.setProperty("class", "container-borda-cinza-fill")
        self.lbl_nome_ingles.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_nome_ingles.setVisible(True)
        layout_card_id.addWidget(self.lbl_nome_ingles)
        

        self.layout_direito_superior.addWidget(self.card_id)

        # --- CARD 1.5: TAXONOMIA (v0.8.2 - Fora do ID) ---
        self.card_taxonomia = QFrame()
        self.card_taxonomia.setProperty("class", "painel")
        self.card_taxonomia.setAttribute(Qt.WA_StyledBackground, True)
        
        sombra_taxo = QGraphicsDropShadowEffect(self.card_taxonomia)
        sombra_taxo.setBlurRadius(15)
        sombra_taxo.setColor(QColor(0, 0, 0, 20))
        sombra_taxo.setOffset(0, 3)
        self.card_taxonomia.setGraphicsEffect(sombra_taxo)
        
        layout_card_taxo = QVBoxLayout(self.card_taxonomia)
        layout_card_taxo.setContentsMargins(15, 15, 15, 15)
        
        lbl_titulo_taxo = QLabel("Taxonomia")
        lbl_titulo_taxo.setProperty("class", "lbl-titulo-sessao")
        lbl_titulo_taxo.setProperty("margin-bottom", "md")
        layout_card_taxo.addWidget(lbl_titulo_taxo)
        
        self.lbl_taxo_details = QLabel("<i>Aguardando identificação da ave...</i>")
        self.lbl_taxo_details.setWordWrap(True)
        self.lbl_taxo_details.setTextFormat(Qt.RichText)
        self.lbl_taxo_details.setProperty("class", "container-borda-cinza-fill")
        self.lbl_taxo_details.setVisible(True)
        layout_card_taxo.addWidget(self.lbl_taxo_details)
        
        self.card_taxonomia.setVisible(True)
        self.layout_direito_superior.addWidget(self.card_taxonomia)

        # --- CARD 1.6: STATUS DE CONSERVAÇÃO (NOVO v0.8.2) ---
        self.card_conservacao = QFrame()
        self.card_conservacao.setProperty("class", "painel")
        self.card_conservacao.setAttribute(Qt.WA_StyledBackground, True)
        
        sombra_cons = QGraphicsDropShadowEffect(self.card_conservacao)
        sombra_cons.setBlurRadius(15)
        sombra_cons.setColor(QColor(0, 0, 0, 20))
        sombra_cons.setOffset(0, 3)
        self.card_conservacao.setGraphicsEffect(sombra_cons)
        
        layout_card_cons = QVBoxLayout(self.card_conservacao)
        layout_card_cons.setContentsMargins(15, 15, 15, 15)
        
        lbl_titulo_cons = QLabel("Status de Conservação")
        lbl_titulo_cons.setProperty("class", "lbl-titulo-sessao")
        lbl_titulo_cons.setProperty("margin-bottom", "md")
        layout_card_cons.addWidget(lbl_titulo_cons)
        
        self.lbl_status_conservacao = QLabel("<i>Aguardando identificação da ave...</i>")
        self.lbl_status_conservacao.setWordWrap(True)
        self.lbl_status_conservacao.setTextFormat(Qt.RichText)
        self.lbl_status_conservacao.setProperty("class", "container-borda-cinza-fill")
        self.lbl_status_conservacao.setVisible(True)
        layout_card_cons.addWidget(self.lbl_status_conservacao)
        
        self.layout_direito_superior.addWidget(self.card_conservacao)

        # --- BOTÕES DE BUSCA EXTERNA (SOLTOS v0.8.2) ---
        layout_botoes = QHBoxLayout()
        layout_botoes.setSpacing(StyleManager.SPACING_MD)
        layout_botoes.setContentsMargins(0, 5, 0, 5)
        
        self.btn_wiki = QPushButton("WikiAves")
        self.btn_wiki.setCursor(Qt.PointingHandCursor)
        self.btn_wiki.clicked.connect(self._buscar_wikiaves)
        layout_botoes.addWidget(self.btn_wiki, stretch=1)
        
        self.btn_ebird = QPushButton("eBird")
        self.btn_ebird.setCursor(Qt.PointingHandCursor)
        self.btn_ebird.clicked.connect(self._buscar_ebird)
        layout_botoes.addWidget(self.btn_ebird, stretch=1)
 
        self.btn_google = QPushButton("Google")
        self.btn_google.setCursor(Qt.PointingHandCursor)
        self.btn_google.clicked.connect(self._buscar_google)
        layout_botoes.addWidget(self.btn_google, stretch=1)
        
        self.layout_direito_superior.addLayout(layout_botoes)
        

        # Botão movido para a linha 2 do Grid (v0.8.2 Refinement)
        pass
        
        # --- CARD 2: ETIMOLOGIA (v0.8.2) ---
        self.card_etimologia = QFrame()
        self.card_etimologia.setProperty("class", "painel")
        self.card_etimologia.setAttribute(Qt.WA_StyledBackground, True)
        
        sombra_etim = QGraphicsDropShadowEffect(self.card_etimologia)
        sombra_etim.setBlurRadius(15)
        sombra_etim.setColor(QColor(0, 0, 0, 20))
        sombra_etim.setOffset(0, 3)
        self.card_etimologia.setGraphicsEffect(sombra_etim)
        
        layout_card_etimologia = QVBoxLayout(self.card_etimologia)
        layout_card_etimologia.setContentsMargins(15, 15, 15, 15)
        
        lbl_titulo_etimologia = QLabel("Etimologia (WikiAves)")
        lbl_titulo_etimologia.setProperty("class", "lbl-titulo-sessao")
        lbl_titulo_etimologia.setProperty("margin-bottom", "md")
        layout_card_etimologia.addWidget(lbl_titulo_etimologia)
        
        # Frame Interno Verde (Estilo Legado v0.8.2 mantido em container painel)
        self.frame_etimologia_info = QFrame()
        self.frame_etimologia_info.setObjectName("frame_etimologia")
        self.frame_etimologia_info.setStyleSheet("""
            QFrame#frame_etimologia {
                background-color: #F8F9FA;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        layout_etim_info = QVBoxLayout(self.frame_etimologia_info)
        layout_etim_info.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_etimologia_texto = QLabel("Carregando...")
        self.lbl_etimologia_texto.setWordWrap(True)
        self.lbl_etimologia_texto.setStyleSheet("color: #374151; font-size: 12px;")
        layout_etim_info.addWidget(self.lbl_etimologia_texto)
        
        layout_card_etimologia.addWidget(self.frame_etimologia_info)
        self.card_etimologia.setVisible(True)
        self.layout_direito_inferior.addWidget(self.card_etimologia)

        # Botão Confirmar agora reside na Linha 2 do QGridLayout Principal (v2.0)
        pass
        
        # --- CARD 3: DADOS GEOGRÁFICOS (v0.8.2) ---
        self.card_geo = QFrame()
        self.card_geo.setProperty("class", "painel")
        self.card_geo.setAttribute(Qt.WA_StyledBackground, True)
        
        sombra_geo = QGraphicsDropShadowEffect(self.card_geo)
        sombra_geo.setBlurRadius(15)
        sombra_geo.setColor(QColor(0, 0, 0, 20))
        sombra_geo.setOffset(0, 3)
        self.card_geo.setGraphicsEffect(sombra_geo)
        
        layout_card_geo = QVBoxLayout(self.card_geo)
        layout_card_geo.setContentsMargins(15, 15, 15, 15)
        
        lbl_titulo_geo_card = QLabel("Dados Geográficos")
        lbl_titulo_geo_card.setProperty("class", "lbl-titulo-sessao")
        lbl_titulo_geo_card.setProperty("margin-bottom", "md")
        layout_card_geo.addWidget(lbl_titulo_geo_card)
        
        self.lbl_geo_details = QLabel("Aguardando localização...")
        self.lbl_geo_details.setWordWrap(True)
        self.lbl_geo_details.setTextFormat(Qt.RichText)
        self.lbl_geo_details.setProperty("class", "container-borda-cinza-fill")
        self.lbl_geo_details.setVisible(True) 
        layout_card_geo.addWidget(self.lbl_geo_details)
        
        self.layout_direito_inferior.addWidget(self.card_geo)

        # --- CARD 4: VOCALIZAÇÕES (v0.8.2) ---
        self.card_audio = QFrame()
        self.card_audio.setProperty("class", "painel")
        self.card_audio.setAttribute(Qt.WA_StyledBackground, True)
        
        sombra_audio = QGraphicsDropShadowEffect(self.card_audio)
        sombra_audio.setBlurRadius(15)
        sombra_audio.setColor(QColor(0, 0, 0, 20))
        sombra_audio.setOffset(0, 3)
        self.card_audio.setGraphicsEffect(sombra_audio)
        
        layout_card_audio = QVBoxLayout(self.card_audio)
        layout_card_audio.setContentsMargins(15, 15, 15, 15)
        
        self.lbl_vocal_title = QLabel("Vocalizações")
        self.lbl_vocal_title.setProperty("class", "lbl-titulo-sessao")
        self.lbl_vocal_title.setProperty("margin-bottom", "md")
        layout_card_audio.addWidget(self.lbl_vocal_title)
        
        self.frame_interno_audio = QFrame()
        self.frame_interno_audio.setProperty("class", "container-borda-cinza-fill")
        self.layout_interno_audio = QVBoxLayout(self.frame_interno_audio)
        self.layout_interno_audio.setContentsMargins(10, 10, 10, 10)
        self.layout_interno_audio.setSpacing(StyleManager.SPACING_SM)
        
        self.lbl_audio_placeholder = QLabel("<i>Aguardando localização geográfica da fotografia...</i>")
        self.lbl_audio_placeholder.setAlignment(Qt.AlignCenter)
        self.lbl_audio_placeholder.setWordWrap(True)
        self.layout_interno_audio.addWidget(self.lbl_audio_placeholder)
        
        layout_card_audio.addWidget(self.frame_interno_audio)
        self.layout_direito_inferior.addWidget(self.card_audio)
        self.layout_direito_inferior.addStretch()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Pronto para uso (Local)")

    def _aplicar_estilo(self):
        """Configura o estilo visual da janela via Sovereign Style (v0.6.3 / v0.8.0)."""
        # Agora o estilo é 100% centralizado no StyleManager.py. 
        # Mantemos esta chamada apenas para retrocompatibilidade de fluxo.
        pass

    def changeEvent(self, event):
        """Blindagem Atômica de Cores (v0.6.8 / v0.6.9 - Anti-Recursion): 
        Rechaça mudanças de paleta impostas pelo Windows Dark Mode com trava de segurança."""
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.PaletteChange:
            if self._bloqueio_palette:
                return
                
            self._bloqueio_palette = True
            try:
                # Sincronia de Title Bar e Ícone v0.6.6 (Soberania Off-White)
                # O corpo da janela ignora a mudança de paleta para evitar o bug de inversão.
                dark_mode = StyleManager.detect_dark_mode()
                
                print(f"[STYLE] Watchdog v0.6.6: Forçando Soberania Off-White. DarkMode: {dark_mode}")
                app = QApplication.instance()
                if app:
                    StyleManager.apply_theme(app, dark_mode=dark_mode)
                
                # Sincronia de Title Bar e Ícone
                StyleManager.setup_window_theme(self)
                StyleManager.set_app_icon(self, dark_mode=dark_mode)
                
            finally:
                self._bloqueio_palette = False
                
        super().changeEvent(event)

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
        
        # 1. Resetar Interface PRIMEIRO (v0.6.6)
        # Preserva a foto do usuário e as coordenadas atuais antes da nova cascata
        self._resetar_interface(manter_imagem=True)
        
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
        # Estilo Biológico Centralizado (v0.8.1/v0.6.6)
        self.input_especie.setProperty("class", "sci-name-input")
        self.input_especie.style().unpolish(self.input_especie)
        self.input_especie.style().polish(self.input_especie)

        self.dados_identificacao_atual["nome_cientifico"] = sci_formatted
        self.especie_em_processamento = sci_formatted # Persistência Atômica v0.6.8
        self.lbl_nome_comum.setText("")
        self.lbl_nome_comum.setVisible(True)
        self.lbl_descricao.setText("<i>Identificado pelo usuário.</i>")
        self.lbl_descricao.setVisible(True)
        
        self.input_especie.setText(sci_formatted) # Garante o texto no widget
        
        self._iniciar_busca_imagem(sci_formatted)
        
        # Sincronizar localização atual com Orchestrator (v0.4.8)
        self.orchestrator.update_location(self.lat_atual, self.lon_atual)
        
        # O Orchestrator assume a cascata linear 1->2->3->4->5 a partir daqui (v0.4.6)
        self.orchestrator.start_cascade_from_step2(sci_formatted)
        
        self.btn_wiki.setVisible(True)
        self.btn_google.setVisible(True)
        self.btn_ebird.setVisible(True)

        # LOGGING DE SESSÃO: ETAPA 1 (Removido aqui, agora centralizado no Orchestrator v0.4.6)
        pass

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
            self.card_geo.setVisible(True)
            self.lbl_geo_details.setText(f"Lat: {lat:.4f}, Lon: {lon:.4f} (Processando...)")
            self.lbl_geo_details.setProperty("class", "container-borda-cinza-fill")
            self.lbl_geo_details.style().unpolish(self.lbl_geo_details)
            self.lbl_geo_details.style().polish(self.lbl_geo_details)
            
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
                 self.card_geo.setVisible(True)
                 self.lbl_geo_details.setText("Localização não detectada na imagem.")
                 self.lbl_geo_details.setProperty("class", "container-borda-cinza-fill")
                 self.lbl_geo_details.style().unpolish(self.lbl_geo_details)
                 self.lbl_geo_details.style().polish(self.lbl_geo_details)
             
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
                self.lbl_geo_details.setProperty("class", "container-borda-cinza-fill")
                self.lbl_geo_details.style().unpolish(self.lbl_geo_details)
                self.lbl_geo_details.style().polish(self.lbl_geo_details)
                
                self._atualizar_geo_info(lat, lon)
                
                # Salva a localização manual para ser usada ao recarregar imagem ou atualizar mapa
                self.ultima_localizacao_manual = (lat, lon)
                
                # ATUALIZAÇÃO INTELIGENTE (v0.6.8): 
                # Blindagem contra volatilidade do dicionário de dados.
                sci_name = self.dados_identificacao_atual.get("nome_cientifico") or self.especie_em_processamento
                print(f"[DEBUG GPS] Nome científico detectado (Estado/Flag): '{sci_name}'")
                
                if sci_name and sci_name != "Identificação Inconclusiva" and "..." not in sci_name:
                    print(f"[UI] Espécie '{sci_name}' já identificada. Refinando apenas dados regionais via _atualizar_geo_info...")
                    self.status_bar.showMessage("Localização atualizada. Refinando dados regionais...")
                else:
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

        self.lbl_nome_popular.setText("<b>Nome Popular:</b> <i>Buscando...</i>")
        self.lbl_nome_popular.setVisible(True)
        self.lbl_nome_ingles.setText("<b>Nome em Inglês:</b> <i>Buscando...</i>")
        self.lbl_nome_ingles.setVisible(True)
        self.lbl_confianca.setText("<b>IA Local:</b> Analisando pixels...")
        self.lbl_confianca.setVisible(True)
        self.txt_descricao.clear() # Limpa descrição rica
        
        # Etimologia agora em card separado (v0.8.2)
        self.lbl_etimologia_texto.setText("Carregando...")
        self.card_etimologia.setVisible(False)
        
        self.input_especie.clear() 
        self.input_especie.setProperty("class", "sci-name-input")
        self.input_especie.style().unpolish(self.input_especie)
        self.input_especie.style().polish(self.input_especie)
        
        self.card_ref.set_placeholder("aguardando identificação da espécie...")
        self.status_bar.showMessage("Iniciando IA Local...")
        
        self.card_user.setAcceptDrops(False) # Bloqueia novos drops durante processamento
        
        try:
            # Sincronizar localização atual com Orchestrator ANTES de iniciar (v0.4.8)
            self.orchestrator.update_location(self.lat_atual, self.lon_atual)
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
        pass
        self.dados_identificacao_atual = dados
        
        nc = dados.get("nome_comum", "-")
        raw_sci = dados.get("nome_cientifico", "")
        
        import re
        sci_clean = re.sub(r"[(\[].*?[)\]]", "", raw_sci)
        parts = sci_clean.strip().split()
        if len(parts) >= 2:
            sci = f"{parts[0]} {parts[1]}"
        else:
            sci = sci_clean.strip()
            
        desc = dados.get("descricao", "")
        conf = dados.get("confianca", 0.0)
        status_msg = dados.get("status_msg", "")
        self.lbl_confianca.setVisible(True)
        
        if "Inconclusiva" not in status_msg and "Baixa" not in status_msg and sci:
            sci_clean = re.sub(r"[(\[].*?[)\]]", "", sci).strip()
            parts = sci_clean.split()
            if len(parts) >= 2:
                # Regra Biológica: Gênero epíteto (v0.8.1)
                sci_formatted = f"{parts[0].capitalize()} {parts[1].lower()}"
            else:
                sci_formatted = sci_clean.capitalize()

            self.input_especie.setText(sci_formatted)
            # A classe 'sci-name-input' no StyleManager garante o itálico
            self.input_especie.style().unpolish(self.input_especie)
            self.input_especie.style().polish(self.input_especie)
            
            if self.dados_identificacao_atual:
                self.dados_identificacao_atual["nome_cientifico"] = sci_formatted
        else:
             self.input_especie.clear()
             self.input_especie.setProperty("class", "container-borda-cinza")
             self.input_especie.style().unpolish(self.input_especie)
             self.input_especie.style().polish(self.input_especie)
        
        self.lbl_confianca.setText(f"<i>Identificado com iNaturalist Vision (Prob {conf*100:.1f}%)</i>")
        self.lbl_confianca.setVisible(True)
        
        if status_msg == "Baixa confiança":
            self.lbl_confianca.setText(f"<b>Identificação com Baixa Confiança:</b> {conf*100:.1f}%")
            self.lbl_confianca.setProperty("class", "lbl-confianca-baixa")
            self.lbl_confianca.style().unpolish(self.lbl_confianca)
            self.lbl_confianca.style().polish(self.lbl_confianca)
            self.status_bar.showMessage("Identificação inconclusiva.")
            
            self.btn_wiki.setVisible(False)
            self.btn_google.setVisible(False)
            self.btn_ebird.setVisible(False)
            
            self.card_ref.set_placeholder("Busca visual suspensa")
            self.card_ref.set_pixmap(None)
            self.card_ref.set_overlay_text(None)
            
            self.txt_descricao.setPlainText("Não foi possível identificar com segurança. Use o Google Lens ou a busca manual.")
            self.btn_google_lens.setEnabled(True)
        else:
            self.lbl_confianca.setProperty("class", "lbl-confianca-alta")
            self.lbl_confianca.style().unpolish(self.lbl_confianca)
            self.lbl_confianca.style().polish(self.lbl_confianca)
            self.status_bar.showMessage("Identificação concluída.")
            
            self.btn_wiki.setVisible(True)
            self.btn_google.setVisible(True)
            self.btn_ebird.setVisible(True)
            self.btn_google_lens.setEnabled(False)
            
            if sci:
                self._iniciar_busca_imagem(sci)
                
            # LOGGING DE SESSÃO: ETAPA 1 (Removido aqui, agora centralizado no Orchestrator v0.4.6)
            pass
        
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
        self.card_audio.setVisible(True)
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


        # Adiciona cards de auditoria (v0.8.2 - Dentro do Frame Interno)
        for i, audio in enumerate(resultados):
            card = VocalAuditCard(
                audio_data=audio,
                ranking_index=i+1,
                on_click=self._abrir_detalhes_vocal,
                parent=self.frame_interno_audio
            )
            self.layout_interno_audio.addWidget(card)
            
            # Guardar referencia para limpeza futura
            if not hasattr(self, 'active_audio_players'):
                self.active_audio_players = []
            self.active_audio_players.append(card)
            
    def _abrir_detalhes_vocal(self, audio_data):
        """Abre a janela de auditoria detalhada ao clicar no ícone vocal (v0.8.2)."""
        print(f"[UI] Chamada para abrir detalhes do áudio: {audio_data.get('id')} em {audio_data.get('audit_geo')}")
        dialog = VocalDetailDialog(audio_data, self)
        print(f"[UI] Executando modal VocalDetailDialog para o ID {audio_data.get('id')}...")
        dialog.exec()
        print(f"[UI] Janela de detalhes {audio_data.get('id')} fechada.")
            
    def _plotar_pins_audio(self, resultados):
        """Extrai coordenadas das vocalizações e plota no mapa (v0.4.3)."""
        if not resultados or not self.map_principal:
            return
            
        audio_markers = []
        for i, audio in enumerate(resultados):
            if audio.get('lat') is not None and audio.get('lon') is not None:
                tipo = audio.get('tipo_canto')
                ranking = i + 1
                title = f"#{ranking} {tipo} - {audio.get('autor', 'Gravador')}" if tipo else f"#{ranking} Gravação de {audio.get('autor', 'Autor')}"
                audio_markers.append({
                     'lat': audio['lat'],
                     'lon': audio['lon'],
                     'title': title,
                     'id': audio.get('id', audio.get('url', '')),
                     'ranking': ranking,
                     'tipo_canto': tipo,
                     'autor': audio.get('autor'),
                     'distancia_km': audio.get('distancia_km')
                })
        
        if audio_markers:
            print(f"[UI] Plotando {len(audio_markers)} pins musicais no mapa.")
            sci = self._obter_sciname_atual()
            
            # Localização de centralização (v0.8.1: Fallback se GPS ausente)
            lat = self.lat_atual
            lon = self.lon_atual
            add_main_marker = True
            
            if lat is None or lon is None:
                lat = -15.7801
                lon = -47.9292
                add_main_marker = False
                current_zoom = 4
            else:
                current_zoom = 6
                
            self.map_principal.update_map(lat, lon, zoom=current_zoom, add_marker=add_main_marker, scientific_name=sci, audio_markers=audio_markers)

    def _registrar_audio_session(self, audio):
        if not audio or not hasattr(self, 'session_logger'):
             return
             
        dados_etapa_4 = {
            "audio_url": audio.get('url', ''),
            "audio_id": audio.get('id', ''),
            "audio_autor": audio.get('autor', 'Desconhecido'),
            "audio_licenca": audio.get('licenca', 'CC BY-NC'),
            "audio_tipo": audio.get('tipo_canto', ''),
            "audio_qualidade": audio.get('q', ''),
            "audio_lat": audio.get('lat'),
            "audio_lon": audio.get('lon'),
            "audio_distancia_km": audio.get('distancia'),
            "audio_link_web": audio.get('link_web', ''),
            "audio_source": audio.get('fonte', 'Xeno-canto'),
            "audio_data_gravacao": audio.get('data', 'Desconhecida'),
            "audio_comentarios": audio.get('comentarios', '')
        }
        self.session_logger.atualizar_ultimo_registro(dados_etapa_4)

    def _ao_erro_audio(self):
        self.lbl_audio_placeholder.setText("<i>Nenhuma gravação encontrada.</i>")
        self.lbl_audio_placeholder.setVisible(True)

    def _atualizar_geo_info(self, lat, lon):
        """Notifica o Orchestrator para iniciar worker de detalhes geo."""
        if not hasattr(self, 'lbl_geo_details'):
             return

        self.lbl_geo_details.setText("Analisando local e bioma...")
        self.lbl_geo_details.setVisible(True)
        
        # Limpar áudios anteriores para nova busca geo-sincronizada (v0.4.3)
        self._limpar_painel_audio()

        # CONEXÃO COM O CÉREBRO (v0.8.2)
        # Sincroniza as coordenadas no Orchestrator usando o fluxo centralizado de reprocessamento
        if self.orchestrator:
             self.orchestrator.reprocessar_localizacao(lat, lon)

    def _ao_clicar_pin_audio(self, audio_id):
        """Lida com o clique no pin de áudio do mapa, garantindo paridade total com o card (v0.8.2)."""
        if not hasattr(self, 'active_audio_players'):
            print("[MAPA] ERRO: Lista de players ativos não inicializada.")
            return
            
        print(f"\n[DIAGNÓSTICO MAPA] Clique interceptado. ID Alvo: {audio_id}")
        card_encontrado = False
        
        for player in self.active_audio_players:
            # player é um VocalAuditCard (v0.7.1)
            if hasattr(player, 'audio_data'):
                # Padronização agressiva de ID para comparação (Xeno ID, iNat ID ou URL)
                p_id = str(player.audio_data.get('id', '')).strip()
                t_id = str(audio_id).strip()
                
                if p_id == t_id:
                    print(f"[DIAGNÓSTICO MAPA] Card localizado: {p_id}. Disparando callback do card.")
                    card_encontrado = True
                    
                    # 1. Execução Direta (Solicitação do Usuário v0.8.2)
                    # Em vez de simular clique no botão, chamamos o callback original com os dados do card
                    if hasattr(player, 'on_click_callback') and player.on_click_callback:
                        # Simulação visual de clique (Feedback para o usuário)
                        # O animateClick() já emite o sinal 'clicked' de forma assíncrona após 100ms,
                        # o que resolve o conflito com o WebEngine e evita a abertura dupla (v0.8.2).
                        if hasattr(player, 'btn_icon'):
                            player.btn_icon.animateClick()
                    else:
                        print("[DIAGNÓSTICO MAPA] AVISO: Card não possui on_click_callback válido.")
                    
                    # 2. Feedback Visual e Scroll
                    if hasattr(player, 'highlight'):
                        player.highlight()
                    self.scroll_area.ensureWidgetVisible(player)
                    break
        
        if not card_encontrado:
             print(f"[DIAGNÓSTICO MAPA] FALHA: Nenhum card encontrado com ID {audio_id} na lista atual ({len(self.active_audio_players)} cards).")
        
    def _ao_concluir_geo_analise(self, details):
        self.last_geo_data = details
        self.lat_atual = details.get('lat')
        self.lon_atual = details.get('lon')
        
        # 1. Atualização Visual Imediata (v0.4.33)
        if hasattr(self, 'lbl_geo_details'):
            lat = details.get('lat')
            lon = details.get('lon')
            lat_str = f"{lat:.5f}" if isinstance(lat, (float, int)) else "?"
            lon_str = f"{lon:.5f}" if isinstance(lon, (float, int)) else "?"

            pais = details.get('pais', '-')
            bioma = details.get('bioma', '-')
            
            if pais.lower() not in ["brazil", "brasil"]:
                bioma = "Informação Não Disponível (Registro Internacional)"

            texto = f"""
            <b>Coordenadas:</b> Lat {lat_str}, Long {lon_str}<br>
            <b>País:</b> {pais}<br>
            <b>Estado:</b> {details.get('estado', '-')}<br>
            <b>Município:</b> {details.get('municipio', '-')}<br>
            <b>Bioma:</b> {bioma}<br>
            """
                
            self.lbl_geo_details.setText(texto)
            self.lbl_geo_details.setVisible(True)
            self.card_geo.setVisible(True)
            self.lbl_geo_details.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # 2. Registro em Segundo Plano (v0.4.33)
        self._registrar_dados_geo_iucn()
        
    def _ao_concluir_iucn(self, results):
        from modules.step3_geography.conservation_worker import NationalConservationWorker
        
        raw_status = results.get("iucn_status", "Não Avaliado")
        # Traduzir para extenso conforme solicitação
        results["iucn_status"] = NationalConservationWorker.traduzir_iucn(raw_status)
        
        self.last_iucn_data = results
        self._registrar_dados_geo_iucn()
        
    def _ao_concluir_conservacao_nacional(self, results):
        self.last_conservation_data = results
        print(f"[UI] Dados de conservação nacional recebidos: {results}")
        
        # Atualizar visualmente o card geográfico com a nova soberania de dados
        if hasattr(self, 'lbl_geo_details') and hasattr(self, 'last_geo_data'):
            geo = self.last_geo_data
            lat = geo.get('lat', 0)
            lon = geo.get('lon', 0)
            
            pais = geo.get('pais', '-')
            bioma = geo.get('bioma', '-')
            
            if pais.lower() not in ["brazil", "brasil"]:
                bioma = "Informação Não Disponível (Registro Internacional)"
            
            # Lógica de Endemismo Permanente (v0.8.2)
            endemismo_val = results.get("endemismo")
            if endemismo_val == "Sim":
                endemismo_texto = '<b style="color: #059669;">Sim (✨)</b>'
            elif endemismo_val == "Não":
                endemismo_texto = "Não"
            else:
                endemismo_texto = "<i>Sem informação</i>"
            
            status_endemismo = f"<br><b>Endêmica do Brasil:</b> {endemismo_texto}"
            
            # Status ICMBio e CITES
            status_br_val = results.get('status_icmbio', '-')
            status_br = f"<br><b>ICMBio:</b> {status_br_val}"
            status_cites = f"<br><b>CITES:</b> {results.get('status_cites', '-')}"
            
            # Mensagem de Distribuição
            msg_dist = results.get("msg_distribuicao", "")
            if "Fora" in msg_dist:
                msg_dist = f'<br><b style="color: #dc2626;">⚠ Fora da distribuição conhecida</b>'
            else:
                msg_dist = ""

            texto_base = f"""
            <b>Coordenadas:</b> {lat:.5f}, {lon:.5f}<br>
            <b>País:</b> {pais}<br>
            <b>Estado:</b> {geo.get('estado', '-')}<br>
            <b>Município:</b> {geo.get('municipio', '-')}<br>
            <b>Bioma:</b> {bioma}
            """
            self.lbl_geo_details.setText(texto_base)

            # Atualizar Novo Card de Status de Conservação (v0.8.2)
            texto_cons = f"""
            <b>IUCN:</b> {self.last_iucn_data.get('iucn_status', '-')}{status_br}{status_cites}{status_endemismo}{msg_dist}
            """
            self.lbl_status_conservacao.setText(texto_cons)
            self.lbl_status_conservacao.setVisible(True)
            self.card_conservacao.setVisible(True)

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
            
            # Atualizar Card de Identificação (Nomes) (v0.8.2.3 - Higienização de Fontes)
            # Nome Popular é gerido exclusivamente pelo WikiAves na Etapa 2.
            # Aqui focamos apenas no Nome em Inglês (iNaturalist).
            
            nome_ingles = results.get("nome_ingles", "Unknown")
            # v0.8.2: O iNaturalist agora é apenas um fallback silencioso na caderneta.
            # A UI é soberana ao WikiAves. Só atualizamos se o label estiver vazio ou com o placeholder.
            texto_atual = self.lbl_nome_ingles.text()
            if "Buscando" in texto_atual or not texto_atual:
                if nome_ingles and nome_ingles not in ["Unknown", "Desconhecido"]:
                    self.lbl_nome_ingles.setText(f"<b>Nome em Inglês:</b> {nome_ingles}")
                    self.lbl_nome_ingles.setVisible(True)

            print("[UI] Etapa 5 (eBird/Clements) integrada ao SessionLogger.")
            
            # Atualizar Card de Taxonomia (v0.8.2)
            sci_name = self.dados_identificacao_atual.get("nome_cientifico", "") or self.especie_em_processamento
            genero = sci_name.split()[0] if sci_name else "-"
            
            taxo_html = f"""
            <b>Classe:</b> {results.get("classe", "Aves")}<br>
            <b>Ordem:</b> {results.get("ordem", "-")}<br>
            <b>Família:</b> {results.get("familia", "-")}<br>
            <b>Gênero:</b> <i>{genero}</i>
            """
            self.lbl_taxo_details.setText(taxo_html)
            self.lbl_taxo_details.setVisible(True)
            self.card_taxonomia.setVisible(True)
            
            print("[EXIF] Módulo placeholder preparado para receber dados (Etapa Final).")

    def _registrar_dados_geo_iucn(self):
        geo = getattr(self, 'last_geo_data', {})
        iucn = getattr(self, 'last_iucn_data', {})
        
        if not geo and not iucn: return
        
        # GBIF link generation removed from main thread (v0.4.33)
        link_gbif = ""

        dados = {
            "lat": self.lat_atual,
            "lon": self.lon_atual,
            "pais": geo.get("pais", "-"),
            "estado": geo.get("estado", "-"),
            "municipio": geo.get("municipio", "-"),
            "bioma": geo.get("bioma", "-"),
            "iucn_status": iucn.get("iucn_status", "Não Avaliado"),
            "status_icmbio": getattr(self, "last_conservation_data", {}).get("status_icmbio", "-"),
            "endemismo": getattr(self, "last_conservation_data", {}).get("endemismo", "Não"),
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

    def _limpar_painel_audio(self):
        """Para e remove todos os players de áudio da interface (v0.5.1)."""
        if hasattr(self, 'active_audio_players'):
            for player in self.active_audio_players:
                try:
                    # Tenta parar e remover explicitamente do layout
                    if hasattr(player, 'stop'): player.stop()
                    player.setParent(None)
                    player.deleteLater()
                except: pass
            self.active_audio_players = []
        
        # Limpeza agressiva do frame interno (v0.8.2)
        if hasattr(self, 'layout_interno_audio') and self.layout_interno_audio:
            # Remove qualquer widget que não seja a label placeholder
            for i in reversed(range(self.layout_interno_audio.count())):
                item = self.layout_interno_audio.itemAt(i)
                widget = item.widget()
                if widget and widget != self.lbl_audio_placeholder:
                    widget.setParent(None)
                    widget.deleteLater()
        
        if hasattr(self, 'lbl_audio_placeholder'):
            self.lbl_audio_placeholder.setText("<i>Aguardando localização geográfica da fotografia...</i>")
            self.lbl_audio_placeholder.setVisible(True)

    def _resetar_interface(self, manter_imagem=False):
        # 1. Parar Orchestrator e Workers (v0.5.1)
        if hasattr(self, 'orchestrator'):
            print("[UI] Solicitando reset total ao Orchestrator...")
            self.orchestrator.reset()

        if hasattr(self, 'session_logger'):
            print("[UI] Resetando SessionLogger...")
            self.session_logger.reset()
            
        self._limpar_painel_audio()
        
        # Invalida estado anterior (v0.6.2: condicional para busca manual)
        if not manter_imagem:
            self.caminho_imagem_atual = None
            self.lat_atual = None
            self.lon_atual = None
            self.card_user.set_image_path(None)
            self.card_user.set_placeholder("Arraste e solte uma foto aqui\n\nou clique para selecionar")

        self.dados_identificacao_atual = {}
        
        self.card_ref.set_image_path(None)
        self.card_ref.set_placeholder("Aguardando a identificação da ave.")
        self.card_ref.set_overlay_text(None)
        
        # 3. Reset de Botões e Inputs
        self.btn_fonte.setEnabled(False)
        self.btn_google_lens.setEnabled(False)
        self.btn_wiki.setVisible(False)
        self.btn_google.setVisible(False)
        self.btn_ebird.setVisible(False)
        
        self.input_especie.clear()
        self.input_especie.setProperty("class", "container-borda-cinza")
        self.input_especie.style().unpolish(self.input_especie)
        self.input_especie.style().polish(self.input_especie)
        
        # 4. Reset de Labels de Dados
        self.lbl_nome_popular.setText("<b>Nome Popular:</b> <i>Aguardando identificação...</i>")
        self.lbl_nome_popular.setVisible(True)
        self.lbl_nome_ingles.setText("<b>Nome em Inglês:</b> <i>Aguardando identificação...</i>")
        self.lbl_nome_ingles.setVisible(True)
        
        self.lbl_confianca.setText("")
        self.lbl_confianca.setVisible(False)
        self.lbl_confianca.setProperty("class", "lbl-titulo-sessao") # Remove classes de cor alta/baixa
        self.lbl_confianca.style().unpolish(self.lbl_confianca)
        self.lbl_confianca.style().polish(self.lbl_confianca)
        
        self.lbl_geo_details.setText("Aguardando localização...")
        self.lbl_geo_details.setVisible(True)
        
        self.lbl_status_conservacao.setText("<i>Aguardando identificação da ave...</i>")
        self.lbl_status_conservacao.setVisible(True)
        self.card_conservacao.setVisible(True)
        
        # Reset de buffers de conservação (v0.8.2)
        self.last_iucn_data = {}
        self.last_geo_data = {}
        self.last_conservation_data = {}
        
        # 5. Reset de Campos de Texto
        self.txt_descricao.clear()
        self.lbl_etimologia_texto.setText("Carregando...")
        
        self.lbl_audio_placeholder.setText("<i>Aguardando localização geográfica da fotografia...</i>")
        self.lbl_audio_placeholder.setVisible(True)
        
        # 6. Reset de Painéis e Mapas
        self.card_id.setVisible(True) # Card ID sempre visível
        self.card_etimologia.setVisible(True) 
        self.card_geo.setVisible(True)
        self.card_audio.setVisible(True)
        self.card_taxonomia.setVisible(True)
        self.lbl_taxo_details.setText("<i>Aguardando identificação da ave...</i>")
        self.lbl_taxo_details.setVisible(True)
        
        if self.map_principal:
             self.map_principal.show_placeholder_message("Aguardando dados de Localização")
             self.map_principal.alert_frame.hide() # Esconde alerta se estiver visivel
             
        self.status_bar.showMessage("Pronto para nova identificação")

    def closeEvent(self, event):
        """Sobrescreve o fechamento para limpar a caderneta de campo temporária."""
        if hasattr(self, 'session_logger'):
            # Flush final antes de fechar (Safety v0.4.4)
            self.session_logger.flush()
            self.session_logger.limpar_sessao()
        event.accept()
