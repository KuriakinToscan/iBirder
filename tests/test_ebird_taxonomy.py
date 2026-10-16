"""Testes da taxonomia eBird embarcada (assets/ebird_taxonomy.csv)."""
from modules.step5_taxonomy import ebird_taxonomy


def test_especie_encontrada_com_link_oficial():
    r = ebird_taxonomy.buscar("Pitangus sulphuratus")
    assert r["species_code"] == "grekis"
    assert r["link"] == "https://ebird.org/species/grekis"
    assert r["common_name"] == "Great Kiskadee"
    assert (r["order"], r["family"]) == ("Passeriformes", "Tyrannidae")


def test_subespecie_cai_para_especie():
    assert ebird_taxonomy.buscar("Junco hyemalis caniceps")["species_code"] == "daejun"


def test_especie_inexistente():
    assert ebird_taxonomy.buscar("Nomen inexistens") is None
