#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Layout "Foco" (proposta 4 do redesenho, v1.6): a foto ocupa a janela e o resto flutua
sobre ela. Pensado para o teclado.

    [cabeçalho]
    +--------+-------------------------------------------+-------------+
    | [fila] |                              [? Atalhos]  | resultado   |
    |        |     sua foto (zoom: roda, + - 0)          | (nome,      |
    |        |                            +-- ficha --+  |  certeza)   |
    |        |                            | referência |  |             |
    |        |                            | abas      |  | Ficha Gravar|
    +--------+-------------------------------------------+-------------+

- Palco: `PalcoFoto` espelha o card da foto em tamanho grande; o card fica na ficha.
- Resultado ("pílula", coluna à direita): identificação, "Ficha" e "Gravar". Fica ao lado
  da foto, sem cobri-la (antes flutuava por cima e tampava metade da foto).
- Ficha (Gaveta à direita do palco): sua foto e a referência, candidatas, buscas e abas.
- Fila (coluna à esquerda), mostrada quando há pasta aberta (tecla F).

Atalhos deste layout (a lista aparece com ? ou F1): I abre e fecha a ficha, F mostra a
fila, Esc fecha a ficha e a lista, ← → trocam de foto, + − 0 dão zoom. Os da janela
(Ctrl+O, Ctrl+Shift+O, Ctrl+K, Ctrl+S) continuam valendo. Letras sem modificador não
disparam num campo de texto (o campo fica com elas).
"""

import shiboken6
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QTabWidget, QVBoxLayout, QWidget

from core.style_manager import StyleManager
from ui import estado_identificacao as ei
from ui.layouts.base import Layout, Paineis, coluna_rolavel
from ui.widgets.componentes_layout import Gaveta, Sobreposicao
from ui.widgets.palco_foto import PalcoFoto

LARGURA_FICHA = 600
LARGURA_PILULA = 380   # coluna do resultado
LARGURA_FILA = 260

ATALHOS = (
    ("Ctrl+O", "abrir uma foto"),
    ("Ctrl+Shift+O", "abrir uma pasta"),
    ("← →", "foto anterior e seguinte da pasta"),
    ("Ctrl+K", "digitar ou buscar a espécie"),
    ("I", "abrir e fechar a ficha da espécie"),
    ("F", "mostrar e esconder a fila"),
    ("+  −  0", "aproximar, afastar e ajustar a foto"),
    ("Ctrl+S", "gravar os dados na foto"),
    ("Esc", "fechar a ficha e esta lista"),
    ("?  ou  F1", "mostrar esta lista"),
)


def _coluna(*widgets, espaco=StyleManager.SPACING_SM):
    coluna = QWidget()
    layout = QVBoxLayout(coluna)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(espaco)
    for widget in widgets:
        if widget is not None:
            layout.addWidget(widget)
    layout.addStretch()  # a sobra de altura fica embaixo, sem esticar os painéis
    return coluna


class _ControleFoco(QObject):
    """Atalhos do Foco e o que aparece conforme a etapa."""

    def __init__(self, raiz, p: Paineis, estado, palco, gaveta, pilula, caixa_fila, lista_atalhos,
                 abas_ficha):
        super().__init__(raiz)
        self.p = p
        self.estado = estado
        self.palco = palco
        self.gaveta = gaveta
        self.pilula = pilula
        self.caixa_fila = caixa_fila
        self.lista_atalhos = lista_atalhos
        self.abas_ficha = abas_ficha
        self._fila_escondida = False
        atalhos = (
            ("I", self.alternar_ficha),
            ("F", self.alternar_fila),
            ("Esc", self.fechar_sobreposicoes),
            ("?", self.alternar_atalhos),
            ("F1", self.alternar_atalhos),
            ("Left", lambda: self.navegar(-1)),
            ("Right", lambda: self.navegar(1)),
        )
        self.atalhos = {}
        for tecla, acao in atalhos:
            atalho = QShortcut(QKeySequence(tecla), raiz)
            atalho.setContext(Qt.WidgetWithChildrenShortcut)
            atalho.activated.connect(acao)
            self.atalhos[tecla] = atalho
        if estado is not None:
            estado.etapa_alterada.connect(self._ao_mudar_etapa)
            # Métodos (não lambdas): as conexões somem junto com o layout; estado e fila continuam
            estado.especie_confirmada.connect(self.abrir_ficha)
            self._ao_mudar_etapa(estado.etapa)
        else:
            self._ao_mudar_etapa(ei.SEM_FOTO)

    # --- Etapas ---

    def _vivo(self, widget):
        """Na troca de layout, a raiz destrói os filhos antes deste controle: o estado e a fila
        (que continuam vivos) ainda podem emitir nesse intervalo."""
        return widget is not None and shiboken6.isValid(widget)

    def _ao_mudar_etapa(self, etapa):
        if not (self._vivo(self.pilula) and self._vivo(self.gaveta)):
            return
        # Sem foto, a pílula só atrapalha o palco (que já diz o que fazer)
        self.pilula.setVisible(etapa != ei.SEM_FOTO)
        if etapa == ei.SEM_FOTO:
            self.gaveta.fechar()
        self.atualizar_fila()

    # --- Ações ---

    def abrir_ficha(self, *_args):
        if self._vivo(self.gaveta):
            self.gaveta.abrir()

    def alternar_ficha(self):
        self.gaveta.alternar()

    def alternar_fila(self):
        self._fila_escondida = not self._fila_escondida
        self.atualizar_fila()

    def atualizar_fila(self, *_args):
        """A fila aparece quando há pasta aberta e a pessoa não a escondeu."""
        if not self._vivo(self.caixa_fila):
            return
        fila = getattr(self.p.fila, "fila", None)
        tem_pasta = bool(getattr(fila, "itens", None)) if fila is not None else False
        visivel = tem_pasta and not self._fila_escondida
        self.caixa_fila.setVisible(visivel)

    def alternar_atalhos(self):
        self.lista_atalhos.setVisible(not self.lista_atalhos.isVisible())
        if self.lista_atalhos.isVisible():
            self.lista_atalhos.reposicionar()

    def fechar_sobreposicoes(self):
        if self.lista_atalhos.isVisible():
            self.lista_atalhos.hide()
        elif self.gaveta.esta_aberta():
            self.gaveta.fechar()
            self.palco.setFocus(Qt.ShortcutFocusReason)

    def navegar(self, passo):
        fila = self.p.fila
        if fila is not None and hasattr(fila, "abrir_vizinha"):
            return fila.abrir_vizinha(passo)
        return False


class LayoutFoco(Layout):
    id = "foco"
    nome = "Foco"
    descricao = "A foto ocupa a janela; resultado e ficha flutuam sobre ela. Bom para o teclado."
    paineis_extras = ("fila", "cartoes")

    def montar(self, p: Paineis, estado=None) -> QWidget:
        raiz = QWidget()
        raiz.setObjectName("container_rolagem")
        mestre = QVBoxLayout(raiz)
        margem = StyleManager.SPACING_MD
        mestre.setContentsMargins(margem, margem, margem, margem)
        mestre.setSpacing(StyleManager.SPACING_SM)
        mestre.addWidget(p.cabecalho)

        corpo = QHBoxLayout()
        corpo.setSpacing(StyleManager.SPACING_MD)
        mestre.addLayout(corpo, 1)

        # --- Fila à esquerda (só com pasta aberta) ---
        caixa_fila = None
        if p.fila is not None:
            if hasattr(p.fila, "definir_vista"):
                p.fila.definir_vista("lista")
            caixa_fila = QFrame()
            caixa_fila.setObjectName("sobreposicao")  # mesmo fundo de antes
            caixa_fila.setFixedWidth(LARGURA_FILA)
            layout_fila = QVBoxLayout(caixa_fila)
            layout_fila.setContentsMargins(0, 0, 0, 0)
            layout_fila.addWidget(p.fila)
            corpo.addWidget(caixa_fila)

        # --- Palco ---
        palco = PalcoFoto()
        palco.espelhar(p.foto)
        corpo.addWidget(palco, 1)

        # --- Resultado ("pílula"), numa coluna ao lado da foto ---
        pilula = QFrame()
        pilula.setObjectName("foco_pilula")
        pilula.setFixedWidth(LARGURA_PILULA)
        layout_pilula = QVBoxLayout(pilula)
        layout_pilula.setContentsMargins(StyleManager.SPACING_SM, StyleManager.SPACING_SM,
                                         StyleManager.SPACING_SM, StyleManager.SPACING_SM)
        layout_pilula.setSpacing(StyleManager.SPACING_SM)
        layout_pilula.addWidget(coluna_rolavel(p.identificacao, margem=0), 1)
        btn_ficha = QPushButton("Ficha  ›")
        btn_ficha.setCursor(Qt.PointingHandCursor)
        btn_ficha.setToolTip("Abrir a ficha da espécie (I)")
        layout_pilula.addWidget(btn_ficha)
        layout_pilula.addWidget(p.btn_gravar)
        corpo.addWidget(pilula)

        # --- Botão e lista de atalhos ---
        dica = Sobreposicao(palco, "superior-direita", margem=StyleManager.SPACING_MD)
        dica.setObjectName("foco_dica")
        layout_dica = QHBoxLayout(dica)
        layout_dica.setContentsMargins(2, 2, 2, 2)
        btn_atalhos = QPushButton("?  Atalhos")
        btn_atalhos.setCursor(Qt.PointingHandCursor)
        btn_atalhos.setToolTip("Atalhos do teclado (? ou F1)")
        layout_dica.addWidget(btn_atalhos)

        lista_atalhos = Sobreposicao(palco, "centro", margem=StyleManager.SPACING_MD)
        lista_atalhos.setObjectName("foco_atalhos")
        layout_lista = QVBoxLayout(lista_atalhos)
        layout_lista.setContentsMargins(StyleManager.SPACING_LG, StyleManager.SPACING_MD,
                                        StyleManager.SPACING_LG, StyleManager.SPACING_MD)
        titulo = QLabel("Atalhos do teclado")
        titulo.setObjectName("foco_atalhos_titulo")
        layout_lista.addWidget(titulo)
        linhas = "".join(f"<tr><td style='padding: 3px 18px 3px 0;'><b>{tecla}</b></td>"
                         f"<td style='padding: 3px 0;'>{texto}</td></tr>" for tecla, texto in ATALHOS)
        tabela = QLabel(f"<table>{linhas}</table>")
        tabela.setTextFormat(Qt.RichText)
        layout_lista.addWidget(tabela)
        layout_lista.addWidget(QLabel("Esc fecha esta lista."))
        lista_atalhos.hide()

        # --- Ficha (gaveta) ---
        gaveta = Gaveta(palco, largura=LARGURA_FICHA)
        cabeca = QHBoxLayout()
        cabeca.setContentsMargins(StyleManager.SPACING_MD, StyleManager.SPACING_SM,
                                  StyleManager.SPACING_SM, 0)
        lbl_ficha = QLabel("Ficha da espécie")
        lbl_ficha.setObjectName("quadro_gaveta_titulo")
        btn_fechar = QPushButton("Fechar")
        btn_fechar.setCursor(Qt.PointingHandCursor)
        btn_fechar.setToolTip("Fechar a ficha (Esc)")
        cabeca.addWidget(lbl_ficha, 1)
        cabeca.addWidget(btn_fechar)
        gaveta.layout_conteudo.addLayout(cabeca)

        fotos = QWidget()
        layout_fotos = QHBoxLayout(fotos)
        layout_fotos.setContentsMargins(0, 0, 0, 0)
        layout_fotos.setSpacing(StyleManager.SPACING_SM)
        layout_fotos.addWidget(_coluna(p.foto, p.btn_lens), 1)
        layout_fotos.addWidget(_coluna(p.referencia, p.btn_fonte), 1)
        if p.cartoes is not None and hasattr(p.cartoes, "definir_orientacao"):
            p.cartoes.definir_orientacao("vertical")
        abas = QTabWidget()
        abas.setObjectName("abas_especie")
        abas.addTab(coluna_rolavel(fotos, p.cartoes, p.buscas), "Comparar")
        abas.addTab(coluna_rolavel(p.descricao, p.etimologia), "Sobre")
        abas.addTab(coluna_rolavel(p.taxonomia, p.conservacao), "Classificação")
        abas.addTab(coluna_rolavel(p.mapa, p.geo), "Mapa")
        abas.addTab(coluna_rolavel(p.sons), "Sons")
        corpo = QWidget()
        layout_corpo = QVBoxLayout(corpo)
        layout_corpo.setContentsMargins(StyleManager.SPACING_MD, 0, StyleManager.SPACING_MD,
                                        StyleManager.SPACING_MD)
        layout_corpo.setSpacing(StyleManager.SPACING_SM)
        layout_corpo.addWidget(abas, 1)
        rodape = QHBoxLayout()
        rodape.addWidget(p.btn_nova)
        rodape.addStretch()
        rodape.addWidget(p.btn_publicar)
        layout_corpo.addLayout(rodape)
        gaveta.layout_conteudo.addWidget(corpo, 1)

        controle = _ControleFoco(raiz, p, estado, palco, gaveta, pilula, caixa_fila, lista_atalhos, abas)
        btn_ficha.clicked.connect(controle.alternar_ficha)
        btn_fechar.clicked.connect(gaveta.fechar)
        btn_atalhos.clicked.connect(controle.alternar_atalhos)
        if caixa_fila is not None and hasattr(p.fila, "lista"):
            # A fila aparece quando uma pasta carrega e some quando a lista é esvaziada
            modelo = p.fila.lista.model()
            modelo.rowsInserted.connect(controle.atualizar_fila)
            modelo.rowsRemoved.connect(controle.atualizar_fila)
            modelo.modelReset.connect(controle.atualizar_fila)
        raiz.controle_foco = controle  # para testes
        return raiz
