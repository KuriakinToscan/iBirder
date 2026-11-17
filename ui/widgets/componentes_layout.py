#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Componentes comuns dos layouts da v1.6 (ui/layouts/), feitos uma vez e usados por vários:

- `SecaoRecolhivel`: título clicável que mostra ou esconde um conteúdo (inspetor da
  Mesa de luz). `GrupoSecoes` pode deixar só uma aberta por vez.
- `RodapeAcoes`: faixa de botões no pé da tela, com um lado esquerdo (Voltar, Nova
  identificação) e um direito (Continuar, Gravar) (Trilha, Cartões).
- `Sobreposicao`: widget que flutua sobre outro e se reposiciona sozinho quando o
  hospedeiro muda de tamanho (pílula de resultado do Foco).
- `Gaveta`: painel que entra pela borda direita do hospedeiro, com animação curta
  (ficha da espécie no Foco).

Nenhum deles tem cor fixa: os estilos vêm do QSS global (classes e objectNames abaixo).
"""

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, QRect, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from core.style_manager import StyleManager

DURACAO_ANIMACAO_MS = 160

SETA_ABERTA = "▾"
SETA_FECHADA = "▸"


class SecaoRecolhivel(QFrame):
    """Título clicável (com seta) e um conteúdo que aparece ou some."""

    alternada = Signal(bool)  # True = aberta

    def __init__(self, titulo, conteudo=None, aberta=True, parent=None):
        super().__init__(parent)
        self.setObjectName("secao_recolhivel")
        self._titulo = titulo
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.cabecalho = QPushButton()
        self.cabecalho.setObjectName("secao_cabecalho")
        self.cabecalho.setCursor(Qt.PointingHandCursor)
        self.cabecalho.setCheckable(True)
        self.cabecalho.toggled.connect(self._ao_alternar)
        layout.addWidget(self.cabecalho)

        self.corpo = QWidget()
        self.corpo.setObjectName("secao_corpo")
        self._layout_corpo = QVBoxLayout(self.corpo)
        self._layout_corpo.setContentsMargins(12, 4, 12, 12)
        self._layout_corpo.setSpacing(StyleManager.SPACING_SM)
        layout.addWidget(self.corpo)

        self._conteudo = None
        if conteudo is not None:
            self.definir_conteudo(conteudo)
        self.cabecalho.setChecked(aberta)
        self._ao_alternar(aberta)

    def definir_conteudo(self, widget):
        """Põe o widget dentro da seção (um painel compartilhado pode vir de outro layout)."""
        if self._conteudo is not None:
            self._layout_corpo.removeWidget(self._conteudo)
        self._conteudo = widget
        self._layout_corpo.addWidget(widget)
        widget.show()

    def conteudo(self):
        return self._conteudo

    def esta_aberta(self):
        return self.cabecalho.isChecked()

    def abrir(self, aberta=True):
        self.cabecalho.setChecked(aberta)

    def _ao_alternar(self, aberta):
        self.cabecalho.setText(f"{SETA_ABERTA if aberta else SETA_FECHADA}  {self._titulo}")
        self.corpo.setVisible(aberta)
        self.alternada.emit(aberta)


class GrupoSecoes(QObject):
    """Conjunto de seções; com `exclusivo`, abrir uma fecha as outras (acordeão)."""

    def __init__(self, exclusivo=True, parent=None):
        super().__init__(parent)
        self.exclusivo = exclusivo
        self.secoes = []

    def adicionar(self, secao):
        self.secoes.append(secao)
        secao.alternada.connect(lambda aberta, s=secao: self._ao_alternar(s, aberta))
        return secao

    def _ao_alternar(self, secao, aberta):
        if not (self.exclusivo and aberta):
            return
        for outra in self.secoes:
            if outra is not secao and outra.esta_aberta():
                outra.abrir(False)


class RodapeAcoes(QFrame):
    """Faixa de botões no pé da tela: ações à esquerda e à direita, com espaço no meio."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rodape_acoes")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(StyleManager.SPACING_LG, StyleManager.SPACING_MD,
                                  StyleManager.SPACING_LG, StyleManager.SPACING_MD)
        layout.setSpacing(StyleManager.SPACING_SM)
        self._esquerda = QHBoxLayout()
        self._esquerda.setSpacing(StyleManager.SPACING_SM)
        self._direita = QHBoxLayout()
        self._direita.setSpacing(StyleManager.SPACING_SM)
        layout.addLayout(self._esquerda)
        layout.addStretch(1)
        layout.addLayout(self._direita)

    def adicionar_esquerda(self, widget):
        self._esquerda.addWidget(widget)
        widget.show()
        return widget

    def adicionar_direita(self, widget):
        self._direita.addWidget(widget)
        widget.show()
        return widget


class _FiltroRedimensionar(QObject):
    """Chama `ao_redimensionar` quando o hospedeiro muda de tamanho."""

    def __init__(self, hospedeiro, ao_redimensionar):
        super().__init__(hospedeiro)
        self._callback = ao_redimensionar
        hospedeiro.installEventFilter(self)

    def eventFilter(self, obj, evento):
        if evento.type() in (QEvent.Resize, QEvent.Show):
            self._callback()
        return False


# Âncoras da Sobreposicao: (horizontal, vertical)
ANCORAS = {
    "superior-esquerda": ("esquerda", "topo"),
    "superior-centro": ("centro", "topo"),
    "superior-direita": ("direita", "topo"),
    "centro": ("centro", "centro"),
    "inferior-esquerda": ("esquerda", "base"),
    "inferior-centro": ("centro", "base"),
    "inferior-direita": ("direita", "base"),
    "esquerda": ("esquerda", "altura"),   # coluna ao longo da borda esquerda
    "direita": ("direita", "altura"),     # coluna ao longo da borda direita
}


def geometria_ancorada(largura_hosp, altura_hosp, largura, altura, ancora, margem):
    """Retângulo (x, y, largura, altura) do widget ancorado dentro do hospedeiro. Sem Qt."""
    horizontal, vertical = ANCORAS[ancora]
    largura = min(largura, max(0, largura_hosp - 2 * margem))
    if vertical == "altura":
        altura = max(0, altura_hosp - 2 * margem)
    else:
        altura = min(altura, max(0, altura_hosp - 2 * margem))
    x = {"esquerda": margem, "centro": (largura_hosp - largura) // 2,
         "direita": largura_hosp - largura - margem}[horizontal]
    y = {"topo": margem, "centro": (altura_hosp - altura) // 2,
         "base": altura_hosp - altura - margem, "altura": margem}[vertical]
    return x, y, largura, altura


class Sobreposicao(QFrame):
    """
    Widget que flutua sobre `hospedeiro`, preso a uma âncora ("inferior-centro",
    "superior-direita", "direita"...). Usa o tamanho sugerido do próprio conteúdo.
    """

    def __init__(self, hospedeiro, ancora="inferior-centro", margem=16, parent=None):
        super().__init__(parent or hospedeiro)
        if ancora not in ANCORAS:
            raise ValueError(f"Âncora desconhecida: {ancora}")
        self.setObjectName("sobreposicao")
        self.hospedeiro = hospedeiro
        self.ancora = ancora
        self.margem = margem
        self._filtro = _FiltroRedimensionar(hospedeiro, self.reposicionar)

    def reposicionar(self):
        hosp = self.hospedeiro
        # sizeHint() é (-1, -1) num QFrame sem layout: respeitar os limites de tamanho
        dica = self.sizeHint().expandedTo(self.minimumSize()).boundedTo(self.maximumSize())
        x, y, w, h = geometria_ancorada(hosp.width(), hosp.height(), dica.width(), dica.height(),
                                        self.ancora, self.margem)
        if self.parentWidget() is not hosp:
            x, y = (hosp.mapTo(self.parentWidget(), QPoint(x, y)).toTuple())
        self.setGeometry(x, y, w, h)
        self.raise_()

    def showEvent(self, evento):
        super().showEvent(evento)
        self.reposicionar()


class Gaveta(QFrame):
    """
    Painel que entra pela borda direita do hospedeiro, por cima do conteúdo.
    `animar=False` abre e fecha sem animação (PC mais lento ou preferência).
    """

    alternada = Signal(bool)

    def __init__(self, hospedeiro, largura=480, animar=True, parent=None):
        super().__init__(parent or hospedeiro)
        self.setObjectName("gaveta")
        self.hospedeiro = hospedeiro
        self.largura = largura
        self.animar = animar
        self._aberta = False
        self._animacao = QPropertyAnimation(self, b"geometry", self)
        self._animacao.setDuration(DURACAO_ANIMACAO_MS)
        self._animacao.setEasingCurve(QEasingCurve.OutCubic)
        self._animacao.finished.connect(self._ao_terminar_animacao)
        self._filtro = _FiltroRedimensionar(hospedeiro, self._reposicionar)
        self.layout_conteudo = QVBoxLayout(self)
        self.layout_conteudo.setContentsMargins(0, 0, 0, 0)
        self.layout_conteudo.setSpacing(0)
        self.hide()

    def esta_aberta(self):
        return self._aberta

    def _geometria(self, aberta):
        hosp = self.hospedeiro
        largura = min(self.largura, hosp.width())
        x = hosp.width() - largura if aberta else hosp.width()
        return QRect(x, 0, largura, hosp.height())

    def _reposicionar(self):
        if self._animacao.state() != QPropertyAnimation.Running and self._aberta:
            self.setGeometry(self._geometria(True))

    def abrir(self):
        self._mover(True)

    def fechar(self):
        self._mover(False)

    def alternar(self):
        self._mover(not self._aberta)

    def _mover(self, aberta):
        if aberta == self._aberta:
            return
        self._aberta = aberta
        if aberta:
            self.show()
            self.raise_()
        if not self.animar or not self.hospedeiro.isVisible():
            self._animacao.stop()
            self.setGeometry(self._geometria(aberta))
            self._ao_terminar_animacao()
        else:
            self._animacao.stop()
            self._animacao.setStartValue(self.geometry() if self.isVisible() and aberta is False
                                         else self._geometria(not aberta))
            self._animacao.setEndValue(self._geometria(aberta))
            self._animacao.start()
        self.alternada.emit(aberta)

    def _ao_terminar_animacao(self):
        if not self._aberta:
            self.hide()


__all__ = ["SecaoRecolhivel", "GrupoSecoes", "RodapeAcoes", "Sobreposicao", "Gaveta",
           "geometria_ancorada", "ANCORAS"]
