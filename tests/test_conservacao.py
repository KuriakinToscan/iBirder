"""Endemismo e status nacional (antes: place_id 6857 = Reino Unido; toda espécie "não endêmica")."""
import pytest

pytest.importorskip("PySide6.QtCore")

from core import taxon_service  # noqa: E402
from modules.step3_geography import conservation_worker as cw  # noqa: E402


def _taxon(establishment, statuses=()):
    detalhe = {"conservation_statuses": list(statuses)}
    if establishment:
        detalhe["establishment_means"] = {"establishment_means": establishment,
                                          "place": {"id": taxon_service.PLACE_BRASIL, "name": "Brazil"}}
    return taxon_service.TaxonInfo({"id": 1}, detalhe)


@pytest.mark.parametrize("ocorrencia, endemismo, texto", [
    ("endemic", "Sim", "Endêmica do Brasil"),
    ("native", "Não", "Nativa"),
    ("introduced", "Não", "Introduzida"),
    (None, "Não informado", "Não informada"),
])
def test_endemismo_vem_do_lugar_brasil(monkeypatch, ocorrencia, endemismo, texto):
    monkeypatch.setattr(cw, "get_taxon", lambda nome: _taxon(ocorrencia))
    out = {}
    w = cw.NationalConservationWorker("Teste teste", country="Brasil")
    w.finished.connect(out.update)
    w.run()
    assert out["endemismo"] == endemismo and out["ocorrencia_brasil"] == texto
    # Espécie fictícia: não consta nas listas embarcadas
    assert out["status_icmbio"] == "Não ameaçada (não consta na lista oficial)"
    assert out["categoria_icmbio"] is None
    assert out["status_cites"] == "Não listada"


def test_listas_embarcadas_e_outras_avaliacoes(monkeypatch):
    estadual = {"authority": "Governo do Paraná", "status": "en", "iucn": 40,
                "place": {"id": 1, "display_name": "Paraná, BR"}}
    argentina = {"authority": "MAyDS", "status": "vu", "iucn": 30, "place": {"id": 2, "display_name": "Argentina"}}
    global_ = {"authority": "IUCN Red List", "status": "lc", "iucn": 10}
    monkeypatch.setattr(cw, "get_taxon", lambda nome: _taxon("native", [argentina, global_, estadual]))
    out = {}
    w = cw.NationalConservationWorker("Harpia harpyja", country="Brasil", estado="Paraná")
    w.finished.connect(out.update)
    w.run()
    assert out["status_icmbio"] == "Vulnerável (VU)" and out["categoria_icmbio"] == "Vulnerável"
    assert out["status_cites"] == "Anexo I"
    lugares = [a["lugar"] for a in out["outras_avaliacoes"]]
    assert lugares == ["Paraná (BR)", "Argentina"]          # estado da foto primeiro; IUCN global fora
    assert out["outras_avaliacoes"][0]["estado_da_foto"] and out["outras_avaliacoes"][0]["categoria"] == "Em Perigo"


def test_sem_internet_as_listas_oficiais_continuam(monkeypatch):
    def falha(nome):
        raise ConnectionError("sem rede")
    monkeypatch.setattr(cw, "get_taxon", falha)
    out = {}
    w = cw.NationalConservationWorker("Sporophila maximiliani", country="Brasil")
    w.finished.connect(out.update)
    w.run()
    assert out["status_icmbio"] == "Criticamente em Perigo (CR)" and out["status_cites"] == "Anexo I"
    assert out["endemismo"] == "Não informado"


def test_estabelecimento_de_outro_lugar_e_ignorado():
    t = taxon_service.TaxonInfo({"id": 1}, {"establishment_means": {"establishment_means": "endemic",
                                                                      "place": {"id": 6857, "name": "United Kingdom"}}})
    assert t.ocorrencia_brasil is None
