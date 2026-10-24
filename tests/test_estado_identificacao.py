"""
Estado da identificação (v1.4): a etapa acompanha os sinais do Orchestrator e o que a
janela informa (foto aberta, busca manual, gravação, limpeza). Sem rede e sem IA.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ui import estado_identificacao as ei  # noqa: E402


class OrchestratorFalso(QObject):
    """Só os sinais que o estado acompanha."""
    step1_identificacao_concluida = Signal(dict)
    step1_identificacao_erro = Signal(str)


@pytest.fixture
def estado():
    QApplication.instance() or QApplication([])
    orq = OrchestratorFalso()
    est = ei.EstadoIdentificacao()
    est.conectar(orq)
    etapas = []
    est.etapa_alterada.connect(etapas.append)
    return est, orq, etapas


def test_fluxo_completo(estado):
    est, orq, etapas = estado
    assert est.etapa == ei.SEM_FOTO
    est.foto_aberta("C:/fotos/ave.jpg")
    orq.step1_identificacao_concluida.emit({"nome_cientifico": "Turdus rufiventris",
                                            "confianca": 0.93, "status_msg": "Alta confiança"})
    assert est.etapa == ei.CONFERIR
    assert est.nome_cientifico == "Turdus rufiventris" and est.confianca == 0.93 and not est.manual
    est.gravada("C:/fotos/Turdus rufiventris 001.jpg")
    assert est.caminho.endswith("001.jpg")
    assert etapas == [ei.IDENTIFICANDO, ei.CONFERIR, ei.GRAVADA]
    est.limpar()
    assert est.etapa == ei.SEM_FOTO and est.caminho is None and est.nome_cientifico is None


def test_inconclusiva_e_busca_manual(estado):
    est, orq, etapas = estado
    est.foto_aberta("ave.jpg")
    orq.step1_identificacao_concluida.emit({"nome_cientifico": "Pitangus sulphuratus",
                                            "confianca": 0.31, "status_msg": "Baixa confiança"})
    assert est.etapa == ei.INCONCLUSIVA and est.nome_cientifico is None
    # A busca manual limpa a análise, mantém a foto e parte da espécie digitada
    est.limpar(manter_foto=True)
    est.especie_digitada("Pitangus sulphuratus")
    assert est.etapa == ei.CONFERIR and est.manual and est.caminho == "ave.jpg"
    assert etapas == [ei.IDENTIFICANDO, ei.INCONCLUSIVA, ei.IDENTIFICANDO, ei.CONFERIR]


def test_erro_e_sinal_alterado_sem_repetir_etapa(estado):
    est, orq, etapas = estado
    alteracoes = []
    est.alterado.connect(lambda: alteracoes.append(est.etapa))
    est.foto_aberta("a.jpg")
    est.foto_aberta("b.jpg")  # mesma etapa: etapa_alterada não repete, alterado sim
    orq.step1_identificacao_erro.emit("modelo ausente")
    assert est.etapa == ei.ERRO and est.mensagem_erro == "modelo ausente"
    assert etapas == [ei.IDENTIFICANDO, ei.ERRO]
    assert alteracoes == [ei.IDENTIFICANDO, ei.IDENTIFICANDO, ei.ERRO]
    assert set(ei.ETAPAS) >= set(etapas)
