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
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QCheckBox, 
                               QScrollArea, QWidget, QFrame,
                               QComboBox, QLineEdit, QSizePolicy)
from PySide6.QtCore import Qt, QSettings
from core import nome_arquivo
from core.style_manager import StyleManager

# Campos agrupados como na ficha (a ordem dentro do grupo é a da gravação)
GRUPOS = (
    ("Espécie", ("nome_cientifico", "nome_comum", "nome_ingles")),
    ("Taxonomia", ("classe", "ordem", "familia", "genero")),
    ("Conservação", ("iucn_status", "status_icmbio", "status_cites", "endemismo")),
    ("Localização", ("pais", "estado", "municipio", "bioma", "coord_gps")),
)

# Caixas avulsas (renomear): só a fonte; o indicador, com o ✓, vem do QSS global
ESTILO_CAIXA = "QCheckBox { font-family: 'var(--fonte)'; font-size: 14px; color: var(--texto); }"

# Linhas da lista: a marcada ganha fundo de seleção e barra na cor de destaque à esquerda
QSS_LISTA = """
    QWidget#exif_lista { background: transparent; }
    QLabel#exif_grupo {
        color: var(--texto_secundario); font-size: 11px; font-weight: 600;
        letter-spacing: 1px; padding: 10px 8px 4px 8px;
    }
    QFrame#exif_linha {
        background-color: transparent; border: none;
        border-left: 3px solid transparent; border-radius: 6px;
    }
    QFrame#exif_linha:hover { background-color: var(--hover); }
    QFrame#exif_linha[marcada="true"] {
        background-color: var(--selecao); border-left: 3px solid var(--destaque);
    }
    QFrame#exif_linha QCheckBox {
        font-family: 'var(--fonte)'; font-size: 13px; color: var(--texto_secundario);
        background: transparent;
    }
    QFrame#exif_linha[marcada="true"] QCheckBox { color: var(--texto); }
    QFrame#exif_linha QCheckBox:disabled { color: var(--texto_suave); }
    QLabel#exif_valor { font-size: 14px; color: var(--texto_secundario); background: transparent; }
    QFrame#exif_linha[marcada="true"] QLabel#exif_valor { color: var(--texto); font-weight: 600; }
    QLabel#exif_valor:disabled { color: var(--texto_suave); font-style: italic; }
"""


class LinhaOpcao(QFrame):
    """
    Uma opção da lista: caixa com o nome do campo à esquerda e o valor à direita (quebra linha).
    A linha inteira é clicável e fica destacada quando marcada.
    """

    def __init__(self, rotulo, valor, parent=None):
        super().__init__(parent)
        self.setObjectName("exif_linha")
        self.setCursor(Qt.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(12)

        self.checkbox = QCheckBox(rotulo)
        self.checkbox.setMinimumWidth(190)
        lay.addWidget(self.checkbox, 0, Qt.AlignTop)

        self.lbl_valor = QLabel(valor)
        self.lbl_valor.setObjectName("exif_valor")
        self.lbl_valor.setWordWrap(True)
        self.lbl_valor.setTextFormat(Qt.PlainText)
        self.lbl_valor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lay.addWidget(self.lbl_valor, 1)

        self.checkbox.toggled.connect(self.atualizar_destaque)

    def atualizar_destaque(self, *_):
        """Propriedade "marcada" (usada no QSS) e cor do valor conforme a caixa."""
        habilitada = self.checkbox.isEnabled()
        self.lbl_valor.setEnabled(habilitada)
        self.setCursor(Qt.PointingHandCursor if habilitada else Qt.ArrowCursor)
        self.setProperty("marcada", habilitada and self.checkbox.isChecked())
        for w in (self, self.checkbox, self.lbl_valor):
            w.style().unpolish(w)
            w.style().polish(w)
        self.update()

    def mousePressEvent(self, evento):  # noqa: N802 (API do Qt)
        """Clique em qualquer ponto da linha (fora da caixa) alterna a opção."""
        if evento.button() == Qt.LeftButton and self.checkbox.isEnabled():
            self.checkbox.toggle()
            evento.accept()
            return
        super().mousePressEvent(evento)


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
        StyleManager.setup_window_theme(self)

    def _setup_ui(self):
        # O Fundo da janela usará a cor base do app
        StyleManager.estilizar(self, """
            QDialog { background-color: var(--fundo); }
            QLabel#exif_contador { color: var(--texto_secundario); font-size: 13px; }
            QPushButton#exif_acao_lote {
                background: transparent; border: 1px solid var(--borda); border-radius: var(--raio_botao);
                color: var(--texto); font-size: 12px; padding: 4px 10px;
            }
            QPushButton#exif_acao_lote:hover { background-color: var(--hover); }
            QPushButton#exif_acao_lote:disabled { color: var(--texto_suave); border-color: var(--borda_suave); }
        """)
        
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

        # Barra de seleção: contador + marcar/desmarcar todos
        barra = QHBoxLayout()
        barra.setSpacing(8)
        self.lbl_contador = QLabel()
        self.lbl_contador.setObjectName("exif_contador")
        barra.addWidget(self.lbl_contador)
        barra.addStretch()
        self.btn_marcar_todos = QPushButton("Marcar todos")
        self.btn_desmarcar_todos = QPushButton("Desmarcar todos")
        for btn, marcar in ((self.btn_marcar_todos, True), (self.btn_desmarcar_todos, False)):
            btn.setObjectName("exif_acao_lote")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, m=marcar: self._marcar_todos(m))
            barra.addWidget(btn)
        layout_principal.addLayout(barra)

        # Card com as opções em grupos; cada opção é uma linha inteira clicável
        card_central = QFrame()
        card_central.setProperty("class", "painel")
        StyleManager.apply_shadow(card_central)
        layout_card = QVBoxLayout(card_central)
        layout_card.setContentsMargins(6, 6, 6, 6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        # Valores longos quebram a linha em vez de criar barra de rolagem horizontal
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        container_checks = QWidget()
        container_checks.setObjectName("exif_lista")
        StyleManager.estilizar(container_checks, QSS_LISTA)
        self.layout_checks = QVBoxLayout(container_checks)
        self.layout_checks.setContentsMargins(4, 4, 8, 4)
        self.layout_checks.setSpacing(2)

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
        self.linhas = {}
        opcoes = {chave: (texto, padrao) for texto, chave, padrao in self.lista_opcoes}

        for titulo_grupo, chaves in GRUPOS:
            lbl_grupo = QLabel(titulo_grupo.upper())
            lbl_grupo.setObjectName("exif_grupo")
            self.layout_checks.addWidget(lbl_grupo)
            for chave_dict in chaves:
                texto_exibicao, default_checked = opcoes[chave_dict]
                valor, habilitada = self._valor_da_opcao(chave_dict)
                linha = LinhaOpcao(texto_exibicao, valor)
                linha.checkbox.setEnabled(habilitada)
                linha.checkbox.setChecked(habilitada and default_checked)
                linha.checkbox.toggled.connect(self._atualizar_contador)
                linha.atualizar_destaque()
                self.checkboxes[chave_dict] = linha.checkbox
                self.linhas[chave_dict] = linha
                self.layout_checks.addWidget(linha)

        self.layout_checks.addStretch()
        scroll.setWidget(container_checks)
        layout_card.addWidget(scroll)
        layout_principal.addWidget(card_central, stretch=1)
        self._atualizar_contador()

        if self.caminho_imagem:
            self._montar_secao_nome(layout_principal)

        # Resumo de Alerta usando CSS class
        if self.tem_gps_nativo:
            lbl_aviso_gps = QLabel("⚠️ A imagem original já possui coordenadas GPS. Elas foram protegidas contra sobrescrita manual.")
            lbl_aviso_gps.setWordWrap(True)
            lbl_aviso_gps.setProperty("class", "lbl-titulo-sessao")
            lbl_aviso_gps.style().unpolish(lbl_aviso_gps)
            lbl_aviso_gps.style().polish(lbl_aviso_gps)
            StyleManager.estilizar(lbl_aviso_gps, "color: var(--alerta_texto); font-size: 13px; background-color: var(--alerta_fundo); padding: 10px; border-radius: 6px; border: 1px solid var(--alerta_borda);")
            layout_principal.addWidget(lbl_aviso_gps)

        # Botões Invertidos (Padrão Windows) - Cancelar esq, Gravar dir
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        btn_cancelar.setProperty("class", "btn-acao-alinhado")
        btn_cancelar.style().unpolish(btn_cancelar)
        btn_cancelar.style().polish(btn_cancelar)
        StyleManager.estilizar(btn_cancelar, "background-color: transparent; border: 1px solid var(--texto_suave); color: var(--texto_secundario);")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_gravar = QPushButton("Gravar Dados na Fotografia")
        btn_gravar.setCursor(Qt.PointingHandCursor)
        btn_gravar.setProperty("class", "btn-acao-alinhado primario")
        btn_gravar.style().unpolish(btn_gravar)
        btn_gravar.style().polish(btn_gravar)
        btn_gravar.clicked.connect(self._confirmar_gravacao)
        
        layout_botoes.addWidget(btn_cancelar)
        layout_botoes.addWidget(btn_gravar)
        
        layout_principal.addLayout(layout_botoes)

    # ------------------------------------------------------------ Seleção dos campos

    def _valor_da_opcao(self, chave):
        """(texto do valor, habilitada) de um campo; sem dado ou GPS protegido = desabilitada."""
        valor = self.dados.get(chave, "N/A")
        if chave == "genero" and valor == "N/A":
            nome_cientifico = self.dados.get("nome_cientifico", "")
            if nome_cientifico:
                valor = nome_cientifico.split()[0]
        if chave == "coord_gps":
            if self.tem_gps_nativo:
                return "Protegido: a imagem já possui GPS original", False
            lat = self.dados.get("latitude")
            lon = self.dados.get("longitude")
            if lat and lon:
                return f"{lat:.5f}, {lon:.5f}", True
            return "Não disponíveis na sessão", False
        if valor == "N/A" or not valor:
            return "Não disponível", False
        return str(valor), True

    def _marcar_todos(self, marcar):
        """Marca ou desmarca todos os campos que têm dado (os desabilitados ficam como estão)."""
        for cb in self.checkboxes.values():
            if cb.isEnabled():
                cb.setChecked(marcar)

    def _atualizar_contador(self, *_):
        habilitadas = [cb for cb in self.checkboxes.values() if cb.isEnabled()]
        marcadas = sum(cb.isChecked() for cb in habilitadas)
        total = len(habilitadas)
        if marcadas == 0:
            texto = "Nenhum campo será gravado"
        elif marcadas == 1:
            texto = f"1 de {total} campos será gravado"
        else:
            texto = f"{marcadas} de {total} campos serão gravados"
        self.lbl_contador.setText(texto)
        self.btn_marcar_todos.setEnabled(marcadas < total)
        self.btn_desmarcar_todos.setEnabled(marcadas > 0)

    # ------------------------------------------------------------ Renomear o arquivo (v1.3)

    def _montar_secao_nome(self, layout_principal):
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
        StyleManager.estilizar(self.cb_renomear, ESTILO_CAIXA)
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
            StyleManager.estilizar(self.cb_irmaos, ESTILO_CAIXA)
            self.cb_irmaos.setChecked(self.settings.value("renomear/irmaos", True, type=bool))
            lay.addWidget(self.cb_irmaos)

        aviso = QLabel("Usa o Lightroom? Renomeie pelo próprio Lightroom: fora dele, o catálogo "
                       "perde o vínculo com a foto.")
        aviso.setWordWrap(True)
        StyleManager.estilizar(aviso, "font-size: 12px; color: var(--texto_suave);")
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
            StyleManager.estilizar(self.lbl_previa, "font-size: 12px; color: var(--texto_suave);")
            return None
        base = self.edit_nome.text()
        erro = nome_arquivo.validar_nome(base)
        if erro:
            self.lbl_previa.setText(f"⚠️ {html.escape(erro)}")
            StyleManager.estilizar(self.lbl_previa, "font-size: 12px; color: var(--erro_texto);")
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
        StyleManager.estilizar(self.lbl_previa, "font-size: 12px; color: var(--texto);")
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
