"""Detecção de foto já processada e substituição do registro ao reprocessar."""
from datetime import datetime

import pytest
from PIL import Image

from modules.step6_persistence import registro_ibirder as reg
from modules.step6_persistence.exif_manager import EXIFManager


def _xmp(tags):
    itens = "".join(f"<rdf:li>{t}</rdf:li>" for t in tags)
    return (f'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            f'<rdf:Description xmlns:lr="http://ns.adobe.com/lightroom/1.0/"><lr:hierarchicalSubject><rdf:Bag>'
            f'{itens}</rdf:Bag></lr:hierarchicalSubject></rdf:Description></rdf:RDF></x:xmpmeta>').encode("utf-8")


@pytest.fixture
def foto(tmp_path):
    def criar(tags=None):
        caminho = tmp_path / "foto.jpg"
        img = Image.new("RGB", (16, 16), "green")
        if tags is None:
            img.save(caminho)
        else:
            img.save(caminho, xmp=_xmp(tags))
        return caminho
    return criar


def test_foto_nunca_processada(foto):
    assert reg.ler_registro(foto()) is None
    assert reg.ler_registro(foto(["Pessoal|Viagem|2026"])) is None


def test_registro_v13_com_data_e_versao(foto):
    r = reg.ler_registro(foto(["iBirder|Taxonomia|ScientificName|Pitangus sulphuratus",
                               "iBirder|Geografia|Biome|Mata Atlântica",
                               "iBirder|Conservacao|Brasil|Vulnerável",
                               "iBirder|Registro|Data|2026-10-16 13:05",
                               "iBirder|Registro|Versao|1.3"]))
    assert r["data"] == datetime(2026, 10, 16, 13, 5) and r["versao"] == "1.3"
    assert reg.descrever_quando(r) == "16/10/2026 às 13:05 (iBirder v1.3)"
    grupos = dict(reg.resumo_legivel(r))
    assert ("Nome científico", "Pitangus sulphuratus") in grupos["Espécie"]
    assert ("Bioma", "Mata Atlântica") in grupos["Local"]
    assert ("Lista nacional (MMA)", "Vulnerável") in grupos["Conservação"]


def test_registro_antigo_sem_data(foto):
    r = reg.ler_registro(foto(["iBirder|Taxonomia|ScientificName|Pitangus sulphuratus"]))
    assert r["data"] is None
    assert reg.descrever_quando(r).startswith("data não registrada (gravado por versão anterior à 1.3)")


def test_reprocessar_remove_registro_anterior_e_grava_data():
    anterior = {"tags": ["iBirder|Geografia|Endemism|Não endêmico do Brasil", "iBirder|Registro|Data|2026-01-01 10:00"],
                "dados": {("Geografia", "Endemism"): "Não endêmico do Brasil"}}
    cmds = EXIFManager()._gerar_comandos({"nome_cientifico": "Aratinga auricapillus", "endemismo": "Sim"}, {},
                                         registro_anterior=anterior, agora=datetime(2026, 10, 16, 13, 5))
    assert "-XMP-lr:HierarchicalSubject-=iBirder|Geografia|Endemism|Não endêmico do Brasil" in cmds
    assert "-Keywords-=Não endêmico do Brasil" in cmds
    assert "-XMP-lr:HierarchicalSubject+=iBirder|Geografia|Endemism|Endêmico do Brasil" in cmds
    assert "-XMP-lr:HierarchicalSubject+=iBirder|Registro|Data|2026-10-16 13:05" in cmds
    assert any(c.startswith("-UserComment=") and "em 16/10/2026 13:05" in c for c in cmds)


def test_nome_original_gravado_so_na_primeira_vez():
    from modules.step6_persistence.exif_manager import EXIFManager
    from modules.step6_persistence.registro_ibirder import nome_preservado
    cmds = EXIFManager()._gerar_comandos({"nome_cientifico": "Pitangus sulphuratus"}, {}, nome_original="IMG_0001.JPG")
    assert "-XMP-xmpMM:PreservedFileName=IMG_0001.JPG" in cmds
    cmds = EXIFManager()._gerar_comandos({"nome_cientifico": "Pitangus sulphuratus"}, {})
    assert not any("PreservedFileName" in c for c in cmds)
    assert nome_preservado('<rdf:Description xmpMM:PreservedFileName="IMG_0001.JPG"/>') == "IMG_0001.JPG"
    assert nome_preservado("<xmpMM:PreservedFileName>DSC_9.NEF</xmpMM:PreservedFileName>") == "DSC_9.NEF"
    assert nome_preservado("") is None
