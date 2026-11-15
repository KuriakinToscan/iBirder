"""IA local (BioCLIP) com aves do Brasil e nuvem sempre consultada (id_worker; avaliação de 14/11/2026)."""
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


class ClassificadorFalso:
    """Faz o papel do BioCLIP (sem arquivo de modelo): registra a lista de candidatas pedida."""

    BRASIL = [("Pitangus sulphuratus", 0.6), ("Turdus rufiventris", 0.3), ("Furnarius rufus", 0.1)]
    MUNDO = [("Turdus merula", 0.7), ("Pitangus sulphuratus", 0.2), ("Erithacus rubecula", 0.1)]

    def __init__(self):
        self.pedidos = []

    @staticmethod
    def preparar(imagem):
        import numpy as np
        assert imagem.size == (224, 224)
        return np.zeros((1, 224, 224, 3), dtype=np.float32)

    def embedding(self, entrada):
        return entrada.reshape(-1)[:4]

    def ranking(self, emb, so_brasil=True):
        self.pedidos.append(so_brasil)
        return list(self.BRASIL if so_brasil else self.MUNDO)


def _rodar(foto, monkeypatch, config, nuvem=None, lat=None, lon=None, classificador="falso"):
    pytest.importorskip("ai_edge_litert")
    monkeypatch.setattr(id_worker, "carregar_config", lambda: dict(config))
    falso = ClassificadorFalso() if classificador == "falso" else classificador
    monkeypatch.setattr(id_worker, "carregar_classificador", lambda progresso=None: falso)
    chamadas = []

    def consultar(self, motivo):
        chamadas.append(motivo)
        return nuvem

    monkeypatch.setattr(id_worker.LocalIdentificationWorker, "_consultar_nuvem", consultar)
    worker = id_worker.LocalIdentificationWorker(str(foto))
    worker.lat, worker.lon = lat, lon
    resultados, erros = [], []
    worker.finished.connect(resultados.append)
    worker.error.connect(erros.append)
    worker.run()  # na mesma thread: os sinais chegam direto
    return (resultados[0] if resultados else None), chamadas, erros, falso


def test_com_nuvem_configurada_a_nuvem_sempre_decide(foto, monkeypatch):
    nuvem = {"nome_cientifico": "Pitangus sulphuratus", "confianca": 0.95, "modelo_ia": "iNaturalist"}
    resultado, chamadas, erros, _ = _rodar(foto, monkeypatch, {"google_vision_api_key": "chave"}, nuvem)
    assert not erros and resultado == nuvem and chamadas == ["Confirmando a espécie"]


def test_sem_nuvem_vira_sugestao_com_aves_do_brasil(foto, monkeypatch):
    resultado, chamadas, erros, falso = _rodar(foto, monkeypatch, {})
    assert not erros and chamadas == [] and falso.pedidos == [True]
    assert resultado["status_msg"] == "Sugestão local" and "confira" in resultado["aviso_sugestao"]
    assert resultado["nome_cientifico"] == "Pitangus sulphuratus" and resultado["modelo_ia"] == "BioCLIP (Local)"
    assert [c["nome_cientifico"] for c in resultado["top3"]] == [n for n, _ in ClassificadorFalso.BRASIL]


def test_gps_fora_do_brasil_usa_todas_as_especies(foto, monkeypatch):
    pytest.importorskip("shapely")
    resultado, _, erros, falso = _rodar(foto, monkeypatch, {}, lat=LISBOA[0], lon=LISBOA[1])
    assert not erros and falso.pedidos == [False] and resultado["nome_cientifico"] == "Turdus merula"


def test_sem_gps_com_opcao_desligada_usa_todas_as_especies(foto, monkeypatch):
    _, _, erros, falso = _rodar(foto, monkeypatch, {"ia_sem_gps_brasil": False})
    assert not erros and falso.pedidos == [False]


def test_sem_nuvem_e_confianca_baixa_e_inconclusiva(foto, monkeypatch):
    monkeypatch.setattr(id_worker, "LIMIAR_SUGESTAO", 0.95)
    resultado, _, erros, _ = _rodar(foto, monkeypatch, {})
    assert not erros and resultado["nome_cientifico"] == "Identificação Inconclusiva"
    assert resultado["status_msg"] == "Baixa confiança"


def test_falha_no_download_do_modelo_vira_erro(foto, monkeypatch):
    resultado, _, erros, _ = _rodar(foto, monkeypatch, {}, classificador=None)
    assert resultado is None and erros and "baixar o modelo" in erros[0]


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
