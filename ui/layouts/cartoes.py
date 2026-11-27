#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Layout "Cartões de escolha" (proposta 3 do redesenho, v1.6): a pessoa compara a própria
foto com as espécies mais prováveis, cada uma com foto de referência, e escolhe.

    [cabeçalho]
    1 Foto › 2 Escolher a espécie › 3 Ficha › 4 Gravar              Nova identificação
    Página Foto:     "Que ave você fotografou?" e o card da foto, grande
    Página Escolher: sua foto (e Lens) | "Qual destas é a sua ave?"
                                         [cartão] [cartão] [cartão]
                                         nome científico (digitar outra), nomes
    Página Ficha:    referência, classificação, conservação, descrição, sons | mapa,
                     dados do local, Gravar, Publicar

"É esta" no cartão da espécie já aberta só confirma (nenhuma consulta nova); em outro
cartão, faz a busca manual, como digitar o nome. A ficha abre quando a espécie é
confirmada ou digitada; "Trocar espécie" volta aos cartões sem apagar nada.
"""

from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QStackedWidget,
                               QTabWidget, QVBoxLayout, QWidget)

from core.style_manager import StyleManager
from ui import estado_identificacao as ei
from ui.layouts.base import Layout, Paineis, coluna_rolavel as _aba
from ui.widgets.componentes_layout import PortaFoto

FOTO, ESCOLHER, FICHA = range(3)
PASSOS = ("Foto", "Escolher a espécie", "Ficha", "Gravar")

LARGURA_SUA_FOTO = 320
LARGURA_FOTO_INICIAL = 560
LARGURA_LATERAL_FICHA = 380


def _repolir(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _rolagem(conteudo, margem=0):
    rolagem = QScrollArea()
    rolagem.setObjectName("area_rolagem")
    rolagem.setWidgetResizable(True)
    rolagem.setFrameShape(QFrame.NoFrame)
    rolagem.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    conteudo.setObjectName("container_rolagem")
    if conteudo.layout() is not None:
        conteudo.layout().setContentsMargins(margem, margem, margem, margem)
    rolagem.setWidget(conteudo)
    return rolagem


def _coluna(*widgets, espaco=StyleManager.SPACING_SM, esticar=True):
    coluna = QWidget()
    layout = QVBoxLayout(coluna)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(espaco)
    for widget in widgets:
        layout.addWidget(widget)
    if esticar:
        layout.addStretch()
    return coluna


def _titulo(texto, nome_objeto="trilha_titulo"):
    rotulo = QLabel(texto)
    rotulo.setObjectName(nome_objeto)  # mesmos estilos de título da Trilha
    rotulo.setWordWrap(True)
    rotulo.setTextFormat(Qt.RichText)
    return rotulo


class BarraPassos(QWidget):
    """1 Foto › 2 Escolher a espécie › 3 Ficha › 4 Gravar, com o passo atual em destaque."""

    def __init__(self, nomes=PASSOS, parent=None):
        super().__init__(parent)
        self.nomes = nomes
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(StyleManager.SPACING_XS)
        self.rotulos = []
        for n, nome in enumerate(nomes):
            if n:
                seta = QLabel("›")
                seta.setProperty("class", "etapa-seta")
                layout.addWidget(seta)
            rotulo = QLabel()
            rotulo.setProperty("class", "etapa")
            layout.addWidget(rotulo)
            self.rotulos.append(rotulo)

    def mostrar(self, atual, gravada=False):
        for i, rotulo in enumerate(self.rotulos):
            feito = i < atual or (gravada and i <= atual)
            classe = "etapa etapa-feita" if feito else ("etapa etapa-ativa" if i == atual else "etapa")
            # Passo feito ganha ✓ no lugar do número (não depende só da cor)
            rotulo.setText(f"{'✓' if feito else i + 1}  {self.nomes[i]}")
            if rotulo.property("class") != classe:
                rotulo.setProperty("class", classe)
                _repolir(rotulo)


class _ControleCartoes(QObject):
    """Troca as páginas conforme a etapa e a confirmação da espécie."""

    def __init__(self, raiz, p: Paineis, estado, pilha, barra, portas, textos, btn_trocar):
        super().__init__(raiz)
        self.p = p
        self.estado = estado
        self.pilha = pilha
        self.barra = barra
        self.portas = portas  # página -> PortaFoto
        self.lbl_titulo_escolher, self.lbl_sub_escolher, self.lbl_titulo_ficha = textos
        btn_trocar.clicked.connect(lambda: self.ir_para(ESCOLHER))
        pilha.currentChanged.connect(lambda _: self.atualizar())
        if estado is not None:
            estado.etapa_alterada.connect(self._ao_mudar_etapa)
            estado.alterado.connect(self.atualizar)
            # Método (não lambda): a conexão some junto com o layout, e o estado continua
            estado.especie_confirmada.connect(self._ao_confirmar)
            self._ao_mudar_etapa(estado.etapa)
        else:
            self.ir_para(FOTO)

    @property
    def pagina(self):
        return self.pilha.currentIndex()

    def _ao_confirmar(self, _nome=None):
        self.ir_para(FICHA)

    def _ao_mudar_etapa(self, etapa):
        estado = self.estado
        if etapa == ei.SEM_FOTO:
            self.ir_para(FOTO)
        elif etapa in (ei.IDENTIFICANDO, ei.INCONCLUSIVA, ei.ERRO):
            self.ir_para(ESCOLHER)
        elif etapa == ei.CONFERIR:
            # Nome digitado (ou cartão escolhido) é escolha da pessoa: abre a ficha
            self.ir_para(FICHA if (estado.manual or estado.confirmada) else ESCOLHER)
        else:
            self.ir_para(FICHA)

    def ir_para(self, pagina):
        porta = self.portas.get(pagina)
        if porta is not None and not porta.contem(self.p.foto):
            porta.receber(self.p.foto)
        if self.pilha.currentIndex() != pagina:
            self.pilha.setCurrentIndex(pagina)
        else:
            self.atualizar()

    def atualizar(self):
        estado = self.estado
        etapa = estado.etapa if estado is not None else ei.SEM_FOTO
        nome = estado.nome_cientifico if estado is not None else None
        pagina = self.pagina
        passo = {FOTO: 0, ESCOLHER: 1, FICHA: 3 if etapa == ei.GRAVADA else 2}[pagina]
        self.barra.mostrar(passo, gravada=etapa == ei.GRAVADA)

        if etapa == ei.IDENTIFICANDO:
            titulo, sub = "Identificando a ave...", "As espécies mais prováveis aparecem em instantes."
        elif etapa == ei.ERRO:
            titulo, sub = "A identificação falhou.", "Digite o nome científico abaixo ou abra outra foto."
        elif etapa == ei.INCONCLUSIVA:
            titulo, sub = ("A IA não teve certeza. Alguma destas é a sua ave?",
                           "Compare a plumagem e o bico, ou digite o nome científico abaixo.")
        else:
            titulo, sub = ("Qual destas é a sua ave?",
                           "Compare a plumagem e o bico. As porcentagens são a certeza da IA; "
                           "nenhuma destas? Digite o nome abaixo (Ctrl+K).")
        self.lbl_titulo_escolher.setText(titulo)
        self.lbl_sub_escolher.setText(sub)
        self.lbl_titulo_ficha.setText(f"<i>{nome}</i>" if nome else "Ficha da espécie")


class LayoutCartoes(Layout):
    id = "cartoes"
    nome = "Cartões de escolha"
    descricao = "Sua foto ao lado das três espécies mais prováveis, cada uma com foto de referência."
    paineis_extras = ("cartoes",)

    def montar(self, p: Paineis, estado=None) -> QWidget:
        raiz = QWidget()
        raiz.setObjectName("container_rolagem")
        mestre = QVBoxLayout(raiz)
        margem = StyleManager.SPACING_MD
        mestre.setContentsMargins(margem, margem, margem, margem)
        mestre.setSpacing(StyleManager.SPACING_MD)
        mestre.addWidget(p.cabecalho)

        topo = QHBoxLayout()
        barra = BarraPassos()
        topo.addWidget(barra)
        topo.addStretch()
        topo.addWidget(p.btn_nova)
        mestre.addLayout(topo)

        pilha = QStackedWidget()
        pilha.setObjectName("cartoes_paginas")
        portas = {}

        # --- 1. Foto ---
        pagina_foto = QWidget()
        layout_foto = QVBoxLayout(pagina_foto)
        layout_foto.setContentsMargins(0, StyleManager.SPACING_MD, 0, 0)
        layout_foto.setSpacing(StyleManager.SPACING_SM)
        titulo_foto = _titulo("Que ave você fotografou?")
        titulo_foto.setAlignment(Qt.AlignHCenter)
        sub_foto = QLabel("Arraste uma foto para o quadro ou clique nele (Ctrl+O). "
                          "O iBirder mostra as espécies mais prováveis e você escolhe.")
        sub_foto.setObjectName("trilha_subtitulo")
        sub_foto.setAlignment(Qt.AlignHCenter)
        sub_foto.setWordWrap(True)
        # O quadro ocupa a altura que sobra (centralizado, até LARGURA_FOTO_INICIAL); antes, com
        # AlignHCenter, ficava no tamanho mínimo (~150 px) no meio de uma tela vazia
        porta_inicial = PortaFoto()
        porta_inicial.setMaximumWidth(LARGURA_FOTO_INICIAL)
        portas[FOTO] = porta_inicial
        layout_foto.addWidget(titulo_foto)
        layout_foto.addWidget(sub_foto)
        layout_foto.addSpacing(StyleManager.SPACING_MD)
        linha_porta = QHBoxLayout()
        linha_porta.addStretch(1)
        linha_porta.addWidget(porta_inicial, 100)
        linha_porta.addStretch(1)
        layout_foto.addLayout(linha_porta, 1)
        pilha.addWidget(pagina_foto)

        # --- 2. Escolher: sua foto | cartões ---
        porta_sua = PortaFoto()
        porta_sua.setFixedHeight(LARGURA_SUA_FOTO)
        portas[ESCOLHER] = porta_sua
        rotulo_sua = QLabel("SUA FOTO")
        rotulo_sua.setObjectName("trilha_sobretitulo")
        coluna_sua = _coluna(rotulo_sua, porta_sua, p.btn_lens)
        coluna_sua.setFixedWidth(LARGURA_SUA_FOTO)

        lbl_titulo_escolher = _titulo("Qual destas é a sua ave?")
        lbl_sub_escolher = QLabel()
        lbl_sub_escolher.setObjectName("trilha_subtitulo")
        lbl_sub_escolher.setWordWrap(True)
        if p.cartoes is not None and hasattr(p.cartoes, "definir_orientacao"):
            p.cartoes.definir_orientacao("horizontal")
        coluna_cartoes = _coluna(lbl_titulo_escolher, lbl_sub_escolher, p.cartoes, p.identificacao)
        pagina_escolher = QWidget()
        layout_escolher = QHBoxLayout(pagina_escolher)
        layout_escolher.setContentsMargins(0, 0, 0, 0)
        layout_escolher.setSpacing(StyleManager.SPACING_LG)
        layout_escolher.addWidget(coluna_sua, 0)
        layout_escolher.addWidget(_rolagem(coluna_cartoes), 1)
        pilha.addWidget(pagina_escolher)

        # --- 3. Ficha: referência e ficha | mapa, local e ações ---
        btn_trocar = QPushButton("‹  Trocar espécie")
        btn_trocar.setCursor(Qt.PointingHandCursor)
        btn_trocar.setToolTip("Voltar aos cartões das candidatas (nada é apagado)")
        lbl_titulo_ficha = _titulo("Ficha da espécie")
        cabeca_ficha = QHBoxLayout()
        cabeca_ficha.addWidget(lbl_titulo_ficha, 1)
        cabeca_ficha.addWidget(btn_trocar)

        referencia = _coluna(p.referencia, p.btn_fonte)
        referencia.setFixedWidth(LARGURA_SUA_FOTO)
        resumo = QHBoxLayout()
        resumo.setSpacing(StyleManager.SPACING_MD)
        resumo.addWidget(referencia, 0)
        resumo.addWidget(_coluna(p.taxonomia, p.conservacao), 1)
        abas = QTabWidget()
        abas.setObjectName("abas_especie")
        abas.addTab(_aba(p.descricao, p.etimologia), "Sobre")
        abas.addTab(_aba(p.sons), "Sons")
        abas.setMinimumHeight(260)
        conteudo_ficha = QWidget()
        layout_ficha = QVBoxLayout(conteudo_ficha)
        layout_ficha.setSpacing(StyleManager.SPACING_MD)
        layout_ficha.addLayout(cabeca_ficha)
        layout_ficha.addWidget(p.buscas)
        layout_ficha.addLayout(resumo)
        layout_ficha.addWidget(abas, 1)

        lateral = QWidget()
        layout_lateral = QVBoxLayout(lateral)
        layout_lateral.setContentsMargins(0, 0, 0, 0)
        layout_lateral.setSpacing(StyleManager.SPACING_SM)
        layout_lateral.addWidget(_rolagem(_coluna(p.mapa, p.geo)), 1)
        layout_lateral.addWidget(p.btn_gravar)
        layout_lateral.addWidget(p.btn_publicar)
        lateral.setFixedWidth(LARGURA_LATERAL_FICHA)

        pagina_ficha = QWidget()
        layout_pagina_ficha = QHBoxLayout(pagina_ficha)
        layout_pagina_ficha.setContentsMargins(0, 0, 0, 0)
        layout_pagina_ficha.setSpacing(StyleManager.SPACING_LG)
        layout_pagina_ficha.addWidget(_rolagem(conteudo_ficha), 1)
        layout_pagina_ficha.addWidget(lateral, 0)
        pilha.addWidget(pagina_ficha)

        mestre.addWidget(pilha, 1)
        controle = _ControleCartoes(raiz, p, estado, pilha, barra, portas,
                                    (lbl_titulo_escolher, lbl_sub_escolher, lbl_titulo_ficha), btn_trocar)
        raiz.controle_cartoes = controle  # para testes
        return raiz
