#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Layout que quebra linha quando os itens não cabem (como palavras num parágrafo).
Usado pelos chips de sugestão de espécie, que precisam caber em colunas estreitas.
Adaptado do exemplo "Flow Layout" da documentação do Qt.
"""

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout


class LayoutFluxo(QLayout):
    def __init__(self, parent=None, espaco=8):
        super().__init__(parent)
        self._itens = []
        self._espaco = espaco
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._itens.append(item)

    def count(self):
        return len(self._itens)

    def itemAt(self, indice):
        return self._itens[indice] if 0 <= indice < len(self._itens) else None

    def takeAt(self, indice):
        return self._itens.pop(indice) if 0 <= indice < len(self._itens) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, largura):
        return self._arrumar(QRect(0, 0, largura, 0), aplicar=False)

    def setGeometry(self, retangulo):
        super().setGeometry(retangulo)
        self._arrumar(retangulo, aplicar=True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        tamanho = QSize()
        for item in self._itens:
            tamanho = tamanho.expandedTo(item.minimumSize())
        margens = self.contentsMargins()
        return tamanho + QSize(margens.left() + margens.right(), margens.top() + margens.bottom())

    def _arrumar(self, retangulo, aplicar):
        margens = self.contentsMargins()
        area = retangulo.adjusted(margens.left(), margens.top(), -margens.right(), -margens.bottom())
        x, y, altura_linha = area.x(), area.y(), 0
        for item in self._itens:
            dica = item.sizeHint()
            proximo_x = x + dica.width() + self._espaco
            if proximo_x - self._espaco > area.right() + 1 and altura_linha > 0:
                x = area.x()
                y += altura_linha + self._espaco
                proximo_x = x + dica.width() + self._espaco
                altura_linha = 0
            if aplicar:
                item.setGeometry(QRect(QPoint(x, y), dica))
            x = proximo_x
            altura_linha = max(altura_linha, dica.height())
        return y + altura_linha - retangulo.y() + margens.bottom()
