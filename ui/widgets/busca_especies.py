#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Sugestões de espécies no campo "Nome Científico" (busca rápida, Ctrl+K).

Enquanto a pessoa digita, mostra até 12 espécies do catálogo embarcado
(core/catalogo_especies.py) que casam com o nome científico ou o nome em inglês.
Escolher uma sugestão preenche o nome científico e dispara a busca manual; Enter sem
sugestão marcada busca o texto digitado (a busca é sempre feita por ao_escolher).
"""

from PySide6.QtCore import QStringListModel, Qt, QTimer
from PySide6.QtWidgets import QCompleter

from core import catalogo_especies


class BuscaEspecies(QCompleter):
    """QCompleter que busca no catálogo a cada tecla (sem filtro próprio do Qt)."""

    def __init__(self, campo, ao_escolher):
        super().__init__(campo)
        self._campo = campo
        self._ao_escolher = ao_escolher
        self._por_rotulo = {}
        self._modelo = QStringListModel(self)
        self.setModel(self._modelo)
        self.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.setCaseSensitivity(Qt.CaseInsensitive)
        self.setMaxVisibleItems(12)
        self.setWidget(campo)
        campo.textEdited.connect(self._atualizar)
        campo.returnPressed.connect(self._enter)
        self.activated[str].connect(self._escolhido)

    def _atualizar(self, texto):
        especies = catalogo_especies.buscar(texto)
        self._por_rotulo = {catalogo_especies.rotulo(e): e["nome_cientifico"] for e in especies}
        self._modelo.setStringList(list(self._por_rotulo))
        if especies:
            self.complete()
        else:
            self.popup().hide()

    def _enter(self, *_):
        """
        Enter no campo. Com uma sugestão marcada na lista, quem busca é _escolhido
        (o Qt entrega o Enter ao campo antes de ativar a sugestão); senão, busca o texto.
        """
        popup = self.popup()
        if popup.isVisible() and popup.selectionModel().hasSelection():
            return
        popup.hide()
        self._ao_escolher()

    def _escolhido(self, rotulo):
        nome = self._por_rotulo.get(rotulo)
        if not nome:
            return
        # Depois do evento: o QCompleter ainda escreveria o rótulo inteiro no campo
        QTimer.singleShot(0, lambda: (self._campo.setText(nome), self._ao_escolher()))
