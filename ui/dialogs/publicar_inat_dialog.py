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

"""Pré-visualização e confirmação antes de publicar a observação no iNaturalist (issue #9)."""

import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel,
                               QPlainTextEdit, QPushButton)

from core.style_manager import StyleManager
from modules.step7_publicacao.inat_publicador import GEOPRIVACIDADES, LICENCAS_OBSERVACAO
from ui.base.base_dialog import BaseDialog

DESCRICAO_PADRAO = "Identificação assistida pelo iBirder e conferida pelo observador."


class DialogoPublicarInat(BaseDialog):
    """
    resumo: nome_cientifico, nome_comum, data ('AAAA-MM-DD HH:MM:SS'), latitude, longitude,
    local (texto), arquivo. Depois de aceito, ler geoprivacidade(), licenca() e descricao().
    """

    def __init__(self, resumo, geoprivacidade_sugerida="open", motivo_sugestao="",
                 licenca_padrao="CC-BY", parent=None):
        super().__init__("Publicar no iNaturalist", parent)
        self.setMinimumWidth(560)

        titulo = QLabel("Conferir antes de publicar")
        StyleManager.estilizar(titulo, "font-family: 'var(--fonte_titulo)'; font-size: 16px; font-weight: bold; color: var(--texto);")
        self.main_layout.addWidget(titulo)

        aviso = QLabel("A observação fica pública no iNaturalist, na sua conta. Confira cada campo.")
        aviso.setWordWrap(True)
        StyleManager.estilizar(aviso, "color: var(--texto_secundario);")
        self.main_layout.addWidget(aviso)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        nome_comum = resumo.get("nome_comum")
        especie = f"<i>{html.escape(resumo.get('nome_cientifico') or '')}</i>"
        if nome_comum:
            especie = f"{html.escape(nome_comum)} ({especie})"
        form.addRow("Espécie:", self._valor(especie))

        data = resumo.get("data")
        form.addRow("Data:", self._valor(self._formatar_data(data) if data else
                                         "<b>Sem data no EXIF da foto: não é possível publicar.</b>"))

        lat, lon = resumo.get("latitude"), resumo.get("longitude")
        if lat is not None and lon is not None:
            local = f"{float(lat):.5f}, {float(lon):.5f}"
            if resumo.get("local"):
                local = f"{html.escape(resumo['local'])} ({local})"
        else:
            local = ("Sem localização. A observação pode ser publicada, mas não chega ao "
                     "grau de pesquisa do iNaturalist.")
        form.addRow("Local:", self._valor(local))
        form.addRow("Arquivo:", self._valor(html.escape(resumo.get("arquivo") or "")))

        self.combo_geo = QComboBox()
        for chave, texto in GEOPRIVACIDADES.items():
            self.combo_geo.addItem(texto, chave)
        self.combo_geo.setCurrentIndex(max(0, self.combo_geo.findData(geoprivacidade_sugerida)))
        form.addRow("Localização pública:", self.combo_geo)
        if motivo_sugestao:
            sugestao = QLabel(f"Sugerido ocultar: espécie ameaçada ({html.escape(motivo_sugestao)}).")
            sugestao.setWordWrap(True)
            StyleManager.estilizar(sugestao, "color: var(--texto_secundario); font-size: 12px;")
            form.addRow("", sugestao)

        self.combo_licenca = QComboBox()
        for chave, texto in LICENCAS_OBSERVACAO.items():
            self.combo_licenca.addItem(texto, chave)
        self.combo_licenca.setCurrentIndex(max(0, self.combo_licenca.findData(licenca_padrao)))
        form.addRow("Licença da observação:", self.combo_licenca)

        nota_foto = QLabel('A licença da <b>foto</b> segue a configuração da sua conta no iNaturalist '
                           '(recomendado: CC BY-NC). <a href="https://www.inaturalist.org/users/edit">'
                           'Abrir as configurações da conta</a>.')
        nota_foto.setWordWrap(True)
        nota_foto.setOpenExternalLinks(True)
        StyleManager.estilizar(nota_foto, "color: var(--texto_secundario); font-size: 12px;")
        form.addRow("", nota_foto)

        self.txt_descricao = QPlainTextEdit(DESCRICAO_PADRAO)
        self.txt_descricao.setFixedHeight(70)
        form.addRow("Descrição:", self.txt_descricao)
        self.main_layout.addLayout(form)

        self.chk_conferido = QCheckBox("Conferi a espécie, a data e o local, e a foto é de minha autoria.")
        self.main_layout.addWidget(self.chk_conferido)

        botoes = QHBoxLayout()
        botoes.addStretch()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_publicar = QPushButton("Publicar")
        self.btn_publicar.setProperty("class", "primario")
        for b in (self.btn_cancelar, self.btn_publicar):
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(34)
            botoes.addWidget(b)
        self.main_layout.addLayout(botoes)

        self._pode_publicar = bool(data)
        self.btn_publicar.setEnabled(False)
        self.chk_conferido.setEnabled(self._pode_publicar)
        self.chk_conferido.toggled.connect(lambda marcado: self.btn_publicar.setEnabled(marcado and self._pode_publicar))
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_publicar.clicked.connect(self.accept)

    @staticmethod
    def _valor(texto_html):
        rotulo = QLabel(texto_html)
        rotulo.setWordWrap(True)
        rotulo.setTextInteractionFlags(Qt.TextSelectableByMouse)
        return rotulo

    @staticmethod
    def _formatar_data(data):
        dia, hora = data.split(" ")
        a, m, d = dia.split("-")
        return f"{d}/{m}/{a} às {hora[:5]}"

    def geoprivacidade(self):
        return self.combo_geo.currentData()

    def licenca(self):
        return self.combo_licenca.currentData()

    def descricao(self):
        return self.txt_descricao.toPlainText().strip()
