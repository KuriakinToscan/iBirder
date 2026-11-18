"""Mesa de luz (v1.6): setas na fila, inspetor em acordeão e largura mínima em 1366 px."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QLineEdit  # noqa: E402


def test_mesa_luz_setas_secoes_e_largura(tmp_path):
    QApplication.instance() or QApplication([])
    from PIL import Image
    from test_layouts import _paineis

    from ui import estado_identificacao as ei
    from ui.layouts.mesa_luz import LayoutMesaLuz
    from ui.widgets.painel_fila import PainelFila

    for nome in ("a.jpg", "b.jpg", "c.jpg"):
        Image.new("RGB", (40, 30), "white").save(tmp_path / nome)
    estado = ei.EstadoIdentificacao()
    paineis = _paineis()
    paineis.fila = PainelFila(estado)
    campo = QLineEdit("Turdus")
    paineis.identificacao = campo
    abertas = []
    paineis.fila.abrir_foto.connect(lambda caminho: (abertas.append(caminho), estado.foto_aberta(caminho)))

    central = LayoutMesaLuz().montar(paineis, estado)
    # Cabe em 1366 x 768 sem rolagem horizontal
    assert central.minimumSizeHint().width() <= 1366
    central.resize(1366, 700)
    central.show()
    QApplication.processEvents()
    paineis.fila.carregar_pasta(tmp_path)
    paineis.fila._parar_verificacao()
    abertas.clear()

    controle = central.controle_mesa_luz
    inicio = paineis.fila.fila.atual  # a pasta pode abrir a primeira pendente sozinha
    paineis.fila.lista.setFocus()
    QTest.keyClick(paineis.fila.lista, Qt.Key_Right)
    esperado = 0 if inicio is None else inicio + 1
    assert paineis.fila.fila.atual == esperado
    assert os.path.basename(abertas[-1]) == ("a.jpg", "b.jpg", "c.jpg")[esperado]
    assert controle.navegar(1) and paineis.fila.fila.atual == esperado + 1
    assert controle.navegar(-1) and paineis.fila.fila.atual == esperado
    assert not paineis.fila.abrir_vizinha(-10)  # fora da pasta: não faz nada
    # No campo de texto, a seta move o cursor e não troca de foto
    antes = paineis.fila.fila.atual
    campo.setFocus()
    campo.setCursorPosition(3)
    QTest.keyClick(campo, Qt.Key_Left)
    assert campo.cursorPosition() == 2 and paineis.fila.fila.atual == antes

    # Acordeão: uma seção por vez; o resultado reabre "Outras sugestões"
    sugestoes, sobre = central.secoes_inspetor[0], central.secoes_inspetor[1]
    sobre.abrir()
    assert sobre.esta_aberta() and not sugestoes.esta_aberta()
    estado.identificacao_concluida({"nome_cientifico": "Turdus rufiventris", "status_msg": "ok"})
    assert sugestoes.esta_aberta() and not sobre.esta_aberta()
    central.close()
    paineis.fila.encerrar()
