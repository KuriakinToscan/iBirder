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


"""Aviso exibido ao abrir uma foto que já foi processada pelo iBirder."""

import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QScrollArea

from modules.step6_persistence.registro_ibirder import descrever_quando, resumo_legivel
from ui.base.base_dialog import BaseDialog


class DialogoFotoProcessada(BaseDialog):
    """exec() devolve Accepted para "Processar novamente" e Rejected para "Ignorar"."""

    def __init__(self, registro, nome_arquivo, parent=None):
        super().__init__("Foto já processada", parent)
        self.setMinimumWidth(520)
        self.resize(560, 520)

        titulo = QLabel("Esta foto já foi processada pelo iBirder")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #111827;")
        self.main_layout.addWidget(titulo)

        original = registro.get("nome_original")
        linha_original = (f"<b>Nome original:</b> {html.escape(original)}<br>"
                          if original and original != nome_arquivo else "")
        cabecalho = QLabel(f"<b>Arquivo:</b> {html.escape(nome_arquivo)}<br>{linha_original}"
                           f"<b>Processada em:</b> {html.escape(descrever_quando(registro))}")
        cabecalho.setWordWrap(True)
        cabecalho.setStyleSheet("color: #374151;")
        self.main_layout.addWidget(cabecalho)

        corpo = ""
        for secao, itens in resumo_legivel(registro):
            corpo += f"<p style='margin:8px 0 2px 0;'><b>{secao}</b></p>"
            corpo += "".join(f"&nbsp;&nbsp;• {html.escape(rotulo)}: {html.escape(valor)}<br>" for rotulo, valor in itens)
        if registro.get("comentario"):
            corpo += f"<p style='margin:8px 0 2px 0;'><b>Comentário</b></p>&nbsp;&nbsp;{html.escape(registro['comentario'])}"
        if not corpo:
            corpo = "<i>Nenhum dado detalhado foi encontrado além da marca do iBirder.</i>"

        lbl_dados = QLabel(f"<div style='line-height:140%; color:#374151;'>{corpo}</div>")
        lbl_dados.setWordWrap(True)
        lbl_dados.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        lbl_dados.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl_dados.setStyleSheet("background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 6px; padding: 10px;")
        rolagem = QScrollArea()
        rolagem.setWidgetResizable(True)
        rolagem.setWidget(lbl_dados)
        self.main_layout.addWidget(rolagem, stretch=1)

        pergunta = QLabel("Deseja processar a foto novamente? Os dados do iBirder gravados nela serão "
                          "substituídos pelos novos quando você usar \"Gravar Dados na Fotografia\".")
        pergunta.setWordWrap(True)
        pergunta.setStyleSheet("color: #4B5563; font-size: 12px;")
        self.main_layout.addWidget(pergunta)

        botoes = QHBoxLayout()
        botoes.addStretch()
        self.btn_ignorar = QPushButton("Ignorar")
        self.btn_ignorar.setCursor(Qt.PointingHandCursor)
        self.btn_ignorar.clicked.connect(self.reject)
        self.btn_processar = QPushButton("Processar novamente")
        self.btn_processar.setCursor(Qt.PointingHandCursor)
        self.btn_processar.setDefault(True)
        self.btn_processar.clicked.connect(self.accept)
        for b in (self.btn_ignorar, self.btn_processar):
            b.setMinimumHeight(34)
            b.setMinimumWidth(150)
            botoes.addWidget(b)
        self.btn_processar.setStyleSheet("background-color: #374151; color: white; font-weight: bold; border-radius: 4px;")
        self.main_layout.addLayout(botoes)
