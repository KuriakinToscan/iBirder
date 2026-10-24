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
import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QScrollArea

from modules.step6_persistence.registro_ibirder import descrever_quando, resumo_legivel
from ui.base.base_dialog import BaseDialog
from core.style_manager import StyleManager


class DialogoFotoProcessada(BaseDialog):
    """
    exec() devolve Accepted para "Processar novamente" e Rejected para "Ignorar".
    Se a foto foi renomeada pelo iBirder, oferece "Desfazer renomeação"; depois de exec(),
    self.caminho tem o caminho atual da foto.
    """

    def __init__(self, registro, nome_arquivo, parent=None, caminho=None):
        super().__init__("Foto já processada", parent)
        self.setMinimumWidth(520)
        self.resize(560, 520)

        titulo = QLabel("Esta foto já foi processada pelo iBirder")
        StyleManager.estilizar(titulo, "font-family: 'var(--fonte_titulo)'; font-size: 16px; font-weight: bold; color: var(--texto);")
        self.main_layout.addWidget(titulo)

        self.registro = registro
        self.caminho = Path(caminho) if caminho else None
        self.nome_original = registro.get("nome_original")
        self.cabecalho = QLabel()
        self.cabecalho.setWordWrap(True)
        StyleManager.estilizar(self.cabecalho, "color: var(--texto_secundario);")
        self.main_layout.addWidget(self.cabecalho)
        self._atualizar_cabecalho(nome_arquivo)

        # Desfazer renomeação: só quando a foto está com nome diferente do original
        self.btn_desfazer = None
        if self.caminho and self.nome_original and Path(self.nome_original).stem != self.caminho.stem:
            linha = QHBoxLayout()
            self.btn_desfazer = QPushButton(f"Desfazer renomeação (voltar para {self.nome_original})")
            self.btn_desfazer.setCursor(Qt.PointingHandCursor)
            self.btn_desfazer.clicked.connect(self._desfazer_renomeacao)
            linha.addWidget(self.btn_desfazer)
            linha.addStretch()
            self.main_layout.addLayout(linha)
        self.lbl_resultado = QLabel()
        self.lbl_resultado.setWordWrap(True)
        self.lbl_resultado.setVisible(False)
        self.main_layout.addWidget(self.lbl_resultado)

        corpo = ""
        for secao, itens in resumo_legivel(registro):
            corpo += f"<p style='margin:8px 0 2px 0;'><b>{secao}</b></p>"
            corpo += "".join(f"&nbsp;&nbsp;• {html.escape(rotulo)}: {html.escape(valor)}<br>" for rotulo, valor in itens)
        if registro.get("comentario"):
            corpo += f"<p style='margin:8px 0 2px 0;'><b>Comentário</b></p>&nbsp;&nbsp;{html.escape(registro['comentario'])}"
        if not corpo:
            corpo = "<i>Nenhum dado detalhado foi encontrado além da marca do iBirder.</i>"

        lbl_dados = QLabel()
        StyleManager.definir_texto(lbl_dados, f"<div style='line-height:140%; color: var(--texto);'>{corpo}</div>")
        lbl_dados.setWordWrap(True)
        lbl_dados.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        lbl_dados.setTextInteractionFlags(Qt.TextSelectableByMouse)
        StyleManager.estilizar(lbl_dados, "background: var(--superficie); border: 1px solid var(--borda_suave); border-radius: 6px; padding: 10px;")
        rolagem = QScrollArea()
        rolagem.setWidgetResizable(True)
        rolagem.setWidget(lbl_dados)
        self.main_layout.addWidget(rolagem, stretch=1)

        pergunta = QLabel("Deseja processar a foto novamente? Os dados do iBirder gravados nela serão "
                          "substituídos pelos novos quando você usar \"Gravar Dados na Fotografia\".")
        pergunta.setWordWrap(True)
        StyleManager.estilizar(pergunta, "color: var(--texto_secundario); font-size: 12px;")
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
        self.btn_processar.setProperty("class", "primario")  # ação principal; cores do tema
        self.main_layout.addLayout(botoes)

    def _atualizar_cabecalho(self, nome_arquivo):
        original = self.nome_original
        linha_original = (f"<b>Nome original:</b> {html.escape(original)}<br>"
                          if original and Path(original).stem != Path(nome_arquivo).stem else "")
        self.cabecalho.setText(f"<b>Arquivo:</b> {html.escape(nome_arquivo)}<br>{linha_original}"
                               f"<b>Processada em:</b> {html.escape(descrever_quando(self.registro))}")

    def _desfazer_renomeacao(self):
        from core import nome_arquivo
        try:
            novo, feitos = nome_arquivo.desfazer_renomeacao(self.caminho, self.nome_original)
        except (OSError, FileExistsError) as e:
            logging.error(f"Falha ao desfazer a renomeação de {self.caminho.name}: {e}")
            self._mostrar_resultado(f"Não foi possível desfazer: {e}", erro=True)
            return
        self.caminho = novo
        self._atualizar_cabecalho(novo.name)
        self.btn_desfazer.setVisible(False)
        nomes = ", ".join(n.name for _, n in feitos)
        self._mostrar_resultado(f"Renomeação desfeita: {nomes}.")

    def _mostrar_resultado(self, texto, erro=False):
        cor = ("erro_texto", "erro_fundo") if erro else ("sucesso_texto", "sucesso_fundo")
        self.lbl_resultado.setText(html.escape(texto))
        StyleManager.estilizar(self.lbl_resultado, f"color: var(--{cor[0]}); background: var(--{cor[1]}); padding: 8px; border-radius: 6px;")
        self.lbl_resultado.setVisible(True)
