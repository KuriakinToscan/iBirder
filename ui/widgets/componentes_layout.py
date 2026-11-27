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
- `PortaFoto`: lugar do card da foto (sempre quadrado) fora de layout, no maior quadrado
  que cabe, para a foto não esticar a janela (Trilha, Cartões de escolha).
- `ColunaFotos`: fotos quadradas empilhadas (e uma barra de botões embaixo) no maior
  lado que deixa TODAS caberem na altura disponível (Ficha compacta).
- `TextoAutoAltura`: caixa de texto (só leitura) cuja altura segue o texto na largura atual,
  recalculada sempre que a própria caixa muda de largura (Descrição e Etimologia).

Nenhum deles tem cor fixa: os estilos vêm do QSS global (classes e objectNames abaixo).
"""

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, QRect, Qt, Signal
from PySide6.QtWidgets import QBoxLayout, QFrame, QHBoxLayout, QPushButton, QSizePolicy, QTextEdit, QVBoxLayout, QWidget

from core.style_manager import StyleManager

DURACAO_ANIMACAO_MS = 160

# Preferência global (Configurações > Aparência > Animações): desligada, as gavetas abrem
# e fecham sem animação (PC mais lento). A janela define ao abrir e o diálogo ao salvar.
_animacoes = {"ativas": True}


def definir_animacoes(ativas):
    _animacoes["ativas"] = bool(ativas)


def animacoes_ativas():
    return _animacoes["ativas"]


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


class FotosLadoALado(QWidget):
    """
    Dois blocos de foto (sua foto | referência) lado a lado quando cabem; quando a largura
    disponível não comporta os dois no lado mínimo do card, um embaixo do outro. A largura
    vem de `medidor` (um widget fora da área de rolagem), porque dentro dela o próprio
    widget nunca fica mais estreito que o seu mínimo e o segundo card era cortado.
    """

    def __init__(self, medidor, desconto=0, lado_minimo=250, espaco=StyleManager.SPACING_MD, parent=None):
        super().__init__(parent)
        self._desconto = desconto
        self._lado_minimo = lado_minimo
        self.layout_fotos = QBoxLayout(QBoxLayout.LeftToRight, self)
        self.layout_fotos.setContentsMargins(0, 0, 0, 0)
        self.layout_fotos.setSpacing(espaco)
        self._filtro = _FiltroRedimensionar(medidor, lambda: self.atualizar(medidor.width()))

    def atualizar(self, largura_medidor):
        cabem = largura_medidor - self._desconto >= 2 * self._lado_minimo + self.layout_fotos.spacing()
        direcao = QBoxLayout.LeftToRight if cabem else QBoxLayout.TopToBottom
        if self.layout_fotos.direction() != direcao:
            self.layout_fotos.setDirection(direcao)

    def lado_a_lado(self):
        return self.layout_fotos.direction() == QBoxLayout.LeftToRight


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

    def event(self, evento):
        resultado = super().event(evento)
        # O conteúdo mudou de tamanho (ex.: chegaram as sugestões): refazer a geometria
        if evento.type() == QEvent.LayoutRequest and self.isVisible():
            self.reposicionar()
        return resultado


class Gaveta(QFrame):
    """
    Painel que entra pela borda direita do hospedeiro, por cima do conteúdo.
    `animar=False` (ou as animações desligadas nas Configurações) abre e fecha sem animação.
    """

    alternada = Signal(bool)

    def __init__(self, hospedeiro, largura=480, animar=True, parent=None, proporcao=None):
        super().__init__(parent or hospedeiro)
        self.setObjectName("gaveta")
        self.hospedeiro = hospedeiro
        self.largura = largura
        # Com `proporcao`, a gaveta cresce com o hospedeiro (fração da largura dele), com
        # `largura` como mínimo: numa janela grande ela não fica estreita no canto
        self.proporcao = proporcao
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

    def largura_atual(self):
        hosp = self.hospedeiro
        largura = self.largura
        if self.proporcao:
            largura = max(largura, int(hosp.width() * self.proporcao))
        return min(largura, hosp.width())

    def _geometria(self, aberta):
        hosp = self.hospedeiro
        largura = self.largura_atual()
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
        if not (self.animar and animacoes_ativas()) or not self.hospedeiro.isVisible():
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


class PortaFoto(QWidget):
    """
    Lugar do card da foto (Trilha, etapas 1 e 2; Cartões de escolha). O card é sempre
    quadrado (altura = largura), então fica fora de layout: o maior quadrado que cabe, no
    topo, centralizado ou à esquerda. Assim uma janela baixa não é esticada pela foto.
    """

    LADO_MINIMO = 250

    def __init__(self, alinhamento="centro", parent=None, lado_minimo=None):
        super().__init__(parent)
        if alinhamento not in ("centro", "esquerda"):
            raise ValueError(f"Alinhamento desconhecido: {alinhamento}")
        self.alinhamento = alinhamento
        self.lado_minimo = lado_minimo or self.LADO_MINIMO
        self._foto = None
        self.setMinimumSize(self.lado_minimo, self.lado_minimo)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def receber(self, foto):
        self._foto = foto
        foto.setParent(self)
        self._posicionar()
        foto.show()

    def contem(self, foto):
        return foto.parentWidget() is self

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._posicionar()

    def _posicionar(self):
        if self._foto is None or not self.contem(self._foto):
            return
        lado = max(self.lado_minimo, min(self.width(), self.height()))
        self._foto.setMinimumWidth(0)
        self._foto.setMaximumWidth(16777215)
        x = (self.width() - lado) // 2 if self.alinhamento == "centro" else 0
        self._foto.setGeometry(x, 0, lado, lado)


class ColunaFotos(QWidget):
    """
    Cards de foto (quadrados) empilhados e, embaixo, um widget de botões. O lado dos cards é
    o maior que deixa todos caberem na altura (e na largura) da coluna, centralizados: antes,
    na Ficha compacta, cada card tinha a largura da coluna e o segundo saía da tela.
    Fica dentro de uma área de rolagem: abaixo de `LADO_MINIMO`, a coluna rola.
    """

    LADO_MINIMO = 150

    def __init__(self, cards, rodape=None, espaco=StyleManager.SPACING_SM, parent=None):
        super().__init__(parent)
        self._cards = []
        self._rodape = rodape
        self._espaco = espaco
        for card in cards:
            self._cards.append(card)
            card.setParent(self)
            card.show()
        if rodape is not None:
            rodape.setParent(self)
            rodape.show()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(self.LADO_MINIMO, self._altura_para(self.LADO_MINIMO))

    def cards(self):
        return list(self._cards)

    def _altura_rodape(self):
        if self._rodape is None:
            return 0
        return self._rodape.sizeHint().height() + self._espaco

    def _altura_para(self, lado):
        n = len(self._cards)
        return n * lado + max(0, n - 1) * self._espaco + self._altura_rodape()

    def lado(self):
        """Lado dos cards no tamanho atual."""
        n = max(1, len(self._cards))
        livre = self.height() - self._altura_rodape() - (n - 1) * self._espaco
        return max(self.LADO_MINIMO, min(self.width(), livre // n))

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._posicionar()

    def _posicionar(self):
        lado = self.lado()
        x = (self.width() - lado) // 2
        y = 0
        for card in self._cards:
            if card.parentWidget() is not self:
                continue
            card.setMinimumSize(0, 0)
            card.setMaximumWidth(16777215)
            card.setGeometry(x, y, lado, lado)
            y += lado + self._espaco
        if self._rodape is not None and self._rodape.parentWidget() is self:
            # Botões na largura da coluna (o texto deles não cabe no lado de uma foto pequena)
            self._rodape.setGeometry(0, y, self.width(), self._rodape.sizeHint().height())


class TextoAutoAltura(QTextEdit):
    """
    QTextEdit sem rolagem cuja altura é a do texto na largura que a caixa tem AGORA.

    Antes a janela calculava a altura uma vez, quando o texto chegava: se o painel mudava
    de largura depois (página escondida da Trilha, gaveta, troca de layout, barra de rolagem
    que aparece), a altura ficava a da largura antiga e as últimas linhas sumiam.
    """

    def __init__(self, altura_minima=45, parent=None):
        super().__init__(parent)
        self._altura_minima = altura_minima
        self._largura_calculada = -1
        self.setReadOnly(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(altura_minima)
        self.textChanged.connect(self.ajustar_altura)

    def ajustar_altura(self):
        """Altura = texto na largura do viewport + bordas e preenchimento do QSS."""
        largura = self.viewport().width()
        if largura <= 1:
            return
        self._largura_calculada = largura
        documento = self.document()
        documento.setTextWidth(largura)
        bordas = max(0, self.height() - self.viewport().height())
        altura = int(documento.size().height() + 0.999) + bordas + 2
        altura = max(altura, self._altura_minima)
        if altura != self.height():
            self.setFixedHeight(altura)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        if self.viewport().width() != self._largura_calculada:
            self.ajustar_altura()

    def showEvent(self, evento):
        super().showEvent(evento)
        self.ajustar_altura()


__all__ = ["ColunaFotos", "FotosLadoALado", "TextoAutoAltura", "definir_animacoes", "animacoes_ativas", "PortaFoto", "SecaoRecolhivel", "GrupoSecoes", "RodapeAcoes", "Sobreposicao", "Gaveta",
           "geometria_ancorada", "ANCORAS"]
