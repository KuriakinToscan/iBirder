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
Autoteste de inicialização (python main.py --smoke-test / iBirder.exe --smoke-test).

Abre o app completo e, após alguns segundos, confere os componentes que o
instalador precisa levar. Encerra com código 0 (tudo certo) ou 1 (falha).
Usado pelo GitHub Actions para validar o executável gerado.
"""

import json
import logging
import platform
import subprocess

from core.paths import APP_DIR


def _modelo():
    from modules.step1_identity.id_worker import tflite
    if tflite is None:
        raise RuntimeError("runtime TFLite (ai-edge-litert) ausente")
    interp = tflite.Interpreter(model_path=str(APP_DIR / "assets" / "models" / "inat_vision_small.tflite"))
    interp.allocate_tensors()
    rotulos = (APP_DIR / "assets" / "models" / "inat_labels.txt").read_text(encoding="utf-8").splitlines()
    saida = interp.get_output_details()[0]["shape"][-1]
    if saida != len([r for r in rotulos if r.strip()]):
        raise RuntimeError(f"modelo com {saida} saídas e {len(rotulos)} rótulos")
    return f"{saida} espécies"


def _exiftool():
    exe = APP_DIR / "assets" / "exiftool" / "exiftool.exe"
    if not exe.exists():
        raise FileNotFoundError(exe)
    if platform.system() != "Windows":
        return "presente (execução só no Windows)"
    r = subprocess.run([str(exe), "-ver"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return f"versão {r.stdout.strip()}"


def _biomas():
    from modules.step3_geography.geo_analyst import GeoAnalyst
    bioma = GeoAnalyst().get_biome(-23.55, -46.63)
    if bioma != "Mata Atlântica":
        raise RuntimeError(f"São Paulo resultou em {bioma!r}")
    return "São Paulo -> Mata Atlântica"


def _ebird():
    from modules.step5_taxonomy import ebird_taxonomy
    r = ebird_taxonomy.buscar("Pitangus sulphuratus")
    if not r or r["species_code"] != "grekis":
        raise RuntimeError("tabela eBird ausente ou inválida")
    return "Pitangus sulphuratus -> grekis"


def _conservacao():
    from modules.step3_geography import listas_conservacao as listas
    nacional = listas.status_nacional("Harpia harpyja")
    if not nacional or nacional["categoria"] != "VU":
        raise RuntimeError("lista nacional (MMA) ausente ou inválida")
    if listas.anexo_cites("Harpia harpyja") != "I":
        raise RuntimeError("tabela da CITES ausente ou inválida")
    if not listas.registrada_no_brasil("Pitangus sulphuratus"):
        raise RuntimeError("lista de ocorrência no Brasil ausente")
    return "Harpia harpyja -> VU (MMA), Anexo I (CITES)"


def _guia():
    json.loads((APP_DIR / "assets" / "models" / "model_meta.json").read_text(encoding="utf-8"))
    for arquivo in ("guia_do_usuario.md", "manual_apis_nuvem.md"):
        if not (APP_DIR / arquivo).exists():
            raise FileNotFoundError(arquivo)
    return "manuais e metadados presentes"


def _mapa(janela):
    """O mapa precisa carregar dentro do executável (QtWebEngine é o ponto frágil do PyInstaller)."""
    import time
    from PySide6.QtCore import QEventLoop, QTimer
    mapa = getattr(janela, "map_principal", None)
    if mapa is None:
        raise RuntimeError("janela sem mapa")
    limite = time.time() + 20
    while not mapa._pronto and time.time() < limite:
        loop = QEventLoop()
        QTimer.singleShot(200, loop.quit)
        loop.exec()
    if not mapa._pronto:
        raise RuntimeError("página do mapa não carregou em 20 s")
    return "página Leaflet carregada"


def _audio():
    """O player de vocalizações (QtMultimedia/FFmpeg) precisa estar no executável."""
    import math
    import struct
    import time
    import wave
    from PySide6.QtCore import QEventLoop, QTimer, QUrl
    from PySide6.QtMultimedia import QMediaPlayer
    from core.paths import TEMP_DIR
    arquivo = TEMP_DIR / "autoteste_audio.wav"
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(arquivo), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i / 10))) for i in range(22050)))
    player = QMediaPlayer()
    player.setSource(QUrl.fromLocalFile(str(arquivo)))
    limite = time.time() + 10
    while player.mediaStatus() not in (QMediaPlayer.LoadedMedia, QMediaPlayer.InvalidMedia) and time.time() < limite:
        loop = QEventLoop()
        QTimer.singleShot(100, loop.quit)
        loop.exec()
    status = player.mediaStatus()
    player.setSource(QUrl())
    if status != QMediaPlayer.LoadedMedia:
        raise RuntimeError(f"áudio não carregou (status {status.name})")
    return f"WAV de teste carregado ({player.duration() if player.duration() > 0 else 1000} ms)"


VERIFICACOES = [
    ("Modelo de IA", _modelo),
    ("ExifTool", _exiftool),
    ("Biomas (IBGE)", _biomas),
    ("Taxonomia eBird", _ebird),
    ("Listas de conservação", _conservacao),
    ("Manuais", _guia),
    ("Áudio (QtMultimedia)", _audio),
]


def executar_smoke_test(janela=None):
    """Executa as verificações, registra no log/console e retorna o código de saída."""
    falhas = 0
    verificacoes = list(VERIFICACOES)
    if janela is not None:
        verificacoes.append(("Mapa (QtWebEngine)", lambda: _mapa(janela)))
    for nome, verificar in verificacoes:
        try:
            detalhe = verificar()
            msg = f"[SMOKE] OK    {nome}: {detalhe}"
        except Exception as e:
            falhas += 1
            msg = f"[SMOKE] FALHA {nome}: {e!r}"
        logging.info(msg)
        print(msg, flush=True)
    resultado = "SUCESSO" if falhas == 0 else f"{falhas} FALHA(S)"
    logging.info(f"[SMOKE] Resultado: {resultado}")
    print(f"[SMOKE] Resultado: {resultado}", flush=True)
    return 0 if falhas == 0 else 1
