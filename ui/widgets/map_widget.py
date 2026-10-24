#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#
#  Este programa é um software livre: você pode redistribuí-lo e/ou 
#  modificá-lo sob os termos da Licença Pública Geral GNU conforme 
#  publicada pela Free Software Foundation, tanto a versão 3 da 
#  Licença, como (a seu critério) qualquer versão posterior.
#
#  Este programa é distribuído na esperança de que possa ser útil, 
#  mas SEM NENHUMA GARANTIA; sem uma garantia implícita de 
#  ADEQUAÇÃO A QUALQUER MERCADO OU APLICAÇÃO EM PARTICULAR. 
#  Veja a Licença Pública Geral GNU para mais detalhes.
#
#  Você deve ter recebido uma cópia da Licença Pública Geral GNU 
#  junto com este programa. Se não, veja <https://www.gnu.org/licenses/>.


"""
Mapa do iBirder (v1.2).

A página (Leaflet embarcado em assets/leaflet) é carregada uma única vez. Depois, cada
update_map() vira chamadas JavaScript (window.ibirder.*) que movem a vista, o pino,
a camada do GBIF e os pinos de áudio, sem recriar o mapa. Antes, cada atualização
gerava um HTML novo com o Folium (10 arquivos externos, ~1 s com o mapa piscando)
e consultava o GBIF na thread da interface.
"""

import base64
import json
import logging

from PySide6.QtCore import QObject, QThread, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QDesktopServices, QColor
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QGraphicsDropShadowEffect

from core.paths import APP_DIR

ASSETS = APP_DIR / "assets"

GBIF_TILE = ("https://api.gbif.org/v2/map/occurrence/density/{{z}}/{{x}}/{{y}}@1x.png?taxonKey={chave}"
             "&basisOfRecord=HUMAN_OBSERVATION&basisOfRecord=OBSERVATION&bin=hex&hexPerTile=20&style=classic.poly")


class _Ponte(QObject):
    """
    Ponte JavaScript -> Python (QWebChannel). Até a v1.1 os eventos do mapa navegavam para
    ibirder://..., mas o Chromium não entrega esquemas desconhecidos ao acceptNavigationRequest:
    arrastar o pino e clicar nos pinos de áudio não tinham efeito.
    """

    def __init__(self, mapa):
        super().__init__(mapa)
        self.mapa = mapa

    @Slot(float, float)
    def pino_arrastado(self, lat, lon):
        self.mapa.marker_dragged.emit(lat, lon)

    @Slot(str)
    def audio_clicado(self, audio_id):
        self.mapa.audio_clicked.emit(audio_id)


class ExternalLinkPage(QWebEnginePage):
    """Abre no navegador padrão os links clicados no mapa (ex.: atribuição do GBIF)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.map_widget = parent

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        if _type == QWebEnginePage.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
            return False
        return True


class _GbifWorker(QThread):
    """Consulta a taxonKey do GBIF fora da thread da interface."""
    pronto = Signal(str, object)  # (nome científico, taxonKey ou None)

    def __init__(self, nome, parent=None):
        super().__init__(parent)
        self.nome = nome

    def run(self):
        from modules.step3_geography.gbif_client import get_gbif_taxon_key
        try:
            chave = get_gbif_taxon_key(self.nome)
        except Exception as e:
            logging.debug(f"GBIF indisponível: {e}")
            chave = None
        self.pronto.emit(self.nome, chave)


def _ler_asset(*partes, binario=False):
    caminho = ASSETS.joinpath(*partes)
    try:
        return caminho.read_bytes() if binario else caminho.read_text(encoding="utf-8")
    except OSError as e:
        logging.error(f"Asset do mapa ausente: {caminho} ({e})")
        return b"" if binario else ""


def html_base(lat, lon, zoom):
    """Página do mapa com Leaflet embutido e a API window.ibirder."""
    pin_audio = base64.b64encode(_ler_asset("vocal_pin_base.png", binario=True)).decode()
    return _TEMPLATE.replace("/*LEAFLET_CSS*/", _ler_asset("leaflet", "leaflet.css")) \
                    .replace("/*LEAFLET_JS*/", _ler_asset("leaflet", "leaflet.js")) \
                    .replace("__PIN_AUDIO__", pin_audio) \
                    .replace("__VISTA__", json.dumps([lat, lon, zoom]))


class MapWidget(QWebEngineView):
    marker_dragged = Signal(float, float)
    audio_clicked = Signal(str)   # v0.4.4
    alert_clicked = Signal()      # v0.6.3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPage(ExternalLinkPage(self))  # Intercepta links para abrir no navegador padrão
        self._ponte = _Ponte(self)
        self._canal = QWebChannel(self)
        self._canal.registerObject("ponte", self._ponte)
        self.page().setWebChannel(self._canal)
        self._cached_audio_markers = None     # Cache de pins de áudio (v1.1)

        # Estado da página incremental
        self._pagina_carregada = False   # setHtml já feito
        self._pronto = False             # JavaScript disponível
        self._fila_js = []               # comandos enviados antes do carregamento
        self._gbif_aplicado = None       # espécie cuja camada GBIF está no mapa
        self._gbif_desejado = None       # espécie pedida mais recentemente
        self._gbif_workers = []
        self.loadFinished.connect(self._ao_carregar)

        # --- Alerta de GPS Ausente (v0.3.34 / v0.6.3 Interativo) ---
        self.alert_frame = QFrame(self)
        self.alert_frame.setObjectName("overlay_alert")
        self.alert_frame.setCursor(Qt.PointingHandCursor)
        self.alert_frame.mousePressEvent = lambda e: self.alert_clicked.emit() if e.button() == Qt.LeftButton else None

        layout = QVBoxLayout(self.alert_frame)
        layout.setContentsMargins(20, 12, 20, 12)
        lbl_alert = QLabel("Sem dados de localização, indique manualmente aqui", self.alert_frame)
        lbl_alert.setObjectName("alert_text")
        lbl_alert.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_alert)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.alert_frame.setGraphicsEffect(shadow)
        self.alert_frame.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'alert_frame'):
            self.alert_frame.adjustSize()
            x = (self.width() - self.alert_frame.width()) // 2
            self.alert_frame.move(x, 20)

    # ---------- página e JavaScript ----------

    def _garantir_pagina(self, lat, lon, zoom):
        if not self._pagina_carregada:
            self._pagina_carregada = True
            self._pronto = False
            self._gbif_aplicado = None
            self.setHtml(html_base(lat, lon, zoom), QUrl("about:blank"))

    def _ao_carregar(self, ok):
        if not self._pagina_carregada:
            return  # carregamento do placeholder
        if not ok:
            logging.error("Falha ao carregar a página do mapa.")
            self._pagina_carregada = False
            return
        self._pronto = True
        fila, self._fila_js = self._fila_js, []
        for codigo in fila:
            self.page().runJavaScript(codigo)

    def _js(self, codigo):
        if self._pronto:
            self.page().runJavaScript(codigo)
        else:
            self._fila_js.append(codigo)

    def show_placeholder_message(self, message):
        self._pagina_carregada = False
        self._pronto = False
        self._fila_js.clear()
        self.setHtml(f"""
        <html>
        <body style="display:flex; justify-content:center; align-items:center; height:100%; margin:0; font-family:'Segoe UI', sans-serif; background-color:#f0f2f5; color:#6b7280;">
            <div style="text-align:center;"><div style="font-size:14px;">{message}</div></div>
        </body>
        </html>
        """)

    def clear_audio_cache(self):
        """Limpa o cache de pins de áudio (chamado ao trocar de espécie/imagem)."""
        self._cached_audio_markers = None

    # ---------- GBIF em segundo plano ----------

    def _atualizar_gbif(self, nome):
        self._gbif_desejado = nome
        if nome == self._gbif_aplicado:
            return
        if not nome:
            self._aplicar_gbif(None, None)
            return
        from modules.step3_geography.gbif_client import _taxon_key_cache
        if nome in _taxon_key_cache:
            self._aplicar_gbif(nome, _taxon_key_cache[nome])
            return
        self._aplicar_gbif(None, None)  # não mostra a distribuição da espécie anterior
        worker = _GbifWorker(nome, self)
        worker.pronto.connect(self._ao_receber_gbif)
        worker.finished.connect(lambda w=worker: self._liberar_worker(w))
        self._gbif_workers.append(worker)
        worker.start()

    def _liberar_worker(self, worker):
        if worker in self._gbif_workers:
            self._gbif_workers.remove(worker)
        worker.deleteLater()

    def _ao_receber_gbif(self, nome, chave):
        if nome == self._gbif_desejado:  # descarta respostas de espécies anteriores
            self._aplicar_gbif(nome, chave)

    def _aplicar_gbif(self, nome, chave):
        self._gbif_aplicado = nome
        if chave:
            url = GBIF_TILE.format(chave=chave)
            atribuicao = (f'<a href="https://www.gbif.org/species/{chave}" '
                          'style="font-weight:bold; color:#005fa8; text-decoration:none;">Dados: GBIF 🔗</a>')
            self._js(f"ibirder.gbif({json.dumps(url)}, {json.dumps(atribuicao)});")
        else:
            self._js("ibirder.gbif(null, null);")

    # ---------- API usada pela janela principal ----------

    def update_map(self, lat, lon, zoom=5, add_marker=False, scientific_name=None, audio_markers=None, force_hide_alert=False):
        try:
            # Cache de pins: guarda novos ou reutiliza os anteriores (v1.1)
            if audio_markers is not None:
                self._cached_audio_markers = audio_markers
            elif self._cached_audio_markers:
                audio_markers = self._cached_audio_markers

            self._garantir_pagina(lat, lon, zoom)
            self._js(f"ibirder.vista({float(lat)}, {float(lon)}, {int(zoom)});")
            if add_marker:
                self._js(f"ibirder.pino({float(lat)}, {float(lon)});")
            else:
                self._js("ibirder.pino(null, null);")

            pinos = []
            for am in audio_markers or []:
                if am.get('lat') is None or am.get('lon') is None:
                    continue
                dist = am.get('distancia_km') or 0
                pinos.append({
                    "lat": am['lat'], "lon": am['lon'],
                    "id": str(am.get('id', am.get('url', ''))),
                    "ranking": am.get('ranking', '?'),
                    "dica": f"Distância {dist:.0f}km" if dist >= 1 else f"Distância {dist:.1f}km",
                })
            self._js(f"ibirder.audios({json.dumps(pinos)});")

            self._atualizar_gbif(scientific_name)

            if not add_marker and not force_hide_alert:
                self.alert_frame.show()
                self.alert_frame.raise_()
            else:
                self.alert_frame.hide()

        except Exception as e:
            logging.error(f"Erro ao atualizar o mapa: {e}", exc_info=True)


_TEMPLATE = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>/*LEAFLET_CSS*/</style>
<style>
  html, body, #mapa { height: 100%; width: 100%; margin: 0; padding: 0; }
  #legenda { position: fixed; bottom: 20px; right: 20px; width: 140px; z-index: 9999; font-size: 12px;
             border: 2px solid grey; background-color: rgba(255,255,255,0.9); border-radius: 8px;
             padding: 10px; display: none; font-family: 'Segoe UI', sans-serif; }
  #legenda i { width: 10px; height: 10px; display: inline-block; margin-right: 5px; }
  .pino-audio { position: relative; width: 44px; height: 44px; cursor: pointer; }
  .pino-audio img { width: 44px; height: 44px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3)); }
  .pino-audio span { position: absolute; top: -2px; right: -2px; background-color: #ef4444; color: white;
             border: 1.5px solid white; border-radius: 50%; width: 20px; height: 20px; display: flex;
             align-items: center; justify-content: center; font-weight: bold; font-size: 11px;
             box-shadow: 0 1px 3px rgba(0,0,0,0.4); pointer-events: none; font-family: 'Segoe UI', sans-serif; }
</style>
<script>/*LEAFLET_JS*/</script>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
</head><body>
<div id="mapa"></div>
<div id="legenda"><b>Densidade (GBIF)</b><br>
  <i style="background:#FF0000"></i> Alta<br>
  <i style="background:#FFA500"></i> Média<br>
  <i style="background:#FFFF00"></i> Baixa</div>
<script>
  var VISTA = __VISTA__;
  var TRANSPARENTE = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
  var mapa = L.map('mapa', {zoomControl: true}).setView([VISTA[0], VISTA[1]], VISTA[2]);
  L.control.scale().addTo(mapa);

  var osm = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(mapa);
  var satelite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 19, attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
  });
  var camadaGbif = L.tileLayer(TRANSPARENTE, {opacity: 0.5, attribution: 'Dados: GBIF (Sem dados)'});
  var camadaAudios = L.featureGroup();
  L.control.layers({'Mapa': osm, 'Satélite': satelite},
                   {'Dist. Geográfica (GBIF)': camadaGbif, 'Vocalizações': camadaAudios},
                   {position: 'topright', collapsed: false}).addTo(mapa);

  var iconeFoto = L.divIcon({className: '', iconSize: [30, 42], iconAnchor: [15, 42], html:
      '<svg width="30" height="42" viewBox="0 0 30 42" xmlns="http://www.w3.org/2000/svg">' +
      '<path d="M15 1C7.3 1 1 7.2 1 14.9 1 25.3 15 41 15 41s14-15.7 14-26.1C29 7.2 22.7 1 15 1z" fill="#d63e2a" stroke="#8b1f12" stroke-width="1.5"/>' +
      '<rect x="8" y="10" width="14" height="10" rx="2" fill="#fff"/><rect x="12" y="8" width="6" height="3" rx="1" fill="#fff"/>' +
      '<circle cx="15" cy="15" r="3" fill="#d63e2a"/></svg>'});

  var pino = null;
  var ponte = null;
  if (typeof QWebChannel !== 'undefined' && window.qt && qt.webChannelTransport) {
    new QWebChannel(qt.webChannelTransport, function(canal) { ponte = canal.objects.ponte; });
  }

  window.ibirder = {
    vista: function(lat, lon, zoom) { mapa.setView([lat, lon], zoom); },
    pino: function(lat, lon) {
      if (lat === null) { if (pino) { mapa.removeLayer(pino); pino = null; } return; }
      if (pino) { pino.setLatLng([lat, lon]); return; }
      pino = L.marker([lat, lon], {draggable: true, icon: iconeFoto}).bindTooltip('Local da Foto (Alvo)').addTo(mapa);
      pino.on('dragend', function() {
        var p = pino.getLatLng();
        if (ponte) { ponte.pino_arrastado(p.lat, p.lng); }
      });
    },
    gbif: function(url, atribuicao) {
      var visivel = mapa.hasLayer(camadaGbif);
      if (visivel) { mapa.attributionControl.removeAttribution(camadaGbif.options.attribution); }
      camadaGbif.options.attribution = atribuicao || 'Dados: GBIF (Sem dados)';
      if (visivel) { mapa.attributionControl.addAttribution(camadaGbif.options.attribution); }
      camadaGbif.setUrl(url || TRANSPARENTE);
      document.getElementById('legenda').style.display = url ? 'block' : 'none';
    },
    audios: function(lista) {
      camadaAudios.clearLayers();
      lista.forEach(function(a) {
        var html = '<div class="pino-audio"><img src="data:image/png;base64,__PIN_AUDIO__"><span>' + a.ranking + '</span></div>';
        L.marker([a.lat, a.lon], {icon: L.divIcon({html: html, className: '', iconSize: [44, 44], iconAnchor: [22, 44]})})
          .bindTooltip(a.dica)
          .on('click', function() { if (ponte) { ponte.audio_clicado(String(a.id)); } })
          .addTo(camadaAudios);
      });
    },
    // Usado pelos testes: estado atual do mapa
    estado: function() {
      return JSON.stringify({
        centro: [mapa.getCenter().lat, mapa.getCenter().lng], zoom: mapa.getZoom(),
        pino: pino ? [pino.getLatLng().lat, pino.getLatLng().lng] : null,
        gbif: camadaGbif._url, audios: camadaAudios.getLayers().length,
        legenda: document.getElementById('legenda').style.display,
        ponte: ponte !== null
      });
    }
  };
</script>
</body></html>
"""
