#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Base dos layouts da janela principal (v1.4).

A janela cria os painéis uma vez (cards de foto, identificação, taxonomia, mapa...) e
toda a lógica continua falando com eles. Um layout só decide ONDE cada painel fica:
`montar()` devolve o widget central com os painéis encaixados. Trocar de layout é
montar outro widget com os mesmos painéis, sem perder o que já está na tela.
"""

from dataclasses import dataclass, fields

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget


@dataclass
class Paineis:
    """Os blocos da janela principal que todo layout arruma."""
    cabecalho: QWidget        # logo, slogan e botões (recarregar, ajuda, configurações)
    foto: QWidget             # card da foto pesquisada (arrastar/clicar)
    referencia: QWidget       # card da imagem de referência
    identificacao: QWidget    # nome científico, certeza, candidatas, nomes comum e inglês
    etimologia: QWidget
    taxonomia: QWidget
    conservacao: QWidget
    descricao: QWidget        # descrição da espécie (WikiAves)
    btn_lens: QWidget         # Pesquisar com Google Lens
    btn_fonte: QWidget        # Abrir fonte da imagem de referência
    buscas: QWidget           # WikiAves, eBird, Google
    btn_nova: QWidget         # Nova identificação
    btn_gravar: QWidget       # Gravar dados na fotografia (ação principal)
    btn_publicar: QWidget     # Publicar no iNaturalist (issue #9)
    mapa: QWidget             # localização geográfica (Leaflet)
    geo: QWidget              # dados geográficos
    sons: QWidget             # vocalizações

    def todos(self):
        return [getattr(self, f.name) for f in fields(self)]


class Layout:
    """Um jeito de arrumar os painéis. Subclasses definem id, nome, descrição e montar()."""
    id = ""
    nome = ""
    descricao = ""

    def montar(self, paineis: Paineis, estado=None) -> QWidget:
        """
        Cria o widget central com todos os painéis (cada um usado uma única vez).
        `estado` (EstadoIdentificacao, opcional) serve aos layouts que mudam conforme a etapa.
        """
        raise NotImplementedError


def coluna_rolavel(*widgets, margem=8, espaco=12):
    """
    Coluna de painéis com rolagem própria, para layouts em que a janela não rola
    (Fluxo guiado, Ficha compacta). O fundo vem do tema (#area_rolagem).
    """
    rolagem = QScrollArea()
    rolagem.setObjectName("area_rolagem")
    rolagem.setWidgetResizable(True)
    rolagem.setFrameShape(QFrame.NoFrame)
    rolagem.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # só rola na vertical
    conteudo = QWidget()
    conteudo.setObjectName("container_rolagem")
    layout = QVBoxLayout(conteudo)
    layout.setContentsMargins(margem, margem, margem, margem)
    layout.setSpacing(espaco)
    for widget in widgets:
        layout.addWidget(widget)
    layout.addStretch()
    rolagem.setWidget(conteudo)
    return rolagem
