"""Aviso de espécie sem registro no Brasil (IA local treinada majoritariamente com aves da América do Norte)."""
import pytest

pytest.importorskip("PySide6.QtCore")
pytest.importorskip("shapely")

from modules.step1_identity import id_worker  # noqa: E402

SAO_PAULO = (-23.55, -46.63)
LISBOA = (38.72, -9.14)
TOP3 = [{"nome_cientifico": "Haemorhous cassinii", "confianca": 0.81},
        {"nome_cientifico": "Pitangus sulphuratus", "confianca": 0.10},
        {"nome_cientifico": "Carpodacus erythrinus", "confianca": 0.05}]


def test_especie_sem_registro_no_brasil_gera_aviso_e_alternativas():
    fora, alternativas = id_worker.avaliar_ocorrencia(TOP3, *SAO_PAULO)
    assert fora
    assert [a["nome_cientifico"] for a in alternativas] == ["Pitangus sulphuratus"]


def test_fora_do_brasil_ou_sem_coordenadas_nao_afirma_nada():
    assert id_worker.avaliar_ocorrencia(TOP3, *LISBOA) == (False, [])
    assert id_worker.avaliar_ocorrencia(TOP3, None, None) == (False, [])


def test_especie_registrada_no_brasil_nao_gera_aviso():
    assert id_worker.avaliar_ocorrencia(TOP3[1:], *SAO_PAULO) == (False, [])
