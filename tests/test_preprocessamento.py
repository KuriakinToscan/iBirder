"""Redução da foto para a identificação: proporção preservada, sem recorte (preprocessamento.py)."""
import io

import pytest
from PIL import Image

from modules.step1_identity import preprocessamento as pp


def _salvar(tmp_path, nome, tamanho, formato="JPEG", orientacao=None):
    img = Image.new("RGB", tamanho, (30, 120, 60))
    caminho = tmp_path / nome
    kwargs = {}
    if orientacao:
        exif = Image.Exif()
        exif[0x0112] = orientacao
        kwargs["exif"] = exif.tobytes()
    img.save(caminho, format=formato, **kwargs)
    return caminho


def test_jpeg_grande_abre_reduzido_com_a_mesma_proporcao(tmp_path):
    caminho = _salvar(tmp_path, "grande.jpg", (6000, 4000))
    img = pp.abrir_reduzida(caminho)
    assert pp.LADO_MIN_ABERTURA <= max(img.size) < 6000
    assert img.width / img.height == pytest.approx(1.5, rel=0.01)
    assert img.mode == "RGB"


def test_orientacao_exif_e_aplicada(tmp_path):
    # Orientation 6 = girar 90°: a foto deitada no arquivo fica em pé
    caminho = _salvar(tmp_path, "vertical.jpg", (6000, 4000), orientacao=6)
    img = pp.abrir_reduzida(caminho)
    assert img.height > img.width
    assert img.height / img.width == pytest.approx(1.5, rel=0.01)


def test_foto_pequena_nao_e_ampliada(tmp_path):
    caminho = _salvar(tmp_path, "pequena.jpg", (640, 480))
    assert pp.abrir_reduzida(caminho).size == (640, 480)


def test_png_grande_e_reduzido_sem_deformar(tmp_path):
    caminho = _salvar(tmp_path, "grande.png", (5000, 2500), formato="PNG")
    img = pp.abrir_reduzida(caminho)
    assert pp.LADO_MIN_ABERTURA <= max(img.size) <= 2 * pp.LADO_MIN_ABERTURA
    assert img.width / img.height == pytest.approx(2.0, rel=0.01)


def test_letterbox_preserva_proporcao_e_completa_com_borda():
    img = Image.new("RGB", (1500, 1000), (255, 0, 0))
    quadro = pp.letterbox(img, 224, 224)
    assert quadro.size == (224, 224)
    # 3:2 -> 224x149 centralizado: faixas de borda em cima e embaixo
    assert quadro.getpixel((112, 0)) == pp.COR_BORDA
    assert quadro.getpixel((112, 223)) == pp.COR_BORDA
    assert quadro.getpixel((0, 112)) == (255, 0, 0)
    assert quadro.getpixel((223, 112)) == (255, 0, 0)
    altura_util = sum(1 for y in range(224) if quadro.getpixel((112, y)) != pp.COR_BORDA)
    assert altura_util == pytest.approx(149, abs=1)


def test_letterbox_tamanho_invalido():
    with pytest.raises(ValueError):
        pp.letterbox(Image.new("RGB", (10, 10)), 0, 224)


def test_preparar_para_modelo_entrega_o_tamanho_da_entrada(tmp_path):
    caminho = _salvar(tmp_path, "foto.jpg", (4000, 6000))
    assert pp.preparar_para_modelo(caminho, 224, 224).size == (224, 224)


def test_copia_para_nuvem_limitada_e_proporcional(tmp_path):
    caminho = _salvar(tmp_path, "nuvem.jpg", (6000, 4000))
    dados = pp.jpeg_para_nuvem(caminho)
    with Image.open(io.BytesIO(dados)) as img:
        assert img.format == "JPEG"
        assert max(img.size) == pp.LADO_NUVEM
        assert img.width / img.height == pytest.approx(1.5, rel=0.01)
