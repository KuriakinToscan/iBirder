"""Renomear a foto ao gravar: NomeComum_aaaammdd (PascalCase, sem acentos)."""
from datetime import datetime

import pytest
from PIL import Image

from core import nome_arquivo as na

DATA = datetime(2026, 10, 16, 14, 35, 22)


@pytest.fixture(autouse=True)
def historico_temporario(tmp_path, monkeypatch):
    """O histórico de renomeações dos testes não vai para a pasta de logs real."""
    arquivo = tmp_path / "logs" / "renomeacoes.csv"
    monkeypatch.setattr(na, "arquivo_historico", lambda: arquivo)
    return arquivo


@pytest.mark.parametrize("nome, esperado", [
    ("Sabiá-laranjeira", "SabiaLaranjeira"),
    ("bem-te-vi", "BemTeVi"),
    ("João-de-barro", "JoaoDeBarro"),
    ("Gavião-pombo-pequeno", "GaviaoPomboPequeno"),
    ("  tico tico  ", "TicoTico"),
    ("ANU-BRANCO", "AnuBranco"),
])
def test_pascal_case_sem_acentos(nome, esperado):
    assert na.pascal_case(nome) == esperado


def test_padroes():
    dados = {"nome_comum": "Sabiá-laranjeira", "nome_cientifico": "Turdus rufiventris"}
    assert na.sugerir_nome(dados, DATA) == "SabiaLaranjeira_20261016"
    assert na.sugerir_nome(dados, DATA, "nome_data_hora") == "SabiaLaranjeira_20261016_143522"
    assert na.sugerir_nome(dados, DATA, "cientifico_data") == "TurdusRufiventris_20261016"


def test_sem_data_o_usuario_completa():
    assert na.sugerir_nome({"nome_comum": "Bem-te-vi"}, None) == "BemTeVi_"


@pytest.mark.parametrize("dados", [
    {"nome_comum": "Identificação Inconclusiva", "nome_cientifico": "Identificação Inconclusiva"},
    {"nome_comum": "Não encontrado"},
    {"nome_comum": "", "nome_cientifico": "Aves"},
    {},
])
def test_sem_especie_nao_sugere(dados):
    assert na.sugerir_nome(dados, DATA) is None
    assert na.sugerir_nome(dados, DATA, "cientifico_data") is None


@pytest.mark.parametrize("nome, valido", [
    ("BemTeVi_20261016", True),
    ("", False), ("a/b", False), ("a:b", False), ('a"b', False), ("nome.", False),
    (" nome", False), ("CON", False), ("com1", False), ("x" * 200, False),
])
def test_validar_nome(nome, valido):
    assert (na.validar_nome(nome) is None) == valido


def _jpg(caminho, data=None):
    img = Image.new("RGB", (8, 8))
    exif = Image.Exif()
    if data:
        exif.get_ifd(0x8769)[0x9003] = data
    img.save(caminho, exif=exif)
    return caminho


def test_data_de_captura(tmp_path):
    assert na.data_captura(_jpg(tmp_path / "a.jpg", "2026:10:16 14:35:22")) == DATA
    assert na.data_captura(_jpg(tmp_path / "b.jpg")) is None
    assert na.data_captura(tmp_path / "inexistente.jpg") is None


def test_sequencia_recebe_sufixo(tmp_path):
    (tmp_path / "BemTeVi_20261016.jpg").write_bytes(b"x")
    (tmp_path / "BemTeVi_20261016_2.jpg").write_bytes(b"x")
    foto = _jpg(tmp_path / "IMG_0003.jpg")
    novo, feitos, falhas = na.renomear(foto, "BemTeVi_20261016")
    assert novo.name == "BemTeVi_20261016_3.jpg" and novo.exists() and not foto.exists()
    assert len(feitos) == 1 and not falhas


def test_mesmo_nome_nao_renomeia(tmp_path):
    foto = _jpg(tmp_path / "BemTeVi_20261016.jpg")
    novo, feitos, _ = na.renomear(foto, "BemTeVi_20261016")
    assert novo == foto and not feitos


def test_raw_e_xmp_renomeados_junto(tmp_path):
    foto = _jpg(tmp_path / "IMG_1234.JPG")
    for nome in ("IMG_1234.CR3", "IMG_1234.xmp", "IMG_1234.JPG.xmp", "IMG_12345.CR3", "IMG_1234.txt"):
        (tmp_path / nome).write_bytes(b"x")
    irmaos = na.arquivos_irmaos(foto)
    assert sorted(f.name for f in irmaos) == ["IMG_1234.CR3", "IMG_1234.JPG.xmp", "IMG_1234.xmp"]

    # O sufixo considera os irmãos: um RAW com o nome-alvo já existente força _2
    (tmp_path / "SabiaLaranjeira_20261016.CR3").write_bytes(b"x")
    novo, feitos, falhas = na.renomear(foto, "SabiaLaranjeira_20261016", irmaos)
    assert novo.name == "SabiaLaranjeira_20261016_2.JPG" and not falhas
    nomes = sorted(p.name for p in tmp_path.iterdir())
    assert {"SabiaLaranjeira_20261016_2.CR3", "SabiaLaranjeira_20261016_2.xmp",
            "SabiaLaranjeira_20261016_2.JPG.xmp", "IMG_12345.CR3", "IMG_1234.txt"} <= set(nomes)


def test_historico_registra_renomeacao_e_desfazer(tmp_path, historico_temporario):
    foto = _jpg(tmp_path / "IMG_0042.jpg")
    (tmp_path / "IMG_0042.CR3").write_bytes(b"raw")
    (tmp_path / "IMG_0042.xmp").write_text("<x/>")
    novo, _, _ = na.renomear(foto, "BemTeVi_20261016", na.arquivos_irmaos(foto))
    assert novo.name == "BemTeVi_20261016.jpg"

    volta, feitos = na.desfazer_renomeacao(novo, "IMG_0042.jpg")
    assert volta == foto and foto.exists()
    assert sorted(p.name for p in tmp_path.glob("IMG_0042*")) == ["IMG_0042.CR3", "IMG_0042.jpg", "IMG_0042.xmp"]
    assert not list(tmp_path.glob("BemTeVi*"))

    linhas = historico_temporario.read_text(encoding="utf-8-sig").splitlines()
    assert linhas[0] == "data;acao;pasta;nome_antigo;nome_novo"
    acoes = [l.split(";")[1] for l in linhas[1:]]
    assert acoes == ["renomeado"] * 3 + ["desfeito"] * 3
    assert any(l.endswith(";IMG_0042.CR3;BemTeVi_20261016.CR3") for l in linhas)


def test_desfazer_nunca_sobrescreve(tmp_path):
    foto = _jpg(tmp_path / "BemTeVi_20261016.jpg")
    (tmp_path / "IMG_0042.jpg").write_bytes(b"outra foto")
    with pytest.raises(FileExistsError):
        na.desfazer_renomeacao(foto, "IMG_0042.jpg")
    assert foto.exists() and (tmp_path / "IMG_0042.jpg").read_bytes() == b"outra foto"


def test_desfazer_sem_mudanca(tmp_path):
    foto = _jpg(tmp_path / "IMG_0042.jpg")
    assert na.desfazer_renomeacao(foto, "IMG_0042.jpg") == (foto, [])
