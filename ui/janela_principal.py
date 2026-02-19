import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QFileDialog, QLineEdit, QTextEdit,
    QFrame, QStatusBar, QApplication, QSizePolicy, QGraphicsDropShadowEffect,
    QMessageBox, QCheckBox, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt, QSize, QThread, Signal, QSettings, QMimeData, QUrl, QTimer
from PySide6.QtGui import (
    QPixmap, QFont, QDragEnterEvent, QDropEvent, QIcon, QColor, 
    QPainter, QAction, QDesktopServices, QDrag, QResizeEvent, QPalette
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PIL import Image, ExifTags
from datetime import datetime
from PIL import Image, ExifTags
from datetime import datetime

# Importações do Core
from core.geo_utils import extract_lat_lon
from core.local_worker import LocalIdentificationWorker
from ui.janela_manual import JanelaManual
from ui.dialogo_aviso import DialogoAviso
from ui.worker_referencia import ReferenceImageWorker
from core.buscador_worker import BuscadorWorker
from core.logger import save_crash_log
from ui.widgets.map_widget import MapWidget
from ui.widgets.map_widget import MapWidget
from ui.custom_widgets import ImageCardWidget
from ui.dialogs.location_dialog import LocationDialog
from core.geo_analyst import GeoAnalyst

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
        
        self.setWindowTitle("iBirder")
        self.resize(1100, 700)
        
        self.caminho_imagem_atual = None
        self.dados_identificacao_atual = {}
        self.lat_atual = None
        self.lon_atual = None

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
        
        # Iniciar worker de informações da espécie (iNaturalist)
        self._iniciar_busca_info_especie(nome_cientifico)

    def _iniciar_busca_info_especie(self, nome_cientifico):
        # Limpeza segura do worker anterior
        old_worker = getattr(self, "worker_species", None)
        if old_worker is not None:
             try:
                 old_worker.info_found.disconnect()
                 old_worker.error_occurred.disconnect()
             except: pass

             if old_worker.isRunning():
                 old_worker.requestInterruption()
                 old_worker.quit()
                 old_worker.wait() # Bloqueia brevemente para garantir parada
             old_worker.deleteLater()

        self.worker_species = BuscadorWorker(nome_cientifico, parent=self)
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
             # Precisamos das coordenadas atuais. 
             # Como o MapWidget não expõe getter fácil do Folium, 
             # idealmente deveríamos ter guardado 'self.current_lat_lon' na classe.
             pass 
             # Vamos assumir que o usuário carregou a imagem e o mapa já tem o marker.
             # Mas para adicionar a camada GBIF, precisamos chamar update_map novamente.
             # O problema é: quais coordenadas?
             # Solução Rápida: Extrair novamente da imagem ou usar a última salva.
             
             lat, lon = None, None
             
             if self.caminho_imagem_atual:
                 coords = extract_lat_lon(self.caminho_imagem_atual)
                 if coords:
                     lat, lon = coords
                 
             if not lat and getattr(self, "ultima_localizacao_manual", None):
                 lat, lon = self.ultima_localizacao_manual
             
             # Fallback para as coordenadas atuais da classe se já definidas
             if not lat and self.lat_atual and self.lon_atual:
                  lat, lon = self.lat_atual, self.lon_atual

             if lat and lon:
                print(f"[UI] Atualizando Widget de Mapa... (GBIF: {sciname})")
                try:
                    # Se tivermos nome cientifico valido, o mapa mostrará o layer GBIF
                    self.map_principal.update_map(lat, lon, zoom=10, add_marker=True, scientific_name=sciname)
                    
                    # Geo (v0.3.11) - Se já temos coordenadas, atualizamos o painel
                    self._atualizar_geo_info(lat, lon)
                    print("[UI] Mapa e GeoAnalyst atualizados.")
                except Exception as e:
                    print(f"[UI] ERRO ao atualizar mapa: {e}")
            
             print("[UI] --- PROCESSO FINALIZADO ---\n")
        
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

        layout_principal = QHBoxLayout(widget_central)
        layout_principal.setContentsMargins(15, 15, 15, 15)
        layout_principal.setSpacing(15)

        # --- LADO ESQUERDO ---
        layout_esquerda = QVBoxLayout()
        layout_esquerda.setSpacing(5)
        
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
        layout_imagens.setSpacing(4) 
        # Não usamos QGridLayout pois QHBoxLayout lida melhor com stretch igual

        # --- Coluna Esquerda (User) ---
        layout_col_user = QVBoxLayout()
        
        lbl_titulo_user = QLabel("Imagem Pesquisada")
        lbl_titulo_user.setStyleSheet("font-weight: bold; color: #374151; font-size: 11px; margin-bottom: 2px;")
        layout_col_user.addWidget(lbl_titulo_user)

        self.card_user = ImageCardWidget()
        self.card_user.set_placeholder("Arraste e solte uma foto aqui\n\nou clique para selecionar")
        self.card_user.set_on_drop(self._carregar_imagem)
        self.card_user.set_on_click(self._abrir_seletor_arquivo)
        
        layout_col_user.addWidget(self.card_user, stretch=1) # Stretch vertical para o card

        self.btn_google_lens = QPushButton("Pesquisar com Google Lens")
        self.btn_google_lens.setCursor(Qt.PointingHandCursor)
        self.btn_google_lens.setEnabled(False)
        # Estilo global será aplicado
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
        # Estilo global será aplicado
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
        
        # --- Botão Definir Localização Manualmente (v0.3.8 - Persistente e Estilizado) ---
        self.btn_set_location = QPushButton("Definir Localização Manualmente")
        self.btn_set_location.setCursor(Qt.PointingHandCursor)
        self.btn_set_location.setVisible(True) # Sempre visível agora
        self.btn_set_location.clicked.connect(self._abrir_dialogo_localizacao)
        
        # Estilo Padronizado (Dark Gray) - Igual aos outros botões de ação
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
        layout_esquerda.addWidget(self.btn_set_location)
        
        # --- Painel de Informações Geo (v0.3.11) ---
        self.lbl_geo_details = QLabel()
        self.lbl_geo_details.setWordWrap(True)
        self.lbl_geo_details.setTextFormat(Qt.RichText)
        self.lbl_geo_details.setStyleSheet("""
            QLabel {
                background-color: #F3F4F6;
                border-radius: 8px;
                padding: 10px;
                color: #374151;
                font-size: 13px;
                border: 1px solid #E5E7EB;
                margin-top: 5px;
            }
        """)
        self.lbl_geo_details.setVisible(False) # Só mostra quando tiver dados
        layout_esquerda.addWidget(self.lbl_geo_details)
        # -------------------------------------------------------
        
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
        layout_direito.setSpacing(15)
        layout_direito.setContentsMargins(12, 18, 12, 12)
        
        # Grupo Resultados
        grupo_resultados = QGroupBox("") 
        layout_res = QVBoxLayout()
        layout_res.setSpacing(8)
        
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

        # --- NOVO: Card Informações Geográficas (v0.3.5) ---
        grupo_geo = QGroupBox("")
        grupo_geo.setStyleSheet("margin-top: 10px; padding-top: 10px;")
        layout_geo = QVBoxLayout()
        
        lbl_titulo_geo_card = QLabel("Informações Geográficas")
        lbl_titulo_geo_card.setStyleSheet("font-weight: bold; color: #374151; font-size: 11px; margin-bottom: 4px;")
        layout_geo.addWidget(lbl_titulo_geo_card)
        
        self.lbl_geo_placeholder = QLabel("Localização não detectada")
        self.lbl_geo_placeholder.setAlignment(Qt.AlignCenter)
        self.lbl_geo_placeholder.setStyleSheet("color: #9CA3AF; font-style: italic; border: 1px dashed #D1D5DB; border-radius: 4px; padding: 20px;")
        layout_geo.addWidget(self.lbl_geo_placeholder)
        
        grupo_geo.setLayout(layout_geo)
        layout_res.addWidget(grupo_geo)
        # ---------------------------------------------------
        
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
        
        # --- Extração de Metadados (EXIF) v0.3.12 ---
        autor_exif = "Autor desconhecido"
        data_exif = "Data não disponível"
        
        try:
            with Image.open(caminho) as img:
                exif_data = img._getexif()
                if exif_data:
                    # Mapear Tags (Código -> Nome)
                    exif = {ExifTags.TAGS.get(k, k): v for k, v in exif_data.items()}
                    
                    # 1. Autor
                    # Tags comuns: Artist (315), XPAuthor (40093 - Windows)
                    # XPAuthor é codificado em bytes UCS-2 (UTF-16LE)
                    artist = exif.get("Artist")
                    xp_author = exif.get("XPAuthor")
                    
                    if artist:
                         autor_exif = str(artist).strip()
                    elif xp_author:
                         try:
                             # XP tags geralmente são bytes com null terminator
                             autor_exif = xp_author.decode("utf-16le").replace('\x00', '').strip()
                         except:
                             pass
                    
                    if not autor_exif:
                         autor_exif = "Autor desconhecido"
                         
                    # 2. Data
                    # Tag: DateTimeOriginal (36867) -> formato "YYYY:MM:DD HH:MM:SS"
                    date_str = exif.get("DateTimeOriginal")
                    if date_str:
                         try:
                             dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                             data_exif = dt.strftime("%d/%m/%Y - %H:%M")
                         except:
                             pass
                             
        except Exception as e:
            # Silently fail for metadata, defaults are set
            # print(f"Erro ao ler EXIF: {e}") 
            pass

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
                self.map_principal.update_map(lat, lon, zoom=10, add_marker=True)
                
            # Atualiza card geo
            self.lbl_geo_placeholder.setText(f"Lat: {lat:.4f}, Lon: {lon:.4f} (GPS)")
            self.lbl_geo_placeholder.setStyleSheet("color: #374151; font-weight: bold; border: none;")
            
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
                 self.lbl_geo_placeholder.setText(msg_erro)
                 self.lbl_geo_placeholder.setStyleSheet("color: #9CA3AF; font-style: italic; border: 1px dashed #D1D5DB; border-radius: 4px; padding: 20px;")
             
        self._identificar_ave()

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
                    self.map_principal.update_map(lat, lon, zoom=10, add_marker=True, scientific_name=sciname)
                
                # Atualizar card geográfico
                self.lbl_geo_placeholder.setText(f"Lat: {lat:.4f}, Lon: {lon:.4f} (Manual)")
                self.lbl_geo_placeholder.setStyleSheet("color: #374151; font-weight: bold; border: none;")
                
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
        print("\n[UI] --- INICIANDO ATUALIZAÇÃO DA INTERFACE ---")
        print(f"[UI] Dados recebidos do WikiAves. Link: {dados.get('link_origem')}")
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
        self.status_bar.showMessage("Erro na identificação.")
        self.card_user.setAcceptDrops(True)
        self.lbl_nome_comum.setText("Erro")
        self.lbl_descricao.setText(erro_msg)
        self.lbl_etimologia_texto.setText("Ocorreu um erro durante a identificação local.")
        
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
        if not hasattr(self, 'lbl_geo_details'):
             return

        texto = f"""
        <b>Local:</b> {details.get('cidade','-')} - {details.get('estado','-')}<br>
        <b>Bioma:</b> {details.get('bioma','-')} 🌿<br>
        <span style='font-size:11px; color:#6B7280;'>{details.get('localidade','')}</span>
        """
        self.lbl_geo_details.setText(texto)

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
        if self.map_principal:
             self.map_principal.show_placeholder_message("Aguardando dados de Localização")
        self.status_bar.showMessage("Pronto (Local)")
