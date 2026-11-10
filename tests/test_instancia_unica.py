"""Instância única: a segunda execução entrega a foto à janela aberta (QLocalServer)."""
import uuid

import pytest

pytest.importorskip("PySide6.QtNetwork")

from PySide6.QtCore import QCoreApplication, QElapsedTimer  # noqa: E402

from core import instancia_unica  # noqa: E402


def _esperar(condicao, ms=3000):
    relogio = QElapsedTimer()
    relogio.start()
    while not condicao() and relogio.elapsed() < ms:
        QCoreApplication.processEvents()
    return condicao()


def test_sem_instancia_aberta_nao_envia():
    QCoreApplication.instance() or QCoreApplication([])
    assert not instancia_unica.enviar_para_instancia_aberta("x.jpg", nome=f"ibirder-teste-{uuid.uuid4().hex}")


def test_foto_chega_a_instancia_aberta():
    app = QCoreApplication.instance() or QCoreApplication([])
    nome = f"ibirder-teste-{uuid.uuid4().hex}"
    recebidas = []
    servidor = instancia_unica.ServidorInstancia(recebidas.append, nome=nome, parent=app)
    assert servidor.iniciar()
    assert instancia_unica.enviar_para_instancia_aberta("C:\\Fotos\\sabiá.jpg", nome=nome)
    assert _esperar(lambda: recebidas)
    assert recebidas == ["C:\\Fotos\\sabiá.jpg"]


def test_nome_do_servidor_por_usuario():
    assert instancia_unica.nome_servidor().startswith("iBirder-")
