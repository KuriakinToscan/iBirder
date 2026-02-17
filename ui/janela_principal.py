import sys
import os
import requests
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QFileDialog, QLineEdit,
    QFrame, QStatusBar, QApplication, QSizePolicy, QGraphicsDropShadowEffect,
    QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt, QSize, QThread, Signal, QSettings, QMimeData, QUrl
from PySide6.QtGui import (
    QPixmap, QFont, QDragEnterEvent, QDropEvent, QIcon, QColor, 
    QPainter, QAction, QDesktopServices, QDrag
)

# Importações do Core
from core.local_worker import LocalIdentificationWorker
# from core.config import carregar_config # Removido se não for usar
from ui.janela_manual import JanelaManual
from ui.dialogo_aviso import DialogoAviso
from ui.worker_referencia import ReferenceImageWorker
from core.wikiaves_worker import WikiAvesWorker
import logging
from core.logger import save_crash_log

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
        self.caminho_imagem = None
        self.drag_start_pos = None

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            caminho = urls[0].toLocalFile()
            self.callback(caminho)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.caminho_imagem:
                self.drag_start_pos = event.position().toPoint()
            else:
                self.drag_start_pos = None
                settings = QSettings("iBirder", "App")
                last_folder = settings.value("last_folder", "")
                
                path, _ = QFileDialog.getOpenFileName(
                    self, "Selecionar Foto", last_folder, "Imagens (*.png *.jpg *.jpeg)"
                )
                if path:
                    self.callback(path)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self.caminho_imagem or not self.drag_start_pos:
            return
            
        if (event.position().toPoint() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
            
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Otimização de Imagem para Google Lens (Limite 20MB)
        caminho_final = self.caminho_imagem
        try:
            tamanho_mb = os.path.getsize(self.caminho_imagem) / (1024 * 1024)
            if tamanho_mb > 15: # Margem de segurança (Google aceita até 20MB)
                print(f"[Drag] Imagem grande ({tamanho_mb:.1f}MB). Comprimindo para temp...")
                
                # Cria temp path mantendo extensão ou forçando jpg
                import tempfile
                temp_dir = tempfile.gettempdir()
                nome_temp = f"ibirder_lens_optimized_{os.path.basename(self.caminho_imagem)}"
                caminho_temp = os.path.join(temp_dir, nome_temp)
                
                # Comprime
                pixmap_full = QPixmap(self.caminho_imagem)
                if not pixmap_full.isNull():
                    # Salva como JPEG com qualidade 85
                    pixmap_full.save(caminho_temp, "JPG", 85)
                    caminho_final = caminho_temp
                    print(f"[Drag] Imagem comprimida salva em: {caminho_final}")
        except Exception as e:
            print(f"[Drag] Erro na otimização: {e}")
            caminho_final = self.caminho_imagem
            
        mime_data.setUrls([QUrl.fromLocalFile(caminho_final)])
        drag.setMimeData(mime_data)
        
        pixmap = self.pixmap()

        if pixmap:
            drag.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
        drag.exec(Qt.CopyAction)

class AreaReferencia(QLabel):
    def __init__(self):
        super().__init__()
        self.setText("Referência")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(250, 250)
        self.setProperty("class", "referencia")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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
        self._aplicar_estilo()

    def _obter_caminho_asset(self, nome_arquivo):
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent / 'assets'
        return str(base_path / nome_arquivo)

    def _iniciar_busca_imagem(self, nome_cientifico):
        # Reset visual
        # Não sobrescrever texto se já estiver "aguardando identificação..."
        if not self.area_referencia.text().startswith("aguardando"):
             self.area_referencia.setText("Buscando ref...")
             
        self.area_referencia.setPixmap(QPixmap())
        self.lbl_referencia_creditos.setText("")
        
        self.frame_etimologia.setVisible(False) # Reset etimologia

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
        self.worker_referencia.search_failed.connect(lambda: self.area_referencia.setText("Sem referência"))
        self.worker_referencia.start()
        
        # Iniciar etimologia também
        self._iniciar_busca_etimologia(nome_cientifico)

    def _iniciar_busca_etimologia(self, nome_cientifico):
        if getattr(self, "worker_wiki", None) is not None:
             try:
                 if self.worker_wiki.isRunning():
                     self.worker_wiki.quit()
                     self.worker_wiki.wait()
                 self.worker_wiki.deleteLater()
             except: pass

        self.worker_wiki = WikiAvesWorker(nome_cientifico)
        self.worker_wiki.etymology_found.connect(self._ao_encontrar_etimologia)
        self.worker_wiki.error_occurred.connect(self._ao_erro_wikiaves)
        self.worker_wiki.start()

    def _ao_encontrar_imagem_referencia(self, path, creditos):
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.area_referencia.setPixmap(pixmap.scaled(self.area_referencia.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.area_referencia.setText("")
            self.lbl_referencia_creditos.setText(creditos)

    def _ao_encontrar_etimologia(self, dados_ou_texto):
        # Suporte legado e novo (dict)
        if isinstance(dados_ou_texto, dict):
            dados = dados_ou_texto
            etimologia = dados.get("etimologia")
            familia = dados.get("familia")
            ordem = dados.get("ordem")
            nome_ingles = dados.get("nome_ingles")
            conservacao = dados.get("conservacao")
            
            # --- Construção do HTML Rico ---
            html = "<div style='line-height: 1.4;'>"
            
            # 1. Taxonomia (Subtítulo discreto)
            if ordem and familia:
                html += f"<div style='color: #6B7280; font-size: 10px; margin-bottom: 2px;'>{ordem.upper()} • {familia.upper()}</div>"
            
            # 2. Nome em Inglês (Destaque)
            if nome_ingles:
                html += f"<div style='font-weight: bold; font-size: 13px; color: #1F2937; margin-bottom: 4px;'>{nome_ingles}</div>"
            
            # 3. Status de Conservação (Badge Colorido)
            if conservacao:
                cor_bg = "#E5E7EB" # Cinza default
                cor_txt = "#374151"
                
                # Lógica de Cores IUCN
                c_lower = conservacao.lower()
                if "pouco preocupante" in c_lower or "quase ameaçada" in c_lower:
                    cor_bg = "#D1FAE5" # Verde claro
                    cor_txt = "#065F46" # Verde escuro
                elif "vulnerável" in c_lower:
                    cor_bg = "#FEF3C7" # Amarelo
                    cor_txt = "#92400E" # Laranja escuro
                elif "perigo" in c_lower or "ameaçada" in c_lower: # Abrange "Em perigo", "Criticamente..."
                    cor_bg = "#FEE2E2" # Vermelho claro
                    cor_txt = "#991B1B" # Vermelho escuro

                html += f"<span style='background-color: {cor_bg}; color: {cor_txt}; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: bold;'>{conservacao.upper()}</span><br>"
            
            # 4. Etimologia (Texto)
            if etimologia:
                html += f"<div style='margin-top: 8px; font-size: 11px; color: #4B5563;'><i>{etimologia}</i></div>"
            
            html += "</div>"
            
            self.lbl_etimologia_texto.setText(html)
            # Título dinâmico não existe como atributo direto na classe atual (lbl_titulo é local no _configurar_ui), 
            # então mantemos apenas o texto rico.
            
            # Atualiza nome comum se disponível e ainda não definido
            if dados.get("nome_comum"):
                # Opcional: atualizar o nome comum se a IA não deu um bom
                pass

        else:
            # Legado (str)
            self.lbl_etimologia_texto.setText(dados_ou_texto)
            
        self.frame_etimologia.setVisible(True)

    def _ao_erro_wikiaves(self, erro_msg):
        self.lbl_etimologia_texto.setText(erro_msg)
        self.frame_etimologia.setVisible(True)

    def _configurar_ui(self):
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout_principal = QHBoxLayout(widget_central)
        layout_principal.setContentsMargins(30, 30, 30, 30)
        layout_principal.setSpacing(30)

        # --- LADO ESQUERDO ---
        layout_esquerda = QVBoxLayout()
        layout_esquerda.setSpacing(20)
        
        # Branding Header (Icon + Text)
        layout_branding = QHBoxLayout()
        layout_branding.setSpacing(12)
        layout_branding.setAlignment(Qt.AlignLeft)
        
        # Logo Icon
        caminho_logo_painel = self._obter_caminho_asset("logo_ave.svg")
        lbl_logo = QLabel()
        if os.path.exists(caminho_logo_painel):
            pixmap_logo = QIcon(caminho_logo_painel).pixmap(QSize(48, 48))
            lbl_logo.setPixmap(pixmap_logo)
        else:
            lbl_logo.setText("🐦")
            lbl_logo.setFont(QFont("Segoe UI Emoji", 32))
        
        layout_branding.addWidget(lbl_logo)
        
        # Text Column
        layout_textos_header = QVBoxLayout()
        layout_textos_header.setSpacing(0)
        
        lbl_titulo_app = QLabel("iBirder")
        lbl_titulo_app.setStyleSheet("color: #1F2937; font-size: 24px; font-weight: bold; font-family: 'Segoe UI';")
        
        lbl_subtitulo = QLabel("IA para BirdWatching")
        lbl_subtitulo.setStyleSheet("color: #6B7280; font-size: 14px; font-weight: normal; font-family: 'Segoe UI';")
        
        layout_textos_header.addWidget(lbl_titulo_app)
        layout_textos_header.addWidget(lbl_subtitulo)
        
        layout_branding.addLayout(layout_textos_header)
        layout_branding.addStretch() # Push everything to the left
        
        layout_esquerda.addLayout(layout_branding)

        caminho_icone_janela = self._obter_caminho_asset(self.nome_icone_janela)
        if os.path.exists(caminho_icone_janela):
            self.setWindowIcon(QIcon(caminho_icone_janela))

        # Layout de Comparação Lado a Lado
        layout_imagens = QHBoxLayout()
        layout_imagens.setSpacing(15)

        # ---------------------------------------------------------
        # COLUNA 1: Área de Drop + Botão Lens (Largura simétrica)
        # ---------------------------------------------------------
        layout_coluna_esquerda = QVBoxLayout()
        layout_coluna_esquerda.setSpacing(10)

        self.area_drop = AreaDrop(self._carregar_imagem)
        layout_coluna_esquerda.addWidget(self.area_drop)
        
        # Botão Google Lens (Agora dentro da coluna da imagem)
        self.btn_google_lens = QPushButton("Pesquisar com Google Lens")
        self.btn_google_lens.setCursor(Qt.PointingHandCursor)
        self.btn_google_lens.setEnabled(False) # Habilita ao carregar imagem
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
        layout_coluna_esquerda.addWidget(self.btn_google_lens)
        
        layout_imagens.addLayout(layout_coluna_esquerda, stretch=1)
        
        # ---------------------------------------------------------
        # COLUNA 2: Referência + Créditos
        # ---------------------------------------------------------
        layout_ref_wrapper = QVBoxLayout()
        layout_ref_wrapper.setSpacing(5)
        
        self.area_referencia = AreaReferencia()
        layout_ref_wrapper.addWidget(self.area_referencia)
        
        self.lbl_referencia_creditos = QLabel("")
        self.lbl_referencia_creditos.setAlignment(Qt.AlignRight)
        self.lbl_referencia_creditos.setStyleSheet("color: #6B7280; font-size: 10px;")
        layout_ref_wrapper.addWidget(self.lbl_referencia_creditos)
        
        # Espaçador para alinhar com o botão da esquerda? 
        # Não, ReferenceImageWorker não tem botão embaixo, então fica vago ou esticado.
        # Para ficar alinhado no topo, addStretch pode ser util, mas Default é expandir.
        
        layout_imagens.addLayout(layout_ref_wrapper, stretch=1)
        
        layout_esquerda.addLayout(layout_imagens)
        
        self.btn_nova = QPushButton("Nova Identificação")
        self.btn_nova.setCursor(Qt.PointingHandCursor)
        self.btn_nova.clicked.connect(self._abrir_seletor_arquivo)
        layout_esquerda.addWidget(self.btn_nova)
        
        layout_principal.addLayout(layout_esquerda, stretch=3)

        # --- LADO DIREITO (Wrapper) ---
        layout_coluna_direita = QVBoxLayout()
        layout_coluna_direita.setSpacing(10)
        
        # Botão Ajuda (Header Global)
        layout_ajuda = QHBoxLayout()
        layout_ajuda.addStretch()
        
        # Botão Reload (Novo)
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
        
        # Grupo Resultados dentro do Painel
        grupo_resultados = QGroupBox("") # Sem título

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

        layout_res.addWidget(QLabel("Nome Científico:"))

        # Container de Busca Manual
        container_busca = QHBoxLayout()
        container_busca.setContentsMargins(0, 0, 0, 0)
        container_busca.setSpacing(5)
        
        self.input_especie = QLineEdit()
        self.input_especie.setPlaceholderText("pesquise ou digite")
        font_input = QFont("Segoe UI", 12)
        font_input.setItalic(True)
        self.input_especie.setFont(font_input)
        self.input_especie.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                border-bottom: 1px solid #E5E7EB; /* Linha sutil para guiar */
                color: #374151;
                font-style: normal;
            }
            QLineEdit:focus {
                border-bottom: 2px solid #10B981;
            }
        """)
        self.input_especie.returnPressed.connect(self._realizar_busca_manual)
        
        self.btn_search = QPushButton()
        self.btn_search.setCursor(Qt.PointingHandCursor)
        self.btn_search.setFixedSize(32, 32)
        self.btn_search.setStyleSheet("background-color: transparent; border: none;") # Transparente e solto
        
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

        layout_res.addWidget(QLabel("Info:"))
        layout_res.addWidget(self.lbl_descricao)
        layout_res.addWidget(self.lbl_confianca)
        
        # Botões de Busca Externa
        layout_botoes = QHBoxLayout()
        layout_botoes.setSpacing(10)
        
        self.btn_wiki = QPushButton("WikiAves")
        self.btn_wiki.setCursor(Qt.PointingHandCursor)
        self.btn_wiki.setStyleSheet("background-color: #F97316; border: none;") # Orange for WikiAves
        self.btn_wiki.clicked.connect(self._buscar_wikiaves)
        layout_botoes.addWidget(self.btn_wiki)
        
        self.btn_ebird = QPushButton("eBird")
        self.btn_ebird.setCursor(Qt.PointingHandCursor)
        self.btn_ebird.setStyleSheet("background-color: #65A30D; border: none;") # Green for eBird
        self.btn_ebird.clicked.connect(self._buscar_ebird)
        layout_botoes.addWidget(self.btn_ebird)

        self.btn_google = QPushButton("Google")
        self.btn_google.setCursor(Qt.PointingHandCursor)
        self.btn_google.setStyleSheet("background-color: #3B82F6; border: none;") # Blue for Google
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
        # -------------------------------------------
        
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
            
            /* Area Referencia */
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
            # Busca no WikiAves
            url = f"https://www.wikiaves.com.br/index.php?t=s&s={sciname}"
            QDesktopServices.openUrl(url)

    def _buscar_ebird(self):
        sciname = self._obter_sciname_atual()
        if sciname and "Inconclusiva" not in sciname:
            # Busca no Google restringindo ao eBird (mais confiável que url direta sem código)
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
             
        # Atualiza dicionario atual para que os botões externos funcionem com o novo termo
        self.dados_identificacao_atual["nome_cientifico"] = texto
        self.lbl_nome_comum.setText("...")
        
        # Dispara enriquecimento
        self._iniciar_busca_imagem(texto)
        self._iniciar_busca_etimologia(texto)
        
        # Reabilita botões se estavam ocultos (caso venha de um estado Inconclusivo)
        self.btn_wiki.setVisible(True)
        self.btn_google.setVisible(True)
        self.btn_ebird.setVisible(True)

    def _abrir_google_lens(self):
        if not self.caminho_imagem_atual:
             return

        # 1. Copia caminho da imagem para o clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(self.caminho_imagem_atual)
        
        # 2. Abre o Google Lens
        QDesktopServices.openUrl("https://lens.google.com/upload")
        
        # 3. Verifica Persistência "Não exibir novamente"
        settings = QSettings("iBirder", "App")
        dont_show = settings.value("lens_dont_show_again", False, type=bool)
        
        if dont_show:
            return

        # 4. Exibe Instruções Customizadas
        msg = QMessageBox(self)
        msg.setWindowTitle("iBirder - Pesquisa Visual")
        
        # Estilização para garantir fundo claro e texto legível
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
        
        # Checkbox "Não exibir novamente"
        chk_dont_show = QCheckBox("Não exibir esta mensagem novamente", msg)
        msg.setCheckBox(chk_dont_show)
        
        msg.exec()
        
        if chk_dont_show.isChecked():
            settings.setValue("lens_dont_show_again", True)

    def _carregar_imagem(self, caminho: str):
        # 1. Reset da Interface (Limpeza Visual para Nova Identificação)
        self.lbl_nome_comum.setText("-")
        self.lbl_descricao.setText("-")
        self.lbl_confianca.setText("-")
        self.input_especie.clear()
        
        self.area_referencia.setText("Referência")
        self.area_referencia.setPixmap(QPixmap())
        self.lbl_referencia_creditos.setText("")
        
        self.frame_etimologia.setVisible(False)
        self.btn_wiki.setVisible(True) # Mantém visível por padrão ou oculta? O reset original do código apenas limparva textos.
        # Vamos ocultar botões externos até ter resultado, para dar feedback de "novo processo"
        self.btn_wiki.setVisible(False)
        self.btn_google.setVisible(False)
        self.btn_ebird.setVisible(False)

        self.caminho_imagem_atual = caminho
        self.area_drop.caminho_imagem = caminho # Atualiza caminho no widget de drop
        
        # Persistência da pasta
        folder = str(Path(caminho).parent)
        settings = QSettings("iBirder", "App")
        settings.setValue("last_folder", folder)
        
        pixmap = QPixmap(caminho)
        if not pixmap.isNull():
            # Usa SmoothTransformation para garantir alta qualidade visual na UI
            self.area_drop.setPixmap(pixmap.scaled(self.area_drop.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        self.status_bar.showMessage(f"Imagem: {Path(caminho).name}")
        self.btn_google_lens.setEnabled(True) # Habilita o botão do Lens
        self._identificar_ave()

    def _identificar_ave(self):
        if not self.caminho_imagem_atual:
            return

        # Check AI Status (v0.16.1)
        if self.ai_status == 'RESTART_REQUIRED':
             # ... (código existente de restart)
             msg = QMessageBox()
             msg.setIcon(QMessageBox.Information)
             msg.setWindowTitle("Reinicialização Necessária")
             msg.setText("Os componentes de Inteligência Artificial foram instalados com sucesso!\n\nPor favor, feche e abra o iBirder novamente para ativar o novo sistema.")
             msg.addButton("Entendi, vou reiniciar", QMessageBox.AcceptRole)
             msg.exec()
             return

        self.lbl_nome_comum.setText("...")
        self.lbl_descricao.setText("-")
        
        # Garante placeholder visível (não define "..." como texto)
        self.input_especie.clear() 
        
        self.area_referencia.setText("aguardando identificação da espécie...")
        self.status_bar.showMessage("Iniciando IA Local...")
        
        # Desabilita interação básica durante processamento
        self.area_drop.setEnabled(False)
        
        # Inicia Worker Local
        self.worker_local = LocalIdentificationWorker(self.caminho_imagem_atual)
        self.worker_local.progress_updated.connect(self._ao_progresso_identificacao)
        self.worker_local.identification_complete.connect(self._ao_concluir_identificacao)
        self.worker_local.error_occurred.connect(self._ao_erro_identificacao)
        self.worker_local.start()
        
    def _ao_progresso_identificacao(self, mensagem):
        self.status_bar.showMessage(mensagem)

    def _ao_concluir_identificacao(self, resultado):
        self.area_drop.setEnabled(True)
        self._atualizar_info_ave(resultado)

    def _atualizar_info_ave(self, dados: dict):
        self.dados_identificacao_atual = dados
        
        nc = dados.get("nome_comum", "-")
        raw_sci = dados.get("nome_cientifico", "")
        
        # Rigor Taxonômico: Apenas Binômio (Gênero espécie) e sem parênteses
        import re
        # Remove conteúdo entre parenteses/colchetes
        sci_clean = re.sub(r'[\(\[].*?[\)\]]', '', raw_sci)
        # Pega apenas as duas primeiras palavras
        parts = sci_clean.strip().split()
        if len(parts) >= 2:
            sci = f"{parts[0]} {parts[1]}"
        else:
            sci = sci_clean.strip()
            
        desc = dados.get("descricao", "")
        conf = dados.get("confianca", 0.0)
        status_msg = dados.get("status_msg", "")
        
        # 1. Atualizar Textos
        self.lbl_nome_comum.setText(nc)
        
        # O Input de Espécie só deve ser preenchido se houver identificação válida.
        # Nunca preencher com status de erro ou mensagens.
        if "Inconclusiva" not in status_msg and "Baixa" not in status_msg and sci:
            # Aplica itálico ao nome científico confirmado
            self.input_especie.setText(sci)
            font_italic = self.input_especie.font()
            font_italic.setItalic(True)
            self.input_especie.setFont(font_italic)
        else:
             # Mantém limpo para mostrar o placeholder
             self.input_especie.clear()
        
        self.lbl_descricao.setText(desc)
        
        # 2. Atualizar Status Bar e Confiança
        if status_msg == "Baixa confiança":
            self.lbl_confianca.setText(f"{conf*100:.1f}% (Baixa)")
            self.lbl_confianca.setStyleSheet("color: #EF4444") # Vermelho
            self.status_bar.showMessage("Identificação inconclusiva.")
            
            # 3. Mode Inconclusivo: Bloquear Botões Externos
            self.btn_wiki.setVisible(False)
            self.btn_google.setVisible(False)
            self.btn_ebird.setVisible(False)
            
            # Limpar área de referência já que não temos espécie válida
            self.area_referencia.setText("Busca visual suspensa")
            self.area_referencia.setPixmap(QPixmap())
            self.lbl_referencia_creditos.setText("")
            
            # Instrução Fixa (Sobrepõe a do worker para garantir o texto solicitado)
            self.lbl_descricao.setText("Não foi possível identificar com segurança.\n\nTente o botão do Google Lens abaixo para uma análise visual.")
            self.btn_google_lens.setEnabled(True)

        else:
            # Modo Sucesso
            self.lbl_confianca.setText(f"{conf*100:.1f}%")
            self.lbl_confianca.setStyleSheet("color: #059669") # Verde
            self.status_bar.showMessage("Identificação concluída.")
            
            # Reabilita botões
            self.btn_wiki.setVisible(True)
            self.btn_google.setVisible(True)
            self.btn_ebird.setVisible(True)
            
            # (Texto de referência já definido no início do processo)

            # Iniciar Workers de Enriquecimento (WikiAves, Imagens, etc)
            if sci:
                self._iniciar_busca_imagem(sci)
        
        # Log para debug
        if status_msg:
             print(f"[UI] Status de Identificação: {status_msg}")

    def _ao_erro_identificacao(self, erro_msg):
        self.area_drop.setEnabled(True)
        self.status_bar.showMessage("Falha na identificação.")
        DialogoAviso("Erro de Identificação", erro_msg, self).exec()

    def _abrir_seletor_arquivo(self):
        # Garante foco na janela principal antes de abrir o diálogo
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
        # Mantido apenas para compatibilidade se algo ainda chamar, mas btn_nova agora chama seletor e _carregar_imagem faz o reset
        self.caminho_imagem_atual = None
        self.area_referencia.setText("Referência")
        self.area_referencia.setPixmap(QPixmap())
        self.area_drop.setPixmap(QPixmap())
        self.area_drop.setText("Arraste e solte uma foto aqui\n\nou clique para selecionar")
        self.area_drop.caminho_imagem = None
        self.input_especie.clear()
        self.lbl_nome_comum.setText("-")
        self.lbl_descricao.setText("-")
        self.lbl_confianca.setText("-")
        self.frame_etimologia.setVisible(False) 
        self.btn_google_lens.setEnabled(False)
        self.status_bar.showMessage("Pronto (Local)")
