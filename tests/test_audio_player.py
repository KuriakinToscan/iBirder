"""
Player de áudio nativo (QtMultimedia). Sem rede: o arquivo é colocado direto no cache,
como se já tivesse sido baixado. O player antigo (Chromium do Qt) não tocava .m4a (AAC).
"""
import math
import os
import struct
import time
import wave

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtMultimedia")

from ui.widgets import audio_player as ap  # noqa: E402


def test_formatar_tempo():
    assert ap.formatar_tempo(0) == "0:00"
    assert ap.formatar_tempo(15_440) == "0:15"
    assert ap.formatar_tempo(125_000) == "2:05"


def test_cache_mantem_extensao_e_e_estavel():
    a = ap.caminho_cache("https://static.inaturalist.org/sounds/1188254.m4a?1724933169")
    assert a.suffix == ".m4a" and a == ap.caminho_cache("https://static.inaturalist.org/sounds/1188254.m4a?1724933169")
    assert a != ap.caminho_cache("https://static.inaturalist.org/sounds/145590.wav?1")


def _gerar_wav(caminho, segundos=2):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i / 10))) for i in range(22050 * segundos)))


def test_player_carrega_toca_e_para(monkeypatch, tmp_path):
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtMultimedia import QMediaPlayer
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(ap, "TEMP_DIR", tmp_path)
    url = "https://static.inaturalist.org/sounds/teste.wav?1"
    _gerar_wav(ap.caminho_cache(url))   # já "baixado": não acessa a rede

    def esperar(seg):
        loop = QEventLoop()
        QTimer.singleShot(int(seg * 1000), loop.quit)
        loop.exec()

    p = ap.PlayerAudio(url)
    p.show()
    inicio = time.time()
    while not p.btn.isEnabled() and time.time() - inicio < 15:
        esperar(0.1)
    assert p.btn.isEnabled(), p.lbl_status.text()
    assert 1900 <= p.player.duration() <= 2100
    assert p.lbl_tempo.text() == "0:00 / 0:02"

    tocou = []
    p.tocou.connect(lambda: tocou.append(True))
    p.alternar()
    assert tocou == [True]
    assert p.player.playbackState() == QMediaPlayer.PlayingState
    p.parar()
    assert p.player.playbackState() == QMediaPlayer.StoppedState
    p.close()


def test_sem_url_mostra_erro():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    p = ap.PlayerAudio("")
    assert not p.btn.isEnabled() and "não disponível" in p.lbl_status.text()
