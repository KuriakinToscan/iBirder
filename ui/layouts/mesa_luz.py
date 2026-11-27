#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Layout "Mesa de luz" (proposta 2 do redesenho, v1.6): a foto grande no centro, a fila da
pasta numa tira embaixo e um inspetor com seções à direita, como num editor de fotos.

    [cabeçalho]
    +-------------------------+------------+  Identificação (nome, certeza)
    |                         | referência |  ▾ Outras sugestões (cartões compactos)
    |        sua foto         | [Fonte]    |  ▸ Sobre a espécie
    |                         |            |  ▸ Classificação e conservação
    |                         | [Lens]     |  ▸ Local e mapa
    +-------------------------+------------+  ▸ Sons
                                              [Gravar dados na fotografia]
                                              [Publicar]  [Nova identificação]
    Fila | miniatura miniatura miniatura miniatura ...

A referência fica numa coluna ao lado da foto (antes flutuava por cima dela e, em janela
estreita, cobria a foto). Sem pasta aberta, a tira da fila fica só com a barra de botões.

As setas ← → abrem a foto anterior ou a seguinte da pasta (no campo de texto, continuam
movendo o cursor). Com "Ir para a próxima ao gravar" (na tira), gravar abre a próxima
pendente. O inspetor abre uma seção por vez; "Outras sugestões" abre a cada foto.
"""

import shiboken6
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from core.style_manager import StyleManager
from ui import estado_identificacao as ei
from ui.layouts.base import Layout, Paineis
from ui.widgets.componentes_layout import GrupoSecoes, PortaFoto, SecaoRecolhivel

LARGURA_INSPETOR = 380
LARGURA_REFERENCIA = 250  # mínimo do card de imagem (ImageCard)


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


class _ControleMesaLuz(QObject):
    """Abre "Outras sugestões" a cada resultado e liga as setas à fila."""

    def __init__(self, raiz, p: Paineis, estado, secao_sugestoes, porta):
        super().__init__(raiz)
        self.p = p
        self.secao_sugestoes = secao_sugestoes
        porta.receber(p.foto)
        lista = getattr(p.fila, "lista", None)
        if lista is not None:
            # A tira encolhe sem pasta e volta ao tamanho cheio quando a pasta carrega
            modelo = lista.model()
            modelo.rowsInserted.connect(self.ajustar_tira)
            modelo.rowsRemoved.connect(self.ajustar_tira)
            modelo.modelReset.connect(self.ajustar_tira)
            self.ajustar_tira()
        for tecla, passo in ((Qt.Key_Left, -1), (Qt.Key_Right, 1)):
            atalho = QShortcut(QKeySequence(tecla), raiz)
            atalho.setContext(Qt.WidgetWithChildrenShortcut)
            atalho.activated.connect(lambda passo=passo: self.navegar(passo))
        if estado is not None:
            estado.etapa_alterada.connect(self._ao_mudar_etapa)

    def ajustar_tira(self, *_args):
        """Sem fotos na fila, a tira fica só com a barra (PainelFila.ajustar_tira_vazia)."""
        fila = self.p.fila
        if fila is not None and shiboken6.isValid(fila) and hasattr(fila, "ajustar_tira_vazia"):
            fila.ajustar_tira_vazia()

    def _ao_mudar_etapa(self, etapa):
        if etapa in (ei.CONFERIR, ei.INCONCLUSIVA) and not self.secao_sugestoes.esta_aberta():
            self.secao_sugestoes.abrir()

    def navegar(self, passo):
        fila = self.p.fila
        if fila is not None and hasattr(fila, "abrir_vizinha"):
            return fila.abrir_vizinha(passo)
        return False


class LayoutMesaLuz(Layout):
    id = "mesa_luz"
    nome = "Mesa de luz"
    descricao = "Foto grande no centro, fila numa tira embaixo e a ficha em seções à direita."
    paineis_extras = ("fila", "cartoes")

    def montar(self, p: Paineis, estado=None) -> QWidget:
        raiz = QWidget()
        raiz.setObjectName("container_rolagem")
        mestre = QVBoxLayout(raiz)
        margem = StyleManager.SPACING_MD
        mestre.setContentsMargins(margem, margem, margem, StyleManager.SPACING_SM)
        mestre.setSpacing(StyleManager.SPACING_SM)
        mestre.addWidget(p.cabecalho)

        corpo = QHBoxLayout()
        corpo.setSpacing(StyleManager.SPACING_MD)
        mestre.addLayout(corpo, 1)

        # --- Palco: a foto e, ao lado, a referência com os botões ---
        palco = QFrame()
        palco.setObjectName("mesa_luz_palco")
        layout_palco = QHBoxLayout(palco)
        layout_palco.setContentsMargins(StyleManager.SPACING_SM, StyleManager.SPACING_SM,
                                        StyleManager.SPACING_SM, StyleManager.SPACING_SM)
        layout_palco.setSpacing(StyleManager.SPACING_MD)
        porta = PortaFoto(alinhamento="centro")
        layout_palco.addWidget(porta, 1)

        lateral = QWidget()
        lateral.setFixedWidth(LARGURA_REFERENCIA)
        layout_lateral = QVBoxLayout(lateral)
        layout_lateral.setContentsMargins(0, 0, 0, 0)
        layout_lateral.setSpacing(StyleManager.SPACING_SM)
        layout_lateral.addWidget(p.referencia)
        layout_lateral.addWidget(p.btn_fonte)
        layout_lateral.addStretch()
        layout_lateral.addWidget(p.btn_lens)
        layout_palco.addWidget(lateral, 0)
        corpo.addWidget(palco, 1)

        # --- Inspetor: identificação, seções e ações ---
        grupo = GrupoSecoes(exclusivo=True, parent=raiz)
        if p.cartoes is not None and hasattr(p.cartoes, "definir_orientacao"):
            p.cartoes.definir_orientacao("vertical")
        secao_sugestoes = grupo.adicionar(SecaoRecolhivel("Outras sugestões", p.cartoes, aberta=True))
        secoes = [
            secao_sugestoes,
            grupo.adicionar(SecaoRecolhivel("Sobre a espécie", _coluna(p.descricao, p.etimologia, p.buscas),
                                            aberta=False)),
            grupo.adicionar(SecaoRecolhivel("Classificação e conservação", _coluna(p.taxonomia, p.conservacao),
                                            aberta=False)),
            grupo.adicionar(SecaoRecolhivel("Local e mapa", _coluna(p.mapa, p.geo), aberta=False)),
            grupo.adicionar(SecaoRecolhivel("Sons", p.sons, aberta=False)),
        ]
        conteudo = QWidget()
        conteudo.setObjectName("container_rolagem")
        layout_conteudo = QVBoxLayout(conteudo)
        layout_conteudo.setContentsMargins(0, 0, 0, 0)
        layout_conteudo.setSpacing(0)
        layout_conteudo.addWidget(p.identificacao)
        layout_conteudo.addSpacing(StyleManager.SPACING_SM)
        for secao in secoes:
            layout_conteudo.addWidget(secao)
        layout_conteudo.addStretch()
        rolagem = QScrollArea()
        rolagem.setObjectName("area_rolagem")
        rolagem.setWidgetResizable(True)
        rolagem.setFrameShape(QFrame.NoFrame)
        rolagem.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        rolagem.setWidget(conteudo)

        acoes_secundarias = QHBoxLayout()
        acoes_secundarias.setSpacing(StyleManager.SPACING_SM)
        acoes_secundarias.addWidget(p.btn_publicar, 1)
        acoes_secundarias.addWidget(p.btn_nova, 1)
        inspetor = QFrame()
        inspetor.setObjectName("mesa_luz_inspetor")
        inspetor.setFixedWidth(LARGURA_INSPETOR)
        layout_inspetor = QVBoxLayout(inspetor)
        layout_inspetor.setContentsMargins(0, 0, 0, 0)
        layout_inspetor.setSpacing(StyleManager.SPACING_SM)
        layout_inspetor.addWidget(rolagem, 1)
        layout_inspetor.addWidget(p.btn_gravar)
        layout_inspetor.addLayout(acoes_secundarias)
        corpo.addWidget(inspetor, 0)

        # --- Tira da fila ---
        if p.fila is not None:
            if hasattr(p.fila, "definir_vista"):
                p.fila.definir_vista("tira")
            mestre.addWidget(p.fila)

        controle = _ControleMesaLuz(raiz, p, estado, secao_sugestoes, porta)
        raiz.controle_mesa_luz = controle  # para testes
        raiz.secoes_inspetor = secoes
        return raiz
