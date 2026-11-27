"""
Diagramação dos layouts (revisão de 27/11/2026): texto que acompanha a largura, fotos que
cabem na coluna, nada flutuando por cima da foto e painéis que não saem da janela.
Sem QtWebEngine: os painéis aqui são widgets simples (ImageCardWidget de verdade nas fotos).
"""
import os
from dataclasses import fields

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QPoint, QRect  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QWidget  # noqa: E402

from ui.layouts import LAYOUTS, Paineis  # noqa: E402

TAMANHOS = ((1920, 1020), (1366, 705), (1000, 680))
TEXTO_LONGO = ("Apresenta plumagem ferrugínea nas partes superiores, peito acinzentado, ventre escuro, "
               "cauda longa, escura e com as pontas das retrizes claras, bico amarelo e íris vermelha. ") * 2


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def _paineis():
    from ui.custom_widgets import ImageCardWidget
    paineis = Paineis(**{f.name: QLabel(f.name) for f in fields(Paineis)})
    paineis.foto = ImageCardWidget()
    paineis.referencia = ImageCardWidget()
    for nome in ("btn_lens", "btn_fonte", "btn_nova", "btn_gravar", "btn_publicar"):
        setattr(paineis, nome, QPushButton(nome))
    return paineis


def _retangulo_na_raiz(widget, raiz):
    return QRect(widget.mapTo(raiz, QPoint(0, 0)), widget.size())


def test_texto_auto_altura_acompanha_a_largura(app):
    from ui.widgets.componentes_layout import TextoAutoAltura
    caixa = TextoAutoAltura()
    caixa.setPlainText(TEXTO_LONGO)
    caixa.resize(900, 50)
    caixa.show()
    QApplication.processEvents()
    larga = caixa.height()
    # O painel estreita DEPOIS de o texto chegar (página da Trilha, gaveta, troca de layout)
    caixa.resize(300, caixa.height())
    QApplication.processEvents()
    assert caixa.height() > larga
    documento = caixa.document()
    assert documento.size().height() <= caixa.viewport().height() + 1  # nada cortado
    caixa.close()


def test_coluna_fotos_cabe_na_altura(app):
    from ui.custom_widgets import ImageCardWidget
    from ui.widgets.componentes_layout import ColunaFotos
    cards = [ImageCardWidget(), ImageCardWidget()]
    botoes = QPushButton("Pesquisar com Google Lens")
    coluna = ColunaFotos(cards, botoes)
    coluna.resize(320, 520)
    coluna.show()
    QApplication.processEvents()
    for card in cards:
        assert card.width() == card.height() == coluna.lado()
        assert card.geometry().bottom() <= coluna.height()
    assert botoes.geometry().bottom() <= coluna.height()
    assert botoes.width() == coluna.width()
    coluna.close()


def test_fotos_lado_a_lado_empilham_em_janela_estreita(app):
    from ui.widgets.componentes_layout import FotosLadoALado
    medidor = QWidget()
    fotos = FotosLadoALado(medidor, desconto=400)
    medidor.resize(1400, 500)
    medidor.show()
    QApplication.processEvents()
    assert fotos.lado_a_lado()
    medidor.resize(800, 500)
    QApplication.processEvents()
    assert not fotos.lado_a_lado()
    medidor.close()


def test_gaveta_proporcional(app):
    from ui.widgets.componentes_layout import Gaveta
    hosp = QWidget()
    hosp.resize(2000, 600)
    gaveta = Gaveta(hosp, largura=640, animar=False, proporcao=0.45)
    assert gaveta.largura_atual() == 900
    hosp.resize(1000, 600)
    assert gaveta.largura_atual() == 640
    hosp.resize(500, 600)
    assert gaveta.largura_atual() == 500


@pytest.mark.parametrize("largura,altura", TAMANHOS)
def test_mesa_de_luz_referencia_nao_cobre_a_foto(app, largura, altura):
    paineis = _paineis()
    raiz = LAYOUTS["mesa_luz"].montar(paineis)
    raiz.resize(largura, altura)
    raiz.show()
    QApplication.processEvents()
    foto = _retangulo_na_raiz(paineis.foto, raiz)
    for nome in ("referencia", "btn_fonte", "btn_lens"):
        outro = _retangulo_na_raiz(getattr(paineis, nome), raiz)
        assert not foto.intersects(outro), f"{nome} por cima da foto em {largura}x{altura}"
    assert foto.right() <= raiz.width()
    raiz.close()


@pytest.mark.parametrize("largura,altura", TAMANHOS)
def test_foco_resultado_nao_cobre_a_foto(app, largura, altura):
    from ui import estado_identificacao as ei
    estado = ei.EstadoIdentificacao()
    paineis = _paineis()
    raiz = LAYOUTS["foco"].montar(paineis, estado)
    raiz.resize(largura, altura)
    raiz.show()
    estado.foto_aberta("x.jpg")  # com foto, o resultado aparece
    QApplication.processEvents()
    controle = raiz.controle_foco
    palco = _retangulo_na_raiz(controle.palco, raiz)
    pilula = _retangulo_na_raiz(controle.pilula, raiz)
    assert controle.pilula.isVisible()
    assert not palco.intersects(pilula)
    assert pilula.right() <= raiz.width()
    raiz.close()


@pytest.mark.parametrize("largura,altura", TAMANHOS)
def test_ficha_compacta_fotos_e_botoes_visiveis(app, largura, altura):
    paineis = _paineis()
    raiz = LAYOUTS["ficha"].montar(paineis)
    raiz.resize(largura, altura)
    raiz.show()
    QApplication.processEvents()
    for nome in ("foto", "referencia", "btn_lens", "btn_fonte"):
        widget = getattr(paineis, nome)
        ret = _retangulo_na_raiz(widget, raiz)
        assert ret.bottom() <= raiz.height() and ret.right() <= raiz.width(), \
            f"{nome} fora da janela em {largura}x{altura}"
    raiz.close()


@pytest.mark.parametrize("id_layout", ["completo", "ficha", "mesa_luz", "foco", "cartoes", "trilha"])
def test_paineis_dentro_da_largura_em_1000px(app, id_layout):
    """Nenhum painel passa da borda direita (cortado sem rolagem horizontal) em 1000 px."""
    from ui import estado_identificacao as ei
    estado = ei.EstadoIdentificacao()
    paineis = _paineis()
    raiz = LAYOUTS[id_layout].montar(paineis, estado)
    raiz.resize(1000, 680)
    raiz.show()
    QApplication.processEvents()
    for f in fields(Paineis):
        widget = getattr(paineis, f.name)
        if widget is None or not widget.isVisible() or widget.window() is not raiz:
            continue
        ret = _retangulo_na_raiz(widget, raiz)
        assert ret.right() <= raiz.width() + 1, f"{id_layout}: {f.name} passa da borda ({ret.right()})"
    raiz.close()
