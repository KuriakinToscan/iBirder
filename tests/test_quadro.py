"""Quadro da sessão (v1.6): colunas da fila, resumo de espécies, pastas recentes e gaveta."""
import os
from pathlib import Path

import pytest

from core import fila_fotos as ff

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _fila():
    fila = ff.FilaFotos(caminhos=[f"/f/IMG_{i}.jpg" for i in range(6)])
    fila.marcar(0, ff.JA_GRAVADA, especie="Pitangus sulphuratus")
    fila.marcar(1, ff.GRAVADA, especie="Paroaria coronata")
    fila.marcar(2, ff.GRAVADA, especie="Pitangus sulphuratus sulphuratus")
    fila.marcar(3, ff.PULADA)
    fila.atual = 4
    return fila


def test_colunas_e_resumo():
    fila = _fila()
    assert ff.colunas(fila) == {ff.NA_FILA: [5], ff.CONFERINDO: [4], ff.GRAVADAS: [0, 1, 2], ff.PULADAS: [3]}
    # A gravada que está aberta fica em Gravadas; a pulada reaberta fica em Conferindo
    fila.atual = 1
    assert ff.coluna_do_item(fila, 1) == ff.GRAVADAS
    fila.atual = 3
    assert ff.coluna_do_item(fila, 3) == ff.CONFERINDO
    assert ff.especies_gravadas(fila) == ["Paroaria coronata", "Pitangus sulphuratus"]
    assert ff.resumo_sessao(fila) == "2 espécies · 3 gravadas de 6"
    assert ff.resumo_sessao(ff.FilaFotos(caminhos=[])) == "Nenhuma foto na pasta"


def test_pastas_recentes():
    assert ff.atualizar_recentes(None, "/a") == [str(Path("/a"))]
    recentes = ff.atualizar_recentes([str(Path(f"/p{i}")) for i in range(6)], "/p3", limite=4)
    assert recentes == [str(Path(p)) for p in ("/p3", "/p0", "/p1", "/p2")]


def test_fila_em_colunas_e_gaveta(tmp_path):
    pytest.importorskip("PySide6.QtWidgets")
    from PIL import Image
    from PySide6.QtWidgets import QApplication
    from test_layouts import _paineis

    from ui import estado_identificacao as ei
    from ui.layouts import quadro as lq
    from ui.widgets.painel_fila import PainelFila

    QApplication.instance() or QApplication([])
    for nome in ("a.jpg", "b.jpg", "c.jpg"):
        Image.new("RGB", (40, 30), "white").save(tmp_path / nome)

    estado = ei.EstadoIdentificacao()
    paineis = _paineis()
    paineis.fila = PainelFila(estado)
    paineis.fila.abrir_foto.connect(estado.foto_aberta)
    central = lq.LayoutQuadro().montar(paineis, estado)
    central.resize(1366, 740)
    central.show()
    controle = central.controle_quadro
    gaveta = controle.gaveta
    assert paineis.fila.vista == "colunas" and not gaveta.esta_aberta()

    paineis.fila.carregar_pasta(tmp_path)
    paineis.fila._parar_verificacao()
    paineis.fila._abrir(0)
    QApplication.processEvents()
    assert gaveta.esta_aberta() and controle.abas.currentIndex() == lq.ABA_CONFERIR
    assert "a.jpg" in controle.lbl_arquivo.text()
    colunas = paineis.fila.colunas_quadro
    assert colunas[ff.CONFERINDO].count() == 1 and colunas[ff.NA_FILA].count() == 2

    estado.identificacao_concluida({"nome_cientifico": "Turdus rufiventris", "status_msg": "ok"})
    QApplication.processEvents()
    assert "Turdus rufiventris?" in colunas[ff.CONFERINDO].item(0).text()
    estado.confirmar()
    assert controle.abas.currentIndex() == lq.ABA_FICHA

    # Fechar não fecha a foto; clicar duas vezes no cartão dela reabre, sem abrir de novo
    gaveta.fechar()
    abertas = []
    paineis.fila.abrir_foto.connect(abertas.append)
    paineis.fila._ao_ativar_item_quadro(colunas[ff.CONFERINDO].item(0))
    assert gaveta.esta_aberta() and abertas == []

    paineis.fila.cb_avancar.setChecked(False)
    estado.gravada(str(tmp_path / "a.jpg"))
    QApplication.processEvents()
    assert colunas[ff.GRAVADAS].count() == 1 and colunas[ff.CONFERINDO].count() == 0
    assert "1 espécie" in paineis.fila.lbl_resumo.text()

    estado.limpar()
    assert not gaveta.esta_aberta()
    central.close()
    paineis.fila.encerrar()
