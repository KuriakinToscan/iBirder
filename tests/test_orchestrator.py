"""
Testes do orquestrador sem rede e sem Chrome: troca de espécie no meio da busca
não pode deixar resultados da espécie anterior chegarem à interface.
"""
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtCore = pytest.importorskip("PySide6.QtCore")

from core import taxon_service  # noqa: E402

LENTA, RAPIDA = "Lenta lenta", "Rapida rapida"


class _Taxon(taxon_service.TaxonInfo):
    def __init__(self, nome):
        super().__init__({"id": 1, "preferred_common_name": nome}, {
            "english_common_name": nome,
            "ancestors": [{"rank": "order", "name": f"Ordem {nome}"}, {"rank": "family", "name": f"Familia {nome}"}],
            "conservation_statuses": [{"authority": "IUCN", "status": "lc"}],
        })


class _BuscadorFalso:
    """Substitui o Chrome: a espécie LENTA demora 1,5 s, a RAPIDA responde na hora."""
    def __init__(self, *a, **k):
        pass

    def buscar_link_wikiaves(self, sci):
        if sci == LENTA:
            time.sleep(1.5)
        return f"https://www.wikiaves.com.br/wiki/{sci.split()[0].lower()}"

    def extrair_dados_especie(self, url, sci=None):
        return {"nome_comum": sci, "etimologia": "x", "caracteristicas": "y"}

    def buscar_link_ebird(self, sci):
        return None

    def fechar(self):
        pass


@pytest.fixture
def app(monkeypatch):
    def buscar(sci):
        if sci == LENTA:
            time.sleep(1.5)
        return _Taxon(sci)
    monkeypatch.setattr(taxon_service, "_buscar", buscar)
    taxon_service.clear_cache()
    import modules.step2_biology.wiki_worker as ww
    monkeypatch.setattr(ww, "BuscadorBlindado", _BuscadorFalso)
    import core.updater as up
    monkeypatch.setattr(up.AppUpdater, "check_for_updates", lambda self: None)
    return QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


def _rodar(app, segundos):
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(int(segundos * 1000), loop.quit)
    loop.exec()


def test_troca_de_especie_descarta_resultados_antigos(app):
    from core.orchestrator import Orchestrator
    from core.session_logger import SessionLogger

    sl = SessionLogger()
    orq = Orchestrator(sl)
    recebidos = []
    orq.step2_wiki_concluida.connect(lambda r: recebidos.append(("wiki", r["nome_comum"])))
    orq.step3_iucn_concluida.connect(lambda r: recebidos.append(("iucn", r["iucn_status"])))
    orq.step5_ebird_concluido.connect(lambda r: recebidos.append(("taxonomia", r["ordem"])))

    orq.start_cascade_from_step2(LENTA)     # usuário pesquisa uma ave...
    _rodar(app, 0.2)
    orq.reset()                             # ...e logo troca de foto/espécie
    sl.reset()
    sl.registrar_identificacao({"nome_cientifico": RAPIDA})
    orq.start_cascade_from_step2(RAPIDA)
    _rodar(app, 2.5)                        # tempo para a LENTA terminar também

    assert ("wiki", RAPIDA) in recebidos
    assert ("taxonomia", f"Ordem {RAPIDA}".capitalize()) in recebidos
    assert not any(LENTA in str(v) or "Lenta" in str(v) for _, v in recebidos), recebidos
    assert "Lenta" not in str(sl.buffer)    # nada da ave anterior na caderneta/EXIF

    orq.encerrar()
    sl.limpar_sessao()


def test_worker_em_execucao_nao_e_destruido(app):
    """Trocar o worker de uma etapa em execução não pode destruir a QThread (derrubaria o app)."""
    from core.orchestrator import Orchestrator
    orq = Orchestrator(None)
    orq.start_step2_biology(LENTA)
    antigo = orq.wiki_worker
    _rodar(app, 0.1)
    assert antigo.isRunning()
    orq.start_step2_biology(RAPIDA)         # substitui enquanto o antigo ainda roda
    assert antigo in orq._workers_orfaos
    _rodar(app, 4.5)                        # timer de órfãos libera após o término
    assert orq._workers_orfaos == []
    orq.encerrar()
