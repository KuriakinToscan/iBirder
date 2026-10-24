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


"""
Player de áudio nativo (QtMultimedia / FFmpeg) para as vocalizações.

Até a v1.2 o áudio tocava num QWebEngineView (Chromium do Qt). A versão do PySide6
instalada via pip não traz codecs proprietários, então gravações .m4a (AAC) — cerca de
metade das vocalizações de aves do iNaturalist — não tocavam. O QMediaPlayer usa o
FFmpeg incluído no PySide6 e toca M4A, MP3, WAV, FLAC etc.

O arquivo é baixado em segundo plano para temp/audios/ (cache da sessão, limpo ao sair).
"""

import hashlib
import logging

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QSlider, QStyle,
                               QToolButton, QVBoxLayout, QWidget)

from core.paths import TEMP_DIR
from core.style_manager import StyleManager


def caminho_cache(url):
    """Arquivo local para a URL (mesma URL -> mesmo arquivo, mantendo a extensão)."""
    nome = url.split("?")[0].rsplit("/", 1)[-1]
    extensao = nome.rsplit(".", 1)[-1].lower() if "." in nome else "audio"
    chave = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    return TEMP_DIR / "audios" / f"{chave}.{extensao}"


def formatar_tempo(ms):
    segundos = max(0, int(ms // 1000))
    return f"{segundos // 60}:{segundos % 60:02d}"


# Downloads em andamento ficam aqui (e não como filhos do player): se a janela fechar
# no meio do download, a QThread não é destruída em execução (o que derrubaria o app).
_downloads_ativos = set()


class _BaixarAudio(QThread):
    pronto = Signal(str)
    falhou = Signal(str)

    def __init__(self, url, destino):
        super().__init__()
        self.url = url
        self.destino = destino
        _downloads_ativos.add(self)
        self.finished.connect(self._concluido)

    def _concluido(self):
        _downloads_ativos.discard(self)
        self.deleteLater()

    def run(self):
        from core import http
        try:
            if not self.destino.exists():
                resp = http.get(self.url, timeout=30)
                resp.raise_for_status()
                self.destino.parent.mkdir(parents=True, exist_ok=True)
                temporario = self.destino.with_suffix(self.destino.suffix + ".parcial")
                temporario.write_bytes(resp.content)
                temporario.replace(self.destino)
            self.pronto.emit(str(self.destino))
        except Exception as e:
            logging.error(f"Falha ao baixar áudio {self.url}: {e}")
            self.falhou.emit(f"não foi possível baixar o arquivo ({e.__class__.__name__})")


class PlayerAudio(QWidget):
    """Tocar/pausar, barra de posição e tempo. Emite `tocou` quando o usuário inicia a reprodução."""
    tocou = Signal()

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self._arrastando = False

        self.player = QMediaPlayer(self)
        self.saida = QAudioOutput(self)
        self.player.setAudioOutput(self.saida)

        self.btn = QToolButton(self)
        self.btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.btn.setToolTip("Tocar / pausar")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setEnabled(False)
        self.btn.clicked.connect(self.alternar)

        self.barra = QSlider(Qt.Horizontal, self)
        self.barra.setEnabled(False)
        self.barra.sliderPressed.connect(lambda: setattr(self, "_arrastando", True))
        self.barra.sliderReleased.connect(self._soltar_barra)

        self.lbl_tempo = QLabel("0:00 / 0:00", self)
        StyleManager.estilizar(self.lbl_tempo, "color: var(--texto_secundario); font-size: 11px;")

        self.lbl_status = QLabel("Carregando áudio...", self)
        StyleManager.estilizar(self.lbl_status, "color: var(--texto_suave); font-size: 11px;")
        self.lbl_status.setAlignment(Qt.AlignCenter)

        self.btn_navegador = QPushButton("Abrir no navegador", self)
        self.btn_navegador.setProperty("class", "btn-link")
        self.btn_navegador.setCursor(Qt.PointingHandCursor)
        self.btn_navegador.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.url)))
        self.btn_navegador.hide()

        linha = QHBoxLayout()
        linha.setContentsMargins(0, 0, 0, 0)
        linha.addWidget(self.btn)
        linha.addWidget(self.barra, stretch=1)
        linha.addWidget(self.lbl_tempo)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addLayout(linha)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.btn_navegador, alignment=Qt.AlignCenter)

        self.player.durationChanged.connect(self._duracao)
        self.player.positionChanged.connect(self._posicao)
        self.player.playbackStateChanged.connect(self._estado)
        self.player.mediaStatusChanged.connect(self._status_midia)
        self.player.errorOccurred.connect(lambda _erro, msg: self._erro(msg or "formato não suportado"))

        if not url:
            self._erro("áudio não disponível na sessão")
            return
        download = _BaixarAudio(url, caminho_cache(url))
        # Métodos do próprio widget: o Qt desconecta sozinho se o player for destruído antes
        download.pronto.connect(self._arquivo_pronto)
        download.falhou.connect(self._erro)
        download.start()

    def _arquivo_pronto(self, caminho):
        self.player.setSource(QUrl.fromLocalFile(caminho))

    # ---------- controles ----------

    def alternar(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()
            self.tocou.emit()

    def parar(self):
        self.player.stop()

    def _soltar_barra(self):
        self._arrastando = False
        self.player.setPosition(self.barra.value())

    # ---------- eventos do player ----------

    def _duracao(self, ms):
        self.barra.setRange(0, ms)
        self.lbl_tempo.setText(f"0:00 / {formatar_tempo(ms)}")

    def _posicao(self, ms):
        if not self._arrastando:
            self.barra.setValue(ms)
        self.lbl_tempo.setText(f"{formatar_tempo(ms)} / {formatar_tempo(self.player.duration())}")

    def _estado(self, estado):
        icone = QStyle.SP_MediaPause if estado == QMediaPlayer.PlayingState else QStyle.SP_MediaPlay
        self.btn.setIcon(self.style().standardIcon(icone))

    def _status_midia(self, status):
        if status in (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia):
            self.btn.setEnabled(True)
            self.barra.setEnabled(True)
            self.lbl_status.hide()
        elif status == QMediaPlayer.EndOfMedia:
            self.player.setPosition(0)
        elif status == QMediaPlayer.InvalidMedia:
            self._erro("formato de áudio não suportado")

    def _erro(self, mensagem):
        logging.warning(f"Player de áudio: {mensagem} ({self.url})")
        self.btn.setEnabled(False)
        self.barra.setEnabled(False)
        self.lbl_status.setText(f"Falha ao carregar áudio: {mensagem}")
        self.lbl_status.show()
        if self.url:
            self.btn_navegador.show()

    def hideEvent(self, event):
        # Ao fechar a janela que contém o player, o som não continua tocando
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        super().hideEvent(event)
