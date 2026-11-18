#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Layout "Quadro da sessão" (proposta 5 do redesenho, v1.6): a pasta da saída de campo
em colunas, e a foto aberta numa gaveta à direita.

    [cabeçalho]
    Fila de fotos  [Abrir pasta...]   5 espécies · 7 gravadas de 12 · ...   Nova identificação
    | Na fila      | Conferindo agora | Gravadas         | Puladas |   +-- gaveta -----------+
    | miniaturas   | a foto aberta    | com a espécie    |         |   | Conferir | Ficha     |
    |              |                  |                  |         |   | foto | referência    |
    Sessões anteriores: [Saída 1] [Saída 2]                            | resultado, cartões   |
    Ir para a próxima ao gravar  [Pular]                               | Publicar     Gravar  |

"Sessão" é a pasta aberta: nenhum arquivo novo é criado na pasta do usuário. A coluna de
cada foto vem da fila (que lê os registros já gravados nas fotos); ao gravar, o cartão vai
para "Gravadas". A gaveta abre quando uma foto é aberta, fecha em "Fechar" (a foto continua
aberta: um clique duplo no cartão dela reabre) e vai para a aba Ficha quando a espécie é
confirmada.
"""

from pathlib import Path

import shiboken6
from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QTabWidget,
                               QVBoxLayout, QWidget)

from core.style_manager import StyleManager
from ui import estado_identificacao as ei
from ui.layouts.base import Layout, Paineis, coluna_rolavel
from ui.widgets.componentes_layout import Gaveta

LARGURA_GAVETA = 640
ABA_CONFERIR, ABA_FICHA = range(2)


def _coluna(*widgets, espaco=StyleManager.SPACING_SM):
    coluna = QWidget()
    layout = QVBoxLayout(coluna)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(espaco)
    for widget in widgets:
        if widget is not None:
            layout.addWidget(widget)
    return coluna


class _ControleQuadro(QObject):
    """Abre e fecha a gaveta conforme a foto aberta e escolhe a aba."""

    def __init__(self, raiz, p: Paineis, estado, gaveta, abas, lbl_arquivo, btn_fechar):
        super().__init__(raiz)
        self.p = p
        self.estado = estado
        self.gaveta = gaveta
        self.abas = abas
        self.lbl_arquivo = lbl_arquivo
        btn_fechar.clicked.connect(gaveta.fechar)
        if p.fila is not None and hasattr(p.fila, "atual_ativada"):
            p.fila.atual_ativada.connect(gaveta.abrir)
        if estado is not None:
            estado.etapa_alterada.connect(self._ao_mudar_etapa)
            estado.alterado.connect(self._atualizar_titulo)
            # Método (não lambda): a conexão some junto com o layout, e o estado continua
            estado.especie_confirmada.connect(self._ao_confirmar)
            self._ao_mudar_etapa(estado.etapa)

    def _vivo(self):
        """Na troca de layout, a raiz destrói os filhos antes deste controle, e o estado
        (que continua vivo) ainda pode emitir nesse intervalo."""
        return all(shiboken6.isValid(w) for w in (self.gaveta, self.abas, self.lbl_arquivo))

    def _ao_confirmar(self, _nome=None):
        if self._vivo():
            self.abas.setCurrentIndex(ABA_FICHA)

    def _ao_mudar_etapa(self, etapa):
        if not self._vivo():
            return
        if etapa == ei.SEM_FOTO:
            self.gaveta.fechar()
        elif etapa == ei.IDENTIFICANDO:
            self.abas.setCurrentIndex(ABA_CONFERIR)
            self.gaveta.abrir()
        elif etapa in (ei.CONFERIR, ei.INCONCLUSIVA, ei.ERRO) and not self.gaveta.esta_aberta():
            self.gaveta.abrir()  # nome digitado sem foto aberta também abre a gaveta
        self._atualizar_titulo()

    def _atualizar_titulo(self):
        if not self._vivo():
            return
        estado = self.estado
        caminho = estado.caminho if estado is not None else None
        etapa = estado.etapa if estado is not None else ei.SEM_FOTO
        rotulo = "Gravada" if etapa == ei.GRAVADA else "Conferindo agora"
        nome = Path(caminho).name if caminho else "sem foto aberta"
        self.lbl_arquivo.setText(f"{rotulo}  ·  {nome}")


class LayoutQuadro(Layout):
    id = "quadro"
    nome = "Quadro da sessão"
    descricao = "A pasta da saída de campo em colunas: na fila, conferindo agora, gravadas e puladas."
    paineis_extras = ("fila", "cartoes")

    def montar(self, p: Paineis, estado=None) -> QWidget:
        raiz = QWidget()
        raiz.setObjectName("container_rolagem")
        mestre = QVBoxLayout(raiz)
        margem = StyleManager.SPACING_MD
        mestre.setContentsMargins(margem, margem, margem, margem)
        mestre.setSpacing(StyleManager.SPACING_SM)
        mestre.addWidget(p.cabecalho)

        # --- Área do quadro (hospedeiro da gaveta) ---
        area = QWidget()
        area.setObjectName("quadro_area")
        layout_area = QVBoxLayout(area)
        layout_area.setContentsMargins(0, 0, 0, 0)
        layout_area.setSpacing(StyleManager.SPACING_SM)
        acoes = QHBoxLayout()
        acoes.addStretch()
        acoes.addWidget(p.btn_nova)
        layout_area.addLayout(acoes)
        # A gaveta cobre só o quadro: "Nova identificação" continua à vista
        area_quadro = QWidget()
        layout_quadro = QVBoxLayout(area_quadro)
        layout_quadro.setContentsMargins(0, 0, 0, 0)
        if p.fila is not None:
            if hasattr(p.fila, "definir_vista"):
                p.fila.definir_vista("colunas")
            layout_quadro.addWidget(p.fila, 1)
        layout_area.addWidget(area_quadro, 1)
        mestre.addWidget(area, 1)

        # --- Gaveta: conferir e ficha da foto aberta ---
        gaveta = Gaveta(area_quadro, largura=LARGURA_GAVETA)
        cabeca = QHBoxLayout()
        cabeca.setContentsMargins(StyleManager.SPACING_MD, StyleManager.SPACING_SM,
                                  StyleManager.SPACING_SM, 0)
        lbl_arquivo = QLabel("Conferindo agora")
        lbl_arquivo.setObjectName("quadro_gaveta_titulo")
        btn_fechar = QPushButton("Fechar")
        btn_fechar.setObjectName("quadro_gaveta_fechar")
        btn_fechar.setCursor(Qt.PointingHandCursor)
        btn_fechar.setToolTip("Fechar a gaveta (a foto continua aberta; clique duas vezes no cartão para voltar)")
        cabeca.addWidget(lbl_arquivo, 1)
        cabeca.addWidget(btn_fechar)
        gaveta.layout_conteudo.addLayout(cabeca)

        fotos = QHBoxLayout()
        fotos.setSpacing(StyleManager.SPACING_MD)
        fotos.addWidget(_coluna(p.foto, p.btn_lens), 1)
        fotos.addWidget(_coluna(p.referencia, p.btn_fonte), 1)
        if p.cartoes is not None and hasattr(p.cartoes, "definir_orientacao"):
            p.cartoes.definir_orientacao("vertical")
        conferir = QWidget()
        layout_conferir = QVBoxLayout(conferir)
        layout_conferir.setSpacing(StyleManager.SPACING_MD)
        layout_conferir.addLayout(fotos)
        layout_conferir.addWidget(p.identificacao)
        if p.cartoes is not None:
            layout_conferir.addWidget(p.cartoes)
        layout_conferir.addStretch()
        rolagem_conferir = QScrollArea()
        rolagem_conferir.setObjectName("area_rolagem")
        rolagem_conferir.setWidgetResizable(True)
        rolagem_conferir.setFrameShape(QFrame.NoFrame)
        rolagem_conferir.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        conferir.setObjectName("container_rolagem")
        rolagem_conferir.setWidget(conferir)

        abas = QTabWidget()
        abas.setObjectName("abas_especie")
        abas.addTab(rolagem_conferir, "Conferir")
        abas.addTab(coluna_rolavel(p.buscas, p.descricao, p.etimologia, p.taxonomia, p.conservacao,
                                   p.mapa, p.geo, p.sons), "Ficha")
        corpo_gaveta = QWidget()
        layout_corpo = QVBoxLayout(corpo_gaveta)
        layout_corpo.setContentsMargins(StyleManager.SPACING_MD, 0, StyleManager.SPACING_MD,
                                        StyleManager.SPACING_MD)
        layout_corpo.setSpacing(StyleManager.SPACING_SM)
        layout_corpo.addWidget(abas, 1)
        rodape = QHBoxLayout()
        rodape.addWidget(p.btn_publicar)
        rodape.addStretch()
        rodape.addWidget(p.btn_gravar)
        layout_corpo.addLayout(rodape)
        gaveta.layout_conteudo.addWidget(corpo_gaveta, 1)

        controle = _ControleQuadro(raiz, p, estado, gaveta, abas, lbl_arquivo, btn_fechar)
        raiz.controle_quadro = controle  # para testes
        return raiz
