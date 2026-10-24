#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Layout "Painel completo": a tela de sempre do iBirder (até a v1.3), com tudo visível
numa grade de 3 colunas e rolagem vertical.

    Imagem pesquisada | Imagem referência | Identificação, etimologia, taxonomia
    Google Lens       | Abrir fonte       | WikiAves  eBird  Google
    Descrição da espécie (2 colunas)      | Conservação
    Nova identificação (2 colunas)        | Gravar dados na fotografia
    Mapa (2 colunas)                      | Dados geográficos, vocalizações
"""

from PySide6.QtWidgets import QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from core.style_manager import StyleManager
from ui.layouts.base import Layout, Paineis


def _titulo(texto):
    rotulo = QLabel(texto)
    rotulo.setProperty("class", "lbl-titulo-sessao")
    return rotulo


def _coluna(*widgets):
    """Painéis empilhados sem margem (ficam colados na mesma célula da grade)."""
    coluna = QWidget()
    layout = QVBoxLayout(coluna)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(StyleManager.SPACING_MD)
    for widget in widgets:
        layout.addWidget(widget)
    return coluna


class LayoutCompleto(Layout):
    id = "completo"
    nome = "Painel completo"
    descricao = "A tela de sempre: tudo visível numa grade de três colunas, com rolagem."

    def montar(self, p: Paineis, estado=None) -> QWidget:
        # Fundo da área de rolagem vem do tema (QScrollArea#area_rolagem)
        rolagem = QScrollArea()
        rolagem.setObjectName("area_rolagem")
        rolagem.setWidgetResizable(True)

        conteudo = QWidget()
        conteudo.setObjectName("container_rolagem")
        rolagem.setWidget(conteudo)

        mestre = QVBoxLayout(conteudo)
        margem = StyleManager.SPACING_MD
        mestre.setContentsMargins(margem, margem, margem, margem)
        mestre.setSpacing(StyleManager.SPACING_SM)
        mestre.addWidget(p.cabecalho)
        mestre.addSpacing(StyleManager.SPACING_LG)

        grade = QGridLayout()
        grade.setSpacing(15)
        for coluna in range(3):  # colunas simétricas
            grade.setColumnStretch(coluna, 1)

        grade.addWidget(_titulo("Imagem Pesquisada"), 0, 0)
        grade.addWidget(_titulo("Imagem Referência"), 0, 1)
        grade.addWidget(_titulo("Resultados da Análise"), 0, 2)

        grade.addWidget(p.foto, 1, 0)
        grade.addWidget(p.referencia, 1, 1)
        grade.addWidget(_coluna(p.identificacao, p.etimologia, p.taxonomia), 1, 2)

        grade.addWidget(p.btn_lens, 2, 0)
        grade.addWidget(p.btn_fonte, 2, 1)
        grade.addWidget(p.buscas, 2, 2)

        grade.addWidget(p.descricao, 3, 0, 1, 2)
        grade.addWidget(p.conservacao, 3, 2)

        grade.addWidget(p.btn_nova, 4, 0, 1, 2)
        grade.addWidget(p.btn_gravar, 4, 2)

        grade.addWidget(p.mapa, 5, 0, 2, 2)
        grade.addWidget(_coluna(p.geo, p.sons), 5, 2)

        mestre.addLayout(grade)
        mestre.addStretch()
        return rolagem
