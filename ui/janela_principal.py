#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#
#  Este programa é um software livre: você pode redistribuí-lo e/ou 
#  modificá-lo sob os termos da Licença Pública Geral GNU conforme 
#  publicada pela Free Software Foundation, tanto a versão 3 da 
#  Licença, como (a seu critério) qualquer versão posterior.
#
#  Este programa é distribuído na esperança de que possa ser útil, 
#  mas SEM NENHUMA GARANTIA; sem uma garantia implícita de 
#  ADEQUAÇÃO A QUALQUER MERCADO OU APLICAÇÃO EM PARTICULAR. 
#  Veja a Licença Pública Geral GNU para mais detalhes.
#
#  Você deve ter recebido uma cópia da Licença Pública Geral GNU 
#  junto com este programa. Se não, veja <https://www.gnu.org/licenses/>.

# ADVERTÊNCIA: Proibido adicionar barras de menu ou ferramentas tradicionais conforme RULES v1.1.
import sys
import os
import json
import logging
import traceback
import urllib.parse
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFileDialog,
                             QScrollArea, QFrame, QGraphicsDropShadowEffect,
                             QMessageBox, QTextEdit, QLineEdit, QGroupBox, QGridLayout,
                             QStatusBar, QSizePolicy, QCheckBox, QDialog)
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
from ui.dialogs.exif_config_dialog import ExifConfigDialog
from modules.step6_persistence.exif_manager import EXIFManager
from ui.widgets.map_widget import MapWidget
from ui.custom_widgets import ImageCardWidget, AudioPlayerWidget, VocalAuditCard
from ui.dialogs.location_dialog import LocationDialog
from ui.dialogs.vocal_detail_dialog import VocalDetailDialog
from ui.dialogs.manual_dialog import ManualUsuarioDialog
from modules.step3_geography.geo_analyst import GeoAnalyst
from core.session_logger import SessionLogger
from modules.step3_geography.iucn_worker import IUCNWorker
from modules.step5_taxonomy.ebird_worker import EBirdWorker

# GeoWorker migrado para o Orchestrator v0.4.2

class JanelaPrincipal(QMainWindow):
    """
    Controlador Principal da Interface Gráfica (View).
    
    Arquitetura:
    - Segue o padrão Feature-Based: a UI não processa dados, apenas emite sinais
      para o Orchestrator e reage aos resultados retornados.
    - Soberania de Estilo: Utiliza o StyleManager para garantir que componentes
      Chromium (Mapas/Players) não quebrem o tema visual do Windows.
    - Persistência de Sessão: Integrada ao SessionLogger para auditoria em tempo real.
    """
    PLACEHOLDER_TEXT = "Aguardando identificação...."

    def __init__(self, nome_icone_janela="logo_ave.svg", modo_inicial="online", ai_status="READY", imagem_inicial=None):
        super().__init__()
        
        # Trava de Estilo (v0.6.9): Impede recursão infinita no changeEvent
        # Deve ser inicializada ANTES de setWindowTitle/resize para evitar AttributeError
        self._bloqueio_palette = False
        
        self.nome_icone_janela = nome_icone_janela
        self.ai_status = ai_status
        
        # Logging de Sessão Temporária (v0.3.15)
        self.session_logger = SessionLogger()
        
        # O Cérebro do Aplicativo (Orchestrator via Feature-Based Architecture)
        # O Orchestrator gerencia a execução assíncrona para não travar a interface.
        from core.orchestrator import Orchestrator
        self.orchestrator = Orchestrator(self.session_logger, parent=self)
        
        # Conexões de Sinais (Pipeline em Cascata)
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
        
        # Inicialização da UI (v1.0.1): Deve ocorrer ANTES do resize/show
        self._configurar_ui()
        
        self.resize(1100, 700)
        
        self.caminho_imagem_atual = None
        self.dados_identificacao_atual = {}
        self.lat_atual = None
        self.lon_atual = None
        
        # Flag de Persistência Atômica (v0.6.8)
        # Mantém o nome científico mesmo durante resets de interface
        self.especie_em_processamento = None 
        
        # Dados de Conservação (v1.6.5)
        self.last_iucn_data = {}
        self.last_conservation_data = {}
        
        # Flags de Estado
        self.caminho_imagem_atual = None
        self._aplicar_estilo()
        
        # Reforço de Title Bar Dark (v0.7.2)
        StyleManager.setup_window_theme(self)
        
        # Suporte a Menu de Contexto (v1.0): Carrega imagem inicial se houver
        if imagem_inicial and os.path.exists(imagem_inicial):
            # Usamos timer para garantir que a UI está pronta antes do processamento pesado
            QTimer.singleShot(500, lambda: self._carregar_imagem(imagem_inicial))

    def _obter_caminho_asset(self, nome_arquivo):
        if getattr(sys, 'frozen', False):
            # No executável, os assets estão na subpasta 'assets' dentro de _MEIPASS
            base_path = Path(sys._MEIPASS) / 'assets'
        else:
            base_path = Path(__file__).parent.parent / 'assets'
        return str(base_path / nome_arquivo)

    def _format_nome_ave(self, prefixo, valor, is_placeholder=False):
        """Formata o prefixo e o valor com o estilo exato do Nome Científico ou Placeholder."""
        cor_valor = "#9CA3AF" if is_placeholder else "#1F2937"
        span_prefixo = f"<span style=\"font-family: 'Segoe UI'; font-weight: bold; color: #4B5563; font-size: 11px;\">{prefixo}</span>"
        span_valor = f"<span style=\"font-family: 'Segoe UI'; font-style: italic; font-weight: 500; color: {cor_valor}; font-size: 13px;\">{valor}</span>"
        return f"{span_prefixo}&nbsp;&nbsp;{span_valor}"

    def _set_placeholder_style(self, label, active=True):
        """Adiciona ou remove a classe de placeholder de uma label."""
        if not label: return
        
        classe_atual = label.property("class") or ""
        if active:
            if "lbl-placeholder" not in classe_atual:
                label.setProperty("class", f"{classe_atual} lbl-placeholder".strip())
        else:
            if "lbl-placeholder" in classe_atual:
                label.setProperty("class", classe_atual.replace("lbl-placeholder", "").strip())
        
        label.style().unpolish(label)
        label.style().polish(label)


    def _iniciar_busca_imagem(self, nome_cientifico):
        # Reset visual
        self.card_ref.set_placeholder(self.PLACEHOLDER_TEXT)
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
        self.txt_etimologia.setPlaceholderText(self.PLACEHOLDER_TEXT)
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
        logging.info(f"Dados biológicos recebidos via Orchestrator (WikiAves). Especial: {dados.get('nome_comum')}")
        
        # Mapeamento do BuscadorBlindado (Agora com chaves nativas corretas - v0.3.17)
        etimologia_texto = dados.get("etimologia", "")
        caracteristicas = dados.get("caracteristicas", "")
        
        # LOGGING DE SESSÃO: ETAPA 2 (v1.6.3 / v0.8.8)
        dados_etapa_2 = {
            "nome_cientifico": dados.get("original_scientific_name", self.dados_identificacao_atual.get("nome_cientifico", "")),
            "link_origem": dados.get("link_origem", ""),
            "link_ebird": dados.get("link_ebird", ""), 
            "descricao": caracteristicas,
            "nome_comum": dados.get("nome_comum", ""),
            "nome_ingles": dados.get("nome_ingles", ""),
            "etimologia": etimologia_texto,
            "ordem": dados.get("ordem", "Desconhecida"),
            "familia": dados.get("familia", "Desconhecida"),
            "latitude": self.lat_atual,
            "longitude": self.lon_atual
        }
        
        if hasattr(self, 'session_logger'):
            self.session_logger.atualizar_ultimo_registro(dados_etapa_2)

        # Persistência de Estado (v0.6.7)
        # Garante que dados retornados populem o dicionário de identificação atual
        # para que o gravador de EXIF encontre todas as informações no final do ciclo.
        sci_persist = dados.get("original_scientific_name", self.dados_identificacao_atual.get("nome_cientifico", ""))
        
        if not self.dados_identificacao_atual:
            self.dados_identificacao_atual = {}
            
        self.dados_identificacao_atual.update(dados_etapa_2)
        self.dados_identificacao_atual["nome_cientifico"] = sci_persist
        
        # UI Update: Nome Comum (v0.8.2)
        nc = dados.get("nome_comum", "")
        if nc and nc.lower() not in ["nome comum não encontrado", "não encontrado"]:
            self.lbl_nome_comum.setText(self._format_nome_ave("Nome Comum:", nc))
        else:
            self.lbl_nome_comum.setText(self._format_nome_ave("Nome Comum:", "Não encontrado"))

        # UI Update: Nome em Inglês (v0.8.5 - Agora via WikiAves)
        ni = dados.get("nome_ingles", "")
        if ni and ni.lower() not in ["desconhecido", "unknown"]:
            self.lbl_nome_ingles.setText(self._format_nome_ave("Nome em Inglês:", ni))
        else:
            if nc:
                self.lbl_nome_ingles.setText(self._format_nome_ave("Nome em Inglês:", "Desconhecido"))

        # Atualiza Campo Etimologia
        # Atualiza Campo Etimologia
        if etimologia_texto and etimologia_texto != "Não encontrado":
            # Aplicação do padrão estético visual (line-height 150%) para o texto via HTML
            html_etimologia = f'<div style="line-height: 150%;">{etimologia_texto}</div>'
            self.txt_etimologia.setHtml(html_etimologia)
        elif etimologia_texto == "Não encontrado":
            self.txt_etimologia.setPlaceholderText("Etimologia não disponível.")
            self.txt_etimologia.clear()

        # Atualiza Campo Descrição (Rodapé)
        if caracteristicas and caracteristicas != "Não encontrado":
            self.txt_descricao.setPlainText(caracteristicas)
            self.txt_descricao.setVisible(True)
            self.lbl_titulo_etimologia.setVisible(True)
            self.txt_etimologia.setVisible(True)
            
        # 🔹 Atualização de Taxonomia (WikiAves v1.6.2)
        # Se o WikiAves retornar taxonomia, já populamos o card para evitar sensação de "vazio"
        ordem = dados.get("ordem")
        familia = dados.get("familia")
        if (ordem and ordem != "Desconhecida") or (familia and familia != "Desconhecida"):
            logging.debug(f"Taxonomia recebida do WikiAves: {ordem} / {familia}")
            self._atualizar_card_taxonomia(ordem=ordem, familia=familia)
            
        # Ativa o botão de gravação (v0.8.9)
        # Se chegamos aqui, temos dados biológicos mínimos para persistir.
        if hasattr(self, 'btn_gravar_exif'):
            self.btn_gravar_exif.setEnabled(True)
            self.btn_gravar_exif.setVisible(True)
            
        self.frame_etimologia.setVisible(False)

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

            # Fallback: Se não tem coords, usa Centro do Brasil apenas para mostrar a distribution
            if lat is None or lon is None:
                lat = -15.7801
                lon = -47.9292
                add_marker = False
                zoom_level = 4
                logging.debug("Sem GPS: Usando fallback (Centro BR) para exibir mapa de distribuição.")

            logging.debug(f"Atualizando Widget de Mapa... (GBIF: {sciname}) [Lat: {lat}, Lon: {lon}]")
            try:
                self.map_principal.update_map(lat, lon, zoom=zoom_level, add_marker=add_marker, scientific_name=sciname)
                logging.debug("Mapa renderizado com sucesso.")
                # GeoAnalyst: Removido disparo manual v0.8.9. 
                # A cascata 2 -> 3 agora é gerida exclusivamente pelo Orchestrator para evitar crash de threads.
                if add_marker:
                    # Apenas atualizamos a label visual na UI, se necessário
                    pass
                
                logging.debug("Mapa renderizado com sucesso.")
            except Exception as e:
                logging.error(f"ERRO CRÍTICO ao atualizar mapa: {e}")
           
            # REFORÇO V0.7.7: Reafirmar soberania após carga de componentes Chromium
            StyleManager.setup_window_theme(self)
            
            logging.info("--- PROCESSO DE IDENTIFICAÇÃO FINALIZADO ---")

        
    def _ao_erro_api(self, erro_msg):
        logging.error(f"Erro na API (Info Espécie): {erro_msg}")
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


        # --- CARREGAMENTO DO ÍCONE DA JANELA (Dinâmico v0.6.5) ---
        StyleManager.set_app_icon(self)

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
        
        # --- NOVO: GRID DE COLUNAS COM SIMETRIA E ALINHAMENTO HORIZONTAL (v1.6.15) ---
        layout_cards_superiores = QGridLayout()
        layout_cards_superiores.setSpacing(15)
        
        # OBRIGAR SIMETRIA: As colunas 0, 1 e 2 devem ter exato peso 1
        layout_cards_superiores.setColumnStretch(0, 1)
        layout_cards_superiores.setColumnStretch(1, 1)
        layout_cards_superiores.setColumnStretch(2, 1)
        
        # LINHA 0: TÍTULOS
        lbl_titulo_user = QLabel("Imagem Pesquisada")
        lbl_titulo_user.setProperty("class", "lbl-titulo-sessao")
        layout_cards_superiores.addWidget(lbl_titulo_user, 0, 0)
        
        lbl_titulo_ref = QLabel("Imagem Referência")
        lbl_titulo_ref.setProperty("class", "lbl-titulo-sessao")
        layout_cards_superiores.addWidget(lbl_titulo_ref, 0, 1)

        lbl_titulo_res = QLabel("Resultados da Análise")
        lbl_titulo_res.setProperty("class", "lbl-titulo-sessao")
        layout_cards_superiores.addWidget(lbl_titulo_res, 0, 2)
        
        # --- CRIAÇÃO DOS WIDGETS ---
        
        # 1. Cards de Imagem
        self.card_user = ImageCardWidget()
        self.card_user.set_placeholder("Arraste e solte uma foto aqui\n\nou clique para selecionar")
        self.card_user.set_on_drop(self._carregar_imagem)
        self.card_user.set_on_click(self._abrir_seletor_arquivo)
        
        self.card_ref = ImageCardWidget()
        self.card_ref.set_placeholder(self.PLACEHOLDER_TEXT)

        # 2. Painéis de Informação (Construção Interna)
        
        # [A] CARD IDENTIFICAÇÃO
        grupo_resultados = QFrame()
        grupo_resultados.setProperty("class", "painel")
        StyleManager.apply_shadow(grupo_resultados)
        layout_res = QVBoxLayout(grupo_resultados)
        layout_res.setContentsMargins(12, 18, 12, 12)
        
        self.lbl_nome_comum = QLabel(self._format_nome_ave("Nome Comum:", self.PLACEHOLDER_TEXT, is_placeholder=True))
        self.lbl_nome_comum.setObjectName("lbl_nome_comum")
        self.lbl_nome_comum.setWordWrap(True)
        self.lbl_nome_comum.setTextFormat(Qt.RichText)
        
        self.lbl_certeza = QLabel("")
        self.lbl_certeza.setObjectName("lbl_certeza")
        self.lbl_certeza.setWordWrap(True)
        self.lbl_certeza.setTextFormat(Qt.RichText)
        self.lbl_certeza.setVisible(False)
        
        self.lbl_candidatos = QLabel("")
        self.lbl_candidatos.setObjectName("lbl_candidatos")
        self.lbl_candidatos.setWordWrap(True)
        self.lbl_candidatos.setTextFormat(Qt.RichText)
        self.lbl_candidatos.setVisible(False)
        self.lbl_candidatos.setProperty("class", "container-borda-cinza-fill")

        self.lbl_nome_ingles = QLabel(self._format_nome_ave("Nome em Inglês:", self.PLACEHOLDER_TEXT, is_placeholder=True))
        self.lbl_nome_ingles.setWordWrap(True)
        self.lbl_nome_ingles.setTextFormat(Qt.RichText)
        
        lbl_titulo_nc = QLabel("Nome Científico")
        lbl_titulo_nc.setProperty("class", "lbl-titulo-sessao")
        layout_res.addWidget(lbl_titulo_nc)

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
        if os.path.exists(caminho_lupa): self.btn_search.setIcon(QIcon(caminho_lupa))
        else: self.btn_search.setText("🔍")
        self.btn_search.clicked.connect(self._realizar_busca_manual)
        
        container_busca.addWidget(self.input_especie)
        container_busca.addWidget(self.btn_search)
        layout_res.addLayout(container_busca)
        layout_res.addWidget(self.lbl_certeza)
        layout_res.addWidget(self.lbl_candidatos)
        layout_res.addWidget(self.lbl_nome_comum)
        layout_res.addWidget(self.lbl_nome_ingles)

        # [B] CARD ETIMOLOGIA
        grupo_etimologia = QFrame()
        grupo_etimologia.setProperty("class", "painel")
        StyleManager.apply_shadow(grupo_etimologia)
        layout_eti = QVBoxLayout(grupo_etimologia)
        layout_eti.setContentsMargins(12, 18, 12, 12)
        
        self.lbl_titulo_etimologia = QLabel('Etimologia <i>(WikiAves)</i>')
        self.lbl_titulo_etimologia.setProperty("class", "lbl-titulo-sessao")
        layout_eti.addWidget(self.lbl_titulo_etimologia)

        self.txt_etimologia = QTextEdit()
        self.txt_etimologia.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.txt_etimologia.setReadOnly(True)
        self.txt_etimologia.setPlaceholderText(self.PLACEHOLDER_TEXT)
        self.txt_etimologia.setMinimumHeight(45) 
        self.txt_etimologia.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.txt_etimologia.textChanged.connect(self._ajustar_altura_etimologia)
        self.txt_etimologia.setProperty("class", "container-borda-cinza")
        layout_eti.addWidget(self.txt_etimologia)
        
        self.frame_etimologia = QFrame()
        self.frame_etimologia.setObjectName("frame_etimologia")
        self.frame_etimologia.setStyleSheet("QFrame#frame_etimologia { background-color: #F8F9FA; border-left: 4px solid #10B981; border-radius: 4px; padding: 10px; margin-top: 10px; }")
        layout_etim_sub = QVBoxLayout(self.frame_etimologia)
        self.lbl_etimologia_texto = QLabel("Carregando...")
        self.lbl_etimologia_texto.setWordWrap(True)
        layout_etim_sub.addWidget(self.lbl_etimologia_texto)
        self.frame_etimologia.setVisible(False)
        layout_eti.addWidget(self.frame_etimologia)

        # [C] CARD TAXONOMIA
        grupo_taxonomia = QFrame()
        grupo_taxonomia.setProperty("class", "painel")
        StyleManager.apply_shadow(grupo_taxonomia)
        layout_tax = QVBoxLayout(grupo_taxonomia)
        layout_tax.setContentsMargins(12, 18, 12, 12)
        
        lbl_titulo_tax = QLabel("Taxonomia")
        lbl_titulo_tax.setProperty("class", "lbl-titulo-sessao")
        layout_tax.addWidget(lbl_titulo_tax)

        self.lbl_taxonomia_texto = QLabel(self.PLACEHOLDER_TEXT)
        self.lbl_taxonomia_texto.setWordWrap(True)
        self.lbl_taxonomia_texto.setTextFormat(Qt.RichText)
        self.lbl_taxonomia_texto.setProperty("class", "container-borda-cinza-fill lbl-placeholder")
        layout_tax.addWidget(self.lbl_taxonomia_texto)

        # [D] CARD CONSERVAÇÃO
        grupo_conservacao = QFrame()
        grupo_conservacao.setProperty("class", "painel")
        StyleManager.apply_shadow(grupo_conservacao)
        layout_cons = QVBoxLayout(grupo_conservacao)
        layout_cons.setContentsMargins(12, 18, 12, 12)
        
        lbl_titulo_cons = QLabel("Status de Conservação")
        lbl_titulo_cons.setProperty("class", "lbl-titulo-sessao")
        layout_cons.addWidget(lbl_titulo_cons)
        
        self.lbl_conservacao_texto = QLabel(self.PLACEHOLDER_TEXT)
        self.lbl_conservacao_texto.setWordWrap(True)
        self.lbl_conservacao_texto.setTextFormat(Qt.RichText)
        self.lbl_conservacao_texto.setProperty("class", "container-borda-cinza-fill lbl-placeholder")
        layout_cons.addWidget(self.lbl_conservacao_texto)

        # [E] DESCRIÇÃO (WIKIAVES)
        self.painel_desc_container = QWidget()
        layout_desc_v = QVBoxLayout(self.painel_desc_container)
        layout_desc_v.setContentsMargins(0, 0, 0, 0)
        
        lbl_titulo_desc = QLabel('Descrição da Espécie <i>(WikiAves)</i>')
        lbl_titulo_desc.setProperty("class", "lbl-titulo-sessao")
        layout_desc_v.addWidget(lbl_titulo_desc)

        self.txt_descricao = QTextEdit()
        self.txt_descricao.setReadOnly(True)
        self.txt_descricao.setPlaceholderText(self.PLACEHOLDER_TEXT)
        self.txt_descricao.setMinimumHeight(45) 
        self.txt_descricao.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.txt_descricao.textChanged.connect(self._ajustar_altura_descricao)
        self.txt_descricao.setProperty("class", "container-borda-cinza")
        layout_desc_v.addWidget(self.txt_descricao)

        # 3. Painéis de Ação (Botoes)
        
        # [FILA 1] 5 Botões
        self.btn_google_lens = QPushButton("Pesquisar com Google Lens")
        self.btn_google_lens.setCursor(Qt.PointingHandCursor)
        self.btn_google_lens.setEnabled(False)
        self.btn_google_lens.clicked.connect(self._abrir_google_lens)
        
        self.btn_fonte = QPushButton("Abrir Fonte")
        self.btn_fonte.setCursor(Qt.PointingHandCursor)
        self.btn_fonte.setEnabled(False)
        self.btn_fonte.clicked.connect(lambda: QDesktopServices.openUrl(self.btn_fonte.property("url_alvo")))
        
        layout_buscas = QHBoxLayout()
        layout_buscas.setSpacing(10)
        self.btn_wiki = QPushButton("WikiAves"); self.btn_wiki.clicked.connect(self._buscar_wikiaves)
        self.btn_ebird = QPushButton("eBird"); self.btn_ebird.clicked.connect(self._buscar_ebird)
        self.btn_google = QPushButton("Google"); self.btn_google.clicked.connect(self._buscar_google)
        layout_buscas.addWidget(self.btn_wiki)
        layout_buscas.addWidget(self.btn_ebird)
        layout_buscas.addWidget(self.btn_google)

        # [FILA 2] Ações Finais
        self.btn_nova = QPushButton("Nova Identificação")
        self.btn_nova.setCursor(Qt.PointingHandCursor)
        self.btn_nova.clicked.connect(self._ao_clicar_nova_identificacao)
        self.btn_gravar_exif = QPushButton("Gravar Dados na Fotografia")
        self.btn_gravar_exif.setCursor(Qt.PointingHandCursor)
        self.btn_gravar_exif.setEnabled(False)
        self.btn_gravar_exif.clicked.connect(self._gravar_metadados_exif)

        # 4. Blocos Geo e Audio (v1.6.25: Mapa em Card Padronizado)
        self.grupo_mapa_card = QFrame()
        self.grupo_mapa_card.setProperty("class", "painel")
        StyleManager.apply_shadow(self.grupo_mapa_card)
        layout_mapa_card = QVBoxLayout(self.grupo_mapa_card)
        layout_mapa_card.setContentsMargins(12, 18, 12, 12)

        lbl_titulo_geo = QLabel("Localização Geográfica")
        lbl_titulo_geo.setProperty("class", "lbl-titulo-sessao")
        layout_mapa_card.addWidget(lbl_titulo_geo)
        
        self.map_principal = MapWidget()
        self.map_principal.setMinimumHeight(400) 
        # Mapa inicia centralizado no Brasil, sem exibir alerta (v1.6.26)
        self.map_principal.update_map(-14.2350, -51.9253, zoom=4, force_hide_alert=True)
        self.map_principal.marker_dragged.connect(self._ao_arrastar_pino)
        self.map_principal.audio_clicked.connect(self._ao_clicar_pin_audio)
        self.map_principal.alert_clicked.connect(self._abrir_dialogo_localizacao)
        layout_mapa_card.addWidget(self.map_principal)

        grupo_geo = QFrame(); grupo_geo.setProperty("class", "painel"); StyleManager.apply_shadow(grupo_geo)
        layout_geo_det = QVBoxLayout(grupo_geo); layout_geo_det.setContentsMargins(12, 18, 12, 12)
        lbl_titulo_geo_card = QLabel("Dados Geográficos"); lbl_titulo_geo_card.setProperty("class", "lbl-titulo-sessao")
        layout_geo_det.addWidget(lbl_titulo_geo_card)
        self.lbl_geo_details = QLabel(self.PLACEHOLDER_TEXT); self.lbl_geo_details.setWordWrap(True)
        self.lbl_geo_details.setProperty("class", "container-borda-cinza-fill lbl-placeholder")
        layout_geo_det.addWidget(self.lbl_geo_details)

        grupo_audio = QFrame(); grupo_audio.setProperty("class", "painel"); StyleManager.apply_shadow(grupo_audio)
        layout_audio = QVBoxLayout(grupo_audio); layout_audio.setContentsMargins(12, 18, 12, 12)
        
        # Título restaurado para evitar AttributeError (v1.6.24)
        self.lbl_vocal_title = QLabel("Vocalizações")
        self.lbl_vocal_title.setProperty("class", "lbl-titulo-sessao")
        layout_audio.addWidget(self.lbl_vocal_title)
        self.vocal_details_container = QFrame()
        self.vocal_details_container.setProperty("class", "container-borda-cinza-fill")
        self.vocal_details_layout = QVBoxLayout(self.vocal_details_container)
        self.vocal_details_layout.setContentsMargins(0, 0, 0, 0)
        self.vocal_details_layout.setSpacing(0)
        
        # Placeholder movido para dentro do container cinza (v1.6.23)
        self.lbl_audio_placeholder = QLabel(self.PLACEHOLDER_TEXT)
        self.lbl_audio_placeholder.setProperty("class", "lbl-placeholder")
        self.lbl_audio_placeholder.setAlignment(Qt.AlignCenter)
        self.lbl_audio_placeholder.setMinimumHeight(60)
        self.vocal_details_layout.addWidget(self.lbl_audio_placeholder)
        
        layout_audio.addWidget(self.vocal_details_container)
        # Container inicia visível para manter simetria (v1.6.23)
        self.vocal_details_container.setVisible(True)

        # --- ASSEMBLE GRID MESTRE (v1.6.15) ---
        
        # COLUNA DIREITA SUP (ID, ETI, TAX) - Agrupar p/ manter coladas
        painel_direito_sup = QWidget()
        layout_dir_v1 = QVBoxLayout(painel_direito_sup)
        layout_dir_v1.setContentsMargins(0, 0, 0, 0)
        layout_dir_v1.setSpacing(StyleManager.SPACING_MD)
        layout_dir_v1.addWidget(grupo_resultados)
        layout_dir_v1.addWidget(grupo_etimologia)
        layout_dir_v1.addWidget(grupo_taxonomia)

        # LINHA 1
        layout_cards_superiores.addWidget(self.card_user, 1, 0)
        layout_cards_superiores.addWidget(self.card_ref, 1, 1)
        layout_cards_superiores.addWidget(painel_direito_sup, 1, 2)
        
        # LINHA 2: FILA HORIZONTAL DE BOTÕES 1
        layout_cards_superiores.addWidget(self.btn_google_lens, 2, 0)
        layout_cards_superiores.addWidget(self.btn_fonte, 2, 1)
        layout_cards_superiores.addLayout(layout_buscas, 2, 2)
        
        # LINHA 3: DESCRIÇÃO E CONSERVAÇÃO
        layout_cards_superiores.addWidget(self.painel_desc_container, 3, 0, 1, 2)
        layout_cards_superiores.addWidget(grupo_conservacao, 3, 2)
        
        # LINHA 4: FILA HORIZONTAL DE BOTÕES 2
        layout_cards_superiores.addWidget(self.btn_nova, 4, 0, 1, 2)
        layout_cards_superiores.addWidget(self.btn_gravar_exif, 4, 2)
        
        # LINHA 5: MAPA E DETALHES FINAIS
        layout_cards_superiores.addWidget(self.grupo_mapa_card, 5, 0, 2, 2) # Span map card across 2 rows
        
        painel_direito_inf = QWidget()
        layout_dir_v2 = QVBoxLayout(painel_direito_inf); layout_dir_v2.setContentsMargins(0,0,0,0); layout_dir_v2.setSpacing(StyleManager.SPACING_MD)
        layout_dir_v2.addWidget(grupo_geo); layout_dir_v2.addWidget(grupo_audio)
        layout_cards_superiores.addWidget(painel_direito_inf, 5, 2)

        layout_mestre.addLayout(layout_cards_superiores)
        layout_mestre.addStretch()

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
                
                app = QApplication.instance()
                logging.debug(f"Watchdog v0.6.6: Forçando Soberania Off-White. DarkMode: {dark_mode}")

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
        """Abre o Guia do Usuário detalhado."""
        dialog = ManualUsuarioDialog(self)
        dialog.exec()

    def _obter_sciname_atual(self):
        return self.dados_identificacao_atual.get("nome_cientifico", "")

    def _buscar_wikiaves(self):
        """Abre WikiAves priorizando o link direto da espécie (v1.6.7)."""
        link_direto = self.dados_identificacao_atual.get("link_origem")
        if link_direto and "wikiaves.com.br" in link_direto:
            QDesktopServices.openUrl(QUrl(link_direto))
            return

        sciname = self._obter_sciname_atual()
        if sciname and "Inconclusiva" not in sciname:
            url = f"https://www.wikiaves.com.br/index.php?t=s&s={urllib.parse.quote(sciname)}"
            QDesktopServices.openUrl(QUrl(url))

    def _buscar_ebird(self):
        """Abre eBird priorizando o link direto da espécie (v1.6.7)."""
        link_direto = self.dados_identificacao_atual.get("link_ebird")
        if link_direto and "ebird.org" in link_direto:
            QDesktopServices.openUrl(QUrl(link_direto))
            return

        sciname = self._obter_sciname_atual()
        if sciname and "Inconclusiva" not in sciname:
            # Fallback limpo para a página de espécie no eBird (v1.6.7)
            url = f"https://ebird.org/species/{urllib.parse.quote(sciname).replace('%20', '')}"
            QDesktopServices.openUrl(QUrl(url))

    def _atualizar_mapa_com_gbif(self, sciname):
        """Atualiza o mapa com a camada GBIF se houver coordenadas definidas."""
        pass 

    # ... Metodos auxiliares ...

    def _buscar_google(self):
        sciname = self._obter_sciname_atual()
        if sciname and "Inconclusiva" not in sciname:
            url = f"https://www.google.com/search?q={urllib.parse.quote(sciname)}"
            QDesktopServices.openUrl(QUrl(url))

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
        self.lbl_nome_comum.setText(self._format_nome_ave("Nome Comum:", ""))
        self.lbl_nome_comum.setVisible(True)
        self.txt_descricao.setHtml("<i>Identificado pelo usuário.</i>")
        self.txt_descricao.setVisible(True)
        
        self.input_especie.setText(sci_formatted) # Garante o texto no widget
        
        self._iniciar_busca_imagem(sci_formatted)
        
        # Sincronizar localização atual com Orchestrator (v0.4.8)
        self.orchestrator.update_location(self.lat_atual, self.lon_atual)
        
        # O Orchestrator assume a cascata linear 1->2->3->4->5 a partir daqui (v0.4.6)
        self.orchestrator.start_cascade_from_step2(sci_formatted)
        
        self.btn_wiki.setVisible(True); self.btn_wiki.setEnabled(True)
        self.btn_google.setVisible(True); self.btn_google.setEnabled(True)
        self.btn_ebird.setVisible(True); self.btn_ebird.setEnabled(True)


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
        coords = extract_lat_lon(caminho)
        if coords:
            lat, lon = coords
            self.lat_atual = lat
            self.lon_atual = lon
            logging.debug(f"Coordenadas encontradas na imagem: {lat}, {lon}")
            
            if self.map_principal:
                # Mapa atualiza apenas com coordenadas por enquanto. 
                self.map_principal.update_map(lat, lon, zoom=6, add_marker=True)
                
            # Atualiza card geo
            self.lbl_geo_details.setVisible(True)
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
            
            logging.debug("Sem dados GPS na imagem.")
            
            if self.map_principal:
                 # Se for uma NOVA imagem carregada sem GPS, mantemos o mapa no Brasil e ativamos o alerta (v1.6.26)
                 self.map_principal.update_map(-14.2350, -51.9253, zoom=4, force_hide_alert=False)
                 self.lbl_geo_details.setVisible(True)
                 self.lbl_geo_details.setText("Localização não detectada na imagem.")
                 self.lbl_geo_details.setProperty("class", "container-borda-cinza-fill")
                 self.lbl_geo_details.style().unpolish(self.lbl_geo_details)
                 self.lbl_geo_details.style().polish(self.lbl_geo_details)
             
        self._identificar_ave()

    def _ao_arrastar_pino(self, lat, lon):
        logging.info(f"Pino do mapa arrastado para: Lat {lat}, Lon {lon}")
        lat = round(lat, 6)
        lon = round(lon, 6)
        self.lat_atual = lat
        self.lon_atual = lon
        self.status_bar.showMessage(f"Coordenadas atualizadas via mapa (Lat {lat}, Lon {lon})")
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
                self.lbl_geo_details.setVisible(True)
                self.lbl_geo_details.setText(f"Lat: {lat:.4f}, Lon: {lon:.4f} (Manual)")
                self.lbl_geo_details.setProperty("class", "container-borda-cinza-fill")
                self.lbl_geo_details.style().unpolish(self.lbl_geo_details)
                self.lbl_geo_details.style().polish(self.lbl_geo_details)
                
                self._atualizar_geo_info(lat, lon)
                
                # Salva a localização manual para ser usada ao recarregar imagem ou atualizar mapa
                self.ultima_localizacao_manual = (lat, lon)
                
                # ATUALIZAÇÃO INTELIGENTE (v0.6.8)
                sci_name = self.dados_identificacao_atual.get("nome_cientifico") or self.especie_em_processamento
                if sci_name and sci_name != "Identificação Inconclusiva" and "..." not in sci_name:
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

        self.lbl_nome_comum.setText(self._format_nome_ave("Nome Comum:", self.PLACEHOLDER_TEXT, is_placeholder=True))
        self.lbl_nome_ingles.setText(self._format_nome_ave("Nome em Inglês:", self.PLACEHOLDER_TEXT, is_placeholder=True))
        
        self.txt_etimologia.clear()
        self.txt_etimologia.setPlaceholderText(self.PLACEHOLDER_TEXT)
        self.lbl_titulo_etimologia.setVisible(True)
        self.txt_etimologia.setVisible(True)
        
        if hasattr(self, 'lbl_taxonomia_texto'):
            self.lbl_taxonomia_texto.setText(self.PLACEHOLDER_TEXT)
            self.lbl_taxonomia_texto.setProperty("class", "container-borda-cinza-fill lbl-placeholder")
            self.lbl_taxonomia_texto.setVisible(True)
        
        self.input_especie.clear() 
        self.input_especie.setProperty("class", "sci-name-input")
        self.input_especie.style().unpolish(self.input_especie)
        self.input_especie.style().polish(self.input_especie)
        
        self.lbl_geo_details.setText(self.PLACEHOLDER_TEXT)
        self.lbl_geo_details.setProperty("class", "container-borda-cinza-fill lbl-placeholder")
        self.lbl_geo_details.setVisible(True)
        
        if hasattr(self, 'lbl_conservacao_texto'):
            self.lbl_conservacao_texto.setText(self.PLACEHOLDER_TEXT)
            self.lbl_conservacao_texto.setProperty("class", "container-borda-cinza-fill lbl-placeholder")
            self.lbl_conservacao_texto.setVisible(True)
            
        self.txt_descricao.clear()
        self.txt_descricao.setPlaceholderText(self.PLACEHOLDER_TEXT)
        
        self.lbl_audio_placeholder.setText(self.PLACEHOLDER_TEXT)
        self.lbl_audio_placeholder.setProperty("class", "container-borda-tracejada lbl-placeholder")
        self.lbl_audio_placeholder.setVisible(True)
        
        self.card_ref.set_placeholder(self.PLACEHOLDER_TEXT)
        self.status_bar.showMessage("Iniciando IA Local...")
        
        self.card_user.setAcceptDrops(False) 
        
        try:
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
        self.dados_identificacao_atual = dados
        
        raw_sci = dados.get("nome_cientifico", "")
        
        import re
        sci_clean = re.sub(r"[(\[].*?[)\]]", "", raw_sci)
        parts = sci_clean.strip().split()
        if len(parts) >= 2:
            sci = f"{parts[0]} {parts[1]}"
        else:
            sci = sci_clean.strip()
            
        conf = dados.get("confianca", 0.0)
        status_msg = dados.get("status_msg", "")
        top_candidates = dados.get("top_candidates", [])
        
        # Exibição da Certeza (v0.8.8): Cor padronizada e metadados da IA
        self.lbl_certeza.setText(f'<span style="color: #4B5563; font-weight: bold; font-size: 11px;">Certeza:</span>&nbsp;&nbsp;'
                                 f'<span style="color: #4B5563; font-weight: 500; font-size: 13px;">{conf*100:.1f}% (EfficientNet V1.3)</span>')
        self.lbl_certeza.setVisible(True)

        if "Inconclusiva" not in status_msg and "Baixa" not in status_msg and sci:
            # ... (formatação sci_formatted existente)
            sci_clean = re.sub(r"[(\[].*?[)\]]", "", sci).strip()
            parts = sci_clean.split()
            if len(parts) >= 2:
                sci_formatted = f"{parts[0].capitalize()} {parts[1].lower()}"
            else:
                sci_formatted = sci_clean.capitalize()

            self.input_especie.setText(sci_formatted)
            self.input_especie.style().unpolish(self.input_especie)
            self.input_especie.style().polish(self.input_especie)
            
            if self.dados_identificacao_atual:
                self.dados_identificacao_atual["nome_cientifico"] = sci_formatted
            
            self.lbl_candidatos.setVisible(False)
        else:
             self.input_especie.clear()
             self.input_especie.setProperty("class", "container-borda-cinza")
             self.input_especie.style().unpolish(self.input_especie)
             self.input_especie.style().polish(self.input_especie)
             
             # Exibição de Candidatos Alternativos (v0.8.6)
             if top_candidates:
                 html_cand = '<div style="line-height: 140%; font-size: 12px; color: #374151;">'
                 html_cand += '<b>Sugestões Alternativas:</b><br>'
                 for i, cand in enumerate(top_candidates[:3]):
                      nome_c = cand.get("label", "Desconhecido")
                      c_conf = cand.get("confianca", 0.0)
                      html_cand += f"• {nome_c} ({c_conf*100:.1f}%)<br>"
                 html_cand += '</div>'
                 self.lbl_candidatos.setText(html_cand)
                 self.lbl_candidatos.setVisible(True)
             else:
                 self.lbl_candidatos.setVisible(False)
        
        if status_msg == "Baixa confiança":
            self.status_bar.showMessage("Identificação inconclusiva.")
            # ... 
            self.btn_wiki.setEnabled(False)
            self.btn_google.setEnabled(False)
            self.btn_ebird.setEnabled(False)
            
            self.card_ref.set_placeholder("Busca visual suspensa")
            self.card_ref.set_pixmap(None)
            self.card_ref.set_overlay_text(None)
            
            self.lbl_nome_comum.setText(self._format_nome_ave("Nome Comum:", "Identificação Inconclusiva"))
            self.lbl_nome_ingles.setText(self._format_nome_ave("Nome em Inglês:", "---"))
            self.btn_google_lens.setEnabled(True)

        else:
            self.status_bar.showMessage("Identificação concluída.")
            
            self.btn_wiki.setEnabled(True)
            self.btn_google.setEnabled(True)
            self.btn_ebird.setEnabled(True)
            self.btn_gravar_exif.setEnabled(True)
            self.btn_wiki.setVisible(True)
            self.btn_google.setVisible(True)
            self.btn_ebird.setVisible(True)
            
            if sci:
                self._iniciar_busca_imagem(sci)
        
    def _ao_erro_identificacao(self, erro_msg):
        self.status_bar.showMessage("Erro na identificação.")
        self.card_user.setAcceptDrops(True)
        self.lbl_nome_comum.setText(self._format_nome_ave("Nome Comum:", erro_msg))
        self.lbl_nome_ingles.setText(self._format_nome_ave("Nome em Inglês:", erro_msg))
        self.lbl_etimologia_texto.setText("Ocorreu um erro durante a identificação local.")
        
    # --- Áudio Player (v0.4.0) ---

    def _ao_encontrar_audio(self, resultados):
        """Recebe lista de áudios e cria os players."""
        if not hasattr(self, 'vocal_details_container') or not self.vocal_details_container:
             return

        layout = self.vocal_details_container.layout()
        if not layout:
            return

        if resultados:
            self.lbl_audio_placeholder.setVisible(False) 
            self.vocal_details_container.setVisible(True)
            for i, audio in enumerate(resultados):
                card = VocalAuditCard(
                    audio_data=audio,
                    ranking_index=i+1, 
                    on_click=self._abrir_detalhes_vocal,
                    parent=self.vocal_details_container
                )
                layout.addWidget(card)
                
                if not hasattr(self, 'active_audio_players'):
                    self.active_audio_players = []
                self.active_audio_players.append(card)
            
    def _abrir_detalhes_vocal(self, audio_data):
        """Abre a janela de auditoria detalhada ao clicar no ícone vocal (v1.3.1)."""
        logging.debug(f"Abrindo Detalhes Vocal: ID {audio_data.get('id')}")
        dialog = VocalDetailDialog(audio_data, self)
        dialog.exec()
            
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
            sci = self._obter_sciname_atual()
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

        self.lbl_geo_details.setText("🔄 Analisando local e bioma...")
        self.lbl_geo_details.setVisible(True)
        
        self._limpar_painel_audio()

        if self.orchestrator:
             self.orchestrator.reprocessar_localizacao(lat, lon)

    def _ao_clicar_pin_audio(self, audio_id):
        """Lida com o clique no pin de áudio do mapa (v1.2.5)."""
        if not hasattr(self, 'active_audio_players'):
            return
            
        for player in self.active_audio_players:
            if hasattr(player, 'audio_data'):
                p_id = str(player.audio_data.get('id', '')).strip()
                t_id = str(audio_id).strip()
                
                if p_id == t_id:
                    if hasattr(player, 'on_click_callback') and player.on_click_callback:
                        if hasattr(player, 'btn_icon'):
                            player.btn_icon.animateClick()
                    
                    if hasattr(player, 'highlight'):
                        player.highlight()
                    self.scroll_area.ensureWidgetVisible(player)
                    break
        
    def _ao_concluir_geo_analise(self, details):
        self.last_geo_data = details
        self.lat_atual = details.get('lat')
        self.lon_atual = details.get('lon')
        
        self._atualizar_card_geografico()
        self._registrar_dados_geo_iucn()
        
    def _ao_concluir_iucn(self, results):
        self.last_iucn_data = results
        self._registrar_dados_geo_iucn()
        self._atualizar_card_conservacao()

    def _ao_concluir_conservacao_nacional(self, results):
        self.last_conservation_data = results
        self._registrar_dados_geo_iucn()
        self._atualizar_card_conservacao()
        self._atualizar_card_geografico()

    def _atualizar_card_geografico(self):
        """Formata o lbl_geo_details com endereço, bioma e endemismo (v1.6.19)."""
        if not hasattr(self, 'lbl_geo_details'): return
        
        details = getattr(self, 'last_geo_data', {})
        cons_data = getattr(self, 'last_conservation_data', {})
        
        lat = details.get('lat')
        lon = details.get('lon')
        lat_str = f"{lat:.5f}" if isinstance(lat, (float, int)) else "?"
        lon_str = f"{lon:.5f}" if isinstance(lon, (float, int)) else "?"
        
        endemismo = cons_data.get("endemismo")
        if endemismo is None:
            endemismo_str = '<span style="color: #9CA3AF; font-style: italic;">Consultando...</span>'
        else:
            endemismo_str = f"{endemismo}"

        texto_html = f"""
        <div style="line-height: 150%;">
        <b>Coordenadas:</b> Lat {lat_str}, Long {lon_str}<br>
        <b>País:</b> {details.get('pais', '-')}<br>
        <b>Estado:</b> {details.get('estado', '-')}<br>
        <b>Município:</b> {details.get('municipio', '-')}<br>
        <b>Bioma:</b> {details.get('bioma', '-')}<br>
        <b>Endêmica do Brasil:</b> {endemismo_str}
        </div>
        """
        
        self.lbl_geo_details.setText(texto_html)
        self.lbl_geo_details.setVisible(True)
        self._set_placeholder_style(self.lbl_geo_details, active=False)
        self.lbl_geo_details.setTextInteractionFlags(Qt.TextSelectableByMouse)

    def _atualizar_card_conservacao(self):
        """Formata o lbl_conservacao_texto com IUCN, ICMBio e CITES (v1.6.5)."""
        if not hasattr(self, 'lbl_conservacao_texto'): return

        from modules.step3_geography.conservation_worker import NationalConservationWorker

        iucn_data = getattr(self, 'last_iucn_data', {})
        cons_data = getattr(self, 'last_conservation_data', {})

        iucn_raw = iucn_data.get("iucn_status", "Não Avaliado")
        iucn_ext = NationalConservationWorker.traduzir_iucn(iucn_raw)
        
        icmbio = cons_data.get("status_icmbio", "Não Avaliado")
        cites = cons_data.get("status_cites", "Não Listado")

        texto_html = f"""
        <div style="line-height: 140%;">
        <b>IUCN (Global):</b> {iucn_ext}<br>
        <b>ICMBio (Nacional):</b> {icmbio}<br>
        <b>CITES:</b> {cites}
        </div>
        """
        self.lbl_conservacao_texto.setText(texto_html)
        self._set_placeholder_style(self.lbl_conservacao_texto, active=False)
        self.lbl_conservacao_texto.setVisible(True)

    def _ao_concluir_ebird(self, results):
        if hasattr(self, 'session_logger'):
            ordem_atual = self.dados_identificacao_atual.get("ordem")
            familia_atual = self.dados_identificacao_atual.get("familia")
            
            ordem_final = results.get("ordem") if (results.get("ordem") and results.get("ordem") != "Desconhecida") else ordem_atual
            familia_final = results.get("familia") if (results.get("familia") and results.get("familia") != "Desconhecida") else familia_atual

            link_ebird_final = results.get("link_ebird")
            if not link_ebird_final or "ebird.org" not in link_ebird_final:
                 link_ebird_final = self.dados_identificacao_atual.get("link_ebird", "")

            nome_en_atual = self.dados_identificacao_atual.get("nome_ingles", "")
            nome_en_final = results.get("nome_ingles") if results.get("nome_ingles") else nome_en_atual

            self.session_logger.atualizar_ultimo_registro({
                "nome_ingles": nome_en_final,
                "classe": results.get("classe", "Aves"),
                "ordem": ordem_final or "Desconhecida",
                "familia": familia_final or "Desconhecida",
                "ebird_code": results.get("ebird_code", ""),
                "raridade_regional": results.get("raridade_regional", ""),
                "link_ebird": link_ebird_final
            })
            
            if not self.dados_identificacao_atual:
                self.dados_identificacao_atual = {}
            self.dados_identificacao_atual["link_ebird"] = link_ebird_final

        if hasattr(self, 'lbl_taxonomia_texto'):
            ordem_vis = results.get('ordem') if (results.get('ordem') and results.get('ordem') != "Desconhecida") else self.dados_identificacao_atual.get("ordem")
            familia_vis = results.get('familia') if (results.get('familia') and results.get('familia') != "Desconhecida") else self.dados_identificacao_atual.get("familia")

            self._atualizar_card_taxonomia(
                classe=results.get('classe', 'Aves'),
                ordem=ordem_vis,
                familia=familia_vis
            )
            
    def _atualizar_card_taxonomia(self, classe="Aves", ordem=None, familia=None):
        """Helper para centralizar a atualização visual do card de taxonomia."""
        if not hasattr(self, 'lbl_taxonomia_texto'): return
        
        nome_ci = self.dados_identificacao_atual.get("nome_cientifico", "")
        genero = nome_ci.split(" ")[0] if nome_ci and " " in nome_ci else "-"
        
        texto_tax = f"""
        <div style="line-height: 150%;">
        <b>Classe:</b> {classe}<br>
        <b>Ordem:</b> {ordem or '-'}<br>
        <b>Família:</b> {familia or '-'}<br>
        <b>Gênero:</b> {genero}
        </div>
        """
        self.lbl_taxonomia_texto.setText(texto_tax)
        self._set_placeholder_style(self.lbl_taxonomia_texto, active=False)
        self.lbl_taxonomia_texto.setVisible(True)
        self.lbl_taxonomia_texto.setTextInteractionFlags(Qt.TextSelectableByMouse)

    def _registrar_dados_geo_iucn(self):
        """Consolida e registra metadados de geografia e conservação na sessão atual (v0.8.8)."""
        geo = getattr(self, 'last_geo_data', {})
        iucn = getattr(self, 'last_iucn_data', {})
        cons = getattr(self, 'last_conservation_data', {})
        
        # Mapeamento robusto para garantir que o diálogo EXIF e o EXIFManager encontrem os dados
        dados_consolidados = {
            "latitude": self.lat_atual,
            "longitude": self.lon_atual,
            "pais": geo.get("pais", "Brasil"),
            "estado": geo.get("estado", "-"),
            "municipio": geo.get("municipio", "-"),
            "bioma": geo.get("bioma", "-"),
            "endemismo": geo.get("endemico", "Não"),
            "iucn_status": iucn.get("iucn_status", "Não Avaliado"),
            "status_icmbio": cons.get("status_icmbio", "Não Avaliado"),
            "status_cites": cons.get("status_cites", "Não Listado"),
            "classe": "Aves"
        }
        
        if hasattr(self, 'session_logger'):
             self.session_logger.atualizar_ultimo_registro(dados_consolidados)

    def _ao_clicar_nova_identificacao(self):
        """Dispara um reset completo antes de abrir o seletor (v0.8.10)."""
        self._resetar_interface(manter_imagem=False)
        self._abrir_seletor_arquivo()

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
                    if hasattr(player, 'stop'): player.stop()
                    player.setParent(None)
                    player.deleteLater()
                except: pass
            self.active_audio_players = []
        
        if hasattr(self, 'lbl_audio_placeholder'):
            layout = self.lbl_audio_placeholder.parentWidget().layout()
            if layout:
                for i in reversed(range(layout.count())):
                    item = layout.itemAt(i)
                    widget = item.widget()
                    if widget and widget not in [self.lbl_audio_placeholder, self.lbl_vocal_title, getattr(self, 'vocal_details_container', None)]:
                        widget.setParent(None)
                        widget.deleteLater()

            self.lbl_audio_placeholder.setText(self.PLACEHOLDER_TEXT)
            self.lbl_audio_placeholder.setProperty("class", "lbl-placeholder")
            self.lbl_audio_placeholder.setVisible(True)
        
        if hasattr(self, 'vocal_details_container'):
            self.vocal_details_container.setVisible(True)

    def _resetar_interface(self, manter_imagem=False):
        if hasattr(self, 'orchestrator'):
            self.orchestrator.reset()

        if hasattr(self, 'session_logger'):
            self.session_logger.reset()
            
        self._limpar_painel_audio()
        
        if not manter_imagem:
            self.caminho_imagem_atual = None
            self.lat_atual = None
            self.lon_atual = None
            self.card_user.set_image_path(None)
            self.card_user.set_placeholder("Arraste e solte uma foto aqui\n\nou clique para selecionar")

        self.dados_identificacao_atual = {}
        self.last_iucn_data = {}
        self.last_conservation_data = {}
        self.especie_em_processamento = None # Adicionado v0.9.6 - Blindagem de Reset
        
        self.card_ref.set_image_path(None)
        self.card_ref.set_placeholder("Aguardando identificação....")
        self.card_ref.set_overlay_text(None)
        
        self.btn_fonte.setEnabled(False)
        self.btn_wiki.setEnabled(False)
        self.btn_google.setEnabled(False)
        self.btn_ebird.setEnabled(False)
        self.btn_gravar_exif.setEnabled(False)
        self.btn_wiki.setVisible(True)
        self.btn_google.setVisible(True)
        self.btn_ebird.setVisible(True)
        
        self.input_especie.clear()
        self.input_especie.setProperty("class", "container-borda-cinza")
        self.input_especie.style().unpolish(self.input_especie)
        self.input_especie.style().polish(self.input_especie)
        
        self.lbl_nome_comum.setText(self._format_nome_ave("Nome Comum:", "Aguardando identificação....", is_placeholder=True))
        self.lbl_nome_ingles.setText(self._format_nome_ave("Nome em Inglês:", "Aguardando identificação....", is_placeholder=True))
        
        # Reset de Confiança e Candidatos (v0.8.7)
        self.lbl_certeza.setText("")
        self.lbl_certeza.setVisible(False)
        self.lbl_candidatos.setText("")
        self.lbl_candidatos.setVisible(False)
        
        self.txt_etimologia.clear()
        self.txt_etimologia.setPlaceholderText(self.PLACEHOLDER_TEXT)
        self.lbl_titulo_etimologia.setVisible(True)
        self.txt_etimologia.setVisible(True)
        
        if hasattr(self, 'frame_etimologia'):
            self.frame_etimologia.setVisible(False)
            self.lbl_etimologia_texto.setText("Carregando...")

        if hasattr(self, 'lbl_taxonomia_texto'):
            self.lbl_taxonomia_texto.setText(self.PLACEHOLDER_TEXT)
            self._set_placeholder_style(self.lbl_taxonomia_texto, active=True)
            self.lbl_taxonomia_texto.setVisible(True)
        
        self.lbl_geo_details.setText(self.PLACEHOLDER_TEXT)
        self._set_placeholder_style(self.lbl_geo_details, active=True)
        self.lbl_geo_details.setVisible(True)
        
        if hasattr(self, 'lbl_conservacao_texto'):
            self.lbl_conservacao_texto.setText(self.PLACEHOLDER_TEXT)
            self._set_placeholder_style(self.lbl_conservacao_texto, active=True)
            self.lbl_conservacao_texto.setVisible(True)
            
        self.txt_descricao.clear()
        self.txt_descricao.setPlaceholderText(self.PLACEHOLDER_TEXT)
        
        if self.map_principal:
             self.map_principal.update_map(-14.2350, -51.9253, zoom=4, force_hide_alert=True)
             
        self.status_bar.showMessage("Pronto para nova identificação")

    def _gravar_metadados_exif(self):
        """Grava os dados consolidados da identificação atual na imagem (v1.8.1)."""
        if not hasattr(self, 'caminho_imagem_atual') or not self.caminho_imagem_atual:
            return
            
        if not hasattr(self, 'session_logger') or not self.session_logger.buffer:
            DialogoAviso("Sem Dados", "Nenhum dado disponível para gravação.", self, tipo="info").exec()
            return

        dados = self.session_logger.buffer[-1]
        
        # Detectar se há GPS original para proteger campos (v0.8.5)
        tem_gps = False
        if self.caminho_imagem_atual:
            from modules.step3_geography.geo_utils import extract_lat_lon
            if extract_lat_lon(self.caminho_imagem_atual):
                tem_gps = True

        # 🔹 Restauração do Diálogo de Configuração (v0.8.4)
        config_dialog = ExifConfigDialog(self, dados, tem_gps_nativo=tem_gps)
        if config_dialog.exec():
            selecionados = config_dialog.get_selected_fields()
            
            try:
                # Forçamos o processamento de eventos para garantir estabilidade da UI
                QApplication.processEvents()
                
                manager = EXIFManager()
                if manager.escrever_metadados_completos(self.caminho_imagem_atual, dados, selecionados):
                    def show_success():
                        msg = DialogoAviso("Sucesso", "Dados gravados com sucesso na fotografia.", self)
                        msg.exec()
                    QTimer.singleShot(100, show_success)
            except Exception as e:
                DialogoAviso("Erro", f"Falha na gravação: {e}", self, tipo="erro").exec()


    def closeEvent(self, event):
        if hasattr(self, 'session_logger'):
            self.session_logger.flush()
            self.session_logger.limpar_sessao()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = JanelaPrincipal()
    window.show()
    sys.exit(app.exec())
