#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Layout "Mesa de trabalho" (proposta B do redesenho): uma pasta inteira em fila.

    [cabeçalho]
    Fila de fotos     | Foto | Referência                 | [Descrição | Classificação | Local | Sons]
    (miniaturas e     | Lens | Abrir fonte                |
     situação de      | Identificação (nome, sugestões)  |
     cada foto)       | WikiAves  eBird  Google          |
    Nova identificação                     Publicar no iNaturalist   Gravar dados na fotografia

Com "Ir para a próxima ao gravar" ligado (no painel da fila), gravar abre sozinho a
próxima foto pendente. A janela não rola: a coluna central e cada aba rolam sozinhas.
"""

from PySide6.QtWidgets import QHBoxLayout, QTabWidget, QVBoxLayout, QWidget

from core.style_manager import StyleManager
from ui.layouts.base import Layout, Paineis, coluna_rolavel

LARGURA_FILA = 300


class LayoutMesa(Layout):
    id = "mesa"
    nome = "Mesa de trabalho"
    descricao = "Uma pasta inteira em fila: grave e vá para a próxima foto."
    paineis_extras = ("fila",)

    def montar(self, p: Paineis, estado=None) -> QWidget:
        raiz = QWidget()
        raiz.setObjectName("container_rolagem")  # fundo do tema
        mestre = QVBoxLayout(raiz)
        margem = StyleManager.SPACING_MD
        mestre.setContentsMargins(margem, margem, margem, margem)
        mestre.setSpacing(StyleManager.SPACING_SM)
        mestre.addWidget(p.cabecalho)

        # Centro: as duas fotos lado a lado (quadradas), botões e identificação
        fotos = QWidget()
        layout_fotos = QHBoxLayout(fotos)
        layout_fotos.setContentsMargins(0, 0, 0, 0)
        layout_fotos.setSpacing(StyleManager.SPACING_SM)
        layout_fotos.addWidget(p.foto, 1)
        layout_fotos.addWidget(p.referencia, 1)
        botoes_foto = QWidget()
        layout_botoes = QHBoxLayout(botoes_foto)
        layout_botoes.setContentsMargins(0, 0, 0, 0)
        layout_botoes.setSpacing(StyleManager.SPACING_SM)
        layout_botoes.addWidget(p.btn_lens)
        layout_botoes.addWidget(p.btn_fonte)
        col_centro = coluna_rolavel(fotos, botoes_foto, p.identificacao, p.buscas, margem=4,
                                    espaco=StyleManager.SPACING_SM)
        # As fotos lado a lado têm largura mínima (cards quadrados): a coluna não fica mais
        # estreita que elas, senão a referência seria cortada (a rolagem é só vertical)
        col_centro.setMinimumWidth(col_centro.widget().minimumSizeHint().width()
                                   + col_centro.verticalScrollBar().sizeHint().width())

        # Direita: o resto da ficha da espécie em abas
        abas = QTabWidget()
        abas.setObjectName("abas_especie")
        abas.addTab(coluna_rolavel(p.descricao, p.etimologia), "Descrição")
        abas.addTab(coluna_rolavel(p.taxonomia, p.conservacao), "Classificação")
        abas.addTab(coluna_rolavel(p.mapa, p.geo), "Local")
        abas.addTab(coluna_rolavel(p.sons), "Sons")

        p.fila.setMinimumWidth(LARGURA_FILA - 60)
        p.fila.setMaximumWidth(LARGURA_FILA + 60)

        corpo = QHBoxLayout()
        corpo.setSpacing(StyleManager.SPACING_LG)
        corpo.addWidget(p.fila, 3)
        corpo.addWidget(col_centro, 6)
        corpo.addWidget(abas, 4)
        mestre.addLayout(corpo, 1)

        acoes = QHBoxLayout()
        acoes.setSpacing(StyleManager.SPACING_SM)
        acoes.addWidget(p.btn_nova)
        acoes.addStretch()
        acoes.addWidget(p.btn_publicar)
        acoes.addWidget(p.btn_gravar)
        mestre.addLayout(acoes)
        return raiz
