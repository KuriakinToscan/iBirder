from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
import io

class ExternalLinkPage(QWebEnginePage):
    def acceptNavigationRequest(self, url, _type, isMainFrame):
        if _type == QWebEnginePage.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
            return False
        return True

class MapWidget(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPage(ExternalLinkPage(self)) # Intercepta links to open in default browser

        # --- Alerta de GPS Ausente (v0.3.34) ---
        from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout
        from PySide6.QtGui import QGraphicsDropShadowEffect, QColor
        from PySide6.QtCore import Qt
        
        self.alert_frame = QFrame(self)
        self.alert_frame.setObjectName("overlay_alert")
        self.alert_frame.setStyleSheet("""
            QFrame#overlay_alert {
                background-color: rgba(254, 243, 199, 0.95);
                border: 1px solid #F59E0B;
                border-radius: 8px;
            }
            QLabel#alert_text {
                color: #92400E;
                font-size: 13px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
        """)
        
        layout = QVBoxLayout(self.alert_frame)
        layout.setContentsMargins(20, 12, 20, 12)
        
        lbl_alert = QLabel("Sem dados de localização, indique manualmente", self.alert_frame)
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

    def update_map(self, lat, lon, zoom=5, add_marker=False, scientific_name=None, audio_markers=None):
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
                show=True
            ).add_to(m)

            if add_marker:
                folium.Marker(
                    [lat, lon], 
                    icon=folium.Icon(color="red", icon="camera", prefix="glyphicon"),
                    tooltip="Local da Foto (Alvo)"
                ).add_to(m)
                
            if audio_markers:
                 for am in audio_markers:
                      folium.Marker(
                           [am['lat'], am['lon']],
                           icon=folium.Icon(color="purple", icon="music", prefix="glyphicon"),
                           tooltip=am.get('title', 'Áudio Gravado')
                      ).add_to(m)

            folium.LayerControl(position='topright', collapsed=False).add_to(m)
            
            data = io.BytesIO()
            m.save(data, close_file=False)
            self.setHtml(data.getvalue().decode())
            
            if hasattr(self, 'alert_frame'):
                if not add_marker:
                    self.alert_frame.show()
                    self.alert_frame.raise_()
                else:
                    self.alert_frame.hide()
            
        except Exception as e:
            self.setHtml(f"<html><body>Error loading map: {e}</body></html>")
