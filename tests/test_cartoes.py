"""
Cartões de escolha (v1.6): candidatas da identificação, foto de referência com cache em
disco (sem rede: iNaturalist falso), painel de cartões e layout. Sem QtWebEngine.
"""
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QApplication  # noqa: E402

from core import fotos_referencia as fr  # noqa: E402
from ui import estado_identificacao as ei  # noqa: E402

DADOS = {
    "nome_cientifico": "Turdus rufiventris",
    "confianca": 0.87,
    "status_msg": "ok",
    "top3": [
        {"nome_cientifico": "Turdus rufiventris rufiventris", "confianca": 0.80},
        {"nome_cientifico": "Turdus leucomelas", "confianca": 0.08},
        {"label": "Turdus amaurochalinus", "confianca": 0.03},
        {"nome_cientifico": "Turdus albicollis", "confianca": 0.01},
    ],
}


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_candidatas_sem_repetir_e_escolhida_primeiro():
    lista = ei.candidatas_da_identificacao(DADOS, "Turdus rufiventris")
    assert [n for n, _ in lista] == ["Turdus rufiventris", "Turdus leucomelas", "Turdus amaurochalinus"]
    assert lista[0][1] == pytest.approx(0.87)
    # Inconclusiva: só as sugestões da IA
    assert ei.candidatas_da_identificacao({"top3": DADOS["top3"]})[0][0] == "Turdus rufiventris rufiventris"
    assert ei.candidatas_da_identificacao({}) == []


def test_estado_confirma_e_busca_manual_mantem_candidatas(app):
    estado = ei.EstadoIdentificacao()
    confirmadas = []
    estado.especie_confirmada.connect(confirmadas.append)
    estado.confirmar()  # sem espécie: nada
    estado.foto_aberta("ave.jpg")
    estado.identificacao_concluida(DADOS)
    assert len(estado.candidatas) == 3 and not estado.confirmada
    estado.confirmar()
    assert estado.confirmada and confirmadas == ["Turdus rufiventris"]
    estado.limpar(manter_foto=True)  # a busca manual começa assim
    estado.especie_digitada("Turdus leucomelas")
    assert len(estado.candidatas) == 3 and estado.manual and not estado.confirmada
    estado.foto_aberta("outra.jpg")
    assert estado.candidatas == [] and not estado.confirmada


def _inat_falso(monkeypatch, chamadas):
    foto = {"medium_url": "https://exemplo/medium.jpg", "license_code": "cc-by-nc",
            "attribution": "(c) Fulana, some rights reserved (CC BY-NC), uploaded by Beltrano"}
    taxon = SimpleNamespace(found=True, default_photo=foto, nome_comum_pt="Sabiá-laranjeira",
                            url="https://www.inaturalist.org/taxa/12345")

    def get_taxon(nome):
        chamadas.append(("taxon", nome))
        return taxon

    def get(url, timeout=10):
        chamadas.append(("foto", url))
        return SimpleNamespace(content=b"\xff\xd8jpeg", raise_for_status=lambda: None)

    monkeypatch.setattr(fr, "get_taxon", get_taxon)
    monkeypatch.setattr(fr.http, "get", get)


def test_foto_de_referencia_com_cache(tmp_path, monkeypatch):
    chamadas = []
    _inat_falso(monkeypatch, chamadas)
    foto = fr.obter_foto("Turdus rufiventris", pasta=tmp_path)
    assert foto is not None and foto.licenca == "CC BY-NC" and foto.credito == "(c) Fulana"
    assert foto.nome_comum == "Sabiá-laranjeira" and foto.texto_credito == "(c) Fulana, CC BY-NC"
    assert (tmp_path / "turdus_rufiventris.jpg").read_bytes() == b"\xff\xd8jpeg"
    # Segunda vez: só o cache, sem rede
    chamadas.clear()
    de_novo = fr.obter_foto("Turdus rufiventris", pasta=tmp_path)
    assert chamadas == [] and de_novo == foto


def test_foto_de_referencia_sem_rede(tmp_path, monkeypatch):
    def falha(nome):
        raise OSError("sem rede")

    monkeypatch.setattr(fr, "get_taxon", falha)
    assert fr.obter_foto("Turdus rufiventris", pasta=tmp_path) is None
    monkeypatch.setattr(fr, "get_taxon", lambda nome: SimpleNamespace(found=False, default_photo=None))
    assert fr.obter_foto("Ave inexistente", pasta=tmp_path) is None


def test_painel_cartoes_segue_o_estado(app):
    from ui.widgets.cartao_candidata import PainelCartoes

    estado = ei.EstadoIdentificacao()
    painel = PainelCartoes(estado, baixar_fotos=False)
    escolhidas = []
    painel.escolhida.connect(escolhidas.append)
    assert painel.cartoes == []
    estado.foto_aberta("ave.jpg")
    assert "Identificando" in painel.lbl_aviso.text()
    estado.identificacao_concluida(DADOS)
    assert [c.nome for c in painel.cartoes] == ["Turdus rufiventris", "Turdus leucomelas", "Turdus amaurochalinus"]
    assert painel.cartoes[0].principal and "Turdidae" in painel.cartoes[0].familia
    painel.cartoes[1].btn_esta.click()
    assert escolhidas == ["Turdus leucomelas"]

    # Busca manual na mesma foto: os cartões continuam
    estado.limpar(manter_foto=True)
    estado.especie_digitada("Turdus leucomelas")
    assert len(painel.cartoes) == 3
    assert painel.cartoes[1].property("escolhida") == "true"

    painel.definir_orientacao("vertical")
    assert len(painel.cartoes) == 3 and painel.cartoes[0].orientacao == "vertical"
    with pytest.raises(ValueError):
        painel.definir_orientacao("diagonal")
    estado.limpar()
    assert painel.cartoes == []


def test_cartao_mostra_foto_e_credito(app, tmp_path):
    from PIL import Image

    from ui.widgets.cartao_candidata import CartaoCandidata

    caminho = tmp_path / "ref.jpg"
    Image.new("RGB", (60, 40), "white").save(caminho)
    cartao = CartaoCandidata("Turdus rufiventris", 0.5)
    cartao.resize(240, 400)
    cartao.definir_foto(fr.FotoReferencia("Turdus rufiventris", str(caminho), "(c) Fulana", "CC BY",
                                          nome_comum="Sabiá-laranjeira"))
    assert cartao.lbl_comum.text() == "Sabiá-laranjeira"
    assert "(c) Fulana, CC BY" in cartao.lbl_credito.text() and "(c) Fulana" in cartao.toolTip()
    cartao.definir_foto(None)  # sem rede: continua de pé


def test_layout_cartoes_troca_de_pagina(app):
    from test_layouts import _paineis

    from ui.layouts import cartoes as lc

    paineis = _paineis()
    estado = ei.EstadoIdentificacao()
    central = lc.LayoutCartoes().montar(paineis, estado)
    central.resize(1366, 740)
    central.show()
    controle = central.controle_cartoes
    assert controle.pagina == lc.FOTO and paineis.foto.isVisibleTo(central)

    estado.foto_aberta("ave.jpg")
    assert controle.pagina == lc.ESCOLHER and paineis.foto.isVisibleTo(central)
    estado.identificacao_concluida(DADOS)
    assert controle.pagina == lc.ESCOLHER and paineis.cartoes.isVisibleTo(central)
    assert [r.text() for r in controle.barra.rotulos][0].startswith("✓")

    estado.confirmar()
    assert controle.pagina == lc.FICHA and paineis.btn_gravar.isVisibleTo(central)
    assert "Turdus rufiventris" in controle.lbl_titulo_ficha.text()
    controle.ir_para(lc.ESCOLHER)  # "Trocar espécie"
    assert controle.pagina == lc.ESCOLHER and estado.nome_cientifico == "Turdus rufiventris"

    # Nome digitado é escolha da pessoa: abre a ficha
    estado.limpar(manter_foto=True)
    estado.especie_digitada("Turdus leucomelas")
    assert controle.pagina == lc.FICHA
    estado.gravada()
    assert controle.pagina == lc.FICHA
    assert all(r.text().startswith("✓") for r in controle.barra.rotulos)
    central.close()
