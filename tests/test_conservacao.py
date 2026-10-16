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
    assert out["status_icmbio"] == "Não disponível"     # nunca o enganoso "Não Avaliado"
    assert out["status_cites"] == "Não disponível"      # nunca o falso "Não Listado"


def test_status_nacional_quando_o_inaturalist_tiver(monkeypatch):
    nacional = {"authority": "ICMBio", "status": "vu", "place": {"id": taxon_service.PLACE_BRASIL}}
    monkeypatch.setattr(cw, "get_taxon", lambda nome: _taxon("endemic", [nacional]))
    out = {}
    w = cw.NationalConservationWorker("Teste teste", country="Brasil")
    w.finished.connect(out.update)
    w.run()
    assert out["status_icmbio"] == "Vulnerável"


def test_estabelecimento_de_outro_lugar_e_ignorado():
    t = taxon_service.TaxonInfo({"id": 1}, {"establishment_means": {"establishment_means": "endemic",
                                                                      "place": {"id": 6857, "name": "United Kingdom"}}})
    assert t.ocorrencia_brasil is None
