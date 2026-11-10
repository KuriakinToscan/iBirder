"""Respostas da nuvem validadas pelo catálogo eBird: nada de "Bird" como espécie (id_worker)."""
import pytest

pytest.importorskip("PySide6.QtCore")

from core.catalogo_especies import resolver_nome  # noqa: E402
from modules.step1_identity import id_worker  # noqa: E402


@pytest.mark.parametrize("texto, esperado", [
    ("Furnarius rufus", "Furnarius rufus"),
    ("pitangus sulphuratus maximiliani", "Pitangus sulphuratus"),  # subespécie -> espécie
    ("Rufous Hornero", "Furnarius rufus"),                         # nome em inglês do eBird
    ("Bird", None), ("Beak", None), ("Wildlife", None), ("", None), (None, None),
])
def test_resolver_nome(texto, esperado):
    assert resolver_nome(texto) == esperado


def _google(web=(), rotulos=()):
    return {"responses": [{"webDetection": {"webEntities": [{"description": d} for d in web]},
                           "labelAnnotations": [{"description": d} for d in rotulos]}]}


def test_google_so_com_rotulos_genericos_nao_vira_especie():
    assert id_worker.interpretar_resposta_google(_google(["Bird", "Beak"], ["Bird", "Feather"])) is None


def test_google_converte_nome_em_ingles_e_monta_top3():
    r = id_worker.interpretar_resposta_google(
        _google(["Bird", "Rufous hornero", "Furnarius rufus"], ["Great Kiskadee"]))
    assert r["nome_cientifico"] == "Furnarius rufus"
    assert [c["nome_cientifico"] for c in r["top3"]] == ["Furnarius rufus", "Pitangus sulphuratus"]


def test_google_resposta_vazia():
    assert id_worker.interpretar_resposta_google({}) is None


def _inat(*itens):
    return {"results": [{"taxon": {"name": n, "iconic_taxon_name": g}, "vision_score": s} for n, g, s in itens]}


def test_inat_top3_real_sem_generos_nem_nao_aves():
    r = id_worker.interpretar_resposta_inat(_inat(
        ("Turdus", "Aves", 60.0),                        # gênero: descartado
        ("Turdus rufiventris", "Aves", 52.5),
        ("Turdus rufiventris juensis", "Aves", 20.0),    # mesma espécie: não repete
        ("Danaus plexippus", "Insecta", 10.0),           # não é ave
        ("Turdus amaurochalinus", "Aves", 8.0),
    ))
    assert r["nome_cientifico"] == "Turdus rufiventris"
    assert r["confianca"] == pytest.approx(0.525)
    assert [(c["nome_cientifico"], c["confianca"]) for c in r["top3"]] == [
        ("Turdus rufiventris", pytest.approx(0.525)), ("Turdus amaurochalinus", pytest.approx(0.08))]


def test_inat_ave_fora_do_catalogo_e_aceita_pelo_grupo():
    r = id_worker.interpretar_resposta_inat(_inat(("Avis inventada", "Aves", 70.0)))
    assert r["nome_cientifico"] == "Avis inventada"


def test_inat_sem_resultado_util():
    assert id_worker.interpretar_resposta_inat(_inat(("Danaus plexippus", "Insecta", 90.0))) is None
    assert id_worker.interpretar_resposta_inat({}) is None
