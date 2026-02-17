import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QFileDialog, QLineEdit,
    QFrame, QStatusBar, QApplication, QSizePolicy, QGraphicsDropShadowEffect,
    QMessageBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QFont, QDragEnterEvent, QDropEvent, QIcon, QColor, QPainter, QAction, QDesktopServices

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
    def __init__(self, nome_icone_janela="logo_ave.svg", modo_inicial="online", ai_status="READY"):
        super().__init__()
        self.nome_icone_janela = nome_icone_janela
        self.ai_status = ai_status
        
        self.setWindowTitle("iBirder (Offline/Local)")
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
        
        caminho_logo_painel = self._obter_caminho_asset("logo_ave.svg")
        if os.path.exists(caminho_logo_painel):
            lbl_logo = QLabel()
            pixmap_logo = QIcon(caminho_logo_painel).pixmap(QSize(170, 70))
            lbl_logo.setPixmap(pixmap_logo)
            layout_esquerda.addWidget(lbl_logo, alignment=Qt.AlignLeft)
        else:
            lbl_logo = QLabel("iBirder")
            lbl_logo.setFont(QFont("Segoe UI Light", 32))
            layout_esquerda.addWidget(lbl_logo)

        caminho_icone_janela = self._obter_caminho_asset(self.nome_icone_janela)
        if os.path.exists(caminho_icone_janela):
            self.setWindowIcon(QIcon(caminho_icone_janela))

        # Layout de Comparação Lado a Lado
        layout_imagens = QHBoxLayout()
        layout_imagens.setSpacing(15)

        self.area_drop = AreaDrop(self._carregar_imagem)
        layout_imagens.addWidget(self.area_drop, stretch=1)
        
        # Wrapper vertical para imagem de referência + créditos
        layout_ref_wrapper = QVBoxLayout()
        layout_ref_wrapper.setSpacing(5)
        
        self.area_referencia = AreaReferencia()
        layout_ref_wrapper.addWidget(self.area_referencia)
        
        self.lbl_referencia_creditos = QLabel("")
        self.lbl_referencia_creditos.setAlignment(Qt.AlignRight)
        self.lbl_referencia_creditos.setStyleSheet("color: #6B7280; font-size: 10px;")
        layout_ref_wrapper.addWidget(self.lbl_referencia_creditos)
        
        layout_imagens.addLayout(layout_ref_wrapper, stretch=1)
        
        layout_esquerda.addLayout(layout_imagens)
        
        # Botão Google Lens (Permanente)
        self.btn_google_lens = QPushButton("Pesquisar com Google Lens 🔍")
        self.btn_google_lens.setCursor(Qt.PointingHandCursor)
        self.btn_google_lens.setEnabled(False) # Habilita ao carregar imagem
        self.btn_google_lens.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #374151;
                border: 1px solid #d1d5db;
            }
            QPushButton:hover {
                background-color: #f3f4f6;
            }
        """)
        self.btn_google_lens.clicked.connect(self._abrir_google_lens)
        layout_esquerda.addWidget(self.btn_google_lens)
        
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
        lbl_controle = QLabel("Identificação Local")
        lbl_controle.setFont(QFont("Segoe UI Semibold", 20))
        layout_cabecalho.addWidget(lbl_controle)
        
        layout_cabecalho.addStretch()
        
        # Botão Ajuda
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
        grupo_resultados = QGroupBox("RESULTADOS (IA LOCAL)")
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

        layout_res.addWidget(QLabel("Nome Científico (IA):"))
        self.lbl_nome_cientifico = QLabel("-") # Novo label explicito
        self.lbl_nome_cientifico.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout_res.addWidget(self.lbl_nome_cientifico)

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
        layout_principal.addWidget(self.painel_direito, stretch=2)

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

    def _abrir_google_lens(self):
        # Abre a página do Google Lens (ou Images) para o usuário fazer upload manual
        # Infelizmente não há API pública simples para upload direto local -> web via GET.
        QDesktopServices.openUrl("https://lens.google.com/")

    def _carregar_imagem(self, caminho: str):
        self.caminho_imagem_atual = caminho
        pixmap = QPixmap(caminho)
        if not pixmap.isNull():
            self.area_drop.setPixmap(pixmap.scaled(self.area_drop.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        self.status_bar.showMessage(f"Imagem: {Path(caminho).name}")
        self.btn_google_lens.setEnabled(True) # Habilita o botão do Lens
        self._identificar_ave()

    def _identificar_ave(self):
        if not self.caminho_imagem_atual:
            return

        # Check AI Status (v0.16.1)
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
        self.lbl_nome_cientifico.setText("...")
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
        sci = dados.get("nome_cientifico", "")
        desc = dados.get("descricao", "")
        conf = dados.get("confianca", 0.0)
        status_msg = dados.get("status_msg", "")
        
        # 1. Atualizar Textos
        self.lbl_nome_comum.setText(nc)
        self.lbl_nome_cientifico.setText(sci)
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
            
            # Instrução Adicional (já está na descrição, mas reforçamos se precisar)
            if "Google Lens" not in desc:
                 self.lbl_descricao.setText(f"{desc}\n\nDica: Tente o botão do Google Lens abaixo.")

        else:
            # Modo Sucesso
            self.lbl_confianca.setText(f"{conf*100:.1f}%")
            self.lbl_confianca.setStyleSheet("color: #059669") # Verde
            self.status_bar.showMessage("Identificação concluída.")
            
            # Reativar botões
            self.btn_wiki.setVisible(True)
            self.btn_google.setVisible(True)
            self.btn_ebird.setVisible(True)
            
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

    def _resetar_interface(self):
        self.caminho_imagem_atual = None
        self.area_referencia.setText("Referência")
        self.area_referencia.setPixmap(QPixmap())
        self.area_drop.setPixmap(QPixmap())
        self.area_drop.setText("Arraste e solte uma foto aqui\n\nou clique para selecionar")
        self.lbl_nome_cientifico.setText("-")
        self.lbl_nome_comum.setText("-")
        self.lbl_descricao.setText("-")
        self.lbl_confianca.setText("-")
        self.frame_etimologia.setVisible(False) 
        self.btn_google_lens.setEnabled(False)
        self.status_bar.showMessage("Pronto (Local)")
