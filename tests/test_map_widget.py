"""
Testes do mapa incremental.

A parte com navegador (QtWebEngine) só roda com IBIRDER_TESTES_GUI=1 (ativado no CI do
Windows), pois exige o Chromium do Qt. Não acessa a rede: a taxonKey do GBIF é pré-carregada.
"""
import json
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWebEngineWidgets")

gui = pytest.mark.skipif(os.environ.get("IBIRDER_TESTES_GUI") != "1",
                         reason="defina IBIRDER_TESTES_GUI=1 para testar com o QtWebEngine")


def test_pagina_base_embute_leaflet_e_api():
    from ui.widgets.map_widget import html_base
    html = html_base(-23.5, -46.6, 6)
    assert "L.map(" in html and "window.ibirder" in html
    assert "/*LEAFLET_JS*/" not in html and "__PIN_AUDIO__" not in html
    assert "[-23.5, -46.6, 6]" in html
    assert "cdn.jsdelivr" not in html and "jquery" not in html.lower()  # sem dependências externas


@gui
def test_mapa_atualiza_sem_recarregar_e_entrega_eventos():
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from modules.step3_geography import gbif_client
    gbif_client._taxon_key_cache.update({"Pitangus sulphuratus": 2482755, "Furnarius rufus": 2482491})
    from ui.widgets.map_widget import MapWidget

    def esperar(seg):
        loop = QEventLoop()
        QTimer.singleShot(int(seg * 1000), loop.quit)
        loop.exec()

    def estado(m):
        res = {}
        loop = QEventLoop()
        m.page().runJavaScript("ibirder.estado()", 0, lambda r: (res.update(json.loads(r)), loop.quit()))
        QTimer.singleShot(5000, loop.quit)
        loop.exec()
        return res

    m = MapWidget()
    m.resize(800, 500)
    m.show()
    cargas, eventos = [], []
    m.loadFinished.connect(cargas.append)
    m.marker_dragged.connect(lambda la, lo: eventos.append(("drag", round(la, 2), round(lo, 2))))
    m.audio_clicked.connect(lambda i: eventos.append(("audio", i)))

    audios = [{"lat": -23.6, "lon": -46.7, "id": "123", "ranking": 1, "distancia_km": 3.2}]
    m.update_map(-14.2, -51.9, zoom=4, force_hide_alert=True)
    m.update_map(-23.58, -46.65, zoom=6, add_marker=True, scientific_name="Pitangus sulphuratus", audio_markers=audios)
    inicio = time.time()
    while not cargas and time.time() - inicio < 30:
        esperar(0.2)
    esperar(1.5)
    e = estado(m)
    assert cargas == [True]
    assert e["pino"] == [-23.58, -46.65] and e["audios"] == 1 and "taxonKey=2482755" in e["gbif"]
    assert e["ponte"] is True

    m.page().runJavaScript("pino.setLatLng([-22.5, -45.1]); pino.fire('dragend');"
                           "camadaAudios.getLayers()[0].fire('click');")
    esperar(1.5)
    assert ("drag", -22.5, -45.1) in eventos and ("audio", "123") in eventos

    m.clear_audio_cache()
    m.update_map(-14.2, -51.9, zoom=4, scientific_name="Furnarius rufus")
    esperar(1.5)
    e = estado(m)
    assert e["pino"] is None and e["audios"] == 0 and "taxonKey=2482491" in e["gbif"]
    assert m.alert_frame.isVisible()
    assert cargas == [True]  # nenhuma recarga da página
    m.close()
