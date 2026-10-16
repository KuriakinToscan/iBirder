"""Testes offline da geração de comandos do ExifTool."""
from modules.step6_persistence.exif_manager import EXIFManager

DADOS = {"nome_cientifico": "Pitangus sulphuratus", "nome_comum": "Bem-te-vi", "lat": -23.55, "lon": -46.63}


def test_gps_grava_hemisferio_sul_oeste():
    cmds = EXIFManager()._gerar_comandos(DADOS, {"coord_gps": True})
    assert "-GPSLatitude=23.55" in cmds and "-GPSLatitudeRef=S" in cmds
    assert "-GPSLongitude=46.63" in cmds and "-GPSLongitudeRef=W" in cmds


def test_gps_preservado_quando_ja_existe():
    cmds = EXIFManager()._gerar_comandos(DADOS, {"coord_gps": True}, gps_existente=True)
    assert not any(c.startswith("-GPS") for c in cmds)


def test_palavras_chave_sao_idempotentes():
    cmds = EXIFManager()._gerar_comandos(DADOS, {})
    for kw in ("iBirder", "Bem-te-vi"):
        assert cmds.index(f"-Keywords-={kw}") < cmds.index(f"-Keywords+={kw}")


def test_darwin_core_usa_tags_da_estrutura_taxon():
    cmds = EXIFManager()._gerar_comandos({**DADOS, "familia": "Tyrannidae", "ordem": "Passeriformes", "classe": "Aves"}, {})
    for tag, valor in [("TaxonScientificName", "Pitangus sulphuratus"), ("TaxonGenus", "Pitangus"),
                       ("TaxonFamily", "Tyrannidae"), ("TaxonOrder", "Passeriformes"),
                       ("TaxonClass", "Aves"), ("TaxonVernacularName", "Bem-te-vi")]:
        assert f"-XMP-dwc:{tag}={valor}" in cmds
    assert not any(c.startswith("-XMP-dwc:ScientificName") for c in cmds)
