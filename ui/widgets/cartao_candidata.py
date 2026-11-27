#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Cartões das espécies candidatas (v1.6, proposta "Cartões de escolha"; também na Trilha).

`PainelCartoes` segue o EstadoIdentificacao: quando a identificação termina, mostra até
três `CartaoCandidata` (a espécie da IA primeiro), cada um com a foto de referência do
iNaturalist (core/fotos_referencia.py, baixada em segundo plano, com crédito e licença),
nome científico, nome popular, família, se tem registro no Brasil e a certeza da IA.
"É esta" emite `escolhida(nome científico)`: a janela confirma a espécie atual ou faz a
busca manual da outra, o mesmo que digitar o nome.

Duas orientações, como as vistas da fila: "horizontal" (cartões grandes lado a lado, no
layout Cartões de escolha) e "vertical" (linhas compactas, na coluna da Trilha).
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QBoxLayout, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton,
                               QSizePolicy, QVBoxLayout, QWidget)

from core import catalogo_especies
from core import fotos_referencia as fr
from core.style_manager import StyleManager
from ui import estado_identificacao as ei

ORIENTACOES = ("horizontal", "vertical")
ALTURA_FOTO = {"horizontal": 170, "vertical": 56}
# Cartão horizontal: a altura da foto acompanha a largura do cartão (proporção ~3:2),
# entre estes limites, e a foto aparece inteira (antes era recortada numa faixa de 170 px
# e uma ave em pé perdia a cabeça e a cauda)
PROPORCAO_FOTO = 0.62
ALTURA_FOTO_MIN, ALTURA_FOTO_MAX = 150, 260


class _CarregadorFotos(QThread):
    """Baixa (ou lê do cache) as fotos das candidatas, uma por vez, fora da interface."""

    foto_pronta = Signal(int, str, object)  # geração, nome científico, FotoReferencia ou None

    def __init__(self, geracao, nomes, parent=None):
        super().__init__(parent)
        self.geracao = geracao
        self.nomes = list(nomes)

    def run(self):
        for nome in self.nomes:
            if self.isInterruptionRequested():
                return
            try:
                foto = fr.obter_foto(nome)
            except Exception as e:  # obter_foto já trata a rede; aqui só por garantia
                logging.warning(f"[Cartões] Foto de {nome}: {e}")
                foto = None
            self.foto_pronta.emit(self.geracao, nome, foto)


def _info_catalogo(nome):
    """Família, nome em inglês e registro no Brasil, do catálogo embarcado (sem rede)."""
    especie = catalogo_especies.obter(nome) or {}
    return especie.get("familia", ""), especie.get("nome_ingles", ""), bool(especie.get("no_brasil"))


class CartaoCandidata(QFrame):
    """Uma espécie candidata: foto de referência, nomes, certeza e o botão "É esta"."""

    escolhida = Signal(str)

    def __init__(self, nome, confianca, principal=False, orientacao="horizontal", parent=None):
        super().__init__(parent)
        self.setObjectName("cartao_candidata")
        self.nome = nome
        self.confianca = confianca
        self.principal = principal
        self.orientacao = orientacao
        self.setProperty("principal", "true" if principal else "false")
        familia, ingles, no_brasil = _info_catalogo(nome)
        self.familia, self.nome_ingles, self.no_brasil = familia, ingles, no_brasil

        horizontal = orientacao == "horizontal"
        layout = QVBoxLayout(self) if horizontal else QHBoxLayout(self)
        margem = 0 if horizontal else StyleManager.SPACING_SM
        layout.setContentsMargins(margem, margem, margem, margem)
        layout.setSpacing(StyleManager.SPACING_SM)

        self.lbl_foto = QLabel("Sem foto de referência" if horizontal else "")
        self.lbl_foto.setObjectName("cartao_foto")
        self.lbl_foto.setAlignment(Qt.AlignCenter)
        altura = ALTURA_FOTO[orientacao]
        self.lbl_foto.setFixedHeight(altura)
        if horizontal:
            self.lbl_foto.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        else:
            self.lbl_foto.setFixedWidth(altura)
        layout.addWidget(self.lbl_foto)

        textos = QWidget()
        layout_textos = QVBoxLayout(textos)
        pad = StyleManager.SPACING_MD if horizontal else 0
        layout_textos.setContentsMargins(pad, 0, pad, pad)
        layout_textos.setSpacing(2)
        mais_provavel = "  ·  mais provável" if principal and horizontal else ""
        self.lbl_certeza = QLabel(f"{confianca * 100:.0f}%{mais_provavel}")
        self.lbl_certeza.setObjectName("cartao_certeza")
        self.lbl_comum = QLabel(ingles or " ")
        self.lbl_comum.setObjectName("cartao_nome_comum")
        self._nome_comum = ingles or " "
        # Na linha compacta (vertical), o nome numa linha só, com reticências se não couber:
        # quebrado em duas, a segunda linha era cortada pela altura do cartão
        self.lbl_comum.setWordWrap(horizontal)
        if not horizontal:
            self.lbl_comum.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.lbl_cientifico = QLabel(f"<i>{nome}</i>")
        self.lbl_cientifico.setObjectName("cartao_cientifico")
        self.lbl_cientifico.setWordWrap(True)
        detalhes = [familia] if familia else []
        detalhes.append("registrada no Brasil" if no_brasil else "sem registro no Brasil")
        self.lbl_detalhes = QLabel(" · ".join(detalhes))
        self.lbl_detalhes.setObjectName("cartao_detalhes")
        self.lbl_detalhes.setWordWrap(True)
        self.barra = QProgressBar()
        self.barra.setObjectName("cartao_barra")
        self.barra.setRange(0, 100)
        self.barra.setValue(round(confianca * 100))
        self.barra.setTextVisible(False)
        self.barra.setFixedHeight(4)
        self.lbl_credito = QLabel("")
        self.lbl_credito.setObjectName("cartao_credito")
        self.lbl_credito.setWordWrap(True)
        if horizontal:
            for widget in (self.lbl_certeza, self.lbl_comum, self.lbl_cientifico, self.lbl_detalhes,
                           self.barra, self.lbl_credito):
                layout_textos.addWidget(widget)
            layout_textos.addStretch()
        else:
            # Linha compacta: científico e certeza em cima, nome comum embaixo
            topo = QHBoxLayout()
            topo.addWidget(self.lbl_cientifico, 1)
            topo.addWidget(self.lbl_certeza)
            layout_textos.addLayout(topo)
            layout_textos.addWidget(self.lbl_comum)
            layout_textos.addWidget(self.barra)
            self.lbl_detalhes.hide()
            self.lbl_credito.hide()
        layout.addWidget(textos, 1)

        self.btn_esta = QPushButton("✓  É esta" if principal else "É esta")
        self.btn_esta.setProperty("class", "primario" if principal else "secundario")
        self.btn_esta.setCursor(Qt.PointingHandCursor)
        self.btn_esta.setToolTip(f"Confirmar {nome}")
        self.btn_esta.clicked.connect(lambda: self.escolhida.emit(self.nome))
        if horizontal:
            rodape = QHBoxLayout()
            rodape.setContentsMargins(pad, 0, pad, pad)
            rodape.addWidget(self.btn_esta)
            layout.addLayout(rodape)
        else:
            layout.addWidget(self.btn_esta, 0, Qt.AlignVCenter)
        self._atualizar_dica()

    def definir_foto(self, foto: fr.FotoReferencia | None):
        """Mostra a foto de referência (ou o aviso de que não há), com crédito e licença."""
        if foto is None:
            if self.orientacao == "horizontal":
                self.lbl_foto.setText("Sem foto de referência")
            return
        pixmap = QPixmap(foto.caminho)
        if pixmap.isNull():
            return
        self._pixmap = pixmap
        self._redesenhar_foto()
        if foto.nome_comum:
            self._nome_comum = foto.nome_comum
            self.lbl_comum.setText(foto.nome_comum)
            self._encaixar_nome()
        self.lbl_credito.setText(f"Foto: {foto.texto_credito} (iNaturalist)")
        self.credito = foto.texto_credito
        self._atualizar_dica()

    def _redesenhar_foto(self):
        pixmap = getattr(self, "_pixmap", None)
        if pixmap is None or self.lbl_foto.width() <= 1:
            return
        alvo = QSize(self.lbl_foto.width(), self.lbl_foto.height())
        if self.orientacao == "horizontal":
            # Foto inteira, centralizada (o fundo do rótulo vem do tema)
            self.lbl_foto.setPixmap(pixmap.scaled(alvo, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            return
        # Miniatura da linha compacta: quadrada, recortada no centro
        escalada = pixmap.scaled(alvo, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x = max(0, (escalada.width() - alvo.width()) // 2)
        y = max(0, (escalada.height() - alvo.height()) // 2)
        self.lbl_foto.setPixmap(escalada.copy(x, y, alvo.width(), alvo.height()))

    def _encaixar_nome(self):
        """Linha compacta: nome comum com reticências quando não cabe na largura."""
        if self.orientacao == "horizontal":
            return
        largura = self.lbl_comum.width()
        if largura <= 1:
            return
        texto = self.lbl_comum.fontMetrics().elidedText(self._nome_comum, Qt.ElideRight, largura)
        if texto != self.lbl_comum.text():
            self.lbl_comum.setText(texto)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        if self.orientacao == "horizontal":
            altura = max(ALTURA_FOTO_MIN, min(ALTURA_FOTO_MAX, int(self.width() * PROPORCAO_FOTO)))
            if self.lbl_foto.height() != altura:
                self.lbl_foto.setFixedHeight(altura)
        self._redesenhar_foto()
        self._encaixar_nome()

    def marcar_escolhida(self, escolhida):
        valor = "true" if escolhida else "false"
        if self.property("escolhida") != valor:
            self.setProperty("escolhida", valor)
            self.style().unpolish(self)
            self.style().polish(self)

    def _atualizar_dica(self):
        partes = [self.nome, f"certeza da IA: {self.confianca * 100:.0f}%"]
        if self.familia:
            partes.append(f"família {self.familia}")
        partes.append("registrada no Brasil" if self.no_brasil else "sem registro no Brasil")
        if getattr(self, "credito", ""):
            partes.append(f"foto: {self.credito}")
        # Na foto (não no cartão todo): a dica não aparece por cima do nome
        self.lbl_foto.setToolTip("\n".join(partes))


class PainelCartoes(QFrame):
    """As candidatas da identificação atual, em cartões. Emite `escolhida(nome científico)`."""

    escolhida = Signal(str)

    def __init__(self, estado=None, baixar_fotos=True, parent=None):
        super().__init__(parent)
        self.setObjectName("painel_cartoes")
        self.orientacao = "horizontal"
        self.baixar_fotos = baixar_fotos
        self.cartoes: list[CartaoCandidata] = []
        self._candidatas = []
        self._geracao = 0
        self._carregador = None
        self._encerrando = set()  # downloads de identificações anteriores ainda terminando
        self._fotos = {}  # nome -> FotoReferencia (da identificação atual)
        self._estado = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(StyleManager.SPACING_SM)
        self.lbl_aviso = QLabel("")
        self.lbl_aviso.setObjectName("cartoes_aviso")
        self.lbl_aviso.setWordWrap(True)
        layout.addWidget(self.lbl_aviso)
        self._area = QWidget()
        self._layout_cartoes = QBoxLayout(QBoxLayout.LeftToRight, self._area)
        self._layout_cartoes.setContentsMargins(0, 0, 0, 0)
        self._layout_cartoes.setSpacing(StyleManager.SPACING_MD)
        layout.addWidget(self._area, 1)
        self._mostrar_aviso("As espécies mais prováveis aparecem aqui depois da identificação.")
        if estado is not None:
            self.conectar_estado(estado)

    # --- Orientação ---

    def definir_orientacao(self, orientacao):
        if orientacao not in ORIENTACOES:
            raise ValueError(f"Orientação desconhecida: {orientacao}")
        if orientacao == self.orientacao:
            return
        self.orientacao = orientacao
        self._layout_cartoes.setDirection(QBoxLayout.LeftToRight if orientacao == "horizontal"
                                          else QBoxLayout.TopToBottom)
        self._montar_cartoes()

    # --- Estado ---

    def conectar_estado(self, estado):
        self._estado = estado
        estado.etapa_alterada.connect(self._ao_mudar_etapa)
        estado.alterado.connect(self._marcar_escolhida)
        self._ao_mudar_etapa(estado.etapa)

    def _ao_mudar_etapa(self, etapa):
        estado = self._estado
        if etapa == ei.SEM_FOTO:
            self.mostrar([])
            self._mostrar_aviso("As espécies mais prováveis aparecem aqui depois da identificação.")
        elif etapa == ei.IDENTIFICANDO:
            if estado is not None and estado.candidatas and estado.candidatas == self._candidatas:
                return  # busca manual na mesma foto: as candidatas continuam
            self.mostrar([])
            self._mostrar_aviso("Identificando a ave...")
        elif etapa == ei.ERRO:
            self.mostrar([])
            self._mostrar_aviso("A identificação falhou. Digite o nome científico da espécie.")
        elif etapa in (ei.CONFERIR, ei.INCONCLUSIVA) and estado is not None:
            if estado.candidatas != self._candidatas:
                self.mostrar(estado.candidatas)
            if not estado.candidatas:
                self._mostrar_aviso("A IA não sugeriu espécies. Digite o nome científico.")

    def _marcar_escolhida(self):
        atual = self._estado.nome_cientifico if self._estado is not None else None
        atual = ei._especie(atual) if atual else None
        for cartao in self.cartoes:
            cartao.marcar_escolhida(atual is not None and ei._especie(cartao.nome) == atual
                                    and bool(self._estado.confirmada or self._estado.manual))

    # --- Cartões ---

    def mostrar(self, candidatas):
        """Mostra as candidatas [(nome científico, confiança)] e começa a buscar as fotos."""
        self._candidatas = list(candidatas)
        self._geracao += 1
        self._parar_carregador()
        self._fotos = {}
        self._montar_cartoes()
        if self._candidatas:
            self.lbl_aviso.hide()
            if self.baixar_fotos:
                self._carregador = _CarregadorFotos(self._geracao, [n for n, _ in self._candidatas], self)
                self._carregador.foto_pronta.connect(self._ao_receber_foto)
                self._carregador.start()

    def _montar_cartoes(self):
        while self._layout_cartoes.count():
            item = self._layout_cartoes.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.cartoes = []
        for i, (nome, confianca) in enumerate(self._candidatas):
            cartao = CartaoCandidata(nome, confianca, principal=(i == 0), orientacao=self.orientacao)
            cartao.escolhida.connect(self.escolhida)
            cartao.definir_foto(self._fotos.get(nome))
            self._layout_cartoes.addWidget(cartao, 1)
            self.cartoes.append(cartao)
        if self.orientacao == "vertical":
            self._layout_cartoes.addStretch()
        if self._estado is not None:
            self._marcar_escolhida()

    def _ao_receber_foto(self, geracao, nome, foto):
        if geracao != self._geracao:
            return  # resposta de uma identificação anterior
        self._fotos[nome] = foto
        for cartao in self.cartoes:
            if cartao.nome == nome:
                cartao.definir_foto(foto)

    def _mostrar_aviso(self, texto):
        self.lbl_aviso.setText(texto)
        self.lbl_aviso.setVisible(bool(texto))

    def _parar_carregador(self, esperar=False):
        """
        Desliga o download anterior. Sem esperar: a thread termina sozinha (no máximo a
        requisição em curso) e fica guardada até lá, para não ser destruída rodando.
        """
        carregador, self._carregador = self._carregador, None
        if carregador is None:
            return
        carregador.requestInterruption()
        try:
            carregador.foto_pronta.disconnect(self._ao_receber_foto)
        except (RuntimeError, TypeError):
            pass
        if esperar:
            carregador.wait(5000)
            return
        if carregador.isRunning():
            self._encerrando.add(carregador)
            carregador.finished.connect(lambda c=carregador: self._encerrando.discard(c))

    def encerrar(self):
        """Para o download em andamento (ao fechar a janela)."""
        self._parar_carregador(esperar=True)
        for carregador in list(self._encerrando):
            carregador.wait(5000)


__all__ = ["CartaoCandidata", "PainelCartoes", "ORIENTACOES"]
