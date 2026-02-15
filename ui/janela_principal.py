import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QRadioButton, QGroupBox, QFileDialog, QMessageBox, 
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
from ui.wizard_config import WizardConfig
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
    def __init__(self, nome_icone_janela="logo_ave.png"):
        super().__init__()
        self.nome_icone_janela = nome_icone_janela
        self.setWindowTitle("iBirder - Identificador de Aves")
        self.resize(1100, 700)
        
        # Inicialização dos Serviços
        self.id_local = IdentificadorLocal()
        self.id_nuvem = IdentificadorNuvem()
        self.servico = ServicoIdentificacao(self.id_local) # Começa Local
        self.motor_metadados = MotorMetadados()
        
        self.caminho_imagem_atual = None
        self.dados_identificacao_atual = {}

        self._configurar_ui()
        self._aplicar_estilo()

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
        # Logo do Painel (Sempre logo_ave.png para identidade visual)
        caminho_logo_painel = self._obter_caminho_asset("logo_ave.png")
        if os.path.exists(caminho_logo_painel):
            lbl_logo = QLabel()
            pixmap_logo = QPixmap(caminho_logo_painel)
            lbl_logo.setPixmap(pixmap_logo.scaled(170, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            layout_esquerda.addWidget(lbl_logo, alignment=Qt.AlignLeft)
        else:
            # Fallback elegante
            lbl_logo = QLabel("iBirder")
            lbl_logo.setFont(QFont("Segoe UI Light", 32))
            lbl_logo.setStyleSheet("color: #222222;")
            layout_esquerda.addWidget(lbl_logo)

        # Ícone da Janela/Barra de Tarefas (Dinâmico)
        caminho_icone_janela = self._obter_caminho_asset(self.nome_icone_janela)
        if os.path.exists(caminho_icone_janela):
            self.setWindowIcon(QIcon(caminho_icone_janela))
        else:
             # Se o dinâmico falhar, tenta o logo padrão
             if os.path.exists(caminho_logo_painel):
                 self.setWindowIcon(QIcon(caminho_logo_painel))

        self.area_drop = AreaDrop(self._carregar_imagem)
        layout_esquerda.addWidget(self.area_drop)
        
        # Instrução sutil
        lbl_instrucao = QLabel("Suporte a JPG, PNG")
        lbl_instrucao.setStyleSheet("color: #616161; font-size: 11px;")
        layout_esquerda.addWidget(lbl_instrucao, alignment=Qt.AlignCenter)

        layout_principal.addLayout(layout_esquerda, stretch=3)

        # --- LADO DIREITO (Painel de Controle) ---
        self.painel_direito = QFrame()
        self.painel_direito.setProperty("class", "painel")
        
        # Sombra sutil no painel
        sombra = QGraphicsDropShadowEffect()
        sombra.setBlurRadius(20)
        sombra.setColor(QColor(0, 0, 0, 20))
        sombra.setOffset(0, 5)
        self.painel_direito.setGraphicsEffect(sombra)

        layout_direito = QVBoxLayout(self.painel_direito)
        layout_direito.setSpacing(30)
        layout_direito.setContentsMargins(25, 35, 25, 25)
        
        # Título do Painel
        lbl_controle = QLabel("Identificação")
        lbl_controle.setFont(QFont("Segoe UI Semibold", 20))
        lbl_controle.setStyleSheet("color: #222222; border: none; background: transparent;")
        layout_direito.addWidget(lbl_controle)

        # Seletor de Modo
        grupo_modo = QGroupBox("MODO DE OPERAÇÃO")
        layout_modo = QVBoxLayout()
        layout_modo.setSpacing(15)
        
        self.radio_local = QRadioButton("Offline (Local AI)")
        self.radio_local.setChecked(True)
        self.radio_local.toggled.connect(self._trocar_modo)
        self.radio_local.setCursor(Qt.PointingHandCursor)
        
        self.radio_nuvem = QRadioButton("Online (Google AI)")
        self.radio_nuvem.toggled.connect(self._trocar_modo)
        self.radio_nuvem.setCursor(Qt.PointingHandCursor)
        
        layout_modo.addWidget(self.radio_local)
        layout_modo.addWidget(self.radio_nuvem)
        grupo_modo.setLayout(layout_modo)
        layout_direito.addWidget(grupo_modo)

        # Painel de Resultados
        grupo_resultados = QGroupBox("RESULTADOS")
        layout_res = QVBoxLayout()
        layout_res.setSpacing(15)
        
        self.lbl_nome_cientifico = QLabel("-")
        self.lbl_nome_cientifico.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.lbl_nome_cientifico.setStyleSheet("color: #222222; background: transparent; border: none;")
        self.lbl_nome_cientifico.setWordWrap(True)
        
        self.lbl_nome_comum = QLabel("-")
        self.lbl_nome_comum.setFont(QFont("Segoe UI", 13))
        self.lbl_nome_comum.setStyleSheet("color: #424242; background: transparent; border: none;")
        self.lbl_nome_comum.setWordWrap(True)
        
        self.lbl_confianca = QLabel("-")
        self.lbl_confianca.setStyleSheet("color: #757575; background: transparent; border: none; font-size: 11px;")
        
        layout_res.addWidget(QLabel("Espécie:"))
        layout_res.addWidget(self.lbl_nome_cientifico)
        layout_res.addWidget(QLabel("Nome Comum:"))
        layout_res.addWidget(self.lbl_nome_comum)
        layout_res.addWidget(self.lbl_confianca)
        grupo_resultados.setLayout(layout_res)
        layout_direito.addWidget(grupo_resultados)

        layout_direito.addStretch()

        # Botão de Ação
        self.btn_gravar = QPushButton("GRAVAR DADOS")
        self.btn_gravar.setEnabled(False) # Só habilita após identificar
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
        # Paleta Industrial/Grafite
        # Fundo: #E0E0E0 (Cinza Claro Industrial)
        # Painel: #F5F5F5 (Quase Branco) ou #FFFFFF
        # Texto: #222222 (Preto Suave/Grafite Profundo)
        # Botão: #444444 (Grafite) -> Hover #222222
        # DropZone: #EEEEEE (Cinza Médio Claro) + Borda #424242
        
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
                color: #757575; /* Label do grupo */
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
                background-color: #444444; /* Grafite */
                color: white;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 12px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: #222222; /* Quase Preto */
            }
            QPushButton:pressed {
                background-color: #000000;
            }
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: #9E9E9E;
                border: 1px solid #BDBDBD;
            }
            QRadioButton {
                color: #222222;
                font-size: 14px;
                padding: 5px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #757575;
                border-radius: 9px;
                background: white;
            }
            QRadioButton::indicator:checked {
                background-color: #222222;
                border: 2px solid #222222;
            }
            QStatusBar {
                background-color: #E0E0E0;
                color: #424242;
                font-size: 11px;
                border-top: 1px solid #BDBDBD;
            }
        """)

    def _trocar_modo(self):
        if self.radio_local.isChecked():
            self.servico.definir_estrategia(self.id_local)
            self.btn_gravar.setEnabled(False) 
            self.status_bar.showMessage("Modo Offline ativado.")
        else:
            # Verifica chave antes de ativar modo online
            if not keyring.get_password("iBirder_Gemini_Key", "user"):
                msg = QMessageBox(self)
                msg.setWindowTitle("Configuração Necessária")
                msg.setText("O Modo Online requer uma chave de API.\nDeseja configurar agora?")
                msg.setIcon(QMessageBox.Question)
                
                # Botões personalizados em Português
                btn_sim = msg.addButton("Sim", QMessageBox.YesRole)
                btn_nao = msg.addButton("Não", QMessageBox.NoRole)
                
                msg.exec()
                
                if msg.clickedButton() == btn_sim:
                    assistente = WizardConfig(self)
                    if assistente.exec():
                         self.servico.definir_estrategia(self.id_nuvem)
                         self.status_bar.showMessage("Modo Online ativado.")
                    else:
                        self.radio_local.setChecked(True)
                else:
                    self.radio_local.setChecked(True)
            else:
                self.servico.definir_estrategia(self.id_nuvem)
                self.status_bar.showMessage("Modo Online ativado.")

        # Se já tiver imagem carregada, reidentifica
        if self.caminho_imagem_atual:
            self._identificar_ave()

    def _carregar_imagem(self, caminho: str):
        self.caminho_imagem_atual = caminho
        
        # Atualiza Preview no DropZone
        original_pixmap = QPixmap(caminho)
        if not original_pixmap.isNull():
            # Redimensiona mantendo aspect ratio e qualidade
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

        self.lbl_nome_cientifico.setText("...")
        self.lbl_nome_comum.setText("...")
        self.lbl_confianca.setText("")
        self.btn_gravar.setEnabled(False)
        self.dados_identificacao_atual = {}
        self.status_bar.showMessage("Identificando...")
        
        # Muda cursor para wait
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents() 

        try:
            resultado = self.servico.identificar(self.caminho_imagem_atual)
            
            if "erro" in resultado:
                QMessageBox.warning(self, "Aviso", resultado["erro"])
                self.lbl_nome_cientifico.setText("Falha")
                self.lbl_nome_comum.setText("-")
                self.lbl_confianca.setText("")
                self.status_bar.showMessage("Falha na identificação.")
                return

            if "melhor_taxa" in resultado: # Resposta Local
                dados = resultado["melhor_taxa"]
                nome_cientifico = dados.get("nome_cientifico", "?")
                confianca = dados.get("confianca", 0.0)
                conf_str = f"Confiança: {confianca:.1%}"
                nome_comum = "Não disponível (Offline)" 
            else: # Resposta Nuvem
                dados = resultado
                nome_cientifico = dados.get("nome_cientifico", "?")
                nome_comum = dados.get("nome_comum", "-")
                confianca = dados.get("confianca", 0.0)
                conf_str = f"Confiança: {confianca:.1%}" if isinstance(confianca, float) else str(confianca)

            self.lbl_nome_cientifico.setText(f"{nome_cientifico}")
            self.lbl_nome_comum.setText(f"{nome_comum}")
            self.lbl_confianca.setText(conf_str)
            
            self.dados_identificacao_atual = {
                "nome_cientifico": nome_cientifico,
                "nome_comum": nome_comum,
                "fonte": "iBirder AI"
            }
            self.btn_gravar.setEnabled(True)
            self.status_bar.showMessage("Concluído.")

        except ChaveApiFaltandoErro:
            QMessageBox.critical(self, "Chave de API", "Chave não encontrada. Configure.")
            self.radio_local.setChecked(True)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro: {str(e)}")
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
            QMessageBox.information(self, "Sucesso", "Metadados gravados com sucesso!")
            self.status_bar.showMessage("Gravado com sucesso.")
        except ErroArquivoInvalido as e:
            QMessageBox.critical(self, "Erro de Arquivo", str(e))
        except RuntimeError as e:
            QMessageBox.critical(self, "Erro no ExifTool", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha: {str(e)}")
        finally:
             QApplication.restoreOverrideCursor()
