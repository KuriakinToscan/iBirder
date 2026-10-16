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


def test_respeita_campos_desmarcados_no_dialogo():
    dados = {**DADOS, "familia": "Tyrannidae", "bioma": "Mata Atlântica", "nome_ingles": "Great Kiskadee"}
    cmds = EXIFManager()._gerar_comandos(dados, {"familia": False, "bioma": False, "nome_ingles": False})
    texto = "\n".join(cmds)
    assert "Tyrannidae" not in texto and "Mata Atlântica" not in texto and "Great Kiskadee" not in texto
    assert "-XMP-dwc:TaxonScientificName=Pitangus sulphuratus" in cmds


def test_valores_desconhecidos_nao_sao_gravados():
    dados = {**DADOS, "endemismo": "Não informado", "status_icmbio": "Não disponível", "bioma": "Não identificado",
             "nome_comum": None}
    texto = "\n".join(EXIFManager()._gerar_comandos(dados, {}))
    assert "endêmico" not in texto.lower()          # antes: desconhecido virava "Não endêmico do Brasil"
    assert "ICMBio" not in texto and "Não identificado" not in texto
    assert "=Ave" not in texto and "Ave (" not in texto  # antes: nome comum ausente virava "Ave"


def test_endemismo_e_status_conhecidos_sao_gravados():
    dados = {**DADOS, "endemismo": "Sim", "status_icmbio": "Vulnerável", "status_cites": "Anexo II"}
    texto = "\n".join(EXIFManager()._gerar_comandos(dados, {}))
    assert "Endêmico do Brasil" in texto and "ICMBio: Vulnerável" in texto and "CITES: Anexo II" in texto


def test_nao_sobrescreve_autor_nem_software_da_camera():
    cmds = EXIFManager()._gerar_comandos(DADOS, {})
    assert not any(c.startswith(("-Creator", "-Software")) for c in cmds)
