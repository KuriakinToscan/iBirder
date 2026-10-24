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


def test_fluxo_guiado_segue_a_etapa():
    from ui import estado_identificacao as ei
    from ui.layouts.guiado import LayoutGuiado

    paineis = _paineis()
    estado = ei.EstadoIdentificacao()
    central = LayoutGuiado().montar(paineis, estado)
    central.resize(1366, 700)
    central.show()
    barra = central.findChild(QLabel, "lbl_dica_etapa").parentWidget()

    # Sem foto: só o card da foto aparece
    assert not paineis.identificacao.isVisibleTo(central)
    assert not paineis.referencia.isVisibleTo(central)
    assert "Ctrl+O" in barra.lbl_dica.text()

    estado.foto_aberta("ave.jpg")
    estado.identificacao_concluida({"nome_cientifico": "Turdus rufiventris", "status_msg": "ok"})
    assert paineis.identificacao.isVisibleTo(central) and paineis.referencia.isVisibleTo(central)
    textos = [r.text() for r in barra.rotulos]
    assert textos[0].startswith("✓") and textos[1].startswith("✓") and textos[2].startswith("3")
    assert "etapa-ativa" in barra.rotulos[2].property("class")

    estado.gravada()
    assert all(r.text().startswith("✓") for r in barra.rotulos)
    central.close()
