#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#
#  Este programa é um software livre: você pode redistribuí-lo e/ou
#  modificá-lo sob os termos da Licença Pública Geral GNU conforme
#  publicada pela Free Software Foundation, tanto a versão 3 da
#  Licença, como (a seu critério) qualquer versão posterior.
#
#  Este programa é distribuído na esperança de que possa ser útil,
#  mas SEM NENHUMA GARANTIA; sem uma garantia implícita de
#  ADEQUAÇÃO A QUALQUER MERCADO OU APLICAÇÃO EM PARTICULAR.
#  Veja a Licença Pública Geral GNU para mais detalhes.
#
#  Você deve ter recebido uma cópia da Licença Pública Geral GNU
#  junto com este programa. Se não, veja <https://www.gnu.org/licenses/>.


"""Aviso de nova versão do iBirder, com as novidades da Release."""

import html

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextBrowser

from core.verificacao_versao import descrever_data
from ui.base.base_dialog import BaseDialog


class DialogoNovaVersao(BaseDialog):
    """
    Mostra versão, data e novidades. Depois de fechado, self.escolha é
    "baixar", "pagina", "depois" ou "ignorar".
    """

    def __init__(self, info, versao_atual, parent=None):
        super().__init__("Nova versão do iBirder", parent)
        self.setMinimumWidth(540)
        self.resize(600, 500)
        self.info = info
        self.escolha = "depois"

        titulo = QLabel(f"Nova versão disponível: {html.escape(info['tag'])}")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #111827;")
        self.main_layout.addWidget(titulo)

        data = descrever_data(info.get("data"))
        subtitulo = f"Você usa a versão {html.escape(str(versao_atual))}."
        if data:
            subtitulo += f" A {html.escape(info['tag'])} foi publicada em {data}."
        lbl_sub = QLabel(subtitulo)
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("color: #374151;")
        self.main_layout.addWidget(lbl_sub)

        notas = QTextBrowser()
        notas.setOpenExternalLinks(True)
        notas.setMarkdown(info.get("notas") or "_A Release não traz descrição das novidades._")
        notas.setStyleSheet("background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 6px; padding: 6px;")
        self.main_layout.addWidget(notas, stretch=1)

        ajuda = QLabel("Para atualizar, baixe e execute o instalador: ele substitui a versão atual "
                       "e mantém suas configurações e chaves de API.")
        ajuda.setWordWrap(True)
        ajuda.setStyleSheet("color: #4B5563; font-size: 12px;")
        self.main_layout.addWidget(ajuda)

        botoes = QHBoxLayout()
        self.btn_ignorar = QPushButton("Ignorar esta versão")
        self.btn_ignorar.setToolTip("Não avisar mais desta versão ao abrir o app")
        botoes.addWidget(self.btn_ignorar)
        botoes.addStretch()
        self.btn_depois = QPushButton("Lembrar depois")
        self.btn_pagina = QPushButton("Ver no GitHub")
        self.btn_baixar = QPushButton("Baixar instalador")
        if not info.get("url_instalador"):
            # Release sem .exe anexado (ex.: instalador ainda sendo gerado): só a página
            self.btn_baixar.setVisible(False)
            self.btn_pagina.setDefault(True)
        else:
            self.btn_baixar.setDefault(True)
        for b in (self.btn_depois, self.btn_pagina, self.btn_baixar):
            botoes.addWidget(b)
        for b in (self.btn_ignorar, self.btn_depois, self.btn_pagina, self.btn_baixar):
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(34)
        self.btn_baixar.setStyleSheet("background-color: #374151; color: white; font-weight: bold; "
                                      "border-radius: 4px; padding: 0 14px;")
        self.main_layout.addLayout(botoes)

        self.btn_ignorar.clicked.connect(lambda: self._fechar("ignorar"))
        self.btn_depois.clicked.connect(lambda: self._fechar("depois"))
        self.btn_pagina.clicked.connect(lambda: self._abrir(self.info["url_pagina"], "pagina"))
        self.btn_baixar.clicked.connect(lambda: self._abrir(self.info["url_instalador"], "baixar"))

    def _abrir(self, url, escolha):
        QDesktopServices.openUrl(QUrl(url))
        self._fechar(escolha)

    def _fechar(self, escolha):
        self.escolha = escolha
        self.accept()
