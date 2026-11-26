"""Card da foto: fotos grandes (acima do limite de 256 MB do Qt) aparecem reduzidas, não em branco."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from PIL import Image  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def test_foto_acima_do_limite_do_qt_aparece_reduzida(tmp_path):
    from ui.custom_widgets import ImageCardWidget, LADO_MAXIMO_PIXMAP
    caminho = tmp_path / "IMG_grande.JPG"
    Image.new("RGB", (9000, 8000), (200, 120, 40)).save(caminho, quality=70)  # 72 MP: Qt recusa inteira
    card = ImageCardWidget()
    card.set_image_path(str(caminho))
    assert card.pixmap is not None and not card.pixmap.isNull()
    assert max(card.pixmap.width(), card.pixmap.height()) == LADO_MAXIMO_PIXMAP
    assert card.pixmap.width() > card.pixmap.height()


def test_foto_pequena_fica_no_tamanho_original(tmp_path):
    from ui.custom_widgets import carregar_pixmap
    caminho = tmp_path / "pequena.jpg"
    Image.new("RGB", (640, 480)).save(caminho)
    pixmap = carregar_pixmap(caminho)
    assert (pixmap.width(), pixmap.height()) == (640, 480)


def test_cai_no_pillow_quando_o_qt_falha(tmp_path, monkeypatch):
    from PySide6.QtGui import QImage, QImageReader
    from ui import custom_widgets
    caminho = tmp_path / "foto.jpg"
    Image.new("RGB", (300, 200)).save(caminho)
    monkeypatch.setattr(QImageReader, "read", lambda self: QImage())
    pixmap = custom_widgets.carregar_pixmap(caminho)
    assert (pixmap.width(), pixmap.height()) == (300, 200)
