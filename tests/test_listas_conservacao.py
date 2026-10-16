"""Listas embarcadas: Portaria MMA 148/2022, CITES e ocorrência no Brasil (sem rede)."""
import pytest

from modules.step3_geography import listas_conservacao as listas


@pytest.mark.parametrize("nome, categoria", [
    ("Sporophila maximiliani", "CR"),
    ("Harpia harpyja", "VU"),
    ("Anodorhynchus glaucus", "RE"),        # extinta no Brasil (Anexo II da portaria)
])
def test_status_nacional(nome, categoria):
    assert listas.status_nacional(nome)["categoria"] == categoria


def test_especie_fora_da_lista_nacional():
    assert listas.status_nacional("Anodorhynchus hyacinthinus") is None
    assert listas.descrever_status_nacional("Pitangus sulphuratus") == "Não ameaçada (não consta na lista oficial)"


def test_subespecie_ameacada_nao_marca_a_especie_inteira():
    assert listas.status_nacional("Thamnophilus caerulescens") is None
    texto = listas.descrever_status_nacional("Thamnophilus caerulescens")
    assert texto.startswith("Não ameaçada; subespécie ameaçada:") and "cearensis (VU)" in texto


@pytest.mark.parametrize("nome, anexo, texto", [
    ("Amazona aestiva", "II", "Anexo II"),
    ("Anodorhynchus hyacinthinus", "I/NC", "Anexo I (algumas populações não listadas)"),
    ("Oryzoborus maximiliani", "I", "Anexo I"),             # sinônimo
    ("Pitangus sulphuratus", None, "Não listada"),
])
def test_cites(nome, anexo, texto):
    assert listas.anexo_cites(nome) == anexo
    assert listas.descrever_cites(nome) == texto


def test_registro_no_brasil():
    assert listas.total_registradas_brasil() > 1500
    assert listas.registrada_no_brasil("Pitangus sulphuratus")
    assert not listas.registrada_no_brasil("Haemorhous cassinii")


def test_comparacao_por_id_do_inaturalist():
    # Nome do iNaturalist diferente do da portaria (gênero e terminação mudaram)
    assert listas.status_nacional("Heteroxolmis dominicana", inat_id=1289524)["categoria"] == "VU"
    assert listas.status_nacional("Buteogallus coronatus", inat_id=201039)["categoria"] == "EN"
    # Táxons que o iNaturalist agrupa ou nomes parecidos não herdam o status
    assert listas.status_nacional("Thalasseus sandvicensis", inat_id=144541) is None
    assert listas.status_nacional("Morus bassanus", inat_id=3802) is None
