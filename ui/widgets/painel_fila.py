#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Painel "Fila de fotos" do layout Mesa de trabalho (v1.4).

    Fila de fotos                      [Abrir pasta...]
    Pasta: Saída de campo 2026-10
    3 de 12 gravadas · 2 já tinham registro
    [miniatura] IMG_001.jpg / ✓ Gravada / Turdus rufiventris
    [miniatura] IMG_002.jpg / ▶ Aberta
    [miniatura] IMG_003.jpg / Pendente
    [x] Ir para a próxima ao gravar
                                                 [Pular]

Ao abrir a pasta, uma thread lê as miniaturas e o registro do iBirder de cada foto
(só Pillow, sem ExifTool): as que já foram gravadas antes ficam marcadas e a fila
começa pela primeira pendente. Depois, o painel acompanha o EstadoIdentificacao:
foto aberta vira a atual; foto gravada é marcada e, com a opção ligada, a próxima
pendente abre sozinha.

Vistas (v1.6, `definir_vista`): "lista" (coluna, Mesa de trabalho), "tira" (faixa horizontal
de miniaturas, Mesa de luz) e "grade" (miniaturas grandes em grade). A fila e a lógica são
as mesmas; só muda a arrumação.
"""

import logging
from pathlib import Path

from PIL import Image, ImageOps
from PySide6.QtCore import QSettings, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (QBoxLayout, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QListView, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout,
                               QWidget)

from core import fila_fotos as ff
from core.style_manager import StyleManager
from ui import estado_identificacao as ei

TAMANHO_MINIATURA = 56

# Vista -> (lado da miniatura em px, texto completo no item)
VISTAS = {
    "lista": (TAMANHO_MINIATURA, True),
    "tira": (88, False),
    "grade": (132, False),
}
VISTA_PADRAO = "lista"
ALTURA_TIRA = 132

TEXTO_SITUACAO = {
    ff.PENDENTE: "Pendente",
    ff.GRAVADA: "✓ Gravada",
    ff.JA_GRAVADA: "✓ Já tinha registro",
    ff.PULADA: "Pulada",
}


def _miniatura(caminho, lado=max(lado for lado, _ in VISTAS.values()) * 2):
    """QImage pequena da foto (JPEG decodificado já reduzido), ou None."""
    try:
        with Image.open(caminho) as img:
            img.draft("RGB", (lado, lado))  # JPEG: decodifica direto em escala menor
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((lado, lado))
            dados = img.tobytes()
            return QImage(dados, img.width, img.height, 3 * img.width, QImage.Format_RGB888).copy()
    except Exception as e:
        logging.debug(f"Fila de fotos: sem miniatura para {caminho}: {e}")
        return None


class VerificadorFila(QThread):
    """Lê miniatura e registro do iBirder de cada foto, sem travar a interface."""

    item_verificado = Signal(int, int, bool, str, QImage)  # geração, índice, já gravada, espécie, miniatura

    def __init__(self, geracao, caminhos, parent=None):
        super().__init__(parent)
        self.geracao = geracao
        self.caminhos = list(caminhos)

    def run(self):
        from modules.step6_persistence.registro_ibirder import ler_registro
        for i, caminho in enumerate(self.caminhos):
            if self.isInterruptionRequested():
                return
            registro = ler_registro(caminho)
            especie = (registro or {}).get("dados", {}).get(("Taxonomia", "ScientificName"), "")
            self.item_verificado.emit(self.geracao, i, registro is not None, especie,
                                      _miniatura(caminho) or QImage())


class PainelFila(QFrame):
    """Lista das fotos da pasta; pede à janela para abrir uma foto com `abrir_foto`."""

    abrir_foto = Signal(str)

    def __init__(self, estado=None, parent=None):
        super().__init__(parent)
        self.setProperty("class", "painel")
        StyleManager.apply_shadow(self)
        self.fila = ff.FilaFotos()
        self.settings = QSettings("iBirder", "App")
        self._geracao = 0
        self._verificador = None
        self._verificados = 0
        self._caminho_aberto = None
        self.vista = VISTA_PADRAO

        # Três blocos (cabeçalho, lista, rodapé) num QBoxLayout: na vista "tira" eles ficam
        # lado a lado, nas outras um embaixo do outro
        layout = QBoxLayout(QBoxLayout.TopToBottom, self)
        self._layout = layout
        layout.setContentsMargins(12, 18, 12, 12)
        layout.setSpacing(StyleManager.SPACING_SM)

        self._bloco_cabecalho = QWidget()
        layout_cabecalho = QVBoxLayout(self._bloco_cabecalho)
        layout_cabecalho.setContentsMargins(0, 0, 0, 0)
        layout_cabecalho.setSpacing(StyleManager.SPACING_SM)
        layout.addWidget(self._bloco_cabecalho)

        topo = QHBoxLayout()
        titulo = QLabel("Fila de fotos")
        titulo.setProperty("class", "lbl-titulo-sessao")
        topo.addWidget(titulo)
        topo.addStretch()
        self.btn_abrir = QPushButton("Abrir pasta...")
        self.btn_abrir.setCursor(Qt.PointingHandCursor)
        self.btn_abrir.setToolTip("Escolher a pasta com as fotos da saída de campo (Ctrl+Shift+O)")
        self.btn_abrir.clicked.connect(self.escolher_pasta)
        topo.addWidget(self.btn_abrir)
        layout_cabecalho.addLayout(topo)

        self.lbl_pasta = QLabel("Abra uma pasta para trabalhar as fotos uma a uma.")
        self.lbl_pasta.setWordWrap(True)
        self.lbl_pasta.setProperty("class", "lbl-placeholder")
        layout_cabecalho.addWidget(self.lbl_pasta)
        self.lbl_resumo = QLabel()
        self.lbl_resumo.setWordWrap(True)
        StyleManager.estilizar(self.lbl_resumo, "color: var(--texto_secundario); font-size: 12px;")
        self.lbl_resumo.setVisible(False)
        layout_cabecalho.addWidget(self.lbl_resumo)

        self.lista = QListWidget()
        self.lista.setObjectName("lista_fila")
        self.lista.setIconSize(QSize(TAMANHO_MINIATURA, TAMANHO_MINIATURA))
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lista.setToolTip("Clique duas vezes (ou Enter) para abrir a foto")
        self.lista.itemActivated.connect(self._ao_ativar_item)
        layout.addWidget(self.lista, 1)

        self._bloco_rodape = QWidget()
        layout_rodape = QVBoxLayout(self._bloco_rodape)
        layout_rodape.setContentsMargins(0, 0, 0, 0)
        layout_rodape.setSpacing(StyleManager.SPACING_SM)
        layout.addWidget(self._bloco_rodape)
        self.cb_avancar = QCheckBox("Ir para a próxima ao gravar")
        self.cb_avancar.setChecked(self.settings.value("fila/avancar", True, type=bool))
        self.cb_avancar.toggled.connect(lambda v: self.settings.setValue("fila/avancar", v))
        layout_rodape.addWidget(self.cb_avancar)
        rodape = QHBoxLayout()
        rodape.addStretch()
        self.btn_pular = QPushButton("Pular")
        self.btn_pular.setCursor(Qt.PointingHandCursor)
        self.btn_pular.setToolTip("Deixar esta foto para depois e abrir a próxima pendente")
        self.btn_pular.setEnabled(False)
        self.btn_pular.clicked.connect(self.pular)
        rodape.addWidget(self.btn_pular)
        layout_rodape.addLayout(rodape)

        if estado is not None:
            self.conectar_estado(estado)

    # --- Vista ---

    def definir_vista(self, vista):
        """Arruma o painel como "lista", "tira" ou "grade" (cada layout escolhe a sua)."""
        if vista not in VISTAS:
            raise ValueError(f"Vista desconhecida: {vista}")
        self.vista = vista
        lado, _ = VISTAS[vista]
        lista = self.lista
        # Limites de tamanho de um layout anterior não valem no próximo
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        lista.setIconSize(QSize(lado, lado))
        if vista == "lista":
            self._layout.setDirection(QBoxLayout.TopToBottom)
            lista.setViewMode(QListView.ListMode)
            lista.setFlow(QListView.TopToBottom)
            lista.setWrapping(False)
            lista.setGridSize(QSize())
            lista.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            lista.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self._bloco_cabecalho.setMaximumWidth(16777215)
            self._bloco_rodape.setMaximumWidth(16777215)
        else:
            tira = vista == "tira"
            self._layout.setDirection(QBoxLayout.LeftToRight if tira else QBoxLayout.TopToBottom)
            lista.setViewMode(QListView.IconMode)
            lista.setMovement(QListView.Static)
            lista.setResizeMode(QListView.Adjust)
            lista.setFlow(QListView.LeftToRight)
            lista.setWrapping(not tira)
            lista.setGridSize(QSize(lado + 16, lado + (24 if tira else 40)))
            lista.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded if tira else Qt.ScrollBarAlwaysOff)
            lista.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff if tira else Qt.ScrollBarAsNeeded)
            largura_lateral = 200 if tira else 16777215
            self._bloco_cabecalho.setMaximumWidth(largura_lateral)
            self._bloco_rodape.setMaximumWidth(largura_lateral)
            if tira:
                self.setFixedHeight(ALTURA_TIRA)
        self.lbl_pasta.setVisible(vista != "tira" or not self.fila.itens)
        for i in range(len(self.fila)):
            self._atualizar_item(i)

    # --- Pasta ---

    def escolher_pasta(self):
        inicial = self.settings.value("last_folder", "")
        pasta = QFileDialog.getExistingDirectory(self, "Abrir pasta de fotos", inicial)
        if pasta:
            self.carregar_pasta(pasta)

    def carregar_pasta(self, pasta, caminhos=None):
        """Monta a fila da pasta e verifica as fotos em segundo plano (abre a primeira pendente no fim)."""
        self._parar_verificacao()
        self.fila = ff.FilaFotos(pasta, caminhos)
        self.fila.atual = self.fila.indice_de(self._caminho_aberto)
        self.settings.setValue("last_folder", str(pasta))
        self.lista.clear()
        for item in self.fila.itens:
            QListWidgetItem(self.lista)
        for i in range(len(self.fila)):
            self._atualizar_item(i)
        self.lbl_pasta.setText(f"Pasta: {Path(pasta).name}")
        self.lbl_pasta.setVisible(self.vista != "tira")
        self.lbl_pasta.setProperty("class", "")
        StyleManager.estilizar(self.lbl_pasta, "color: var(--texto); font-weight: 600;")
        self.lbl_resumo.setVisible(True)
        logging.info(f"Fila de fotos: {len(self.fila)} fotos em {pasta}")
        if not self.fila.itens:
            self.lbl_resumo.setText("Nenhuma foto JPG ou PNG nesta pasta.")
            self._atualizar_botoes()
            return
        self.lbl_resumo.setText(f"Verificando as fotos... 0 de {len(self.fila)}")
        self._geracao += 1
        self._verificados = 0
        self._verificador = VerificadorFila(self._geracao, [it.caminho for it in self.fila.itens], self)
        self._verificador.item_verificado.connect(self._ao_verificar_item)
        self._verificador.start()
        self._atualizar_botoes()

    def _parar_verificacao(self):
        if self._verificador is not None and self._verificador.isRunning():
            self._verificador.requestInterruption()
            self._verificador.wait(2000)
        self._verificador = None

    def _ao_verificar_item(self, geracao, indice, ja_gravada, especie, miniatura):
        if geracao != self._geracao or indice >= len(self.fila):
            return  # resposta de uma pasta anterior
        item = self.fila.itens[indice]
        if ja_gravada and item.situacao == ff.PENDENTE:
            self.fila.marcar(indice, ff.JA_GRAVADA, especie=especie)
        if not miniatura.isNull():
            self.lista.item(indice).setIcon(QIcon(QPixmap.fromImage(miniatura)))
        self._atualizar_item(indice)
        self._verificados += 1
        if self._verificados < len(self.fila):
            self.lbl_resumo.setText(f"Verificando as fotos... {self._verificados} de {len(self.fila)}")
            return
        self._atualizar_resumo()
        if self.fila.atual is None:
            self.ir_para_proxima()

    # --- Navegação ---

    def ir_para_proxima(self):
        """Abre a próxima foto pendente; avisa quando a fila acabou."""
        indice = self.fila.proxima()
        if indice is None:
            if self.fila.itens:
                self.lbl_resumo.setText(f"Fila concluída. {self.fila.resumo()}")
            return
        self._abrir(indice)

    def pular(self):
        if self.fila.atual is not None and self.fila.itens[self.fila.atual].situacao == ff.PENDENTE:
            self.fila.marcar(self.fila.atual, ff.PULADA)
            self._atualizar_item(self.fila.atual)
            self._atualizar_resumo()
        self.ir_para_proxima()

    def _ao_ativar_item(self, item_lista):
        self._abrir(self.lista.row(item_lista))

    def _abrir(self, indice):
        item = self.fila.itens[indice]
        if item.situacao == ff.PULADA:
            self.fila.marcar(indice, ff.PENDENTE)  # voltou para ela: deixa de estar pulada
            self._atualizar_resumo()
        self.lista.setCurrentRow(indice)
        self.lista.scrollToItem(self.lista.item(indice))
        self.abrir_foto.emit(str(item.caminho))

    def avanca_ao_gravar(self):
        """A janela pergunta antes de gravar: a próxima foto vai abrir sozinha depois?"""
        return (self.isVisible() and self.cb_avancar.isChecked() and self.fila.atual is not None
                and self.fila.proxima() is not None)

    # --- Estado da identificação ---

    def conectar_estado(self, estado):
        self._estado = estado
        estado.alterado.connect(self._ao_mudar_estado)

    def _ao_mudar_estado(self):
        estado = self._estado
        if estado.etapa == ei.IDENTIFICANDO and estado.caminho != self._caminho_aberto:
            self._definir_atual(estado.caminho)
        elif estado.etapa == ei.SEM_FOTO and self._caminho_aberto is not None:
            self._definir_atual(None)
        elif estado.etapa == ei.GRAVADA and self.fila.atual is not None:
            indice = self.fila.atual
            if self.fila.itens[indice].situacao == ff.GRAVADA and estado.caminho == self._caminho_aberto:
                return  # mesma gravação já registrada
            avancar = self.avanca_ao_gravar()
            self.fila.marcar(indice, ff.GRAVADA, caminho=estado.caminho, especie=estado.nome_cientifico or "")
            self._caminho_aberto = estado.caminho  # a foto pode ter sido renomeada
            self._atualizar_item(indice)
            self._atualizar_resumo()
            if avancar:
                QTimer.singleShot(0, self.ir_para_proxima)  # depois que a janela terminar a gravação

    def _definir_atual(self, caminho):
        self._caminho_aberto = caminho
        anterior, self.fila.atual = self.fila.atual, self.fila.indice_de(caminho)
        for indice in {anterior, self.fila.atual} - {None}:
            self._atualizar_item(indice)
        if self.fila.atual is not None:
            self.lista.setCurrentRow(self.fila.atual)
        self._atualizar_botoes()

    # --- Aparência da lista ---

    def _atualizar_item(self, indice):
        item = self.fila.itens[indice]
        texto = TEXTO_SITUACAO[item.situacao]
        if indice == self.fila.atual and item.situacao in (ff.PENDENTE, ff.PULADA):
            texto = "▶ Aberta"
        if item.especie:
            texto += f"\n{item.especie}"  # linha própria: cabe numa coluna estreita
        linha = self.lista.item(indice)
        _, texto_completo = VISTAS[self.vista]
        # Nas vistas de miniatura, o nome do arquivo e a situação; o resto vai na dica
        linha.setText(f"{item.nome}\n{texto}" if texto_completo else texto.split("\n")[0])
        linha.setToolTip(f"{item.caminho}\n{texto}")
        fonte = linha.font()
        fonte.setBold(indice == self.fila.atual)
        linha.setFont(fonte)

    def _atualizar_resumo(self):
        self.lbl_resumo.setText(self.fila.resumo())

    def _atualizar_botoes(self):
        self.btn_pular.setEnabled(bool(self.fila.itens))

    def encerrar(self):
        """Para a verificação em andamento (ao fechar a janela)."""
        self._parar_verificacao()
