"""Foco (v1.6): palco espelhando a foto, pílula, ficha em gaveta e uso pelo teclado."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QPixmap  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QLineEdit  # noqa: E402


def test_foco_pelo_teclado(tmp_path):
    QApplication.instance() or QApplication([])
    from PIL import Image
    from test_layouts import _paineis

    from ui import estado_identificacao as ei
    from ui.custom_widgets import ImageCardWidget
    from ui.layouts.foco import LayoutFoco
    from ui.widgets import componentes_layout as cl
    from ui.widgets.painel_fila import PainelFila

    cl.definir_animacoes(False)  # geometria final na hora, sem esperar a animação
    for nome in ("a.jpg", "b.jpg"):
        Image.new("RGB", (40, 30), "white").save(tmp_path / nome)
    estado = ei.EstadoIdentificacao()
    paineis = _paineis()
    paineis.foto = ImageCardWidget()
    paineis.fila = PainelFila(estado)
    campo = QLineEdit()
    paineis.identificacao = campo
    paineis.fila.abrir_foto.connect(estado.foto_aberta)

    central = LayoutFoco().montar(paineis, estado)
    central.resize(1366, 740)
    central.show()
    QApplication.processEvents()
    controle = central.controle_foco
    palco, gaveta = controle.palco, controle.gaveta

    # Sem foto: palco vazio, sem pílula nem fila
    assert not palco.tem_imagem() and not controle.pilula.isVisible()
    assert not controle.caixa_fila.isVisible()

    # A foto do card aparece no palco; zoom pelo teclado
    pixmap = QPixmap(200, 100)
    pixmap.fill(Qt.darkGreen)
    paineis.foto.set_pixmap(pixmap)
    assert palco.tem_imagem()
    escala = palco.escala()
    palco.setFocus()
    QTest.keyClick(palco, Qt.Key_Plus)
    assert palco.escala() > escala
    QTest.keyClick(palco, Qt.Key_0)
    assert palco.escala() == pytest.approx(escala)

    # Pasta: a fila aparece; ← → trocam de foto; F esconde
    paineis.fila.carregar_pasta(tmp_path)
    paineis.fila._parar_verificacao()
    QApplication.processEvents()
    assert controle.caixa_fila.isVisible()
    paineis.fila.abrir_vizinha(1)
    atual = paineis.fila.fila.atual
    QTest.keyClick(palco, Qt.Key_Right)
    assert paineis.fila.fila.atual == min(atual + 1, 1)
    QTest.keyClick(palco, Qt.Key_Left)
    assert paineis.fila.fila.atual == min(atual + 1, 1) - 1
    QTest.keyClick(palco, Qt.Key_F)
    assert not controle.caixa_fila.isVisible()
    QTest.keyClick(palco, Qt.Key_F)
    assert controle.caixa_fila.isVisible()

    # Com foto aberta, a pílula aparece; I abre e fecha a ficha; Esc fecha
    assert controle.pilula.isVisible()
    QTest.keyClick(palco, Qt.Key_I)
    assert gaveta.esta_aberta() and gaveta.geometry().width() == min(gaveta.largura, palco.width())
    QTest.keyClick(palco, Qt.Key_Escape)
    assert not gaveta.esta_aberta()

    # Num campo de texto, a letra é texto (não abre a ficha)
    campo.setFocus()
    QTest.keyClick(campo, Qt.Key_I)
    assert campo.text().lower() == "i" and not gaveta.esta_aberta()

    # Lista de atalhos: F1 mostra, Esc fecha
    QTest.keyClick(palco, Qt.Key_F1)
    assert controle.lista_atalhos.isVisible()
    QTest.keyClick(palco, Qt.Key_Escape)
    assert not controle.lista_atalhos.isVisible()

    # Confirmar a espécie abre a ficha; Nova identificação (sem foto) esconde a pílula
    estado.identificacao_concluida({"nome_cientifico": "Turdus rufiventris", "status_msg": "ok"})
    estado.confirmar()
    assert gaveta.esta_aberta()
    estado.limpar()
    assert not gaveta.esta_aberta() and not controle.pilula.isVisible()
    central.close()
    paineis.fila.encerrar()
    cl.definir_animacoes(True)
