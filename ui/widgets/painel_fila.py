#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Painel "Fila de fotos" (v1.4, da antiga Mesa de trabalho; hoje nos layouts da v1.6).

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

Vistas (v1.6, `definir_vista`): "lista" (coluna, Foco), "tira" (faixa horizontal
de miniaturas, Mesa de luz) e "grade" (miniaturas grandes em grade, Trilha). A fila e a lógica
são as mesmas; só muda a arrumação. Nas vistas de miniatura, cada foto é um cartão do mesmo
tamanho (`DelegadoCartaoFila`): miniatura quadrada com a foto inteira, selo da situação no
canto e duas linhas (nome do arquivo; espécie ou situação).
"""

import logging
from pathlib import Path

from PIL import Image, ImageOps
from PySide6.QtCore import QRect, QSettings, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QFontMetrics, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (QBoxLayout, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QListView, QListWidget, QListWidgetItem, QPushButton, QStyle,
                               QStyledItemDelegate, QStyleOptionViewItem, QVBoxLayout, QWidget)

from core import fila_fotos as ff
from core.style_manager import StyleManager
from ui import estado_identificacao as ei

TAMANHO_MINIATURA = 56

# Vista -> (lado da miniatura em px, cartão desenhado pelo DelegadoCartaoFila)
VISTAS = {
    "lista": (TAMANHO_MINIATURA, False),
    "tira": (88, True),
    "grade": (100, True),  # três por linha na coluna da Trilha
}
VISTA_PADRAO = "lista"

# Dados de cada item para o cartão (além do ícone e do texto completo)
PAPEL_NOME = Qt.UserRole + 1
PAPEL_LINHA2 = Qt.UserRole + 2
PAPEL_SELO = Qt.UserRole + 3

# Selo da situação: (símbolo, token do fundo, token do símbolo); pendente não tem selo
SELOS = {
    "aberta": ("▶", "destaque", "texto_destaque"),
    ff.GRAVADA: ("✓", "sucesso_fundo", "sucesso_texto"),
    ff.JA_GRAVADA: ("✓", "sucesso_fundo", "sucesso_texto"),
    ff.PULADA: ("»", "alerta_fundo", "alerta_texto"),
}

TEXTO_SITUACAO = {
    ff.PENDENTE: "Pendente",
    ff.GRAVADA: "✓ Gravada",
    ff.JA_GRAVADA: "✓ Já tinha registro",
    ff.PULADA: "Pulada",
}


def _miniatura(caminho, lado=max(lado for lado, _ in VISTAS.values()) * 2):
    """
    QImage quadrada (lado x lado) com a foto inteira centralizada e o resto transparente,
    ou None. Quadrada para que retrato e paisagem deem cartões do mesmo tamanho.
    """
    try:
        with Image.open(caminho) as img:
            img.draft("RGB", (lado, lado))  # JPEG: decodifica direto em escala menor
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((lado, lado))
            tela = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
            tela.paste(img, ((lado - img.width) // 2, (lado - img.height) // 2))
            dados = tela.tobytes()
            return QImage(dados, lado, lado, 4 * lado, QImage.Format_RGBA8888).copy()
    except Exception as e:
        logging.debug(f"Fila de fotos: sem miniatura para {caminho}: {e}")
        return None


class DelegadoCartaoFila(QStyledItemDelegate):
    """
    Cartão de uma foto nas vistas de miniatura: todos do mesmo tamanho, com a miniatura
    quadrada, o selo da situação no canto e duas linhas elididas (nome do arquivo; espécie
    ou situação). As cores vêm do tema ativo na hora de desenhar.
    """

    MARGEM = 6
    SELO = 22

    def __init__(self, lado, parent=None):
        super().__init__(parent)
        self.lado = lado

    def _fonte_pequena(self, fonte):
        pequena = type(fonte)(fonte)
        pequena.setBold(False)
        pequena.setPointSizeF(max(fonte.pointSizeF() - 1, 7))
        return pequena

    def tamanho(self, fonte):
        """Tamanho fixo do cartão (miniatura + duas linhas + margens)."""
        linhas = QFontMetrics(fonte).height() + QFontMetrics(self._fonte_pequena(fonte)).height()
        return QSize(self.lado + 2 * self.MARGEM + 8, self.lado + 3 * self.MARGEM + linhas + 2)

    def sizeHint(self, option, index):
        return self.tamanho(option.font)

    def paint(self, painter, option, index):
        from core.style_manager import StyleManager
        opcao = QStyleOptionViewItem(option)
        self.initStyleOption(opcao, index)
        estilo = opcao.widget.style() if opcao.widget is not None else None
        # Fundo do item (hover, seleção) pelo estilo, sem ícone e sem texto
        fundo = QStyleOptionViewItem(opcao)
        fundo.text = ""
        fundo.icon = QIcon()
        fundo.features &= ~QStyleOptionViewItem.HasDecoration
        if estilo is not None:
            estilo.drawControl(QStyle.CE_ItemViewItem, fundo, painter, opcao.widget)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        ret = opcao.rect
        foto = QRect(ret.x() + (ret.width() - self.lado) // 2, ret.y() + self.MARGEM, self.lado, self.lado)
        icone = index.data(Qt.DecorationRole)
        if isinstance(icone, QIcon) and not icone.isNull():
            icone.paint(painter, foto, Qt.AlignCenter)
        else:  # miniatura ainda não lida
            painter.setPen(StyleManager.qcor("borda"))
            painter.setBrush(StyleManager.qcor("superficie_alt"))
            painter.drawRoundedRect(foto.adjusted(4, 4, -4, -4), 6, 6)
        selo = SELOS.get(index.data(PAPEL_SELO))
        if selo:
            simbolo, token_fundo, token_texto = selo
            area = QRect(foto.right() - self.SELO - 2, foto.top() + 2, self.SELO, self.SELO)
            painter.setPen(StyleManager.qcor("superficie"))
            painter.setBrush(StyleManager.qcor(token_fundo))
            painter.drawEllipse(area)
            fonte_selo = type(opcao.font)(opcao.font)
            fonte_selo.setBold(True)
            painter.setFont(fonte_selo)
            painter.setPen(StyleManager.qcor(token_texto))
            painter.drawText(area, Qt.AlignCenter, simbolo)
        # Duas linhas, elididas na largura do cartão
        largura = ret.width() - 2 * self.MARGEM
        y = foto.bottom() + self.MARGEM
        fonte = opcao.font
        metricas = QFontMetrics(fonte)
        painter.setFont(fonte)
        painter.setPen(StyleManager.qcor("texto"))
        nome = metricas.elidedText(index.data(PAPEL_NOME) or "", Qt.ElideMiddle, largura)
        painter.drawText(QRect(ret.x() + self.MARGEM, y, largura, metricas.height()), Qt.AlignHCenter, nome)
        y += metricas.height()
        pequena = self._fonte_pequena(fonte)
        metricas2 = QFontMetrics(pequena)
        painter.setFont(pequena)
        painter.setPen(StyleManager.qcor("texto_secundario"))
        linha2 = metricas2.elidedText(index.data(PAPEL_LINHA2) or "", Qt.ElideRight, largura)
        painter.drawText(QRect(ret.x() + self.MARGEM, y, largura, metricas2.height()), Qt.AlignHCenter, linha2)
        painter.restore()


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
    atual_ativada = Signal()  # clique na foto que já está aberta (não abre de novo)

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

        # Três blocos (cabeçalho, lista, rodapé), um embaixo do outro. Na vista "tira", o
        # cabeçalho e o rodapé viram uma barra só, acima das miniaturas (que ficam com a largura toda)
        layout = QVBoxLayout(self)
        self._layout = layout
        layout.setContentsMargins(12, 18, 12, 12)
        layout.setSpacing(StyleManager.SPACING_SM)

        self._barra = QWidget()
        self._layout_barra = QHBoxLayout(self._barra)
        self._layout_barra.setContentsMargins(0, 0, 0, 0)
        self._layout_barra.setSpacing(StyleManager.SPACING_LG)
        self._barra.hide()
        layout.addWidget(self._barra)

        self._bloco_cabecalho = QWidget()
        layout_cabecalho = QBoxLayout(QBoxLayout.TopToBottom, self._bloco_cabecalho)
        self._layout_cabecalho = layout_cabecalho
        layout_cabecalho.setContentsMargins(0, 0, 0, 0)
        layout_cabecalho.setSpacing(StyleManager.SPACING_SM)
        layout.addWidget(self._bloco_cabecalho)

        topo = QHBoxLayout()
        topo.setSpacing(StyleManager.SPACING_MD)
        titulo = QLabel("Fila de fotos")
        titulo.setProperty("class", "lbl-titulo-sessao")
        topo.addWidget(titulo, 1)
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
        layout_cabecalho.addWidget(self.lbl_resumo, 1)

        self.lista = QListWidget()
        self.lista.setObjectName("lista_fila")
        self.lista.setIconSize(QSize(TAMANHO_MINIATURA, TAMANHO_MINIATURA))
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lista.setToolTip("Clique duas vezes (ou Enter) para abrir a foto")
        self.lista.itemActivated.connect(self._ao_ativar_item)
        self._delegado_texto = self.lista.itemDelegate()
        self._delegados = {vista: DelegadoCartaoFila(lado, self.lista)
                           for vista, (lado, cartao) in VISTAS.items() if cartao}
        layout.addWidget(self.lista, 1)

        self._bloco_rodape = QWidget()
        layout_rodape = QBoxLayout(QBoxLayout.TopToBottom, self._bloco_rodape)
        self._layout_rodape = layout_rodape
        layout_rodape.setContentsMargins(0, 0, 0, 0)
        layout_rodape.setSpacing(StyleManager.SPACING_SM)
        layout.addWidget(self._bloco_rodape)
        self.cb_avancar = QCheckBox("Ir para a próxima ao gravar")
        self.cb_avancar.setChecked(self.settings.value("fila/avancar", True, type=bool))
        self.cb_avancar.toggled.connect(lambda v: self.settings.setValue("fila/avancar", v))
        layout_rodape.addWidget(self.cb_avancar)
        rodape = QHBoxLayout()
        self.btn_pular = QPushButton("Pular")
        self.btn_pular.setCursor(Qt.PointingHandCursor)
        self.btn_pular.setToolTip("Deixar esta foto para depois e abrir a próxima pendente")
        self.btn_pular.setEnabled(False)
        self.btn_pular.clicked.connect(self.pular)
        rodape.addWidget(self.btn_pular, 0, Qt.AlignRight)
        layout_rodape.addLayout(rodape)

        if estado is not None:
            self.conectar_estado(estado)

    # --- Vista ---

    def definir_vista(self, vista):
        """Arruma o painel como "lista", "tira" ou "grade" (cada layout escolhe a sua)."""
        if vista not in VISTAS:
            raise ValueError(f"Vista desconhecida: {vista}")
        self.vista = vista
        lado, cartao = VISTAS[vista]
        lista = self.lista
        tira = vista == "tira"
        # Limites de tamanho de um layout anterior não valem no próximo
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        lista.setMinimumHeight(0)
        lista.setMaximumHeight(16777215)
        lista.setIconSize(QSize(lado, lado))
        self._montar_barra(tira)
        if not cartao:
            lista.setItemDelegate(self._delegado_texto)
            lista.setViewMode(QListView.ListMode)
            lista.setFlow(QListView.TopToBottom)
            lista.setWrapping(False)
            lista.setGridSize(QSize())
            lista.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            lista.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            delegado = self._delegados[vista]
            lista.setItemDelegate(delegado)
            lista.setViewMode(QListView.IconMode)
            lista.setMovement(QListView.Static)
            lista.setResizeMode(QListView.Adjust)
            lista.setFlow(QListView.LeftToRight)
            lista.setWrapping(not tira)
            lista.setUniformItemSizes(True)
            lista.setSpacing(0)
            lista.setGridSize(delegado.tamanho(lista.font()) + QSize(4, 4))
            lista.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded if tira else Qt.ScrollBarAlwaysOff)
            lista.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff if tira else Qt.ScrollBarAsNeeded)
        self.lbl_pasta.setVisible(not tira or not self.fila.itens)
        for i in range(len(self.fila)):
            self._atualizar_item(i)
        if tira:
            self.ajustar_tira_vazia()

    def _montar_barra(self, tira):
        """Na tira, cabeçalho e rodapé numa barra acima das miniaturas; nas outras, nos extremos."""
        for bloco in (self._bloco_cabecalho, self._bloco_rodape):
            self._layout.removeWidget(bloco)
            self._layout_barra.removeWidget(bloco)
        direcao = QBoxLayout.LeftToRight if tira else QBoxLayout.TopToBottom
        self._layout_cabecalho.setDirection(direcao)
        self._layout_rodape.setDirection(direcao)
        self._layout_cabecalho.setSpacing(StyleManager.SPACING_LG if tira else StyleManager.SPACING_SM)
        self._layout_rodape.setSpacing(StyleManager.SPACING_LG if tira else StyleManager.SPACING_SM)
        self.lbl_resumo.setWordWrap(not tira)
        if tira:
            self._layout_barra.addWidget(self._bloco_cabecalho, 1)
            self._layout_barra.addWidget(self._bloco_rodape, 0)
            self._layout.setContentsMargins(12, 10, 12, 10)
        else:
            self._layout.insertWidget(self._layout.indexOf(self.lista), self._bloco_cabecalho)
            self._layout.addWidget(self._bloco_rodape)
            self._layout.setContentsMargins(12, 18, 12, 12)
        self._barra.setVisible(tira)

    def altura_lista_tira(self):
        """Altura da faixa de miniaturas: um cartão, a barra de rolagem e as bordas."""
        lista = self.lista
        rolagem = lista.style().pixelMetric(QStyle.PM_ScrollBarExtent, None, lista)
        return lista.gridSize().height() + rolagem + 2 * lista.frameWidth() + 8

    def ajustar_tira_vazia(self):
        """
        Vista "tira": sem fotos, a lista vazia some e a tira fica só com a barra (Abrir pasta,
        opções), na altura mínima; com fotos, a faixa de miniaturas com um cartão inteiro de altura.
        Só mexe na diagramação.
        """
        if self.vista != "tira":
            return
        vazia = self.lista.count() == 0
        self.lista.setVisible(not vazia)
        if not vazia:
            self.lista.setFixedHeight(self.altura_lista_tira())
        self._layout.activate()
        self.setFixedHeight(max(self._layout.minimumSize().height(), 48))

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

    def abrir_vizinha(self, passo):
        """
        Abre a foto anterior (passo -1) ou a seguinte (+1) da pasta, qualquer que seja a
        situação dela (setas ← → da Mesa de luz). Sem foto aberta, começa pela primeira.
        Devolve False quando não há para onde ir.
        """
        if not self.fila.itens:
            return False
        atual = self.fila.atual
        indice = 0 if atual is None else atual + passo
        if not 0 <= indice < len(self.fila.itens):
            return False
        self._abrir(indice)
        return True

    def pular(self):
        if self.fila.atual is not None and self.fila.itens[self.fila.atual].situacao == ff.PENDENTE:
            self.fila.marcar(self.fila.atual, ff.PULADA)
            self._atualizar_item(self.fila.atual)
            self._atualizar_resumo()
        self.ir_para_proxima()

    def _ao_ativar_item(self, item_lista):
        self._ativar(self.lista.row(item_lista))

    def _ativar(self, indice):
        """Clique duplo/Enter numa foto: a já aberta não é aberta de novo (nada de nova consulta)."""
        if indice is None or not 0 <= indice < len(self.fila.itens):
            return
        if indice == self.fila.atual:
            self.atual_ativada.emit()
            return
        self._abrir(indice)

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
        situacao = TEXTO_SITUACAO[item.situacao]
        selo = item.situacao
        if indice == self.fila.atual and item.situacao in (ff.PENDENTE, ff.PULADA):
            situacao, selo = "▶ Aberta", "aberta"
        texto = situacao + (f"\n{item.especie}" if item.especie else "")  # linha própria: coluna estreita
        linha = self.lista.item(indice)
        linha.setText(f"{item.nome}\n{texto}")
        linha.setToolTip(f"{item.caminho}\n{texto}")
        # Cartão (tira e grade): nome do arquivo; espécie, ou a situação; selo no canto da foto
        linha.setData(PAPEL_NOME, item.nome)
        linha.setData(PAPEL_LINHA2, item.especie or situacao)
        linha.setData(PAPEL_SELO, selo)
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
