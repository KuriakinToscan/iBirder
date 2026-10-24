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

import html
import os
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QCheckBox, 
                               QScrollArea, QWidget, QMessageBox, QFrame,
                               QComboBox, QLineEdit)
from PySide6.QtCore import Qt, QSettings
from core import nome_arquivo
try:
    from core.style_manager import StyleManager
except ImportError:
    StyleManager = None

class ExifConfigDialog(QDialog):
    def __init__(self, parent=None, dados=None, tem_gps_nativo=False, caminho_imagem=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Gravação de Dados na Fotografia")
        self.setMinimumWidth(480)
        self.setMinimumHeight(640)
        self.dados = dados or {}
        self.tem_gps_nativo = tem_gps_nativo
        self.opcoes_selecionadas = {}
        self.caminho_imagem = Path(caminho_imagem) if caminho_imagem else None
        self.renomeacao = None

        self._setup_ui()
        if StyleManager: StyleManager.setup_window_theme(self)

    def _setup_ui(self):
        # O Fundo da janela usará a cor base do app
        self.setStyleSheet("QDialog { background-color: #f7f7f9; }")
        
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)
        layout_principal.setSpacing(15)

        # Cabeçalho
        lbl_instrucao = QLabel("Selecione quais dados devem ser gravados permanentemente na fotografia:")
        lbl_instrucao.setWordWrap(True)
        lbl_instrucao.setProperty("class", "lbl-titulo-sessao")
        lbl_instrucao.style().unpolish(lbl_instrucao)
        lbl_instrucao.style().polish(lbl_instrucao)
        layout_principal.addWidget(lbl_instrucao)

        # Card Central (Fundo Branco, Borda Suave, Sombra)
        card_central = QFrame()
        card_central.setProperty("class", "painel")
        if StyleManager: StyleManager.apply_shadow(card_central)
        layout_card = QVBoxLayout(card_central)
        layout_card.setContentsMargins(15, 15, 15, 15)

        # Scroll Area limpo por cima do Card
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        container_checks = QWidget()
        container_checks.setStyleSheet("QWidget { background: transparent; }")
        self.layout_checks = QVBoxLayout(container_checks)
        self.layout_checks.setSpacing(12)

        self.lista_opcoes = [
            ("Nome Científico", "nome_cientifico", True),
            ("Nome Comum", "nome_comum", True),
            ("Nome em Inglês", "nome_ingles", True),
            ("Classe", "classe", True),
            ("Ordem", "ordem", True),
            ("Família", "familia", True),
            ("Gênero", "genero", True),
            ("Status IUCN", "iucn_status", True),
            ("Status Nacional", "status_icmbio", True),
            ("Status CITES", "status_cites", True),
            ("País", "pais", True),
            ("Estado", "estado", True),
            ("Município", "municipio", True),
            ("Bioma", "bioma", True),
            ("Endêmico do Brasil", "endemismo", True),
            ("Coordenadas Geográficas (GPS)", "coord_gps", True)  
        ]

        self.checkboxes = {}

        # Estilo raw das checkboxes customizadas para leitura elegante
        check_style = """
            QCheckBox {
                font-family: 'Segoe UI'; font-size: 14px; color: #374151;
            }
            QCheckBox::indicator {
                width: 18px; height: 18px; border-radius: 4px;
                border: 1px solid #9CA3AF;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #1F2937;
                border: 1px solid #1F2937;
            }
            QCheckBox:disabled { color: #9CA3AF; }
        """

        for texto_exibicao, chave_dict, default_checked in self.lista_opcoes:
            valor_atual = self.dados.get(chave_dict, "N/A")
            
            if chave_dict == "genero" and valor_atual == "N/A":
                nome_cientifico = self.dados.get("nome_cientifico", "")
                if nome_cientifico:
                    valor_atual = nome_cientifico.split()[0]
            
            if chave_dict == "coord_gps":
                lat = self.dados.get("latitude")
                lon = self.dados.get("longitude")
                if lat and lon:
                    valor_atual = f"{lat:.5f}, {lon:.5f}"
                else:
                    valor_atual = "Não disponíveis na sessão"

            cb = QCheckBox(f"{texto_exibicao}: {valor_atual}")
            cb.setStyleSheet(check_style)
            
            if chave_dict == "coord_gps":
                if self.tem_gps_nativo:
                    cb.setChecked(False)
                    cb.setEnabled(False)
                    cb.setText(f"{texto_exibicao}: [Protegido - Imagem possui GPS original]")
                elif valor_atual == "Não disponíveis na sessão":
                    cb.setChecked(False)
                    cb.setEnabled(False)
                else:
                    cb.setChecked(default_checked)
            else:
                if valor_atual == "N/A" or not valor_atual:
                    cb.setChecked(False)
                    cb.setEnabled(False)
                else:
                    cb.setChecked(default_checked)

            self.checkboxes[chave_dict] = cb
            self.layout_checks.addWidget(cb)

        self.layout_checks.addStretch()
        scroll.setWidget(container_checks)
        layout_card.addWidget(scroll)
        layout_principal.addWidget(card_central)

        if self.caminho_imagem:
            self._montar_secao_nome(layout_principal, check_style)

        # Resumo de Alerta usando CSS class
        if self.tem_gps_nativo:
            lbl_aviso_gps = QLabel("⚠️ A imagem original já possui coordenadas GPS. Elas foram protegidas contra sobrescrita manual.")
            lbl_aviso_gps.setWordWrap(True)
            lbl_aviso_gps.setProperty("class", "lbl-titulo-sessao")
            lbl_aviso_gps.style().unpolish(lbl_aviso_gps)
            lbl_aviso_gps.style().polish(lbl_aviso_gps)
            lbl_aviso_gps.setStyleSheet("color: #B45309; font-size: 13px; background-color: #FEF3C7; padding: 10px; border-radius: 6px; border: 1px solid #FDE68A;")
            layout_principal.addWidget(lbl_aviso_gps)

        # Botões Invertidos (Padrão Windows) - Cancelar esq, Gravar dir
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        btn_cancelar.setProperty("class", "btn-acao-alinhado")
        btn_cancelar.style().unpolish(btn_cancelar)
        btn_cancelar.style().polish(btn_cancelar)
        btn_cancelar.setStyleSheet("background-color: transparent; border: 1px solid #9CA3AF; color: #4B5563;")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_gravar = QPushButton("Gravar Dados na Fotografia")
        btn_gravar.setCursor(Qt.PointingHandCursor)
        btn_gravar.setProperty("class", "btn-acao-alinhado")
        btn_gravar.style().unpolish(btn_gravar)
        btn_gravar.style().polish(btn_gravar)
        btn_gravar.clicked.connect(self._confirmar_gravacao)
        
        layout_botoes.addWidget(btn_cancelar)
        layout_botoes.addWidget(btn_gravar)
        
        layout_principal.addLayout(layout_botoes)

    # ------------------------------------------------------------ Renomear o arquivo (v1.3)

    def _montar_secao_nome(self, layout_principal, check_style):
        """Caixa 'Renomear o arquivo' com padrão, nome editável e prévia (NomeComum_aaaammdd)."""
        self.settings = QSettings("iBirder", "App")
        self.data_foto = nome_arquivo.data_captura(self.caminho_imagem)
        self.irmaos = nome_arquivo.arquivos_irmaos(self.caminho_imagem)
        self.extensao = self.caminho_imagem.suffix

        painel = QFrame()
        painel.setProperty("class", "painel")
        lay = QVBoxLayout(painel)
        lay.setContentsMargins(15, 12, 15, 12)
        lay.setSpacing(8)

        self.cb_renomear = QCheckBox("Renomear o arquivo")
        self.cb_renomear.setStyleSheet(check_style)
        lay.addWidget(self.cb_renomear)

        linha_padrao = QHBoxLayout()
        linha_padrao.addWidget(QLabel("Padrão:"))
        self.combo_padrao = QComboBox()
        for chave, rotulo in nome_arquivo.PADROES.items():
            self.combo_padrao.addItem(rotulo, chave)
        linha_padrao.addWidget(self.combo_padrao, stretch=1)
        lay.addLayout(linha_padrao)

        linha_nome = QHBoxLayout()
        self.edit_nome = QLineEdit()
        self.edit_nome.setMaxLength(nome_arquivo.TAMANHO_MAXIMO)
        linha_nome.addWidget(self.edit_nome, stretch=1)
        linha_nome.addWidget(QLabel(html.escape(self.extensao)))
        lay.addLayout(linha_nome)

        self.lbl_previa = QLabel()
        self.lbl_previa.setWordWrap(True)
        self.lbl_previa.setStyleSheet("font-size: 12px;")
        lay.addWidget(self.lbl_previa)

        self.cb_irmaos = None
        if self.irmaos:
            nomes = ", ".join(f.name for f in self.irmaos)
            self.cb_irmaos = QCheckBox(f"Renomear também: {nomes}")
            self.cb_irmaos.setStyleSheet(check_style)
            self.cb_irmaos.setChecked(self.settings.value("renomear/irmaos", True, type=bool))
            lay.addWidget(self.cb_irmaos)

        aviso = QLabel("Usa o Lightroom? Renomeie pelo próprio Lightroom: fora dele, o catálogo "
                       "perde o vínculo com a foto.")
        aviso.setWordWrap(True)
        aviso.setStyleSheet("font-size: 12px; color: #6B7280;")
        lay.addWidget(aviso)
        layout_principal.addWidget(painel)

        padrao = self.settings.value("renomear/padrao", nome_arquivo.PADRAO_PADRAO)
        indice = self.combo_padrao.findData(padrao)
        self.combo_padrao.setCurrentIndex(max(indice, 0))
        self.cb_renomear.setChecked(self.settings.value("renomear/ativo", False, type=bool))
        if not (nome_arquivo.nome_comum(self.dados) or nome_arquivo.nome_cientifico(self.dados)):
            # Sem espécie identificada não há o que sugerir
            self.cb_renomear.setChecked(False)
            self.cb_renomear.setEnabled(False)
            self.cb_renomear.setText("Renomear o arquivo (indisponível: espécie não identificada)")

        self.cb_renomear.toggled.connect(self._atualizar_secao_nome)
        self.combo_padrao.currentIndexChanged.connect(self._aplicar_padrao)
        self.edit_nome.textChanged.connect(self._atualizar_previa)
        if self.cb_irmaos:
            self.cb_irmaos.toggled.connect(self._atualizar_previa)
        self._aplicar_padrao()

    def _aplicar_padrao(self):
        sugestao = nome_arquivo.sugerir_nome(self.dados, self.data_foto, self.combo_padrao.currentData())
        self.sem_nome_especie = sugestao is None
        self.edit_nome.setText(sugestao or self.caminho_imagem.stem)
        self._atualizar_secao_nome()

    def _atualizar_secao_nome(self):
        ativo = self.cb_renomear.isChecked()
        for w in (self.combo_padrao, self.edit_nome, self.cb_irmaos):
            if w is not None:
                w.setEnabled(ativo)
        self._atualizar_previa()

    def _atualizar_previa(self):
        """Valida o nome e mostra o nome final (com sufixo, se já existir)."""
        if not self.cb_renomear.isChecked():
            self.lbl_previa.setText(f"Nome atual: {html.escape(self.caminho_imagem.name)}")
            self.lbl_previa.setStyleSheet("font-size: 12px; color: #6B7280;")
            return None
        base = self.edit_nome.text()
        erro = nome_arquivo.validar_nome(base)
        if erro:
            self.lbl_previa.setText(f"⚠️ {html.escape(erro)}")
            self.lbl_previa.setStyleSheet("font-size: 12px; color: #B91C1C;")
            return None
        irmaos = self.irmaos if (self.cb_irmaos and self.cb_irmaos.isChecked()) else []
        final = nome_arquivo.nome_livre(self.caminho_imagem, base, irmaos)
        texto = f"Será salvo como: <b>{html.escape(final + self.extensao)}</b>"
        if final != base:
            texto += " (já existe um arquivo com esse nome)"
        if self.data_foto is None:
            texto += "<br>⚠️ A foto não tem data de captura: complete a data no nome, se quiser."
        if self.sem_nome_especie:
            texto += "<br>⚠️ Sem nome comum: digite o nome ou escolha o padrão com o nome científico."
        self.lbl_previa.setText(texto)
        self.lbl_previa.setStyleSheet("font-size: 12px; color: #374151;")
        return base

    def _confirmar_gravacao(self):
        self.renomeacao = None
        if self.caminho_imagem and self.cb_renomear.isChecked():
            base = self._atualizar_previa()
            if base is None:
                return  # nome inválido: a mensagem já está na tela
            irmaos = self.irmaos if (self.cb_irmaos and self.cb_irmaos.isChecked()) else []
            self.renomeacao = {"base": base, "irmaos": irmaos}
        if self.caminho_imagem and self.cb_renomear.isEnabled():
            self.settings.setValue("renomear/ativo", self.cb_renomear.isChecked())
            self.settings.setValue("renomear/padrao", self.combo_padrao.currentData())
            if self.cb_irmaos:
                self.settings.setValue("renomear/irmaos", self.cb_irmaos.isChecked())
        for chave, cb in self.checkboxes.items():
            self.opcoes_selecionadas[chave] = cb.isChecked()
        self.accept()

    def get_renomeacao(self):
        """None (não renomear) ou {'base': nome sem extensão, 'irmaos': [Path, ...]}."""
        return self.renomeacao

    def get_selected_fields(self):
        """Retorna o dicionário de campos selecionados pelo usuário (v0.8.8)."""
        return self.opcoes_selecionadas
