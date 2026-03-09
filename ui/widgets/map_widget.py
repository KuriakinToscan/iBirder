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

from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
import io

class ExternalLinkPage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.map_widget = parent

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        url_str = url.toString()
        if url_str.startswith("ibirder://map_drag"):
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url_str)
            query = parse_qs(parsed.query)
            if 'lat' in query and 'lon' in query:
                try:
                    lat = float(query['lat'][0])
                    lon = float(query['lon'][0])
                    if hasattr(self.map_widget, 'marker_dragged'):
                        self.map_widget.marker_dragged.emit(lat, lon)
                except ValueError: pass
            return False
            
        if url_str.startswith("ibirder://audio_click"):
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url_str)
            query = parse_qs(parsed.query)
            if 'id' in query:
                audio_id = query['id'][0]
                if hasattr(self.map_widget, 'audio_clicked'):
                    self.map_widget.audio_clicked.emit(audio_id)
            return False

        if _type == QWebEnginePage.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
            return False
        return True
class MapWidget(QWebEngineView):
    from PySide6.QtCore import Signal
    marker_dragged = Signal(float, float)
    audio_clicked = Signal(str) # v0.4.4
    alert_clicked = Signal()    # v0.6.3
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPage(ExternalLinkPage(self)) # Intercepta links to open in default browser

        # --- Alerta de GPS Ausente (v0.3.34 / v0.6.3 Interativo) ---
        from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        from PySide6.QtCore import Qt
        
        self.alert_frame = QFrame(self)
        self.alert_frame.setObjectName("overlay_alert")
        self.alert_frame.setCursor(Qt.PointingHandCursor)
        self.alert_frame.mousePressEvent = lambda e: self.alert_clicked.emit() if e.button() == Qt.LeftButton else None
        
        # Estilo removido e movido para StyleManager (v0.6.3 / v0.8.0)
        
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
            y = 20  # Margem do topo superior
            self.alert_frame.move(x, y)

    def show_placeholder_message(self, message):
        html = f"""
        <html>
        <body style="display:flex; justify-content:center; align-items:center; height:100%; margin:0; font-family:'Segoe UI', sans-serif; background-color:#f0f2f5; color:#6b7280;">
            <div style="text-align:center;">
                <div style="font-size:14px;">{message}</div>
            </div>
        </body>
        </html>
        """
        self.setHtml(html)

    def update_map(self, lat, lon, zoom=5, add_marker=False, scientific_name=None, audio_markers=None, force_hide_alert=False):
        try:
            from modules.step3_geography.gbif_client import get_gbif_taxon_key
            import folium
            
            # Create Folium Map
            m = folium.Map(location=[lat, lon], zoom_start=zoom, control_scale=True, tiles=None)
            
            # Base Layers (OSM First as default)
            folium.TileLayer('OpenStreetMap', name='Mapa', control=True).add_to(m)
            
            # Satellite Layer (Second, hidden by default)
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community', 
                name='Satélite', 
                control=True,
                show=False
            ).add_to(m)

            # GBIF Layer (Always present for control visibility)
            gbif_url = ""
            attr_html = ""
            
            if scientific_name:
                taxon_key = get_gbif_taxon_key(scientific_name)
                if taxon_key:
                    # Attribution Link
                    species_url = f"https://www.gbif.org/species/{taxon_key}"
                    attr_html = f'<a href="{species_url}" style="font-weight:bold; color:#005fa8; text-decoration:none;">Dados: GBIF 🔗</a>'
                    
                    # v0.3.13: HexPerTile=20 (Larger hexagons)
                    gbif_url = f"https://api.gbif.org/v2/map/occurrence/density/{{z}}/{{x}}/{{y}}@1x.png?taxonKey={taxon_key}&basisOfRecord=HUMAN_OBSERVATION&basisOfRecord=OBSERVATION&bin=hex&hexPerTile=20&style=purpleYellow.poly"

                    # Add Legend (v0.3.13)
                    legend_html = '''
                    <div style="position: fixed; 
                                bottom: 20px; right: 20px; width: 140px; height: 90px; 
                                border:2px solid grey; z-index:9999; font-size:12px;
                                background-color:rgba(255, 255, 255, 0.9);
                                border-radius: 8px; padding: 10px;">
                        <b>Densidade (GBIF)</b><br>
                        <i style="background: #FFFF00; width: 10px; height: 10px; display: inline-block; margin-right: 5px;"></i> Alta<br>
                        <i style="background: #FF0000; width: 10px; height: 10px; display: inline-block; margin-right: 5px;"></i> Média<br>
                        <i style="background: #800080; width: 10px; height: 10px; display: inline-block; margin-right: 5px;"></i> Baixa
                    </div>
                    '''
                    m.get_root().html.add_child(folium.Element(legend_html))
            
            if not gbif_url:
                # Transparent tile for "Empty" state
                pass

            # Valid GBIF URL or Fallback for visibility
            # Transparent 1x1 png:
            transp_tile = "https://upload.wikimedia.org/wikipedia/commons/c/ca/1x1.png"
            
            final_url = gbif_url if gbif_url else transp_tile
            final_attr = attr_html if attr_html else "Dados: GBIF (Sem dados)"
            
            folium.TileLayer(
                tiles=final_url, 
                attr=final_attr, 
                name='Dist. Geográfica (GBIF)',
                overlay=True, 
                control=True, 
                show=False,
                opacity=0.5
            ).add_to(m)

            if add_marker:
                marker = folium.Marker(
                    [lat, lon], 
                    icon=folium.Icon(color="red", icon="camera", prefix="glyphicon"),
                    tooltip="Local da Foto (Alvo)",
                    draggable=True
                )
                marker.add_to(m)
                
                # JS to hook dragend
                drag_js = """
                <script>
                setTimeout(function() {
                    for (var key in window) {
                        if (key.startsWith("map_")) {
                            var mapObj = window[key];
                            mapObj.eachLayer(function(layer) {
                                if (layer.options && layer.options.draggable) {
                                    layer.on('dragend', function(e) {
                                        var position = layer.getLatLng();
                                        window.location.href = "ibirder://map_drag?lat=" + position.lat + "&lon=" + position.lng;
                                    });
                                }
                            });
                        }
                    }
                }, 500);
                </script>
                """
                m.get_root().html.add_child(folium.Element(drag_js))
                
            if audio_markers:
                import base64
                import os
                import sys
                from pathlib import Path

                # Obter caminho do asset (v0.8.2)
                if getattr(sys, 'frozen', False):
                    base_path = Path(sys._MEIPASS) / 'assets'
                else:
                    base_path = Path(__file__).parent.parent.parent / 'assets'
                
                vocal_pin_path = base_path / "vocal_pin_base.png"
                vocal_pin_b64 = ""
                if vocal_pin_path.exists():
                    with open(vocal_pin_path, "rb") as f:
                        vocal_pin_b64 = base64.b64encode(f.read()).decode()

                fg_audio = folium.FeatureGroup(name='Vocalizações', show=False)
                for am in audio_markers:
                    a_lat = am.get('lat')
                    a_lon = am.get('lon')
                    if a_lat is not None and a_lon is not None:
                        # Icone Premium v0.8.2: Pin Customizado com Badge Numerado
                        audio_id = am.get('id', am.get('url', ''))
                        ranking = am.get('ranking', '?')
                        
                        # Pin background image + Badge superior
                        icon_html = f"""
                        <div style="position: relative; width: 44px; height: 44px;">
                            <!-- Pin Base -->
                            <img src="data:image/png;base64,{vocal_pin_b64}" 
                                 style="width: 44px; height: 44px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));"
                                 onclick="window.location.href='ibirder://audio_click?id={audio_id}'">
                            
                            <!-- Badge Numerado -->
                            <div style="
                                position: absolute;
                                top: -2px;
                                right: -2px;
                                background-color: #ef4444; 
                                color: white; 
                                border: 1.5px solid white;
                                border-radius: 50%;
                                width: 20px;
                                height: 20px;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-weight: bold;
                                font-size: 11px;
                                box-shadow: 0 1px 3px rgba(0,0,0,0.4);
                                pointer-events: none;
                                font-family: 'Segoe UI', sans-serif;">
                                {ranking}
                            </div>
                        </div>
                        """
                        
                        dist_val = am.get('distancia_km', 0)
                        dist_str = f"{dist_val:.0f}" if dist_val >= 1 else f"{dist_val:.1f}"
                        
                        folium.Marker(
                             [a_lat, a_lon],
                             icon=folium.DivIcon(html=icon_html, icon_size=(44, 44), icon_anchor=(22, 44)),
                             tooltip=f"Distância {dist_str}km"
                        ).add_to(fg_audio)
                fg_audio.add_to(m)

            folium.LayerControl(position='topright', collapsed=False).add_to(m)
            
            data = io.BytesIO()
            m.save(data, close_file=False)
            self.setHtml(data.getvalue().decode())
            
            if hasattr(self, 'alert_frame'):
                if not add_marker and not force_hide_alert:
                    self.alert_frame.show()
                    self.alert_frame.raise_()
                else:
                    self.alert_frame.hide()
            
        except Exception as e:
            self.setHtml(f"<html><body>Error loading map: {e}</body></html>")
