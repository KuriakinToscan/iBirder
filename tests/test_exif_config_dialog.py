"""Diálogo de gravação: seleção dos campos (linhas destacadas, marcar/desmarcar todos) e ✓ do indicador."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

DADOS = {
    "nome_cientifico": "Sicalis flaveola", "nome_comum": "Canário-da-terra", "nome_ingles": "Saffron Finch",
    "classe": "Aves", "ordem": "Passeriformes", "familia": "Thraupidae",
    "iucn_status": "Pouco Preocupante (LC)", "pais": "Brasil", "estado": "Rio Grande do Sul",
    "latitude": -31.7, "longitude": -52.3,
}


@pytest.fixture
def dialogo():
    QApplication.instance() or QApplication([])
    from ui.dialogs.exif_config_dialog import ExifConfigDialog
    dlg = ExifConfigDialog(None, dict(DADOS))
    yield dlg
    dlg.deleteLater()


def test_campos_sem_dado_ficam_desmarcados_e_desabilitados(dialogo):
    assert dialogo.checkboxes["genero"].isChecked()  # vem do nome científico
    assert dialogo.linhas["genero"].lbl_valor.text() == "Sicalis"
    for chave in ("status_icmbio", "status_cites", "municipio", "bioma", "endemismo"):
        assert not dialogo.checkboxes[chave].isEnabled()
        assert not dialogo.checkboxes[chave].isChecked()
    assert dialogo.checkboxes["coord_gps"].isChecked()
    assert dialogo.lbl_contador.text() == "11 de 11 campos serão gravados"
    assert not dialogo.btn_marcar_todos.isEnabled()


def test_gps_original_protegido():
    QApplication.instance() or QApplication([])
    from ui.dialogs.exif_config_dialog import ExifConfigDialog
    dlg = ExifConfigDialog(None, dict(DADOS), tem_gps_nativo=True)
    assert not dlg.checkboxes["coord_gps"].isEnabled()
    assert "Protegido" in dlg.linhas["coord_gps"].lbl_valor.text()


def test_marcar_e_desmarcar_todos(dialogo):
    dialogo._marcar_todos(False)
    assert not any(cb.isChecked() for cb in dialogo.checkboxes.values())
    assert dialogo.lbl_contador.text() == "Nenhum campo será gravado"
    assert not dialogo.btn_desmarcar_todos.isEnabled()
    dialogo._marcar_todos(True)
    assert not dialogo.checkboxes["bioma"].isChecked()  # sem dado continua de fora
    dialogo._confirmar_gravacao()
    selecionados = dialogo.get_selected_fields()
    assert selecionados["nome_comum"] and not selecionados["bioma"]


def test_linha_marcada_fica_destacada_e_clique_na_linha_alterna(dialogo):
    linha = dialogo.linhas["nome_ingles"]
    assert linha.property("marcada") is True
    QTest.mouseClick(linha, Qt.LeftButton, pos=QPoint(linha.width() - 5, 5))
    assert not dialogo.checkboxes["nome_ingles"].isChecked()
    assert linha.property("marcada") is False
    assert dialogo.lbl_contador.text() == "10 de 11 campos serão gravados"
    # Linha desabilitada não reage ao clique
    QTest.mouseClick(dialogo.linhas["bioma"], Qt.LeftButton, pos=QPoint(5, 5))
    assert not dialogo.checkboxes["bioma"].isChecked()


@pytest.mark.parametrize("tema", __import__("core.temas", fromlist=["x"]).COMBINACOES,
                         ids=lambda t: f"{t.id}-{t.modo}")
def test_indicador_marcado_tem_o_check_desenhado(tema):
    """Caixa marcada = fundo de destaque + ✓ em texto_destaque (contraste já exigido em test_temas)."""
    from core.style_manager import QSS_GLOBAL, caminho_indicador
    from core.temas import renderizar
    assert "image: url(ibirder-img:check)" in QSS_GLOBAL
    caminho = caminho_indicador("check", tema)
    with open(caminho, encoding="utf-8") as f:
        assert tema["texto_destaque"] in f.read()
    assert "ibirder-img:" in renderizar(QSS_GLOBAL, tema)  # só o StyleManager troca as imagens


def test_render_troca_as_imagens_pelo_arquivo():
    from core.style_manager import StyleManager
    saida = StyleManager.render("image: url(ibirder-img:check); x: url(ibirder-img:ponto_desativado);")
    assert "ibirder-img:" not in saida
    assert saida.count(".svg\"") == 2
