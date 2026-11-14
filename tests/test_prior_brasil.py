"""IA local com prior Brasil e nuvem sempre consultada (id_worker; avaliação de 14/11/2026)."""
import pytest

pytest.importorskip("PySide6.QtCore")

from modules.step1_identity import id_worker  # noqa: E402

SAO_PAULO = (-23.55, -46.63)
LISBOA = (38.72, -9.14)


def test_ranking_por_especie_junta_subespecies_e_renormaliza():
    rotulos = ["Turdus rufiventris", "Turdus merula", "Turdus merula", "Pitangus sulphuratus"]
    saida = [0.2, 0.5, 0.1, 0.2]
    assert id_worker.ranking_por_especie(rotulos, saida)[0] == ("Turdus merula", 0.5)
    so_brasil = id_worker.ranking_por_especie(rotulos, saida, {"turdus rufiventris", "pitangus sulphuratus"})
    assert [nome for nome, _ in so_brasil] == ["Turdus rufiventris", "Pitangus sulphuratus"]
    assert sum(valor for _, valor in so_brasil) == pytest.approx(1.0)


def test_usar_prior_brasil_por_gps_e_opcao_sem_gps():
    pytest.importorskip("shapely")
    assert id_worker.usar_prior_brasil(*SAO_PAULO, sem_gps_brasil=False)
    assert not id_worker.usar_prior_brasil(*LISBOA, sem_gps_brasil=True)
    assert id_worker.usar_prior_brasil(None, None, sem_gps_brasil=True)
    assert not id_worker.usar_prior_brasil(None, None, sem_gps_brasil=False)


def test_especies_registradas_brasil():
    from modules.step3_geography import listas_conservacao as listas
    especies = listas.especies_registradas_brasil()
    assert "pitangus sulphuratus" in especies and "turdus merula" not in especies


# ------------------------------------------------------------------ worker de ponta a ponta

@pytest.fixture
def foto(tmp_path):
    from PIL import Image
    caminho = tmp_path / "ave.jpg"
    Image.new("RGB", (900, 600), (120, 110, 90)).save(caminho)
    return caminho


def _rodar(foto, monkeypatch, config, nuvem=None):
    pytest.importorskip("ai_edge_litert")
    monkeypatch.setattr(id_worker, "carregar_config", lambda: dict(config))
    chamadas = []

    def consultar(self, motivo):
        chamadas.append(motivo)
        return nuvem

    monkeypatch.setattr(id_worker.LocalIdentificationWorker, "_consultar_nuvem", consultar)
    worker = id_worker.LocalIdentificationWorker(str(foto))
    resultados, erros = [], []
    worker.finished.connect(resultados.append)
    worker.error.connect(erros.append)
    worker.run()  # na mesma thread: os sinais chegam direto
    assert not erros
    return resultados[0], chamadas


def test_com_nuvem_configurada_a_nuvem_sempre_decide(foto, monkeypatch):
    nuvem = {"nome_cientifico": "Pitangus sulphuratus", "confianca": 0.95, "modelo_ia": "iNaturalist"}
    resultado, chamadas = _rodar(foto, monkeypatch, {"google_vision_api_key": "chave"}, nuvem)
    assert resultado == nuvem and chamadas == ["Confirmando a espécie"]


def test_sem_nuvem_vira_sugestao_com_aves_do_brasil(foto, monkeypatch):
    from modules.step3_geography import listas_conservacao as listas
    monkeypatch.setattr(id_worker, "LIMIAR_SUGESTAO", 0.0)
    resultado, chamadas = _rodar(foto, monkeypatch, {})
    assert chamadas == []
    assert resultado["status_msg"] == "Sugestão local" and "confira" in resultado["aviso_sugestao"]
    assert all(listas.registrada_no_brasil(c["nome_cientifico"]) for c in resultado["top3"])


def test_sem_nuvem_e_confianca_baixa_e_inconclusiva(foto, monkeypatch):
    monkeypatch.setattr(id_worker, "LIMIAR_SUGESTAO", 1.01)
    resultado, _ = _rodar(foto, monkeypatch, {"ia_sem_gps_brasil": False})
    assert resultado["nome_cientifico"] == "Identificação Inconclusiva"
    assert resultado["status_msg"] == "Baixa confiança"


def test_opcao_sem_gps_nas_configuracoes(monkeypatch):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QMessageBox
    QApplication.instance() or QApplication([])
    from ui.dialogs import api_settings_dialog as dlg
    salvo = {}
    monkeypatch.setattr(dlg, "carregar_config", lambda: {"tema": "offwhite", "layout": "completo"})
    monkeypatch.setattr(dlg, "salvar_config", salvo.update)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    dialogo = dlg.APISettingsDialog()
    assert dialogo.chk_sem_gps_brasil.isChecked()  # padrão: ligado
    dialogo.chk_sem_gps_brasil.setChecked(False)
    dialogo.save_settings()
    assert salvo["ia_sem_gps_brasil"] is False
