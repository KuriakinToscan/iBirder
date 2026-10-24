#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Layout "Fluxo guiado" (proposta A do redesenho): uma etapa por vez.

    [cabeçalho]
    1 Foto  ›  2 Identificação  ›  3 Conferir  ›  4 Gravar      dica da etapa atual
    Foto | Referência          | Identificação (nome, certeza, sugestões)
    Lens | Abrir fonte         | WikiAves  eBird  Google
                               | [Descrição | Classificação | Local | Sons]
    Nova identificação                         Gravar dados na fotografia

Sem foto aberta, só o card da foto aparece, grande e centralizado, com a dica
"arraste uma foto ou Ctrl+O". A barra de etapas e a dica seguem o EstadoIdentificacao.
Sem rolagem na janela: o que não cabe fica nas abas (cada aba rola sozinha).
"""

from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QScrollArea, QTabWidget,
                               QVBoxLayout, QWidget)

from core.style_manager import StyleManager
from ui import estado_identificacao as ei
from ui.layouts.base import Layout, Paineis, coluna_rolavel as _aba

ETAPAS_BARRA = ("Foto", "Identificação", "Conferir", "Gravar")

# Etapa do estado -> posição na barra (0 a 3) e dica exibida ao lado
POSICAO = {
    ei.SEM_FOTO: 0,
    ei.IDENTIFICANDO: 1,
    ei.CONFERIR: 2,
    ei.INCONCLUSIVA: 2,
    ei.ERRO: 2,
    ei.GRAVADA: 3,
}
DICAS = {
    ei.SEM_FOTO: "Arraste uma foto para o quadro ou pressione Ctrl+O.",
    ei.IDENTIFICANDO: "Identificando a ave...",
    ei.CONFERIR: "Confira a espécie e grave os dados na foto (Ctrl+S).",
    ei.INCONCLUSIVA: "A IA não teve certeza: escolha uma sugestão ou digite o nome científico.",
    ei.ERRO: "A identificação falhou: digite o nome científico ou abra outra foto.",
    ei.GRAVADA: "Dados gravados. Abra a próxima foto (Ctrl+O).",
}

LARGURA_FOTO_INICIAL = 400  # card da foto sozinho, antes de abrir uma (é sempre quadrado)


def _coluna(*widgets, espaco=StyleManager.SPACING_SM):
    coluna = QWidget()
    layout = QVBoxLayout(coluna)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(espaco)
    for widget in widgets:
        layout.addWidget(widget)
    return coluna


def _definir_classe(widget, classe):
    widget.setProperty("class", classe)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class BarraEtapas(QWidget):
    """Foto › Identificação › Conferir › Gravar, com a etapa atual em destaque e uma dica."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(StyleManager.SPACING_XS)
        self.rotulos = []
        for n, nome in enumerate(ETAPAS_BARRA, 1):
            if n > 1:
                seta = QLabel("›")
                seta.setProperty("class", "etapa-seta")
                layout.addWidget(seta)
            rotulo = QLabel(f"{n}  {nome}")
            rotulo.setProperty("class", "etapa")
            layout.addWidget(rotulo)
            self.rotulos.append(rotulo)
        layout.addSpacing(StyleManager.SPACING_LG)
        self.lbl_dica = QLabel()
        self.lbl_dica.setObjectName("lbl_dica_etapa")
        self.lbl_dica.setWordWrap(True)
        layout.addWidget(self.lbl_dica, 1)

    def mostrar(self, etapa):
        atual = POSICAO.get(etapa, 0)
        gravada = etapa == ei.GRAVADA
        for i, rotulo in enumerate(self.rotulos):
            feita = i < atual or (gravada and i == atual)
            if feita:
                classe = "etapa etapa-feita"
            elif i == atual:
                classe = "etapa etapa-ativa"
            else:
                classe = "etapa"
            # Etapa concluída ganha ✓ no lugar do número (não depende só da cor)
            rotulo.setText(f"{'✓' if feita else i + 1}  {ETAPAS_BARRA[i]}")
            _definir_classe(rotulo, classe)
        self.lbl_dica.setText(DICAS.get(etapa, ""))


class _ControleGuiado(QObject):
    """Mostra/esconde as áreas conforme a etapa. Filho do widget central: some junto com ele."""

    def __init__(self, raiz, barra, col_referencia, col_resultados, caixa_foto, fotos,
                 layout_col_fotos, abas, estado):
        super().__init__(raiz)
        self.barra = barra
        self.fotos = fotos
        self.layout_col_fotos = layout_col_fotos
        self.col_referencia = col_referencia
        self.col_resultados = col_resultados
        self.caixa_foto = caixa_foto
        self.abas = abas
        self._etapa = None
        if estado is not None:
            estado.etapa_alterada.connect(self.atualizar)
            self.atualizar(estado.etapa)
        else:
            self.atualizar(ei.SEM_FOTO)

    def atualizar(self, etapa):
        sem_foto = etapa == ei.SEM_FOTO
        self.barra.mostrar(etapa)
        self.col_referencia.setVisible(not sem_foto)
        self.col_resultados.setVisible(not sem_foto)
        # Sozinho, o card da foto fica grande e centralizado; depois divide espaço com a referência
        if sem_foto:
            self.caixa_foto.setFixedWidth(LARGURA_FOTO_INICIAL)
        else:
            self.caixa_foto.setMinimumWidth(0)
            self.caixa_foto.setMaximumWidth(16777215)
        self.layout_col_fotos.setAlignment(self.fotos, Qt.AlignHCenter if sem_foto else Qt.AlignmentFlag(0))
        if etapa == ei.CONFERIR and self._etapa != ei.CONFERIR:
            self.abas.setCurrentIndex(0)  # descrição da espécie recém-identificada
        self._etapa = etapa


class LayoutGuiado(Layout):
    id = "guiado"
    nome = "Fluxo guiado"
    descricao = "Uma etapa por vez: foto, identificação, conferência e gravação, sem rolar a tela."

    def montar(self, p: Paineis, estado=None) -> QWidget:
        raiz = QWidget()
        raiz.setObjectName("container_rolagem")  # mesmo fundo do tema que o Painel completo
        mestre = QVBoxLayout(raiz)
        margem = StyleManager.SPACING_MD
        mestre.setContentsMargins(margem, margem, margem, margem)
        mestre.setSpacing(StyleManager.SPACING_MD)
        mestre.addWidget(p.cabecalho)

        barra = BarraEtapas()
        mestre.addWidget(barra)

        # --- Fotos (esquerda) ---
        caixa_foto = _coluna(p.foto, p.btn_lens)
        col_referencia = _coluna(p.referencia, p.btn_fonte)
        fotos = QWidget()
        layout_fotos = QHBoxLayout(fotos)
        layout_fotos.setContentsMargins(0, 0, 0, 0)
        layout_fotos.setSpacing(StyleManager.SPACING_MD)
        layout_fotos.addWidget(caixa_foto, 1)
        layout_fotos.addWidget(col_referencia, 1)
        col_fotos = QWidget()
        layout_col_fotos = QVBoxLayout(col_fotos)
        layout_col_fotos.setContentsMargins(0, 0, 0, 0)
        layout_col_fotos.addWidget(fotos)
        layout_col_fotos.addStretch()
        # Os cards de foto são sempre quadrados (altura = largura): numa área de rolagem,
        # uma janela estreita ou baixa rola as fotos em vez de esticar a janela
        rolagem_fotos = QScrollArea()
        rolagem_fotos.setObjectName("area_rolagem")
        rolagem_fotos.setWidgetResizable(True)
        rolagem_fotos.setFrameShape(QFrame.NoFrame)
        rolagem_fotos.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        col_fotos.setObjectName("container_rolagem")
        rolagem_fotos.setWidget(col_fotos)

        # --- Resultados (direita): identificação, buscas e abas ---
        abas = QTabWidget()
        abas.setObjectName("abas_especie")
        abas.addTab(_aba(p.descricao, p.etimologia), "Descrição")
        abas.addTab(_aba(p.taxonomia, p.conservacao), "Classificação e conservação")
        abas.addTab(_aba(p.mapa, p.geo), "Local")
        abas.addTab(_aba(p.sons), "Sons")
        col_resultados = QWidget()
        layout_res = QVBoxLayout(col_resultados)
        layout_res.setContentsMargins(0, 0, 0, 0)
        layout_res.setSpacing(StyleManager.SPACING_SM)
        layout_res.addWidget(p.identificacao)
        layout_res.addWidget(p.buscas)
        layout_res.addWidget(abas, 1)

        corpo = QHBoxLayout()
        corpo.setSpacing(StyleManager.SPACING_LG)
        corpo.addWidget(rolagem_fotos, 5)
        corpo.addWidget(col_resultados, 6)
        mestre.addLayout(corpo, 1)

        # --- Barra de ações ---
        acoes = QHBoxLayout()
        acoes.addWidget(p.btn_nova)
        acoes.addStretch()
        acoes.addWidget(p.btn_gravar)
        mestre.addLayout(acoes)

        _ControleGuiado(raiz, barra, col_referencia, col_resultados, caixa_foto, fotos,
                        layout_col_fotos, abas, estado)
        return raiz
