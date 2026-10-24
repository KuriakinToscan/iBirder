#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Layout "Ficha compacta" (proposta C do redesenho): tudo numa tela, em três colunas,
como a ficha de campo de uma espécie.

    [cabeçalho]
    Foto       | Identificação (nome, certeza, sugestões) | Mapa
    Referência | Descrição, etimologia                    | Dados geográficos
    Lens Fonte | Taxonomia, conservação                   | Vocalizações
    WikiAves eBird Google     Nova identificação   Publicar no iNaturalist   Gravar

A janela não rola: cada coluna rola sozinha quando o conteúdo passa da altura.
A busca rápida de espécies (Ctrl+K) leva direto ao campo do nome científico.
"""

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from core.style_manager import StyleManager
from ui.layouts.base import Layout, Paineis, coluna_rolavel


class LayoutFicha(Layout):
    id = "ficha"
    nome = "Ficha compacta"
    descricao = "Tudo numa tela só, em três colunas, com busca rápida de espécies (Ctrl+K)."

    def montar(self, p: Paineis, estado=None) -> QWidget:
        raiz = QWidget()
        raiz.setObjectName("container_rolagem")  # fundo do tema
        mestre = QVBoxLayout(raiz)
        margem = StyleManager.SPACING_MD
        mestre.setContentsMargins(margem, margem, margem, margem)
        mestre.setSpacing(StyleManager.SPACING_SM)
        mestre.addWidget(p.cabecalho)

        # Fotos empilhadas (quadradas): a coluna rola se a janela for baixa
        botoes_foto = QWidget()
        layout_botoes = QHBoxLayout(botoes_foto)
        layout_botoes.setContentsMargins(0, 0, 0, 0)
        layout_botoes.setSpacing(StyleManager.SPACING_SM)
        layout_botoes.addWidget(p.btn_lens)
        layout_botoes.addWidget(p.btn_fonte)
        col_fotos = coluna_rolavel(p.foto, p.referencia, botoes_foto, margem=4,
                                   espaco=StyleManager.SPACING_SM)

        col_especie = coluna_rolavel(p.identificacao, p.descricao, p.etimologia,
                                     p.taxonomia, p.conservacao, margem=4,
                                     espaco=StyleManager.SPACING_MD)
        col_local = coluna_rolavel(p.mapa, p.geo, p.sons, margem=4,
                                   espaco=StyleManager.SPACING_MD)

        corpo = QHBoxLayout()
        corpo.setSpacing(StyleManager.SPACING_LG)
        corpo.addWidget(col_fotos, 3)
        corpo.addWidget(col_especie, 5)
        corpo.addWidget(col_local, 4)
        mestre.addLayout(corpo, 1)

        acoes = QHBoxLayout()
        acoes.setSpacing(StyleManager.SPACING_SM)
        acoes.addWidget(p.buscas)
        acoes.addStretch()
        acoes.addWidget(p.btn_nova)
        acoes.addWidget(p.btn_publicar)
        acoes.addWidget(p.btn_gravar)
        mestre.addLayout(acoes)
        return raiz
