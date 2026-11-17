"""
Componentes comuns dos layouts da v1.6 (ui/widgets/componentes_layout.py) e as vistas
da fila de fotos. Sem QtWebEngine.
"""
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QApplication, QLabel, QListView, QWidget  # noqa: E402

from ui.widgets.componentes_layout import (Gaveta, GrupoSecoes, RodapeAcoes, SecaoRecolhivel,  # noqa: E402
                                           Sobreposicao, geometria_ancorada)

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_geometria_ancorada():
    assert geometria_ancorada(1000, 600, 400, 80, "inferior-centro", 16) == (300, 504, 400, 80)
    assert geometria_ancorada(1000, 600, 200, 50, "superior-direita", 10) == (790, 10, 200, 50)
    assert geometria_ancorada(1000, 600, 100, 50, "esquerda", 16) == (16, 16, 100, 568)
    # Maior que o hospedeiro: encolhe para caber dentro das margens
    assert geometria_ancorada(300, 200, 800, 80, "centro", 10) == (10, 60, 280, 80)


def test_secao_recolhivel_e_grupo(app):
    a, b = SecaoRecolhivel("Sobre", QLabel("a")), SecaoRecolhivel("Sons", QLabel("b"), aberta=False)
    assert a.esta_aberta() and not b.esta_aberta()
    assert not b.corpo.isVisibleTo(b)
    grupo = GrupoSecoes(exclusivo=True)
    grupo.adicionar(a)
    grupo.adicionar(b)
    b.abrir()
    assert b.esta_aberta() and not a.esta_aberta()
    assert a.cabecalho.text().startswith("▸") and b.cabecalho.text().startswith("▾")
    # Painel compartilhado pode ser trocado de seção
    novo = QLabel("novo")
    a.definir_conteudo(novo)
    assert a.conteudo() is novo and novo.parentWidget() is a.corpo


def test_rodape_acoes(app):
    rodape = RodapeAcoes()
    esquerda, direita = rodape.adicionar_esquerda(QLabel("Voltar")), rodape.adicionar_direita(QLabel("Gravar"))
    rodape.resize(800, 60)
    rodape.show()
    QApplication.processEvents()
    assert esquerda.geometry().right() < direita.geometry().left()
    rodape.close()


def test_sobreposicao_e_gaveta(app):
    # Hospedeiro filho de uma janela: o tamanho de uma janela de topo depende da plataforma
    janela = QWidget()
    janela.resize(1200, 800)
    hospedeiro = QWidget(janela)
    hospedeiro.setGeometry(0, 0, 1000, 600)
    janela.show()
    pilula = Sobreposicao(hospedeiro, "inferior-centro", margem=20)
    pilula.setFixedSize(400, 80)
    pilula.show()
    QApplication.processEvents()
    assert pilula.geometry().getRect() == (300, 500, 400, 80)
    hospedeiro.resize(800, 500)
    QApplication.processEvents()
    assert pilula.geometry().getRect() == (200, 400, 400, 80)
    with pytest.raises(ValueError):
        Sobreposicao(hospedeiro, "lado-errado")

    gaveta = Gaveta(hospedeiro, largura=300, animar=False)
    eventos = []
    gaveta.alternada.connect(eventos.append)
    assert not gaveta.isVisible()
    gaveta.abrir()
    assert gaveta.isVisible() and gaveta.geometry().getRect() == (500, 0, 300, 500)
    gaveta.alternar()
    assert not gaveta.isVisible() and not gaveta.esta_aberta()
    assert eventos == [True, False]
    janela.close()


def test_fila_troca_de_vista(app, tmp_path):
    from PIL import Image
    from ui.widgets.painel_fila import ALTURA_TIRA, PainelFila

    for nome in ("a.jpg", "b.jpg"):
        Image.new("RGB", (40, 30), "white").save(tmp_path / nome)
    painel = PainelFila()
    painel.carregar_pasta(tmp_path)
    painel._parar_verificacao()
    painel.definir_vista("tira")
    assert painel.lista.viewMode() == QListView.IconMode and not painel.lista.isWrapping()
    assert painel.height() == ALTURA_TIRA or painel.maximumHeight() == ALTURA_TIRA
    assert painel.lista.item(0).text() == "Pendente"     # na tira, só a situação
    painel.definir_vista("grade")
    assert painel.lista.isWrapping() and painel.maximumHeight() > ALTURA_TIRA
    painel.definir_vista("lista")
    assert painel.lista.viewMode() == QListView.ListMode
    assert painel.lista.item(0).text().startswith("a.jpg\n")
    with pytest.raises(ValueError):
        painel.definir_vista("mosaico")
    painel.encerrar()


def test_miniaturas_dos_layouts_existem():
    from ui.layouts import LAYOUTS, LAYOUTS_PLANEJADOS
    ids = list(LAYOUTS) + [item[0] for item in LAYOUTS_PLANEJADOS]
    faltando = [i for i in ids if not (RAIZ / "assets" / "layouts" / f"{i}.png").is_file()]
    assert not faltando
