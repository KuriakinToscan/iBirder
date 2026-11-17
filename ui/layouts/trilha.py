#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Layout "Trilha" (proposta 1 do redesenho, v1.6): assistente em cinco etapas, com a
trilha sempre à vista e um botão principal por tela.

    [cabeçalho]
    SEU TRABALHO      | ETAPA 3 DE 5 · IMG_4520.JPG
    ✓ Escolher a foto | A IA acha que é Turdus rufiventris. Confere?
    ✓ Identificar     | [página da etapa]
    3 Conferir        |
    4 Conhecer a ave  |
    5 Gravar e public.|
    Nova identificação| Voltar   situação               [Continuar ›]

Páginas (QStackedWidget):
    1. Escolher a foto: card da foto (arrastar ou clicar) e a fila da pasta, em grade.
    2. Identificar: a foto e o aviso de que a IA está trabalhando.
    3. Conferir a espécie: a foto, a referência e o resultado (nome, certeza), com as
       candidatas em cartões compactos ("É esta" confirma e segue).
    4. Conhecer a ave: buscas e abas (descrição, classificação, local, sons).
    5. Gravar e publicar: os botões de gravar na foto e publicar no iNaturalist.

A etapa da identificação (EstadoIdentificacao) limita até onde dá para avançar e leva
a trilha adiante sozinha (foto aberta -> Identificar; resultado -> Conferir). Voltar só
troca de página: nada é apagado. O card da foto acompanha as páginas 1 a 3 (cada painel
existe uma vez só, então ele muda de lugar).
"""

from pathlib import Path

from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea,
                               QSizePolicy, QStackedWidget, QTabWidget, QVBoxLayout, QWidget)

from core.style_manager import StyleManager
from ui import estado_identificacao as ei
from ui.layouts.base import Layout, Paineis, coluna_rolavel as _aba
from ui.widgets.componentes_layout import PortaFoto, RodapeAcoes

# Páginas da trilha, na ordem
ESCOLHER, IDENTIFICAR, CONFERIR, CONHECER, GRAVAR = range(5)
PASSOS = ("Escolher a foto", "Identificar", "Conferir a espécie", "Conhecer a ave", "Gravar e publicar")

# Até que página a etapa da identificação deixa ir
MAXIMO_POR_ETAPA = {
    ei.SEM_FOTO: ESCOLHER,
    ei.IDENTIFICANDO: IDENTIFICAR,
    ei.INCONCLUSIVA: CONFERIR,
    ei.ERRO: CONFERIR,
    ei.CONFERIR: GRAVAR,
    ei.GRAVADA: GRAVAR,
}

LARGURA_LATERAL = 230
LARGURA_RESULTADO = 380   # coluna do resultado na página Conferir
LARGURA_FILA = 460        # coluna da fila na página Escolher (três miniaturas por linha)


def _coluna(*widgets, espaco=StyleManager.SPACING_SM, esticar=None):
    """Coluna simples; `esticar` é o índice do widget que fica com a sobra de altura."""
    coluna = QWidget()
    layout = QVBoxLayout(coluna)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(espaco)
    for i, widget in enumerate(widgets):
        layout.addWidget(widget, 1 if i == esticar else 0)
    if esticar is None:
        layout.addStretch()
    return coluna


def _rolagem(conteudo):
    """Área de rolagem vertical com o fundo do tema (para janelas baixas)."""
    rolagem = QScrollArea()
    rolagem.setObjectName("area_rolagem")
    rolagem.setWidgetResizable(True)
    rolagem.setFrameShape(QFrame.NoFrame)
    rolagem.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    conteudo.setObjectName("container_rolagem")
    rolagem.setWidget(conteudo)
    return rolagem


def _repolir(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _nome_arquivo(caminho):
    return Path(caminho).name if caminho else ""


class LateralTrilha(QFrame):
    """Coluna da esquerda: os cinco passos, cada um feito, atual, liberado ou bloqueado."""

    def __init__(self, ao_escolher, parent=None):
        super().__init__(parent)
        self.setObjectName("trilha_lateral")
        self.setFixedWidth(LARGURA_LATERAL)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(StyleManager.SPACING_MD, StyleManager.SPACING_LG,
                                  StyleManager.SPACING_MD, StyleManager.SPACING_MD)
        layout.setSpacing(StyleManager.SPACING_XS)
        rotulo = QLabel("SEU TRABALHO")
        rotulo.setObjectName("trilha_rotulo")
        layout.addWidget(rotulo)
        layout.addSpacing(StyleManager.SPACING_XS)
        self.botoes = []
        for indice, nome in enumerate(PASSOS):
            botao = QPushButton()
            botao.setObjectName("trilha_passo")
            botao.setCursor(Qt.PointingHandCursor)
            botao.setFocusPolicy(Qt.TabFocus)
            botao.clicked.connect(lambda _=False, i=indice: ao_escolher(i))
            layout.addWidget(botao)
            self.botoes.append(botao)
        self.layout_rodape = QVBoxLayout()
        self.layout_rodape.setSpacing(StyleManager.SPACING_SM)
        layout.addStretch()
        layout.addLayout(self.layout_rodape)

    def mostrar(self, pagina, maximo, gravada):
        for indice, botao in enumerate(self.botoes):
            feito = indice < pagina or (gravada and indice <= GRAVAR and indice != pagina)
            if indice == pagina:
                situacao = "atual"
            elif feito and indice <= maximo:
                situacao = "feito"
            elif indice <= maximo:
                situacao = "livre"
            else:
                situacao = "bloqueado"
            # Passo feito ganha ✓ no lugar do número (não depende só da cor)
            marca = "✓" if situacao == "feito" else str(indice + 1)
            botao.setText(f"{marca}   {PASSOS[indice]}")
            botao.setEnabled(indice <= maximo or indice == pagina)
            if botao.property("situacao") != situacao:
                botao.setProperty("situacao", situacao)
                _repolir(botao)
            botao.setAccessibleName(f"Etapa {indice + 1}: {PASSOS[indice]} ({situacao})")


class _ControleTrilha(QObject):
    """Liga a etapa da identificação às páginas, à trilha lateral e ao rodapé."""

    def __init__(self, raiz, p: Paineis, estado, pilha, lateral, rodape, textos, porta_fotos):
        super().__init__(raiz)
        self.p = p
        self.estado = estado
        self.pilha = pilha
        self.lateral = lateral
        self.lbl_sobretitulo, self.lbl_titulo, self.lbl_subtitulo, self.lbl_situacao = textos
        self.btn_voltar, self.btn_continuar = rodape
        self.porta_fotos = porta_fotos  # página -> layout onde o card da foto entra
        self.btn_voltar.clicked.connect(self.voltar)
        self.btn_continuar.clicked.connect(self.continuar)
        # Outra parte do app pode trocar a página (Ctrl+K leva ao campo do nome, na página 3)
        pilha.currentChanged.connect(lambda _: self.atualizar())
        if estado is not None:
            estado.etapa_alterada.connect(self._ao_mudar_etapa)
            estado.alterado.connect(self.atualizar)
            estado.especie_confirmada.connect(self._ao_confirmar)
        self.ir_para(ESCOLHER if self.etapa == ei.SEM_FOTO else self._pagina_da_etapa(self.etapa))

    # --- Estado ---

    @property
    def etapa(self):
        return self.estado.etapa if self.estado is not None else ei.SEM_FOTO

    @property
    def maximo(self):
        return MAXIMO_POR_ETAPA.get(self.etapa, ESCOLHER)

    @property
    def pagina(self):
        return self.pilha.currentIndex()

    @staticmethod
    def _pagina_da_etapa(etapa):
        return {ei.SEM_FOTO: ESCOLHER, ei.IDENTIFICANDO: IDENTIFICAR, ei.GRAVADA: GRAVAR}.get(etapa, CONFERIR)

    def _ao_mudar_etapa(self, etapa):
        if etapa in (ei.SEM_FOTO, ei.IDENTIFICANDO, ei.INCONCLUSIVA, ei.ERRO):
            self.ir_para(self._pagina_da_etapa(etapa))
        elif etapa == ei.CONFERIR and self.pagina < CONFERIR:
            self.ir_para(CONFERIR)  # resultado da IA (ou nome digitado) chega: conferir
        else:
            self.atualizar()  # gravada, ou nome digitado já na página 3 em diante: fica onde está

    def _ao_confirmar(self, _nome):
        """Espécie confirmada (rodapé ou "É esta" num cartão): segue para Conhecer a ave."""
        if self.pagina <= CONFERIR and self.maximo >= CONHECER:
            self.ir_para(CONHECER)

    # --- Navegação ---

    def ir_para(self, pagina):
        pagina = max(ESCOLHER, min(GRAVAR, pagina))
        porta = self.porta_fotos.get(pagina)
        if isinstance(porta, PortaFoto):
            if not porta.contem(self.p.foto):
                porta.receber(self.p.foto)
        elif porta is not None and porta.indexOf(self.p.foto) < 0:
            porta.insertWidget(0, self.p.foto)
            self.p.foto.show()
        if self.pilha.currentIndex() != pagina:
            self.pilha.setCurrentIndex(pagina)  # dispara atualizar() por currentChanged
        else:
            self.atualizar()

    def escolher_passo(self, pagina):
        """Clique num passo da trilha lateral."""
        if pagina <= self.maximo or pagina == self.pagina:
            self.ir_para(pagina)

    def voltar(self):
        if self.pagina > ESCOLHER:
            self.ir_para(self.pagina - 1)

    def continuar(self):
        if self.pagina == GRAVAR:
            fila = getattr(self.p.fila, "fila", None)
            if fila is not None and fila.proxima() is not None:
                self.p.fila.ir_para_proxima()  # abre a próxima pendente da pasta
            else:
                self.ir_para(ESCOLHER)
            return
        if self.pagina == CONFERIR and self.estado is not None and self.estado.nome_cientifico:
            self.estado.confirmar()  # "Sim, é esta": o sinal leva a Conhecer a ave
            if self.pagina != CONFERIR:
                return
        if self.pagina < self.maximo:
            self.ir_para(self.pagina + 1)

    # --- Textos e botões ---

    def _nome(self):
        nome = self.estado.nome_cientifico if self.estado is not None else None
        return f"<i>{nome}</i>" if nome else ""

    def _textos(self, pagina):
        """Título e subtítulo de cada página, conforme a etapa."""
        etapa, nome = self.etapa, self._nome()
        if pagina == ESCOLHER:
            return ("Qual foto você quer identificar?",
                    "Arraste uma foto para o quadro, clique nele ou abra uma pasta inteira para "
                    "trabalhar em fila (Ctrl+O, Ctrl+Shift+O).")
        if pagina == IDENTIFICAR:
            if etapa == ei.IDENTIFICANDO:
                return ("Identificando a ave...", "A IA está comparando a sua foto com as espécies conhecidas.")
            return ("Identificação concluída", "Continue para conferir o resultado.")
        if pagina == CONFERIR:
            dica = "Não é? Escolha uma sugestão ou digite o nome científico (Ctrl+K)."
            if etapa == ei.INCONCLUSIVA:
                return ("A IA não teve certeza. Qual é a espécie?", dica)
            if etapa == ei.ERRO:
                return ("A identificação falhou. Qual é a espécie?",
                        "Digite o nome científico (Ctrl+K) ou volte e abra outra foto.")
            if self.estado is not None and self.estado.manual:
                return (f"Você indicou {nome}. Confere?", "Compare a sua foto com a de referência.")
            if nome:
                return (f"A IA acha que é {nome}. Confere?", dica)
            return ("Confira a espécie", dica)
        if pagina == CONHECER:
            return (f"Conheça {nome}" if nome else "Conheça a ave",
                    "Descrição, classificação, onde ocorre e como canta.")
        if etapa == ei.GRAVADA:
            return ("Dados gravados na foto", "Publique no iNaturalist, se quiser, ou siga para a próxima foto.")
        return ("Gravar e publicar",
                "Gravar põe a espécie, a família e o local nos metadados da própria foto (Ctrl+S).")

    def _texto_continuar(self, pagina):
        if pagina == CONFERIR:
            return "✓  Sim, é esta"
        if pagina == CONHECER:
            return "Continuar para gravar  ›"
        if pagina == GRAVAR:
            fila = getattr(self.p.fila, "fila", None)
            return "Próxima foto  ›" if fila is not None and fila.proxima() is not None else "Outra foto  ›"
        return "Continuar  ›"

    def atualizar(self):
        pagina, etapa = self.pagina, self.etapa
        gravada = etapa == ei.GRAVADA
        self.lateral.mostrar(pagina, self.maximo, gravada)

        caminho = self.estado.caminho if self.estado is not None else None
        sobretitulo = f"ETAPA {pagina + 1} DE {len(PASSOS)}"
        if caminho and pagina > ESCOLHER:
            sobretitulo += f"  ·  {_nome_arquivo(caminho).upper()}"
        self.lbl_sobretitulo.setText(sobretitulo)
        titulo, subtitulo = self._textos(pagina)
        self.lbl_titulo.setText(titulo)
        self.lbl_subtitulo.setText(subtitulo)
        self.lbl_situacao.setText(_nome_arquivo(caminho) or "Nenhuma foto aberta")

        self.btn_voltar.setVisible(pagina > ESCOLHER)
        self.btn_continuar.setText(self._texto_continuar(pagina))
        if pagina == GRAVAR:
            # Antes de gravar, a ação principal é o botão Gravar da própria página
            self.btn_continuar.setVisible(gravada)
            self.btn_continuar.setEnabled(gravada)
        else:
            self.btn_continuar.setVisible(True)
            self.btn_continuar.setEnabled(pagina < self.maximo)


class LayoutTrilha(Layout):
    id = "trilha"
    nome = "Trilha"
    descricao = "Assistente em cinco etapas, com a trilha sempre à vista e um botão principal por tela."
    paineis_extras = ("fila", "cartoes")

    def montar(self, p: Paineis, estado=None) -> QWidget:
        raiz = QWidget()
        raiz.setObjectName("container_rolagem")
        mestre = QVBoxLayout(raiz)
        mestre.setContentsMargins(0, 0, 0, 0)
        mestre.setSpacing(0)
        topo = QWidget()
        layout_topo = QVBoxLayout(topo)
        margem = StyleManager.SPACING_MD
        layout_topo.setContentsMargins(margem, margem, margem, StyleManager.SPACING_SM)
        layout_topo.addWidget(p.cabecalho)
        mestre.addWidget(topo)

        corpo = QHBoxLayout()
        corpo.setContentsMargins(0, 0, 0, 0)
        corpo.setSpacing(0)
        mestre.addLayout(corpo, 1)

        # --- Coluna principal: cabeçalho da etapa, páginas e rodapé ---
        principal = QWidget()
        layout_principal = QVBoxLayout(principal)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)
        miolo = QWidget()
        layout_miolo = QVBoxLayout(miolo)
        layout_miolo.setContentsMargins(StyleManager.SPACING_LG, StyleManager.SPACING_MD,
                                        StyleManager.SPACING_LG, StyleManager.SPACING_MD)
        layout_miolo.setSpacing(StyleManager.SPACING_XS)
        lbl_sobretitulo = QLabel()
        lbl_sobretitulo.setObjectName("trilha_sobretitulo")
        lbl_titulo = QLabel()
        lbl_titulo.setObjectName("trilha_titulo")
        lbl_titulo.setTextFormat(Qt.RichText)
        lbl_titulo.setWordWrap(True)
        lbl_subtitulo = QLabel()
        lbl_subtitulo.setObjectName("trilha_subtitulo")
        lbl_subtitulo.setWordWrap(True)
        for rotulo in (lbl_sobretitulo, lbl_titulo, lbl_subtitulo):
            layout_miolo.addWidget(rotulo)
        layout_miolo.addSpacing(StyleManager.SPACING_SM)

        pilha = QStackedWidget()
        pilha.setObjectName("trilha_paginas")
        porta_fotos = {}

        # 1. Escolher a foto: card da foto e fila da pasta
        pagina1 = QWidget()
        layout1 = QHBoxLayout(pagina1)
        layout1.setContentsMargins(0, 0, 0, 0)
        layout1.setSpacing(StyleManager.SPACING_LG)
        porta1 = PortaFoto()
        layout1.addWidget(porta1, 3)
        porta_fotos[ESCOLHER] = porta1
        if p.fila is not None:
            if hasattr(p.fila, "definir_vista"):
                p.fila.definir_vista("grade")
            p.fila.setMinimumWidth(320)
            p.fila.setMaximumWidth(LARGURA_FILA)
            layout1.addWidget(p.fila, 2)
        pilha.addWidget(pagina1)

        # 2. Identificar: a foto e o andamento
        pagina2 = QWidget()
        layout2 = QHBoxLayout(pagina2)
        layout2.setContentsMargins(0, 0, 0, 0)
        layout2.setSpacing(StyleManager.SPACING_LG)
        porta2 = PortaFoto()
        layout2.addWidget(porta2, 3)
        porta_fotos[IDENTIFICAR] = porta2
        aviso = QFrame()
        aviso.setProperty("class", "painel")
        layout_aviso = QVBoxLayout(aviso)
        layout_aviso.setContentsMargins(StyleManager.SPACING_LG, StyleManager.SPACING_LG,
                                        StyleManager.SPACING_LG, StyleManager.SPACING_LG)
        lbl_aviso = QLabel("A IA local procura a espécie e, se a nuvem estiver configurada, "
                           "confirma com ela. Leva alguns segundos.")
        lbl_aviso.setWordWrap(True)
        barra = QProgressBar()
        barra.setRange(0, 0)  # indeterminada
        barra.setTextVisible(False)
        barra.setFixedHeight(6)
        layout_aviso.addWidget(lbl_aviso)
        layout_aviso.addWidget(barra)
        layout_aviso.addStretch()
        aviso.setFixedWidth(LARGURA_RESULTADO)
        layout2.addWidget(aviso, 0, Qt.AlignTop)
        pilha.addWidget(pagina2)

        # 3. Conferir: sua foto | referência | resultado
        fotos = QWidget()
        layout_fotos = QHBoxLayout(fotos)
        layout_fotos.setContentsMargins(0, 0, 0, 0)
        layout_fotos.setSpacing(StyleManager.SPACING_MD)
        caixa_foto = QWidget()
        porta3 = QVBoxLayout(caixa_foto)
        porta3.setContentsMargins(0, 0, 0, 0)
        porta3.setSpacing(StyleManager.SPACING_SM)
        porta3.addWidget(p.btn_lens)
        porta3.addStretch()
        porta_fotos[CONFERIR] = porta3
        layout_fotos.addWidget(caixa_foto, 1)
        layout_fotos.addWidget(_coluna(p.referencia, p.btn_fonte), 1)
        if p.cartoes is not None and hasattr(p.cartoes, "definir_orientacao"):
            p.cartoes.definir_orientacao("vertical")  # linhas compactas sob o resultado
        rolagem_resultado = _rolagem(_coluna(*(w for w in (p.identificacao, p.cartoes) if w is not None)))
        rolagem_resultado.setFixedWidth(LARGURA_RESULTADO)
        pagina3 = QWidget()
        layout3 = QHBoxLayout(pagina3)
        layout3.setContentsMargins(0, 0, 0, 0)
        layout3.setSpacing(StyleManager.SPACING_LG)
        layout3.addWidget(_rolagem(fotos), 1)
        layout3.addWidget(rolagem_resultado, 0)
        pilha.addWidget(pagina3)

        # 4. Conhecer a ave: buscas e abas
        abas = QTabWidget()
        abas.setObjectName("abas_especie")
        abas.addTab(_aba(p.descricao, p.etimologia), "Sobre")
        abas.addTab(_aba(p.taxonomia, p.conservacao), "Classificação e conservação")
        abas.addTab(_aba(p.mapa, p.geo), "Onde ocorre")
        abas.addTab(_aba(p.sons), "Sons")
        pagina4 = QWidget()
        layout4 = QVBoxLayout(pagina4)
        layout4.setContentsMargins(0, 0, 0, 0)
        layout4.setSpacing(StyleManager.SPACING_SM)
        layout4.addWidget(p.buscas)
        layout4.addWidget(abas, 1)
        pilha.addWidget(pagina4)

        # 5. Gravar e publicar
        cartao = QFrame()
        cartao.setProperty("class", "painel")
        cartao.setMaximumWidth(640)
        layout_cartao = QVBoxLayout(cartao)
        layout_cartao.setContentsMargins(StyleManager.SPACING_LG, StyleManager.SPACING_LG,
                                         StyleManager.SPACING_LG, StyleManager.SPACING_LG)
        layout_cartao.setSpacing(StyleManager.SPACING_MD)
        lbl_gravar = QLabel("Os dados ficam dentro da foto (EXIF, IPTC e XMP, com os termos Darwin Core): "
                            "qualquer programa de fotos passa a mostrar a espécie. A foto original não é "
                            "recomprimida.")
        lbl_gravar.setWordWrap(True)
        layout_cartao.addWidget(lbl_gravar)
        layout_cartao.addWidget(p.btn_gravar)
        lbl_publicar = QLabel("Publicar no iNaturalist é opcional: você confere tudo antes do envio.")
        lbl_publicar.setWordWrap(True)
        layout_cartao.addWidget(lbl_publicar)
        layout_cartao.addWidget(p.btn_publicar)
        pagina5 = QWidget()
        layout5 = QVBoxLayout(pagina5)
        layout5.setContentsMargins(0, 0, 0, 0)
        layout5.addWidget(cartao)
        layout5.addStretch()
        pilha.addWidget(pagina5)

        layout_miolo.addWidget(pilha, 1)
        layout_principal.addWidget(miolo, 1)

        rodape = RodapeAcoes()
        btn_voltar = QPushButton("Voltar")
        btn_voltar.setObjectName("trilha_voltar")
        btn_voltar.setCursor(Qt.PointingHandCursor)
        btn_voltar.setShortcut("Alt+Left")
        btn_voltar.setToolTip("Etapa anterior (Alt+←). Nada é apagado.")
        rodape.adicionar_esquerda(btn_voltar)
        lbl_situacao = QLabel()
        lbl_situacao.setObjectName("trilha_situacao")
        rodape.adicionar_esquerda(lbl_situacao)
        btn_continuar = QPushButton("Continuar  ›")
        btn_continuar.setProperty("class", "primario")
        btn_continuar.setCursor(Qt.PointingHandCursor)
        btn_continuar.setShortcut("Alt+Right")
        btn_continuar.setToolTip("Próxima etapa (Alt+→)")
        btn_continuar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        rodape.adicionar_direita(btn_continuar)
        layout_principal.addWidget(rodape)

        # --- Trilha lateral ---
        controle = None
        lateral = LateralTrilha(lambda i: controle.escolher_passo(i))
        lateral.layout_rodape.addWidget(p.btn_nova)
        corpo.addWidget(lateral)
        corpo.addWidget(principal, 1)

        controle = _ControleTrilha(raiz, p, estado, pilha, lateral, (btn_voltar, btn_continuar),
                                   (lbl_sobretitulo, lbl_titulo, lbl_subtitulo, lbl_situacao), porta_fotos)
        raiz.controle_trilha = controle  # para testes e para a janela
        return raiz
