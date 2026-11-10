"""Instância única: a segunda execução entrega a foto à janela aberta (QLocalServer)."""
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtNetwork")

from PySide6.QtCore import QCoreApplication, QElapsedTimer  # noqa: E402

from core import instancia_unica  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


def _esperar(condicao, ms=8000):
    relogio = QElapsedTimer()
    relogio.start()
    while not condicao() and relogio.elapsed() < ms:
        QCoreApplication.processEvents()
    return condicao()


def test_sem_instancia_aberta_nao_envia():
    QCoreApplication.instance() or QCoreApplication([])
    assert not instancia_unica.enviar_para_instancia_aberta("x.jpg", nome=f"ibirder-teste-{uuid.uuid4().hex}")


def test_foto_chega_a_instancia_aberta_vinda_de_outro_processo():
    # Outro processo, como no "Abrir com" real: o envio espera o servidor ler e fechar a conexão
    app = QCoreApplication.instance() or QCoreApplication([])
    nome = f"ibirder-teste-{uuid.uuid4().hex}"
    recebidas = []
    servidor = instancia_unica.ServidorInstancia(recebidas.append, nome=nome, parent=app)
    assert servidor.iniciar()
    caminho = "C:\\Fotos\\sabiá.jpg"
    codigo = ("import sys; from PySide6.QtCore import QCoreApplication; app = QCoreApplication([]); "
              "from core.instancia_unica import enviar_para_instancia_aberta as e; "
              f"sys.exit(0 if e({caminho!r}, nome={nome!r}) else 3)")
    processo = subprocess.Popen([sys.executable, "-c", codigo], cwd=RAIZ)
    assert _esperar(lambda: recebidas)
    assert processo.wait(timeout=10) == 0
    assert recebidas == [caminho]


def test_nome_do_servidor_por_usuario():
    assert instancia_unica.nome_servidor().startswith("iBirder-")
