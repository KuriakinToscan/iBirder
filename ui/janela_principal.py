import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QFileDialog, QLineEdit,
    QFrame, QStatusBar, QApplication, QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QFont, QDragEnterEvent, QDropEvent, QIcon, QPainter, QColor

# Importações do Core
from core.identificador_local import IdentificadorLocal
from core.identificador_nuvem import IdentificadorNuvem
from core.servico_identificacao import ServicoIdentificacao
from core.motor_metadados import MotorMetadados
from core.erros import ChaveApiFaltandoErro, ErroArquivoInvalido
from core.config import carregar_config
from ui.wizard_config import WizardConfig
from ui.janela_config import JanelaConfig # v0.3.2
from ui.dialogo_aviso import DialogoAviso # v0.3.7
import keyring

class AreaDrop(QLabel):
    def __init__(self, callback_arquivo_carregado):
        super().__init__()
        self.callback = callback_arquivo_carregado
        self.setText("Arraste e solte uma foto aqui\n\nou clique para selecionar")
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumSize(450, 450)
        self.setProperty("class", "dropzone") # Para QSS
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

class JanelaPrincipal(QMainWindow):
    def __init__(self, nome_icone_janela="logo_ave.png", modo_inicial="offline"):
        super().__init__()
        self.nome_icone_janela = nome_icone_janela
        self.modo_atual = modo_inicial # "online" ou "offline" Recebido do main
        
        self.setWindowTitle(f"iBirder - Modo {self.modo_atual.capitalize()}")
        self.resize(1100, 700)
        
        # Inicialização dos Serviços
        self.id_local = IdentificadorLocal()
        self.id_nuvem = IdentificadorNuvem()
        self.servico = ServicoIdentificacao(self.id_local) 
        self.motor_metadados = MotorMetadados()
        
        # Configura estratégia inicial
        self._definir_estrategia(self.modo_atual)
        
        self.caminho_imagem_atual = None
        self.dados_identificacao_atual = {}

        self._configurar_ui()
        self._aplicar_estilo()

    def _definir_estrategia(self, modo):
        self.modo_atual = modo
        if modo == "online":
            self.servico.definir_estrategia(self.id_nuvem)
            self.setWindowTitle("iBirder - Modo Online")
        else:
            self.servico.definir_estrategia(self.id_local)
            self.setWindowTitle("iBirder - Modo Offline")
            
        # Atualiza UI se existir
        if hasattr(self, 'lbl_modo_status'):
             self.lbl_modo_status.setText(f"MODO: {modo.upper()}")

    def _obter_caminho_asset(self, nome_arquivo):
        """Retorna o caminho correto para assets (dev ou frozen)."""
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

        # --- LADO ESQUERDO (Drop Zone + Logo) ---
        layout_esquerda = QVBoxLayout()
        layout_esquerda.setSpacing(20)
        
        # Logo
        caminho_logo_painel = self._obter_caminho_asset("logo_ave.png")
        if os.path.exists(caminho_logo_painel):
            lbl_logo = QLabel()
            pixmap_logo = QPixmap(caminho_logo_painel)
            lbl_logo.setPixmap(pixmap_logo.scaled(170, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            layout_esquerda.addWidget(lbl_logo, alignment=Qt.AlignLeft)
        else:
            lbl_logo = QLabel("iBirder")
            lbl_logo.setFont(QFont("Segoe UI Light", 32))
            lbl_logo.setStyleSheet("color: #222222;")
            layout_esquerda.addWidget(lbl_logo)

        # Ícone da Janela
        caminho_icone_janela = self._obter_caminho_asset(self.nome_icone_janela)
        if os.path.exists(caminho_icone_janela):
            self.setWindowIcon(QIcon(caminho_icone_janela))
        else:
             if os.path.exists(caminho_logo_painel):
                 self.setWindowIcon(QIcon(caminho_logo_painel))

        self.area_drop = AreaDrop(self._carregar_imagem)
        layout_esquerda.addWidget(self.area_drop)
        
        # Botão Reset / Nova Identificação (v0.3.8)
        self.btn_nova = QPushButton("Nova Identificação")
        self.btn_nova.setCursor(Qt.PointingHandCursor)
        self.btn_nova.setToolTip("Limpar imagem e começar de novo")
        self.btn_nova.setProperty("class", "reset-btn") # Novo estilo
        self.btn_nova.clicked.connect(self._resetar_interface)
        layout_esquerda.addWidget(self.btn_nova)
        
        lbl_instrucao = QLabel("Suporte a JPG, PNG")
        lbl_instrucao.setStyleSheet("color: #616161; font-size: 11px;")
        layout_esquerda.addWidget(lbl_instrucao, alignment=Qt.AlignCenter)

        layout_principal.addLayout(layout_esquerda, stretch=3)

        # --- LADO DIREITO (Painel de Controle) ---
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
        
        # Cabeçalho do Painel (Título + Engrenagem)
        layout_cabecalho = QHBoxLayout()
        
        lbl_controle = QLabel("Identificação")
        lbl_controle.setFont(QFont("Segoe UI Semibold", 20))
        lbl_controle.setStyleSheet("color: #222222; border: none; background: transparent;")
        layout_cabecalho.addWidget(lbl_controle)
        
        layout_cabecalho.addStretch()
        
        # Botão Configurações (Engrenagem) v0.3.2/v0.3.7
        self.btn_config = QPushButton()
        self.btn_config.setFixedSize(40, 40)
        self.btn_config.setToolTip("Configurações")
        self.btn_config.setProperty("class", "icon-btn")
        
        caminho_gear = self._obter_caminho_asset("config_gear.png")
        if os.path.exists(caminho_gear):
            self.btn_config.setIcon(QIcon(caminho_gear))
            self.btn_config.setIconSize(QSize(24, 24))
        else:
            self.btn_config.setText("⚙️") # Fallback
            
        self.btn_config.clicked.connect(self._abrir_configuracoes)
        layout_cabecalho.addWidget(self.btn_config)
        
        layout_direito.addLayout(layout_cabecalho)
        
        # Indicador de Modo
        self.lbl_modo_status = QLabel(f"MODO: {self.modo_atual.upper()}")
        self.lbl_modo_status.setAlignment(Qt.AlignCenter)
        self.lbl_modo_status.setStyleSheet("""
            background-color: #EEEEEE; 
            color: #616161; 
            border-radius: 4px; 
            padding: 5px; 
            font-weight: bold; 
            font-size: 10px; 
            letter-spacing: 1px;
        """)
        layout_direito.addWidget(self.lbl_modo_status)

        # Painel de Resultados
        grupo_resultados = QGroupBox("RESULTADOS")
        layout_res = QVBoxLayout()
        layout_res.setSpacing(15)
        
        # Layout Horizontal para Busca (v0.4.0)
        layout_busca = QHBoxLayout()
        layout_busca.setSpacing(10)

        self.input_nome_cientifico = QLineEdit()
        self.input_nome_cientifico.setPlaceholderText("Digite o nome científico...")
        self.input_nome_cientifico.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.input_nome_cientifico.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 5px;
                color: #222222;
                background-color: #FAFAFA;
                font-style: italic; /* v0.5.0 */
            }
            QLineEdit:focus {
                border: 1px solid #444444;
                background-color: #FFFFFF;
            }
        """)
        
        self.btn_buscar = QPushButton()
        self.btn_buscar.setFixedSize(36, 36)
        self.btn_buscar.setToolTip("Buscar Espécie")
        self.btn_buscar.setProperty("class", "search-btn")
        
        caminho_lupa = self._obter_caminho_asset("search_loupe.png")
        if os.path.exists(caminho_lupa):
            self.btn_buscar.setIcon(QIcon(caminho_lupa))
            self.btn_buscar.setIconSize(QSize(20, 20))
        else:
            self.btn_buscar.setText("🔍")
            
        self.btn_buscar.clicked.connect(self._buscar_especie_manual)
        
        layout_busca.addWidget(self.input_nome_cientifico)
        layout_busca.addWidget(self.btn_buscar)

        layout_res.addWidget(QLabel("Espécie (Editável):"))
        layout_res.addLayout(layout_busca)
        
        self.lbl_nome_comum = QLabel("-")
        self.lbl_nome_comum.setFont(QFont("Segoe UI", 13))
        self.lbl_nome_comum.setStyleSheet("color: #424242; background: transparent; border: none;")
        self.lbl_nome_comum.setWordWrap(True)
        
        self.lbl_confianca = QLabel("-")
        self.lbl_confianca.setStyleSheet("color: #757575; background: transparent; border: none; font-size: 11px;")
        
        self.lbl_descricao = QLabel("-") 
        self.lbl_descricao.setFont(QFont("Segoe UI", 11))
        self.lbl_descricao.setStyleSheet("color: #616161; background: transparent; border: none;")
        self.lbl_descricao.setWordWrap(True)


        layout_res.addWidget(QLabel("Nome Comum:"))
        layout_res.addWidget(self.lbl_nome_comum)
        layout_res.addWidget(QLabel("Descrição:"))
        layout_res.addWidget(self.lbl_descricao)
        layout_res.addWidget(self.lbl_confianca)
        grupo_resultados.setLayout(layout_res)
        layout_direito.addWidget(grupo_resultados)

        layout_direito.addStretch()

        # Botão de Ação
        self.btn_gravar = QPushButton("GRAVAR DADOS")
        self.btn_gravar.setEnabled(False)
        self.btn_gravar.setCursor(Qt.PointingHandCursor)
        self.btn_gravar.setMinimumHeight(60)
        self.btn_gravar.clicked.connect(self._gravar_metadados)
        layout_direito.addWidget(self.btn_gravar)

        layout_principal.addWidget(self.painel_direito, stretch=2)

        # Barra de Status
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Pronto")

    def _aplicar_estilo(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #E0E0E0;
            }
            QFrame.painel {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #BDBDBD;
            }
            QLabel.dropzone {
                border: 2px dashed #424242;
                border-radius: 12px;
                background-color: #EEEEEE;
                color: #616161;
                font-size: 14px;
                font-weight: bold;
            }
            QLabel.dropzone:hover {
                background-color: #E0E0E0;
                border-color: #212121;
                color: #212121;
            }
            QGroupBox {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 20px;
                padding-top: 20px;
                font-weight: bold;
                font-size: 11px;
                background-color: #FFFFFF;
                color: #757575;
                letter-spacing: 1px;
                text-transform: uppercase;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                background-color: #FFFFFF;
            }
            QPushButton {
                background-color: #444444; 
                color: white;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 12px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: #222222; 
            }
            QPushButton:pressed {
                background-color: #000000;
            }
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: #9E9E9E;
                border: 1px solid #BDBDBD;
            }
            QStatusBar {
                background-color: #E0E0E0;
                color: #424242;
                font-size: 11px;
                border-top: 1px solid #BDBDBD;
            }
            /* Botão Ícone (Engrenagem) */
            QPushButton[class="icon-btn"] {
                background-color: transparent;
                color: #444444;
                border: 1px solid transparent;
                font-size: 20px;
                padding: 0;
            }
            QPushButton[class="icon-btn"]:hover {
                background-color: #EEEEEE;
                border: 1px solid #BDBDBD;
                color: #222222;
            }
            /* Botão Reset Clean (v0.3.8) */
            QPushButton[class="reset-btn"] {
                background-color: transparent;
                color: #616161;
                border: 1px solid #E0E0E0;
                font-size: 12px;
                padding: 8px;
                margin-top: 15px; 
            }
            QPushButton[class="reset-btn"]:hover {
                color: #222222;
                border-color: #BDBDBD;
                background-color: #FAFAFA;
            }
            /* Botão Busca (v0.4.0) */
            QPushButton[class="search-btn"] {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
            }
            QPushButton[class="search-btn"]:hover {
                background-color: #F5F5F5;
                border-color: #BDBDBD;
            }
        """)

    def _abrir_configuracoes(self):
        janela_cfg = JanelaConfig(self)
        if janela_cfg.exec(): # Se salvou (exec retorna 1/True)
            # Recarregar config e aplicar
            nova_config = carregar_config()
            novo_modo = nova_config.get("modo_operacao")
            
            if novo_modo and novo_modo != self.modo_atual:
                self._alterar_modo_runtime(novo_modo)
                DialogoAviso("Modo Atualizado", f"A aplicação agora está operando no modo: {novo_modo.upper()}", self).exec()

    def _alterar_modo_runtime(self, novo_modo):
        if novo_modo == "online":
             if not keyring.get_password("iBirder_Gemini_Key", "user"):
                 DialogoAviso("Falta Chave", "Configure a chave primeiro no menu de opções.", self).exec()
                 return
        
        self._definir_estrategia(novo_modo)
        if self.caminho_imagem_atual:
            self._identificar_ave()

    def _carregar_imagem(self, caminho: str):
        self.caminho_imagem_atual = caminho
        
        original_pixmap = QPixmap(caminho)
        if not original_pixmap.isNull():
            scaled_pixmap = original_pixmap.scaled(
                self.area_drop.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.area_drop.setPixmap(scaled_pixmap)
            self.area_drop.setText("") 
        
        self.status_bar.showMessage(f"Imagem: {Path(caminho).name}")
        self._identificar_ave()

    def _identificar_ave(self):
        if not self.caminho_imagem_atual:
            return

        if not self.caminho_imagem_atual:
            return
 
        self.input_nome_cientifico.setText("...")
        self.lbl_nome_comum.setText("...")
        self.lbl_confianca.setText("")
        self.lbl_descricao.setText("-")
        self.btn_gravar.setEnabled(False)
        self.dados_identificacao_atual = {}
        
        if self.modo_atual == "online":
            self.status_bar.showMessage("Analisando ave com IA...")
        else:
            self.status_bar.showMessage("Identificando...")
        
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents() 

        try:
            resultado = self.servico.identificar(self.caminho_imagem_atual)
            
            if "erro" in resultado:
                DialogoAviso("Aviso", resultado["erro"], self).exec()
                self.input_nome_cientifico.setText("Falha")
                self.lbl_nome_comum.setText("-")
                self.lbl_confianca.setText("")
                self.lbl_descricao.setText(f"Erro: {resultado.get('detalhes', '-')}")
                self.status_bar.showMessage("Falha na identificação.")
                return

            descricao = "-"

            if "melhor_taxa" in resultado: # Resposta Local
                dados = resultado["melhor_taxa"]
                nome_cientifico = dados.get("nome_cientifico", "?")
                confianca = dados.get("confianca", 0.0)
                conf_str = f"Confiança: {confianca:.1%}"
                nome_comum = "Não disponível (Offline)" 
            else: # Resposta Nuvem e Local devolvem estruturas diferentes?
                # Ajuste: se for nuvem padronizada
                dados = resultado
                nome_cientifico = dados.get("nome_cientifico", "?")
                nome_comum = dados.get("nome_comum", "-")
                confianca = dados.get("confianca", 0.0)
                conf_str = f"Confiança: {confianca:.1%}" if isinstance(confianca, float) else str(confianca)
                descricao = dados.get("descricao", "-")

            self.input_nome_cientifico.setText(f"{nome_cientifico}")
            self.lbl_nome_comum.setText(f"{nome_comum}")
            self.lbl_confianca.setText(conf_str)
            self.lbl_descricao.setText(descricao)
            
            self.dados_identificacao_atual = {
                "nome_cientifico": nome_cientifico,
                "nome_comum": nome_comum,
                "fonte": "iBirder AI",
                "descricao": descricao
            }
            self.btn_gravar.setEnabled(True)
            self.status_bar.showMessage("Concluído.")

        except ChaveApiFaltandoErro:
            DialogoAviso("Chave de API", "Chave não encontrada. Configure no menu.", self).exec()
            # Fallback para offline
            self._alterar_modo_runtime("offline")
        except Exception as e:
            DialogoAviso("Erro", f"Erro: {str(e)}", self).exec()
            self.status_bar.showMessage("Erro fatal.")
        finally:
            QApplication.restoreOverrideCursor()

    def _gravar_metadados(self):
        if not self.caminho_imagem_atual or not self.dados_identificacao_atual:
            return

        self.status_bar.showMessage("Gravando...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            self.motor_metadados.inserir_metadados(
                self.caminho_imagem_atual, 
                self.dados_identificacao_atual
            )
            DialogoAviso("Sucesso", "Metadados gravados com sucesso na imagem!", self).exec()
            
            self.status_bar.showMessage("Gravado com sucesso.")
        except ErroArquivoInvalido as e:
            DialogoAviso("Erro de Arquivo", str(e), self).exec()
        except RuntimeError as e:
             DialogoAviso("Erro no ExifTool", str(e), self).exec()
        except Exception as e:
             DialogoAviso("Erro", f"Falha: {str(e)}", self).exec()
        finally:
             QApplication.restoreOverrideCursor()

    def _resetar_interface(self):
        """Limpa a interface para uma nova identificação (v0.3.8/v0.3.9)."""
        self.caminho_imagem_atual = None
        self.dados_identificacao_atual = {}
        
        # Reseta Área de Imagem
        self.area_drop.setPixmap(QPixmap()) # Limpa imagem
        self.area_drop.setText("Arraste e solte uma foto aqui\n\nou clique para selecionar")
        
        # Reseta Labels
        self.input_nome_cientifico.clear() # v0.4.0
        self.lbl_nome_comum.setText("-")
        self.lbl_confianca.setText("-")
        self.lbl_descricao.setText("-")
        
        self.btn_gravar.setEnabled(False)
        self.status_bar.showMessage("Pronto")

    def _buscar_especie_manual(self):
        """Busca manual via texto, Híbrida (v0.5.0)."""
        nome = self.input_nome_cientifico.text().strip()
        if not nome or len(nome) < 3:
            DialogoAviso("Busca Inválida", "Digite pelo menos 3 caracteres.", self).exec()
            return

        self.status_bar.showMessage(f"Buscando informações sobre {nome}...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.btn_buscar.setEnabled(False)
        QApplication.processEvents()
        
        try:
            if self.modo_atual == "online":
                resultado = self.id_nuvem.consultar_especie(nome)
            else:
                # Modo Offline (v0.5.0)
                resultado = self.id_local.consultar_especie(nome)
            
            if "erro" in resultado:
                if self.modo_atual != "online":
                    sugestao = " Conecte-se para uma busca completa."
                    DialogoAviso("Não Encontrado", resultado["erro"] + sugestao, self).exec()
                else:
                    DialogoAviso("Não Encontrado", resultado["erro"], self).exec()
                    
                self.status_bar.showMessage("Espécie não encontrada.")
            else:
                # Preencher dados
                # Nota: O input já está em itálico pelo CSS
                self.lbl_nome_comum.setText(resultado.get("nome_comum", "-"))
                self.lbl_descricao.setText(resultado.get("descricao", "-"))
                self.lbl_confianca.setText(resultado.get("confianca", "Validado Manualmente"))
                
                # Atualizar dados para gravação (Metadados sem formatação visual)
                self.dados_identificacao_atual = {
                    "nome_cientifico": resultado.get("nome_cientifico"),
                    "nome_comum": resultado.get("nome_comum"),
                    "fonte": "Busca Manual " + ("(Online)" if self.modo_atual == "online" else "(Local)"),
                    "descricao": resultado.get("descricao")
                }
                self.btn_gravar.setEnabled(True)
                self.status_bar.showMessage("Busca concluída.")
                
        except Exception as e:
            DialogoAviso("Erro na Busca", str(e), self).exec()
        finally:
             QApplication.restoreOverrideCursor()
             self.btn_buscar.setEnabled(True)
