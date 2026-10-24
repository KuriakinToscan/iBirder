"""
Layouts da janela principal (v1.4): cada layout usa todos os painéis uma única vez e
trocar de layout só reparenta os painéis (o conteúdo não é recriado). Sem QtWebEngine:
os painéis aqui são widgets simples.
"""
import os
from dataclasses import fields

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from ui.layouts import LAYOUT_PADRAO, LAYOUTS, LAYOUTS_PLANEJADOS, Paineis, obter_layout  # noqa: E402


def _paineis():
    QApplication.instance() or QApplication([])
    return Paineis(**{f.name: QLabel(f.name) for f in fields(Paineis)})


def _contem(raiz, widget):
    pai = widget.parentWidget()
    while pai is not None:
        if pai is raiz:
            return True
        pai = pai.parentWidget()
    return False


def test_registro():
    assert LAYOUT_PADRAO in LAYOUTS
    assert obter_layout(None).id == LAYOUT_PADRAO
    assert obter_layout("inexistente").id == LAYOUT_PADRAO
    for id_layout, layout in LAYOUTS.items():
        assert layout.id == id_layout and layout.nome and layout.descricao
    ids_planejados = [item[0] for item in LAYOUTS_PLANEJADOS]
    assert len(set(ids_planejados)) == len(ids_planejados)


@pytest.mark.parametrize("layout", LAYOUTS.values(), ids=list(LAYOUTS))
def test_layout_usa_todos_os_paineis(layout):
    paineis = _paineis()
    central = layout.montar(paineis)
    faltando = [f.name for f in fields(Paineis) if not _contem(central, getattr(paineis, f.name))]
    assert not faltando, f"{layout.id} não posicionou: {faltando}"


@pytest.mark.parametrize("layout", LAYOUTS.values(), ids=list(LAYOUTS))
def test_trocar_layout_reaproveita_paineis(layout):
    paineis = _paineis()
    paineis.identificacao.setText("Turdus rufiventris")
    primeiro = layout.montar(paineis)
    segundo = obter_layout(LAYOUT_PADRAO).montar(paineis)
    for painel in paineis.todos():
        assert _contem(segundo, painel) and not _contem(primeiro, painel)
    primeiro.deleteLater()  # descartar o antigo não leva os painéis junto
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert paineis.identificacao.text() == "Turdus rufiventris"
