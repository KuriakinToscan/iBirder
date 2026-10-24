"""
Busca rápida de espécies (Ctrl+K): catálogo embarcado (eBird + registradas no Brasil) e
o comportamento do Enter no campo com e sem sugestão marcada. Sem rede.
"""
import os

import pytest

from core import catalogo_especies as cat


def test_catalogo_registradas_no_brasil_primeiro():
    especies = cat.carregar()
    assert len(especies) > 10000
    assert especies[0]["no_brasil"]
    primeira_fora = next(i for i, e in enumerate(especies) if not e["no_brasil"])
    assert all(not e["no_brasil"] for e in especies[primeira_fora:])


def test_busca_por_cientifico_ingles_e_sem_acento():
    assert cat.buscar("pitangus")[0]["nome_cientifico"] == "Pitangus sulphuratus"
    assert "Pitangus sulphuratus" in [e["nome_cientifico"] for e in cat.buscar("great kiskadee")]
    # Todas as palavras precisam casar, em qualquer dos dois nomes
    assert [e["nome_cientifico"] for e in cat.buscar("turdus rufiv")][0] == "Turdus rufiventris"
    assert cat.buscar("TURDUS RUFIVENTRIS")[0]["nome_cientifico"] == "Turdus rufiventris"
    assert cat.buscar("p") == []  # menos de 2 letras não busca
    assert len(cat.buscar("a", limite=5)) == 0 and len(cat.buscar("an", limite=5)) == 5


def test_rotulo():
    assert cat.rotulo({"nome_cientifico": "Pitangus sulphuratus", "nome_ingles": "Great Kiskadee"}) == \
        "Pitangus sulphuratus — Great Kiskadee"
    assert cat.rotulo({"nome_cientifico": "Xus yus", "nome_ingles": ""}) == "Xus yus"


@pytest.fixture
def campo():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6.QtTest")
    from PySide6.QtWidgets import QApplication, QLineEdit
    from ui.widgets.busca_especies import BuscaEspecies
    app = QApplication.instance() or QApplication([])
    buscas = []
    edit = QLineEdit()
    edit.show()
    busca = BuscaEspecies(edit, lambda: buscas.append(edit.text()))
    return app, edit, busca, buscas


def _processar(app, vezes=5):
    for _ in range(vezes):
        app.processEvents()


def test_enter_numa_sugestao_busca_so_a_sugestao(campo):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    app, edit, busca, buscas = campo
    edit.setFocus()
    QTest.keyClicks(edit, "kiskad")
    _processar(app)
    assert busca.popup().isVisible()
    QTest.keyClick(busca.popup(), Qt.Key_Down)
    QTest.keyClick(busca.popup(), Qt.Key_Return)
    _processar(app)
    # Uma busca só, já com o nome científico (antes do ajuste, "kiskad" também era buscado)
    assert len(buscas) == 1 and buscas[0] in ("Philohydor lictor", "Pitangus sulphuratus")
    assert edit.text() == buscas[0]


def test_enter_sem_sugestao_marcada_busca_o_texto(campo):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    app, edit, busca, buscas = campo
    edit.setFocus()
    QTest.keyClicks(edit, "Pitangus sulphuratus")
    _processar(app)
    QTest.keyClick(edit, Qt.Key_Return)
    _processar(app)
    assert buscas == ["Pitangus sulphuratus"]
