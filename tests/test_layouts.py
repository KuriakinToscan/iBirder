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

from ui.layouts import (LAYOUT_PADRAO, LAYOUTS, PAINEIS_EXTRAS,  # noqa: E402
                        Paineis, obter_layout)


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
    # Ids que saíram na v1.6 levam ao sucessor
    assert obter_layout("guiado").id == "trilha"
    assert obter_layout("mesa").id == "mesa_luz"
    assert obter_layout("quadro").id == "mesa_luz"  # Quadro da sessão saiu depois da v1.6
    assert "guiado" not in LAYOUTS and "mesa" not in LAYOUTS


@pytest.mark.parametrize("layout", LAYOUTS.values(), ids=list(LAYOUTS))
def test_layout_usa_todos_os_paineis(layout):
    paineis = _paineis()
    central = layout.montar(paineis)
    assert set(layout.paineis_extras) <= set(PAINEIS_EXTRAS)
    esperados = [f.name for f in fields(Paineis)
                 if f.name not in PAINEIS_EXTRAS or f.name in layout.paineis_extras]
    faltando = [nome for nome in esperados if not _contem(central, getattr(paineis, nome))]
    assert not faltando, f"{layout.id} não posicionou: {faltando}"
    sobrando = [nome for nome in PAINEIS_EXTRAS
                if nome not in layout.paineis_extras and _contem(central, getattr(paineis, nome))]
    assert not sobrando, f"{layout.id} posicionou painel que não declarou: {sobrando}"


@pytest.mark.parametrize("layout", LAYOUTS.values(), ids=list(LAYOUTS))
def test_trocar_layout_reaproveita_paineis(layout):
    paineis = _paineis()
    paineis.identificacao.setText("Turdus rufiventris")
    primeiro = layout.montar(paineis)
    segundo = obter_layout(LAYOUT_PADRAO).montar(paineis)
    padrao = obter_layout(LAYOUT_PADRAO)
    for f in fields(Paineis):
        if f.name in PAINEIS_EXTRAS and f.name not in padrao.paineis_extras:
            continue
        painel = getattr(paineis, f.name)
        assert _contem(segundo, painel) and not _contem(primeiro, painel)
    primeiro.deleteLater()  # descartar o antigo não leva os painéis junto
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert paineis.identificacao.text() == "Turdus rufiventris"


def test_trilha_segue_a_etapa_e_volta_sem_perder_dados():
    from ui import estado_identificacao as ei
    from ui.layouts import trilha as tr

    paineis = _paineis()
    estado = ei.EstadoIdentificacao()
    central = tr.LayoutTrilha().montar(paineis, estado)
    central.resize(1366, 700)
    central.show()
    controle = central.controle_trilha
    lateral = controle.lateral

    # Sem foto: etapa 1, só ela liberada, Continuar bloqueado e a foto ao lado da fila
    assert controle.pagina == tr.ESCOLHER and not controle.btn_continuar.isEnabled()
    assert not controle.btn_voltar.isVisible()
    assert [b.isEnabled() for b in lateral.botoes] == [True, False, False, False, False]
    assert paineis.foto.isVisibleTo(central) and paineis.fila.isVisibleTo(central)

    # Foto aberta: vai sozinha para Identificar, e a foto acompanha
    estado.foto_aberta("C:/fotos/IMG_4520.JPG")
    assert controle.pagina == tr.IDENTIFICAR and paineis.foto.isVisibleTo(central)
    assert "IMG_4520.JPG" in controle.lbl_sobretitulo.text()
    assert not controle.btn_continuar.isEnabled()

    # Resultado: Conferir, com o nome no título
    estado.identificacao_concluida({"nome_cientifico": "Turdus rufiventris", "status_msg": "ok"})
    assert controle.pagina == tr.CONFERIR
    assert "Turdus rufiventris" in controle.lbl_titulo.text()
    assert paineis.foto.isVisibleTo(central) and paineis.identificacao.isVisibleTo(central)
    assert lateral.botoes[0].text().startswith("✓") and lateral.botoes[1].text().startswith("✓")
    assert lateral.botoes[2].property("situacao") == "atual"

    # Só com Continuar até Gravar; o botão de gravar fica na última página
    controle.btn_continuar.click()
    assert controle.pagina == tr.CONHECER and paineis.descricao.isVisibleTo(central)
    controle.btn_continuar.click()
    assert controle.pagina == tr.GRAVAR and paineis.btn_gravar.isVisibleTo(central)
    assert not controle.btn_continuar.isVisible()

    # Voltar só troca de página
    controle.btn_voltar.click()
    controle.btn_voltar.click()
    assert controle.pagina == tr.CONFERIR and estado.nome_cientifico == "Turdus rufiventris"
    lateral.botoes[4].click()  # passo liberado pela trilha lateral
    assert controle.pagina == tr.GRAVAR

    # Gravada: fica em Gravar e oferece outra foto; depois volta à etapa 1
    estado.gravada()
    assert controle.pagina == tr.GRAVAR and controle.btn_continuar.isEnabled()
    controle.btn_continuar.click()
    assert controle.pagina == tr.ESCOLHER and paineis.foto.isVisibleTo(central)
    central.close()


def test_trilha_inconclusiva_e_nome_digitado():
    from ui import estado_identificacao as ei
    from ui.layouts import trilha as tr

    paineis = _paineis()
    estado = ei.EstadoIdentificacao()
    central = tr.LayoutTrilha().montar(paineis, estado)
    controle = central.controle_trilha
    estado.foto_aberta("ave.jpg")
    estado.identificacao_concluida({"nome_cientifico": "", "status_msg": "Inconclusiva"})
    assert controle.pagina == tr.CONFERIR and "certeza" in controle.lbl_titulo.text()
    assert not controle.btn_continuar.isEnabled()  # falta a pessoa indicar a espécie
    estado.especie_digitada("Pitangus sulphuratus")
    assert controle.pagina == tr.CONFERIR and controle.btn_continuar.isEnabled()
    assert "Você indicou" in controle.lbl_titulo.text()


def test_config_antiga_sem_layout_mantem_painel_completo(tmp_path, monkeypatch):
    import json

    from core import config as cfg

    caminho = tmp_path / "config.json"
    monkeypatch.setattr(cfg, "obter_caminho_config", lambda: caminho)
    assert cfg.carregar_config()["layout"] == "trilha"  # instalação nova
    caminho.write_text(json.dumps({"tema": "clean"}), encoding="utf-8")
    assert cfg.carregar_config()["layout"] == "completo"  # quem atualiza
    caminho.write_text(json.dumps({"layout": "foco"}), encoding="utf-8")
    assert cfg.carregar_config()["layout"] == "foco"
    # Layouts que saíram (v1.6 e, depois dela, o Quadro da sessão)
    caminho.write_text(json.dumps({"layout": "quadro"}), encoding="utf-8")
    assert cfg.carregar_config()["layout"] == "mesa_luz"
    caminho.write_text(json.dumps({"layout": "mesa"}), encoding="utf-8")
    assert cfg.carregar_config()["layout"] == "mesa_luz"
    caminho.write_text(json.dumps({"layout": "guiado"}), encoding="utf-8")
    assert cfg.carregar_config()["layout"] == "trilha"
